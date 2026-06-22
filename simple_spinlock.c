#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <pthread.h>
#include <stdatomic.h>
#include <sched.h>
#include <unistd.h>
#include <stdalign.h>
#include <stdint.h>
#include <time.h>
#include <x86gprintrin.h>

#define cpu_relax()     asm volatile("rep; nop")
#define DURATION 30
#define WORKING_SET_SIZE (1024 * 1024) // 1MB程度のバッファ

alignas(64) atomic_bool	lock_var;
alignas(64) atomic_bool stop_flag = false;

alignas(64) pthread_mutex_t mutex = PTHREAD_MUTEX_INITIALIZER;
alignas(64) pthread_cond_t  cond  = PTHREAD_COND_INITIALIZER;

alignas(64) char dummy_buffer[WORKING_SET_SIZE];

alignas(64) long long	total_count = 0;

typedef struct thread_arg {
	int thread_id;
	long long count;
} thread_arg_t;

// 実験パラメータ
alignas(64) unsigned int	num_threads = 16;
alignas(64) unsigned int	spin_wait_pause_multiplier = 50;
alignas(64) unsigned int	spin_wait_rounds = 30;
alignas(64) unsigned int	spin_wait_delay = 6;
alignas(64) long			work_ns = 0;

void lock_init(atomic_bool *l) {
	atomic_store(l, false);
}

static double tsc_cycles_per_ns = 0.0;

static void calibrate_tsc(void) {
	struct timespec t1, t2;
	uint64_t c1, c2;

	clock_gettime(CLOCK_MONOTONIC, &t1);
	c1 = __rdtsc();
	struct timespec sleep_ts = {0, 100000000L}; // 100ms
	nanosleep(&sleep_ts, NULL);
	c2 = __rdtsc();
	clock_gettime(CLOCK_MONOTONIC, &t2);

	long elapsed_ns = (t2.tv_sec - t1.tv_sec) * 1000000000L + (t2.tv_nsec - t1.tv_nsec);
	tsc_cycles_per_ns = (double)(c2 - c1) / elapsed_ns;
	printf("TSC calibration: %.4f cycles/ns (%.4f GHz)\n",
	       tsc_cycles_per_ns, tsc_cycles_per_ns);
}

static void busy_wait_ns(long ns)
{
	if (ns <= 0) return;
	uint64_t target = __rdtsc() + (uint64_t)((double)ns * tsc_cycles_per_ns);
	while (__rdtsc() < target);
}

// https://github.com/mysql/mysql-server/blob/trunk/storage/innobase/ut/ut0ut.cc#L95
unsigned long ut_delay(unsigned long delay) {
	unsigned long i, j;
	const unsigned long iterations = delay * spin_wait_pause_multiplier;

	// 低優先度にする
	// UT_LOW_PRIORITY_CPU();

	j = 0;

	for (i = 0; i < iterations; i++) {
	  j += i;
	  cpu_relax();
	}

	// 優先度を戻す
	// UT_RESUME_PRIORITY_CPU();

	return (j);
}

// https://github.com/mysql/mysql-server/blob/447eb26e094b444a88c532028647e48228c3c04f/storage/innobase/sync/sync0rw.cc#L273
bool lock_acquire(atomic_bool *l) {
	unsigned long	i = 0;

lock_loop:

	while (i < spin_wait_rounds && atomic_load_explicit(l, memory_order_relaxed)) {
		if (spin_wait_delay) {
			ut_delay(rand() % spin_wait_delay);
		}

		i++;
	}

	if (i >= spin_wait_rounds) {
		sched_yield();
	}

	// atomic_exchange_explicitは変更前の値が返されるのでfalseなら成功、trueならすでに他のスレッドがロックを獲得済みと判断できる
	if (!atomic_exchange_explicit(l, true, memory_order_acquire)) {
		return true;
	} else {
		if (i < spin_wait_rounds) {
			goto lock_loop;
		}

		// lock holderからシグナルを受け取るまでスリープ
		pthread_mutex_lock(&mutex);
		if (!atomic_load_explicit(&stop_flag, memory_order_relaxed) &&
		    atomic_load_explicit(l, memory_order_relaxed)) {
			pthread_cond_wait(&cond, &mutex);
		}
		bool stopping = atomic_load_explicit(&stop_flag, memory_order_relaxed);
		pthread_mutex_unlock(&mutex);
		if (stopping) return false;

		i = 0;

		goto lock_loop;
	}
}

void lock_release(atomic_bool *l) {
	atomic_exchange_explicit(l, false, memory_order_release);
	pthread_mutex_lock(&mutex);
	// cond_signalはブロックしているスレッドを少なくとも1つ以上起床させる
	pthread_cond_signal(&cond);
	pthread_mutex_unlock(&mutex);
}

void fake_work() {
    // 適当な場所を数カ所読み書きしてキャッシュミスを誘発
    for (int i = 0; i < 8; i++) {
        int target = rand() % WORKING_SET_SIZE;
        dummy_buffer[target] += (char)i;
    }
}

void *thread_func(void *param)
{
	thread_arg_t *arg = (thread_arg_t *)param;

	while (!atomic_load_explicit(&stop_flag, memory_order_relaxed)) {
		if (!lock_acquire(&lock_var)) break;
		busy_wait_ns(work_ns);
		arg->count++;
		lock_release(&lock_var);
	}
	return NULL;
}

int main(int argc, char *argv[]) {
	int opt;
	while ((opt = getopt(argc, argv, "t:m:r:w:")) != -1) {
		switch (opt) {
			case 't':
				num_threads = atoi(optarg);
				break;
			case 'm':
				spin_wait_pause_multiplier = atoi(optarg);
				break;
			case 'r':
				spin_wait_rounds = atoi(optarg);
				break;
			case 'w':
				work_ns = atol(optarg);
				break;
			default:
				fprintf(stderr, "Usage: %s [-t num_threads] [-m multiplier] [-r rounds] [-w work_ns]\n", argv[0]);
				exit(EXIT_FAILURE);
		}
	}
	pthread_t *threads = malloc(sizeof(pthread_t) * num_threads);
	if (!threads) {
		perror("malloc");
		return 1;
	}
	thread_arg_t *thread_args = calloc(num_threads, sizeof(thread_arg_t));
	if (!thread_args) {
		perror("calloc");
		free(threads);
		return 1;
	}

	lock_init(&lock_var);
	lock_init(&stop_flag);

	calibrate_tsc();
	printf("Starting experiment: Threads=%u, Multiplier=%u, Rounds=%u, WorkNs=%ld\n", num_threads, spin_wait_pause_multiplier, spin_wait_rounds, work_ns);

	for (int i = 0; i < num_threads; i++) {
		thread_args[i].thread_id = i;
		if (pthread_create(&threads[i], NULL, thread_func, &thread_args[i]) != 0) {
			perror("fail: pthread_create");
			free(thread_args);
			return 1;
		}
		// printf("Thread[%d] is created\n", i);
	}

	sleep(DURATION);
	pthread_mutex_lock(&mutex);
	atomic_store_explicit(&stop_flag, true, memory_order_relaxed);
	pthread_cond_broadcast(&cond);
	pthread_mutex_unlock(&mutex);

	for (int i = 0; i < num_threads; i++) {
		pthread_join(threads[i], NULL);
	}

	for (int i = 0; i < num_threads; i++) {
		total_count += thread_args[i].count;
	}

	printf("------------------------------------\n");
	printf("Total Counter: %lld\n", total_count);
	printf("Throughput: %.2f ops/sec\n", (double)total_count / DURATION);
	printf("Work[ns]: %ld\n", work_ns);

	free(thread_args);
	free(threads);
	return 0;
}
