"""
Tiny 版本 Flask 服務管理器測試

測試 FlaskManager 類別的核心功能：
1. 埠號尋找邏輯
2. Flask 服務啟動與停止
3. 健康檢查機制
4. 自動重啟邏輯
5. 錯誤處理情境
"""

import sys
import os
import time
from unittest.mock import Mock, patch, MagicMock
import socket

# 添加專案路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'qtwebview-app'))

import pytest

# 由於 PyQt6 可能未安裝，我們模擬導入
try:
    from flask_manager import FlaskManager
except ImportError:
    pytest.skip("PyQt6 未安裝，跳過 Tiny 版本測試", allow_module_level=True)


class TestFlaskManager:
    """Flask 服務管理器測試"""
    
    def test_find_available_port_success(self):
        """測試成功尋找可用埠號"""
        manager = FlaskManager(base_port=5100)
        port = manager._find_available_port(start_port=5100, max_attempts=10)
        
        assert isinstance(port, int)
        assert 5100 <= port < 5110
        
        # 驗證埠號確實可用
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('127.0.0.1', port))
    
    def test_find_available_port_all_occupied(self):
        """測試所有埠號都被佔用的情況"""
        manager = FlaskManager()
        
        # 佔用一些埠號
        sockets = []
        for port in range(5100, 5105):
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.bind(('127.0.0.1', port))
                sockets.append(s)
            except OSError:
                pass
        
        try:
            # 應該能找到其他可用埠號
            port = manager._find_available_port(start_port=5100, max_attempts=100)
            assert port >= 5105
        finally:
            # 清理
            for s in sockets:
                s.close()
    
    def test_generate_token(self):
        """測試 token 生成"""
        manager = FlaskManager()
        token = manager._generate_token()
        
        assert isinstance(token, str)
        assert len(token) == 64  # 32 bytes hex = 64 characters
        assert all(c in '0123456789abcdef' for c in token)
    
    @patch('flask_manager.subprocess.Popen')
    @patch('flask_manager.requests.get')
    def test_start_service_success(self, mock_get, mock_popen):
        """測試成功啟動 Flask 服務"""
        # Mock subprocess
        mock_process = Mock()
        mock_process.pid = 12345
        mock_popen.return_value = mock_process
        
        # Mock health check
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        manager = FlaskManager()
        
        with patch.object(manager, '_start_health_check'):
            with patch.object(manager, '_start_output_readers'):
                result = manager.start()
        
        assert result is True
        assert manager.port is not None
        assert manager.token is not None
        assert manager.process == mock_process
        mock_popen.assert_called_once()
    
    @patch('flask_manager.subprocess.Popen')
    @patch('flask_manager.requests.get')
    def test_start_service_timeout(self, mock_get, mock_popen):
        """測試服務啟動超時"""
        mock_process = Mock()
        mock_process.pid = 12345
        mock_popen.return_value = mock_process
        
        # Health check 總是失敗
        mock_get.side_effect = Exception("Connection refused")
        
        manager = FlaskManager()
        
        with patch.object(manager, '_start_output_readers'):
            result = manager.start()
        
        assert result is False
    
    def test_stop_service(self):
        """測試停止服務"""
        manager = FlaskManager()
        
        # Mock process
        mock_process = Mock()
        mock_process.poll.return_value = None
        manager.process = mock_process
        
        manager.stop()
        
        mock_process.terminate.assert_called_once()
        mock_process.wait.assert_called()
        assert manager.process is None
    
    @patch('flask_manager.requests.get')
    def test_is_healthy_true(self, mock_get):
        """測試健康檢查 - 健康"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        manager = FlaskManager()
        manager.port = 5100
        manager.process = Mock()
        manager.process.poll.return_value = None
        
        assert manager.is_healthy() is True
    
    @patch('flask_manager.requests.get')
    def test_is_healthy_false_process_died(self, mock_get):
        """測試健康檢查 - 進程已死亡"""
        manager = FlaskManager()
        manager.port = 5100
        manager.process = Mock()
        manager.process.poll.return_value = 1  # 進程已退出
        
        assert manager.is_healthy() is False
    
    def test_is_healthy_false_http_error(self):
        """測試健康檢查 - HTTP 錯誤"""
        import requests
        
        manager = FlaskManager()
        manager.port = 5100
        manager.process = Mock()
        manager.process.poll.return_value = None
        
        with patch('requests.get', side_effect=requests.RequestException("Connection refused")):
            assert manager.is_healthy() is False
    
    def test_get_url_success(self):
        """測試取得 URL"""
        manager = FlaskManager()
        manager.port = 5100
        
        url = manager.get_url()
        assert url == "http://127.0.0.1:5100"
    
    def test_get_url_not_started(self):
        """測試服務未啟動時取得 URL"""
        manager = FlaskManager()
        
        with pytest.raises(RuntimeError, match="Flask 服務尚未啟動"):
            manager.get_url()
    
    @patch('flask_manager.subprocess.Popen')
    @patch('flask_manager.requests.get')
    def test_restart_flask_process(self, mock_get, mock_popen):
        """測試重啟 Flask 進程"""
        # Setup
        mock_process = Mock()
        mock_process.pid = 12345
        mock_popen.return_value = mock_process
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        manager = FlaskManager()
        manager.port = 5100
        manager.token = "test-token"
        manager.process = Mock()
        
        with patch.object(manager, '_start_output_readers'):
            result = manager._restart_flask_process()
        
        assert result is True
        assert manager.process == mock_process


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
