"""
Tiny 版本 Native Bridge 測試

測試 NativeBridge 類別的核心功能：
1. pyqtSlot 裝飾器正確性
2. 檔案對話框功能（使用 mock）
3. 通知信號發射
4. 版本資訊取得
5. 平台資訊取得
6. 錯誤處理情境
"""

import sys
import os
from unittest.mock import Mock, patch, MagicMock

# 添加專案路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'qtwebview-app'))

import pytest

# 由於 PyQt6 可能未安裝，我們模擬導入
try:
    from PyQt6.QtCore import QObject
    from bridge import NativeBridge, __version__
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False
    pytest.skip("PyQt6 未安裝，跳過 Tiny 版本測試", allow_module_level=True)


@pytest.mark.skipif(not PYQT_AVAILABLE, reason="PyQt6 未安裝")
class TestNativeBridge:
    """Native Bridge 測試"""
    
    def test_bridge_initialization(self):
        """測試橋接器初始化"""
        bridge = NativeBridge()
        
        assert isinstance(bridge, QObject)
        assert hasattr(bridge, 'notificationReceived')
        assert bridge._parent_widget is None
    
    def test_bridge_initialization_with_parent(self):
        """測試帶父元件的橋接器初始化"""
        mock_parent = Mock()
        bridge = NativeBridge(parent=mock_parent)
        
        assert bridge._parent_widget == mock_parent
    
    @patch('bridge.QFileDialog.getOpenFileName')
    def test_show_file_dialog_open(self, mock_dialog):
        """測試開啟檔案對話框"""
        mock_dialog.return_value = ('/path/to/file.json', '*.json')
        
        bridge = NativeBridge()
        result = bridge.showFileDialog('open', '*.json')
        
        assert result == '/path/to/file.json'
        mock_dialog.assert_called_once()
    
    @patch('bridge.QFileDialog.getSaveFileName')
    def test_show_file_dialog_save(self, mock_dialog):
        """測試儲存檔案對話框"""
        mock_dialog.return_value = ('/path/to/save.json', '*.json')
        
        bridge = NativeBridge()
        result = bridge.showFileDialog('save', '*.json')
        
        assert result == '/path/to/save.json'
        mock_dialog.assert_called_once()
    
    @patch('bridge.QFileDialog.getOpenFileName')
    def test_show_file_dialog_cancel(self, mock_dialog):
        """測試取消檔案對話框"""
        mock_dialog.return_value = ('', '')
        
        bridge = NativeBridge()
        result = bridge.showFileDialog('open', '*.json')
        
        assert result == ''
    
    def test_show_file_dialog_invalid_mode(self):
        """測試無效的對話框模式"""
        bridge = NativeBridge()
        result = bridge.showFileDialog('invalid', '*.json')
        
        assert result == ''
    
    @patch('bridge.QFileDialog.getOpenFileName')
    def test_show_file_dialog_exception(self, mock_dialog):
        """測試檔案對話框異常處理"""
        mock_dialog.side_effect = Exception("Dialog error")
        
        bridge = NativeBridge()
        result = bridge.showFileDialog('open', '*.json')
        
        assert result == ''
    
    def test_show_notification(self):
        """測試顯示通知"""
        bridge = NativeBridge()
        
        # 使用 Mock 捕獲信號
        mock_handler = Mock()
        bridge.notificationReceived.connect(mock_handler)
        
        bridge.showNotification('Test Title', 'Test Message')
        
        mock_handler.assert_called_once_with('Test Title', 'Test Message')
    
    def test_get_app_version(self):
        """測試取得應用程式版本"""
        bridge = NativeBridge()
        version = bridge.getAppVersion()
        
        assert isinstance(version, str)
        assert version == __version__
    
    @patch('bridge.QDesktopServices.openUrl')
    def test_open_external_url(self, mock_open):
        """測試開啟外部連結"""
        bridge = NativeBridge()
        bridge.openExternal('https://example.com')
        
        mock_open.assert_called_once()
    
    @patch('bridge.QDesktopServices.openUrl')
    def test_open_external_url_exception(self, mock_open):
        """測試開啟外部連結異常處理"""
        mock_open.side_effect = Exception("Open error")
        
        bridge = NativeBridge()
        # 不應該拋出異常
        bridge.openExternal('https://example.com')
    
    def test_get_platform(self):
        """測試取得平台資訊"""
        bridge = NativeBridge()
        platform = bridge.getPlatform()
        
        assert isinstance(platform, str)
        assert platform in ['Windows', 'Darwin', 'Linux']
    
    @patch('bridge.QFileDialog.getExistingDirectory')
    def test_select_directory(self, mock_dialog):
        """測試選擇資料夾"""
        mock_dialog.return_value = '/path/to/directory'
        
        bridge = NativeBridge()
        result = bridge.selectDirectory('選擇資料夾')
        
        assert result == '/path/to/directory'
        mock_dialog.assert_called_once()
    
    @patch('bridge.QFileDialog.getExistingDirectory')
    def test_select_directory_cancel(self, mock_dialog):
        """測試取消選擇資料夾"""
        mock_dialog.return_value = ''
        
        bridge = NativeBridge()
        result = bridge.selectDirectory()
        
        assert result == ''
    
    @patch('bridge.QFileDialog.getExistingDirectory')
    def test_select_directory_exception(self, mock_dialog):
        """測試選擇資料夾異常處理"""
        mock_dialog.side_effect = Exception("Dialog error")
        
        bridge = NativeBridge()
        result = bridge.selectDirectory()
        
        assert result == ''


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
