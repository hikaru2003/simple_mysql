# 実験記録 2026-04-23

## 実装の特徴

- **カウンタ実装**: グローバルアトミック変数（`atomic_long`）で yield / sleep / ut_delay / latency を集計
  - カウンタ更新のたびに atomic 命令が発行される → カウンタ操作自体がオーバーヘッドになる
- **レイテンシ計測あり**: ロック取得〜解放の TSC を記録し Average Latency を算出
- **fake work あり**: `dummy_buffer` への random アクセスでキャッシュミスを意図的に誘発

## 実験パラメータ

| パラメータ | 値 |
|-----------|---|
| スレッド数 | 8 (固定) |
| multiplier (m) | 限定範囲（初期調査） |
| work duration (w) | 不明（初期設定） |
| repeat | 複数回 |

## 対象サーバ

broadwell_xl170、skylake_ann、emerald_c6620（限定的）

## グラフ一覧

| ファイル | 内容 |
|---------|------|
| plot_Throughput.png | サーバ比較スループット |
| plot_Average_Latency_tsc.png | ロック平均レイテンシ（TSCサイクル） |
| plot_Global_ut_delay_count.png | ut_delay 呼び出し回数 |
| plot_Global_yield_count.png | sched_yield 呼び出し回数 |
| plot_Global_sleep_count.png | cond_wait 呼び出し回数 |

## 備考

最初期の探索的実験。グローバルアトミックカウンタのオーバーヘッドと latency 計測コードが性能に影響している可能性がある。
