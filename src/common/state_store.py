"""
Local State Store
基於 SQLite 的本地狀態存儲，用於服務間狀態共享

提供：
- 鍵值對存儲
- TTL 過期機制
- 非同步操作支援
- JSON 序列化/反序列化
"""

import asyncio
import json
import logging
import sqlite3
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .datetime_utils import utc_now

logger = logging.getLogger(__name__)


@dataclass
class StateEntry:
    """狀態條目"""
    key: str
    value: Any
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class LocalStateStore:
    """
    本地狀態存儲

    使用 SQLite 作為持久化後端，提供：
    - 鍵值對存儲與檢索
    - 可選的 TTL 過期機制
    - 前綴搜尋功能
    - 非同步操作支援
    """

    def __init__(
        self,
        db_path: Optional[str] = None,
        cleanup_interval: float = 60.0,
    ):
        """
        初始化狀態存儲

        Args:
            db_path: SQLite 資料庫路徑，預設為記憶體資料庫
            cleanup_interval: 過期清理間隔（秒）
        """
        self._db_path = db_path or ":memory:"
        self._cleanup_interval = cleanup_interval
        self._lock = threading.RLock()
        self._running = False
        self._cleanup_task: Optional[asyncio.Task] = None

        # 對於記憶體資料庫，保持一個持久連線
        self._is_memory_db = self._db_path == ":memory:"
        self._persistent_conn: Optional[sqlite3.Connection] = None

        # 初始化資料庫
        self._init_db()

        logger.info("LocalStateStore initialized", extra={
            "db_path": self._db_path,
            "cleanup_interval": cleanup_interval,
            "service": "state_store"
        })

    def _init_db(self) -> None:
        """初始化資料庫表格"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS state (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    expires_at TEXT,
                    metadata TEXT
                )
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_expires_at
                ON state (expires_at)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_key_prefix
                ON state (key)
            """)
            conn.commit()

    @contextmanager
    def _get_connection(self):
        """取得資料庫連線"""
        if self._is_memory_db:
            # 記憶體資料庫使用持久連線
            if self._persistent_conn is None:
                self._persistent_conn = sqlite3.connect(
                    self._db_path, check_same_thread=False
                )
                self._persistent_conn.row_factory = sqlite3.Row
            yield self._persistent_conn
        else:
            # 檔案資料庫每次建立新連線
            conn = sqlite3.connect(self._db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            try:
                yield conn
            finally:
                conn.close()

    async def start(self) -> None:
        """啟動狀態存儲（啟動過期清理任務）"""
        if self._running:
            return

        self._running = True
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup())

        logger.info("LocalStateStore started", extra={
            "service": "state_store"
        })

    async def stop(self) -> None:
        """停止狀態存儲"""
        if not self._running:
            return

        self._running = False

        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None

        # 關閉持久連線
        if self._persistent_conn:
            self._persistent_conn.close()
            self._persistent_conn = None

        logger.info("LocalStateStore stopped", extra={
            "service": "state_store"
        })

    async def _periodic_cleanup(self) -> None:
        """定期清理過期條目"""
        while self._running:
            try:
                await asyncio.sleep(self._cleanup_interval)
                await self.cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in periodic cleanup", extra={
                    "error": str(e),
                    "service": "state_store"
                })

    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        設置狀態

        Args:
            key: 狀態鍵
            value: 狀態值（會被 JSON 序列化）
            ttl_seconds: 過期時間（秒），None 表示永不過期
            metadata: 額外的元資料

        Returns:
            是否成功設置
        """
        now = utc_now()
        expires_at = None
        if ttl_seconds is not None:
            expires_at = now + timedelta(seconds=ttl_seconds)

        try:
            value_json = json.dumps(value, ensure_ascii=False, default=str)
            metadata_json = json.dumps(metadata, ensure_ascii=False) if metadata else None

            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT OR REPLACE INTO state
                        (key, value, created_at, updated_at, expires_at, metadata)
                        VALUES (?, ?, COALESCE(
                            (SELECT created_at FROM state WHERE key = ?),
                            ?
                        ), ?, ?, ?)
                    """, (
                        key,
                        value_json,
                        key,
                        now.isoformat(),
                        now.isoformat(),
                        expires_at.isoformat() if expires_at else None,
                        metadata_json,
                    ))
                    conn.commit()

            logger.debug("State set", extra={
                "key": key,
                "ttl_seconds": ttl_seconds,
                "service": "state_store"
            })
            return True

        except Exception as e:
            logger.error("Failed to set state", extra={
                "key": key,
                "error": str(e),
                "service": "state_store"
            })
            return False

    async def get(self, key: str) -> Optional[Any]:
        """
        取得狀態

        Args:
            key: 狀態鍵

        Returns:
            狀態值，若不存在或已過期則返回 None
        """
        try:
            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT value, expires_at FROM state WHERE key = ?
                    """, (key,))
                    row = cursor.fetchone()

            if row is None:
                return None

            # 檢查是否過期
            if row["expires_at"]:
                expires_at = datetime.fromisoformat(row["expires_at"])
                if expires_at <= utc_now():
                    # 過期，移除並返回 None
                    await self.delete(key)
                    return None

            return json.loads(row["value"])

        except Exception as e:
            logger.error("Failed to get state", extra={
                "key": key,
                "error": str(e),
                "service": "state_store"
            })
            return None

    async def get_entry(self, key: str) -> Optional[StateEntry]:
        """
        取得完整狀態條目

        Args:
            key: 狀態鍵

        Returns:
            完整的狀態條目，包含元資料
        """
        try:
            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT * FROM state WHERE key = ?
                    """, (key,))
                    row = cursor.fetchone()

            if row is None:
                return None

            # 檢查是否過期
            expires_at = None
            if row["expires_at"]:
                expires_at = datetime.fromisoformat(row["expires_at"])
                if expires_at <= utc_now():
                    await self.delete(key)
                    return None

            return StateEntry(
                key=row["key"],
                value=json.loads(row["value"]),
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
                expires_at=expires_at,
                metadata=json.loads(row["metadata"]) if row["metadata"] else None,
            )

        except Exception as e:
            logger.error("Failed to get state entry", extra={
                "key": key,
                "error": str(e),
                "service": "state_store"
            })
            return None

    async def delete(self, key: str) -> bool:
        """
        刪除狀態

        Args:
            key: 狀態鍵

        Returns:
            是否成功刪除
        """
        try:
            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM state WHERE key = ?", (key,))
                    conn.commit()
                    deleted = cursor.rowcount > 0

            if deleted:
                logger.debug("State deleted", extra={
                    "key": key,
                    "service": "state_store"
                })
            return deleted

        except Exception as e:
            logger.error("Failed to delete state", extra={
                "key": key,
                "error": str(e),
                "service": "state_store"
            })
            return False

    async def exists(self, key: str) -> bool:
        """
        檢查狀態是否存在

        Args:
            key: 狀態鍵

        Returns:
            是否存在且未過期
        """
        return await self.get(key) is not None

    async def get_by_prefix(self, prefix: str) -> Dict[str, Any]:
        """
        取得指定前綴的所有狀態

        Args:
            prefix: 鍵前綴

        Returns:
            符合前綴的狀態字典
        """
        results = {}
        now = utc_now()

        try:
            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT key, value, expires_at FROM state
                        WHERE key LIKE ? || '%'
                    """, (prefix,))
                    rows = cursor.fetchall()

            for row in rows:
                # 檢查是否過期
                if row["expires_at"]:
                    expires_at = datetime.fromisoformat(row["expires_at"])
                    if expires_at <= now:
                        continue
                results[row["key"]] = json.loads(row["value"])

            return results

        except Exception as e:
            logger.error("Failed to get states by prefix", extra={
                "prefix": prefix,
                "error": str(e),
                "service": "state_store"
            })
            return {}

    async def get_keys(self, prefix: Optional[str] = None) -> List[str]:
        """
        取得所有鍵

        Args:
            prefix: 可選的鍵前綴過濾

        Returns:
            鍵列表
        """
        now = utc_now()

        try:
            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    if prefix:
                        cursor.execute("""
                            SELECT key, expires_at FROM state
                            WHERE key LIKE ? || '%'
                        """, (prefix,))
                    else:
                        cursor.execute("SELECT key, expires_at FROM state")
                    rows = cursor.fetchall()

            keys = []
            for row in rows:
                if row["expires_at"]:
                    expires_at = datetime.fromisoformat(row["expires_at"])
                    if expires_at <= now:
                        continue
                keys.append(row["key"])

            return keys

        except Exception as e:
            logger.error("Failed to get keys", extra={
                "prefix": prefix,
                "error": str(e),
                "service": "state_store"
            })
            return []

    async def cleanup_expired(self) -> int:
        """
        清理過期條目

        Returns:
            清理的條目數量
        """
        now = utc_now()

        try:
            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        DELETE FROM state
                        WHERE expires_at IS NOT NULL AND expires_at <= ?
                    """, (now.isoformat(),))
                    conn.commit()
                    count = cursor.rowcount

            if count > 0:
                logger.info("Expired states cleaned up", extra={
                    "count": count,
                    "service": "state_store"
                })
            return count

        except Exception as e:
            logger.error("Failed to cleanup expired states", extra={
                "error": str(e),
                "service": "state_store"
            })
            return 0

    async def clear(self) -> bool:
        """
        清除所有狀態

        Returns:
            是否成功清除
        """
        try:
            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM state")
                    conn.commit()

            logger.info("All states cleared", extra={
                "service": "state_store"
            })
            return True

        except Exception as e:
            logger.error("Failed to clear states", extra={
                "error": str(e),
                "service": "state_store"
            })
            return False

    async def health_check(self) -> Dict[str, Any]:
        """
        健康檢查

        Returns:
            健康狀態資訊
        """
        try:
            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) as count FROM state")
                    row = cursor.fetchone()
                    count = row["count"] if row else 0

            return {
                "status": "healthy",
                "running": self._running,
                "db_path": self._db_path,
                "entry_count": count,
                "timestamp": utc_now().isoformat(),
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "running": self._running,
                "db_path": self._db_path,
                "error": str(e),
                "timestamp": utc_now().isoformat(),
            }
