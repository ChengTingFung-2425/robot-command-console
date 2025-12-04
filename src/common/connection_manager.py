"""
Connection Manager
服務連線管理器

提供：
- 服務斷線檢測
- 自動重連機制
- 指數退避策略
- 連線狀態追蹤
"""

import asyncio
import logging
import random
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional

from .datetime_utils import utc_now

logger = logging.getLogger(__name__)


class ConnectionStatus(Enum):
    """連線狀態"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


@dataclass
class ConnectionState:
    """連線狀態資訊"""
    status: ConnectionStatus = ConnectionStatus.DISCONNECTED
    endpoint: Optional[str] = None
    last_connected_at: Optional[datetime] = None
    last_disconnected_at: Optional[datetime] = None
    reconnect_attempts: int = 0
    total_reconnects: int = 0
    last_error: Optional[str] = None
    latency_ms: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "status": self.status.value,
            "endpoint": self.endpoint,
            "last_connected_at": self.last_connected_at.isoformat() if self.last_connected_at else None,
            "last_disconnected_at": self.last_disconnected_at.isoformat() if self.last_disconnected_at else None,
            "reconnect_attempts": self.reconnect_attempts,
            "total_reconnects": self.total_reconnects,
            "last_error": self.last_error,
            "latency_ms": self.latency_ms,
        }


# 連線處理器類型
ConnectHandler = Callable[[], Coroutine[Any, Any, bool]]
DisconnectHandler = Callable[[], Coroutine[Any, Any, None]]
HealthCheckHandler = Callable[[], Coroutine[Any, Any, bool]]

# 狀態變更回呼類型
ConnectionStatusCallback = Callable[
    [ConnectionStatus, ConnectionStatus, ConnectionState],
    Coroutine[Any, Any, None]
]


class ConnectionManager:
    """
    服務連線管理器

    功能：
    - 管理與遠端服務的連線
    - 自動檢測斷線
    - 使用指數退避策略自動重連
    - 追蹤連線統計資訊
    """

    def __init__(
        self,
        name: str,
        endpoint: Optional[str] = None,
        health_check_interval: float = 30.0,
        reconnect_enabled: bool = True,
        max_reconnect_attempts: int = 10,
        initial_reconnect_delay: float = 1.0,
        max_reconnect_delay: float = 60.0,
        reconnect_jitter: float = 0.1,
    ):
        """
        初始化連線管理器

        Args:
            name: 連線名稱（用於日誌和識別）
            endpoint: 連線端點
            health_check_interval: 健康檢查間隔（秒）
            reconnect_enabled: 是否啟用自動重連
            max_reconnect_attempts: 最大重連嘗試次數（0 表示無限）
            initial_reconnect_delay: 初始重連延遲（秒）
            max_reconnect_delay: 最大重連延遲（秒）
            reconnect_jitter: 重連延遲抖動比例（0-1）
        """
        self._name = name
        self._health_check_interval = health_check_interval
        self._reconnect_enabled = reconnect_enabled
        self._max_reconnect_attempts = max_reconnect_attempts
        self._initial_reconnect_delay = initial_reconnect_delay
        self._max_reconnect_delay = max_reconnect_delay
        self._reconnect_jitter = reconnect_jitter

        self._state = ConnectionState(endpoint=endpoint)
        self._running = False
        self._health_check_task: Optional[asyncio.Task] = None
        self._reconnect_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()

        # 處理器
        self._connect_handler: Optional[ConnectHandler] = None
        self._disconnect_handler: Optional[DisconnectHandler] = None
        self._health_check_handler: Optional[HealthCheckHandler] = None

        # 回呼
        self._callbacks: List[ConnectionStatusCallback] = []

        logger.info("ConnectionManager initialized", extra={
            "connection_name": name,
            "endpoint": endpoint,
            "health_check_interval": health_check_interval,
            "reconnect_enabled": reconnect_enabled,
            "max_reconnect_attempts": max_reconnect_attempts,
            "service": "connection_manager"
        })

    @property
    def name(self) -> str:
        """取得連線名稱"""
        return self._name

    @property
    def status(self) -> ConnectionStatus:
        """取得當前連線狀態"""
        return self._state.status

    @property
    def is_connected(self) -> bool:
        """是否已連線"""
        return self._state.status == ConnectionStatus.CONNECTED

    @property
    def state(self) -> ConnectionState:
        """取得完整連線狀態"""
        return self._state

    def set_connect_handler(self, handler: ConnectHandler) -> None:
        """設定連線處理器"""
        self._connect_handler = handler

    def set_disconnect_handler(self, handler: DisconnectHandler) -> None:
        """設定斷線處理器"""
        self._disconnect_handler = handler

    def set_health_check_handler(self, handler: HealthCheckHandler) -> None:
        """設定健康檢查處理器"""
        self._health_check_handler = handler

    def add_callback(self, callback: ConnectionStatusCallback) -> None:
        """添加狀態變更回呼"""
        self._callbacks.append(callback)

    def remove_callback(self, callback: ConnectionStatusCallback) -> None:
        """移除狀態變更回呼"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    async def start(self) -> None:
        """啟動連線管理器"""
        if self._running:
            return

        self._running = True
        self._shutdown_event.clear()

        logger.info("ConnectionManager started", extra={
            "connection_name": self._name,
            "service": "connection_manager"
        })

    async def stop(self) -> None:
        """停止連線管理器"""
        if not self._running:
            return

        self._running = False
        self._shutdown_event.set()

        # 取消健康檢查任務
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
            self._health_check_task = None

        # 取消重連任務
        if self._reconnect_task:
            self._reconnect_task.cancel()
            try:
                await self._reconnect_task
            except asyncio.CancelledError:
                pass
            self._reconnect_task = None

        # 斷開連線
        if self._state.status == ConnectionStatus.CONNECTED:
            await self.disconnect()

        logger.info("ConnectionManager stopped", extra={
            "connection_name": self._name,
            "service": "connection_manager"
        })

    async def connect(self) -> bool:
        """
        建立連線

        Returns:
            是否成功連線
        """
        if self._state.status == ConnectionStatus.CONNECTED:
            return True

        if not self._connect_handler:
            logger.warning("No connect handler configured", extra={
                "connection_name": self._name,
                "service": "connection_manager"
            })
            return False

        old_status = self._state.status
        self._state.status = ConnectionStatus.CONNECTING

        logger.info("Connecting", extra={
            "connection_name": self._name,
            "endpoint": self._state.endpoint,
            "service": "connection_manager"
        })

        try:
            start_time = asyncio.get_event_loop().time()
            success = await self._connect_handler()
            end_time = asyncio.get_event_loop().time()

            if success:
                self._state.status = ConnectionStatus.CONNECTED
                self._state.last_connected_at = utc_now()
                self._state.reconnect_attempts = 0
                self._state.last_error = None
                self._state.latency_ms = (end_time - start_time) * 1000

                await self._notify_status_change(old_status, ConnectionStatus.CONNECTED)

                # 啟動健康檢查
                if self._health_check_handler and not self._health_check_task:
                    self._health_check_task = asyncio.create_task(
                        self._periodic_health_check()
                    )

                logger.info("Connected successfully", extra={
                    "connection_name": self._name,
                    "latency_ms": self._state.latency_ms,
                    "service": "connection_manager"
                })

                return True
            else:
                self._state.status = ConnectionStatus.DISCONNECTED
                self._state.last_error = "Connect returned false"
                await self._notify_status_change(old_status, ConnectionStatus.DISCONNECTED)

                logger.warning("Connection failed", extra={
                    "connection_name": self._name,
                    "service": "connection_manager"
                })

                return False

        except Exception as e:
            self._state.status = ConnectionStatus.DISCONNECTED
            self._state.last_error = str(e)
            await self._notify_status_change(old_status, ConnectionStatus.DISCONNECTED)

            logger.error("Connection error", extra={
                "connection_name": self._name,
                "error": str(e),
                "service": "connection_manager"
            })

            return False

    async def disconnect(self) -> None:
        """斷開連線"""
        if self._state.status == ConnectionStatus.DISCONNECTED:
            return

        old_status = self._state.status

        # 停止健康檢查
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
            self._health_check_task = None

        if self._disconnect_handler:
            try:
                await self._disconnect_handler()
            except Exception as e:
                logger.error("Disconnect error", extra={
                    "connection_name": self._name,
                    "error": str(e),
                    "service": "connection_manager"
                })

        self._state.status = ConnectionStatus.DISCONNECTED
        self._state.last_disconnected_at = utc_now()

        await self._notify_status_change(old_status, ConnectionStatus.DISCONNECTED)

        logger.info("Disconnected", extra={
            "connection_name": self._name,
            "service": "connection_manager"
        })

    async def reconnect(self) -> bool:
        """
        重新連線

        Returns:
            是否成功重連
        """
        if self._state.status == ConnectionStatus.CONNECTED:
            return True

        if not self._reconnect_enabled:
            logger.debug("Reconnect disabled", extra={
                "connection_name": self._name,
                "service": "connection_manager"
            })
            return False

        # 檢查重連次數限制
        if (self._max_reconnect_attempts > 0 and
                self._state.reconnect_attempts >= self._max_reconnect_attempts):
            old_status = self._state.status
            self._state.status = ConnectionStatus.FAILED
            await self._notify_status_change(old_status, ConnectionStatus.FAILED)

            logger.error("Max reconnect attempts reached", extra={
                "connection_name": self._name,
                "attempts": self._state.reconnect_attempts,
                "max_attempts": self._max_reconnect_attempts,
                "service": "connection_manager"
            })

            return False

        old_status = self._state.status
        self._state.status = ConnectionStatus.RECONNECTING
        self._state.reconnect_attempts += 1

        # 計算指數退避延遲
        delay = self._calculate_reconnect_delay()

        logger.info("Reconnecting", extra={
            "connection_name": self._name,
            "attempt": self._state.reconnect_attempts,
            "delay_seconds": delay,
            "service": "connection_manager"
        })

        await asyncio.sleep(delay)

        # 檢查是否已關閉
        if not self._running or self._shutdown_event.is_set():
            return False

        success = await self.connect()

        if success:
            self._state.total_reconnects += 1

            logger.info("Reconnected successfully", extra={
                "connection_name": self._name,
                "attempts": self._state.reconnect_attempts,
                "total_reconnects": self._state.total_reconnects,
                "service": "connection_manager"
            })
        else:
            logger.warning("Reconnect attempt failed", extra={
                "connection_name": self._name,
                "attempt": self._state.reconnect_attempts,
                "service": "connection_manager"
            })

        return success

    def _calculate_reconnect_delay(self) -> float:
        """
        計算重連延遲（指數退避 + 隨機抖動）

        Returns:
            延遲秒數
        """
        # 指數退避: initial_delay * 2^(attempts-1)
        delay = self._initial_reconnect_delay * (2 ** (self._state.reconnect_attempts - 1))

        # 限制最大延遲
        delay = min(delay, self._max_reconnect_delay)

        # 添加隨機抖動
        jitter = delay * self._reconnect_jitter
        delay = delay + random.uniform(-jitter, jitter)

        return max(0.1, delay)  # 最少 0.1 秒

    async def _periodic_health_check(self) -> None:
        """定期健康檢查"""
        while self._running and self._state.status == ConnectionStatus.CONNECTED:
            try:
                await asyncio.wait_for(
                    self._shutdown_event.wait(),
                    timeout=self._health_check_interval,
                )
                break  # 收到關閉信號
            except asyncio.TimeoutError:
                # 正常超時，執行檢查
                if not self._running:
                    break

                if self._health_check_handler:
                    try:
                        is_healthy = await self._health_check_handler()

                        if not is_healthy:
                            logger.warning("Health check failed", extra={
                                "connection_name": self._name,
                                "service": "connection_manager"
                            })

                            # 標記斷線
                            old_status = self._state.status
                            self._state.status = ConnectionStatus.DISCONNECTED
                            self._state.last_disconnected_at = utc_now()
                            await self._notify_status_change(old_status, ConnectionStatus.DISCONNECTED)

                            # 觸發重連
                            if self._reconnect_enabled:
                                self._reconnect_task = asyncio.create_task(
                                    self._auto_reconnect()
                                )

                            break

                    except Exception as e:
                        logger.error("Health check error", extra={
                            "connection_name": self._name,
                            "error": str(e),
                            "service": "connection_manager"
                        })

                        # 視為斷線
                        old_status = self._state.status
                        self._state.status = ConnectionStatus.DISCONNECTED
                        self._state.last_disconnected_at = utc_now()
                        self._state.last_error = str(e)
                        await self._notify_status_change(old_status, ConnectionStatus.DISCONNECTED)

                        if self._reconnect_enabled:
                            self._reconnect_task = asyncio.create_task(
                                self._auto_reconnect()
                            )

                        break

    async def _auto_reconnect(self) -> None:
        """自動重連循環"""
        while (self._running and
               self._state.status not in [ConnectionStatus.CONNECTED, ConnectionStatus.FAILED]):
            success = await self.reconnect()

            if success:
                break

            if self._state.status == ConnectionStatus.FAILED:
                break

            if self._shutdown_event.is_set():
                break

    async def _notify_status_change(
        self,
        old_status: ConnectionStatus,
        new_status: ConnectionStatus,
    ) -> None:
        """通知狀態變更"""
        if old_status == new_status:
            return

        logger.info("Connection status changed", extra={
            "connection_name": self._name,
            "old_status": old_status.value,
            "new_status": new_status.value,
            "service": "connection_manager"
        })

        for callback in self._callbacks:
            try:
                await callback(old_status, new_status, self._state)
            except Exception as e:
                logger.error("Error in connection status callback", extra={
                    "connection_name": self._name,
                    "error": str(e),
                    "service": "connection_manager"
                })

    async def health_check(self) -> Dict[str, Any]:
        """
        健康檢查

        Returns:
            健康狀態資訊
        """
        is_healthy = (
            self._running and
            self._state.status == ConnectionStatus.CONNECTED
        )

        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "running": self._running,
            "connection_state": self._state.to_dict(),
            "reconnect_enabled": self._reconnect_enabled,
            "health_check_interval": self._health_check_interval,
            "timestamp": utc_now().isoformat(),
        }


class ConnectionPool:
    """
    連線池

    管理多個連線管理器
    """

    def __init__(self):
        """初始化連線池"""
        self._connections: Dict[str, ConnectionManager] = {}

    def add(self, connection: ConnectionManager) -> None:
        """添加連線管理器"""
        self._connections[connection.name] = connection

    def remove(self, name: str) -> Optional[ConnectionManager]:
        """移除連線管理器"""
        return self._connections.pop(name, None)

    def get(self, name: str) -> Optional[ConnectionManager]:
        """取得連線管理器"""
        return self._connections.get(name)

    def get_all(self) -> Dict[str, ConnectionManager]:
        """取得所有連線管理器"""
        return self._connections.copy()

    async def start_all(self) -> Dict[str, bool]:
        """啟動所有連線管理器"""
        results = {}
        for name, conn in self._connections.items():
            try:
                await conn.start()
                results[name] = True
            except Exception as e:
                logger.error("Failed to start connection", extra={
                    "connection_name": name,
                    "error": str(e),
                    "service": "connection_pool"
                })
                results[name] = False
        return results

    async def stop_all(self) -> Dict[str, bool]:
        """停止所有連線管理器"""
        results = {}
        for name, conn in self._connections.items():
            try:
                await conn.stop()
                results[name] = True
            except Exception as e:
                logger.error("Failed to stop connection", extra={
                    "connection_name": name,
                    "error": str(e),
                    "service": "connection_pool"
                })
                results[name] = False
        return results

    async def connect_all(self) -> Dict[str, bool]:
        """連接所有"""
        results = {}
        for name, conn in self._connections.items():
            try:
                results[name] = await conn.connect()
            except Exception as e:
                logger.error("Failed to connect", extra={
                    "connection_name": name,
                    "error": str(e),
                    "service": "connection_pool"
                })
                results[name] = False
        return results

    async def disconnect_all(self) -> None:
        """斷開所有連線"""
        for name, conn in self._connections.items():
            try:
                await conn.disconnect()
            except Exception as e:
                logger.error("Failed to disconnect", extra={
                    "connection_name": name,
                    "error": str(e),
                    "service": "connection_pool"
                })

    async def health_check_all(self) -> Dict[str, Dict[str, Any]]:
        """健康檢查所有連線"""
        results = {}
        for name, conn in self._connections.items():
            try:
                results[name] = await conn.health_check()
            except Exception as e:
                results[name] = {
                    "status": "error",
                    "error": str(e),
                    "timestamp": utc_now().isoformat(),
                }
        return results

    def get_connected_count(self) -> int:
        """取得已連線數量"""
        return sum(1 for c in self._connections.values() if c.is_connected)

    def get_disconnected_count(self) -> int:
        """取得未連線數量"""
        return sum(1 for c in self._connections.values() if not c.is_connected)
