#!/bin/bash
#
# Usage:
#   bash exec_extended.sh
#
# Description:
#   2026-05-28 実験用スクリプト（初期版）。
#   スレッド数(1, 4, 8) × multiplier(0〜100, 10刻み) × work(0ns, 500ns) の
#   全組み合わせを3回繰り返して実行する。
#   wait_signal.c を都度ビルドしてから実行する。
#
# Parameters (in script):
#   REPS           = 3
#   THREADS        = (1 4 8)
#   MULTIPLIERS    = (0 10 20 ... 100)
#   WORK_DURATIONS = (0 500)   # ns
#   BINARY         = simple_lock
#   OUTDIR         = result_new
#
# Output:
#   result_new/w{0,500}/rep{1,2,3}/t{1,4,8}_m{0..100}.txt
#
# Prerequisites:
#   - wait_signal.c がカレントディレクトリにあること
#   - gcc, taskset, sudo cpupower が使用可能であること

set -e

REPS=3
THREADS=(1 4 8)
MULTIPLIERS=(0 10 20 30 40 50 60 70 80 90 100)
WORK_DURATIONS=(0 500)   # ns: 0=no work, 500=fixed 500ns critical section
BINARY=simple_lock
OUTDIR=result_new

# CPU frequency setup
echo "=== CPU Setup ==="
if sudo cpupower frequency-set -g performance 2>/dev/null; then
    echo "  governor: performance"
else
    echo "  WARNING: cpupower not available or failed"
fi
if echo 1 | sudo tee /sys/devices/system/cpu/intel_pstate/no_turbo > /dev/null 2>&1; then
    echo "  Intel turbo: disabled"
elif echo 0 | sudo tee /sys/devices/system/cpu/cpufreq/boost > /dev/null 2>&1; then
    echo "  AMD boost: disabled"
else
    echo "  WARNING: could not disable turbo/boost"
fi
echo ""

# Build
echo "=== Build ==="
gcc -O2 -march=native -o ${BINARY} wait_signal.c -lpthread
echo "  Built: ${BINARY}"
echo ""

# Setup output dirs
for w in "${WORK_DURATIONS[@]}"; do
    for rep in $(seq 1 $REPS); do
        mkdir -p ${OUTDIR}/w${w}/rep${rep}
    done
done

total=$((REPS * ${#THREADS[@]} * ${#MULTIPLIERS[@]} * ${#WORK_DURATIONS[@]}))
done_count=0
start_time=$(date +%s)

echo "=== Experiment ==="
echo "Reps: $REPS, Threads: ${THREADS[*]}, Multipliers: ${MULTIPLIERS[*]}, Work(ns): ${WORK_DURATIONS[*]}"
echo "Total runs: $total (est. ~$((total * 30 / 60)) min)"
echo ""

for w in "${WORK_DURATIONS[@]}"; do
    for rep in $(seq 1 $REPS); do
        echo "--- w=${w}ns, rep=${rep}/${REPS} ---"
        for t in "${THREADS[@]}"; do
            for m in "${MULTIPLIERS[@]}"; do
                taskset -c 0-7 ./${BINARY} -t $t -m $m -w $w \
                    > ${OUTDIR}/w${w}/rep${rep}/t${t}_m${m}.txt
                done_count=$((done_count + 1))
                elapsed=$(( $(date +%s) - start_time ))
                eta=$(( elapsed * (total - done_count) / done_count ))
                echo "  [${done_count}/${total}] t=${t} m=${m} w=${w} | elapsed=${elapsed}s eta=${eta}s"
            done
        done
    done
done

# Restore CPU settings
echo ""
echo "=== CPU Restore ==="
sudo cpupower frequency-set -g ondemand 2>/dev/null || true
if echo 0 | sudo tee /sys/devices/system/cpu/intel_pstate/no_turbo > /dev/null 2>&1; then
    echo "  Intel turbo: restored"
elif echo 1 | sudo tee /sys/devices/system/cpu/cpufreq/boost > /dev/null 2>&1; then
    echo "  AMD boost: restored"
fi

echo ""
echo "=== Done. Results in ${OUTDIR}/ ==="
