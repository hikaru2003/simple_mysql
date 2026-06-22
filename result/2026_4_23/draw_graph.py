# Usage:
#   python3 draw_graph.py <file1> [file2 ...] <output_basename>
#
# Description:
#   2026-04-23 実験データを正規化して棒グラフに描画するスクリプト。
#   Multiplier=50 を基準(1.0)として各メトリクスを正規化表示する。
#
# Parameters:
#   file1...fileN  : 実験結果テキストファイル（result/{condition}/t{n}_m{m}.txt）
#   output_basename: 出力ファイルのベース名（.png が付加される）
#
# Output:
#   {output_basename}.png  : 正規化棒グラフ（上下分割スタイル）
#
# Prerequisites:
#   pip install pandas matplotlib

import sys
import re
import pandas as pd
import matplotlib.pyplot as plt

def parse_experiment_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

            data = {}
            m_mult = re.search(r'Multiplier=(\d+)', content)
            if m_mult:
                data['Multiplier'] = int(m_mult.group(1))
            else:
                return None

            patterns = {
                'Throughput': r'Throughput:\s*([\d\.]+)',
                'Global ut_delay count': r'Global ut_delay count:\s*(\d+)',
                'Global yield count': r'Global yield count:\s*(\d+)',
                'Global sleep count': r'Global sleep count:\s*(\d+)',
                'Average Latency': r'Average Latency\[tsc\]:\s*(\d+)'
            }

            for key, pattern in patterns.items():
                match = re.search(pattern, content)
                if match:
                    val = match.group(1)
                    data[key] = float(val) if '.' in val else int(val)

            return data
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return None

def main():
    if len(sys.argv) < 2:
        print("Usage: python script.py <file1> <file2> ... <output_filename>")
        return

    output_filename = sys.argv[-1]+'.png'
    file_paths = sys.argv[1:-1]
    all_results = []
    for path in file_paths:
        parsed_data = parse_experiment_file(path)
        if parsed_data:
            all_results.append(parsed_data)

    if not all_results:
        print("有効なデータが見つかりませんでした。")
        return

    df = pd.DataFrame(all_results).sort_values('Multiplier')

    baseline_val = 50
    if baseline_val not in df['Multiplier'].values:
        print(f"エラー: Multiplier={baseline_val} のデータがありません。")
        return

    baseline_row = df[df['Multiplier'] == baseline_val].iloc[0]
    metrics = ['Throughput', 'Global ut_delay count', 'Global yield count', 'Global sleep count', 'Average Latency']

    df_norm = df.copy()
    for col in metrics:
        if baseline_row[col] != 0:
            df_norm[col] = df[col] / baseline_row[col]
        else:
            df_norm[col] = 0.0

    plot_df = df_norm.set_index('Multiplier')[metrics].T

    fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True, figsize=(12, 8), gridspec_kw={'height_ratios': [1, 5]})
    fig.subplots_adjust(hspace=0.1)

    plot_df.plot(kind='bar', ax=ax1, width=0.8, edgecolor='white', legend=False)
    plot_df.plot(kind='bar', ax=ax2, width=0.8, edgecolor='white', legend=False)

    max_val = max(plot_df.max().max() * 1.1, 2, 5)
    ax1.set_ylim(2.5, max_val)
    ax2.set_ylim(0, 2.5)

    ax1.spines['bottom'].set_visible(False)
    ax2.spines['top'].set_visible(False)
    ax1.xaxis.tick_top()
    ax1.tick_params(labeltop=False)
    ax2.xaxis.tick_bottom()
    plt.xticks(rotation=0, ha='center')

    d = .015
    kwargs = dict(transform=ax1.transAxes, color='k', clip_on=False)
    ax1.plot((-d, +d), (-d, +d), **kwargs)
    ax1.plot((1 - d, 1 + d), (-d, +d), **kwargs)

    kwargs.update(transform=ax2.transAxes)
    ax2.plot((-d, +d), (1 - d, 1 + d), **kwargs)
    ax2.plot((1 - d, 1 + d), (1 - d, 1 + d), **kwargs)

    ax2.axhline(y=1.0, color='red', linestyle='--', linewidth=1.5, alpha=0.8, label=f'Baseline (M={baseline_val})')

    fig.suptitle(f'Normalized Results (Baseline: M={baseline_val})', fontsize=14)
    ax2.set_xlabel('Measurement Metrics', fontsize=12)
    ax2.set_ylabel('Relative Scale', fontsize=12)
    ax2.yaxis.set_label_coords(-0.07, 0.7)

    ax1.legend(title='Multiplier', bbox_to_anchor=(1, 1), loc='upper left')

    plt.savefig(output_filename)
    print(f"Graph saved as {output_filename}")
    plt.show()

if __name__ == "__main__":
    main()
