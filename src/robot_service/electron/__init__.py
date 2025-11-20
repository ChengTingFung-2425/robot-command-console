"""
Electron 整合模組
提供 Electron 管理模式的服務入口
"""

from .flask_adapter import create_flask_app

__all__ = ["create_flask_app"]
