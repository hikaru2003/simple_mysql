import os, re
import matplotlib.pyplot as plt

BASE = '/home/morisaki/simple_mysql/result'

SERVERS = [
    ('ivy_c8220',       {'pause': 14.56,  'label': 'Ivy Bridge (c8220)',        'color': '#4CAF50', 'ls': '-'}),
    ('broadwell_xl170', {'pause': 12.34,  'label': 'Broadwell (xl170)',         'color': '#2196F3', 'ls': '-'}),
    ('skylake_c220g5',  {'pause': 141.97, 'label': 'Skylake HTT-on (c220g5)',  'color': '#FF5722', 'ls': '-'}),
    ('skylake_ann',     {'pause': 142.31, 'label': 'Skylake HTT-off (ann)',    'color': '#FF9800', 'ls': '--'}),
    ('emerald_c6620',   {'pause': 37.15,  'label': 'Emerald Rapids (c6620)',   'color': '#FF0000', 'ls': '-'}),
]

# ---- データ読み込み ----

def _summary_path(srv, w, t, use_old=False):
    if use_old:
        return f'{BASE}/{srv}/2026_5_28/w{w}/summary_t{t}.md'
    direct = f'{BASE}/{srv}/w{w}/summary_t{t}.md'
    if os.path.exists(direct):
        return direct
    return f'{BASE}/{srv}/2026_5_28/w{w}/summary_t{t}.md'

def load_summary(srv, w, t, use_old=False):
    path = _summary_path(srv, w, t, use_old)
    if not os.path.exists(path):
        return [], []
    muls, tps = [], []
    with open(path) as f:
        for line in f:
            m = re.match(r'\| (\d+) \| ([\d.]+) \|', line)
            if m:
                muls.append(int(m.group(1)))
                tps.append(float(m.group(2)) / 1e6)
    return muls, tps

def load_counters(srv, w, t, use_old=False):
    path = _summary_path(srv, w, t, use_old)
    if not os.path.exists(path):
        return {k: [] for k in ['m', 'ut_delay', 'yield', 'sleep']}
    data = {k: [] for k in ['m', 'ut_delay', 'yield', 'sleep']}
    with open(path) as f:
        for line in f:
            m = re.match(r'\| (\d+) \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \|', line)
            if m:
                data['m'].append(int(m.group(1)))
                data['ut_delay'].append(float(m.group(3)) / 1e6)
                data['yield'].append(float(m.group(4)))
                data['sleep'].append(float(m.group(5)))
    return data

def get_ref_muls(w, t, use_old=False):
    all_muls = set()
    for srv, _ in SERVERS:
        muls, _ = load_summary(srv, w, t, use_old)
        all_muls.update(muls)
    return sorted(all_muls)

def to_index(muls, ref_muls):
    idx_map = {v: i for i, v in enumerate(ref_muls)}
    return [idx_map[m] for m in muls if m in idx_map], [v for v in muls if v in idx_map]

def set_categorical_xticks(ax, ref_muls):
    ax.set_xticks(range(len(ref_muls)))
    ax.set_xticklabels([str(m) for m in ref_muls], rotation=45, ha='right', fontsize=8)

# ---- グラフ描画 ----

def plot_comparison_all(threads=(4, 8, 16, 32), use_old=False, suffix=''):
    fig, axes = plt.subplots(2, len(threads), figsize=(7 * len(threads), 10))
    tag = '(old: atomic counter)' if use_old else '(new: local counter)'
    fig.suptitle(f'Throughput vs spin_wait_pause_multiplier\n{tag}',
                 fontsize=14, fontweight='bold')

    for row, w in enumerate([0, 500]):
        for col, t in enumerate(threads):
            ax = axes[row][col]
            ref_muls = get_ref_muls(w, t, use_old)
            for srv, meta in SERVERS:
                muls, tps = load_summary(srv, w, t, use_old)
                if not muls:
                    continue
                xs, _ = to_index(muls, ref_muls)
                ax.plot(xs, tps, marker='o', markersize=5, linewidth=2,
                        color=meta['color'], linestyle=meta['ls'],
                        label=f"{meta['label']} (PAUSE={meta['pause']} cyc)")
            ax.set_title(f'w={w}ns, t={t}', fontsize=11)
            ax.set_xlabel('spin_wait_pause_multiplier')
            ax.set_ylabel('Throughput (Mops/s)')
            ax.legend(fontsize=7, loc='lower right')
            ax.grid(True, alpha=0.3)
            set_categorical_xticks(ax, ref_muls)

    plt.tight_layout()
    out = f'{BASE}/comparison_all{suffix}.png'
    plt.savefig(out, dpi=150, bbox_inches='tight')
    print(f'saved: {out}')
    plt.close()


def plot_counters(t, use_old=False, suffix=''):
    fig, axes = plt.subplots(2, 3, figsize=(17, 10))
    tag = '(old: atomic counter)' if use_old else '(new: local counter)'
    fig.suptitle(f'Counter rates vs multiplier  t={t}, w=0ns vs w=500ns  {tag}',
                 fontsize=13, fontweight='bold')

    metrics = [('ut_delay', 'ut_delay calls/s (M)'), ('yield', 'sched_yield calls/s'), ('sleep', 'cond_wait calls/s')]

    for col, (key, ylabel) in enumerate(metrics):
        for row, w in enumerate([0, 500]):
            ax = axes[row][col]
            ref_muls = get_ref_muls(w, t, use_old)
            for srv, meta in SERVERS:
                d = load_counters(srv, w, t, use_old)
                if not d['m']:
                    continue
                xs, _ = to_index(d['m'], ref_muls)
                ax.plot(xs, d[key], marker='o', markersize=5, linewidth=2,
                        color=meta['color'], linestyle=meta['ls'],
                        label=f"{meta['label']} (PAUSE={meta['pause']} cyc)")
            ax.set_title(f'w={w}ns: {ylabel}')
            ax.set_xlabel('spin_wait_pause_multiplier')
            ax.set_ylabel(ylabel)
            ax.legend(fontsize=7)
            ax.grid(True, alpha=0.3)
            set_categorical_xticks(ax, ref_muls)

    plt.tight_layout()
    out = f'{BASE}/counters_t{t}_w0_w500{suffix}.png'
    plt.savefig(out, dpi=150, bbox_inches='tight')
    print(f'saved: {out}')
    plt.close()


def plot_effective_cycles(use_old=False, suffix=''):
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    tag = '(old: atomic counter)' if use_old else '(new: local counter)'
    fig.suptitle(f'Throughput vs Effective PAUSE cycles per spin  {tag}',
                 fontsize=13, fontweight='bold')

    for ax, (w, t) in zip(axes, [(0, 8), (0, 4)]):
        for srv, meta in SERVERS:
            muls, tps = load_summary(srv, w, t, use_old)
            if not muls:
                continue
            eff = [2.5 * m * meta['pause'] for m in muls]
            ax.plot(eff, tps, marker='o', markersize=5, linewidth=2,
                    color=meta['color'], linestyle=meta['ls'],
                    label=f"{meta['label']} (PAUSE={meta['pause']} cyc)")
        ax.set_title(f'w={w}ns, t={t}')
        ax.set_xlabel('Effective PAUSE cycles per spin (2.5 x m x PAUSE_cycles)')
        ax.set_ylabel('Throughput (Mops/s)')
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
        ax.set_xscale('symlog', linthresh=1)

    plt.tight_layout()
    out = f'{BASE}/effective_cycles{suffix}.png'
    plt.savefig(out, dpi=150, bbox_inches='tight')
    print(f'saved: {out}')
    plt.close()


if __name__ == '__main__':
    # 新実験 (local counter)
    plot_comparison_all(threads=(4, 8, 16, 32), use_old=False, suffix='')
    for t in [4, 8, 16, 32]:
        plot_counters(t, use_old=False, suffix='')
    plot_effective_cycles(use_old=False, suffix='')

    # 旧実験 (atomic counter, 2026_5_28)
    plot_comparison_all(threads=(4, 8), use_old=True, suffix='_old')
    for t in [4, 8]:
        plot_counters(t, use_old=True, suffix='_old')
    plot_effective_cycles(use_old=True, suffix='_old')

    print('All graphs generated.')
