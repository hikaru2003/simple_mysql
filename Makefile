CC      = gcc
CFLAGS  = -O2
LDFLAGS = -lpthread

TARGETS = simple_spinlock debug_simple_spinlock

.PHONY: all clean

all: $(TARGETS)

simple_spinlock: simple_spinlock.c
	$(CC) $(CFLAGS) -o $@ $< $(LDFLAGS)

debug_simple_spinlock: debug_simple_spinlock.c
	$(CC) $(CFLAGS) -o $@ $< $(LDFLAGS)

clean:
	rm -f $(TARGETS)
