"""
Offline Buffer
離線指令緩衝模組

提供：
- 離線時指令持久化緩衝
- 重連後自動重送機制
- 緩衝區大小管理
- 指令優先權保持
"""

import asyncio
import json
import logging
import os
import sqlite3
import sys
import threading
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional

# 確保可以正確導入 common 模組
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from common.datetime_utils import utc_now  # noqa: E402
from src.robot_service.queue.interface import Message  # noqa: E402

logger = logging.getLogger(__name__)


class BufferEntryStatus(Enum):
    """緩衝條目狀態"""
    PENDING = "pending"          # 等待發送
    SENDING = "sending"          # 正在發送
    SENT = "sent"                # 已發送
    FAILED = "failed"            # 發送失敗
    EXPIRED = "expired"          # 已過期


@dataclass
class BufferEntry:
    """緩衝條目"""
    id: str
    message: Message
    status: BufferEntryStatus = BufferEntryStatus.PENDING
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    retry_count: int = 0
    last_error: Optional[str] = None
    expires_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "id": self.id,
            "message": self.message.to_dict(),
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "retry_count": self.retry_count,
            "last_error": self.last_error,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BufferEntry":
        """從字典建立"""
        return cls(
            id=data["id"],
            message=Message.from_dict(data["message"]),
            status=BufferEntryStatus(data.get("status", "pending")),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else utc_now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else utc_now(),
            retry_count=data.get("retry_count", 0),
            last_error=data.get("last_error"),
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
        )


# 發送處理器類型
SendHandler = Callable[[Message], Coroutine[Any, Any, bool]]


class OfflineBuffer:
    """
    離線指令緩衝器

    功能：
    - 離線時將指令持久化到 SQLite
    - 支援指令優先權
    - 自動過期清理
    - 重連後自動發送緩衝指令
    - 發送失敗重試
    """

    def __init__(
        self,
        db_path: Optional[str] = None,
        max_size: int = 1000,
        default_ttl_seconds: float = 3600.0,  # 預設 1 小時過期
        max_retry_count: int = 3,
        retry_delay_seconds: float = 5.0,
        send_batch_size: int = 10,
    ):
        """
        初始化離線緩衝器

        Args:
            db_path: SQLite 資料庫路徑，預設為記憶體資料庫
            max_size: 最大緩衝數量
            default_ttl_seconds: 預設過期時間（秒）
            max_retry_count: 最大重試次數
            retry_delay_seconds: 重試延遲（秒）
            send_batch_size: 批次發送數量
        """
        self._db_path = db_path or ":memory:"
        self._max_size = max_size
        self._default_ttl_seconds = default_ttl_seconds
        self._max_retry_count = max_retry_count
        self._retry_delay_seconds = retry_delay_seconds
        self._send_batch_size = send_batch_size

        self._lock = threading.RLock()
        self._running = False
        self._send_handler: Optional[SendHandler] = None
        self._flush_task: Optional[asyncio.Task] = None
        self._is_online = False

        # 對於記憶體資料庫，保持一個持久連線
        self._is_memory_db = self._db_path == ":memory:"
        self._persistent_conn: Optional[sqlite3.Connection] = None

        # 統計資訊
        self._total_buffered = 0
        self._total_sent = 0
        self._total_failed = 0
        self._total_expired = 0

        # 初始化資料庫
        self._init_db()

        logger.info("OfflineBuffer initialized", extra={
            "db_path": self._db_path,
            "max_size": max_size,
            "default_ttl_seconds": default_ttl_seconds,
            "service": "offline_buffer"
        })

    def _init_db(self) -> None:
        """初始化資料庫表格"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS offline_buffer (
                    id TEXT PRIMARY KEY,
                    message_json TEXT NOT NULL,
                    priority INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    retry_count INTEGER DEFAULT 0,
                    last_error TEXT,
                    expires_at TEXT
                )
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_status
                ON offline_buffer (status)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_priority_created
                ON offline_buffer (priority DESC, created_at ASC)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_expires_at
                ON offline_buffer (expires_at)
            """)
            conn.commit()

    @contextmanager
    def _get_connection(self):
        """取得資料庫連線"""
        if self._is_memory_db:
            if self._persistent_conn is None:
                self._persistent_conn = sqlite3.connect(
                    self._db_path, check_same_thread=False
                )
                self._persistent_conn.row_factory = sqlite3.Row
            yield self._persistent_conn
        else:
            conn = sqlite3.connect(self._db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            try:
                yield conn
            finally:
                conn.close()

    def set_send_handler(self, handler: SendHandler) -> None:
        """
        設定發送處理器

        Args:
            handler: 非同步發送函式，接收 Message，返回是否成功
        """
        self._send_handler = handler

    def set_online(self, is_online: bool) -> None:
        """
        設定在線狀態

        Args:
            is_online: 是否在線
        """
        old_online = self._is_online
        self._is_online = is_online

        if is_online and not old_online:
            logger.info("Network restored, will flush buffer", extra={
                "service": "offline_buffer"
            })

    async def start(self) -> None:
        """啟動離線緩衝器"""
        if self._running:
            return

        self._running = True

        # 清理過期條目
        await self.cleanup_expired()

        logger.info("OfflineBuffer started", extra={
            "service": "offline_buffer"
        })

    async def stop(self) -> None:
        """停止離線緩衝器"""
        if not self._running:
            return

        self._running = False

        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
            self._flush_task = None

        # 關閉持久連線
        if self._persistent_conn:
            self._persistent_conn.close()
            self._persistent_conn = None

        logger.info("OfflineBuffer stopped", extra={
            "service": "offline_buffer"
        })

    async def buffer(
        self,
        message: Message,
        ttl_seconds: Optional[float] = None,
    ) -> bool:
        """
        緩衝指令

        Args:
            message: 要緩衝的訊息
            ttl_seconds: 過期時間（秒），None 使用預設值

        Returns:
            是否成功緩衝
        """
        # 檢查緩衝區大小
        current_size = await self.size()
        if current_size >= self._max_size:
            logger.warning("Buffer full, rejecting message", extra={
                "message_id": message.id,
                "current_size": current_size,
                "max_size": self._max_size,
                "service": "offline_buffer"
            })
            return False

        now = utc_now()
        ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl_seconds
        expires_at = now + timedelta(seconds=ttl) if ttl > 0 else None

        entry = BufferEntry(
            id=message.id,
            message=message,
            status=BufferEntryStatus.PENDING,
            created_at=now,
            updated_at=now,
            expires_at=expires_at,
        )

        try:
            message_json = json.dumps(message.to_dict(), ensure_ascii=False)

            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT OR REPLACE INTO offline_buffer
                        (id, message_json, priority, status, created_at, updated_at,
                         retry_count, last_error, expires_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        entry.id,
                        message_json,
                        message.priority.value,
                        entry.status.value,
                        entry.created_at.isoformat(),
                        entry.updated_at.isoformat(),
                        entry.retry_count,
                        entry.last_error,
                        entry.expires_at.isoformat() if entry.expires_at else None,
                    ))
                    conn.commit()

            self._total_buffered += 1

            logger.info("Message buffered", extra={
                "message_id": message.id,
                "priority": message.priority.name,
                "trace_id": message.trace_id,
                "expires_at": entry.expires_at.isoformat() if entry.expires_at else None,
                "service": "offline_buffer"
            })

            return True

        except Exception as e:
            logger.error("Failed to buffer message", extra={
                "message_id": message.id,
                "error": str(e),
                "service": "offline_buffer"
            })
            return False

    async def flush(self) -> Dict[str, Any]:
        """
        發送所有緩衝的指令

        Returns:
            發送結果統計
        """
        if not self._is_online:
            logger.debug("Not online, skipping flush", extra={
                "service": "offline_buffer"
            })
            return {"skipped": True, "reason": "offline"}

        if not self._send_handler:
            logger.warning("No send handler configured", extra={
                "service": "offline_buffer"
            })
            return {"skipped": True, "reason": "no_handler"}

        # 清理過期條目
        await self.cleanup_expired()

        sent_count = 0
        failed_count = 0
        remaining = await self.size()

        while remaining > 0 and self._is_online:
            entries = await self._get_pending_entries(self._send_batch_size)
            if not entries:
                break

            for entry in entries:
                if not self._is_online:
                    break

                success = await self._send_entry(entry)
                if success:
                    sent_count += 1
                else:
                    failed_count += 1

            remaining = await self.size()

        result = {
            "sent": sent_count,
            "failed": failed_count,
            "remaining": remaining,
        }

        logger.info("Buffer flush completed", extra={
            "sent": sent_count,
            "failed": failed_count,
            "remaining": remaining,
            "service": "offline_buffer"
        })

        return result

    async def _get_pending_entries(self, limit: int) -> List[BufferEntry]:
        """取得待發送的條目"""
        entries = []
        now = utc_now()

        try:
            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT id, message_json, status, created_at, updated_at,
                               retry_count, last_error, expires_at
                        FROM offline_buffer
                        WHERE status = ? AND (expires_at IS NULL OR expires_at > ?)
                        ORDER BY priority DESC, created_at ASC
                        LIMIT ?
                    """, (BufferEntryStatus.PENDING.value, now.isoformat(), limit))
                    rows = cursor.fetchall()

            for row in rows:
                try:
                    message_data = json.loads(row["message_json"])
                    message = Message.from_dict(message_data)
                    entry = BufferEntry(
                        id=row["id"],
                        message=message,
                        status=BufferEntryStatus(row["status"]),
                        created_at=datetime.fromisoformat(row["created_at"]),
                        updated_at=datetime.fromisoformat(row["updated_at"]),
                        retry_count=row["retry_count"],
                        last_error=row["last_error"],
                        expires_at=datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None,
                    )
                    entries.append(entry)
                except Exception as e:
                    logger.error("Failed to parse buffer entry", extra={
                        "entry_id": row["id"],
                        "error": str(e),
                        "service": "offline_buffer"
                    })

        except Exception as e:
            logger.error("Failed to get pending entries", extra={
                "error": str(e),
                "service": "offline_buffer"
            })

        return entries

    async def _send_entry(self, entry: BufferEntry) -> bool:
        """發送單個條目"""
        # 更新狀態為發送中
        await self._update_entry_status(entry.id, BufferEntryStatus.SENDING)

        try:
            success = await self._send_handler(entry.message)

            if success:
                # 發送成功，移除條目
                await self._remove_entry(entry.id)
                self._total_sent += 1

                logger.info("Buffered message sent successfully", extra={
                    "message_id": entry.message.id,
                    "service": "offline_buffer"
                })

                return True
            else:
                # 發送失敗，增加重試計數
                entry.retry_count += 1

                if entry.retry_count >= self._max_retry_count:
                    await self._update_entry_status(
                        entry.id,
                        BufferEntryStatus.FAILED,
                        error="Max retries exceeded",
                        retry_count=entry.retry_count,
                    )
                    self._total_failed += 1

                    logger.warning("Message send failed, max retries exceeded", extra={
                        "message_id": entry.message.id,
                        "retry_count": entry.retry_count,
                        "service": "offline_buffer"
                    })
                else:
                    await self._update_entry_status(
                        entry.id,
                        BufferEntryStatus.PENDING,
                        error="Send returned false",
                        retry_count=entry.retry_count,
                    )

                    logger.warning("Message send failed, will retry", extra={
                        "message_id": entry.message.id,
                        "retry_count": entry.retry_count,
                        "max_retries": self._max_retry_count,
                        "service": "offline_buffer"
                    })

                return False

        except Exception as e:
            entry.retry_count += 1

            if entry.retry_count >= self._max_retry_count:
                await self._update_entry_status(
                    entry.id,
                    BufferEntryStatus.FAILED,
                    error=str(e),
                    retry_count=entry.retry_count,
                )
                self._total_failed += 1
            else:
                await self._update_entry_status(
                    entry.id,
                    BufferEntryStatus.PENDING,
                    error=str(e),
                    retry_count=entry.retry_count,
                )

            logger.error("Error sending buffered message", extra={
                "message_id": entry.message.id,
                "error": str(e),
                "retry_count": entry.retry_count,
                "service": "offline_buffer"
            })

            return False

    async def _update_entry_status(
        self,
        entry_id: str,
        status: BufferEntryStatus,
        error: Optional[str] = None,
        retry_count: Optional[int] = None,
    ) -> None:
        """更新條目狀態"""
        now = utc_now()

        try:
            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    if retry_count is not None:
                        cursor.execute("""
                            UPDATE offline_buffer
                            SET status = ?, updated_at = ?, last_error = ?, retry_count = ?
                            WHERE id = ?
                        """, (status.value, now.isoformat(), error, retry_count, entry_id))
                    else:
                        cursor.execute("""
                            UPDATE offline_buffer
                            SET status = ?, updated_at = ?, last_error = ?
                            WHERE id = ?
                        """, (status.value, now.isoformat(), error, entry_id))
                    conn.commit()

        except Exception as e:
            logger.error("Failed to update entry status", extra={
                "entry_id": entry_id,
                "error": str(e),
                "service": "offline_buffer"
            })

    async def _remove_entry(self, entry_id: str) -> None:
        """移除條目"""
        try:
            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "DELETE FROM offline_buffer WHERE id = ?",
                        (entry_id,)
                    )
                    conn.commit()

        except Exception as e:
            logger.error("Failed to remove entry", extra={
                "entry_id": entry_id,
                "error": str(e),
                "service": "offline_buffer"
            })

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
                        DELETE FROM offline_buffer
                        WHERE expires_at IS NOT NULL AND expires_at <= ?
                    """, (now.isoformat(),))
                    conn.commit()
                    count = cursor.rowcount

            if count > 0:
                self._total_expired += count
                logger.info("Expired entries cleaned up", extra={
                    "count": count,
                    "service": "offline_buffer"
                })

            return count

        except Exception as e:
            logger.error("Failed to cleanup expired entries", extra={
                "error": str(e),
                "service": "offline_buffer"
            })
            return 0

    async def size(self) -> int:
        """
        取得緩衝區大小（待發送的條目數）

        Returns:
            待發送條目數量
        """
        try:
            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT COUNT(*) as count FROM offline_buffer
                        WHERE status = ?
                    """, (BufferEntryStatus.PENDING.value,))
                    row = cursor.fetchone()
                    return row["count"] if row else 0

        except Exception as e:
            logger.error("Failed to get buffer size", extra={
                "error": str(e),
                "service": "offline_buffer"
            })
            return 0

    async def clear(self) -> None:
        """清空緩衝區"""
        try:
            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM offline_buffer")
                    conn.commit()

            logger.info("Buffer cleared", extra={
                "service": "offline_buffer"
            })

        except Exception as e:
            logger.error("Failed to clear buffer", extra={
                "error": str(e),
                "service": "offline_buffer"
            })

    async def get_statistics(self) -> Dict[str, Any]:
        """
        取得統計資訊

        Returns:
            統計資訊字典
        """
        pending = 0
        sending = 0
        failed = 0

        try:
            with self._lock:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT status, COUNT(*) as count
                        FROM offline_buffer
                        GROUP BY status
                    """)
                    for row in cursor.fetchall():
                        if row["status"] == BufferEntryStatus.PENDING.value:
                            pending = row["count"]
                        elif row["status"] == BufferEntryStatus.SENDING.value:
                            sending = row["count"]
                        elif row["status"] == BufferEntryStatus.FAILED.value:
                            failed = row["count"]

        except Exception as e:
            logger.error("Failed to get statistics", extra={
                "error": str(e),
                "service": "offline_buffer"
            })

        return {
            "pending": pending,
            "sending": sending,
            "failed": failed,
            "total_buffered": self._total_buffered,
            "total_sent": self._total_sent,
            "total_failed": self._total_failed,
            "total_expired": self._total_expired,
            "max_size": self._max_size,
            "is_online": self._is_online,
        }

    async def health_check(self) -> Dict[str, Any]:
        """
        健康檢查

        Returns:
            健康狀態資訊
        """
        stats = await self.get_statistics()

        return {
            "status": "healthy" if self._running else "stopped",
            "running": self._running,
            "statistics": stats,
            "db_path": self._db_path,
            "timestamp": utc_now().isoformat(),
        }
