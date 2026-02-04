"""
Service Manager
服務管理器 - 管理服務間通訊與協調
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ServiceManager:
    """
    服務管理器
    
    負責管理 MCP、Robot-Console 和 Web Interface 之間的通訊
    """
    
    def __init__(self):
        self.mcp_url: Optional[str] = None
        self.web_url: Optional[str] = None
        self.queue = None
        self.event_bus = None
    
    def set_mcp_url(self, url: str):
        """設定 MCP 服務 URL"""
        self.mcp_url = url
        logger.info(f"MCP URL set to: {url}")
    
    def set_web_url(self, url: str):
        """設定 Web Interface URL"""
        self.web_url = url
        logger.info(f"Web URL set to: {url}")
    
    def setup_inter_service_communication(self):
        """設定服務間通訊"""
        logger.info("Setting up inter-service communication...")
        
        # Web → MCP: HTTP REST API (已由 BackendServiceManager 處理)
        # MCP → Robot-Console: 本地佇列 (已由 BackendServiceManager 處理)
        # Robot-Console → MCP: 事件總線 (已由 SharedStateManager 處理)
        
        logger.info("Inter-service communication configured")
    
    def get_mcp_url(self) -> Optional[str]:
        """取得 MCP 服務 URL"""
        return self.mcp_url
    
    def get_web_url(self) -> Optional[str]:
        """取得 Web Interface URL"""
        return self.web_url
