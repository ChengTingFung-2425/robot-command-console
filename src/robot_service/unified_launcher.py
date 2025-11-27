"""
Unified Launcher
統一啟動器，一鍵啟動所有服務與健康檢查

Phase 3.1 核心功能：
- 一鍵啟動/停止所有服務
- 統一健康檢查
- 服務狀態監控
"""

import asyncio
import logging
import os
import secrets
import signal
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

import aiohttp

# 添加專案路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from common.service_types import ServiceConfig  # noqa: E402
from .service_coordinator import ServiceBase, ServiceCoordinator, QueueService  # noqa: E402


logger = logging.getLogger(__name__)


class ServiceType(Enum):
    """服務類型"""
    FLASK_API = "flask-api"
    MCP_SERVICE = "mcp-service"
    WEBUI = "webui"
    QUEUE = "queue"


@dataclass
class ProcessServiceConfig:
    """進程服務配置"""
    name: str
    service_type: ServiceType
    command: List[str]
    port: int
    health_url: str
    working_dir: Optional[str] = None
    env: Dict[str, str] = field(default_factory=dict)
    startup_timeout_seconds: float = 10.0
    health_check_timeout_seconds: float = 5.0
    enabled: bool = True


class ProcessService(ServiceBase):
    """
    進程服務

    管理外部進程（如 Flask、FastAPI、WebUI）的生命週期
    """

    def __init__(self, config: ProcessServiceConfig):
        """
        初始化進程服務

        Args:
            config: 進程服務配置
        """
        self._config = config
        self._process: Optional[subprocess.Popen] = None
        self._running = False
        self._http_session: Optional[aiohttp.ClientSession] = None

    @property
    def name(self) -> str:
        return self._config.name

    @property
    def config(self) -> ProcessServiceConfig:
        return self._config

    @property
    def is_running(self) -> bool:
        if not self._running:
            return False
        process = self._process
        return process is not None and process.poll() is None

    async def _get_http_session(self) -> aiohttp.ClientSession:
        """取得或建立 HTTP 客戶端會話（重複使用以提高效能）"""
        if self._http_session is None or self._http_session.closed:
            self._http_session = aiohttp.ClientSession()
        return self._http_session

    async def _close_http_session(self) -> None:
        """關閉 HTTP 客戶端會話"""
        if self._http_session and not self._http_session.closed:
            await self._http_session.close()
            self._http_session = None

    async def start(self) -> bool:
        """啟動服務進程"""
        if self.is_running:
            logger.warning(f"Service {self.name} already running")
            return True

        try:
            # 設定環境變數
            env = os.environ.copy()
            env.update(self._config.env)

            # 設定工作目錄
            cwd = self._config.working_dir

            logger.info(f"Starting service: {self.name}", extra={
                "command": self._config.command,
                "port": self._config.port,
                "service": "unified_launcher"
            })

            # 啟動進程（使用 DEVNULL 避免管道緩衝區阻塞）
            self._process = subprocess.Popen(
                self._config.command,
                env=env,
                cwd=cwd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            # 等待服務就緒（透過健康檢查）
            startup_success = await self._wait_for_startup()

            if startup_success:
                self._running = True
                logger.info(f"Service {self.name} started successfully", extra={
                    "pid": self._process.pid,
                    "port": self._config.port,
                    "service": "unified_launcher"
                })
                return True
            else:
                logger.error(f"Service {self.name} failed to start within timeout", extra={
                    "timeout_seconds": self._config.startup_timeout_seconds,
                    "service": "unified_launcher"
                })
                await self.stop()
                return False

        except Exception as e:
            logger.error(f"Failed to start service {self.name}", extra={
                "error": str(e),
                "service": "unified_launcher"
            }, exc_info=True)
            return False

    async def _wait_for_startup(self) -> bool:
        """等待服務啟動完成"""
        start_time = datetime.now(timezone.utc)
        timeout = self._config.startup_timeout_seconds

        while (datetime.now(timezone.utc) - start_time).total_seconds() < timeout:
            # 檢查進程是否仍在運行（防止競態條件）
            process = self._process
            if process is None or process.poll() is not None:
                # 進程已退出或不存在
                if process is not None:
                    logger.error("Process exited during startup", extra={
                        "service": self.name,
                        "exit_code": process.returncode,
                    })
                return False

            # 嘗試健康檢查（使用共用會話以提高效能）
            try:
                session = await self._get_http_session()
                async with session.get(
                    self._config.health_url,
                    timeout=aiohttp.ClientTimeout(total=2)
                ) as response:
                    if response.status == 200:
                        return True
            except Exception:
                # 服務尚未就緒，繼續等待
                pass

            await asyncio.sleep(0.5)

        return False

    async def stop(self, timeout: Optional[float] = None) -> bool:
        """停止服務進程"""
        # 關閉 HTTP 會話
        await self._close_http_session()

        if not self._process:
            self._running = False
            return True

        timeout = timeout or 10.0

        try:
            logger.info(f"Stopping service: {self.name}", extra={
                "pid": self._process.pid,
                "service": "unified_launcher"
            })

            # 發送 SIGTERM
            self._process.terminate()

            try:
                # 等待進程結束
                self._process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                # 強制結束
                logger.warning(f"Service {self.name} did not terminate gracefully, killing", extra={
                    "service": "unified_launcher"
                })
                self._process.kill()
                try:
                    self._process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    logger.error(f"Service {self.name} did not respond to SIGKILL", extra={
                        "service": "unified_launcher"
                    })
                    # 進程可能處於不可中斷的睡眠狀態，設為 None 避免洩漏
                    self._process = None

            self._running = False
            self._process = None

            logger.info(f"Service {self.name} stopped", extra={
                "service": "unified_launcher"
            })

            return True

        except Exception as e:
            logger.error(f"Failed to stop service {self.name}", extra={
                "error": str(e),
                "service": "unified_launcher"
            }, exc_info=True)
            return False

    async def health_check(self) -> Dict[str, Any]:
        """健康檢查"""
        if not self.is_running:
            return {
                "status": "stopped",
                "message": "Service is not running"
            }

        try:
            session = await self._get_http_session()
            async with session.get(
                self._config.health_url,
                timeout=aiohttp.ClientTimeout(total=self._config.health_check_timeout_seconds)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "status": "healthy",
                        "response": data,
                        "port": self._config.port
                    }
                else:
                    return {
                        "status": "unhealthy",
                        "message": f"Health check returned status {response.status}",
                        "port": self._config.port
                    }
        except asyncio.TimeoutError:
            return {
                "status": "unhealthy",
                "message": "Health check timed out",
                "port": self._config.port
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": str(e),
                "port": self._config.port
            }


class UnifiedLauncher:
    """
    統一啟動器

    整合所有服務的啟動、停止與健康檢查功能

    功能：
    - 一鍵啟動所有服務
    - 一鍵停止所有服務
    - 統一健康檢查
    - 服務狀態監控
    - 自動重啟失敗的服務
    """

    def __init__(
        self,
        health_check_interval: float = 30.0,
        max_restart_attempts: int = 3,
        restart_delay: float = 2.0,
        base_dir: Optional[str] = None,
    ):
        """
        初始化統一啟動器

        Args:
            health_check_interval: 健康檢查間隔（秒）
            max_restart_attempts: 最大重啟嘗試次數
            restart_delay: 重啟延遲（秒）
            base_dir: 專案根目錄
        """
        self._base_dir = base_dir or self._detect_base_dir()
        self._coordinator = ServiceCoordinator(
            health_check_interval=health_check_interval,
            max_restart_attempts=max_restart_attempts,
            restart_delay=restart_delay,
        )
        self._services: Dict[str, ProcessService] = {}
        self._running = False
        self._shutdown_event: Optional[asyncio.Event] = None

        # 設定告警回呼
        self._coordinator.set_alert_callback(self._handle_alert)

        logger.info("UnifiedLauncher initialized", extra={
            "base_dir": self._base_dir,
            "health_check_interval": health_check_interval,
            "max_restart_attempts": max_restart_attempts,
            "service": "unified_launcher"
        })

    def _detect_base_dir(self) -> str:
        """偵測專案根目錄"""
        # 從當前模組位置向上尋找專案根目錄
        current = os.path.dirname(os.path.abspath(__file__))
        while current != os.path.dirname(current):
            if os.path.exists(os.path.join(current, 'requirements.txt')):
                return current
            current = os.path.dirname(current)
        return os.getcwd()

    def _get_default_services(self) -> List[ProcessServiceConfig]:
        """取得預設服務配置"""
        # 使用環境變數或生成安全的隨機 token
        app_token = os.environ.get("APP_TOKEN")
        if not app_token:
            app_token = secrets.token_hex(32)
            logger.warning(
                "APP_TOKEN not set, using generated token. "
                "Set APP_TOKEN environment variable for production.",
                extra={"service": "unified_launcher"}
            )

        return [
            # Flask API 服務
            ProcessServiceConfig(
                name="flask_api",
                service_type=ServiceType.FLASK_API,
                command=["python3", "flask_service.py"],
                port=5000,
                health_url="http://127.0.0.1:5000/health",
                working_dir=self._base_dir,
                env={
                    "APP_TOKEN": app_token,
                    "PORT": "5000",
                },
                startup_timeout_seconds=15.0,
            ),
            # MCP 服務
            ProcessServiceConfig(
                name="mcp_service",
                service_type=ServiceType.MCP_SERVICE,
                command=["python3", "-m", "MCP.start"],
                port=8000,
                health_url="http://127.0.0.1:8000/health",
                working_dir=self._base_dir,
                env={
                    "MCP_API_HOST": "127.0.0.1",
                    "MCP_API_PORT": "8000",
                },
                startup_timeout_seconds=15.0,
            ),
        ]

    def register_default_services(self) -> None:
        """註冊預設服務"""
        for config in self._get_default_services():
            self.register_process_service(config)

        # 同時註冊佇列服務
        queue_service = QueueService(
            queue_max_size=1000,
            max_workers=5,
            poll_interval=0.1,
        )
        queue_config = ServiceConfig(
            name="queue_service",
            service_type="QueueService",
            enabled=True,
            auto_restart=True,
        )
        self._coordinator.register_service(queue_service, queue_config)

        logger.info("Default services registered", extra={
            "service_count": len(self._services) + 1,  # +1 for queue_service
            "service": "unified_launcher"
        })

    def register_process_service(self, config: ProcessServiceConfig) -> None:
        """
        註冊進程服務

        Args:
            config: 進程服務配置
        """
        process_service = ProcessService(config)
        self._services[config.name] = process_service

        service_config = ServiceConfig(
            name=config.name,
            service_type=config.service_type.value,
            enabled=config.enabled,
            auto_restart=True,
            startup_timeout_seconds=config.startup_timeout_seconds,
        )

        self._coordinator.register_service(process_service, service_config)

        logger.info(f"Process service registered: {config.name}", extra={
            "port": config.port,
            "service_type": config.service_type.value,
            "service": "unified_launcher"
        })

    async def start_all(self) -> Dict[str, bool]:
        """
        一鍵啟動所有服務

        Returns:
            服務名稱 -> 是否成功啟動
        """
        logger.info("Starting all services (一鍵啟動)", extra={
            "service": "unified_launcher"
        })

        self._running = True
        # 延遲建立 Event 直到確定有事件迴圈運行
        if self._shutdown_event is None:
            self._shutdown_event = asyncio.Event()
        self._shutdown_event.clear()

        try:
            success = await self._coordinator.start()

            if success:
                logger.info("All services started successfully", extra={
                    "service": "unified_launcher"
                })
            else:
                logger.warning("Some services failed to start", extra={
                    "service": "unified_launcher"
                })

            return self._coordinator.get_services_status()

        except Exception as e:
            logger.error("Failed to start services", extra={
                "error": str(e),
                "service": "unified_launcher"
            }, exc_info=True)
            raise

    async def stop_all(self, timeout: Optional[float] = None) -> Dict[str, bool]:
        """
        一鍵停止所有服務

        Args:
            timeout: 停止超時（秒）

        Returns:
            服務名稱 -> 是否成功停止
        """
        logger.info("Stopping all services (一鍵停止)", extra={
            "service": "unified_launcher"
        })

        self._running = False
        if self._shutdown_event is not None:
            self._shutdown_event.set()

        try:
            success = await self._coordinator.stop(timeout=timeout)

            if success:
                logger.info("All services stopped successfully", extra={
                    "service": "unified_launcher"
                })
            else:
                logger.warning("Some services failed to stop", extra={
                    "service": "unified_launcher"
                })

            return self._coordinator.get_services_status()

        except Exception as e:
            logger.error("Failed to stop services", extra={
                "error": str(e),
                "service": "unified_launcher"
            }, exc_info=True)
            raise

    async def health_check_all(self) -> Dict[str, Any]:
        """
        統一健康檢查

        Returns:
            所有服務的健康狀態
        """
        logger.info("Performing health check on all services (健康檢查)", extra={
            "service": "unified_launcher"
        })

        results = await self._coordinator.check_all_services_health()

        # 取得詳細狀態
        statuses = self._coordinator.get_services_status()

        return {
            "overall_healthy": all(results.values()),
            "services": statuses,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def get_services_status(self) -> Dict[str, Dict[str, Any]]:
        """
        取得所有服務狀態

        Returns:
            服務狀態字典
        """
        return self._coordinator.get_services_status()

    async def _handle_alert(self, title: str, body: str, context: Dict[str, Any]) -> None:
        """處理告警"""
        logger.warning(f"Alert: {title} - {body}", extra={
            "context": context,
            "service": "unified_launcher"
        })

    async def run_forever(self) -> None:
        """持續運行直到收到關閉信號"""
        logger.info("UnifiedLauncher running, press Ctrl+C to stop", extra={
            "service": "unified_launcher"
        })

        # 確保 shutdown event 已建立
        if self._shutdown_event is None:
            self._shutdown_event = asyncio.Event()
        await self._shutdown_event.wait()

        logger.info("UnifiedLauncher shutting down", extra={
            "service": "unified_launcher"
        })

    @property
    def is_running(self) -> bool:
        return self._running


def setup_signal_handlers(launcher: UnifiedLauncher, shutdown_event: asyncio.Event) -> None:
    """
    設定信號處理器

    Args:
        launcher: 統一啟動器實例
        shutdown_event: 關閉事件物件，用於通知主迴圈停止
    """
    def signal_handler(signum, _frame):
        logger.info(f"Received signal {signum}, initiating shutdown", extra={
            "service": "unified_launcher"
        })
        shutdown_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


async def main_async(args) -> int:
    """
    非同步主函式

    Args:
        args: argparse 解析後的命令列參數

    Returns:
        int: 退出碼（0 表示成功，1 表示失敗）
    """
    # 設定日誌
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    )

    # 建立啟動器
    launcher = UnifiedLauncher(
        health_check_interval=args.health_check_interval,
        max_restart_attempts=args.max_restart_attempts,
        restart_delay=args.restart_delay,
    )

    # 註冊預設服務
    launcher.register_default_services()

    # 設定信號處理
    shutdown_event = asyncio.Event()
    setup_signal_handlers(launcher, shutdown_event)

    try:
        # 啟動所有服務
        await launcher.start_all()

        # 等待關閉信號
        await shutdown_event.wait()

        # 停止所有服務
        await launcher.stop_all(timeout=30.0)

        return 0

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        await launcher.stop_all(timeout=10.0)
        return 1


def main():
    """
    CLI 入口點

    解析命令列參數，並啟動統一啟動器（UnifiedLauncher）。
    此函式負責：
        - 建立並解析 argparse 參數
        - 設定啟動器相關參數（健康檢查間隔、重啟次數、延遲、日誌等級）
        - 啟動非同步主流程
        - 結束時以適當的狀態碼離開
    """
    import argparse

    parser = argparse.ArgumentParser(
        description='Robot Console - 統一啟動器 (Unified Launcher)'
    )

    parser.add_argument(
        '--health-check-interval',
        type=float,
        default=30.0,
        help='健康檢查間隔（秒，預設: 30.0）'
    )

    parser.add_argument(
        '--max-restart-attempts',
        type=int,
        default=3,
        help='最大重啟嘗試次數（預設: 3）'
    )

    parser.add_argument(
        '--restart-delay',
        type=float,
        default=2.0,
        help='重啟延遲（秒，預設: 2.0）'
    )

    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        default='INFO',
        help='日誌等級（預設: INFO）'
    )

    args = parser.parse_args()

    # 執行
    sys.exit(asyncio.run(main_async(args)))


if __name__ == '__main__':
    main()
