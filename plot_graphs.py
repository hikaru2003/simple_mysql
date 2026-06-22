# Usage:
#   python3 plot_graphs.py
#
# Description:
#   各サーバの実験サマリ (summary_t{t}.md) を読み込み、複数のグラフを生成する。
#   グラフは result/ および result/per_server/ に出力される。
#
# Parameters (in script):
#   BASE      = '/home/morisaki/simple_mysql/result'
#   SERVERS   : サーバ名・PAUSE cycles・色などを定義するリスト
#   ALL_W     = [0, 100, 200, 500, 1000, 2000, 5000]  # 対象 work duration (ns)
#   W_GROUPS  : F2グラフ用 w の4グループ定義
#
# Input:
#   result/{server}/w{w}/summary_t{t}.md
#
# Output:
#   result/graph_A_throughput_by_t.png        : 全サーバ比較スループット（w=0, t=8/16/32）
#   result/graph_B_throughput_by_w.png        : 全サーバ比較スループット（サーバ別, 全w, t=8）
#   result/graph_C_effective_cycles.png       : PAUSE effective cycles 正規化
#   result/graph_D_counters.png               : yield/sleep/ut_delay カウンタ（w=0 vs w=500, t=8）
#   result/graph_E_optimal_m_scatter.png      : 最適m vs PAUSE cycles 散布図
#   result/comparison_all.png                 : 全サーバ比較（w=0,500 × t=8,16,32）
#   result/effective_cycles.png               : PAUSE effective cycles（レガシー形式）
#   result/counters_t{8,16,32}_w0_w500.png    : カウンタ推移（レガシー形式）
#   result/per_server/{srv}_t{t}_all_metrics.png : サーバ別 4パネル（スループット/ut_delay/yield/sleep）
#   result/per_server/{srv}_throughput_grouped.png: サーバ別スループット（w 4グループ, t=8/16/32）
#
# Prerequisites:
#   pip install matplotlib numpy pandas
#   summarize.py を先に実行して summary_t{t}.md を生成しておくこと

import os, re
import matplotlib.pyplot as plt
import numpy as np

BASE = '/home/morisaki/simple_mysql/result'

SERVERS = [
    ('ivy_c8220',       {'pause': 14.56,  'label': 'Ivy Bridge (c8220)',       'color': '#4CAF50', 'ls': '-'}),
    ('broadwell_xl170', {'pause': 12.34,  'label': 'Broadwell (xl170)',        'color': '#2196F3', 'ls': '-'}),
    ('skylake_c220g5',  {'pause': 141.97, 'label': 'Skylake HTT-on (c220g5)', 'color': '#FF5722', 'ls': '-'}),
    ('skylake_ann',     {'pause': 142.31, 'label': 'Skylake HTT-off (ann)',   'color': '#FF9800', 'ls': '--'}),
    ('icelake_sm110',   {'pause': 38.86,  'label': 'Ice Lake (sm110)',         'color': '#9C27B0', 'ls': '-'}),
    ('emerald_c6620',   {'pause': 37.15,  'label': 'Emerald Rapids (c6620)',  'color': '#E91E63', 'ls': '-'}),
]

ALL_W = [0, 100, 200, 500, 1000, 2000, 5000]
W_COLORS = ['#1565C0', '#0288D1', '#00838F', '#388E3C', '#F57F17', '#E65100', '#B71C1C']

# ---- data loading ----

def _summary_path(srv, w, t):
    direct = f'{BASE}/{srv}/w{w}/summary_t{t}.md'
    if os.path.exists(direct):
        return direct
    fallback = f'{BASE}/{srv}/2026_5_28/w{w}/summary_t{t}.md'
    if os.path.exists(fallback):
        return fallback
    return None

def load_summary(srv, w, t):
    path = _summary_path(srv, w, t)
    if not path:
        return [], []
    muls, tps = [], []
    with open(path) as f:
        for line in f:
            m = re.match(r'\| (\d+) \| ([\d.]+) \|', line)
            if m:
                muls.append(int(m.group(1)))
                tps.append(float(m.group(2)) / 1e6)
    return muls, tps

def load_counters(srv, w, t):
    path = _summary_path(srv, w, t)
    if not path:
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

def get_ref_muls_servers(w, t):
    all_muls = set()
    for srv, _ in SERVERS:
        muls, _ = load_summary(srv, w, t)
        all_muls.update(muls)
    return sorted(all_muls)

def get_ref_muls_w(srv, t):
    all_muls = set()
    for w in ALL_W:
        muls, _ = load_summary(srv, w, t)
        all_muls.update(muls)
    return sorted(all_muls)

def to_index(muls, ref_muls):
    idx_map = {v: i for i, v in enumerate(ref_muls)}
    return [idx_map[m] for m in muls if m in idx_map]

def set_xticks(ax, ref_muls):
    ax.set_xticks(range(len(ref_muls)))
    ax.set_xticklabels([str(m) for m in ref_muls], rotation=45, ha='right', fontsize=7)

# ---- Graph A: throughput vs m, all servers, w=0 ----

def plot_graph_A(threads=(8, 16, 32)):
    fig, axes = plt.subplots(1, len(threads), figsize=(7 * len(threads), 5))
    fig.suptitle('Graph A: Throughput vs spin_wait_pause_multiplier  [w=0ns, no lock hold time]',
                 fontsize=13, fontweight='bold')
    w = 0
    for col, t in enumerate(threads):
        ax = axes[col]
        ref_muls = get_ref_muls_servers(w, t)
        for srv, meta in SERVERS:
            muls, tps = load_summary(srv, w, t)
            if not muls:
                continue
            xs = to_index(muls, ref_muls)
            ax.plot(xs, tps, marker='o', markersize=4, linewidth=2,
                    color=meta['color'], linestyle=meta['ls'],
                    label=f"{meta['label']} (PAUSE={meta['pause']}cyc)")
        ax.set_title(f't = {t} threads', fontsize=11)
        ax.set_xlabel('spin_wait_pause_multiplier')
        ax.set_ylabel('Throughput (Mops/s)')
        ax.legend(fontsize=7, loc='upper left')
        ax.grid(True, alpha=0.3)
        set_xticks(ax, ref_muls)
    plt.tight_layout()
    out = f'{BASE}/graph_A_throughput_by_t.png'
    plt.savefig(out, dpi=150, bbox_inches='tight')
    print(f'saved: {out}')
    plt.close()

# ---- Graph B: throughput vs m, all w values, per server ----

def plot_graph_B(t=8):
    active = [(srv, meta) for srv, meta in SERVERS
              if any(load_summary(srv, w, t)[0] for w in ALL_W)]
    ncols = 3
    nrows = (len(active) + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(8 * ncols, 5 * nrows))
    axes_flat = axes.flatten() if nrows * ncols > 1 else [axes]
    fig.suptitle(f'Graph B: Effect of lock hold time (w) on throughput  [t={t} threads]',
                 fontsize=13, fontweight='bold')

    for i, (srv, meta) in enumerate(active):
        ax = axes_flat[i]
        ref_muls = get_ref_muls_w(srv, t)
        for j, w in enumerate(ALL_W):
            muls, tps = load_summary(srv, w, t)
            if not muls:
                continue
            xs = to_index(muls, ref_muls)
            ax.plot(xs, tps, marker='o', markersize=3, linewidth=1.8,
                    color=W_COLORS[j], label=f'w={w}ns')
        ax.set_title(f"{meta['label']} (PAUSE={meta['pause']}cyc)", fontsize=10)
        ax.set_xlabel('spin_wait_pause_multiplier')
        ax.set_ylabel('Throughput (Mops/s)')
        ax.legend(fontsize=7, loc='upper left')
        ax.grid(True, alpha=0.3)
        set_xticks(ax, ref_muls)

    for i in range(len(active), len(axes_flat)):
        axes_flat[i].set_visible(False)

    plt.tight_layout()
    out = f'{BASE}/graph_B_throughput_by_w.png'
    plt.savefig(out, dpi=150, bbox_inches='tight')
    print(f'saved: {out}')
    plt.close()

# ---- Graph C: effective PAUSE cycles normalization ----

def plot_graph_C():
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle('Graph C: Throughput vs Effective PAUSE cycles per spin\n'
                 'x = 2.5 × m × PAUSE_cyc  (normalizes backoff across architectures)',
                 fontsize=12, fontweight='bold')
    for ax, (w, t) in zip(axes, [(0, 8), (0, 16)]):
        for srv, meta in SERVERS:
            muls, tps = load_summary(srv, w, t)
            if not muls:
                continue
            eff = [2.5 * m * meta['pause'] for m in muls]
            ax.plot(eff, tps, marker='o', markersize=4, linewidth=2,
                    color=meta['color'], linestyle=meta['ls'],
                    label=f"{meta['label']} (PAUSE={meta['pause']}cyc)")
        ax.set_title(f'w={w}ns, t={t}')
        ax.set_xlabel('Effective PAUSE cycles per spin (2.5 × m × PAUSE_cyc)')
        ax.set_ylabel('Throughput (Mops/s)')
        ax.legend(fontsize=7)
        ax.grid(True, alpha=0.3)
        ax.set_xscale('symlog', linthresh=1)
    plt.tight_layout()
    out = f'{BASE}/graph_C_effective_cycles.png'
    plt.savefig(out, dpi=150, bbox_inches='tight')
    print(f'saved: {out}')
    plt.close()

# ---- Graph D: counter rates (yield / sleep / ut_delay) ----

def plot_graph_D(t=8):
    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    fig.suptitle(f'Graph D: Counter rates vs multiplier  [t={t}, w=0ns vs w=500ns]',
                 fontsize=13, fontweight='bold')
    metrics = [
        ('ut_delay', 'ut_delay calls/s (M)'),
        ('yield',    'sched_yield calls/s'),
        ('sleep',    'cond_wait calls/s'),
    ]
    for col, (key, ylabel) in enumerate(metrics):
        for row, w in enumerate([0, 500]):
            ax = axes[row][col]
            ref_muls = get_ref_muls_servers(w, t)
            for srv, meta in SERVERS:
                d = load_counters(srv, w, t)
                if not d['m']:
                    continue
                xs = to_index(d['m'], ref_muls)
                ax.plot(xs, d[key], marker='o', markersize=4, linewidth=2,
                        color=meta['color'], linestyle=meta['ls'],
                        label=f"{meta['label']} (PAUSE={meta['pause']}cyc)")
            ax.set_title(f'w={w}ns: {ylabel}')
            ax.set_xlabel('spin_wait_pause_multiplier')
            ax.set_ylabel(ylabel)
            ax.legend(fontsize=6)
            ax.grid(True, alpha=0.3)
            set_xticks(ax, ref_muls)
    plt.tight_layout()
    out = f'{BASE}/graph_D_counters.png'
    plt.savefig(out, dpi=150, bbox_inches='tight')
    print(f'saved: {out}')
    plt.close()

# ---- Graph E: optimal m (95% throughput threshold) vs PAUSE cycles ----

def find_optimal_m_95(srv, w, t):
    muls, tps = load_summary(srv, w, t)
    if not muls:
        return None
    max_tp = max(tps)
    for m, tp in zip(muls, tps):
        if tp >= 0.95 * max_tp:
            return m
    return muls[-1]

def plot_graph_E(threads=(8, 16, 32), w=0):
    markers = ['o', 's', '^', 'D']
    fig, ax = plt.subplots(figsize=(10, 6))
    fig.suptitle(f'Graph E: Optimal multiplier vs PAUSE cycles  [w={w}ns]\n'
                 'Optimal m = smallest m where throughput ≥ 95% of max',
                 fontsize=12, fontweight='bold')

    for ti, t in enumerate(threads):
        for srv, meta in SERVERS:
            m_opt = find_optimal_m_95(srv, w, t)
            if m_opt is None:
                continue
            ax.scatter(meta['pause'], m_opt,
                       color=meta['color'], marker=markers[ti],
                       s=120, zorder=5, edgecolors='black', linewidths=0.5)

    from matplotlib.lines import Line2D
    server_handles = [
        Line2D([0], [0], color=meta['color'], marker='o', linewidth=0, markersize=9,
               label=meta['label'])
        for _, meta in SERVERS
    ]
    thread_handles = [
        Line2D([0], [0], color='gray', marker=mk, linewidth=0, markersize=9,
               label=f't={t}')
        for mk, t in zip(markers, threads)
    ]
    leg1 = ax.legend(handles=server_handles, fontsize=8, loc='upper right', title='Architecture')
    ax.add_artist(leg1)
    ax.legend(handles=thread_handles, fontsize=8, loc='upper left', title='Threads')

    ax.set_xlabel('PAUSE cycles per instruction (architecture-specific)', fontsize=11)
    ax.set_ylabel('Optimal spin_wait_pause_multiplier (95% threshold)', fontsize=11)
    ax.set_yscale('log')
    ax.set_xscale('log')
    ax.grid(True, alpha=0.3, which='both')
    plt.tight_layout()
    out = f'{BASE}/graph_E_optimal_m_scatter.png'
    plt.savefig(out, dpi=150, bbox_inches='tight')
    print(f'saved: {out}')
    plt.close()

# ---- Graph F: per-server throughput, w as legend ----

def plot_graph_F(threads=(8, 16, 32)):
    os.makedirs(f'{BASE}/per_server', exist_ok=True)
    for srv, meta in SERVERS:
        has_data = any(load_summary(srv, w, threads[0])[0] for w in ALL_W)
        if not has_data:
            print(f'skip: {srv} (no data)')
            continue
        fig, axes = plt.subplots(1, len(threads), figsize=(7 * len(threads), 5), sharey=False)
        fig.suptitle(f"{meta['label']}  (PAUSE = {meta['pause']} cyc/instr)\n"
                     f"Throughput vs spin_wait_pause_multiplier — legend: w (lock hold time)",
                     fontsize=13, fontweight='bold')
        for col, t in enumerate(threads):
            ax = axes[col]
            ref_muls = get_ref_muls_w(srv, t)
            if not ref_muls:
                ax.set_visible(False)
                continue
            for j, w in enumerate(ALL_W):
                muls, tps = load_summary(srv, w, t)
                if not muls:
                    continue
                xs = to_index(muls, ref_muls)
                ax.plot(xs, tps, marker='o', markersize=4, linewidth=2,
                        color=W_COLORS[j], label=f'w={w}ns')
            ax.set_title(f't = {t} threads', fontsize=11)
            ax.set_xlabel('spin_wait_pause_multiplier')
            ax.set_ylabel('Throughput (Mops/s)')
            ax.legend(fontsize=8, loc='upper left')
            ax.grid(True, alpha=0.3)
            set_xticks(ax, ref_muls)
        plt.tight_layout()
        out = f'{BASE}/per_server/{srv}_throughput_by_w.png'
        plt.savefig(out, dpi=150, bbox_inches='tight')
        print(f'saved: {out}')
        plt.close()

# ---- Graph F2: per-server throughput, w grouped by CS length, 3 rows x 3 cols ----

W_GROUPS = [
    ('w=0  (CS ~ 0ns)',              [0]),
    ('w=100,200  (CS short)',         [100, 200]),
    ('w=500,1000  (CS medium)',       [500, 1000]),
    ('w=2000,5000  (CS very long)',   [2000, 5000]),
]

def plot_graph_F2(threads=(8, 16, 32)):
    os.makedirs(f'{BASE}/per_server', exist_ok=True)
    for srv, meta in SERVERS:
        has_data = any(load_summary(srv, w, threads[0])[0] for w in ALL_W)
        if not has_data:
            print(f'skip: {srv} (no data)')
            continue

        fig, axes = plt.subplots(len(W_GROUPS), len(threads),
                                 figsize=(7 * len(threads), 5 * len(W_GROUPS)),
                                 sharey='row')
        fig.suptitle(f"{meta['label']}  (PAUSE = {meta['pause']} cyc/instr)\n"
                     f"Throughput vs spin_wait_pause_multiplier  —  legend: w (lock hold time ns)",
                     fontsize=13, fontweight='bold')

        for row, (group_label, w_list) in enumerate(W_GROUPS):
            for col, t in enumerate(threads):
                ax = axes[row][col]
                ref_muls = get_ref_muls_w(srv, t)
                for w in w_list:
                    muls, tps = load_summary(srv, w, t)
                    if not muls:
                        continue
                    j = ALL_W.index(w)
                    xs = to_index(muls, ref_muls)
                    ax.plot(xs, tps, marker='o', markersize=4, linewidth=2,
                            color=W_COLORS[j], label=f'w={w}ns')
                if col == 0:
                    ax.set_ylabel(f'{group_label}\nThroughput (Mops/s)', fontsize=9)
                ax.set_title(f't = {t} threads', fontsize=10)
                ax.set_xlabel('spin_wait_pause_multiplier')
                ax.legend(fontsize=8, loc='lower right')
                ax.grid(True, alpha=0.3)
                set_xticks(ax, ref_muls)

        plt.tight_layout()
        out = f'{BASE}/per_server/{srv}_throughput_grouped.png'
        plt.savefig(out, dpi=150, bbox_inches='tight')
        print(f'saved: {out}')
        plt.close()

# ---- Graph G: per-server throughput + ut_delay + yield + sleep, all t, shared y-axis ----

PANELS = [
    ('throughput', 'Throughput (Mops/s)'),
    ('ut_delay',   'ut_delay calls/s (M)'),
    ('yield',      'sched_yield calls/s'),
    ('sleep',      'cond_wait calls/s'),
]

def _collect_vals(srv, w, t, key):
    if key == 'throughput':
        _, vals = load_summary(srv, w, t)
    else:
        vals = load_counters(srv, w, t)[key]
    return vals

def plot_graph_G(threads=(8, 16, 32)):
    """all w values on a single row of 4 panels; y-axis per subplot."""
    os.makedirs(f'{BASE}/per_server', exist_ok=True)
    for srv, meta in SERVERS:
        has_any = any(load_summary(srv, w, threads[0])[0] for w in ALL_W)
        if not has_any:
            print(f'skip: {srv} (no data)')
            continue

        for t in threads:
            has_data = any(load_summary(srv, w, t)[0] for w in ALL_W)
            if not has_data:
                continue

            ref_muls = get_ref_muls_w(srv, t)
            fig, axes = plt.subplots(1, len(PANELS), figsize=(7 * len(PANELS), 5))
            fig.suptitle(
                f"{meta['label']}  (PAUSE = {meta['pause']} cyc/instr, t = {t} threads)\n"
                f"legend: w (lock hold time ns)",
                fontsize=13, fontweight='bold')

            for col, (key, ylabel) in enumerate(PANELS):
                ax = axes[col]
                cell_max = 0.0
                for j, w in enumerate(ALL_W):
                    muls = load_summary(srv, w, t)[0] if key == 'throughput' \
                           else load_counters(srv, w, t)['m']
                    vals = _collect_vals(srv, w, t, key)
                    if not muls:
                        continue
                    xs = to_index(muls, ref_muls)
                    ax.plot(xs, vals, marker='o', markersize=4, linewidth=2,
                            color=W_COLORS[j], label=f'w={w}ns')
                    if vals:
                        cell_max = max(cell_max, max(vals))
                ax.set_title(ylabel, fontsize=11)
                ax.set_xlabel('spin_wait_pause_multiplier')
                ax.set_ylabel(ylabel)
                ax.set_ylim(0, cell_max * 1.1 if cell_max > 0 else 1)
                ax.legend(fontsize=8, loc='upper right')
                ax.grid(True, alpha=0.3)
                set_xticks(ax, ref_muls)

            plt.tight_layout()
            out = f'{BASE}/per_server/{srv}_t{t}_all_metrics.png'
            plt.savefig(out, dpi=150, bbox_inches='tight')
            print(f'saved: {out}')
            plt.close()

    _save_script(f'{BASE}/per_server', 'plot_graph_G', f'threads={threads}')


def plot_graph_G_grouped(threads=(8, 16, 32)):
    """4 w-groups x 4 metrics; y-axis per cell."""
    os.makedirs(f'{BASE}/per_server', exist_ok=True)
    for srv, meta in SERVERS:
        has_any = any(load_summary(srv, w, threads[0])[0] for w in ALL_W)
        if not has_any:
            print(f'skip: {srv} (no data)')
            continue

        for t in threads:
            has_data = any(load_summary(srv, w, t)[0] for w in ALL_W)
            if not has_data:
                continue

            ref_muls = get_ref_muls_w(srv, t)
            nrows, ncols = len(W_GROUPS), len(PANELS)
            fig, axes = plt.subplots(nrows, ncols, figsize=(7 * ncols, 5 * nrows))
            fig.suptitle(
                f"{meta['label']}  (PAUSE = {meta['pause']} cyc/instr, t = {t} threads)\n"
                f"legend: w (lock hold time ns)",
                fontsize=13, fontweight='bold')

            for row, (group_label, w_list) in enumerate(W_GROUPS):
                for col, (key, ylabel) in enumerate(PANELS):
                    ax = axes[row][col]
                    cell_max = 0.0
                    for w in w_list:
                        muls = load_summary(srv, w, t)[0] if key == 'throughput' \
                               else load_counters(srv, w, t)['m']
                        vals = _collect_vals(srv, w, t, key)
                        if not muls:
                            continue
                        j = ALL_W.index(w)
                        xs = to_index(muls, ref_muls)
                        ax.plot(xs, vals, marker='o', markersize=4, linewidth=2,
                                color=W_COLORS[j], label=f'w={w}ns')
                        if vals:
                            cell_max = max(cell_max, max(vals))
                    if row == 0:
                        ax.set_title(ylabel, fontsize=11)
                    if col == 0:
                        ax.set_ylabel(f'{group_label}\n{ylabel}', fontsize=9)
                    ax.set_xlabel('spin_wait_pause_multiplier')
                    ax.set_ylim(0, cell_max * 1.1 if cell_max > 0 else 1)
                    ax.legend(fontsize=8, loc='upper right')
                    ax.grid(True, alpha=0.3)
                    set_xticks(ax, ref_muls)

            plt.tight_layout()
            out = f'{BASE}/per_server/{srv}_t{t}_all_metrics_grouped.png'
            plt.savefig(out, dpi=150, bbox_inches='tight')
            print(f'saved: {out}')
            plt.close()

    _save_script(f'{BASE}/per_server', 'plot_graph_G_grouped', f'threads={threads}')

# ---- legacy graphs (kept for comparison) ----

def _summary_path_legacy(srv, w, t, use_old=False):
    if use_old:
        return f'{BASE}/{srv}/2026_5_28/w{w}/summary_t{t}.md'
    direct = f'{BASE}/{srv}/w{w}/summary_t{t}.md'
    if os.path.exists(direct):
        return direct
    return f'{BASE}/{srv}/2026_5_28/w{w}/summary_t{t}.md'

SERVERS_LEGACY = [
    ('ivy_c8220',       {'pause': 14.56,  'label': 'Ivy Bridge (c8220)',       'color': '#4CAF50', 'ls': '-'}),
    ('broadwell_xl170', {'pause': 12.34,  'label': 'Broadwell (xl170)',        'color': '#2196F3', 'ls': '-'}),
    ('skylake_c220g5',  {'pause': 141.97, 'label': 'Skylake HTT-on (c220g5)', 'color': '#FF5722', 'ls': '-'}),
    ('skylake_ann',     {'pause': 142.31, 'label': 'Skylake HTT-off (ann)',   'color': '#FF9800', 'ls': '--'}),
    ('emerald_c6620',   {'pause': 37.15,  'label': 'Emerald Rapids (c6620)',  'color': '#FF0000', 'ls': '-'}),
]

def _load_legacy(srv, w, t, use_old=False):
    path = _summary_path_legacy(srv, w, t, use_old)
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

def _get_ref_muls_legacy(w, t, use_old=False):
    all_muls = set()
    for srv, _ in SERVERS_LEGACY:
        muls, _ = _load_legacy(srv, w, t, use_old)
        all_muls.update(muls)
    return sorted(all_muls)

def plot_comparison_all(threads=(4, 8, 16, 32), use_old=False, suffix=''):
    fig, axes = plt.subplots(2, len(threads), figsize=(7 * len(threads), 10))
    tag = '(old: atomic counter)' if use_old else '(new: local counter)'
    fig.suptitle(f'Throughput vs spin_wait_pause_multiplier\n{tag}',
                 fontsize=14, fontweight='bold')
    for row, w in enumerate([0, 500]):
        for col, t in enumerate(threads):
            ax = axes[row][col]
            ref_muls = _get_ref_muls_legacy(w, t, use_old)
            for srv, meta in SERVERS_LEGACY:
                muls, tps = _load_legacy(srv, w, t, use_old)
                if not muls:
                    continue
                xs = to_index(muls, ref_muls)
                ax.plot(xs, tps, marker='o', markersize=5, linewidth=2,
                        color=meta['color'], linestyle=meta['ls'],
                        label=f"{meta['label']} (PAUSE={meta['pause']}cyc)")
            ax.set_title(f'w={w}ns, t={t}', fontsize=11)
            ax.set_xlabel('spin_wait_pause_multiplier')
            ax.set_ylabel('Throughput (Mops/s)')
            ax.legend(fontsize=7, loc='lower right')
            ax.grid(True, alpha=0.3)
            set_xticks(ax, ref_muls)
    plt.tight_layout()
    out = f'{BASE}/comparison_all{suffix}.png'
    plt.savefig(out, dpi=150, bbox_inches='tight')
    print(f'saved: {out}')
    plt.close()

def plot_effective_cycles(use_old=False, suffix=''):
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    tag = '(old: atomic counter)' if use_old else '(new: local counter)'
    fig.suptitle(f'Throughput vs Effective PAUSE cycles per spin  {tag}',
                 fontsize=13, fontweight='bold')
    for ax, (w, t) in zip(axes, [(0, 8), (0, 16)]):
        for srv, meta in SERVERS_LEGACY:
            muls, tps = _load_legacy(srv, w, t, use_old)
            if not muls:
                continue
            eff = [2.5 * m * meta['pause'] for m in muls]
            ax.plot(eff, tps, marker='o', markersize=5, linewidth=2,
                    color=meta['color'], linestyle=meta['ls'],
                    label=f"{meta['label']} (PAUSE={meta['pause']}cyc)")
        ax.set_title(f'w={w}ns, t={t}')
        ax.set_xlabel('Effective PAUSE cycles per spin (2.5 × m × PAUSE_cycles)')
        ax.set_ylabel('Throughput (Mops/s)')
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
        ax.set_xscale('symlog', linthresh=1)
    plt.tight_layout()
    out = f'{BASE}/effective_cycles{suffix}.png'
    plt.savefig(out, dpi=150, bbox_inches='tight')
    print(f'saved: {out}')
    plt.close()


def _save_script(outdir, func_name, call_args):
    """Save a reproduce script to outdir/generate.py."""
    os.makedirs(outdir, exist_ok=True)
    rel = os.path.relpath(BASE, outdir)
    content = f"""#!/usr/bin/env python3
# Usage:
#   cd /home/morisaki/simple_mysql
#   python3 {outdir}/generate.py
#
# Description:
#   このディレクトリのグラフを再生成するスクリプト。
#   plot_graphs.py が存在するプロジェクトルートから実行すること。
#
# Prerequisites:
#   pip install matplotlib numpy

import sys, os
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '{rel}')))
import plot_graphs

plot_graphs.{func_name}({call_args})
"""
    path = os.path.join(outdir, 'generate.py')
    with open(path, 'w') as f:
        f.write(content)
    print(f'saved: {path}')


def plot_cross_server(threads=(8, 16, 32), w_list=(0, 100, 500, 2000), normalize=False):
    """One file per t: rows=w values, cols=metrics, lines=servers.
    normalize=True: divide each server's values by its own m=0 baseline."""
    os.makedirs(f'{BASE}/per_server', exist_ok=True)
    suffix = '_normalized' if normalize else ''
    for t in threads:
        nrows, ncols = len(w_list), len(PANELS)
        fig, axes = plt.subplots(nrows, ncols, figsize=(7 * ncols, 5 * nrows))
        norm_tag = '  [normalized to m=0]' if normalize else ''
        fig.suptitle(
            f'Cross-server comparison  (t = {t} threads){norm_tag}\n'
            f'legend: server  |  x-axis: spin_wait_pause_multiplier',
            fontsize=13, fontweight='bold')

        for row, w in enumerate(w_list):
            ref_muls = get_ref_muls_servers(w, t)
            for col, (key, ylabel) in enumerate(PANELS):
                ax = axes[row][col]
                cell_min = float('inf')
                cell_max = 0.0
                for srv, meta in SERVERS:
                    if key == 'throughput':
                        muls, vals = load_summary(srv, w, t)
                    else:
                        cnt = load_counters(srv, w, t)
                        muls, vals = cnt['m'], cnt[key]
                    if not muls:
                        continue
                    if normalize:
                        if 0 in muls:
                            base = vals[muls.index(0)]
                        else:
                            base = None
                        if base and base != 0:
                            vals = [v / base for v in vals]
                        else:
                            continue
                    xs = to_index(muls, ref_muls)
                    ax.plot(xs, vals, marker='o', markersize=4, linewidth=2,
                            color=meta['color'], linestyle=meta['ls'],
                            label=meta['label'])
                    if vals:
                        cell_min = min(cell_min, min(vals))
                        cell_max = max(cell_max, max(vals))
                if row == 0:
                    ax.set_title(ylabel, fontsize=11)
                ylabel_label = 'ratio to m=0' if normalize else ylabel
                if col == 0:
                    ax.set_ylabel(f'w={w}ns\n{ylabel_label}', fontsize=9)
                if normalize:
                    ax.axhline(y=1.0, color='gray', linestyle='--', linewidth=1, alpha=0.5)
                ax.set_xlabel('spin_wait_pause_multiplier')
                if cell_max > 0 and cell_min != float('inf'):
                    margin = (cell_max - cell_min) * 0.1 or cell_max * 0.1
                    ylo = (cell_min - margin) if normalize else max(0, cell_min - margin)
                    ax.set_ylim(ylo, cell_max + margin)
                else:
                    ax.set_ylim(0, 1)
                ax.legend(fontsize=7, loc='upper right')
                ax.grid(True, alpha=0.3)
                set_xticks(ax, ref_muls)

        plt.tight_layout()
        out = f'{BASE}/per_server/cross_server_t{t}{suffix}.png'
        plt.savefig(out, dpi=150, bbox_inches='tight')
        print(f'saved: {out}')
        plt.close()

    _save_script(f'{BASE}/per_server',
                 'plot_cross_server',
                 f'threads={threads}, w_list={w_list}, normalize={normalize}')


if __name__ == '__main__':
    print('=== Generating Graphs A-E ===')
    plot_graph_A(threads=(8, 16, 32))
    plot_graph_B(t=8)
    plot_graph_C()
    plot_graph_D(t=8)
    plot_graph_E(threads=(8, 16, 32), w=0)

    print('\n=== Generating legacy comparison graphs ===')
    plot_comparison_all(threads=(4, 8, 16, 32), use_old=False, suffix='')
    plot_comparison_all(threads=(4, 8), use_old=True, suffix='_old')
    plot_effective_cycles(use_old=False, suffix='')
    plot_effective_cycles(use_old=True, suffix='_old')

    print('\nAll graphs generated.')
