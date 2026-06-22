# 使用スクリプト一覧（2026-06-03〜04 実験）

この実験で使用したスクリプトはプロジェクトルートに置かれています。

| スクリプト | パス | 役割 |
|-----------|------|------|
| 実験実行 | `../../exec_extended.sh` | 全パラメータ組み合わせの自動実行（SERVER引数でサーバ名指定） |
| サマリ生成 | `../../summarize.py` | rep平均を計算して `summary_t{t}.md` を出力 |
| グラフ生成 | `../../plot_graphs.py` | `summary_t{t}.md` を読んでグラフA〜G, per_server を出力 |

## 実行順序

```bash
# 1. 各サーバで実験実行（サーバごとに実施）
bash exec_extended.sh ivy_c8220

# 2. サマリ生成（ローカルで実行）
python3 summarize.py

# 3. グラフ生成（ローカルで実行）
python3 plot_graphs.py
```

## 実験パラメータ（exec_extended.sh の設定値）

| パラメータ | 値 |
|-----------|---|
| THREADS | 8, 16, 32 |
| MULTIPLIERS | 0, 10, ..., 100, 150, 200, ..., 50000 (26点) |
| WORK_DURATIONS | 0, 100, 200, 500, 1000, 2000, 5000 ns |
| REPS | 3 |
| taskset | -c 0-7 |
| timeout | 45秒/run（hang 防止） |
