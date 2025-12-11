#!/usr/bin/env python3
"""
Batch CLI Runner

批次指令執行的 CLI 入口點，專注於無頭部署環境的批次操作。
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# 添加 src 到路徑
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from robot_service.batch import (
    BatchParser,
    BatchExecutor,
    ProgressTracker,
    ResultExporter
)
from robot_service.service_coordinator import ServiceCoordinator, QueueService
from robot_service.command_history_manager import CommandHistoryManager
from common.service_types import ServiceConfig

logger = logging.getLogger(__name__)


class BatchCLI:
    """批次 CLI 執行器"""
    
    def __init__(self):
        self.coordinator = None
        self.service_manager = None
        self.history_manager = None
        self.parser = BatchParser()
        self.exporter = ResultExporter()
    
    async def setup_services(self):
        """設定服務"""
        logger.info("Setting up services...")
        
        # 建立服務協調器
        self.coordinator = ServiceCoordinator(health_check_interval=60.0)
        
        # 建立佇列服務
        queue_service = QueueService(
            queue_max_size=10000,
            max_workers=10,
            poll_interval=0.1,
        )
        
        queue_config = ServiceConfig(
            name="queue_service",
            service_type="QueueService",
            enabled=True,
            auto_restart=True,
        )
        
        self.coordinator.register_service(queue_service, queue_config)
        
        # 啟動服務
        success = await self.coordinator.start()
        if not success:
            raise RuntimeError("Failed to start services")
        
        # 取得 service_manager
        self.service_manager = queue_service.service_manager
        
        # 建立歷史管理器
        self.history_manager = CommandHistoryManager(
            history_db_path="data/batch_history.db",
            cache_max_size=1000,
            cache_ttl_seconds=3600,
        )
        
        logger.info("Services started successfully")
    
    async def cleanup_services(self):
        """清理服務"""
        if self.coordinator:
            logger.info("Stopping services...")
            await self.coordinator.stop(timeout=30.0)
            logger.info("Services stopped")
    
    async def run_batch(self, args: argparse.Namespace):
        """
        執行批次
        
        Args:
            args: 命令列參數
        """
        try:
            # 設定服務
            await self.setup_services()
            
            # 解析批次檔案
            logger.info(f"Parsing batch file: {args.file}")
            
            if args.stdin:
                # 從標準輸入讀取
                content = sys.stdin.read()
                batch_spec = self.parser.parse_string(content, format=args.format or "json")
            else:
                # 從檔案讀取
                batch_spec = self.parser.parse_file(args.file)
            
            # 驗證批次
            self.parser.validate(batch_spec)
            
            logger.info(f"Batch loaded: {batch_spec.batch_id}, "
                        f"{len(batch_spec.commands)} commands")
            
            # 應用命令列參數覆寫
            if args.max_parallel:
                batch_spec.options.max_parallel = args.max_parallel
            
            if args.dry_run:
                batch_spec.options.dry_run = True
            
            # 建立執行器
            executor = BatchExecutor(
                service_manager=self.service_manager,
                history_manager=self.history_manager,
                max_parallel=batch_spec.options.max_parallel
            )
            
            # 建立進度追蹤器（如果需要）
            tracker = None
            if args.monitor:
                tracker = ProgressTracker()
                tracker.start_batch(batch_spec.batch_id, len(batch_spec.commands))
                print("\nStarting batch execution...")
                print(tracker.render_summary())
            
            # 執行批次
            logger.info("Executing batch...")
            result = await executor.execute_batch(
                batch_spec,
                dry_run=args.dry_run
            )
            
            # 輸出結果
            if args.output:
                logger.info(f"Exporting result to: {args.output}")
                self.exporter.export(result, args.output, format=args.format)
            
            # 列印摘要
            if args.monitor or not args.quiet:
                self.exporter.print_summary(result)
            
            # 返回狀態碼
            if result.failed > 0 or result.timeout > 0:
                return 1
            else:
                return 0
        
        finally:
            await self.cleanup_services()
    
    def parse_args(self) -> argparse.Namespace:
        """解析命令列參數"""
        parser = argparse.ArgumentParser(
            description='Robot Command Console - Batch CLI',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  # 執行 JSON 批次檔案
  python3 run_batch_cli.py --file batch.json
  
  # 乾跑模式（不實際執行）
  python3 run_batch_cli.py --file batch.json --dry-run
  
  # 輸出結果到 CSV
  python3 run_batch_cli.py --file batch.json --output results.csv
  
  # 監控模式（顯示進度）
  python3 run_batch_cli.py --file batch.json --monitor
  
  # 從標準輸入讀取
  cat batch.json | python3 run_batch_cli.py --stdin --format json
            """
        )
        
        parser.add_argument(
            '--file',
            type=str,
            help='Batch file path (JSON/YAML/CSV)'
        )
        
        parser.add_argument(
            '--stdin',
            action='store_true',
            help='Read batch from stdin'
        )
        
        parser.add_argument(
            '--format',
            type=str,
            choices=['json', 'yaml', 'csv'],
            help='Force input/output format (auto-detect if not specified)'
        )
        
        parser.add_argument(
            '--output',
            type=str,
            help='Output result file path'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Dry run mode (do not execute commands)'
        )
        
        parser.add_argument(
            '--monitor',
            action='store_true',
            help='Monitor mode (show progress)'
        )
        
        parser.add_argument(
            '--max-parallel',
            type=int,
            help='Maximum parallel execution count'
        )
        
        parser.add_argument(
            '--log-level',
            type=str,
            choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
            default='INFO',
            help='Logging level (default: INFO)'
        )
        
        parser.add_argument(
            '--quiet',
            action='store_true',
            help='Quiet mode (no summary output)'
        )
        
        return parser.parse_args()
    
    def setup_logging(self, level: str):
        """設定日誌"""
        logging.basicConfig(
            level=getattr(logging, level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler(sys.stdout)]
        )
    
    def run(self) -> int:
        """執行 CLI"""
        args = self.parse_args()
        
        # 驗證參數
        if not args.file and not args.stdin:
            print("Error: Either --file or --stdin must be specified", file=sys.stderr)
            return 1
        
        if args.file and args.stdin:
            print("Error: Cannot use both --file and --stdin", file=sys.stderr)
            return 1
        
        # 設定日誌
        self.setup_logging(args.log_level)
        
        # 執行批次
        try:
            return asyncio.run(self.run_batch(args))
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
            return 130
        except Exception as e:
            logger.error(f"Fatal error: {e}", exc_info=True)
            return 1


def main():
    """CLI 入口點"""
    cli = BatchCLI()
    sys.exit(cli.run())


if __name__ == '__main__':
    main()
