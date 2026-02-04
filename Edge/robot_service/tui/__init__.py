"""
TUI (Terminal User Interface) Module

提供終端機互動式介面，適用於無頭伺服器或容器環境。
"""

from .app import RobotConsoleTUI
from .runner import main

__all__ = ['RobotConsoleTUI', 'main']
