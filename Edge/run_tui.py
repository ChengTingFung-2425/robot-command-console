#!/usr/bin/env python3
"""
Robot Console TUI 入口點
終端機互動介面模式
"""

import os
import sys

# 添加 src 到路徑（必須在導入 robot_service 前執行）
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from robot_service.tui.runner import main  # noqa: E402


if __name__ == '__main__':
    main()
