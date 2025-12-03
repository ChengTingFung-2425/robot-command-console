"""
Shared State Manager
服務間狀態共享管理器

整合 LocalStateStore 和 LocalEventBus，提供：
- 機器人狀態管理
- 指令佇列狀態
- 用戶設定
- 服務健康狀態
- 狀態變更通知
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional

from .datetime_utils import utc_now
from .event_bus import EventHandler, LocalEventBus
from .state_store import LocalStateStore

logger = logging.getLogger(__name__)


# 預定義的狀態鍵前綴
class StateKeys:
    """狀態鍵常數"""
    ROBOT_STATUS = "robot:{robot_id}:status"
    ROBOT_CONFIG = "robot:{robot_id}:config"
    QUEUE_STATUS = "queue:status"
    USER_SETTINGS = "user:settings"
    SERVICE_STATUS = "service:{service_name}:status"
    LLM_PROVIDER = "llm:provider"
    LLM_MODEL = "llm:model"


# 預定義的事件主題
class EventTopics:
    """事件主題常數"""
    ROBOT_STATUS_UPDATED = "robot.status.updated"
    ROBOT_CONNECTED = "robot.connected"
    ROBOT_DISCONNECTED = "robot.disconnected"
    QUEUE_STATUS_UPDATED = "queue.status.updated"
    COMMAND_SUBMITTED = "command.submitted"
    COMMAND_COMPLETED = "command.completed"
    COMMAND_FAILED = "command.failed"
    SERVICE_STARTED = "service.started"
    SERVICE_STOPPED = "service.stopped"
    SERVICE_HEALTH_CHANGED = "service.health.changed"
    USER_SETTINGS_UPDATED = "user.settings.updated"
    LLM_PROVIDER_CHANGED = "llm.provider.changed"


@dataclass
class RobotStatus:
    """機器人狀態"""
    robot_id: str
    connected: bool = False
    battery_level: Optional[float] = None
    mode: str = "standby"
    position: Optional[Dict[str, float]] = None
    last_command: Optional[str] = None
    last_command_at: Optional[datetime] = None
    error: Optional[str] = None
    updated_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "robot_id": self.robot_id,
            "connected": self.connected,
            "battery_level": self.battery_level,
            "mode": self.mode,
            "position": self.position,
            "last_command": self.last_command,
            "last_command_at": self.last_command_at.isoformat() if self.last_command_at else None,
            "error": self.error,
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RobotStatus":
        """從字典建立"""
        return cls(
            robot_id=data["robot_id"],
            connected=data.get("connected", False),
            battery_level=data.get("battery_level"),
            mode=data.get("mode", "standby"),
            position=data.get("position"),
            last_command=data.get("last_command"),
            last_command_at=datetime.fromisoformat(data["last_command_at"]) if data.get("last_command_at") else None,
            error=data.get("error"),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else utc_now(),
        )


@dataclass
class QueueStatus:
    """佇列狀態"""
    pending_count: int = 0
    processing_count: int = 0
    completed_count: int = 0
    failed_count: int = 0
    worker_count: int = 0
    is_running: bool = False
    updated_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "pending_count": self.pending_count,
            "processing_count": self.processing_count,
            "completed_count": self.completed_count,
            "failed_count": self.failed_count,
            "worker_count": self.worker_count,
            "is_running": self.is_running,
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QueueStatus":
        """從字典建立"""
        return cls(
            pending_count=data.get("pending_count", 0),
            processing_count=data.get("processing_count", 0),
            completed_count=data.get("completed_count", 0),
            failed_count=data.get("failed_count", 0),
            worker_count=data.get("worker_count", 0),
            is_running=data.get("is_running", False),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else utc_now(),
        )


class SharedStateManager:
    """
    共享狀態管理器

    管理 MCP、WebUI、Robot-Console 之間的共享狀態：
    - 機器人狀態（由 Robot-Console 更新，WebUI 讀取）
    - 指令佇列狀態（由 MCP 更新，WebUI 顯示）
    - 用戶設定（WebUI 更新，所有服務讀取）
    - 服務健康狀態
    """

    def __init__(
        self,
        db_path: Optional[str] = None,
        history_size: int = 100,
        enable_history: bool = True,
    ):
        """
        初始化共享狀態管理器

        Args:
            db_path: SQLite 資料庫路徑，預設為記憶體資料庫
            history_size: 事件歷史記錄大小
            enable_history: 是否啟用事件歷史
        """
        self._state_store = LocalStateStore(db_path=db_path)
        self._event_bus = LocalEventBus(
            history_size=history_size,
            enable_history=enable_history,
        )
        self._running = False

        logger.info("SharedStateManager initialized", extra={
            "db_path": db_path,
            "history_size": history_size,
            "enable_history": enable_history,
            "service": "shared_state"
        })

    @property
    def state_store(self) -> LocalStateStore:
        """取得狀態存儲"""
        return self._state_store

    @property
    def event_bus(self) -> LocalEventBus:
        """取得事件匯流排"""
        return self._event_bus

    async def start(self) -> None:
        """啟動共享狀態管理器"""
        if self._running:
            return

        await self._state_store.start()
        await self._event_bus.start()
        self._running = True

        logger.info("SharedStateManager started", extra={
            "service": "shared_state"
        })

    async def stop(self) -> None:
        """停止共享狀態管理器"""
        if not self._running:
            return

        self._running = False
        await self._event_bus.stop()
        await self._state_store.stop()

        logger.info("SharedStateManager stopped", extra={
            "service": "shared_state"
        })

    # ==================== 機器人狀態管理 ====================

    async def update_robot_status(
        self,
        robot_id: str,
        status: Dict[str, Any],
        source: Optional[str] = None,
    ) -> bool:
        """
        更新機器人狀態

        Args:
            robot_id: 機器人 ID
            status: 狀態資料
            source: 更新來源

        Returns:
            是否成功更新
        """
        key = StateKeys.ROBOT_STATUS.format(robot_id=robot_id)

        # 合併更新
        existing = await self._state_store.get(key) or {}
        updated = {**existing, **status, "robot_id": robot_id, "updated_at": utc_now().isoformat()}

        success = await self._state_store.set(key, updated)

        if success:
            # 發布事件
            await self._event_bus.publish(
                EventTopics.ROBOT_STATUS_UPDATED,
                {"robot_id": robot_id, "status": updated},
                source=source,
            )

            # 檢查連線狀態變更
            old_connected = existing.get("connected", False)
            new_connected = status.get("connected", old_connected)
            if old_connected != new_connected:
                topic = EventTopics.ROBOT_CONNECTED if new_connected else EventTopics.ROBOT_DISCONNECTED
                await self._event_bus.publish(
                    topic,
                    {"robot_id": robot_id},
                    source=source,
                )

        return success

    async def get_robot_status(self, robot_id: str) -> Optional[RobotStatus]:
        """
        取得機器人狀態

        Args:
            robot_id: 機器人 ID

        Returns:
            機器人狀態
        """
        key = StateKeys.ROBOT_STATUS.format(robot_id=robot_id)
        data = await self._state_store.get(key)
        if data:
            return RobotStatus.from_dict(data)
        return None

    async def get_all_robots_status(self) -> Dict[str, RobotStatus]:
        """
        取得所有機器人狀態

        Returns:
            機器人 ID -> 狀態的字典
        """
        prefix = "robot:"
        all_data = await self._state_store.get_by_prefix(prefix)

        result = {}
        for key, value in all_data.items():
            if ":status" in key and isinstance(value, dict) and "robot_id" in value:
                robot_id = value["robot_id"]
                result[robot_id] = RobotStatus.from_dict(value)

        return result

    # ==================== 佇列狀態管理 ====================

    async def update_queue_status(
        self,
        status: Dict[str, Any],
        source: Optional[str] = None,
    ) -> bool:
        """
        更新佇列狀態

        Args:
            status: 佇列狀態資料
            source: 更新來源

        Returns:
            是否成功更新
        """
        key = StateKeys.QUEUE_STATUS
        status = {**status, "updated_at": utc_now().isoformat()}

        success = await self._state_store.set(key, status)

        if success:
            await self._event_bus.publish(
                EventTopics.QUEUE_STATUS_UPDATED,
                {"status": status},
                source=source,
            )

        return success

    async def get_queue_status(self) -> Optional[QueueStatus]:
        """
        取得佇列狀態

        Returns:
            佇列狀態
        """
        data = await self._state_store.get(StateKeys.QUEUE_STATUS)
        if data:
            return QueueStatus.from_dict(data)
        return None

    # ==================== 用戶設定管理 ====================

    async def update_user_settings(
        self,
        settings: Dict[str, Any],
        source: Optional[str] = None,
    ) -> bool:
        """
        更新用戶設定

        Args:
            settings: 設定資料
            source: 更新來源

        Returns:
            是否成功更新
        """
        key = StateKeys.USER_SETTINGS
        existing = await self._state_store.get(key) or {}
        updated = {**existing, **settings, "updated_at": utc_now().isoformat()}

        success = await self._state_store.set(key, updated)

        if success:
            await self._event_bus.publish(
                EventTopics.USER_SETTINGS_UPDATED,
                {"settings": updated},
                source=source,
            )

        return success

    async def get_user_settings(self) -> Dict[str, Any]:
        """
        取得用戶設定

        Returns:
            用戶設定字典
        """
        return await self._state_store.get(StateKeys.USER_SETTINGS) or {}

    # ==================== 服務狀態管理 ====================

    async def update_service_status(
        self,
        service_name: str,
        status: str,
        details: Optional[Dict[str, Any]] = None,
        source: Optional[str] = None,
    ) -> bool:
        """
        更新服務狀態

        Args:
            service_name: 服務名稱
            status: 狀態值（如 running, stopped, error）
            details: 額外詳細資訊
            source: 更新來源

        Returns:
            是否成功更新
        """
        key = StateKeys.SERVICE_STATUS.format(service_name=service_name)

        data = {
            "service_name": service_name,
            "status": status,
            "details": details or {},
            "updated_at": utc_now().isoformat(),
        }

        # 取得舊狀態以比較
        old_data = await self._state_store.get(key)
        old_status = old_data.get("status") if old_data else None

        success = await self._state_store.set(key, data)

        if success and old_status != status:
            # 發布健康狀態變更事件
            await self._event_bus.publish(
                EventTopics.SERVICE_HEALTH_CHANGED,
                {
                    "service_name": service_name,
                    "old_status": old_status,
                    "new_status": status,
                    "details": details,
                },
                source=source,
            )

            # 發布啟動/停止事件
            if status == "running":
                await self._event_bus.publish(
                    EventTopics.SERVICE_STARTED,
                    {"service_name": service_name},
                    source=source,
                )
            elif status == "stopped":
                await self._event_bus.publish(
                    EventTopics.SERVICE_STOPPED,
                    {"service_name": service_name},
                    source=source,
                )

        return success

    async def get_service_status(self, service_name: str) -> Optional[Dict[str, Any]]:
        """
        取得服務狀態

        Args:
            service_name: 服務名稱

        Returns:
            服務狀態資訊
        """
        key = StateKeys.SERVICE_STATUS.format(service_name=service_name)
        return await self._state_store.get(key)

    async def get_all_services_status(self) -> Dict[str, Dict[str, Any]]:
        """
        取得所有服務狀態

        Returns:
            服務名稱 -> 狀態的字典
        """
        prefix = "service:"
        all_data = await self._state_store.get_by_prefix(prefix)

        result = {}
        for key, value in all_data.items():
            if ":status" in key and isinstance(value, dict) and "service_name" in value:
                service_name = value["service_name"]
                result[service_name] = value

        return result

    # ==================== LLM 提供商管理 ====================

    async def update_llm_provider(
        self,
        provider: str,
        model: Optional[str] = None,
        source: Optional[str] = None,
    ) -> bool:
        """
        更新 LLM 提供商設定

        Args:
            provider: 提供商名稱
            model: 模型名稱
            source: 更新來源

        Returns:
            是否成功更新
        """
        success = await self._state_store.set(StateKeys.LLM_PROVIDER, provider)

        if model:
            await self._state_store.set(StateKeys.LLM_MODEL, model)

        if success:
            await self._event_bus.publish(
                EventTopics.LLM_PROVIDER_CHANGED,
                {"provider": provider, "model": model},
                source=source,
            )

        return success

    async def get_llm_provider(self) -> Optional[str]:
        """取得當前 LLM 提供商"""
        return await self._state_store.get(StateKeys.LLM_PROVIDER)

    async def get_llm_model(self) -> Optional[str]:
        """取得當前 LLM 模型"""
        return await self._state_store.get(StateKeys.LLM_MODEL)

    # ==================== 指令事件 ====================

    async def notify_command_submitted(
        self,
        command_id: str,
        robot_id: str,
        command: str,
        source: Optional[str] = None,
    ) -> None:
        """
        通知指令已提交

        Args:
            command_id: 指令 ID
            robot_id: 目標機器人 ID
            command: 指令內容
            source: 來源
        """
        await self._event_bus.publish(
            EventTopics.COMMAND_SUBMITTED,
            {
                "command_id": command_id,
                "robot_id": robot_id,
                "command": command,
                "timestamp": utc_now().isoformat(),
            },
            source=source,
        )

    async def notify_command_completed(
        self,
        command_id: str,
        robot_id: str,
        result: Optional[Dict[str, Any]] = None,
        source: Optional[str] = None,
    ) -> None:
        """
        通知指令已完成

        Args:
            command_id: 指令 ID
            robot_id: 目標機器人 ID
            result: 執行結果
            source: 來源
        """
        await self._event_bus.publish(
            EventTopics.COMMAND_COMPLETED,
            {
                "command_id": command_id,
                "robot_id": robot_id,
                "result": result,
                "timestamp": utc_now().isoformat(),
            },
            source=source,
        )

    async def notify_command_failed(
        self,
        command_id: str,
        robot_id: str,
        error: str,
        source: Optional[str] = None,
    ) -> None:
        """
        通知指令失敗

        Args:
            command_id: 指令 ID
            robot_id: 目標機器人 ID
            error: 錯誤訊息
            source: 來源
        """
        await self._event_bus.publish(
            EventTopics.COMMAND_FAILED,
            {
                "command_id": command_id,
                "robot_id": robot_id,
                "error": error,
                "timestamp": utc_now().isoformat(),
            },
            source=source,
        )

    # ==================== 訂閱管理 ====================

    async def subscribe(
        self,
        pattern: str,
        handler: EventHandler,
    ) -> str:
        """
        訂閱事件

        Args:
            pattern: 事件主題模式
            handler: 事件處理器

        Returns:
            訂閱 ID
        """
        return await self._event_bus.subscribe(pattern, handler)

    async def unsubscribe(self, subscription_id: str) -> bool:
        """
        取消訂閱

        Args:
            subscription_id: 訂閱 ID

        Returns:
            是否成功取消
        """
        return await self._event_bus.unsubscribe(subscription_id)

    # ==================== 健康檢查 ====================

    async def health_check(self) -> Dict[str, Any]:
        """
        健康檢查

        Returns:
            健康狀態資訊
        """
        store_health = await self._state_store.health_check()
        bus_health = await self._event_bus.health_check()

        is_healthy = (
            store_health.get("status") == "healthy"
            and bus_health.get("status") in ["healthy", "stopped"]
        )

        return {
            "status": "healthy" if (self._running and is_healthy) else "unhealthy",
            "running": self._running,
            "state_store": store_health,
            "event_bus": bus_health,
            "timestamp": utc_now().isoformat(),
        }
