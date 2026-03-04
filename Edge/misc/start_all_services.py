#!/usr/bin/env python3
"""
Edge Service Starter Script

啟動 Edge 層各核心服務的輔助腳本。
此腳本委派給上層的 Edge/start_all_services.py，
並提供 Edge 服務的預設啟動設定。

使用方式：
    python3 Edge/misc/start_all_services.py
    python3 Edge/misc/start_all_services.py --services flask,mcp
"""

import os
import runpy
import sys
from pathlib import Path

# 將 Edge 根目錄加入路徑，委派給主腳本
_edge_root = Path(__file__).parent.parent
sys.path.insert(0, str(_edge_root))

if __name__ == '__main__':
    # 切換到 Edge 根目錄，確保相對路徑正確
    os.chdir(_edge_root)
    runpy.run_path(str(_edge_root / 'start_all_services.py'), run_name='__main__')
