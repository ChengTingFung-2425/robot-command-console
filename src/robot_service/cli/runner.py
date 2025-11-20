"""
CLI Runner
獨立 CLI 模式的服務啟動器
"""

import argparse
import asyncio
import logging
import signal
import sys
from typing import Optional

from ..service_manager import ServiceManager


logger = logging.getLogger(__name__)


class CLIRunner:
    """
    CLI 執行器
    
    提供獨立 CLI 模式：
    - 不依賴 Electron
    - 可作為系統服務執行
    - 支援命令列參數配置
    """
    
    def __init__(self):
        self.service_manager: Optional[ServiceManager] = None
        self._shutdown_event = asyncio.Event()
    
    def parse_args(self) -> argparse.Namespace:
        """解析命令列參數"""
        parser = argparse.ArgumentParser(
            description='Robot Service - Standalone CLI Mode'
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
            help='Number of worker threads (default: 5)'
        )
        
        parser.add_argument(
            '--poll-interval',
            type=float,
            default=0.1,
            help='Queue poll interval in seconds (default: 0.1)'
        )
        
        parser.add_argument(
            '--log-level',
            choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
            default='INFO',
            help='Logging level (default: INFO)'
        )
        
        return parser.parse_args()
    
    def setup_logging(self, level: str) -> None:
        """設定日誌"""
        logging.basicConfig(
            level=getattr(logging, level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler(sys.stdout)]
        )
    
    def setup_signal_handlers(self) -> None:
        """設定信號處理器"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down...")
            self._shutdown_event.set()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def run_async(self, args: argparse.Namespace) -> None:
        """非同步執行"""
        logger.info("Starting Robot Service in CLI mode")
        logger.info(f"Configuration: queue_size={args.queue_size}, "
                   f"workers={args.workers}, poll_interval={args.poll_interval}")
        
        # 建立服務管理器
        self.service_manager = ServiceManager(
            queue_max_size=args.queue_size,
            max_workers=args.workers,
            poll_interval=args.poll_interval,
        )
        
        # 啟動服務
        await self.service_manager.start()
        
        logger.info("Robot Service started successfully")
        logger.info("Press Ctrl+C to stop")
        
        # 等待關閉信號
        await self._shutdown_event.wait()
        
        logger.info("Shutting down Robot Service...")
        
        # 停止服務
        await self.service_manager.stop(timeout=30.0)
        
        logger.info("Robot Service stopped")
    
    def run(self) -> int:
        """執行 CLI"""
        args = self.parse_args()
        self.setup_logging(args.log_level)
        self.setup_signal_handlers()
        
        try:
            asyncio.run(self.run_async(args))
            return 0
        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
            return 1


def main():
    """CLI 入口點"""
    runner = CLIRunner()
    sys.exit(runner.run())


if __name__ == '__main__':
    main()
