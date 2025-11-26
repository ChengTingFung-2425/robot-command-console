"""
Robot Service 模組
提供模組化、可測試的機器人指令服務，支援 Electron 整合與獨立 CLI 模式
"""

__version__ = "1.0.0"
__all__ = [
    "QueueHandler",
    "ServiceManager",
    "ServiceCoordinator",
    "ServiceBase",
    "ServiceStatus",
    "ServiceConfig",
    "ServiceState",
    "QueueService",
    "CLIRunner",
]

from .queue.handler import QueueHandler
from .service_manager import ServiceManager
from .service_coordinator import (
    ServiceCoordinator,
    ServiceBase,
    QueueService,
)
# 從 common 模組導入共用服務類型
from common.service_types import ServiceStatus, ServiceConfig, ServiceState

try:
    from .cli.runner import CLIRunner
except ImportError:
    CLIRunner = None
