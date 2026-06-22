#!/bin/bash
#
# Usage:
#   bash run.sh <BINARY> [SERVER_NAME]
#
# Examples:
#   bash run.sh simple_spinlock
#   bash run.sh simple_spinlock ivy_c8220
#   nohup bash run.sh simple_spinlock ivy_c8220 > result/ivy_c8220/experiment.log 2>&1 &
#
# Parameters:
#   BINARY      : 実行するバイナリ名（例: simple_spinlock, debug_simple_spinlock）必須
#   SERVER_NAME : 結果保存ディレクトリ名（省略時は hostname -s）
#
# Environment variables (override defaults):
#   THREADS         : スレッド数リスト（デフォルト: "8 16 32"）
#   MULTIPLIERS     : multiplierリスト（デフォルト: "0 10 20 ... 50000"）
#   WORK_DURATIONS  : work duration リスト in ns（デフォルト: "0 100 200 500 1000 2000 5000"）
#   REPS            : 繰り返し回数（デフォルト: 3）
#
# Examples with overrides:
#   THREADS="4 8" WORK_DURATIONS="0 500" bash run.sh simple_spinlock broadwell_xl170
#
# Output:
#   result/${SERVER_NAME}/w<w>/rep<n>/t<t>_m<m>.txt
#
# Prerequisites:
#   - ./<BINARY> がカレントディレクトリにあること（make または gcc でビルド済み）
#   - sudo 権限があること（cpupower, intel_pstate 設定に使用）

set -e

if [ $# -lt 1 ]; then
    echo "Usage: $0 <BINARY> [SERVER_NAME]" >&2
    exit 1
fi

BINARY=$1
SERVER=${2:-$(hostname -s)}

REPS=${REPS:-3}
read -ra THREADS        <<< "${THREADS:-8 16 32}"
read -ra MULTIPLIERS    <<< "${MULTIPLIERS:-0 10 20 30 40 50 60 70 80 90 100 150 200 250 300 400 500 700 1000 2000 3000 5000 7000 10000 20000 50000}"
read -ra WORK_DURATIONS <<< "${WORK_DURATIONS:-0 100 200 500 1000 2000 5000}"

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

echo "=== Experiment (Binary: ${BINARY}, Server: ${SERVER}) ==="
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
                if ! timeout 45 taskset -c 0-7 ./${BINARY} -t $t -m $m -w $w > "$outfile"; then
                    echo "  [${done_count}/${total}] TIMEOUT/ERROR t=${t} m=${m} w=${w} -- skipping" >&2
                    rm -f "$outfile"
                    continue
                fi
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
