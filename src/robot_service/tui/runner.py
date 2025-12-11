"""
TUI Runner

啟動 TUI 應用並整合服務協調器。
"""

import argparse
import asyncio
import logging
import os
import sys
from typing import Optional

from ..service_coordinator import ServiceCoordinator, QueueService
from ..command_history_manager import CommandHistoryManager
from common.service_types import ServiceConfig
from common.shared_state import SharedStateManager
from .app import RobotConsoleTUI


logger = logging.getLogger(__name__)


class TUIRunner:
    """
    TUI 執行器
    
    啟動服務並顯示 TUI 介面。
    """
    
    def __init__(self):
        self.coordinator: Optional[ServiceCoordinator] = None
        self.state_manager: Optional[SharedStateManager] = None
        self.history_manager: Optional[CommandHistoryManager] = None
        self.tui_app: Optional[RobotConsoleTUI] = None
    
    def parse_args(self) -> argparse.Namespace:
        """解析命令列參數"""
        parser = argparse.ArgumentParser(
            description='Robot Console - Terminal UI Mode'
        )
        
        parser.add_argument(
            '--queue-size',
            type=int,
            default=1000,
            help='Maximum queue size (default: 1000)'
        )
        
        parser.add_argument(
            '--workers',
            type=int,
            default=5,
            help='Number of worker coroutines (default: 5)'
        )
        
        parser.add_argument(
            '--poll-interval',
            type=float,
            default=0.1,
            help='Queue poll interval in seconds (default: 0.1)'
        )
        
        parser.add_argument(
            '--health-check-interval',
            type=float,
            default=30.0,
            help='Health check interval in seconds (default: 30.0)'
        )
        
        parser.add_argument(
            '--log-level',
            choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
            default='WARNING',
            help='Logging level (default: WARNING for TUI)'
        )
        
        parser.add_argument(
            '--history-db',
            type=str,
            default='data/command_history.db',
            help='Path to command history database'
        )
        
        return parser.parse_args()
    
    def setup_logging(self, level: str) -> None:
        """設定日誌"""
        # TUI 模式下，將日誌輸出到檔案避免干擾畫面
        # 確保 logs 目錄存在
        os.makedirs('logs', exist_ok=True)
        
        logging.basicConfig(
            level=getattr(logging, level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/tui.log'),
            ]
        )
    
    async def setup_services(self, args: argparse.Namespace) -> None:
        """設定服務"""
        # 建立共享狀態管理器
        self.state_manager = SharedStateManager()
        await self.state_manager.start()
        
        # 建立指令歷史管理器
        self.history_manager = CommandHistoryManager(
            history_db_path=args.history_db
        )
        
        # 建立服務協調器
        self.coordinator = ServiceCoordinator(
            health_check_interval=args.health_check_interval,
        )
        
        # 建立並註冊佇列服務
        queue_service = QueueService(
            queue_max_size=args.queue_size,
            max_workers=args.workers,
            poll_interval=args.poll_interval,
        )
        
        queue_config = ServiceConfig(
            name="queue_service",
            service_type="QueueService",
            enabled=True,
            auto_restart=True,
        )
        
        self.coordinator.register_service(queue_service, queue_config)
        
        # 啟動服務協調器
        success = await self.coordinator.start()
        if not success:
            logger.error("Failed to start service coordinator")
            raise RuntimeError("Service coordinator startup failed")
        
        # 建立 TUI 應用並傳入 service_manager
        self.tui_app = RobotConsoleTUI(
            coordinator=self.coordinator,
            state_manager=self.state_manager,
            history_manager=self.history_manager,
            service_manager=queue_service.manager  # 傳入 ServiceManager
        )
    
    async def cleanup_services(self) -> None:
        """清理服務"""
        if self.coordinator:
            await self.coordinator.stop(timeout=30.0)
        
        if self.state_manager:
            await self.state_manager.stop()
    
    async def run_async(self, args: argparse.Namespace) -> None:
        """非同步執行"""
        try:
            # 設定服務
            await self.setup_services(args)
            
            # 取得 queue_service 的 manager
            queue_service_info = self.coordinator.get_service_info("queue_service")
            service_manager = queue_service_info.manager if hasattr(queue_service_info, 'manager') else None
            
            # 建立並執行 TUI
            self.tui_app = RobotConsoleTUI(
                coordinator=self.coordinator,
                state_manager=self.state_manager,
                history_manager=self.history_manager,
                service_manager=service_manager,
            )
            
            await self.tui_app.run_async()
            
        finally:
            # 清理服務
            await self.cleanup_services()
    
    def run(self) -> int:
        """執行 TUI"""
        args = self.parse_args()
        self.setup_logging(args.log_level)
        
        try:
            asyncio.run(self.run_async(args))
            return 0
        except KeyboardInterrupt:
            logger.info("TUI interrupted by user")
            return 0
        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
            return 1


def main():
    """TUI 入口點"""
    runner = TUIRunner()
    sys.exit(runner.run())


if __name__ == '__main__':
    main()
