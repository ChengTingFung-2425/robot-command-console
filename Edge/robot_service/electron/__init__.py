"""
Electron 整合模組
提供 Electron 管理模式的服務入口

包含：
- Flask 適配器
- Token 驗證器（支援輪替期間的多 Token 驗證）
- Edge UI 藍圖（本地 WebUI 功能）
"""

from .flask_adapter import create_flask_app, TokenValidator
from .edge_ui import edge_ui

__all__ = ["create_flask_app", "TokenValidator", "edge_ui"]
