"""
Tests for Edge Token Cache

Tests token storage, encryption, platform integration, and error handling.
"""

import unittest
import os
import sys
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from src.edge_app.auth.token_cache import EdgeTokenCache
    EDGE_APP_AVAILABLE = True
except ImportError as e:
    EDGE_APP_AVAILABLE = False
    SKIP_REASON = f"Edge app auth module not available: {e}"


@unittest.skipUnless(EDGE_APP_AVAILABLE, "Edge app auth module not installed")
class TestEdgeTokenCache(unittest.TestCase):
    """Test suite for Edge Token Cache."""
    
    def setUp(self):
        """Set up test environment."""
        # Create temporary directory for testing
        self.temp_dir = tempfile.mkdtemp()
        self.original_home = Path.home()
        
        # Mock home directory to use temp dir
        self.home_patcher = patch('pathlib.Path.home', return_value=Path(self.temp_dir))
        self.home_patcher.start()
        
        # Create token cache instance
        self.cache = EdgeTokenCache(app_name='robot-edge-test')
    
    def tearDown(self):
        """Clean up test environment."""
        self.home_patcher.stop()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_init(self):
        """Test EdgeTokenCache initialization."""
        self.assertIsNotNone(self.cache)
        self.assertEqual(self.cache.app_name, 'robot-edge-test')
        self.assertTrue(self.cache.cache_dir.exists())
    
    def test_device_id_generation(self):
        """Test device ID generation and persistence."""
        device_id1 = self.cache.get_device_id()
        self.assertIsNotNone(device_id1)
        self.assertEqual(len(device_id1), 64)  # SHA-256 hex
        
        # Device ID should be stable
        device_id2 = self.cache.get_device_id()
        self.assertEqual(device_id1, device_id2)
    
    def test_save_and_load_tokens_fallback(self):
        """Test save and load tokens using fallback file storage."""
        # Mock keychain as unavailable
        self.cache._keychain_available = False
        
        access_token = 'test_access_token_123'
        refresh_token = 'test_refresh_token_456'
        device_id = self.cache.get_device_id()
        user_info = {
            'id': 1,
            'username': 'testuser',
            'role': 'admin'
        }
        
        # Save tokens
        self.cache.save_tokens(access_token, refresh_token, device_id, user_info)
        
        # Verify file created
        self.assertTrue(self.cache.token_file.exists())
        
        # Load tokens
        loaded_access = self.cache.get_access_token()
        loaded_refresh = self.cache.get_refresh_token()
        loaded_user = self.cache.get_user_info()
        
        self.assertEqual(loaded_access, access_token)
        self.assertEqual(loaded_refresh, refresh_token)
        self.assertEqual(loaded_user, user_info)
    
    def test_access_token_expiration(self):
        """Test access token expiration detection."""
        self.cache._keychain_available = False
        
        access_token = 'test_access_token'
        refresh_token = 'test_refresh_token'
        device_id = self.cache.get_device_id()
        user_info = {'id': 1, 'username': 'testuser'}
        
        # Save tokens
        self.cache.save_tokens(access_token, refresh_token, device_id, user_info)
        
        # Token should be valid initially
        self.assertTrue(self.cache.is_access_token_valid())
        
        # Manually expire the token
        token_data = self.cache._load_tokens()
        token_data['access_token_expires_at'] = (datetime.utcnow() - timedelta(minutes=1)).isoformat()
        self.cache._save_to_file(token_data)
        
        # Token should now be invalid
        self.assertFalse(self.cache.is_access_token_valid())
        self.assertIsNone(self.cache.get_access_token())
    
    def test_refresh_token_expiration(self):
        """Test refresh token expiration detection."""
        self.cache._keychain_available = False
        
        access_token = 'test_access_token'
        refresh_token = 'test_refresh_token'
        device_id = self.cache.get_device_id()
        user_info = {'id': 1, 'username': 'testuser'}
        
        # Save tokens
        self.cache.save_tokens(access_token, refresh_token, device_id, user_info)
        
        # Refresh token should be valid
        self.assertIsNotNone(self.cache.get_refresh_token())
        
        # Manually expire the refresh token
        token_data = self.cache._load_tokens()
        token_data['refresh_token_expires_at'] = (datetime.utcnow() - timedelta(days=1)).isoformat()
        self.cache._save_to_file(token_data)
        
        # Refresh token should now be invalid
        self.assertIsNone(self.cache.get_refresh_token())
    
    def test_clear_tokens(self):
        """Test clearing cached tokens."""
        self.cache._keychain_available = False
        
        access_token = 'test_access_token'
        refresh_token = 'test_refresh_token'
        device_id = self.cache.get_device_id()
        user_info = {'id': 1, 'username': 'testuser'}
        
        # Save tokens
        self.cache.save_tokens(access_token, refresh_token, device_id, user_info)
        self.assertTrue(self.cache.token_file.exists())
        
        # Clear tokens
        self.cache.clear_tokens()
        
        # Verify cleared
        self.assertFalse(self.cache.token_file.exists())
        self.assertIsNone(self.cache.get_access_token())
        self.assertIsNone(self.cache.get_refresh_token())
    
    def test_encryption_key_generation(self):
        """Test encryption key generation and persistence."""
        key_file = self.cache.cache_dir / 'key.bin'
        self.assertTrue(key_file.exists())
        
        # Key should be stable
        key1 = self.cache._encryption_key
        cache2 = EdgeTokenCache(app_name='robot-edge-test')
        key2 = cache2._encryption_key
        self.assertEqual(key1, key2)
    
    def test_corrupted_token_file(self):
        """Test handling of corrupted token file."""
        self.cache._keychain_available = False
        
        # Write corrupted data
        with open(self.cache.token_file, 'wb') as f:
            f.write(b'corrupted data')
        
        # Should return None gracefully
        self.assertIsNone(self.cache.get_access_token())
        self.assertIsNone(self.cache.get_refresh_token())
    
    def test_no_tokens_saved(self):
        """Test behavior when no tokens are saved."""
        self.assertIsNone(self.cache.get_access_token())
        self.assertIsNone(self.cache.get_refresh_token())
        self.assertIsNone(self.cache.get_user_info())
        self.assertFalse(self.cache.is_access_token_valid())
    
    @patch('platform.system', return_value='Linux')
    def test_linux_platform_detection(self, mock_system):
        """Test Linux platform detection."""
        cache = EdgeTokenCache(app_name='robot-edge-test')
        self.assertEqual(cache.platform, 'Linux')
    
    @patch('platform.system', return_value='Windows')
    def test_windows_platform_detection(self, mock_system):
        """Test Windows platform detection."""
        cache = EdgeTokenCache(app_name='robot-edge-test')
        self.assertEqual(cache.platform, 'Windows')
    
    def test_file_permissions_linux(self):
        """Test file permissions on Linux."""
        if self.cache.platform != 'Linux':
            self.skipTest("Linux-specific test")
        
        self.cache._keychain_available = False
        
        access_token = 'test_access_token'
        refresh_token = 'test_refresh_token'
        device_id = self.cache.get_device_id()
        user_info = {'id': 1, 'username': 'testuser'}
        
        # Save tokens
        self.cache.save_tokens(access_token, refresh_token, device_id, user_info)
        
        # Check file permissions (should be 600)
        stat_info = os.stat(self.cache.token_file)
        permissions = oct(stat_info.st_mode)[-3:]
        self.assertEqual(permissions, '600')
    
    @patch('src.edge_app.auth.token_cache.EdgeTokenCache._init_keychain', return_value=True)
    @patch('platform.system', return_value='Linux')
    def test_linux_keychain_save(self, mock_system, mock_init):
        """Test saving tokens to Linux keychain."""
        # Mock secretstorage
        mock_connection = MagicMock()
        mock_collection = MagicMock()
        mock_secret_storage = MagicMock()
        mock_secret_storage.dbus_init.return_value = mock_connection
        mock_secret_storage.get_default_collection.return_value = mock_collection
        
        cache = EdgeTokenCache(app_name='robot-edge-test')
        cache._secret_storage = mock_secret_storage
        cache._keychain_available = True
        cache.platform = 'Linux'
        
        access_token = 'test_access_token'
        refresh_token = 'test_refresh_token'
        device_id = cache.get_device_id()
        user_info = {'id': 1, 'username': 'testuser'}
        
        # Save tokens
        cache.save_tokens(access_token, refresh_token, device_id, user_info)
        
        # Verify keychain was called
        self.assertEqual(mock_collection.create_item.call_count, 3)
    
    @patch('src.edge_app.auth.token_cache.EdgeTokenCache._init_keychain', return_value=True)
    @patch('platform.system', return_value='Windows')
    def test_windows_keychain_save(self, mock_system, mock_init):
        """Test saving tokens to Windows keychain."""
        # Mock keyring
        mock_keyring = MagicMock()
        
        cache = EdgeTokenCache(app_name='robot-edge-test')
        cache._keyring = mock_keyring
        cache._keychain_available = True
        cache.platform = 'Windows'
        
        access_token = 'test_access_token'
        refresh_token = 'test_refresh_token'
        device_id = cache.get_device_id()
        user_info = {'id': 1, 'username': 'testuser'}
        
        # Save tokens
        cache.save_tokens(access_token, refresh_token, device_id, user_info)
        
        # Verify keyring was called
        self.assertEqual(mock_keyring.set_password.call_count, 3)
    
    def test_user_info_cached(self):
        """Test that user info is properly cached."""
        self.cache._keychain_available = False
        
        access_token = 'test_access_token'
        refresh_token = 'test_refresh_token'
        device_id = self.cache.get_device_id()
        user_info = {
            'id': 1,
            'username': 'testuser',
            'role': 'admin',
            'email': 'test@example.com'
        }
        
        # Save tokens
        self.cache.save_tokens(access_token, refresh_token, device_id, user_info)
        
        # Load user info
        loaded_user = self.cache.get_user_info()
        self.assertEqual(loaded_user, user_info)
        self.assertEqual(loaded_user['id'], 1)
        self.assertEqual(loaded_user['username'], 'testuser')
        self.assertEqual(loaded_user['role'], 'admin')
    
    def test_device_id_stability(self):
        """Test that device ID remains stable across instances."""
        device_id1 = self.cache.get_device_id()
        
        # Create new cache instance
        cache2 = EdgeTokenCache(app_name='robot-edge-test')
        device_id2 = cache2.get_device_id()
        
        self.assertEqual(device_id1, device_id2)
    
    def test_multiple_apps_isolation(self):
        """Test that different app names have isolated storage."""
        self.cache._keychain_available = False
        
        # Save tokens for app1
        cache1 = EdgeTokenCache(app_name='robot-edge-test-1')
        cache1._keychain_available = False
        cache1.save_tokens('token1', 'refresh1', cache1.get_device_id(), {'id': 1})
        
        # Save tokens for app2
        cache2 = EdgeTokenCache(app_name='robot-edge-test-2')
        cache2._keychain_available = False
        cache2.save_tokens('token2', 'refresh2', cache2.get_device_id(), {'id': 2})
        
        # Verify isolation
        self.assertEqual(cache1.get_access_token(), 'token1')
        self.assertEqual(cache2.get_access_token(), 'token2')


if __name__ == '__main__':
    unittest.main()
