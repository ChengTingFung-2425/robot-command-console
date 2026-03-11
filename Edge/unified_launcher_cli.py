#!/usr/bin/env python3
"""
統一啟動器 CLI 入口點
一鍵啟動所有服務與健康檢查

使用方式：
    python unified_launcher_cli.py             # 啟動所有服務
    python unified_launcher_cli.py --help      # 顯示幫助
"""

import os
import sys

# 添加專案與啟動器目錄到路徑（必須在導入 robot_service 前執行）
project_root = os.path.dirname(os.path.dirname(__file__))
launcher_dir = os.path.dirname(__file__)
for path in [project_root, launcher_dir]:
    if path not in sys.path:
        sys.path.insert(0, path)

from robot_service.unified_launcher import main  # noqa: E402


if __name__ == '__main__':
    main()
