"""
統一啟動器測試
測試 Electron 統一啟動器的服務協調功能
"""

import os
import sys
import pytest

# 添加 src 到路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class TestServiceCoordinatorDesign:
    """測試服務協調器的設計結構"""
    
    def test_electron_main_js_exists(self):
        """確認 main.js 存在"""
        main_js_path = os.path.join(
            os.path.dirname(__file__), 
            '..', 'electron-app', 'main.js'
        )
        assert os.path.exists(main_js_path), "electron-app/main.js 不存在"
    
    def test_electron_preload_js_exists(self):
        """確認 preload.js 存在"""
        preload_path = os.path.join(
            os.path.dirname(__file__), 
            '..', 'electron-app', 'preload.js'
        )
        assert os.path.exists(preload_path), "electron-app/preload.js 不存在"
    
    def test_electron_renderer_exists(self):
        """確認 renderer 目錄存在"""
        renderer_path = os.path.join(
            os.path.dirname(__file__), 
            '..', 'electron-app', 'renderer'
        )
        assert os.path.isdir(renderer_path), "electron-app/renderer/ 目錄不存在"
    
    def test_renderer_index_html_exists(self):
        """確認 index.html 存在"""
        index_path = os.path.join(
            os.path.dirname(__file__), 
            '..', 'electron-app', 'renderer', 'index.html'
        )
        assert os.path.exists(index_path), "electron-app/renderer/index.html 不存在"
    
    def test_renderer_js_exists(self):
        """確認 renderer.js 存在"""
        renderer_js_path = os.path.join(
            os.path.dirname(__file__), 
            '..', 'electron-app', 'renderer', 'renderer.js'
        )
        assert os.path.exists(renderer_js_path), "electron-app/renderer/renderer.js 不存在"


class TestMainJsStructure:
    """測試 main.js 的結構內容"""
    
    @pytest.fixture
    def main_js_content(self):
        """讀取 main.js 內容"""
        main_js_path = os.path.join(
            os.path.dirname(__file__), 
            '..', 'electron-app', 'main.js'
        )
        with open(main_js_path, 'r', encoding='utf-8') as f:
            return f.read()
    
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
    
    def test_service_type_defined(self, main_js_content):
        """確認服務類型已定義"""
        assert "type: 'python-flask'" in main_js_content, "Flask 服務類型未定義"


class TestPreloadJsStructure:
    """測試 preload.js 的結構內容"""
    
    @pytest.fixture
    def preload_content(self):
        """讀取 preload.js 內容"""
        preload_path = os.path.join(
            os.path.dirname(__file__), 
            '..', 'electron-app', 'preload.js'
        )
        with open(preload_path, 'r', encoding='utf-8') as f:
            return f.read()
    
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
        html_path = os.path.join(
            os.path.dirname(__file__), 
            '..', 'electron-app', 'renderer', 'index.html'
        )
        with open(html_path, 'r', encoding='utf-8') as f:
            return f.read()
    
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
        renderer_path = os.path.join(
            os.path.dirname(__file__), 
            '..', 'electron-app', 'renderer', 'renderer.js'
        )
        with open(renderer_path, 'r', encoding='utf-8') as f:
            return f.read()
    
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


class TestFlaskServiceIntegration:
    """測試 Flask 服務整合"""
    
    def test_flask_service_py_exists(self):
        """確認 flask_service.py 存在"""
        flask_service_path = os.path.join(
            os.path.dirname(__file__), 
            '..', 'flask_service.py'
        )
        assert os.path.exists(flask_service_path), "flask_service.py 不存在"
    
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
