"""
MCP (Model Context Protocol) 服務模組
提供統一的 API 介面，管理指令處理、機器人路由、協定適配與可觀測性
"""

from .auth_manager import AuthManager
from .command_handler import CommandHandler
from .context_manager import ContextManager
from .logging_monitor import LoggingMonitor
from .robot_router import RobotRouter

__version__ = "1.0.0"
__all__ = [
    "CommandHandler",
    "ContextManager",
    "RobotRouter",
    "AuthManager",
    "LoggingMonitor",
]
