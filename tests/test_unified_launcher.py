"""
統一啟動器測試
測試 Electron 統一啟動器的服務協調功能
"""

import sys
from pathlib import Path
import pytest

# 添加 src 到路徑
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))


class TestServiceCoordinatorDesign:
    """測試服務協調器的設計結構"""
    
    def test_electron_main_js_exists(self):
        """確認 main.js 存在"""
        main_js_path = Path(__file__).parent.parent / 'electron-app' / 'main.js'
        assert main_js_path.exists(), "electron-app/main.js 不存在"
    
    def test_electron_preload_js_exists(self):
        """確認 preload.js 存在"""
        preload_path = Path(__file__).parent.parent / 'electron-app' / 'preload.js'
        assert preload_path.exists(), "electron-app/preload.js 不存在"
    
    def test_electron_renderer_exists(self):
        """確認 renderer 目錄存在"""
        renderer_path = Path(__file__).parent.parent / 'electron-app' / 'renderer'
        assert renderer_path.is_dir(), "electron-app/renderer/ 目錄不存在"
    
    def test_renderer_index_html_exists(self):
        """確認 index.html 存在"""
        index_path = Path(__file__).parent.parent / 'electron-app' / 'renderer' / 'index.html'
        assert index_path.exists(), "electron-app/renderer/index.html 不存在"
    
    def test_renderer_js_exists(self):
        """確認 renderer.js 存在"""
        renderer_js_path = Path(__file__).parent.parent / 'electron-app' / 'renderer' / 'renderer.js'
        assert renderer_js_path.exists(), "electron-app/renderer/renderer.js 不存在"


class TestMainJsStructure:
    """測試 main.js 的結構內容"""
    
    @pytest.fixture
    def main_js_content(self):
        """讀取 main.js 內容"""
        main_js_path = Path(__file__).parent.parent / 'electron-app' / 'main.js'
        return main_js_path.read_text(encoding='utf-8')
    
    def test_service_coordinator_defined(self, main_js_content):
        """確認服務協調器已定義"""
        assert 'serviceCoordinator' in main_js_content, "serviceCoordinator 未定義"
    
    def test_start_service_function_exists(self, main_js_content):
        """確認 startService 函數存在"""
        assert 'async function startService' in main_js_content, "startService 函數未定義"
    
    def test_stop_service_function_exists(self, main_js_content):
        """確認 stopService 函數存在"""
        assert 'async function stopService' in main_js_content, "stopService 函數未定義"
    
    def test_start_all_services_function_exists(self, main_js_content):
        """確認 startAllServices 函數存在"""
        assert 'async function startAllServices' in main_js_content, "startAllServices 函數未定義"
    
    def test_stop_all_services_function_exists(self, main_js_content):
        """確認 stopAllServices 函數存在"""
        assert 'async function stopAllServices' in main_js_content, "stopAllServices 函數未定義"
    
    def test_check_service_health_function_exists(self, main_js_content):
        """確認 checkServiceHealth 函數存在"""
        assert 'async function checkServiceHealth' in main_js_content, "checkServiceHealth 函數未定義"
    
    def test_check_all_services_health_function_exists(self, main_js_content):
        """確認 checkAllServicesHealth 函數存在"""
        assert 'async function checkAllServicesHealth' in main_js_content, "checkAllServicesHealth 函數未定義"
    
    def test_get_services_status_function_exists(self, main_js_content):
        """確認 getServicesStatus 函數存在"""
        assert 'function getServicesStatus' in main_js_content, "getServicesStatus 函數未定義"
    
    def test_ipc_handlers_defined(self, main_js_content):
        """確認 IPC 處理器已定義"""
        assert "ipcMain.handle('get-services-status'" in main_js_content, "get-services-status IPC 未定義"
        assert "ipcMain.handle('start-service'" in main_js_content, "start-service IPC 未定義"
        assert "ipcMain.handle('stop-service'" in main_js_content, "stop-service IPC 未定義"
        assert "ipcMain.handle('start-all-services'" in main_js_content, "start-all-services IPC 未定義"
        assert "ipcMain.handle('stop-all-services'" in main_js_content, "stop-all-services IPC 未定義"
    
    def test_flask_service_in_coordinator(self, main_js_content):
        """確認 Flask 服務已添加到協調器"""
        assert "flask:" in main_js_content, "Flask 服務未添加到 serviceCoordinator"
        assert "'Flask API 服務'" in main_js_content, "Flask 服務名稱未定義"
    
    def test_coordinator_config_defined(self, main_js_content):
        """確認協調器配置常數已定義"""
        assert 'COORDINATOR_CONFIG' in main_js_content, "COORDINATOR_CONFIG 常數未定義"
        assert 'maxRestartAttempts' in main_js_content, "maxRestartAttempts 未配置"
        assert 'healthCheckIntervalMs' in main_js_content, "healthCheckIntervalMs 未配置"
        assert 'healthCheckMaxRetries' in main_js_content, "healthCheckMaxRetries 未配置"
        assert 'healthCheckRetryDelayMs' in main_js_content, "healthCheckRetryDelayMs 未配置"
    
    def test_service_type_defined(self, main_js_content):
        """確認服務類型已定義"""
        assert "type: 'python-flask'" in main_js_content, "Flask 服務類型未定義"
    
    def test_cleanup_complete_flag(self, main_js_content):
        """確認清理完成標誌已定義"""
        assert 'cleanupComplete' in main_js_content, "cleanupComplete 標誌未定義"


class TestPreloadJsStructure:
    """測試 preload.js 的結構內容"""
    
    @pytest.fixture
    def preload_content(self):
        """讀取 preload.js 內容"""
        preload_path = Path(__file__).parent.parent / 'electron-app' / 'preload.js'
        return preload_path.read_text(encoding='utf-8')
    
    def test_electron_api_exposed(self, preload_content):
        """確認 electronAPI 已暴露"""
        assert 'electronAPI' in preload_content, "electronAPI 未暴露"
    
    def test_get_services_status_exposed(self, preload_content):
        """確認 getServicesStatus 方法已暴露"""
        assert 'getServicesStatus' in preload_content, "getServicesStatus 未暴露到 renderer"
    
    def test_start_service_exposed(self, preload_content):
        """確認 startService 方法已暴露"""
        assert 'startService' in preload_content, "startService 未暴露到 renderer"
    
    def test_stop_service_exposed(self, preload_content):
        """確認 stopService 方法已暴露"""
        assert 'stopService' in preload_content, "stopService 未暴露到 renderer"
    
    def test_start_all_services_exposed(self, preload_content):
        """確認 startAllServices 方法已暴露"""
        assert 'startAllServices' in preload_content, "startAllServices 未暴露到 renderer"
    
    def test_stop_all_services_exposed(self, preload_content):
        """確認 stopAllServices 方法已暴露"""
        assert 'stopAllServices' in preload_content, "stopAllServices 未暴露到 renderer"


class TestRendererHtmlStructure:
    """測試 index.html 的結構內容"""
    
    @pytest.fixture
    def html_content(self):
        """讀取 index.html 內容"""
        html_path = Path(__file__).parent.parent / 'electron-app' / 'renderer' / 'index.html'
        return html_path.read_text(encoding='utf-8')
    
    def test_unified_launcher_title(self, html_content):
        """確認頁面標題包含統一啟動器"""
        assert '統一啟動器' in html_content, "頁面標題未包含統一啟動器"
    
    def test_service_control_center(self, html_content):
        """確認服務控制中心存在"""
        assert '服務控制中心' in html_content, "服務控制中心未定義"
    
    def test_start_all_button_exists(self, html_content):
        """確認啟動所有服務按鈕存在"""
        assert 'start-all-btn' in html_content, "啟動所有服務按鈕未定義"
    
    def test_stop_all_button_exists(self, html_content):
        """確認停止所有服務按鈕存在"""
        assert 'stop-all-btn' in html_content, "停止所有服務按鈕未定義"
    
    def test_refresh_status_button_exists(self, html_content):
        """確認刷新狀態按鈕存在"""
        assert 'refresh-status-btn' in html_content, "刷新狀態按鈕未定義"
    
    def test_services_dashboard_exists(self, html_content):
        """確認服務監控儀表板存在"""
        assert 'services-dashboard' in html_content, "服務監控儀表板未定義"
    
    def test_phase_3_1_reference(self, html_content):
        """確認 Phase 3.1 引用存在"""
        assert 'Phase 3.1' in html_content, "Phase 3.1 引用不存在"


class TestRendererJsStructure:
    """測試 renderer.js 的結構內容"""
    
    @pytest.fixture
    def renderer_content(self):
        """讀取 renderer.js 內容"""
        renderer_path = Path(__file__).parent.parent / 'electron-app' / 'renderer' / 'renderer.js'
        return renderer_path.read_text(encoding='utf-8')
    
    def test_unified_launcher_comment(self, renderer_content):
        """確認統一啟動器註解存在"""
        assert '統一啟動器' in renderer_content, "統一啟動器註解不存在"
    
    def test_refresh_services_status_function(self, renderer_content):
        """確認 refreshServicesStatus 函數存在"""
        assert 'async function refreshServicesStatus' in renderer_content, "refreshServicesStatus 函數未定義"
    
    def test_render_services_dashboard_function(self, renderer_content):
        """確認 renderServicesDashboard 函數存在"""
        assert 'function renderServicesDashboard' in renderer_content, "renderServicesDashboard 函數未定義"
    
    def test_start_service_function_defined(self, renderer_content):
        """確認 startService 函數已定義"""
        assert 'async function startService' in renderer_content, "startService 函數未定義"
    
    def test_stop_service_function_defined(self, renderer_content):
        """確認 stopService 函數已定義"""
        assert 'async function stopService' in renderer_content, "stopService 函數未定義"
    
    def test_check_service_health_function_defined(self, renderer_content):
        """確認 checkServiceHealth 函數已定義"""
        assert 'async function checkServiceHealth' in renderer_content, "checkServiceHealth 函數未定義"
    
    def test_global_functions_exposed(self, renderer_content):
        """確認全域函數已暴露到命名空間"""
        assert 'window.LauncherServices' in renderer_content, "LauncherServices 命名空間未定義"
        assert 'LauncherServices.startService' in renderer_content, "startService 未使用命名空間"
        assert 'LauncherServices.stopService' in renderer_content, "stopService 未使用命名空間"
    
    def test_auto_refresh_interval(self, renderer_content):
        """確認自動刷新間隔已設置"""
        assert 'refreshInterval' in renderer_content, "自動刷新間隔未設置"
        assert 'REFRESH_INTERVAL_MS' in renderer_content, "REFRESH_INTERVAL_MS 常數未定義"
    
    def test_beforeunload_cleanup(self, renderer_content):
        """確認 beforeunload 清理已設置"""
        assert 'beforeunload' in renderer_content, "beforeunload 事件監聽器未設置"


class TestFlaskServiceIntegration:
    """測試 Flask 服務整合"""
    
    def test_flask_service_py_exists(self):
        """確認 flask_service.py 存在"""
        flask_service_path = Path(__file__).parent.parent / 'flask_service.py'
        assert flask_service_path.exists(), "flask_service.py 不存在"
    
    def test_flask_adapter_can_import(self):
        """確認 Flask adapter 可以導入"""
        try:
            from robot_service.electron import create_flask_app
            assert callable(create_flask_app), "create_flask_app 不是可呼叫的函數"
        except ImportError as e:
            pytest.fail(f"無法導入 Flask adapter: {e}")
    
    def test_service_manager_can_import(self):
        """確認 ServiceManager 可以導入"""
        try:
            from robot_service.service_manager import ServiceManager
            assert callable(ServiceManager), "ServiceManager 不是可呼叫的類別"
        except ImportError as e:
            pytest.fail(f"無法導入 ServiceManager: {e}")


class TestPythonServiceCoordinator:
    """測試 Python 服務協調器"""
    
    def test_service_coordinator_can_import(self):
        """確認 ServiceCoordinator 可以導入"""
        try:
            from robot_service.service_coordinator import ServiceCoordinator
            assert callable(ServiceCoordinator), "ServiceCoordinator 不是可呼叫的類別"
        except ImportError as e:
            pytest.fail(f"無法導入 ServiceCoordinator: {e}")
    
    def test_service_base_can_import(self):
        """確認 ServiceBase 可以導入"""
        try:
            from robot_service.service_coordinator import ServiceBase
            assert ServiceBase is not None, "ServiceBase 為 None"
        except ImportError as e:
            pytest.fail(f"無法導入 ServiceBase: {e}")
    
    def test_queue_service_can_import(self):
        """確認 QueueService 可以導入"""
        try:
            from robot_service.service_coordinator import QueueService
            assert callable(QueueService), "QueueService 不是可呼叫的類別"
        except ImportError as e:
            pytest.fail(f"無法導入 QueueService: {e}")
    
    def test_service_status_can_import(self):
        """確認 ServiceStatus 可以導入（從 common 模組）"""
        try:
            from common.service_types import ServiceStatus
            assert ServiceStatus.STOPPED is not None
            assert ServiceStatus.RUNNING is not None
            assert ServiceStatus.HEALTHY is not None
        except ImportError as e:
            pytest.fail(f"無法導入 ServiceStatus: {e}")
    
    def test_service_config_can_import(self):
        """確認 ServiceConfig 可以導入（從 common 模組）"""
        try:
            from common.service_types import ServiceConfig
            config = ServiceConfig(name="test", service_type="test")
            assert config.name == "test"
            assert config.enabled is True
        except ImportError as e:
            pytest.fail(f"無法導入 ServiceConfig: {e}")
    
    def test_service_coordinator_file_exists(self):
        """確認 service_coordinator.py 存在"""
        coordinator_path = Path(__file__).parent.parent / 'src' / 'robot_service' / 'service_coordinator.py'
        assert coordinator_path.exists(), "service_coordinator.py 不存在"
    
    def test_cli_runner_uses_coordinator(self):
        """確認 CLI runner 使用 ServiceCoordinator"""
        runner_path = Path(__file__).parent.parent / 'src' / 'robot_service' / 'cli' / 'runner.py'
        content = runner_path.read_text(encoding='utf-8')
        assert 'ServiceCoordinator' in content, "CLI runner 未使用 ServiceCoordinator"
        assert 'QueueService' in content, "CLI runner 未使用 QueueService"
