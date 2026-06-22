# Usage:
#   python3 summarize.py
#
# Description:
#   各サーバ・w 値・スレッド数の実験結果 (rep1/2/3) を集計し、
#   平均スループット・yield/sleep/ut_delay カウンタを summary_{t}.md として出力する。
#
# Parameters (in script):
#   BASE           = '/home/morisaki/simple_mysql/result'
#   SERVERS        = [ivy_c8220, broadwell_xl170, skylake_c220g5, skylake_ann, icelake_sm110, emerald_c6620]
#   WORK_DURATIONS = [0, 100, 200, 500, 1000, 2000, 5000]  # ns
#   THREADS        = [1, 4, 8, 16, 32]
#   REPS           = ['rep1', 'rep2', 'rep3']
#
# Input:
#   result/{server}/w{w}/rep{1,2,3}/t{t}_m{m}.txt
#   （なければ result/{server}/2026_5_28/w{w}/ にフォールバック）
#
# Output:
#   result/{server}/w{w}/summary_t{t}.md  : multiplier × throughput/カウンタの集計表

import os, re

DURATION = 30
BASE = '/home/morisaki/simple_mysql/result'
SERVERS = ['ivy_c8220', 'broadwell_xl170', 'skylake_c220g5', 'skylake_ann', 'icelake_sm110', 'emerald_c6620']
WORK_DURATIONS = [0, 100, 200, 500, 1000, 2000, 5000]
THREADS = [1, 4, 8, 16, 32]
REPS = ['rep1', 'rep2', 'rep3']

def get_data_dir(srv, w):
    """直下の w{w}/ を優先し、なければ 2026_5_28/w{w}/ を使う"""
    direct = f'{BASE}/{srv}/w{w}'
    if os.path.exists(f'{direct}/rep1'):
        return direct
    fallback = f'{BASE}/{srv}/2026_5_28/w{w}'
    if os.path.exists(f'{fallback}/rep1'):
        return fallback
    return None

def parse_file(path):
    with open(path) as f:
        content = f.read()
    tp   = re.search(r'Throughput: ([\d.]+) ops/sec', content)
    ud   = re.search(r'Global ut_delay count: (\d+)', content)
    yd   = re.search(r'Global yield count: (\d+)', content)
    sl   = re.search(r'Global sleep count: (\d+)', content)
    if not all([tp, ud, yd, sl]):
        return None
    return {
        'throughput': float(tp.group(1)),
        'ut_delay':   int(ud.group(1)) / DURATION,
        'yield':      int(yd.group(1)) / DURATION,
        'sleep':      int(sl.group(1)) / DURATION,
    }

created = 0
for srv in SERVERS:
    for w in WORK_DURATIONS:
        data_dir = get_data_dir(srv, w)
        if not data_dir:
            print(f'SKIP: {srv}/w{w} not found')
            continue
        muls = sorted(set(
            int(re.match(r't\d+_m(\d+)\.txt', f).group(1))
            for f in os.listdir(f'{data_dir}/rep1')
            if re.match(r't\d+_m(\d+)\.txt', f)
        ))
        for t in THREADS:
            rows = []
            for m in muls:
                vals = {'throughput': [], 'ut_delay': [], 'yield': [], 'sleep': []}
                for rep in REPS:
                    fpath = f'{data_dir}/{rep}/t{t}_m{m}.txt'
                    if not os.path.exists(fpath):
                        continue
                    r = parse_file(fpath)
                    if r:
                        for k in vals:
                            vals[k].append(r[k])
                if not vals['throughput']:
                    continue
                rows.append({
                    'm': m,
                    'throughput_avg':       sum(vals['throughput']) / len(vals['throughput']),
                    'ut_delay_per_sec_avg': sum(vals['ut_delay'])   / len(vals['ut_delay']),
                    'yield_per_sec_avg':    sum(vals['yield'])      / len(vals['yield']),
                    'sleep_per_sec_avg':    sum(vals['sleep'])      / len(vals['sleep']),
                    'n': len(vals['throughput']),
                })
            out_path = f'{data_dir}/summary_t{t}.md'
            with open(out_path, 'w') as f:
                f.write(f'# {srv} / w={w}ns / t={t}\n\n')
                f.write('| m | throughput_avg (ops/s) | ut_delay_per_sec | yield_per_sec | sleep_per_sec | n |\n')
                f.write('|---|---|---|---|---|---|\n')
                for row in rows:
                    f.write(f"| {row['m']} | {row['throughput_avg']:.2f} | {row['ut_delay_per_sec_avg']:.2f} | {row['yield_per_sec_avg']:.4f} | {row['sleep_per_sec_avg']:.4f} | {row['n']} |\n")
            print(f'created: {out_path} ({len(rows)} rows)')
            created += 1

print(f'\nTotal: {created} files created')
