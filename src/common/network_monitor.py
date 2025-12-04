"""
Network Monitor
網路連線狀態監控模組

提供：
- 網路連線狀態檢測
- 離線/上線事件發布
- 多端點彈性檢查
- 定期連線監控
"""

import asyncio
import logging
import socket
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional

from .datetime_utils import utc_now

logger = logging.getLogger(__name__)


class NetworkStatus(Enum):
    """網路狀態"""
    ONLINE = "online"
    OFFLINE = "offline"
    CHECKING = "checking"
    UNKNOWN = "unknown"


@dataclass
class NetworkState:
    """網路狀態資訊"""
    status: NetworkStatus = NetworkStatus.UNKNOWN
    last_check_at: Optional[datetime] = None
    last_online_at: Optional[datetime] = None
    last_offline_at: Optional[datetime] = None
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    latency_ms: Optional[float] = None
    checked_endpoint: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "status": self.status.value,
            "last_check_at": self.last_check_at.isoformat() if self.last_check_at else None,
            "last_online_at": self.last_online_at.isoformat() if self.last_online_at else None,
            "last_offline_at": self.last_offline_at.isoformat() if self.last_offline_at else None,
            "consecutive_failures": self.consecutive_failures,
            "consecutive_successes": self.consecutive_successes,
            "latency_ms": self.latency_ms,
            "checked_endpoint": self.checked_endpoint,
        }


# 網路狀態變更回呼類型
NetworkStatusCallback = Callable[
    [NetworkStatus, NetworkStatus, NetworkState],
    Coroutine[Any, Any, None]
]


class NetworkMonitor:
    """
    網路連線監控器

    功能：
    - 定期檢查網路連線狀態
    - 支援多個備用檢測端點
    - 狀態變更時發送通知
    - 記錄連線統計資訊
    """

    # 預設檢測端點（考慮不同網路環境）
    DEFAULT_CHECK_ENDPOINTS = [
        "https://www.google.com",
        "https://www.cloudflare.com",
        "https://1.1.1.1",
        "https://www.baidu.com",  # 中國大陸備用
    ]

    def __init__(
        self,
        check_endpoints: Optional[List[str]] = None,
        check_interval: float = 30.0,
        timeout: float = 5.0,
        failure_threshold: int = 2,
        recovery_threshold: int = 1,
    ):
        """
        初始化網路監控器

        Args:
            check_endpoints: 檢測端點列表，預設使用 DEFAULT_CHECK_ENDPOINTS
            check_interval: 檢測間隔（秒）
            timeout: 單個端點檢測超時（秒）
            failure_threshold: 連續失敗多少次判定為離線
            recovery_threshold: 連續成功多少次判定為恢復上線
        """
        self._check_endpoints = check_endpoints or self.DEFAULT_CHECK_ENDPOINTS
        self._check_interval = check_interval
        self._timeout = timeout
        self._failure_threshold = failure_threshold
        self._recovery_threshold = recovery_threshold

        self._state = NetworkState()
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        self._callbacks: List[NetworkStatusCallback] = []

        logger.info("NetworkMonitor initialized", extra={
            "check_interval": check_interval,
            "timeout": timeout,
            "failure_threshold": failure_threshold,
            "recovery_threshold": recovery_threshold,
            "endpoints_count": len(self._check_endpoints),
            "service": "network_monitor"
        })

    @property
    def status(self) -> NetworkStatus:
        """取得當前網路狀態"""
        return self._state.status

    @property
    def is_online(self) -> bool:
        """是否在線"""
        return self._state.status == NetworkStatus.ONLINE

    @property
    def state(self) -> NetworkState:
        """取得完整網路狀態資訊"""
        return self._state

    def add_callback(self, callback: NetworkStatusCallback) -> None:
        """
        添加狀態變更回呼

        Args:
            callback: 狀態變更時呼叫的非同步函式
        """
        self._callbacks.append(callback)

    def remove_callback(self, callback: NetworkStatusCallback) -> None:
        """
        移除狀態變更回呼

        Args:
            callback: 要移除的回呼函式
        """
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    async def start(self) -> None:
        """啟動網路監控"""
        if self._running:
            return

        self._running = True
        self._shutdown_event.clear()

        # 執行初始檢查
        await self.check_connection()

        # 啟動定期檢查任務
        self._monitor_task = asyncio.create_task(self._periodic_check())

        logger.info("NetworkMonitor started", extra={
            "initial_status": self._state.status.value,
            "service": "network_monitor"
        })

    async def stop(self) -> None:
        """停止網路監控"""
        if not self._running:
            return

        self._running = False
        self._shutdown_event.set()

        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None

        logger.info("NetworkMonitor stopped", extra={
            "service": "network_monitor"
        })

    async def check_connection(self) -> bool:
        """
        立即檢查網路連線

        Returns:
            是否連線成功
        """
        old_status = self._state.status
        self._state.status = NetworkStatus.CHECKING
        self._state.last_check_at = utc_now()

        is_connected = False
        latency_ms: Optional[float] = None
        checked_endpoint: Optional[str] = None

        for endpoint in self._check_endpoints:
            try:
                start_time = asyncio.get_event_loop().time()
                is_connected = await self._check_endpoint(endpoint)
                end_time = asyncio.get_event_loop().time()

                if is_connected:
                    latency_ms = (end_time - start_time) * 1000
                    checked_endpoint = endpoint
                    break
            except Exception as e:
                logger.debug(f"Failed to check endpoint {endpoint}: {e}", extra={
                    "endpoint": endpoint,
                    "error": str(e),
                    "service": "network_monitor"
                })

        self._state.latency_ms = latency_ms
        self._state.checked_endpoint = checked_endpoint

        if is_connected:
            self._state.consecutive_successes += 1
            self._state.consecutive_failures = 0

            if (old_status != NetworkStatus.ONLINE and
                    self._state.consecutive_successes >= self._recovery_threshold):
                self._state.status = NetworkStatus.ONLINE
                self._state.last_online_at = utc_now()
                await self._notify_status_change(old_status, NetworkStatus.ONLINE)
            elif old_status == NetworkStatus.ONLINE:
                self._state.status = NetworkStatus.ONLINE
            else:
                # 還未達到恢復閾值
                self._state.status = old_status if old_status != NetworkStatus.CHECKING else NetworkStatus.UNKNOWN

            logger.debug("Network check succeeded", extra={
                "endpoint": checked_endpoint,
                "latency_ms": latency_ms,
                "consecutive_successes": self._state.consecutive_successes,
                "service": "network_monitor"
            })
        else:
            self._state.consecutive_failures += 1
            self._state.consecutive_successes = 0

            if (old_status != NetworkStatus.OFFLINE and
                    self._state.consecutive_failures >= self._failure_threshold):
                self._state.status = NetworkStatus.OFFLINE
                self._state.last_offline_at = utc_now()
                await self._notify_status_change(old_status, NetworkStatus.OFFLINE)
            elif old_status == NetworkStatus.OFFLINE:
                self._state.status = NetworkStatus.OFFLINE
            else:
                # 還未達到離線閾值
                self._state.status = old_status if old_status != NetworkStatus.CHECKING else NetworkStatus.UNKNOWN

            logger.warning("Network check failed", extra={
                "consecutive_failures": self._state.consecutive_failures,
                "service": "network_monitor"
            })

        return is_connected

    async def _check_endpoint(self, endpoint: str) -> bool:
        """
        檢查單個端點

        Args:
            endpoint: 要檢查的 URL

        Returns:
            是否可連線
        """
        loop = asyncio.get_event_loop()

        def _do_check():
            try:
                # 使用 socket 進行快速連線檢查
                if endpoint.startswith("https://"):
                    host = endpoint.replace("https://", "").split("/")[0]
                    port = 443
                elif endpoint.startswith("http://"):
                    host = endpoint.replace("http://", "").split("/")[0]
                    port = 80
                else:
                    host = endpoint.split("/")[0]
                    port = 80

                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(self._timeout)
                try:
                    sock.connect((host, port))
                    return True
                finally:
                    sock.close()
            except (socket.timeout, socket.error, OSError):
                return False

        try:
            return await asyncio.wait_for(
                loop.run_in_executor(None, _do_check),
                timeout=self._timeout + 1
            )
        except asyncio.TimeoutError:
            return False

    async def _periodic_check(self) -> None:
        """定期檢查網路連線"""
        while self._running:
            try:
                await asyncio.wait_for(
                    self._shutdown_event.wait(),
                    timeout=self._check_interval,
                )
                break  # 收到關閉信號
            except asyncio.TimeoutError:
                # 正常超時，執行檢查
                if not self._running:
                    break
                await self.check_connection()

    async def _notify_status_change(
        self,
        old_status: NetworkStatus,
        new_status: NetworkStatus,
    ) -> None:
        """通知狀態變更"""
        logger.info("Network status changed", extra={
            "old_status": old_status.value,
            "new_status": new_status.value,
            "service": "network_monitor"
        })

        for callback in self._callbacks:
            try:
                await callback(old_status, new_status, self._state)
            except Exception as e:
                logger.error("Error in network status callback", extra={
                    "error": str(e),
                    "service": "network_monitor"
                })

    async def health_check(self) -> Dict[str, Any]:
        """
        健康檢查

        Returns:
            健康狀態資訊
        """
        return {
            "status": "healthy" if self._running else "stopped",
            "running": self._running,
            "network_state": self._state.to_dict(),
            "check_interval": self._check_interval,
            "timeout": self._timeout,
            "endpoints_count": len(self._check_endpoints),
            "timestamp": utc_now().isoformat(),
        }


# 全域網路監控器實例
_global_network_monitor: Optional[NetworkMonitor] = None


def get_network_monitor() -> NetworkMonitor:
    """
    取得全域網路監控器實例

    Returns:
        NetworkMonitor 實例
    """
    global _global_network_monitor
    if _global_network_monitor is None:
        _global_network_monitor = NetworkMonitor()
    return _global_network_monitor


def reset_network_monitor() -> None:
    """重置全域網路監控器（用於測試）"""
    global _global_network_monitor
    _global_network_monitor = None
