"""
測試配置

提供所有測試共用的 fixtures 和配置
"""

import sys
from pathlib import Path

import pytest

# 添加專案路徑
PROJECT_ROOT = Path(__file__).parent.parent
SRC_PATH = PROJECT_ROOT / 'src'

# 確保 src 目錄在 Python 路徑中
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

# 確保專案根目錄在 Python 路徑中
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def project_root():
    """返回專案根目錄"""
    return PROJECT_ROOT


@pytest.fixture
def electron_app_path():
    """返回 Electron 應用目錄"""
    return PROJECT_ROOT / 'electron-app'


@pytest.fixture
def src_path():
    """返回 src 目錄"""
    return PROJECT_ROOT / 'src'


@pytest.fixture
def mcp_path():
    """返回 MCP 目錄"""
    return PROJECT_ROOT / 'MCP'
