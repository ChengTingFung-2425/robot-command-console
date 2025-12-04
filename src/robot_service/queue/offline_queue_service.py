"""
Offline Queue Service
離線佇列服務

處理 Edge 到網路佇列服務的離線場景：

架構說明：
Edge 可能使用網路佇列服務（Redis/RabbitMQ）連接到 Runner。
當網路斷開時，佇列服務不可用，需要：
1. 將指令緩衝到本地 SQLite
2. 網路恢復時自動同步到網路佇列
3. 保持指令順序和優先權

┌─────────────────────────────────────────────────────────────────┐
│              網路佇列服務 (Redis/RabbitMQ/Kafka)                 │
│                    ↑ 網路斷開時不可用 ↑                         │
└─────────────────────────────────────────────────────────────────┘
                              ↓ ↑
┌─────────────────────────────────────────────────────────────────┐
│                         Edge 層                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    OfflineQueueService                     │  │
│  │                                                           │  │
│  │   ┌─────────────────┐      ┌─────────────────────────┐   │  │
│  │   │ 本地離線佇列    │←─────│ 網路佇列代理            │   │  │
│  │   │ (SQLite)        │      │                         │   │  │
│  │   │                 │      │ • 在線時直接發送       │   │  │
│  │   │ • 網路斷開時緩衝│      │ • 恢復時同步緩衝       │   │  │
│  │   │ • 持久化存儲    │─────▶│                         │   │  │
│  │   └─────────────────┘      └─────────────────────────┘   │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                     Runner（執行器）                             │
│                  從網路佇列接收並執行指令                        │
└─────────────────────────────────────────────────────────────────┘
"""

import asyncio
import logging
import os
import sys
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, Optional

# 確保可以正確導入 common 模組
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from common.network_monitor import NetworkMonitor, NetworkStatus  # noqa: E402
from common.shared_state import SharedStateManager  # noqa: E402
from common.datetime_utils import utc_now  # noqa: E402
from src.robot_service.queue.interface import Message, MessagePriority  # noqa: E402
from src.robot_service.queue.offline_buffer import OfflineBuffer  # noqa: E402

logger = logging.getLogger(__name__)


class QueueServiceStatus(Enum):
    """佇列服務狀態"""
    AVAILABLE = "available"      # 可用
    UNAVAILABLE = "unavailable"  # 不可用
    CHECKING = "checking"        # 檢查中


class SyncDataType(Enum):
    """同步資料類型"""
    COMMAND_LOG = "command_log"      # 指令執行日誌
    STATUS_UPDATE = "status_update"  # 狀態更新
    EVENT_LOG = "event_log"          # 事件日誌
    TELEMETRY = "telemetry"          # 遙測資料


# 網路佇列發送處理器類型
QueueSendHandler = Callable[[Message], Coroutine[Any, Any, bool]]

# 佇列服務健康檢查處理器類型
QueueHealthCheckHandler = Callable[[], Coroutine[Any, Any, bool]]


class OfflineQueueService:
    """
    離線佇列服務

    功能：
    1. **指令提交**：
       - 在線：指令直接發送到網路佇列服務
       - 離線：指令緩衝到本地 SQLite
       - 恢復：自動將緩衝指令同步到網路佇列

    2. **雲端同步**：
       - 在線：直接同步日誌/狀態到雲端
       - 離線：緩衝到本地
       - 恢復：批次同步
    """

    def __init__(
        self,
        # 離線指令緩衝（SQLite）
        command_buffer: Optional[OfflineBuffer] = None,
        command_buffer_path: Optional[str] = None,
        # 雲端同步緩衝
        sync_buffer: Optional[OfflineBuffer] = None,
        sync_buffer_path: Optional[str] = None,
        # 網路監控
        network_monitor: Optional[NetworkMonitor] = None,
        shared_state: Optional[SharedStateManager] = None,
        # 配置
        auto_flush_on_online: bool = True,
        flush_batch_size: int = 50,
        flush_interval: float = 5.0,
        health_check_interval: float = 10.0,
    ):
        """
        初始化離線佇列服務

        Args:
            command_buffer: 指令緩衝（離線時緩衝指令）
            command_buffer_path: 指令緩衝資料庫路徑
            sync_buffer: 同步緩衝（離線時緩衝日誌/狀態）
            sync_buffer_path: 同步緩衝資料庫路徑
            network_monitor: 網路監控器
            shared_state: 共享狀態管理器
            auto_flush_on_online: 網路恢復時是否自動同步
            flush_batch_size: 批次同步大小
            flush_interval: 同步檢查間隔（秒）
            health_check_interval: 佇列服務健康檢查間隔（秒）
        """
        # 指令緩衝 - 處理網路佇列服務離線
        self._command_buffer = command_buffer or OfflineBuffer(
            db_path=command_buffer_path or ":memory:",
            send_batch_size=flush_batch_size,
        )

        # 雲端同步緩衝 - 處理與雲端的離線
        self._sync_buffer = sync_buffer or OfflineBuffer(
            db_path=sync_buffer_path or ":memory:",
            send_batch_size=flush_batch_size,
        )

        self._network_monitor = network_monitor or NetworkMonitor()
        self._shared_state = shared_state

        self._auto_flush_on_online = auto_flush_on_online
        self._flush_interval = flush_interval
        self._health_check_interval = health_check_interval

        # 佇列服務狀態
        self._queue_service_status = QueueServiceStatus.UNAVAILABLE
        self._queue_send_handler: Optional[QueueSendHandler] = None
        self._queue_health_check_handler: Optional[QueueHealthCheckHandler] = None

        # 雲端同步處理器
        self._cloud_sync_handler: Optional[QueueSendHandler] = None

        self._running = False
        self._flush_task: Optional[asyncio.Task] = None
        self._health_check_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()

        # 統計
        self._stats = {
            "commands_submitted": 0,
            "commands_sent_direct": 0,
            "commands_buffered": 0,
            "commands_flushed": 0,
            "sync_data_sent": 0,
            "sync_data_buffered": 0,
            "sync_data_flushed": 0,
        }

        logger.info("OfflineQueueService initialized", extra={
            "auto_flush_on_online": auto_flush_on_online,
            "flush_interval": flush_interval,
            "health_check_interval": health_check_interval,
            "service": "offline_queue_service"
        })

    # ==================== 屬性 ====================

    @property
    def is_network_online(self) -> bool:
        """網路是否在線（用於雲端同步）"""
        return self._network_monitor.is_online

    @property
    def is_queue_service_available(self) -> bool:
        """網路佇列服務是否可用"""
        return self._queue_service_status == QueueServiceStatus.AVAILABLE

    @property
    def command_buffer(self) -> OfflineBuffer:
        """取得指令緩衝"""
        return self._command_buffer

    @property
    def sync_buffer(self) -> OfflineBuffer:
        """取得同步緩衝"""
        return self._sync_buffer

    @property
    def network_monitor(self) -> NetworkMonitor:
        """取得網路監控器"""
        return self._network_monitor

    # ==================== 配置處理器 ====================

    def set_queue_send_handler(self, handler: QueueSendHandler) -> None:
        """
        設定網路佇列發送處理器

        Args:
            handler: 發送處理函式，用於發送指令到網路佇列服務
        """
        self._queue_send_handler = handler
        self._command_buffer.set_send_handler(handler)

    def set_queue_health_check_handler(self, handler: QueueHealthCheckHandler) -> None:
        """
        設定網路佇列服務健康檢查處理器

        Args:
            handler: 健康檢查函式
        """
        self._queue_health_check_handler = handler

    def set_cloud_sync_handler(self, handler: QueueSendHandler) -> None:
        """
        設定雲端同步處理器

        Args:
            handler: 同步處理函式，用於同步日誌/狀態到雲端
        """
        self._cloud_sync_handler = handler
        self._sync_buffer.set_send_handler(handler)

    # ==================== 生命週期 ====================

    async def start(self) -> None:
        """啟動離線佇列服務"""
        if self._running:
            return

        self._running = True
        self._shutdown_event.clear()

        # 啟動緩衝
        await self._command_buffer.start()
        await self._sync_buffer.start()

        # 設定網路狀態變更回呼
        self._network_monitor.add_callback(self._on_network_status_change)

        # 啟動網路監控
        await self._network_monitor.start()

        # 啟動定期任務
        self._flush_task = asyncio.create_task(self._periodic_flush())
        self._health_check_task = asyncio.create_task(self._periodic_queue_health_check())

        logger.info("OfflineQueueService started", extra={
            "is_network_online": self.is_network_online,
            "is_queue_service_available": self.is_queue_service_available,
            "service": "offline_queue_service"
        })

    async def stop(self) -> None:
        """停止離線佇列服務"""
        if not self._running:
            return

        self._running = False
        self._shutdown_event.set()

        # 停止定期任務
        for task in [self._flush_task, self._health_check_task]:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        self._flush_task = None
        self._health_check_task = None

        # 停止網路監控
        await self._network_monitor.stop()

        # 停止緩衝
        await self._command_buffer.stop()
        await self._sync_buffer.stop()

        logger.info("OfflineQueueService stopped", extra={
            "service": "offline_queue_service"
        })

    # ==================== 指令提交 ====================

    async def submit_command(
        self,
        payload: Dict[str, Any],
        priority: MessagePriority = MessagePriority.NORMAL,
        trace_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        提交指令

        根據佇列服務狀態決定：
        - 可用：直接發送到網路佇列服務
        - 不可用：緩衝到本地 SQLite

        Args:
            payload: 指令內容
            priority: 優先權
            trace_id: 追蹤 ID
            correlation_id: 關聯 ID

        Returns:
            訊息 ID，失敗則返回 None
        """
        message = Message(
            payload=payload,
            priority=priority,
            trace_id=trace_id,
            correlation_id=correlation_id,
        )

        self._stats["commands_submitted"] += 1

        # 嘗試直接發送到網路佇列服務
        if self.is_queue_service_available and self._queue_send_handler:
            try:
                success = await self._queue_send_handler(message)
                if success:
                    self._stats["commands_sent_direct"] += 1

                    logger.info("Command sent to queue service", extra={
                        "message_id": message.id,
                        "trace_id": trace_id,
                        "service": "offline_queue_service"
                    })

                    return message.id
            except Exception as e:
                logger.warning("Failed to send to queue service, buffering", extra={
                    "message_id": message.id,
                    "error": str(e),
                    "service": "offline_queue_service"
                })
                # 標記佇列服務不可用
                await self._set_queue_service_status(QueueServiceStatus.UNAVAILABLE)

        # 佇列服務不可用或發送失敗：緩衝到本地
        success = await self._command_buffer.buffer(message)

        if success:
            self._stats["commands_buffered"] += 1

            logger.info("Command buffered (queue service unavailable)", extra={
                "message_id": message.id,
                "trace_id": trace_id,
                "queue_service_status": self._queue_service_status.value,
                "service": "offline_queue_service"
            })

            # 通知共享狀態
            if self._shared_state:
                await self._shared_state.notify_command_buffered(
                    command_id=message.id,
                    robot_id=payload.get("robot_id", "unknown"),
                    command=str(payload.get("command", "")),
                    source="offline_queue_service",
                )

            return message.id
        else:
            logger.error("Failed to buffer command", extra={
                "message_id": message.id,
                "trace_id": trace_id,
                "service": "offline_queue_service"
            })
            return None

    async def flush_command_buffer(self) -> Dict[str, Any]:
        """
        手動清空指令緩衝（發送到網路佇列服務）

        Returns:
            清空結果統計
        """
        if not self.is_queue_service_available:
            return {"skipped": True, "reason": "queue_service_unavailable"}

        result = await self._command_buffer.flush()
        self._stats["commands_flushed"] += result.get("sent", 0)

        logger.info("Command buffer flushed", extra={
            "result": result,
            "service": "offline_queue_service"
        })

        return result

    # ==================== 雲端同步 ====================

    async def queue_sync_data(
        self,
        data_type: SyncDataType,
        payload: Dict[str, Any],
        priority: int = 1,
    ) -> Optional[str]:
        """
        將資料加入雲端同步佇列

        在線時直接同步，離線時緩衝。

        Args:
            data_type: 資料類型
            payload: 資料內容
            priority: 優先權

        Returns:
            資料 ID，失敗則返回 None
        """
        from uuid import uuid4
        data_id = str(uuid4())

        message = Message(
            id=data_id,
            payload={
                "data_type": data_type.value,
                "data": payload,
            },
            priority=MessagePriority(min(priority, 3)),
        )

        if self.is_network_online and self._cloud_sync_handler:
            # 在線：嘗試直接同步
            try:
                success = await self._cloud_sync_handler(message)
                if success:
                    self._stats["sync_data_sent"] += 1
                    logger.debug("Sync data sent directly", extra={
                        "data_id": data_id,
                        "data_type": data_type.value,
                        "service": "offline_queue_service"
                    })
                    return data_id
            except Exception as e:
                logger.warning("Direct sync failed, buffering", extra={
                    "data_id": data_id,
                    "error": str(e),
                    "service": "offline_queue_service"
                })

        # 離線或直接同步失敗：加入緩衝
        success = await self._sync_buffer.buffer(message)

        if success:
            self._stats["sync_data_buffered"] += 1
            logger.info("Sync data buffered", extra={
                "data_id": data_id,
                "data_type": data_type.value,
                "is_network_online": self.is_network_online,
                "service": "offline_queue_service"
            })
            return data_id
        else:
            logger.error("Failed to buffer sync data", extra={
                "data_id": data_id,
                "service": "offline_queue_service"
            })
            return None

    async def log_command_execution(
        self,
        command_id: str,
        robot_id: str,
        command: str,
        success: bool,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> Optional[str]:
        """
        記錄指令執行結果（用於雲端同步）

        Args:
            command_id: 指令 ID
            robot_id: 機器人 ID
            command: 指令內容
            success: 是否成功
            result: 執行結果
            error: 錯誤訊息

        Returns:
            日誌 ID
        """
        return await self.queue_sync_data(
            data_type=SyncDataType.COMMAND_LOG,
            payload={
                "command_id": command_id,
                "robot_id": robot_id,
                "command": command,
                "success": success,
                "result": result,
                "error": error,
                "executed_at": utc_now().isoformat(),
            },
            priority=2 if not success else 1,  # 失敗優先同步
        )

    async def flush_sync_buffer(self) -> Dict[str, Any]:
        """
        手動清空雲端同步緩衝

        Returns:
            清空結果統計
        """
        if not self.is_network_online:
            return {"skipped": True, "reason": "network_offline"}

        result = await self._sync_buffer.flush()
        self._stats["sync_data_flushed"] += result.get("sent", 0)

        # 通知共享狀態
        if self._shared_state:
            await self._shared_state.notify_buffer_flushed(
                result=result,
                source="offline_queue_service",
            )

        return result

    # ==================== 內部方法 ====================

    async def _set_queue_service_status(self, status: QueueServiceStatus) -> None:
        """設定佇列服務狀態"""
        old_status = self._queue_service_status
        self._queue_service_status = status
        self._command_buffer.set_online(status == QueueServiceStatus.AVAILABLE)

        if old_status != status:
            logger.info("Queue service status changed", extra={
                "old_status": old_status.value,
                "new_status": status.value,
                "service": "offline_queue_service"
            })

            # 狀態變為可用時，嘗試清空緩衝
            if status == QueueServiceStatus.AVAILABLE and self._auto_flush_on_online:
                await self.flush_command_buffer()

    async def _check_queue_service_health(self) -> bool:
        """檢查佇列服務健康狀態"""
        if not self._queue_health_check_handler:
            # 沒有健康檢查處理器，假設可用
            return True

        try:
            return await self._queue_health_check_handler()
        except Exception as e:
            logger.warning("Queue service health check failed", extra={
                "error": str(e),
                "service": "offline_queue_service"
            })
            return False

    async def _periodic_queue_health_check(self) -> None:
        """定期檢查佇列服務健康狀態"""
        while self._running:
            try:
                await asyncio.wait_for(
                    self._shutdown_event.wait(),
                    timeout=self._health_check_interval,
                )
                break  # 收到關閉信號
            except asyncio.TimeoutError:
                if not self._running:
                    break

                is_healthy = await self._check_queue_service_health()

                if is_healthy:
                    await self._set_queue_service_status(QueueServiceStatus.AVAILABLE)
                else:
                    await self._set_queue_service_status(QueueServiceStatus.UNAVAILABLE)

    async def _on_network_status_change(
        self,
        old_status: NetworkStatus,
        new_status: NetworkStatus,
        state: Any,
    ) -> None:
        """網路狀態變更回呼"""
        is_online = new_status == NetworkStatus.ONLINE
        self._sync_buffer.set_online(is_online)

        logger.info("Network status changed", extra={
            "old_status": old_status.value,
            "new_status": new_status.value,
            "is_online": is_online,
            "service": "offline_queue_service"
        })

        # 更新共享狀態
        if self._shared_state:
            await self._shared_state.update_network_status(
                is_online=is_online,
                details=state.to_dict() if hasattr(state, 'to_dict') else {},
                source="offline_queue_service",
            )

        # 網路恢復時嘗試檢查佇列服務並同步
        if is_online:
            # 檢查佇列服務
            is_healthy = await self._check_queue_service_health()
            if is_healthy:
                await self._set_queue_service_status(QueueServiceStatus.AVAILABLE)

            # 同步雲端緩衝
            if self._auto_flush_on_online:
                await self.flush_sync_buffer()

    async def _periodic_flush(self) -> None:
        """定期嘗試同步緩衝資料"""
        while self._running:
            try:
                await asyncio.wait_for(
                    self._shutdown_event.wait(),
                    timeout=self._flush_interval,
                )
                break  # 收到關閉信號
            except asyncio.TimeoutError:
                if not self._running:
                    break

                # 嘗試同步指令緩衝
                if self.is_queue_service_available:
                    command_buffer_size = await self._command_buffer.size()
                    if command_buffer_size > 0:
                        await self.flush_command_buffer()

                # 嘗試同步雲端緩衝
                if self.is_network_online:
                    sync_buffer_size = await self._sync_buffer.size()
                    if sync_buffer_size > 0:
                        await self.flush_sync_buffer()

    # ==================== 統計與健康檢查 ====================

    async def get_statistics(self) -> Dict[str, Any]:
        """
        取得統計資訊

        Returns:
            統計資訊字典
        """
        command_buffer_stats = await self._command_buffer.get_statistics()
        sync_buffer_stats = await self._sync_buffer.get_statistics()
        network_state = self._network_monitor.state.to_dict()

        return {
            "is_network_online": self.is_network_online,
            "is_queue_service_available": self.is_queue_service_available,
            "queue_service_status": self._queue_service_status.value,
            "stats": self._stats.copy(),
            "command_buffer": command_buffer_stats,
            "sync_buffer": sync_buffer_stats,
            "network": network_state,
            "timestamp": utc_now().isoformat(),
        }

    async def health_check(self) -> Dict[str, Any]:
        """
        健康檢查

        Returns:
            健康狀態資訊
        """
        command_buffer_health = await self._command_buffer.health_check()
        sync_buffer_health = await self._sync_buffer.health_check()
        network_health = await self._network_monitor.health_check()

        is_healthy = (
            self._running and
            command_buffer_health.get("status") == "healthy" and
            sync_buffer_health.get("status") == "healthy"
        )

        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "running": self._running,
            "is_network_online": self.is_network_online,
            "is_queue_service_available": self.is_queue_service_available,
            "queue_service_status": self._queue_service_status.value,
            "command_buffer": command_buffer_health,
            "sync_buffer": sync_buffer_health,
            "network": network_health,
            "timestamp": utc_now().isoformat(),
        }
