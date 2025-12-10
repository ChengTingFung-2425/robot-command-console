"""
本地指令快取模組

提供指令結果的記憶體快取，支援 LRU 淘汰策略與 TTL 過期機制。
用於減少重複請求、提升響應速度與支援離線查詢。
"""

import logging
import threading
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from .datetime_utils import utc_now


logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """快取項目"""
    
    key: str
    value: Any
    created_at: datetime = field(default_factory=utc_now)
    accessed_at: datetime = field(default_factory=utc_now)
    expires_at: Optional[datetime] = None
    hit_count: int = 0
    
    def is_expired(self) -> bool:
        """檢查是否過期"""
        if self.expires_at is None:
            return False
        return utc_now() >= self.expires_at
    
    def touch(self):
        """更新存取時間並增加命中計數"""
        self.accessed_at = utc_now()
        self.hit_count += 1


class CommandCache:
    """本地指令快取
    
    使用 LRU（Least Recently Used）策略管理快取，支援：
    - 記憶體快取指令結果
    - TTL（Time To Live）過期機制
    - LRU 淘汰策略
    - 執行緒安全
    - 快取統計資訊
    """
    
    def __init__(
        self,
        max_size: int = 1000,
        default_ttl_seconds: int = 3600,
        enable_stats: bool = True
    ):
        """初始化指令快取
        
        Args:
            max_size: 最大快取項目數量
            default_ttl_seconds: 預設 TTL（秒），0 表示永不過期
            enable_stats: 是否啟用統計功能
        """
        self.max_size = max_size
        self.default_ttl_seconds = default_ttl_seconds
        self.enable_stats = enable_stats
        
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        
        # 統計資訊
        self._stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'expirations': 0,
            'sets': 0,
            'deletes': 0
        }
        
        logger.info(f"CommandCache initialized with max_size={max_size}, default_ttl={default_ttl_seconds}s")
    
    def get(self, key: str) -> Optional[Any]:
        """取得快取值
        
        Args:
            key: 快取鍵
            
        Returns:
            快取值，若不存在或已過期則回傳 None
        """
        with self._lock:
            entry = self._cache.get(key)
            
            if entry is None:
                if self.enable_stats:
                    self._stats['misses'] += 1
                return None
            
            # 檢查是否過期
            if entry.is_expired():
                self._remove_entry(key)
                if self.enable_stats:
                    self._stats['misses'] += 1
                    self._stats['expirations'] += 1
                return None
            
            # 更新存取記錄（LRU）
            entry.touch()
            self._cache.move_to_end(key)
            
            if self.enable_stats:
                self._stats['hits'] += 1
            
            return entry.value
    
    def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None
    ) -> bool:
        """設定快取值
        
        Args:
            key: 快取鍵
            value: 快取值
            ttl_seconds: TTL（秒），None 表示使用預設值，0 表示永不過期
            
        Returns:
            是否設定成功
        """
        with self._lock:
            try:
                # 計算過期時間
                expires_at = None
                if ttl_seconds is None:
                    ttl_seconds = self.default_ttl_seconds
                
                if ttl_seconds > 0:
                    expires_at = utc_now() + timedelta(seconds=ttl_seconds)
                
                # 如果鍵已存在，先移除
                if key in self._cache:
                    del self._cache[key]
                
                # 如果快取已滿，移除最舊的項目（LRU）
                if len(self._cache) >= self.max_size:
                    self._evict_lru()
                
                # 新增快取項目
                entry = CacheEntry(
                    key=key,
                    value=value,
                    expires_at=expires_at
                )
                self._cache[key] = entry
                
                if self.enable_stats:
                    self._stats['sets'] += 1
                
                return True
            except Exception as e:
                logger.error(f"Failed to set cache: {e}")
                return False
    
    def delete(self, key: str) -> bool:
        """刪除快取項目
        
        Args:
            key: 快取鍵
            
        Returns:
            是否刪除成功（鍵存在）
        """
        with self._lock:
            if key in self._cache:
                self._remove_entry(key)
                if self.enable_stats:
                    self._stats['deletes'] += 1
                return True
            return False
    
    def clear(self):
        """清空所有快取"""
        with self._lock:
            self._cache.clear()
            logger.info("Cache cleared")
    
    def cleanup_expired(self) -> int:
        """清理過期項目
        
        Returns:
            清理的項目數量
        """
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired()
            ]
            
            for key in expired_keys:
                self._remove_entry(key)
                if self.enable_stats:
                    self._stats['expirations'] += 1
            
            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
            
            return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """取得快取統計資訊
        
        Returns:
            統計資訊字典
        """
        with self._lock:
            total_requests = self._stats['hits'] + self._stats['misses']
            hit_rate = (self._stats['hits'] / total_requests * 100) if total_requests > 0 else 0.0
            
            return {
                'size': len(self._cache),
                'max_size': self.max_size,
                'hits': self._stats['hits'],
                'misses': self._stats['misses'],
                'hit_rate': round(hit_rate, 2),
                'evictions': self._stats['evictions'],
                'expirations': self._stats['expirations'],
                'sets': self._stats['sets'],
                'deletes': self._stats['deletes']
            }
    
    def reset_stats(self):
        """重置統計資訊"""
        with self._lock:
            self._stats = {
                'hits': 0,
                'misses': 0,
                'evictions': 0,
                'expirations': 0,
                'sets': 0,
                'deletes': 0
            }
            logger.info("Cache stats reset")
    
    def _evict_lru(self):
        """淘汰最少使用的項目（LRU）"""
        if self._cache:
            # OrderedDict 的第一個項目是最舊的
            oldest_key = next(iter(self._cache))
            self._remove_entry(oldest_key)
            if self.enable_stats:
                self._stats['evictions'] += 1
            logger.debug(f"Evicted LRU cache entry: {oldest_key}")
    
    def _remove_entry(self, key: str):
        """移除快取項目（內部使用）"""
        if key in self._cache:
            del self._cache[key]


class CommandResultCache(CommandCache):
    """指令結果快取
    
    特化的快取類別，專門用於快取指令執行結果。
    提供針對指令 ID 和 trace ID 的快速查詢。
    """
    
    def __init__(
        self,
        max_size: int = 500,
        default_ttl_seconds: int = 1800
    ):
        """初始化指令結果快取
        
        Args:
            max_size: 最大快取項目數量
            default_ttl_seconds: 預設 TTL（秒），預設 30 分鐘
        """
        super().__init__(
            max_size=max_size,
            default_ttl_seconds=default_ttl_seconds,
            enable_stats=True
        )
        
        # trace_id 到 command_id 的對應
        self._trace_to_command: Dict[str, str] = {}
    
    def set_command_result(
        self,
        command_id: str,
        trace_id: str,
        result: Dict[str, Any],
        ttl_seconds: Optional[int] = None
    ) -> bool:
        """設定指令結果快取
        
        Args:
            command_id: 指令 ID
            trace_id: 追蹤 ID
            result: 指令結果
            ttl_seconds: TTL（秒）
            
        Returns:
            是否設定成功
        """
        success = self.set(command_id, result, ttl_seconds)
        if success:
            with self._lock:
                self._trace_to_command[trace_id] = command_id
        return success
    
    def get_by_trace_id(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """透過 trace ID 取得指令結果
        
        Args:
            trace_id: 追蹤 ID
            
        Returns:
            指令結果，若不存在則回傳 None
        """
        with self._lock:
            command_id = self._trace_to_command.get(trace_id)
            if command_id is None:
                return None
            return self.get(command_id)
    
    def delete_by_trace_id(self, trace_id: str) -> bool:
        """透過 trace ID 刪除指令結果
        
        Args:
            trace_id: 追蹤 ID
            
        Returns:
            是否刪除成功
        """
        with self._lock:
            command_id = self._trace_to_command.get(trace_id)
            if command_id is None:
                return False
            
            # 刪除對應關係
            del self._trace_to_command[trace_id]
            
            # 刪除快取項目
            return self.delete(command_id)
    
    def clear(self):
        """清空所有快取"""
        with self._lock:
            super().clear()
            self._trace_to_command.clear()
            logger.info("Command result cache cleared")
