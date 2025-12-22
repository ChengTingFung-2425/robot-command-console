"""
Platform Storage 測試套件

測試 PlatformStorage 類別的平台專用 Token 儲存功能：
- Linux Secret Service API
- Windows Credential Manager
- Fallback 加密檔案儲存
"""

import os
import sys
import unittest
import platform
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, project_root)

from src.edge_app.auth.platform_storage import PlatformStorage


class TestPlatformStorage(unittest.TestCase):
    """Platform Storage 測試"""

    def setUp(self):
        """測試前置作業"""
        self.test_dir = tempfile.mkdtemp()
        self.app_name = "robot-edge-test"
        self.storage = None

    def tearDown(self):
        """測試清理"""
        if self.storage:
            try:
                self.storage.delete_secret("test_key")
            except Exception:
                pass  # Ignore cleanup errors
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_linux_platform_detection(self):
        """測試 Linux 平台偵測"""
        with patch('platform.system', return_value='Linux'):
            storage = PlatformStorage(self.app_name)
            self.assertEqual(storage.platform, 'Linux')

    def test_windows_platform_detection(self):
        """測試 Windows 平台偵測"""
        with patch('platform.system', return_value='Windows'):
            storage = PlatformStorage(self.app_name)
            self.assertEqual(storage.platform, 'Windows')

    @patch('platform.system', return_value='Linux')
    def test_linux_secret_service_available(self, mock_platform):
        """測試 Linux Secret Service 可用性"""
        # Mock secretstorage module
        mock_secretstorage = MagicMock()
        mock_connection = MagicMock()
        mock_collection = MagicMock()
        mock_secretstorage.dbus_init.return_value = mock_connection
        mock_secretstorage.get_default_collection.return_value = mock_collection
        
        with patch.dict('sys.modules', {'secretstorage': mock_secretstorage}):
            storage = PlatformStorage(self.app_name)
            self.assertTrue(storage.is_available())

    @patch('platform.system', return_value='Linux')
    def test_linux_secret_service_save(self, mock_platform):
        """測試 Linux Secret Service 儲存功能"""
        # Mock secretstorage module
        mock_secretstorage = MagicMock()
        mock_connection = MagicMock()
        mock_collection = MagicMock()
        mock_secretstorage.dbus_init.return_value = mock_connection
        mock_secretstorage.get_default_collection.return_value = mock_collection
        
        with patch.dict('sys.modules', {'secretstorage': mock_secretstorage}):
            storage = PlatformStorage(self.app_name)
            result = storage.save_secret("test_key", "test_value")
            self.assertTrue(result)

    @patch('platform.system', return_value='Linux')
    def test_linux_secret_service_get(self, mock_platform):
        """測試 Linux Secret Service 讀取功能"""
        # Mock secretstorage module
        mock_secretstorage = MagicMock()
        mock_connection = MagicMock()
        mock_collection = MagicMock()
        mock_item = MagicMock()
        
        mock_item.get_secret.return_value = b"test_value"
        mock_collection.search_items.return_value = [mock_item]
        mock_secretstorage.dbus_init.return_value = mock_connection
        mock_secretstorage.get_default_collection.return_value = mock_collection
        
        with patch.dict('sys.modules', {'secretstorage': mock_secretstorage}):
            storage = PlatformStorage(self.app_name)
            value = storage.get_secret("test_key")
            self.assertEqual(value, "test_value")

    @patch('platform.system', return_value='Windows')
    def test_windows_credential_manager_save(self, mock_platform):
        """測試 Windows Credential Manager 儲存功能"""
        # Mock keyring module
        mock_keyring = MagicMock()
        
        with patch.dict('sys.modules', {'keyring': mock_keyring}):
            storage = PlatformStorage(self.app_name)
            result = storage.save_secret("test_key", "test_value")
            
            self.assertTrue(result)
            mock_keyring.set_password.assert_called_once_with(self.app_name, "test_key", "test_value")

    @patch('platform.system', return_value='Windows')
    def test_windows_credential_manager_get(self, mock_platform):
        """測試 Windows Credential Manager 讀取功能"""
        # Mock keyring module
        mock_keyring = MagicMock()
        mock_keyring.get_password.return_value = "test_value"
        
        with patch.dict('sys.modules', {'keyring': mock_keyring}):
            storage = PlatformStorage(self.app_name)
            value = storage.get_secret("test_key")
            
            self.assertEqual(value, "test_value")
            mock_keyring.get_password.assert_called_once_with(self.app_name, "test_key")

    def test_fallback_to_file_storage(self):
        """測試 Fallback 至檔案儲存模式"""
        # Force fallback by patching module to fail import
        with patch('platform.system', return_value='Linux'):
            # Mock secretstorage to raise exception
            mock_secretstorage = MagicMock()
            mock_secretstorage.dbus_init.side_effect = Exception("D-Bus not available")
            
            with patch.dict('sys.modules', {'secretstorage': mock_secretstorage}):
                storage = PlatformStorage(self.app_name, storage_dir=self.test_dir)
                
                # Should fallback to file storage
                result = storage.save_secret("test_key", "test_value")
                self.assertTrue(result)
                
                # Should be able to read back
                value = storage.get_secret("test_key")
                self.assertEqual(value, "test_value")

    def test_file_storage_encryption(self):
        """測試檔案儲存加密"""
        with patch('platform.system', return_value='Linux'):
            # Mock secretstorage to fail
            mock_secretstorage = MagicMock()
            mock_secretstorage.dbus_init.side_effect = Exception("Force fallback")
            
            with patch.dict('sys.modules', {'secretstorage': mock_secretstorage}):
                storage = PlatformStorage(self.app_name, storage_dir=self.test_dir)
                storage.save_secret("test_key", "sensitive_data")
                
                # Read file directly - should be encrypted (not plain text)
                secrets_file = Path(self.test_dir) / f"secrets_{self.app_name}.enc"
                self.assertTrue(secrets_file.exists())
                
                with open(secrets_file, 'rb') as f:
                    raw_content = f.read()
                    # Should not contain plain text
                    self.assertNotIn(b"sensitive_data", raw_content)

    def test_storage_isolation(self):
        """測試多應用程式隔離"""
        with patch('platform.system', return_value='Linux'):
            # Mock secretstorage to fail
            mock_secretstorage = MagicMock()
            mock_secretstorage.dbus_init.side_effect = Exception("Force fallback")
            
            with patch.dict('sys.modules', {'secretstorage': mock_secretstorage}):
                storage1 = PlatformStorage("app1", storage_dir=self.test_dir)
                storage2 = PlatformStorage("app2", storage_dir=self.test_dir)
                
                # Save to different apps
                storage1.save_secret("key", "value1")
                storage2.save_secret("key", "value2")
                
                # Should be isolated
                self.assertEqual(storage1.get_secret("key"), "value1")
                self.assertEqual(storage2.get_secret("key"), "value2")


if __name__ == '__main__':
    unittest.main()
