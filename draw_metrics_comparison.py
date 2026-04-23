import os
import re
import argparse
import pandas as pd
import matplotlib.pyplot as plt

def parse_performance_file(filepath):
    """ファイルからメトリクスを抽出する"""
    metrics = {}
    # ファイル名からmultiplierを抽出
    match_m = re.search(r't8_m(\d+)\.txt', os.path.basename(filepath))
    if not match_m:
        return None
    metrics['multiplier'] = int(match_m.group(1))
    
    with open(filepath, 'r') as f:
        content = f.read()
        
    patterns = {
        'Throughput': r'Throughput:\s+([\d.]+)',
        'Global ut_delay count': r'Global ut_delay count:\s+(\d+)',
        'Global yield count': r'Global yield count:\s+(\d+)',
        'Global sleep count': r'Global sleep count:\s+(\d+)',
        'Average Latency[tsc]': r'Average Latency\[tsc\]:\s+(\d+)'
    }
    
    for key, pattern in patterns.items():
        match = re.search(pattern, content)
        if match:
            metrics[key] = float(match.group(1))
            
    return metrics

def main():
    target_metrics = [
        'Throughput', 
        'Global ut_delay count', 
        'Global yield count', 
        'Global sleep count', 
        'Average Latency[tsc]'
    ]

    parser = argparse.ArgumentParser(description='性能データの正規化比較グラフ生成（x軸: arch, 凡例: m*）')
    parser.add_argument('metric', choices=target_metrics, help='グラフ化する項目を選択')
    args = parser.parse_args()
    
    archs = ['ann', 'broadwell_xl170', 'emerald_c6620']
    base_dir = 'result'
    all_data = []

    for arch in archs:
        target_dir = os.path.join(base_dir, arch, 'with_fakework')
        if not os.path.exists(target_dir):
            continue
            
        arch_results = []
        baseline_val = None
        
        # まずディレクトリ内のファイルをすべて読み込む
        for filename in os.listdir(target_dir):
            if filename.startswith('t8_m') and filename.endswith('.txt'):
                file_path = os.path.join(target_dir, filename)
                data = parse_performance_file(file_path)
                if data and args.metric in data:
                    arch_results.append(data)
                    if data['multiplier'] == 50:
                        baseline_val = data[args.metric]
        
        # 正規化して保存用リストに追加
        if baseline_val and baseline_val != 0:
            for item in arch_results:
                item['arch'] = arch
                item['normalized_value'] = item[args.metric] / baseline_val
                # 凡例用に文字列化（m0, m50...）
                item['label'] = f"m{item['multiplier']}"
                all_data.append(item)

    if not all_data:
        print("Error: No data found.")
        return

    df = pd.DataFrame(all_data)

    # --- ここが修正ポイント ---
    # x軸(index)を arch、凡例(columns)を label にしてピボット
    plot_df = df.pivot(index='arch', columns='label', values='normalized_value')
    
    # Multiplierの数値順にカラム（凡例）をソート
    # "m10"などの文字列を数値に戻してソート順を決定
    sorted_columns = sorted(plot_df.columns, key=lambda x: int(x[1:]))
    plot_df = plot_df[sorted_columns]

    # グラフ描画
    ax = plot_df.plot(kind='bar', figsize=(10, 6), width=0.8)
    
    ax.set_title(f'Comparison of {args.metric} (Normalized to m50)', fontsize=13)
    ax.set_xlabel('Architecture', fontsize=12)
    ax.set_ylabel('Relative Value (m50 = 1.0)', fontsize=12)
    
    # 基準線 (1.0)
    ax.axhline(y=1.0, color='black', linestyle='-', linewidth=0.8, alpha=0.5)
    
    plt.xticks(rotation=0) # アーキテクチャ名を水平に表示
    plt.legend(title='Multiplier', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.grid(axis='y', linestyle=':', alpha=0.6)
    
    safe_metric_name = args.metric.replace('[', '_').replace(']', '').replace(' ', '_')
    output_path = f"plot_{safe_metric_name}.png"
    plt.tight_layout()
    plt.savefig(output_path)
    print(f"Success: Graph saved as {output_path}")

if __name__ == "__main__":
    main()