"""
Service Coordinator
服務協調器，負責啟動、停止、健康檢查多個服務
"""

import asyncio
import logging
import os
import sys
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine, Dict, Optional

# 從 common 模組導入共用服務類型
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from common.service_types import ServiceStatus, ServiceConfig, ServiceState  # noqa: E402

from .service_manager import ServiceManager  # noqa: E402

# 明確重新導出 common 模組的類型，確保向後相容
__all__ = [
    "ServiceBase",
    "ServiceCoordinator",
    "QueueService",
    # 從 common 重新導出，保持向後相容
    "ServiceStatus",
    "ServiceConfig",
    "ServiceState",
]


logger = logging.getLogger(__name__)


class ServiceBase(ABC):
    """
    服務基礎類別

    所有需要被協調器管理的服務都應實作此介面
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        服務名稱

        Returns:
            str: 服務的唯一名稱
        """
        pass

    @abstractmethod
    async def start(self) -> bool:
        """
        啟動服務

        Returns:
            bool: True 表示啟動成功，False 表示啟動失敗

        Raises:
            Exception: 啟動過程中發生的任何異常，應由實作類別處理
        """
        pass

    @abstractmethod
    async def stop(self, timeout: Optional[float] = None) -> bool:
        """
        停止服務

        Args:
            timeout (Optional[float]): 停止操作的超時秒數，若為 None 則不限時

        Returns:
            bool: True 表示停止成功，False 表示停止失敗或超時

        Raises:
            Exception: 停止過程中發生的任何異常，應由實作類別處理
        """
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """
        健康檢查

        Returns:
            Dict[str, Any]: 健康檢查結果，應包含 "status" 鍵與相關訊息

        Raises:
            Exception: 健康檢查過程中發生的任何異常，應由實作類別處理
        """
        pass

    @property
    @abstractmethod
    def is_running(self) -> bool:
        """
        服務是否運行中

        Returns:
            bool: True 表示服務正在運行，False 表示未運行
        """
        pass


class QueueService(ServiceBase):
    """
    佇列服務封裝

    將 ServiceManager 封裝為符合 ServiceBase 介面的服務
    """

    def __init__(
        self,
        queue_max_size: Optional[int] = None,
        max_workers: int = 5,
        poll_interval: float = 0.1,
    ):
        """初始化佇列服務"""
        self._manager = ServiceManager(
            queue_max_size=queue_max_size,
            max_workers=max_workers,
            poll_interval=poll_interval,
        )
        self._running = False

    @property
    def name(self) -> str:
        """服務名稱"""
        return "queue_service"

    @property
    def manager(self) -> ServiceManager:
        """取得內部的 ServiceManager 實例"""
        return self._manager

    async def start(self) -> bool:
        """啟動服務"""
        try:
            await self._manager.start()
            self._running = True
            return True
        except Exception as e:
            logger.error("Failed to start queue service", extra={
                "error": str(e),
                "service": self.name
            })
            return False

    async def stop(self, timeout: Optional[float] = None) -> bool:
        """停止服務"""
        try:
            await self._manager.stop(timeout=timeout or 30.0)
            self._running = False
            return True
        except Exception as e:
            logger.error("Failed to stop queue service", extra={
                "error": str(e),
                "service": self.name
            })
            return False

    async def health_check(self) -> Dict[str, Any]:
        """健康檢查"""
        return await self._manager.health_check()

    @property
    def is_running(self) -> bool:
        """服務是否運行中"""
        return self._running


class ServiceCoordinator:
    """
    服務協調器

    負責：
    - 管理多個服務的生命週期
    - 啟動與停止服務
    - 定期健康檢查
    - 自動重啟失敗的服務
    - 提供統一的狀態查詢介面
    - 非同步狀態變更通知
    """

    def __init__(
        self,
        health_check_interval: float = 30.0,
        max_restart_attempts: int = 3,
        restart_delay: float = 2.0,
        alert_threshold: int = 3,
    ):
        """
        初始化服務協調器

        Args:
            health_check_interval: 健康檢查間隔（秒）
            max_restart_attempts: 最大重啟嘗試次數
            restart_delay: 重啟延遲（秒）
            alert_threshold: 連續失敗達到此閾值時發送告警
        """
        self._services: Dict[str, ServiceBase] = {}
        self._states: Dict[str, ServiceState] = {}
        self._health_check_interval = health_check_interval
        self._max_restart_attempts = max_restart_attempts
        self._restart_delay = restart_delay
        self._alert_threshold = alert_threshold
        self._health_check_task: Optional[asyncio.Task] = None
        self._running = False
        self._shutdown_event = asyncio.Event()
        self._alert_callback: Optional[Callable[[str, str, Dict], Coroutine]] = None
        # 非同步狀態變更回呼
        self._state_change_callback: Optional[
            Callable[[str, ServiceStatus, ServiceStatus, ServiceState], Coroutine]
        ] = None

        logger.info("ServiceCoordinator initialized", extra={
            "health_check_interval": health_check_interval,
            "max_restart_attempts": max_restart_attempts,
            "restart_delay": restart_delay,
            "service": "service_coordinator"
        })

    def register_service(
        self,
        service: ServiceBase,
        config: Optional[ServiceConfig] = None,
    ) -> None:
        """
        註冊服務到協調器

        此方法使用簡單的狀態檢查來防止替換正在運行的服務。設計考量：

        1. **簡單檢查 vs 鎖定機制**：選擇簡單檢查而非鎖定機制，因為：
           - 服務註冊通常在啟動階段完成，不會有並發問題
           - Python 的 GIL 和 asyncio 事件循環確保單線程執行
           - 避免引入不必要的複雜性和潛在死鎖風險

        2. **安全保證**：
           - 若服務正在運行，會拋出 ValueError 拒絕替換
           - 調用方應確保在註冊新服務前先停止並取消註冊舊服務

        3. **未來改進 (Phase 3.2)**：
           - 在 Linux 環境下，可實作基於檔案鎖定 (file lock) 搭配進程雜湊 (process hash) 的機制
           - 此機制可解決跨應用程式重啟時的服務狀態同步問題
           - 實作路徑：使用 fcntl.flock() 或 fcntl.lockf() 配合 PID 檔案
           - 詳見規劃文件：docs/plans/PHASE3_EDGE_ALL_IN_ONE.md

        Args:
            service: 服務實例
            config: 服務配置（可選）

        Raises:
            ValueError: 如果嘗試替換正在運行的服務
        """
        if service.name in self._services:
            old_service = self._services[service.name]
            if old_service.is_running:
                raise ValueError(f"Cannot replace running service: {service.name}")
            # 建議使用 replace_service() 或先調用 unregister_service()
            raise ValueError(
                f"Service '{service.name}' already registered. "
                "Use replace_service() to replace an existing service, "
                "or call unregister_service() first."
            )

        self._services[service.name] = service

        # 建立或更新狀態
        if config is None:
            config = ServiceConfig(
                name=service.name,
                service_type=type(service).__name__,
            )

        self._states[service.name] = ServiceState(config=config)

        logger.info("Service registered", extra={
            "service_name": service.name,
            "service_type": config.service_type,
            "enabled": config.enabled,
            "service": "service_coordinator"
        })

    def replace_service(
        self,
        service: ServiceBase,
        config: Optional[ServiceConfig] = None,
    ) -> None:
        """
        替換已註冊的服務

        此方法明確用於替換現有服務。如果服務不存在，則等同於 register_service()。
        如果服務正在運行，將拋出 ValueError。

        Args:
            service: 新的服務實例
            config: 服務配置（可選）

        Raises:
            ValueError: 如果嘗試替換正在運行的服務
        """
        if service.name in self._services:
            old_service = self._services[service.name]
            if old_service.is_running:
                raise ValueError(f"Cannot replace running service: {service.name}")
            logger.warning("Replacing existing service", extra={
                "service_name": service.name,
                "old_service_type": type(old_service).__name__,
                "new_service_type": type(service).__name__,
                "service": "service_coordinator"
            })
            # 清理舊狀態
            del self._states[service.name]

        self._services[service.name] = service

        # 建立或更新狀態
        if config is None:
            config = ServiceConfig(
                name=service.name,
                service_type=type(service).__name__,
            )

        self._states[service.name] = ServiceState(config=config)

        logger.info("Service replaced/registered", extra={
            "service_name": service.name,
            "service_type": config.service_type,
            "enabled": config.enabled,
            "service": "service_coordinator"
        })

    def unregister_service(self, service_name: str) -> bool:
        """
        取消註冊服務

        Args:
            service_name: 服務名稱

        Returns:
            是否成功取消註冊
        """
        if service_name not in self._services:
            return False

        del self._services[service_name]
        del self._states[service_name]

        logger.info("Service unregistered", extra={
            "service_name": service_name,
            "service": "service_coordinator"
        })

        return True

    def set_alert_callback(
        self,
        callback: Callable[[str, str, Dict], Coroutine],
    ) -> None:
        """
        設定告警回呼函式

        Args:
            callback: 告警回呼函式，接收 (title, body, context)
        """
        self._alert_callback = callback

    def set_state_change_callback(
        self,
        callback: Callable[[str, ServiceStatus, ServiceStatus, ServiceState], Coroutine],
    ) -> None:
        """
        設定非同步狀態變更回呼函式

        當服務狀態發生變更時，會非同步呼叫此回呼函式。

        Args:
            callback: 非同步回呼函式，接收 (service_name, old_status, new_status, state)
        """
        self._state_change_callback = callback

    async def _notify_state_change(
        self,
        service_name: str,
        old_status: ServiceStatus,
        new_status: ServiceStatus,
    ) -> None:
        """
        非同步通知狀態變更

        Args:
            service_name: 服務名稱
            old_status: 舊狀態
            new_status: 新狀態
        """
        if old_status == new_status:
            return

        state = self._states.get(service_name)
        if not state:
            return

        logger.debug("Service state changed", extra={
            "service_name": service_name,
            "old_status": old_status.value,
            "new_status": new_status.value,
            "service": "service_coordinator"
        })

        if self._state_change_callback:
            try:
                await self._state_change_callback(
                    service_name, old_status, new_status, state
                )
            except Exception as e:
                logger.error("Failed to notify state change", extra={
                    "service_name": service_name,
                    "error": str(e),
                    "service": "service_coordinator"
                })

    async def _send_alert(self, title: str, body: str, context: Dict = None) -> None:
        """發送告警"""
        if context is None:
            context = {}

        logger.warning("Alert triggered", extra={
            "alert_title": title,
            "alert_body": body,
            "context": context,
            "service": "service_coordinator"
        })

        if self._alert_callback:
            try:
                await self._alert_callback(title, body, context)
            except Exception as e:
                logger.error("Failed to send alert", extra={
                    "error": str(e),
                    "service": "service_coordinator"
                })

    async def start_service(self, service_name: str) -> bool:
        """
        啟動單個服務，包含啟動異常恢復邏輯

        當服務啟動失敗時，如果配置了啟動重試（startup_retry_enabled），
        會自動進行指定次數（max_startup_retry_attempts）的重試嘗試。

        Args:
            service_name: 服務名稱

        Returns:
            是否成功啟動
        """
        if service_name not in self._services:
            logger.error("Service not found", extra={
                "service_name": service_name,
                "service": "service_coordinator"
            })
            return False

        service = self._services[service_name]
        state = self._states[service_name]

        if service.is_running:
            logger.warning("Service already running", extra={
                "service_name": service_name,
                "service": "service_coordinator"
            })
            return True

        # 重置啟動重試計數
        state.startup_retry_count = 0

        # 第一次啟動嘗試
        success = await self._do_start_service(service_name)

        # 如果啟動失敗且配置了啟動重試，則進行重試
        if not success and state.config.startup_retry_enabled:
            max_retries = state.config.max_startup_retry_attempts
            retry_delay = state.config.startup_retry_delay_seconds

            while state.startup_retry_count < max_retries:
                state.startup_retry_count += 1

                logger.info("Attempting startup recovery", extra={
                    "service_name": service_name,
                    "retry_attempt": state.startup_retry_count,
                    "max_retries": max_retries,
                    "retry_delay": retry_delay,
                    "service": "service_coordinator"
                })

                # 發送啟動重試告警
                await self._send_alert(
                    "服務啟動失敗，正在重試",
                    f"{service_name} 啟動失敗，正在進行第 {state.startup_retry_count}/{max_retries} 次重試",
                    {
                        "alert_type": "startup_retry",
                        "service": service_name,
                        "retry_attempt": state.startup_retry_count,
                        "last_error": state.last_error
                    }
                )

                # 等待重試延遲
                await asyncio.sleep(retry_delay)

                # 重新嘗試啟動
                success = await self._do_start_service(service_name)

                if success:
                    logger.info("Startup recovery succeeded", extra={
                        "service_name": service_name,
                        "retry_attempt": state.startup_retry_count,
                        "service": "service_coordinator"
                    })
                    break

            # 如果重試後仍然失敗，發送最終告警
            if not success:
                await self._send_alert(
                    "服務啟動失敗，重試次數已用盡",
                    f"{service_name} 在 {max_retries} 次重試後仍然無法啟動",
                    {
                        "alert_type": "startup_failed",
                        "service": service_name,
                        "total_attempts": state.startup_retry_count + 1,
                        "last_error": state.last_error
                    }
                )

        return success

    async def _do_start_service(self, service_name: str) -> bool:
        """
        執行實際的服務啟動操作

        這是內部方法，負責執行單次服務啟動嘗試。
        不包含重試邏輯，由 start_service 方法處理重試。

        Args:
            service_name: 服務名稱

        Returns:
            是否成功啟動
        """
        service = self._services[service_name]
        state = self._states[service_name]

        old_status = state.status
        state.status = ServiceStatus.STARTING
        await self._notify_state_change(service_name, old_status, ServiceStatus.STARTING)

        logger.info("Starting service", extra={
            "service_name": service_name,
            "service": "service_coordinator"
        })

        try:
            success = await asyncio.wait_for(
                service.start(),
                timeout=state.config.startup_timeout_seconds,
            )

            if success:
                old_status = state.status
                state.status = ServiceStatus.RUNNING
                state.started_at = datetime.now(timezone.utc)
                state.restart_attempts = 0
                # 注意：此處故意不重置 startup_retry_count
                # 與 restart_attempts（健康檢查失敗後的重啟計數）不同，
                # startup_retry_count 記錄的是當次啟動過程的重試次數，
                # 用於監控和告警追蹤，應保留以供外部查詢
                state.last_error = None
                await self._notify_state_change(service_name, old_status, ServiceStatus.RUNNING)

                logger.info("Service started successfully", extra={
                    "service_name": service_name,
                    "service": "service_coordinator"
                })

                return True
            else:
                old_status = state.status
                state.status = ServiceStatus.ERROR
                state.last_error = "Start returned False"
                await self._notify_state_change(service_name, old_status, ServiceStatus.ERROR)

                logger.error("Service failed to start", extra={
                    "service_name": service_name,
                    "service": "service_coordinator"
                })

                return False

        except asyncio.TimeoutError:
            old_status = state.status
            state.status = ServiceStatus.ERROR
            state.last_error = "Startup timeout"
            await self._notify_state_change(service_name, old_status, ServiceStatus.ERROR)

            logger.error("Service startup timeout", extra={
                "service_name": service_name,
                "timeout": state.config.startup_timeout_seconds,
                "service": "service_coordinator"
            })

            return False

        except Exception as e:
            old_status = state.status
            state.status = ServiceStatus.ERROR
            state.last_error = str(e)
            await self._notify_state_change(service_name, old_status, ServiceStatus.ERROR)

            logger.error("Service startup error", extra={
                "service_name": service_name,
                "error": str(e),
                "service": "service_coordinator"
            }, exc_info=True)

            return False

    async def stop_service(
        self,
        service_name: str,
        timeout: Optional[float] = None,
    ) -> bool:
        """
        停止單個服務

        Args:
            service_name: 服務名稱
            timeout: 停止逾時（秒）

        Returns:
            是否成功停止
        """
        if service_name not in self._services:
            logger.error("Service not found", extra={
                "service_name": service_name,
                "service": "service_coordinator"
            })
            return False

        service = self._services[service_name]
        state = self._states[service_name]

        if not service.is_running:
            logger.info("Service not running", extra={
                "service_name": service_name,
                "service": "service_coordinator"
            })
            return True

        old_status = state.status
        state.status = ServiceStatus.STOPPING
        await self._notify_state_change(service_name, old_status, ServiceStatus.STOPPING)

        logger.info("Stopping service", extra={
            "service_name": service_name,
            "service": "service_coordinator"
        })

        try:
            success = await service.stop(timeout=timeout)

            if success:
                old_status = state.status
                state.status = ServiceStatus.STOPPED
                state.restart_attempts = 0
                state.consecutive_failures = 0
                state.started_at = None
                await self._notify_state_change(service_name, old_status, ServiceStatus.STOPPED)

                logger.info("Service stopped successfully", extra={
                    "service_name": service_name,
                    "service": "service_coordinator"
                })

                return True
            else:
                old_status = state.status
                state.status = ServiceStatus.ERROR
                state.last_error = "Stop returned False"
                await self._notify_state_change(service_name, old_status, ServiceStatus.ERROR)

                logger.error("Service failed to stop", extra={
                    "service_name": service_name,
                    "service": "service_coordinator"
                })

                return False

        except Exception as e:
            old_status = state.status
            state.status = ServiceStatus.ERROR
            state.last_error = str(e)
            await self._notify_state_change(service_name, old_status, ServiceStatus.ERROR)

            logger.error("Service stop error", extra={
                "service_name": service_name,
                "error": str(e),
                "service": "service_coordinator"
            }, exc_info=True)

            return False

    async def start_all_services(self, concurrent: bool = False) -> Dict[str, bool]:
        """
        啟動所有已註冊的服務

        Args:
            concurrent: 是否並發啟動服務。預設為 False（循序啟動）。
                        若服務之間有依賴關係，建議使用循序啟動。

        Returns:
            服務名稱 -> 是否成功的字典
        """
        logger.info("Starting all services", extra={
            "service_count": len(self._services),
            "concurrent": concurrent,
            "service": "service_coordinator"
        })

        results = {}

        # 取得需要啟動的服務
        services_to_start = [
            (name, state) for name, state in self._states.items()
            if state.config.enabled
        ]
        disabled_services = [
            name for name, state in self._states.items()
            if not state.config.enabled
        ]

        # 記錄被停用的服務
        for service_name in disabled_services:
            logger.info("Service disabled, skipping", extra={
                "service_name": service_name,
                "service": "service_coordinator"
            })
            results[service_name] = True

        if concurrent and services_to_start:
            # 並發啟動所有服務
            service_names = [name for name, _ in services_to_start]
            tasks = [self.start_service(name) for name in service_names]
            results_list = await asyncio.gather(*tasks, return_exceptions=True)

            for name, result in zip(service_names, results_list):
                if isinstance(result, Exception):
                    logger.error("Service start raised exception", extra={
                        "service_name": name,
                        "error": str(result),
                        "service": "service_coordinator"
                    })
                    results[name] = False
                else:
                    results[name] = result
        else:
            # 循序啟動（預設，適用於有依賴關係的服務）
            for service_name, _ in services_to_start:
                results[service_name] = await self.start_service(service_name)

        all_success = all(results.values())

        if all_success:
            logger.info("All services started successfully", extra={
                "service_count": len(self._services),
                "service": "service_coordinator"
            })

        return results

    async def stop_all_services(
        self,
        timeout: Optional[float] = None,
        concurrent: bool = False,
    ) -> Dict[str, bool]:
        """
        停止所有已註冊的服務

        Args:
            timeout: 每個服務的停止逾時（秒）
            concurrent: 是否並發停止服務。預設為 False（循序停止）。
                        若服務之間有依賴關係，建議使用循序停止。

        Returns:
            服務名稱 -> 是否成功的字典
        """
        logger.info("Stopping all services", extra={
            "service_count": len(self._services),
            "concurrent": concurrent,
            "service": "service_coordinator"
        })

        results = {}
        service_names = list(self._services.keys())

        if concurrent and service_names:
            # 並發停止所有服務
            tasks = [self.stop_service(name, timeout=timeout) for name in service_names]
            results_list = await asyncio.gather(*tasks, return_exceptions=True)

            for name, result in zip(service_names, results_list):
                if isinstance(result, Exception):
                    logger.error("Service stop raised exception", extra={
                        "service_name": name,
                        "error": str(result),
                        "service": "service_coordinator"
                    })
                    results[name] = False
                else:
                    results[name] = result
        else:
            # 循序停止（預設，適用於有依賴關係的服務）
            for service_name in service_names:
                results[service_name] = await self.stop_service(
                    service_name,
                    timeout=timeout,
                )

        all_success = all(results.values())

        if all_success:
            logger.info("All services stopped successfully", extra={
                "service_count": len(self._services),
                "service": "service_coordinator"
            })

        return results

    async def check_service_health(self, service_name: str) -> bool:
        """
        檢查單個服務的健康狀態

        Args:
            service_name: 服務名稱

        Returns:
            是否健康
        """
        if service_name not in self._services:
            logger.error("Service not found", extra={
                "service_name": service_name,
                "service": "service_coordinator"
            })
            return False

        service = self._services[service_name]
        state = self._states[service_name]

        if not service.is_running:
            logger.info("Service not running, health check skipped", extra={
                "service_name": service_name,
                "service": "service_coordinator"
            })
            return False

        try:
            health = await service.health_check()
            state.last_health_check = datetime.now(timezone.utc)

            is_healthy = health.get("status") in ["healthy", "running"]

            if is_healthy:
                if state.consecutive_failures > 0:
                    logger.info("Service health recovered", extra={
                        "service_name": service_name,
                        "previous_failures": state.consecutive_failures,
                        "service": "service_coordinator"
                    })

                old_status = state.status
                state.status = ServiceStatus.HEALTHY
                state.consecutive_failures = 0
                await self._notify_state_change(service_name, old_status, ServiceStatus.HEALTHY)

                logger.info("Service health check passed", extra={
                    "service_name": service_name,
                    "health": health,
                    "service": "service_coordinator"
                })

                return True
            else:
                old_status = state.status
                state.consecutive_failures += 1
                state.status = ServiceStatus.UNHEALTHY
                await self._notify_state_change(service_name, old_status, ServiceStatus.UNHEALTHY)

                logger.warning("Service health check failed", extra={
                    "service_name": service_name,
                    "consecutive_failures": state.consecutive_failures,
                    "health": health,
                    "service": "service_coordinator"
                })

                await self._handle_health_failure(service_name)

                return False

        except Exception as e:
            old_status = state.status
            state.consecutive_failures += 1
            state.status = ServiceStatus.UNHEALTHY
            state.last_error = str(e)
            state.last_health_check = datetime.now(timezone.utc)
            await self._notify_state_change(service_name, old_status, ServiceStatus.UNHEALTHY)

            logger.error("Service health check error", extra={
                "service_name": service_name,
                "consecutive_failures": state.consecutive_failures,
                "error": str(e),
                "service": "service_coordinator"
            })

            await self._handle_health_failure(service_name)

            return False

    async def check_all_services_health(self) -> Dict[str, bool]:
        """
        檢查所有服務的健康狀態

        使用並發執行以提高效能，減少總健康檢查時間。

        Returns:
            服務名稱 -> 是否健康的字典
        """
        if not self._services:
            return {}

        # 並發執行所有健康檢查以提高效能
        service_names = list(self._services.keys())
        tasks = [self.check_service_health(name) for name in service_names]

        # 使用 gather 並發執行，return_exceptions=True 確保單個失敗不會影響其他
        results_list = await asyncio.gather(*tasks, return_exceptions=True)

        results = {}
        for name, result in zip(service_names, results_list):
            if isinstance(result, Exception):
                logger.error("Health check raised exception", extra={
                    "service_name": name,
                    "error": str(result),
                    "service": "service_coordinator"
                })
                results[name] = False
            else:
                results[name] = result

        return results

    async def _handle_health_failure(self, service_name: str) -> None:
        """處理健康檢查失敗"""
        state = self._states[service_name]

        if state.consecutive_failures >= self._alert_threshold:
            await self._send_alert(
                "服務健康狀態異常",
                f"{service_name} 已連續 {state.consecutive_failures} 次健康檢查失敗",
                {"alert_type": "health_failure", "service": service_name}
            )

            # 嘗試自動重啟
            # 避免重複重啟：當服務處於 STARTING 狀態時表示重啟操作正在進行中，
            # 此時不應觸發新的重啟操作以防止並發重啟導致資源競爭
            if state.config.auto_restart and state.restart_attempts < state.config.max_restart_attempts:
                if state.status != ServiceStatus.STARTING:
                    await self._attempt_restart(service_name)

    async def _attempt_restart(self, service_name: str) -> None:
        """嘗試重啟服務"""
        state = self._states[service_name]

        state.restart_attempts += 1

        logger.info("Attempting to restart service", extra={
            "service_name": service_name,
            "attempt": state.restart_attempts,
            "max_attempts": state.config.max_restart_attempts,
            "service": "service_coordinator"
        })

        await asyncio.sleep(state.config.restart_delay_seconds)

        await self.stop_service(service_name, timeout=10.0)
        success = await self.start_service(service_name)

        if success:
            # 給服務預熱時間再進行健康檢查（使用配置的預熱時間）
            if state.config.warmup_seconds > 0:
                await asyncio.sleep(state.config.warmup_seconds)
            healthy = await self.check_service_health(service_name)
            if healthy:
                state.restart_attempts = 0
                state.consecutive_failures = 0

                logger.info("Service restarted successfully", extra={
                    "service_name": service_name,
                    "service": "service_coordinator"
                })
            else:
                await self._send_alert(
                    "服務重啟後健康檢查失敗",
                    f"{service_name} 重啟後健康檢查仍然失敗 (嘗試 {state.restart_attempts}/{state.config.max_restart_attempts})",
                    {"alert_type": "restart_unhealthy", "service": service_name}
                )
        else:
            await self._send_alert(
                "服務重啟失敗",
                f"{service_name} 重啟失敗 (嘗試 {state.restart_attempts}/{state.config.max_restart_attempts})",
                {"alert_type": "restart_failed", "service": service_name}
            )

    async def _periodic_health_check(self) -> None:
        """定期健康檢查協程"""
        logger.info("Starting periodic health check", extra={
            "interval_seconds": self._health_check_interval,
            "service": "service_coordinator"
        })

        while self._running:
            try:
                # 等待 shutdown event 或超時
                await asyncio.wait_for(
                    self._shutdown_event.wait(),
                    timeout=self._health_check_interval,
                )
                # 收到關閉信號
                break
            except asyncio.TimeoutError:
                # 正常的超時，檢查是否仍在運行後再執行健康檢查
                if not self._running or self._shutdown_event.is_set():
                    break

                # 建立可取消的健康檢查任務
                health_check_task = asyncio.create_task(
                    self.check_all_services_health()
                )
                shutdown_wait_task = asyncio.create_task(
                    self._shutdown_event.wait()
                )

                try:
                    done, pending = await asyncio.wait(
                        [health_check_task, shutdown_wait_task],
                        return_when=asyncio.FIRST_COMPLETED,
                    )

                    # 取消未完成的任務
                    for task in pending:
                        task.cancel()
                        try:
                            await task
                        except asyncio.CancelledError:
                            pass

                    # 如果收到 shutdown 信號，退出循環
                    if self._shutdown_event.is_set():
                        break

                except asyncio.CancelledError:
                    # 取消健康檢查任務
                    if not health_check_task.done():
                        health_check_task.cancel()
                        try:
                            await health_check_task
                        except asyncio.CancelledError:
                            pass
                    if not shutdown_wait_task.done():
                        shutdown_wait_task.cancel()
                        try:
                            await shutdown_wait_task
                        except asyncio.CancelledError:
                            pass
                    raise

            except asyncio.CancelledError:
                # 健康檢查任務被取消是正常流程，安全忽略
                break
            except Exception as e:
                logger.error("Error in periodic health check", extra={
                    "error": str(e),
                    "service": "service_coordinator"
                }, exc_info=True)

        logger.info("Periodic health check stopped", extra={
            "service": "service_coordinator"
        })

    async def start(self) -> bool:
        """
        啟動服務協調器

        Returns:
            是否成功啟動
        """
        if self._running:
            logger.warning("ServiceCoordinator already running", extra={
                "service": "service_coordinator"
            })
            return True

        logger.info("Starting ServiceCoordinator", extra={
            "service": "service_coordinator"
        })

        try:
            self._running = True
            self._shutdown_event.clear()

            # 啟動所有服務
            results = await self.start_all_services()

            # 執行初始健康檢查
            await self.check_all_services_health()

            # 啟動定期健康檢查
            self._health_check_task = asyncio.create_task(
                self._periodic_health_check()
            )

            logger.info("ServiceCoordinator started", extra={
                "service_results": results,
                "service": "service_coordinator"
            })

            return all(results.values())
        except Exception:
            self._running = False
            raise

    async def stop(self, timeout: Optional[float] = None) -> bool:
        """
        停止服務協調器

        Args:
            timeout: 停止逾時（秒）

        Returns:
            是否成功停止
        """
        if not self._running:
            return True

        logger.info("Stopping ServiceCoordinator", extra={
            "service": "service_coordinator"
        })

        self._running = False
        self._shutdown_event.set()

        # 停止定期健康檢查
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                # 健康檢查任務被取消是正常流程，安全忽略
                pass
            self._health_check_task = None

        # 停止所有服務
        results = await self.stop_all_services(timeout=timeout)

        logger.info("ServiceCoordinator stopped", extra={
            "service_results": results,
            "service": "service_coordinator"
        })

        return all(results.values())

    def get_services_status(self) -> Dict[str, Dict[str, Any]]:
        """
        取得所有服務的狀態

        Returns:
            服務狀態字典
        """
        statuses = {}

        for service_name, service in self._services.items():
            state = self._states[service_name]

            statuses[service_name] = {
                "name": state.config.name,
                "type": state.config.service_type,
                "status": state.status.value,
                "is_running": service.is_running,
                "enabled": state.config.enabled,
                "restart_attempts": state.restart_attempts,
                "startup_retry_count": state.startup_retry_count,
                "consecutive_failures": state.consecutive_failures,
                "last_health_check": state.last_health_check.isoformat() if state.last_health_check else None,
                "last_error": state.last_error,
                "started_at": state.started_at.isoformat() if state.started_at else None,
            }

        return statuses

    async def health_check(self) -> Dict[str, Any]:
        """
        服務協調器自身的健康檢查

        Returns:
            健康狀態資訊
        """
        service_healths = {}

        for service_name in self._services:
            state = self._states[service_name]
            service_healths[service_name] = {
                "status": state.status.value,
                "healthy": state.status in [ServiceStatus.HEALTHY, ServiceStatus.RUNNING],
            }

        all_healthy = len(service_healths) > 0 and all(
            h["healthy"] for h in service_healths.values()
        )

        return {
            "status": "healthy" if (self._running and all_healthy) else "unhealthy",
            "running": self._running,
            "service_count": len(self._services),
            "services": service_healths,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
