"""
Unified Edge App Launcher
統一 Edge App 啟動器

整合 MCP、Robot-Console 和 Web Interface 為單一應用
"""

import asyncio
import logging
import signal
import sys
from pathlib import Path
from typing import Optional

# 添加專案路徑
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.common.backend_service_manager import BackendServiceManager
from .config import UnifiedConfig

logger = logging.getLogger(__name__)


class UnifiedEdgeApp:
    """
    統一 Edge App
    
    整合所有必要服務為單一應用程式：
    - MCP Service: 指令處理、LLM 整合
    - Robot-Console: 動作執行
    - Web Interface: 本地管理介面
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        初始化統一 Edge App
        
        Args:
            config_path: 配置檔案路徑（可選）
        """
        self.config = UnifiedConfig(config_path)
        self.backend_manager: Optional[BackendServiceManager] = None
        self.running = False
        
        logger.info(f"Initializing Unified Edge App v{self.config.version}")
    
    async def start(self):
        """啟動所有服務"""
        if self.running:
            logger.warning("App is already running")
            return
        
        logger.info("Starting Unified Edge App...")
        
        try:
            # 使用統一後端服務管理器
            self.backend_manager = BackendServiceManager(
                project_root=self.config.project_root
            )
            
            # 啟動所有後端服務
            success_count, total_count = await self.backend_manager.start_all()
            
            if success_count == 0:
                raise RuntimeError("Failed to start any backend services")
            
            if success_count < total_count:
                logger.warning(
                    f"Only {success_count}/{total_count} services started successfully"
                )
            
            self.running = True
            logger.info("✅ Unified Edge App started successfully")
            logger.info(f"   Flask API: {self.backend_manager.get_service_url('flask')}")
            logger.info(f"   MCP Service: {self.backend_manager.get_service_url('mcp')}")
            
        except Exception as e:
            logger.error(f"Failed to start Unified Edge App: {e}")
            raise
    
    def stop(self):
        """停止所有服務"""
        if not self.running:
            return
        
        logger.info("Stopping Unified Edge App...")
        
        if self.backend_manager:
            self.backend_manager.stop_all()
        
        self.running = False
        logger.info("✅ Unified Edge App stopped")
    
    async def run(self):
        """運行應用程式（阻塞）"""
        # 設定信號處理
        def signal_handler(signum, frame):
            logger.info("Received shutdown signal")
            self.stop()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # 啟動
        await self.start()
        
        # 持續運行
        try:
            while self.running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
        finally:
            self.stop()
    
    def get_service_url(self, service: str) -> Optional[str]:
        """取得服務 URL"""
        if self.backend_manager:
            return self.backend_manager.get_service_url(service)
        return None
    
    def is_running(self) -> bool:
        """檢查是否運行中"""
        return self.running


async def main():
    """主程式入口"""
    app = UnifiedEdgeApp()
    await app.run()


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    asyncio.run(main())
