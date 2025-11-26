"""
工具模組
提供共用的工具函式與類別

此模組從 src/common 重新導出工具，以保持向後相容性
Edge 環境專用
"""

import sys
import os

# 添加 src 到路徑以便導入 common
src_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# 從 common 模組導入
from common.logging_utils import CustomJsonFormatter, setup_json_logging, get_logger
from common.datetime_utils import utc_now, utc_now_iso, parse_iso_datetime, format_timestamp, seconds_since
from common.config import EdgeConfig, get_config

__all__ = [
    "CustomJsonFormatter",
    "setup_json_logging",
    "get_logger",
    "utc_now",
    "utc_now_iso",
    "parse_iso_datetime",
    "format_timestamp",
    "seconds_since",
    "EdgeConfig",
    "get_config",
]
