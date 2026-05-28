#!/bin/bash
#
# exec_extended.sh の再開版。完了済みの出力ファイルはスキップする。
#
# Usage:
#   bash exec_resume.sh [SERVER_NAME]
#
# Examples:
#   bash exec_resume.sh                  # SERVER_NAME = $(hostname -s)
#   bash exec_resume.sh broadwell_xl170  # SERVER_NAME を明示指定
#   nohup bash exec_resume.sh broadwell_xl170 > result/broadwell_xl170/experiment_resume.log 2>&1 &
#
# Skip condition:
#   出力ファイルが存在し "Total Counter:" を含む場合はスキップ（正常終了済みと判断）
#   途中で強制終了されたファイルは不完全なので再実行される
#
# Output:
#   result/${SERVER_NAME}/w{0,500}/rep{1,2,3}/t{4,8}_m{250..10000}.txt
#
# Prerequisites:
#   - ./simple_lock がカレントディレクトリにあること（make または gcc でビルド済み）
#   - sudo 権限があること（cpupower, intel_pstate 設定に使用）

set -e

REPS=3
THREADS=(4 8)
MULTIPLIERS=(0 10 20 30 40 50 60 70 80 90 100)
WORK_DURATIONS=(0 500)   # ns: 0=no work, 500=fixed 500ns critical section
BINARY=simple_lock
SERVER=${1:-$(hostname -s)}
OUTDIR=result/${SERVER}

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

# Setup output dirs
for w in "${WORK_DURATIONS[@]}"; do
    for rep in $(seq 1 $REPS); do
        mkdir -p ${OUTDIR}/w${w}/rep${rep}
    done
done

total=$((REPS * ${#THREADS[@]} * ${#MULTIPLIERS[@]} * ${#WORK_DURATIONS[@]}))
done_count=0
skip_count=0
start_time=$(date +%s)

echo "=== Experiment Resume (Server: ${SERVER}) ==="
echo "Reps: $REPS, Threads: ${THREADS[*]}, Multipliers: ${MULTIPLIERS[*]}, Work(ns): ${WORK_DURATIONS[*]}"
echo "Total runs: $total (est. ~$((total * 30 / 60)) min)"
echo ""

for w in "${WORK_DURATIONS[@]}"; do
    for rep in $(seq 1 $REPS); do
        echo "--- w=${w}ns, rep=${rep}/${REPS} ---"
        for t in "${THREADS[@]}"; do
            for m in "${MULTIPLIERS[@]}"; do
                outfile=${OUTDIR}/w${w}/rep${rep}/t${t}_m${m}.txt
                done_count=$((done_count + 1))
                if grep -q "Total Counter:" "$outfile" 2>/dev/null; then
                    skip_count=$((skip_count + 1))
                    echo "  [${done_count}/${total}] SKIP t=${t} m=${m} w=${w}"
                    continue
                fi
                taskset -c 0-7 ./${BINARY} -t $t -m $m -w $w > "$outfile"
                elapsed=$(( $(date +%s) - start_time ))
                remaining=$((total - done_count))
                ran=$((done_count - skip_count))
                eta=$(( ran > 0 ? elapsed * remaining / ran : 0 ))
                echo "  [${done_count}/${total}] t=${t} m=${m} w=${w} | elapsed=${elapsed}s eta=${eta}s"
            done
        done
    done
done

echo ""
echo "=== Done. Results in ${OUTDIR}/ (skipped: ${skip_count}/${total}) ==="
