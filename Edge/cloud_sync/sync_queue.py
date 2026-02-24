# imports
import json
import logging
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple
from uuid import uuid4

logger = logging.getLogger(__name__)


class SyncItemStatus(Enum):
    """同步項目狀態"""
    PENDING = "pending"    # 等待發送
    SENDING = "sending"    # 正在發送
    SENT = "sent"          # 已發送
    FAILED = "failed"      # 發送失敗（超出重試次數）


# 發送處理器類型：接收 (op_type, payload)，返回是否成功
SendHandler = Callable[[str, Dict[str, Any]], bool]


class CloudSyncQueue:
    """雲端同步佇列

    功能：
    1. **先後發送機制**：以 SQLite 序號（seq）確保 FIFO 順序，
       重連後仍按原始入隊順序補發，不會亂序。
    2. **本地快取**：離線時將待同步資料持久化到 SQLite，
       程式重啟後佇列仍保留，確保資料不遺失。
    3. **自動重試**：網路暫時失敗時保持 PENDING 狀態，
       下次 flush 時重試，直到超出最大重試次數才標記 FAILED。
    4. **批次發送**：可設定 batch_size，每次 flush 批次取出項目，
       降低記憶體壓力。
    """

    def __init__(
        self,
        db_path: Optional[str] = None,
        max_size: int = 500,
        max_retry_count: int = 3,
        batch_size: int = 20,
    ):
        """初始化雲端同步佇列

        Args:
            db_path: SQLite 資料庫路徑；None 表示使用記憶體資料庫（:memory:）
            max_size: 最大佇列大小（PENDING 項目數）
            max_retry_count: 最大重試次數，超出後標記 FAILED
            batch_size: 每次 flush 批次大小
        """
        self._db_path = db_path or ":memory:"
        self._max_size = max_size
        self._max_retry_count = max_retry_count
        self._batch_size = batch_size

        self._lock = threading.RLock()
        self._is_online = False

        # 記憶體資料庫保持持久連線，避免資料在連線關閉後消失
        self._is_memory_db = self._db_path == ":memory:"
        self._persistent_conn: Optional[sqlite3.Connection] = None

        # 統計
        self._total_enqueued = 0
        self._total_sent = 0
        self._total_failed = 0

        self._init_db()

        logger.info("CloudSyncQueue initialized", extra={
            "db_path": self._db_path,
            "max_size": max_size,
            "max_retry_count": max_retry_count,
            "batch_size": batch_size,
            "service": "cloud_sync_queue",
        })

    # ==================== 資料庫 ====================

    @contextmanager
    def _get_conn(self) -> Generator[sqlite3.Connection, None, None]:
        """取得資料庫連線（context manager）"""
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

    def _init_db(self) -> None:
        """初始化 SQLite 資料表與索引，並將殘留 SENDING 重置回 PENDING"""
        with self._lock:
            with self._get_conn() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS sync_queue (
                        id         TEXT    PRIMARY KEY,
                        seq        INTEGER NOT NULL,
                        op_type    TEXT    NOT NULL,
                        payload    TEXT    NOT NULL,
                        trace_id   TEXT,
                        status     TEXT    NOT NULL DEFAULT 'pending',
                        retry_cnt  INTEGER NOT NULL DEFAULT 0,
                        last_error TEXT,
                        created_at TEXT    NOT NULL,
                        updated_at TEXT    NOT NULL
                    )
                """)
                conn.execute(
                    "CREATE UNIQUE INDEX IF NOT EXISTS idx_sq_seq "
                    "ON sync_queue (seq)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_sq_status "
                    "ON sync_queue (status)"
                )
                # 程序上次崩潰時可能留下 SENDING 狀態的項目；重置為 PENDING 以允許重試
                conn.execute(
                    "UPDATE sync_queue SET status = 'pending' WHERE status = 'sending'"
                )
                conn.commit()

    # ==================== 狀態管理 ====================

    def set_online(self, is_online: bool) -> None:
        """設定雲端在線狀態

        Args:
            is_online: 雲端是否可用
        """
        old = self._is_online
        self._is_online = is_online
        if is_online and not old:
            logger.info("Cloud became online, sync queue ready to flush", extra={
                "service": "cloud_sync_queue",
            })

    @property
    def is_online(self) -> bool:
        """雲端是否在線"""
        return self._is_online

    # ==================== 佇列操作 ====================

    def enqueue(
        self,
        op_type: str,
        payload: Dict[str, Any],
        trace_id: Optional[str] = None,
    ) -> Optional[str]:
        """將同步操作加入佇列（先後發送快取）

        離線或雲端不可用時呼叫此方法，操作會被持久化到 SQLite，
        待 flush() 時按 seq 序號順序依序發送。

        Args:
            op_type: 操作類型（例如：'user_settings'、'command_history'）
            payload: 要同步的資料（必須可 JSON 序列化）
            trace_id: 追蹤 ID（可選）

        Returns:
            操作 ID（UUID），佇列已滿或序列化失敗時返回 None
        """
        op_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()

        try:
            payload_json = json.dumps(payload, ensure_ascii=False)
        except (TypeError, ValueError) as e:
            logger.error("Failed to serialize payload for enqueue", extra={
                "op_type": op_type,
                "error": str(e),
                "service": "cloud_sync_queue",
            })
            return None

        with self._lock:
            with self._get_conn() as conn:
                cnt = conn.execute(
                    "SELECT COUNT(*) FROM sync_queue WHERE status = 'pending'"
                ).fetchone()[0]

                if cnt >= self._max_size:
                    logger.warning("Sync queue full, rejecting item", extra={
                        "op_type": op_type,
                        "queue_size": cnt,
                        "max_size": self._max_size,
                        "service": "cloud_sync_queue",
                    })
                    return None

                next_seq = conn.execute(
                    "SELECT COALESCE(MAX(seq), -1) + 1 AS ns FROM sync_queue"
                ).fetchone()["ns"]

                try:
                    conn.execute(
                        """
                        INSERT INTO sync_queue
                            (id, seq, op_type, payload, trace_id, status,
                             retry_cnt, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, 'pending', 0, ?, ?)
                        """,
                        (op_id, next_seq, op_type, payload_json,
                         trace_id, now, now),
                    )
                    conn.commit()
                except Exception as e:
                    logger.error("Failed to insert sync item", extra={
                        "op_type": op_type,
                        "error": str(e),
                        "service": "cloud_sync_queue",
                    })
                    return None

            self._total_enqueued += 1

        logger.info("Sync item enqueued", extra={
            "op_id": op_id,
            "op_type": op_type,
            "trace_id": trace_id,
            "service": "cloud_sync_queue",
        })
        return op_id

    def flush(self, send_handler: SendHandler) -> Dict[str, Any]:
        """清空佇列：按 seq 順序依序發送所有 PENDING 項目

        先後發送機制的核心：以 seq 升序取出項目，確保入隊順序即發送順序。
        單筆發送失敗不中斷後續項目（除非整批失敗表示離線）。

        Args:
            send_handler: 發送函式，接收 (op_type, payload)，
                          返回 True 表示成功，False 表示失敗

        Returns:
            Dict with keys: sent, failed, remaining
        """
        sent = 0
        failed = 0

        while True:
            batch = self._get_pending_batch()
            if not batch:
                break

            batch_all_failed = True
            for item in batch:
                op_id, op_type, payload, trace_id, retry_cnt = item

                try:
                    success = send_handler(op_type, payload)
                except Exception as e:
                    logger.error("send_handler raised exception", extra={
                        "op_id": op_id,
                        "op_type": op_type,
                        "trace_id": trace_id,
                        "error": str(e),
                        "service": "cloud_sync_queue",
                    })
                    success = False

                if success:
                    self._remove_item(op_id)
                    sent += 1
                    batch_all_failed = False
                    self._total_sent += 1
                    logger.info("Sync item sent successfully", extra={
                        "op_id": op_id,
                        "op_type": op_type,
                        "trace_id": trace_id,
                        "service": "cloud_sync_queue",
                    })
                else:
                    new_retry = retry_cnt + 1
                    if new_retry >= self._max_retry_count:
                        self._update_status(
                            op_id, SyncItemStatus.FAILED,
                            error="Max retries exceeded",
                            retry_cnt=new_retry,
                        )
                        failed += 1
                        self._total_failed += 1
                        logger.warning("Sync item permanently failed", extra={
                            "op_id": op_id,
                            "op_type": op_type,
                            "trace_id": trace_id,
                            "retry_cnt": new_retry,
                            "service": "cloud_sync_queue",
                        })
                    else:
                        self._update_status(
                            op_id, SyncItemStatus.PENDING,
                            error="Send failed, will retry",
                            retry_cnt=new_retry,
                        )
                        failed += 1
                        logger.warning("Sync item failed, will retry", extra={
                            "op_id": op_id,
                            "op_type": op_type,
                            "trace_id": trace_id,
                            "retry_cnt": new_retry,
                            "max_retry": self._max_retry_count,
                            "service": "cloud_sync_queue",
                        })

            # 整批都失敗代表可能離線，停止避免無限循環
            if batch_all_failed:
                break

        remaining = self.size()
        logger.info("Sync queue flush completed", extra={
            "sent": sent,
            "failed": failed,
            "remaining": remaining,
            "service": "cloud_sync_queue",
        })
        return {"sent": sent, "failed": failed, "remaining": remaining}

    # ==================== 查詢 ====================

    def size(self) -> int:
        """取得 PENDING 項目數量"""
        with self._lock:
            with self._get_conn() as conn:
                row = conn.execute(
                    "SELECT COUNT(*) FROM sync_queue WHERE status = 'pending'"
                ).fetchone()
                return row[0] if row else 0

    def get_statistics(self) -> Dict[str, Any]:
        """取得統計資訊"""
        counts: Dict[str, int] = {
            SyncItemStatus.PENDING.value: 0,
            SyncItemStatus.SENDING.value: 0,
            SyncItemStatus.FAILED.value: 0,
        }
        with self._lock:
            with self._get_conn() as conn:
                for row in conn.execute(
                    "SELECT status, COUNT(*) cnt FROM sync_queue GROUP BY status"
                ).fetchall():
                    if row["status"] in counts:
                        counts[row["status"]] = row["cnt"]

        return {
            "pending": counts[SyncItemStatus.PENDING.value],
            "sending": counts[SyncItemStatus.SENDING.value],
            "failed": counts[SyncItemStatus.FAILED.value],
            "total_enqueued": self._total_enqueued,
            "total_sent": self._total_sent,
            "total_failed": self._total_failed,
            "max_size": self._max_size,
            "is_online": self._is_online,
        }

    # ==================== 維護 ====================

    def clear(self) -> None:
        """清空佇列（所有狀態）"""
        with self._lock:
            with self._get_conn() as conn:
                conn.execute("DELETE FROM sync_queue")
                conn.commit()
        logger.info("Sync queue cleared", extra={"service": "cloud_sync_queue"})

    def close(self) -> None:
        """關閉持久記憶體資料庫連線"""
        if self._persistent_conn:
            self._persistent_conn.close()
            self._persistent_conn = None

    # ==================== 私有輔助 ====================

    def _get_pending_batch(self) -> List[Tuple]:
        """按 seq 升序取得一批 PENDING 項目"""
        with self._lock:
            with self._get_conn() as conn:
                rows = conn.execute(
                    """
                    SELECT id, seq, op_type, payload, trace_id, retry_cnt
                    FROM sync_queue
                    WHERE status = 'pending'
                    ORDER BY seq ASC
                    LIMIT ?
                    """,
                    (self._batch_size,),
                ).fetchall()

        result = []
        for row in rows:
            try:
                payload = json.loads(row["payload"])
                result.append((
                    row["id"], row["op_type"], payload,
                    row["trace_id"], row["retry_cnt"],
                ))
            except Exception as e:
                logger.error("Failed to parse queued sync item", extra={
                    "item_id": row["id"],
                    "error": str(e),
                    "service": "cloud_sync_queue",
                })
        return result

    def _update_status(
        self,
        op_id: str,
        status: SyncItemStatus,
        error: Optional[str] = None,
        retry_cnt: Optional[int] = None,
    ) -> None:
        """更新項目狀態"""
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            with self._get_conn() as conn:
                if retry_cnt is not None:
                    conn.execute(
                        """
                        UPDATE sync_queue
                        SET status = ?, last_error = ?, retry_cnt = ?, updated_at = ?
                        WHERE id = ?
                        """,
                        (status.value, error, retry_cnt, now, op_id),
                    )
                else:
                    conn.execute(
                        """
                        UPDATE sync_queue
                        SET status = ?, last_error = ?, updated_at = ?
                        WHERE id = ?
                        """,
                        (status.value, error, now, op_id),
                    )
                conn.commit()

    def _remove_item(self, op_id: str) -> None:
        """移除已成功發送的項目"""
        with self._lock:
            with self._get_conn() as conn:
                conn.execute(
                    "DELETE FROM sync_queue WHERE id = ?", (op_id,)
                )
                conn.commit()
