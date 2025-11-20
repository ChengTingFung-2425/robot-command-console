#!/usr/bin/env python3
"""
Robot Service CLI 入口點
獨立執行模式，不依賴 Electron
"""

import os
import sys

# 添加 src 到路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from robot_service.cli.runner import main


if __name__ == '__main__':
    main()
