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

# 添加 src 到路徑（必須在導入 robot_service 前執行）
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from robot_service.unified_launcher import main  # noqa: E402


if __name__ == '__main__':
    main()
