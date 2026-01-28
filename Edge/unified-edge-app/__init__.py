"""
Unified Edge App Package
整合 WebUI/MCP/Robot-Console 的統一部署套件

此套件將三個模組整合為單一的 Edge 應用程式，提供：
- 完整的本地機器人控制功能
- 一鍵啟動所有必要服務
- 精簡的 Web 管理介面
- LLM 整合與進階指令支援
"""

__version__ = "1.0.0"
__author__ = "Robot Command Console Team"

from .core.launcher import UnifiedEdgeApp

__all__ = ["UnifiedEdgeApp"]
