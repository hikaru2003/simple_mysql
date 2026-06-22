#!/usr/bin/env python3
# Usage:
#   cd /home/morisaki/simple_mysql
#   python3 /home/morisaki/simple_mysql/result/per_server/generate.py
#
# Description:
#   このディレクトリのグラフを再生成するスクリプト。
#   plot_graphs.py が存在するプロジェクトルートから実行すること。
#
# Prerequisites:
#   pip install matplotlib numpy

import sys, os
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')))
import plot_graphs

plot_graphs.plot_cross_server(threads=(8, 16, 32), w_list=(0, 100, 500, 2000), normalize=True)
