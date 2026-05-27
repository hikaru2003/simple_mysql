#include <stdio.h>
#include <signal.h>
#include <x86gprintrin.h>

#define cpu_relax() asm volatile ("rep; nop")

static int stopped = 0;
unsigned long long count = 0;

int main(void)
{
	unsigned long long start, end;
	int cnt = 10000000;

	start = __rdtsc();
	for (int i = 0; i < cnt; i++) {
		cpu_relax();
	}
	end = __rdtsc();
	double ave = (double)(end - start) / cnt;
	printf("%.2lf\n", ave);

	return 0;
}
