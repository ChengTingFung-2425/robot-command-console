"""
日期時間工具模組
提供統一的時間處理函式
"""

from datetime import datetime, timezone
from typing import Optional


def utc_now() -> datetime:
    """
    取得當前 UTC 時間
    
    Returns:
        當前 UTC 時間的 datetime 物件
    """
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    """
    取得當前 UTC 時間的 ISO 格式字串
    
    Returns:
        ISO 8601 格式的時間字串
    """
    return datetime.now(timezone.utc).isoformat()


def parse_iso_datetime(iso_string: str) -> Optional[datetime]:
    """
    解析 ISO 格式的時間字串
    
    Args:
        iso_string: ISO 8601 格式的時間字串
        
    Returns:
        datetime 物件，如果解析失敗則返回 None
    """
    try:
        return datetime.fromisoformat(iso_string)
    except (ValueError, TypeError):
        return None


def format_timestamp(dt: Optional[datetime] = None) -> str:
    """
    格式化時間戳為 ISO 格式
    
    Args:
        dt: datetime 物件，如果為 None 則使用當前 UTC 時間
        
    Returns:
        ISO 8601 格式的時間字串
    """
    if dt is None:
        dt = datetime.now(timezone.utc)
    return dt.isoformat()


def seconds_since(start_time: datetime) -> float:
    """
    計算從指定時間到現在經過的秒數
    
    Args:
        start_time: 開始時間
        
    Returns:
        經過的秒數
    """
    return (datetime.now(timezone.utc) - start_time).total_seconds()
