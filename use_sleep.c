#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <pthread.h>
#include <stdatomic.h>
#include <sched.h>
#include <unistd.h>

// #define cpu_relax()     asm volatile("rep; nop")
#define cpu_relax()     asm volatile("pause" ::: "memory")

#define DURATION 10
#define NUM_THREADS 16
#define SLEEP_TIME 100 // nano sec

alignas(64) atomic_bool	lock_var;
alignas(64) atomic_bool stop_flag = false;

alignas(64) long long	total_count = 0;
alignas(64) long long	global_ut_delay_count = 0;
alignas(64) long long	global_yield_count = 0;
alignas(64) long long	global_sleep_count = 0;

alignas(64) unsigned int spin_wait_delay = 6;
alignas(64) unsigned int spin_wait_pause_multiplier = 0;
alignas(64) unsigned int spin_wait_rounds = 30;

void lock_init(atomic_bool *l) {
	atomic_store(l, false);
}

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

void lock_acquire(atomic_bool *l) {
	unsigned long	i = 0;

lock_loop:

	while (i < spin_wait_rounds && atomic_load_explicit(l, memory_order_relaxed)) {
		if (spin_wait_delay) {
			atomic_fetch_add_explicit(&global_ut_delay_count, 1, memory_order_relaxed);
			ut_delay(rand() % spin_wait_delay);
		}

		i++;
	}

	if (i >= spin_wait_rounds) {
		atomic_fetch_add_explicit(&global_yield_count, 1, memory_order_relaxed);
		sched_yield();
	}

	// atomic_exchange_explicitは変更前の値が返されるのでfalseなら成功、trueならすでに他のスレッドがロックを獲得済みと判断できる
	if (!atomic_exchange_explicit(l, true, memory_order_acquire)) {
		return;
	} else {
		if (i < spin_wait_rounds) {
			goto lock_loop;
		}

		atomic_fetch_add_explicit(&global_sleep_count, 1, memory_order_relaxed);

		struct timespec ts = {0, SLEEP_TIME};
		nanosleep(&ts, NULL);

		i = 0;
		
		goto lock_loop;
	}
}

void lock_release(atomic_bool *l) {
	atomic_exchange_explicit(l, false, memory_order_release);
}

void fake_work() {

}

void *thread_func(void *param)
{
	while (!atomic_load_explicit(&stop_flag, memory_order_relaxed)) {
		lock_acquire(&lock_var);
		// fake_work();
		total_count++;
		lock_release(&lock_var);
	}
	return NULL;
}

int main(int argc, char *argv) {
	pthread_t threads[NUM_THREADS];

	if (argc == 2) {
		spin_wait_pause_multiplier = (unsigned int)argv[1];
	}

	lock_init(&lock_var);
	lock_init(&stop_flag);

	for (int i = 0; i < NUM_THREADS; i++) {
		if (pthread_create(&threads[i], NULL, thread_func, NULL) != 0) {
			perror("fail: pthread_create");
			return 1;
		}
		printf("Thread[%d] is created\n", i);
	}

	sleep(DURATION);
	atomic_store_explicit(&stop_flag, true, memory_order_relaxed);

	for (int i = 0; i < NUM_THREADS; i++) {
		pthread_join(threads[i], NULL);
	}

	printf("Finished Main Thread\n");
	printf("Total Counter: %lld\n", total_count);
	printf("Throughput: %.2f ops/sec\n", (double)total_count / DURATION);
	printf("Global ut_delay count: %lld\n", global_ut_delay_count);
	printf("Global yield count: %lld\n", global_yield_count);
	printf("Global sleep count: %lld\n", global_sleep_count);
	
	return 0;
}