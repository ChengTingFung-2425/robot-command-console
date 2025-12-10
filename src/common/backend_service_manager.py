"""
統一後端服務管理器
供 Electron 和 PyQt 應用使用，自動啟動和管理所有後端服務

此模組負責：
1. 自動啟動 Flask API、MCP Service、WebUI 等後端服務
2. 隱藏底層進程細節（除非啟用除錯模式）
3. 提供簡單的啟動/停止介面
4. 自動健康檢查與錯誤恢復
"""

import asyncio
import logging
import os
import secrets
import subprocess
import sys
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import aiohttp
except ImportError:
    aiohttp = None

logger = logging.getLogger(__name__)


class ServiceType(Enum):
    """服務類型"""
    FLASK_API = "flask-api"
    MCP = "mcp"
    WEBUI = "webui"
    ROBOT_CONSOLE = "robot-console"


@dataclass
class ServiceConfig:
    """服務配置"""
    name: str
    service_type: ServiceType
    command: List[str]
    working_dir: Path
    env: Dict[str, str]
    port: Optional[int]
    health_url: Optional[str]
    startup_delay: float = 2.0
    enabled: bool = True


class BackendServiceManager:
    """
    統一後端服務管理器
    
    用於 Electron 和 PyQt 應用，自動啟動所有必要的後端服務
    """

    def __init__(self, project_root: Optional[Path] = None, debug_mode: bool = False):
        """
        初始化服務管理器
        
        Args:
            project_root: 專案根目錄，如果為 None 則自動偵測
            debug_mode: 內部參數，不對外公開
        """
        self.project_root = project_root or self._detect_project_root()
        self.debug_mode = self._check_secret_debug_mode() or debug_mode
        self.processes: Dict[str, subprocess.Popen] = {}
        self.tokens: Dict[str, str] = {}
        self.running = False
        
        # 配置日誌級別
        if not self.debug_mode:
            # 一般模式：只顯示警告和錯誤
            logging.getLogger().setLevel(logging.WARNING)
        else:
            # 秘密除錯模式：顯示所有資訊
            logging.getLogger().setLevel(logging.DEBUG)
            logger.debug("Internal diagnostics enabled")
            
            # 生成除錯文件
            try:
                from .debug_docs_manager import ensure_debug_docs
                if ensure_debug_docs():
                    logger.debug("Debug documentation generated at docs/developer/")
            except Exception as e:
                logger.debug(f"Could not generate debug docs: {e}")

    def _check_secret_debug_mode(self) -> bool:
        """
        檢查是否啟用秘密除錯模式
        
        秘密除錯模式啟用方式（開發者專用）：
        必須同時滿足以下三個條件：
        1. 環境變數: __ROBOT_INTERNAL_DEBUG__=1
        2. 檔案標記: .robot_debug 存在於專案根目錄
        3. 特殊埠號: 環境變數 DEBUG_PORT=54321
        """
        # 檢查方法 1: 特殊環境變數
        has_env_var = os.environ.get('__ROBOT_INTERNAL_DEBUG__') == '1'
        
        # 檢查方法 2: 隱藏檔案標記
        debug_file = self._detect_project_root() / '.robot_debug'
        has_debug_file = debug_file.exists()
        
        # 檢查方法 3: 特殊埠號組合
        has_debug_port = os.environ.get('DEBUG_PORT') == '54321'
        
        # 必須三個條件同時滿足
        return has_env_var and has_debug_file and has_debug_port
    
    def _detect_project_root(self) -> Path:
        """自動偵測專案根目錄"""
        current = Path(__file__).parent
        
        # 向上查找，直到找到包含 MCP、WebUI 和 Robot-Console 的目錄
        for _ in range(5):  # 最多向上查找 5 層
            if all([
                (current / "MCP").exists(),
                (current / "WebUI").exists(),
                (current / "Robot-Console").exists()
            ]):
                return current
            current = current.parent
        
        # 如果找不到，回退到 __file__ 的上上層
        return Path(__file__).parent.parent.parent

    def _generate_token(self) -> str:
        """生成安全 token"""
        return secrets.token_hex(32)

    def get_service_configs(self) -> Dict[str, ServiceConfig]:
        """
        取得所有服務配置
        
        這裡定義了需要啟動的所有後端服務
        """
        # 生成統一的 API token
        api_token = self.tokens.get("api", self._generate_token())
        self.tokens["api"] = api_token
        
        configs = {
            "flask": ServiceConfig(
                name="Flask API",
                service_type=ServiceType.FLASK_API,
                command=["python3", "flask_service.py"],
                working_dir=self.project_root,
                env={
                    "APP_TOKEN": api_token,
                    "PORT": "5000",
                    "FLASK_ENV": "production"
                },
                port=5000,
                health_url="http://127.0.0.1:5000/health",
                startup_delay=3.0
            ),
            "mcp": ServiceConfig(
                name="MCP Service",
                service_type=ServiceType.MCP,
                command=["python3", "start.py"],
                working_dir=self.project_root / "MCP",
                env={
                    "MCP_API_HOST": "127.0.0.1",  # 只監聽本地
                    "MCP_API_PORT": "8000",
                    "MCP_JWT_SECRET": self._generate_token()
                },
                port=8000,
                health_url="http://127.0.0.1:8000/health",
                startup_delay=5.0
            ),
        }
        
        # WebUI 是可選的（如果已經整合到前端應用中則不需要）
        if os.environ.get("START_WEBUI", "false").lower() == "true":
            configs["webui"] = ServiceConfig(
                name="WebUI",
                service_type=ServiceType.WEBUI,
                command=["python3", "microblog.py"],
                working_dir=self.project_root / "WebUI",
                env={
                    "MCP_API_URL": "http://localhost:8000/api",
                    "SECRET_KEY": self._generate_token()
                },
                port=8080,
                health_url=None,  # WebUI 沒有 health endpoint
                startup_delay=3.0,
                enabled=False  # 預設不啟動（前端已整合）
            )
        
        return configs

    async def start_service(self, service_id: str, config: ServiceConfig) -> bool:
        """
        啟動單一服務
        
        Args:
            service_id: 服務 ID
            config: 服務配置
            
        Returns:
            是否啟動成功
        """
        try:
            if self.debug_mode:
                logger.debug(f"正在啟動 {config.name}...")
            
            # 準備環境變數
            env = os.environ.copy()
            env.update(config.env)
            
            # 啟動進程
            process = subprocess.Popen(
                config.command,
                cwd=config.working_dir,
                env=env,
                stdout=subprocess.PIPE if not self.debug_mode else None,
                stderr=subprocess.PIPE if not self.debug_mode else None,
                text=True
            )
            
            self.processes[service_id] = process
            
            # 等待啟動
            await asyncio.sleep(config.startup_delay)
            
            # 檢查進程是否還活著
            if process.poll() is not None:
                logger.error(f"{config.name} 啟動失敗")
                return False
            
            # 執行健康檢查（如果有）
            if config.health_url:
                healthy = await self._health_check(config.health_url)
                if not healthy:
                    logger.warning(f"{config.name} 健康檢查失敗")
                    if self.debug_mode:
                        logger.debug(f"健康檢查 URL: {config.health_url}")
                else:
                    if self.debug_mode:
                        logger.debug(f"{config.name} 啟動成功並通過健康檢查")
            else:
                if self.debug_mode:
                    logger.debug(f"{config.name} 已啟動")
            
            return True
            
        except Exception as e:
            logger.error(f"啟動 {config.name} 時發生錯誤: {e}")
            if self.debug_mode:
                logger.exception("詳細錯誤資訊：")
            return False

    async def _health_check(self, url: str, max_retries: int = 5) -> bool:
        """執行健康檢查"""
        if aiohttp is None:
            # 如果沒有 aiohttp，使用 urllib
            import urllib.request
            for i in range(max_retries):
                try:
                    with urllib.request.urlopen(url, timeout=3) as response:
                        if response.status == 200:
                            return True
                except Exception as e:
                    if self.debug_mode:
                        logger.debug(f"健康檢查嘗試 {i+1}/{max_retries}: {e}")
                
                if i < max_retries - 1:
                    await asyncio.sleep(1)
            return False
        
        # 使用 aiohttp
        for i in range(max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=3)) as resp:
                        if resp.status == 200:
                            return True
            except Exception as e:
                if self.debug_mode:
                    logger.debug(f"健康檢查嘗試 {i+1}/{max_retries}: {e}")
            
            if i < max_retries - 1:
                await asyncio.sleep(1)
        
        return False

    async def start_all(self) -> Tuple[int, int]:
        """
        啟動所有服務
        
        Returns:
            (成功數, 總數) 的元組
        """
        if self.running:
            logger.warning("服務已在運行中")
            return (0, 0)
        
        configs = self.get_service_configs()
        enabled_configs = {k: v for k, v in configs.items() if v.enabled}
        
        if not self.debug_mode:
            # 一般模式：簡單的啟動訊息
            logger.info("正在啟動後端服務...")
        else:
            # 除錯模式：詳細的啟動訊息
            logger.info(f"準備啟動 {len(enabled_configs)} 個服務")
        
        success_count = 0
        for service_id, config in enabled_configs.items():
            success = await self.start_service(service_id, config)
            if success:
                success_count += 1
        
        self.running = True
        
        if not self.debug_mode:
            # 一般模式：只報告結果
            if success_count == len(enabled_configs):
                logger.info("所有後端服務已就緒")
            else:
                logger.warning(f"部分服務啟動失敗 ({success_count}/{len(enabled_configs)})")
        else:
            # 除錯模式：詳細報告
            logger.info(f"服務啟動完成: {success_count}/{len(enabled_configs)} 成功")
        
        return (success_count, len(enabled_configs))

    def stop_all(self):
        """停止所有服務"""
        if not self.running:
            return
        
        if self.debug_mode:
            logger.debug("正在停止所有服務...")
        
        for service_id, process in self.processes.items():
            try:
                if self.debug_mode:
                    logger.debug(f"停止 {service_id}...")
                
                process.terminate()
                
                # 等待最多 5 秒
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    if self.debug_mode:
                        logger.debug(f"{service_id} 未在 5 秒內停止，強制終止...")
                    process.kill()
                    process.wait()
                
                if self.debug_mode:
                    logger.debug(f"{service_id} 已停止")
                    
            except Exception as e:
                logger.error(f"停止 {service_id} 時發生錯誤: {e}")
        
        self.processes.clear()
        self.running = False
        
        if self.debug_mode:
            logger.debug("所有服務已停止")

    def get_service_url(self, service_id: str) -> Optional[str]:
        """
        取得服務的 URL
        
        Args:
            service_id: 服務 ID（如 'flask', 'mcp'）
            
        Returns:
            服務 URL 或 None
        """
        configs = self.get_service_configs()
        if service_id in configs and configs[service_id].port:
            return f"http://127.0.0.1:{configs[service_id].port}"
        return None

    def get_api_token(self) -> Optional[str]:
        """取得 API token（用於前端請求）"""
        return self.tokens.get("api")

    def is_running(self) -> bool:
        """檢查服務是否運行中"""
        return self.running

    def __enter__(self):
        """Context manager 進入"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager 退出"""
        self.stop_all()


# 提供同步介面（用於非 asyncio 環境）
class BackendServiceManagerSync:
    """同步版本的服務管理器（用於不支援 asyncio 的環境）"""
    
    def __init__(self, project_root: Optional[Path] = None, debug_mode: bool = False):
        self.manager = BackendServiceManager(project_root, debug_mode)
    
    def start_all(self) -> Tuple[int, int]:
        """啟動所有服務（同步）"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.manager.start_all())
        finally:
            loop.close()
    
    def stop_all(self):
        """停止所有服務"""
        self.manager.stop_all()
    
    def get_service_url(self, service_id: str) -> Optional[str]:
        """取得服務 URL"""
        return self.manager.get_service_url(service_id)
    
    def get_api_token(self) -> Optional[str]:
        """取得 API token"""
        return self.manager.get_api_token()
    
    def is_running(self) -> bool:
        """檢查是否運行中"""
        return self.manager.is_running()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop_all()


if __name__ == '__main__':
    # 測試模式
    import argparse
    
    parser = argparse.ArgumentParser(description="後端服務管理器測試")
    parser.add_argument('--debug', action='store_true', help='啟用除錯模式')
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    async def test():
        manager = BackendServiceManager(debug_mode=args.debug)
        
        try:
            print("\n" + "="*60)
            print("啟動後端服務...")
            print("="*60 + "\n")
            
            success, total = await manager.start_all()
            
            print("\n" + "="*60)
            print(f"啟動完成: {success}/{total} 個服務成功")
            print("="*60)
            print(f"\nFlask API: {manager.get_service_url('flask')}")
            print(f"MCP Service: {manager.get_service_url('mcp')}")
            print("API Token is generated and available for use.")
            print("\n按 Ctrl+C 停止...")
            
            # 持續運行
            while True:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            print("\n\n正在停止服務...")
            manager.stop_all()
            print("服務已停止")
    
    asyncio.run(test())
