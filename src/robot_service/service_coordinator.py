"""
Service Coordinator
服務協調器，負責啟動、停止、健康檢查多個服務
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional

from .service_manager import ServiceManager


logger = logging.getLogger(__name__)


class ServiceStatus(Enum):
    """服務狀態"""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass
class ServiceConfig:
    """服務配置"""
    name: str
    service_type: str
    enabled: bool = True
    auto_restart: bool = True
    max_restart_attempts: int = 3
    restart_delay_seconds: float = 2.0
    health_check_interval_seconds: float = 30.0
    startup_timeout_seconds: float = 5.0
    extra_config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ServiceState:
    """服務狀態資訊"""
    config: ServiceConfig
    status: ServiceStatus = ServiceStatus.STOPPED
    restart_attempts: int = 0
    consecutive_failures: int = 0
    last_health_check: Optional[datetime] = None
    last_error: Optional[str] = None
    started_at: Optional[datetime] = None


class ServiceBase(ABC):
    """
    服務基礎類別
    
    所有需要被協調器管理的服務都應實作此介面
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """服務名稱"""
        pass
    
    @abstractmethod
    async def start(self) -> bool:
        """啟動服務"""
        pass
    
    @abstractmethod
    async def stop(self, timeout: Optional[float] = None) -> bool:
        """停止服務"""
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """健康檢查"""
        pass
    
    @property
    @abstractmethod
    def is_running(self) -> bool:
        """服務是否運行中"""
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
        
        Args:
            service: 服務實例
            config: 服務配置（可選）
        """
        if service.name in self._services:
            logger.warning("Service already registered, replacing", extra={
                "service_name": service.name,
                "service": "service_coordinator"
            })
        
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
        啟動單個服務
        
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
        
        state.status = ServiceStatus.STARTING
        
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
                state.status = ServiceStatus.RUNNING
                state.started_at = datetime.now(timezone.utc)
                state.restart_attempts = 0
                state.last_error = None
                
                logger.info("Service started successfully", extra={
                    "service_name": service_name,
                    "service": "service_coordinator"
                })
                
                return True
            else:
                state.status = ServiceStatus.ERROR
                state.last_error = "Start returned False"
                
                logger.error("Service failed to start", extra={
                    "service_name": service_name,
                    "service": "service_coordinator"
                })
                
                return False
        
        except asyncio.TimeoutError:
            state.status = ServiceStatus.ERROR
            state.last_error = "Startup timeout"
            
            logger.error("Service startup timeout", extra={
                "service_name": service_name,
                "timeout": state.config.startup_timeout_seconds,
                "service": "service_coordinator"
            })
            
            return False
        
        except Exception as e:
            state.status = ServiceStatus.ERROR
            state.last_error = str(e)
            
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
        
        state.status = ServiceStatus.STOPPING
        
        logger.info("Stopping service", extra={
            "service_name": service_name,
            "service": "service_coordinator"
        })
        
        try:
            success = await service.stop(timeout=timeout)
            
            if success:
                state.status = ServiceStatus.STOPPED
                state.restart_attempts = 0
                state.consecutive_failures = 0
                state.started_at = None
                
                logger.info("Service stopped successfully", extra={
                    "service_name": service_name,
                    "service": "service_coordinator"
                })
                
                return True
            else:
                state.status = ServiceStatus.ERROR
                state.last_error = "Stop returned False"
                
                logger.error("Service failed to stop", extra={
                    "service_name": service_name,
                    "service": "service_coordinator"
                })
                
                return False
        
        except Exception as e:
            state.status = ServiceStatus.ERROR
            state.last_error = str(e)
            
            logger.error("Service stop error", extra={
                "service_name": service_name,
                "error": str(e),
                "service": "service_coordinator"
            }, exc_info=True)
            
            return False
    
    async def start_all_services(self) -> Dict[str, bool]:
        """
        啟動所有已註冊的服務
        
        Returns:
            服務名稱 -> 是否成功的字典
        """
        logger.info("Starting all services", extra={
            "service_count": len(self._services),
            "service": "service_coordinator"
        })
        
        results = {}
        
        for service_name in self._services:
            state = self._states[service_name]
            if state.config.enabled:
                results[service_name] = await self.start_service(service_name)
            else:
                logger.info("Service disabled, skipping", extra={
                    "service_name": service_name,
                    "service": "service_coordinator"
                })
                results[service_name] = True
        
        all_success = all(results.values())
        
        if all_success:
            await self._send_alert(
                "所有服務已啟動",
                "服務協調器已成功啟動所有服務",
                {"alert_type": "all_started"}
            )
        
        return results
    
    async def stop_all_services(
        self,
        timeout: Optional[float] = None,
    ) -> Dict[str, bool]:
        """
        停止所有已註冊的服務
        
        Args:
            timeout: 每個服務的停止逾時（秒）
            
        Returns:
            服務名稱 -> 是否成功的字典
        """
        logger.info("Stopping all services", extra={
            "service_count": len(self._services),
            "service": "service_coordinator"
        })
        
        results = {}
        
        for service_name in self._services:
            results[service_name] = await self.stop_service(
                service_name,
                timeout=timeout,
            )
        
        all_success = all(results.values())
        
        if all_success:
            await self._send_alert(
                "所有服務已停止",
                "服務協調器已停止所有服務",
                {"alert_type": "all_stopped"}
            )
        
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
                
                state.status = ServiceStatus.HEALTHY
                state.consecutive_failures = 0
                
                logger.info("Service health check passed", extra={
                    "service_name": service_name,
                    "health": health,
                    "service": "service_coordinator"
                })
                
                return True
            else:
                state.consecutive_failures += 1
                state.status = ServiceStatus.UNHEALTHY
                
                logger.warning("Service health check failed", extra={
                    "service_name": service_name,
                    "consecutive_failures": state.consecutive_failures,
                    "health": health,
                    "service": "service_coordinator"
                })
                
                await self._handle_health_failure(service_name)
                
                return False
        
        except Exception as e:
            state.consecutive_failures += 1
            state.status = ServiceStatus.UNHEALTHY
            state.last_error = str(e)
            state.last_health_check = datetime.now(timezone.utc)
            
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
        
        Returns:
            服務名稱 -> 是否健康的字典
        """
        results = {}
        
        for service_name in self._services:
            results[service_name] = await self.check_service_health(service_name)
        
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
            if state.config.auto_restart and state.restart_attempts < state.config.max_restart_attempts:
                await self._attempt_restart(service_name)
    
    async def _attempt_restart(self, service_name: str) -> None:
        """嘗試重啟服務"""
        state = self._states[service_name]
        
        if state.restart_attempts >= state.config.max_restart_attempts:
            await self._send_alert(
                "服務重啟失敗",
                f"{service_name} 已達最大重啟次數 ({state.config.max_restart_attempts})，服務無法恢復",
                {"alert_type": "restart_exhausted", "service": service_name}
            )
            return
        
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
                await asyncio.wait_for(
                    self._shutdown_event.wait(),
                    timeout=self._health_check_interval,
                )
                # 收到關閉信號
                break
            except asyncio.TimeoutError:
                # 正常的超時，執行健康檢查
                await self.check_all_services_health()
            except asyncio.CancelledError:
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
        
        all_healthy = all(
            h["healthy"] for h in service_healths.values()
        )
        
        return {
            "status": "healthy" if (self._running and all_healthy) else "unhealthy",
            "running": self._running,
            "service_count": len(self._services),
            "services": service_healths,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
