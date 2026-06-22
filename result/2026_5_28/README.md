# 実験記録 2026-05-28

## 実装の特徴

- **カウンタ実装**: グローバルアトミック変数（`atomic_long`）で yield / sleep / ut_delay を集計
  - カウンタ更新のたびに `atomic_fetch_add` が発行される → 高スレッド数時にカウンタ自体が競合ポイントになる
  - この影響でスループット計測値が実際より低めに出る可能性がある
- **デッドロックバグあり（未修正）**: stop_flag を set してから broadcast を送るまでの間に、
  スレッドが yield 後に spin に戻り 30 ラウンドを使い切って cond_wait に入ると、
  すでに broadcast が終わった後のため永久に起きられなくなる hang が発生する場合がある
- **latency 計測**: なし（コメントアウト済み）
- **fake work**: なし

## 実験パラメータ

| パラメータ | 値 |
|-----------|---|
| スレッド数 | 1, 4, 8 |
| multiplier (m) | 0, 10, 20, ..., 100（10刻み） |
| work duration (w) | 0 ns, 500 ns |
| repeat | 3回 |
| 計測時間 | 30秒/run |
| CPU固定 | taskset -c 0-7 |

## 対象サーバ

ivy_c8220、broadwell_xl170、skylake_c220g5、skylake_ann、emerald_c6620
（icelake_sm110 は未実施）

## グラフ一覧

このディレクトリには **2種類の実装** で生成されたグラフが混在している。

### `_old` ファイル（グローバルアトミックカウンタ実装）
5/28 実験データをアトミックカウンタ実装のままプロットしたもの。

| ファイル | 内容 |
|---------|------|
| comparison_all_old.png | 全サーバ比較スループット（t=4,8 × w=0,500） |
| counters_t4_w0_w500_old.png | t=4 の yield/sleep/ut_delay カウンタ |
| counters_t8_w0_w500_old.png | t=8 の yield/sleep/ut_delay カウンタ |
| effective_cycles_old.png | PAUSE effective cycles 正規化 |

### `_old` なしファイル（ローカルスレッドカウンタ実装）
同じ5/28実験データを、ローカルカウンタ実装（2026_6_3 と同じコード）で再プロットしたもの。
カウンタのアトミックオーバーヘッドがないため、`_old` ファイルより正確な値になっている。

| ファイル | 内容 |
|---------|------|
| counters_t1_w0_w500.png | t=1 の yield/sleep/ut_delay カウンタ |
| counters_t4_w0_w500.png | t=4 の yield/sleep/ut_delay カウンタ |
| counters_t8_w0_w500.png | t=8 の yield/sleep/ut_delay カウンタ |
| counters_t16_w0_w500.png | t=16（5/28 はデータなし → 空白） |
| counters_t32_w0_w500.png | t=32（5/28 はデータなし → 空白） |

## 備考

デッドロックバグの影響で、後続の実験（2026_6_3）と直接比較する際は注意が必要。
multiplier の範囲が 0〜100 と狭く、最適値の探索には不十分だった。
同一実験データに対して2種類の実装でプロットした結果が混在しているため、
比較する際は `_old` の有無でフィルタすること。
