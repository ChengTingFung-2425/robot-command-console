"""
測試統一啟動器
驗證一鍵啟動所有服務與健康檢查功能
"""

import asyncio
import sys
import os
import unittest
from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, MagicMock, patch

# 添加 src 目錄到路徑
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import pytest


class TestUnifiedLauncherExists:
    """測試統一啟動器檔案存在"""

    def test_unified_launcher_module_exists(self):
        """確認 unified_launcher.py 存在"""
        launcher_path = Path(__file__).parent.parent / 'src' / 'robot_service' / 'unified_launcher.py'
        assert launcher_path.exists(), "unified_launcher.py 不存在"

    def test_unified_launcher_cli_exists(self):
        """確認 unified_launcher_cli.py 存在"""
        cli_path = Path(__file__).parent.parent / 'unified_launcher_cli.py'
        assert cli_path.exists(), "unified_launcher_cli.py 不存在"


class TestUnifiedLauncherImports:
    """測試統一啟動器可導入"""

    def test_unified_launcher_can_import(self):
        """確認 UnifiedLauncher 可以導入"""
        try:
            from robot_service.unified_launcher import UnifiedLauncher
            assert callable(UnifiedLauncher), "UnifiedLauncher 不是可呼叫的類別"
        except ImportError as e:
            pytest.fail(f"無法導入 UnifiedLauncher: {e}")

    def test_process_service_can_import(self):
        """確認 ProcessService 可以導入"""
        try:
            from robot_service.unified_launcher import ProcessService
            assert callable(ProcessService), "ProcessService 不是可呼叫的類別"
        except ImportError as e:
            pytest.fail(f"無法導入 ProcessService: {e}")

    def test_process_service_config_can_import(self):
        """確認 ProcessServiceConfig 可以導入"""
        try:
            from robot_service.unified_launcher import ProcessServiceConfig
            assert ProcessServiceConfig is not None
        except ImportError as e:
            pytest.fail(f"無法導入 ProcessServiceConfig: {e}")

    def test_service_type_can_import(self):
        """確認 ServiceType 可以導入"""
        try:
            from robot_service.unified_launcher import ServiceType
            assert ServiceType.FLASK_API is not None
            assert ServiceType.MCP_SERVICE is not None
            assert ServiceType.QUEUE is not None
        except ImportError as e:
            pytest.fail(f"無法導入 ServiceType: {e}")


class TestProcessServiceConfig:
    """測試進程服務配置"""

    def test_default_config(self):
        """測試預設配置"""
        from robot_service.unified_launcher import ProcessServiceConfig, ServiceType

        config = ProcessServiceConfig(
            name="test_service",
            service_type=ServiceType.FLASK_API,
            command=["python3", "test.py"],
            port=5000,
            health_url="http://127.0.0.1:5000/health",
        )

        assert config.name == "test_service"
        assert config.service_type == ServiceType.FLASK_API
        assert config.port == 5000
        assert config.enabled is True
        assert config.startup_timeout_seconds == 10.0

    def test_config_with_env(self):
        """測試配置環境變數"""
        from robot_service.unified_launcher import ProcessServiceConfig, ServiceType

        config = ProcessServiceConfig(
            name="test_service",
            service_type=ServiceType.MCP_SERVICE,
            command=["python3", "-m", "MCP.start"],
            port=8000,
            health_url="http://127.0.0.1:8000/health",
            env={"API_KEY": "test-key"},
        )

        assert config.env == {"API_KEY": "test-key"}


class TestProcessService:
    """測試進程服務"""

    def test_service_name(self):
        """測試服務名稱"""
        from robot_service.unified_launcher import ProcessService, ProcessServiceConfig, ServiceType

        config = ProcessServiceConfig(
            name="test_service",
            service_type=ServiceType.FLASK_API,
            command=["python3", "test.py"],
            port=5000,
            health_url="http://127.0.0.1:5000/health",
        )

        service = ProcessService(config)
        assert service.name == "test_service"

    def test_service_initial_state(self):
        """測試服務初始狀態"""
        from robot_service.unified_launcher import ProcessService, ProcessServiceConfig, ServiceType

        config = ProcessServiceConfig(
            name="test_service",
            service_type=ServiceType.FLASK_API,
            command=["python3", "test.py"],
            port=5000,
            health_url="http://127.0.0.1:5000/health",
        )

        service = ProcessService(config)
        assert service.is_running is False


class TestUnifiedLauncher:
    """測試統一啟動器"""

    def test_launcher_initialization(self):
        """測試啟動器初始化"""
        from robot_service.unified_launcher import UnifiedLauncher

        launcher = UnifiedLauncher(
            health_check_interval=30.0,
            max_restart_attempts=3,
            restart_delay=2.0,
        )

        assert launcher is not None
        assert launcher.is_running is False

    def test_register_default_services(self):
        """測試註冊預設服務"""
        from robot_service.unified_launcher import UnifiedLauncher

        launcher = UnifiedLauncher()
        launcher.register_default_services()

        # 應該有服務被註冊
        status = launcher.get_services_status()
        assert len(status) >= 1, "應該至少有一個服務被註冊"

    def test_get_services_status(self):
        """測試取得服務狀態"""
        from robot_service.unified_launcher import UnifiedLauncher

        launcher = UnifiedLauncher()
        launcher.register_default_services()

        status = launcher.get_services_status()

        # 驗證狀態格式
        for service_name, service_status in status.items():
            assert "name" in service_status
            assert "status" in service_status
            assert "is_running" in service_status


class TestUnifiedLauncherAsync(unittest.IsolatedAsyncioTestCase):
    """非同步測試統一啟動器"""

    async def test_health_check_all(self):
        """測試統一健康檢查"""
        from robot_service.unified_launcher import UnifiedLauncher

        launcher = UnifiedLauncher()
        # 不註冊任何服務，只測試方法可執行

        result = await launcher.health_check_all()

        assert "overall_healthy" in result
        assert "services" in result
        assert "timestamp" in result


class TestUnifiedLauncherModuleContent:
    """測試統一啟動器模組內容"""

    @pytest.fixture
    def launcher_content(self):
        """讀取 unified_launcher.py 內容"""
        launcher_path = Path(__file__).parent.parent / 'src' / 'robot_service' / 'unified_launcher.py'
        return launcher_path.read_text(encoding='utf-8')

    def test_has_start_all_method(self, launcher_content):
        """確認有 start_all 方法"""
        assert "async def start_all" in launcher_content, "start_all 方法未定義"

    def test_has_stop_all_method(self, launcher_content):
        """確認有 stop_all 方法"""
        assert "async def stop_all" in launcher_content, "stop_all 方法未定義"

    def test_has_health_check_all_method(self, launcher_content):
        """確認有 health_check_all 方法"""
        assert "async def health_check_all" in launcher_content, "health_check_all 方法未定義"

    def test_has_process_service_class(self, launcher_content):
        """確認有 ProcessService 類別"""
        assert "class ProcessService" in launcher_content, "ProcessService 類別未定義"

    def test_has_unified_launcher_class(self, launcher_content):
        """確認有 UnifiedLauncher 類別"""
        assert "class UnifiedLauncher" in launcher_content, "UnifiedLauncher 類別未定義"

    def test_has_main_function(self, launcher_content):
        """確認有 main 函式"""
        assert "def main():" in launcher_content, "main 函式未定義"

    def test_uses_service_coordinator(self, launcher_content):
        """確認使用 ServiceCoordinator"""
        assert "ServiceCoordinator" in launcher_content, "未使用 ServiceCoordinator"

    def test_has_health_check_documentation(self, launcher_content):
        """確認有健康檢查相關文檔"""
        assert "健康檢查" in launcher_content, "健康檢查文檔缺失"

    def test_has_one_click_documentation(self, launcher_content):
        """確認有一鍵啟動相關文檔"""
        assert "一鍵" in launcher_content, "一鍵啟動/停止文檔缺失"


class TestUnifiedLauncherCLI:
    """測試統一啟動器 CLI"""

    @pytest.fixture
    def cli_content(self):
        """讀取 unified_launcher_cli.py 內容"""
        cli_path = Path(__file__).parent.parent / 'unified_launcher_cli.py'
        return cli_path.read_text(encoding='utf-8')

    def test_cli_imports_main(self, cli_content):
        """確認 CLI 導入 main 函式"""
        assert "from robot_service.unified_launcher import main" in cli_content, \
            "CLI 未導入 main 函式"

    def test_cli_has_main_block(self, cli_content):
        """確認 CLI 有 main 區塊"""
        assert "if __name__ == '__main__':" in cli_content, "CLI 缺少 main 區塊"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
