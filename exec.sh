#!/bin/bash

FAKE=with_fakework
DEFAULT=without_fakework

mkdir -p result/{${FAKE},${DEFAULT}}

# with light request
# thread: 1
taskset -c 0-3 ./${DEFAULT} -t 1 -m 0 > result/${DEFAULT}/t1_m0.txt
taskset -c 0-3 ./${DEFAULT} -t 1 -m 25 > result/${DEFAULT}/t1_m25.txt
taskset -c 0-3 ./${DEFAULT} -t 1 -m 50 > result/${DEFAULT}/t1_m50.txt
taskset -c 0-3 ./${DEFAULT} -t 1 -m 100 > result/${DEFAULT}/t1_m100.txt
taskset -c 0-3 ./${DEFAULT} -t 1 -m 200 > result/${DEFAULT}/t1_m200.txt
taskset -c 0-3 ./${DEFAULT} -t 1 -m 500 > result/${DEFAULT}/t1_m500.txt
taskset -c 0-3 ./${DEFAULT} -t 1 -m 1000 > result/${DEFAULT}/t1_m1000.txt
taskset -c 0-3 ./${DEFAULT} -t 1 -m 5000 > result/${DEFAULT}/t1_m5000.txt
taskset -c 0-3 ./${DEFAULT} -t 1 -m 10000 > result/${DEFAULT}/t1_m10000.txt
# thread: 8
taskset -c 0-3 ./${DEFAULT} -t 8 -m 0 > result/${DEFAULT}/t8_m0.txt
taskset -c 0-3 ./${DEFAULT} -t 8 -m 25 > result/${DEFAULT}/t8_m25.txt
taskset -c 0-3 ./${DEFAULT} -t 8 -m 50 > result/${DEFAULT}/t8_m50.txt
taskset -c 0-3 ./${DEFAULT} -t 8 -m 100 > result/${DEFAULT}/t8_m100.txt
taskset -c 0-3 ./${DEFAULT} -t 8 -m 200 > result/${DEFAULT}/t8_m200.txt
taskset -c 0-3 ./${DEFAULT} -t 8 -m 500 > result/${DEFAULT}/t8_m500.txt
taskset -c 0-3 ./${DEFAULT} -t 8 -m 1000 > result/${DEFAULT}/t8_m1000.txt
taskset -c 0-3 ./${DEFAULT} -t 8 -m 5000 > result/${DEFAULT}/t8_m5000.txt
taskset -c 0-3 ./${DEFAULT} -t 8 -m 10000 > result/${DEFAULT}/t8_m10000.txt

# with heavy request
# thread: 1
taskset -c 0-3 ./${FAKE} -t 1 -m 0 > result/${FAKE}/t1_m0.txt
taskset -c 0-3 ./${FAKE} -t 1 -m 25 > result/${FAKE}/t1_m25.txt
taskset -c 0-3 ./${FAKE} -t 1 -m 50 > result/${FAKE}/t1_m50.txt
taskset -c 0-3 ./${FAKE} -t 1 -m 100 > result/${FAKE}/t1_m100.txt
taskset -c 0-3 ./${FAKE} -t 1 -m 200 > result/${FAKE}/t1_m200.txt
taskset -c 0-3 ./${FAKE} -t 1 -m 500 > result/${FAKE}/t1_m500.txt
taskset -c 0-3 ./${FAKE} -t 1 -m 1000 > result/${FAKE}/t1_m1000.txt
taskset -c 0-3 ./${FAKE} -t 1 -m 5000 > result/${FAKE}/t1_m5000.txt
taskset -c 0-3 ./${FAKE} -t 1 -m 10000 > result/${FAKE}/t1_m10000.txt

# thread: 8
taskset -c 0-3 ./${FAKE} -t 8 -m 0 > result/${FAKE}/t8_m0.txt
taskset -c 0-3 ./${FAKE} -t 8 -m 25 > result/${FAKE}/t8_m25.txt
taskset -c 0-3 ./${FAKE} -t 8 -m 50 > result/${FAKE}/t8_m50.txt
taskset -c 0-3 ./${FAKE} -t 8 -m 100 > result/${FAKE}/t8_m100.txt
taskset -c 0-3 ./${FAKE} -t 8 -m 200 > result/${FAKE}/t8_m200.txt
taskset -c 0-3 ./${FAKE} -t 8 -m 500 > result/${FAKE}/t8_m500.txt
taskset -c 0-3 ./${FAKE} -t 8 -m 1000 > result/${FAKE}/t8_m1000.txt
taskset -c 0-3 ./${FAKE} -t 8 -m 5000 > result/${FAKE}/t8_m5000.txt
taskset -c 0-3 ./${FAKE} -t 8 -m 10000 > result/${FAKE}/t8_m10000.txt

# draw graph
python3 draw_graph.py result/without_fakework/t1_m* without_fakework_thread1
python3 draw_graph.py result/without_fakework/t8_m* without_fakework_thread8
python3 draw_graph.py result/with_fakework/t1_m* with_fakework_thread1
python3 draw_graph.py result/with_fakework/t8_m* with_fakework_thread8