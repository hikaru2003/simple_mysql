# 実験記録 2026-06-03〜04

## 実装の特徴

- **カウンタ実装**: スレッドローカル構造体（`thread_stats_t`）で yield / sleep / ut_delay を集計
  - アトミック操作不要 → カウンタ自体の競合・オーバーヘッドがゼロ
  - 集計は全スレッド join 後にメインスレッドが単純加算
- **デッドロック修正済み**: pre-sleep check パターンを採用
  - `pthread_cond_wait` に入る前に、mutex 保護下で stop_flag と lock 状態を確認
  - stop_flag が true なら cond_wait をスキップして即リターン
  - メイン側も mutex 保護下で stop_flag を set してから broadcast
- **latency 計測**: なし（コメントアウト済み）
- **fake work**: なし

## 実験パラメータ

| パラメータ | 値 |
|-----------|---|
| スレッド数 | 8, 16, 32（t=1, 4 は除外） |
| multiplier (m) | 0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 150, 200, 250, 300, 400, 500, 700, 1000, 2000, 3000, 5000, 7000, 10000, 20000, 50000 |
| work duration (w) | 0, 100, 200, 500, 1000, 2000, 5000 ns |
| repeat | 3回 |
| 計測時間 | 30秒/run |
| timeout | 45秒（hang 防止） |
| CPU固定 | taskset -c 0-7 |

## 対象サーバと PAUSE サイクル数

| サーバ | アーキテクチャ | PAUSE cycles/instr |
|--------|-------------|-------------------|
| ivy_c8220 | Ivy Bridge | 14.56 |
| broadwell_xl170 | Broadwell | 12.34 |
| skylake_c220g5 | Skylake HTT-on | 141.97 |
| skylake_ann | Skylake HTT-off | 142.31 |
| icelake_sm110 | Ice Lake | 38.86 |
| emerald_c6620 | Emerald Rapids | 37.15 |

## グラフ一覧

### 全サーバ比較グラフ

| ファイル | 内容 |
|---------|------|
| graph_A_throughput_by_t.png | 全サーバ比較スループット（w=0、t=8/16/32 並列） |
| graph_B_throughput_by_w.png | 全サーバ比較（サーバ別サブプロット、全w値、t=8固定） |
| graph_C_effective_cycles.png | PAUSE effective cycles 正規化（アーキテクチャ間スケーリング検証） |
| graph_D_counters.png | yield/sleep/ut_delay カウンタ推移（w=0 vs w=500、t=8） |
| graph_E_optimal_m_scatter.png | 最適 m vs PAUSE cycles 散布図（95%スループット閾値） |
| comparison_all.png | 全サーバ比較（w=0, w=500 × t=8,16,32） |
| effective_cycles.png | PAUSE effective cycles（レガシー形式） |

### カウンタグラフ（レガシー形式）

| ファイル | 内容 |
|---------|------|
| counters_t8_w0_w500.png | t=8、w=0 vs w=500 のカウンタ推移 |
| counters_t16_w0_w500.png | t=16、w=0 vs w=500 のカウンタ推移 |
| counters_t32_w0_w500.png | t=32、w=0 vs w=500 のカウンタ推移 |
| counters_t1_w0_w500.png | t=1（データなし、空白） |
| counters_t4_w0_w500.png | t=4（データなし、空白） |

### per_server グラフ（`result/per_server/` 参照）

各サーバごとに以下を出力:
- `{server}_t{8,16,32}_all_metrics.png`: スループット / ut_delay / yield / sleep の4パネル（縦軸共通スケール）
- `{server}_throughput_by_w.png`: スループットのみ（t=8/16/32 横並び）

## 主要な発見

1. 最適 m はアーキテクチャごとに異なる（Skylake: m≈1000-2000、IceLake/Emerald: m≈3000-5000、Broadwell/Ivy: m>20000）
2. 近似式: `m_opt ≈ 200,000 / PAUSE_cycles`
3. スレッド数が増えるほど最適 m は低下
4. w が大きくなると m の効果は薄れる（w=5000ns ではほぼフラット）
5. Skylake HTT-on は HTT-off より peak throughput が低い（SMT resource 共有のコスト）
