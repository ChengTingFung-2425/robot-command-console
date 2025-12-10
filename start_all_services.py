#!/usr/bin/env python3
"""
啟動所有服務的整合腳本
一鍵啟動 WebUI、MCP 和 Robot-Console 整合系統

使用方式：
    python3 start_all_services.py                    # 啟動所有服務
    python3 start_all_services.py --services mcp,webui  # 啟動指定服務
    python3 start_all_services.py --help             # 顯示幫助
"""

import argparse
import asyncio
import logging
import os
import signal
import subprocess
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ServiceType(Enum):
    """服務類型"""
    FLASK_API = "flask"
    MCP = "mcp"
    WEBUI = "webui"
    ROBOT_CONSOLE = "robot-console"
    UNIFIED_LAUNCHER = "unified"


@dataclass
class ServiceConfig:
    """服務配置"""
    name: str
    service_type: ServiceType
    command: List[str]
    working_dir: Optional[Path] = None
    env: Optional[Dict[str, str]] = None
    port: Optional[int] = None
    health_check_url: Optional[str] = None
    startup_delay: float = 2.0


class ServiceManager:
    """服務管理器"""

    def __init__(self):
        self.processes: Dict[str, subprocess.Popen] = {}
        self.running = False
        self.project_root = Path(__file__).parent.absolute()

    def get_service_configs(self) -> Dict[str, ServiceConfig]:
        """取得所有服務配置"""
        return {
            "flask": ServiceConfig(
                name="Flask API Service",
                service_type=ServiceType.FLASK_API,
                command=["python3", "flask_service.py"],
                working_dir=self.project_root,
                env={
                    "APP_TOKEN": os.environ.get("APP_TOKEN", self._generate_token()),
                    "PORT": "5000"
                },
                port=5000,
                health_check_url="http://127.0.0.1:5000/health",
                startup_delay=3.0
            ),
            "mcp": ServiceConfig(
                name="MCP Service",
                service_type=ServiceType.MCP,
                command=["python3", "start.py"],
                working_dir=self.project_root / "MCP",
                env={
                    "MCP_API_HOST": "0.0.0.0",
                    "MCP_API_PORT": "8000"
                },
                port=8000,
                health_check_url="http://127.0.0.1:8000/health",
                startup_delay=5.0
            ),
            "webui": ServiceConfig(
                name="WebUI Service",
                service_type=ServiceType.WEBUI,
                command=["python3", "microblog.py"],
                working_dir=self.project_root / "WebUI",
                env={
                    "MCP_API_URL": "http://localhost:8000/api",
                    "FLASK_APP": "microblog.py"
                },
                port=8080,
                health_check_url=None,  # WebUI 沒有 health endpoint
                startup_delay=3.0
            ),
            "robot-console": ServiceConfig(
                name="Robot-Console PubSub",
                service_type=ServiceType.ROBOT_CONSOLE,
                command=["python3", "pubsub.py"],
                working_dir=self.project_root / "Robot-Console",
                env={
                    "MQTT_ENDPOINT": os.environ.get("MQTT_ENDPOINT", "localhost"),
                    "MQTT_PORT": os.environ.get("MQTT_PORT", "1883")
                },
                port=None,
                health_check_url=None,
                startup_delay=2.0
            ),
            "unified": ServiceConfig(
                name="Unified Launcher",
                service_type=ServiceType.UNIFIED_LAUNCHER,
                command=["python3", "unified_launcher_cli.py"],
                working_dir=self.project_root,
                env={},
                port=None,
                health_check_url=None,
                startup_delay=2.0
            ),
        }

    def _generate_token(self) -> str:
        """生成安全 token"""
        import secrets
        return secrets.token_hex(32)

    async def start_service(self, service_id: str, config: ServiceConfig) -> bool:
        """啟動單一服務"""
        try:
            logger.info(f"🚀 啟動 {config.name}...")

            # 準備環境變數
            env = os.environ.copy()
            if config.env:
                env.update(config.env)

            # 啟動進程
            process = subprocess.Popen(
                config.command,
                cwd=config.working_dir,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True
            )

            self.processes[service_id] = process

            # 等待啟動
            await asyncio.sleep(config.startup_delay)

            # 檢查進程狀態
            if process.poll() is not None:
                # 進程已結束，讀取錯誤
                _, stderr = process.communicate()
                logger.error(f"❌ {config.name} 啟動失敗: {stderr}")
                return False

            # 如果有 health check URL，執行健康檢查
            if config.health_check_url:
                healthy = await self._health_check(config.health_check_url)
                if not healthy:
                    logger.warning(f"⚠️ {config.name} 健康檢查失敗")
                else:
                    logger.info(f"✅ {config.name} 啟動成功")
            else:
                logger.info(f"✅ {config.name} 已啟動")

            return True

        except Exception as e:
            logger.error(f"❌ 啟動 {config.name} 時發生錯誤: {e}")
            return False

    async def _health_check(self, url: str, max_retries: int = 5) -> bool:
        """執行健康檢查"""
        import aiohttp

        for i in range(max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=3)) as resp:
                        if resp.status == 200:
                            return True
            except Exception as e:
                logger.debug(f"健康檢查嘗試 {i+1}/{max_retries}: {e}")

            if i < max_retries - 1:
                await asyncio.sleep(1)

        return False

    async def start_all(self, service_ids: Optional[List[str]] = None):
        """啟動所有或指定服務"""
        configs = self.get_service_configs()

        # 如果沒指定，啟動所有服務（除了 unified launcher）
        if service_ids is None:
            service_ids = [sid for sid in configs.keys() if sid != "unified"]

        logger.info(f"📋 準備啟動服務: {', '.join(service_ids)}")

        # 按順序啟動
        success_count = 0
        for service_id in service_ids:
            if service_id not in configs:
                logger.warning(f"⚠️ 未知服務: {service_id}")
                continue

            config = configs[service_id]
            success = await self.start_service(service_id, config)
            if success:
                success_count += 1

        logger.info(f"\n{'='*60}")
        logger.info(f"✅ 成功啟動 {success_count}/{len(service_ids)} 個服務")
        logger.info(f"{'='*60}\n")

        # 顯示存取資訊
        self._show_access_info(service_ids, configs)

    def _show_access_info(self, service_ids: List[str], configs: Dict[str, ServiceConfig]):
        """顯示服務存取資訊"""
        logger.info("📍 服務存取資訊：")
        logger.info("")

        for service_id in service_ids:
            config = configs[service_id]
            if config.port:
                logger.info(f"  • {config.name}: http://localhost:{config.port}")

        logger.info("")
        logger.info("💡 提示：")
        logger.info("  - 使用 Ctrl+C 停止所有服務")
        logger.info("  - 查看日誌以了解服務狀態")
        logger.info("")

    def stop_all(self):
        """停止所有服務"""
        logger.info("\n🛑 停止所有服務...")

        for service_id, process in self.processes.items():
            try:
                logger.info(f"  停止 {service_id}...")
                process.terminate()

                # 等待最多 5 秒
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    logger.warning(f"  {service_id} 未在 5 秒內停止，強制終止...")
                    process.kill()
                    process.wait()

                logger.info(f"  ✅ {service_id} 已停止")
            except Exception as e:
                logger.error(f"  ❌ 停止 {service_id} 時發生錯誤: {e}")

        self.processes.clear()
        logger.info("✅ 所有服務已停止")

    async def run(self, service_ids: Optional[List[str]] = None):
        """啟動服務並持續運行"""
        self.running = True

        # 註冊信號處理器
        def signal_handler(signum, frame):
            logger.info("\n收到停止信號...")
            self.running = False

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        try:
            # 啟動服務
            await self.start_all(service_ids)

            # 持續運行並監控
            logger.info("🔄 服務運行中... (按 Ctrl+C 停止)")
            while self.running:
                await asyncio.sleep(1)

                # 檢查進程是否還活著
                for service_id, process in list(self.processes.items()):
                    if process.poll() is not None:
                        logger.error(f"⚠️ 檢測到 {service_id} 已停止")
                        # 可以選擇自動重啟
                        # await self.start_service(service_id, self.get_service_configs()[service_id])

        finally:
            self.stop_all()


def main():
    """主程式入口"""
    parser = argparse.ArgumentParser(
        description="啟動 WebUI/MCP/Robot-Console 整合系統",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
範例：
  python3 start_all_services.py                    # 啟動所有服務
  python3 start_all_services.py --services mcp,webui  # 只啟動 MCP 和 WebUI
  python3 start_all_services.py --list             # 列出所有可用服務
        """
    )

    parser.add_argument(
        '--services',
        type=str,
        help='要啟動的服務列表（逗號分隔），如: flask,mcp,webui'
    )

    parser.add_argument(
        '--list',
        action='store_true',
        help='列出所有可用服務'
    )

    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='日誌級別'
    )

    args = parser.parse_args()

    # 設定日誌級別
    logging.getLogger().setLevel(getattr(logging, args.log_level))

    manager = ServiceManager()

    # 列出服務
    if args.list:
        configs = manager.get_service_configs()
        print("\n可用服務：")
        for service_id, config in configs.items():
            port_info = f" (port {config.port})" if config.port else ""
            print(f"  • {service_id}: {config.name}{port_info}")
        print("")
        return

    # 解析服務列表
    service_ids = None
    if args.services:
        service_ids = [s.strip() for s in args.services.split(',')]

    # 啟動服務
    try:
        asyncio.run(manager.run(service_ids))
    except KeyboardInterrupt:
        logger.info("\n程式已被用戶中斷")
    except Exception as e:
        logger.error(f"發生錯誤: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
