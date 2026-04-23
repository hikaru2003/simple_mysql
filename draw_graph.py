import sys
import re
import pandas as pd
import matplotlib.pyplot as plt

def parse_experiment_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
            data = {}
            # Multiplierの抽出
            m_mult = re.search(r'Multiplier=(\d+)', content)
            if m_mult:
                data['Multiplier'] = int(m_mult.group(1))
            else:
                return None
            
            # 各数値項目の抽出
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

    # 1. DataFrameの作成とソート
    df = pd.DataFrame(all_results).sort_values('Multiplier')
    
    # 2. Multiplier=50 を基準とした正規化
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

    # 3. グラフ用にデータの形を変形 (ここがポイント)
    # Multiplierを列名にし、計測項目（metrics）を行（X軸）にするために転置(T)を行う
    # IndexをMultiplierにしてからmetrics列のみを抽出し、転置する
    plot_df = df_norm.set_index('Multiplier')[metrics].T

    # 4. グラフ作成 (上下に分割)
    # sharex=True でX軸のラベルを共通化
    fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True, figsize=(12, 8), gridspec_kw={'height_ratios': [1, 5]})
    fig.subplots_adjust(hspace=0.1)  # 上下の隙間を詰める

    # 両方のaxで棒グラフを描画
    plot_df.plot(kind='bar', ax=ax1, width=0.8, edgecolor='white', legend=False)
    plot_df.plot(kind='bar', ax=ax2, width=0.8, edgecolor='white', legend=False)

    # --- 表示範囲の設定 ---
    # 上側のグラフ (ax1): 4以上の大きな値を見せる範囲 (例: 4〜20)
    # データに合わせて最大値を調整してください
    max_val = max(plot_df.max().max() * 1.1, 2,5)
    ax1.set_ylim(2.5, max_val)

    # 下側のグラフ (ax2): 0〜4を大きく見せる範囲
    ax2.set_ylim(0, 2.5)

    # --- 省略記号と枠線の設定 ---
    # 上側のグラフの下枠線と、下側のグラフの上枠線を消す
    ax1.spines['bottom'].set_visible(False)
    ax2.spines['top'].set_visible(False)
    ax1.xaxis.tick_top()
    ax1.tick_params(labeltop=False)  # 上側にラベルは出さない
    ax2.xaxis.tick_bottom()
    plt.xticks(rotation=0, ha='center')

    # 省略記号 (波線/斜線) の描画
    d = .015  # 斜線のサイズ
    kwargs = dict(transform=ax1.transAxes, color='k', clip_on=False)
    ax1.plot((-d, +d), (-d, +d), **kwargs)        # 左上の斜線
    ax1.plot((1 - d, 1 + d), (-d, +d), **kwargs)  # 右上の斜線

    kwargs.update(transform=ax2.transAxes)
    ax2.plot((-d, +d), (1 - d, 1 + d), **kwargs)  # 左下の斜線
    ax2.plot((1 - d, 1 + d), (1 - d, 1 + d), **kwargs) # 右下の斜線

    # 基準線 (y=1.0) は下側のグラフに引く
    ax2.axhline(y=1.0, color='red', linestyle='--', linewidth=1.5, alpha=0.8, label=f'Baseline (M={baseline_val})')

    # ラベルとタイトル
    fig.suptitle(f'Normalized Results (Baseline: M={baseline_val})', fontsize=14)
    ax2.set_xlabel('Measurement Metrics', fontsize=12)
    ax2.set_ylabel('Relative Scale', fontsize=12)
    ax2.yaxis.set_label_coords(-0.07, 0.7) # Y軸ラベルの位置を中央に寄せる

    # 凡例を配置
    ax1.legend(title='Multiplier', bbox_to_anchor=(1, 1), loc='upper left')

    plt.savefig(output_filename)
    print(f"Graph saved as {output_filename}")
    plt.show()

if __name__ == "__main__":
    main()