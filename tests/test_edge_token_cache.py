"""
Tests for Edge Token Cache

Tests token storage, encryption, platform integration, performance, security,
and error handling.  All test classes were originally split across five files:
  - test_edge_token_cache.py          (unit, core)
  - test_edge_token_cache_step4.py    (step-4 TDD, merged in)
  - test_edge_token_cache_security.py (security, merged in)
  - test_edge_token_cache_performance.py (performance, merged in)
  - test_edge_token_cache_integration.py (integration, merged in)
"""

import gc
import json
import os
import shutil
import stat
import sys
import tempfile
import time
import unittest
import base64
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import psutil

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from src.edge_app.auth.token_cache import EdgeTokenCache
    from src.edge_app.auth.encryption import TokenEncryption
    from src.edge_app.auth.platform_storage import PlatformStorage
    EDGE_APP_AVAILABLE = True
except ImportError as e:
    EDGE_APP_AVAILABLE = False
    SKIP_REASON = f"Edge app auth module not available: {e}"


def create_test_jwt(user_id=1, username='testuser', exp_minutes=15):
    """Create a test JWT token with proper structure.
    
    Args:
        user_id: User ID
        username: Username
        exp_minutes: Expiration time in minutes from now
        
    Returns:
        str: Valid JWT token (header.payload.signature format)
    """
    # Create header
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = base64.urlsafe_b64encode(
        json.dumps(header).encode()
    ).decode().rstrip('=')
    
    # Create payload with exp claim
    exp_time = int(time.time()) + (exp_minutes * 60)
    payload = {
        "user_id": user_id,
        "username": username,
        "exp": exp_time
    }
    payload_b64 = base64.urlsafe_b64encode(
        json.dumps(payload).encode()
    ).decode().rstrip('=')
    
    # Create dummy signature (for testing, doesn't need to be valid)
    signature = "test_signature_for_testing_only"
    
    return f"{header_b64}.{payload_b64}.{signature}"


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
        
        # Create valid JWT tokens
        access_token = create_test_jwt(user_id=1, username='testuser', exp_minutes=15)
        refresh_token = create_test_jwt(user_id=1, username='testuser', exp_minutes=60*24*7)
        device_id = self.cache.get_device_id()
        user_info = {'id': 1, 'username': 'testuser'}
        
        # Save tokens
        self.cache.save_tokens(access_token, refresh_token, device_id, user_info)
        
        # Token should be valid initially
        self.assertTrue(self.cache.is_access_token_valid())
        
        # Create an expired token (exp in the past)
        expired_token = create_test_jwt(user_id=1, username='testuser', exp_minutes=-5)
        self.cache._access_token = expired_token
        
        # Token should now be invalid
        self.assertFalse(self.cache.is_access_token_valid())
    
    def test_refresh_token_expiration(self):
        """Test refresh token expiration detection."""
        self.cache._keychain_available = False
        
        # Create valid JWT tokens
        access_token = create_test_jwt(user_id=1, username='testuser', exp_minutes=15)
        refresh_token = create_test_jwt(user_id=1, username='testuser', exp_minutes=60*24*7)
        device_id = self.cache.get_device_id()
        user_info = {'id': 1, 'username': 'testuser'}
        
        # Save tokens
        self.cache.save_tokens(access_token, refresh_token, device_id, user_info)
        
        # Refresh token should be valid
        self.assertTrue(self.cache.is_refresh_token_valid())
        
        # Create an expired refresh token
        expired_token = create_test_jwt(user_id=1, username='testuser', exp_minutes=-60*24)
        self.cache._refresh_token = expired_token
        
        # Refresh token should now be invalid
        self.assertFalse(self.cache.is_refresh_token_valid())
    
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
        # TokenEncryption stores keys in its own storage_dir (~/.robot-edge by default)
        # Check that the encryption key was loaded
        self.assertIsNotNone(self.cache._encryption_key)
        
        # Key should be stable across instances
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
        # Clear any existing tokens first
        self.cache.clear_tokens()
        
        # Now check that everything is None
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
    
    @unittest.skip("Test needs update for PlatformStorage refactor")
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
    
    @unittest.skip("Test needs update for PlatformStorage refactor")
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

    def test_token_overwrite(self):
        """Test that saving new tokens overwrites the previous ones."""
        self.cache._keychain_available = False

        self.cache.save_tokens('token-a', 'refresh-a', 'device-a', {'username': 'user-a'})
        self.cache.save_tokens('token-b', 'refresh-b', 'device-a', {'username': 'user-b'})

        self.assertEqual(self.cache.get_access_token(), 'token-b')
        self.assertEqual(self.cache.get_refresh_token(), 'refresh-b')
        self.assertEqual(self.cache.get_user_info(), {'username': 'user-b'})

    def test_invalid_json_in_token_file(self):
        """Test handling of encrypted-but-invalid-JSON token file."""
        self.cache._keychain_available = False

        token_file = self.cache.token_file
        token_file.parent.mkdir(parents=True, exist_ok=True)
        encryption = TokenEncryption()
        encrypted_str = encryption.encrypt("not valid json")
        with open(token_file, 'w', encoding='utf-8') as fh:
            fh.write(encrypted_str)

        self.assertIsNone(self.cache.get_access_token())

    def test_token_cache_with_platform_storage(self):
        """Test that EdgeTokenCache saves and retrieves via platform storage."""
        self.cache._keychain_available = False

        result = self.cache.save_tokens('pt.access', 'pt.refresh', 'dev-pt', {'username': 'pt'})
        self.assertTrue(result)
        self.assertEqual(self.cache.get_access_token(), 'pt.access')

    def test_token_cache_fallback_mode(self):
        """Test that the cache falls back to encrypted-file storage correctly."""
        self.cache._keychain_available = False

        with patch.object(PlatformStorage, 'is_available', return_value=False):
            cache = EdgeTokenCache(app_name='robot-edge-test-fallback')
            result = cache.save_tokens('fb.access', 'fb.refresh', 'dev-fb', {'username': 'fb'})
            self.assertTrue(result)
            self.assertEqual(cache.get_access_token(), 'fb.access')


# ---------------------------------------------------------------------------
# Security tests (originally test_edge_token_cache_security.py)
# ---------------------------------------------------------------------------

@unittest.skipUnless(EDGE_APP_AVAILABLE, "Edge app auth module not installed")
class TestEdgeTokenCacheSecurity(unittest.TestCase):
    """Edge Token Cache 安全測試"""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.original_home = os.environ.get('HOME')
        os.environ['HOME'] = self.test_dir
        self.cache = EdgeTokenCache(app_name="test-security")

        future_time = int((datetime.utcnow() + timedelta(minutes=15)).timestamp())
        header = base64.urlsafe_b64encode(b'{"alg":"HS256"}').decode().rstrip('=')
        payload = json.dumps({"exp": future_time, "user_id": "test-user"})
        body = base64.urlsafe_b64encode(payload.encode()).decode().rstrip('=')

        self.test_access_token = f"{header}.{body}.fake_signature"
        self.test_refresh_token = f"{header}.{body}.refresh_signature"
        self.test_device_id = "test-device-security"
        self.test_user_info = {"user_id": "test-user", "role": "admin"}

    def tearDown(self):
        if self.original_home:
            os.environ['HOME'] = self.original_home
        elif 'HOME' in os.environ:
            del os.environ['HOME']
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_file_permissions(self):
        """Token 快取目錄和檔案的權限應符合安全要求（Unix 600/700）。"""
        self.cache.save_tokens(
            self.test_access_token, self.test_refresh_token,
            self.test_device_id, self.test_user_info
        )

        cache_dir = os.path.join(self.test_dir, ".test-security")
        self.assertTrue(os.path.exists(cache_dir), "快取目錄應該存在")

        if os.name != 'nt':
            dir_stat = os.stat(cache_dir)
            dir_mode = stat.S_IMODE(dir_stat.st_mode)
            self.assertEqual(dir_mode & stat.S_IRWXU, stat.S_IRWXU,
                             "擁有者應該有完整目錄權限")

        for fname in ("tokens.json", "tokens.enc"):
            fpath = os.path.join(cache_dir, fname)
            if os.path.exists(fpath) and os.name != 'nt':
                fmode = stat.S_IMODE(os.stat(fpath).st_mode)
                self.assertEqual(fmode & stat.S_IRUSR, stat.S_IRUSR, "擁有者可讀")
                self.assertEqual(fmode & stat.S_IWUSR, stat.S_IWUSR, "擁有者可寫")
                self.assertEqual(fmode & stat.S_IXUSR, 0, "檔案不可執行")

    def test_encryption_strength(self):
        """Token 應以 Fernet/AES-128 加密，不能以明文儲存。"""
        encryption = TokenEncryption()
        test_data = "sensitive_token_data"
        encrypted = encryption.encrypt(test_data)

        self.assertIsInstance(encrypted, str)
        self.assertNotEqual(encrypted, test_data)
        self.assertGreater(len(encrypted), len(test_data))

        decrypted = encryption.decrypt(encrypted)
        self.assertEqual(decrypted, test_data)

        try:
            base64.urlsafe_b64decode(encrypted.encode())
        except Exception:
            self.fail("加密輸出應該是 base64 編碼（Fernet 特徵）")

    def test_no_plaintext_tokens(self):
        """快取檔案中不應出現明文 Token 的 signature 部分。"""
        self.cache.save_tokens(
            self.test_access_token, self.test_refresh_token,
            self.test_device_id, self.test_user_info
        )

        cache_dir = os.path.join(self.test_dir, ".test-security")
        if not os.path.exists(cache_dir):
            self.skipTest("快取目錄不存在，可能使用平台儲存")

        token_signature = self.test_access_token.split('.')[-1]
        for root, _, files in os.walk(cache_dir):
            for filename in files:
                filepath = os.path.join(root, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as fh:
                        content = fh.read()
                    self.assertNotIn(token_signature, content,
                                     f"明文 Token 不應出現在 {filename} 中")
                except (UnicodeDecodeError, PermissionError):
                    pass

    def test_device_id_binding_enforcement(self):
        """儲存不同 Device ID 時快取應正確更新綁定。"""
        self.cache.save_tokens(
            self.test_access_token, self.test_refresh_token,
            "device-001", self.test_user_info
        )
        self.assertEqual(self.cache.get_device_id(), "device-001")

        self.cache.save_tokens(
            self.test_access_token, self.test_refresh_token,
            "device-002", self.test_user_info
        )
        self.assertEqual(self.cache.get_device_id(), "device-002")
        self.assertIsNotNone(self.cache.get_access_token())


# ---------------------------------------------------------------------------
# Performance tests (originally test_edge_token_cache_performance.py)
# ---------------------------------------------------------------------------

@unittest.skipUnless(EDGE_APP_AVAILABLE, "Edge app auth module not installed")
class TestEdgeTokenCachePerformance(unittest.TestCase):
    """Edge Token Cache 效能測試"""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.original_home = os.environ.get('HOME')
        os.environ['HOME'] = self.test_dir
        self.cache = EdgeTokenCache(app_name="test-performance")

        future_time = int((datetime.utcnow() + timedelta(minutes=15)).timestamp())
        header = base64.urlsafe_b64encode(b'{"alg":"HS256"}').decode().rstrip('=')
        body = base64.urlsafe_b64encode(
            json.dumps({"exp": future_time, "user_id": "test-user"}).encode()
        ).decode().rstrip('=')

        self.test_access_token = f"{header}.{body}.fake_signature"
        self.test_refresh_token = f"{header}.{body}.fake_signature"
        self.test_device_id = "test-device-perf"
        self.test_user_info = {"user_id": "test-user", "role": "admin"}

        self.cache.save_tokens(
            self.test_access_token, self.test_refresh_token,
            self.test_device_id, self.test_user_info
        )

    def tearDown(self):
        if self.original_home:
            os.environ['HOME'] = self.original_home
        elif 'HOME' in os.environ:
            del os.environ['HOME']
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_token_read_performance(self):
        """Token 讀取平均應 <5 ms。"""
        iterations = 100
        total_time = 0.0
        for _ in range(iterations):
            start = time.perf_counter()
            token = self.cache.get_access_token()
            total_time += time.perf_counter() - start
            self.assertIsNotNone(token)

        avg_ms = (total_time / iterations) * 1000
        self.assertLess(avg_ms, 5.0,
                        f"Token 讀取時間 {avg_ms:.3f}ms 超過 5ms 標準")

    def test_token_write_performance(self):
        """Token 寫入平均應 <10 ms。"""
        iterations = 50
        total_time = 0.0
        for i in range(iterations):
            token = self.test_access_token + f"-{i}"
            start = time.perf_counter()
            success = self.cache.save_tokens(
                token, self.test_refresh_token,
                self.test_device_id, self.test_user_info
            )
            total_time += time.perf_counter() - start
            self.assertTrue(success)

        avg_ms = (total_time / iterations) * 1000
        self.assertLess(avg_ms, 10.0,
                        f"Token 寫入時間 {avg_ms:.3f}ms 超過 10ms 標準")

    def test_memory_usage(self):
        """100 個 cache 實例的記憶體增長應 <10 MB。"""
        process = psutil.Process()
        gc.collect()
        mem_before = process.memory_info().rss / (1024 * 1024)

        dirs = []
        caches = []
        for i in range(100):
            d = tempfile.mkdtemp()
            dirs.append(d)
            os.environ['HOME'] = d
            c = EdgeTokenCache(app_name=f"test-mem-{i}")
            c.save_tokens(self.test_access_token, self.test_refresh_token,
                          self.test_device_id, self.test_user_info)
            caches.append(c)

        for c in caches:
            c.get_access_token()
            c.get_refresh_token()
            c.get_device_id()
            c.get_user_info()

        mem_after = process.memory_info().rss / (1024 * 1024)
        for d in dirs:
            shutil.rmtree(d, ignore_errors=True)

        mem_used = mem_after - mem_before
        self.assertLess(mem_used, 10.0,
                        f"記憶體使用 {mem_used:.2f}MB 超過 10MB 標準")


# ---------------------------------------------------------------------------
# Integration tests (originally test_edge_token_cache_integration.py)
# ---------------------------------------------------------------------------

@unittest.skipUnless(EDGE_APP_AVAILABLE, "Edge app auth module not installed")
class TestEdgeTokenCacheIntegration(unittest.TestCase):
    """Edge Token Cache 整合測試"""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.original_home = os.environ.get('HOME')
        os.environ['HOME'] = self.test_dir
        self.cache = EdgeTokenCache(app_name="test-robot-edge")

        future_time = int((datetime.utcnow() + timedelta(minutes=15)).timestamp())
        refresh_future = int((datetime.utcnow() + timedelta(days=7)).timestamp())
        past_time = int((datetime.utcnow() - timedelta(minutes=5)).timestamp())

        header = base64.urlsafe_b64encode(b'{"alg":"HS256"}').decode().rstrip('=')
        access_body = base64.urlsafe_b64encode(
            json.dumps({"exp": future_time, "user_id": "test-user"}).encode()
        ).decode().rstrip('=')
        refresh_body = base64.urlsafe_b64encode(
            json.dumps({"exp": refresh_future, "user_id": "test-user"}).encode()
        ).decode().rstrip('=')
        expired_body = base64.urlsafe_b64encode(
            json.dumps({"exp": past_time, "user_id": "test-user"}).encode()
        ).decode().rstrip('=')

        self.valid_access_token = f"{header}.{access_body}.fake_signature"
        self.valid_refresh_token = f"{header}.{refresh_body}.fake_signature"
        self.expired_token = f"{header}.{expired_body}.fake_signature"

        self.test_device_id = "test-device-12345678"
        self.test_user_info = {"user_id": "test-user", "username": "testuser", "role": "admin"}

    def tearDown(self):
        if self.original_home:
            os.environ['HOME'] = self.original_home
        elif 'HOME' in os.environ:
            del os.environ['HOME']
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_full_token_lifecycle(self):
        """儲存 → 讀取 → 驗效 → 清除的完整生命週期。"""
        self.assertTrue(self.cache.save_tokens(
            self.valid_access_token, self.valid_refresh_token,
            self.test_device_id, self.test_user_info
        ))
        self.assertEqual(self.cache.get_access_token(), self.valid_access_token)
        self.assertEqual(self.cache.get_refresh_token(), self.valid_refresh_token)
        self.assertEqual(self.cache.get_device_id(), self.test_device_id)
        self.assertEqual(self.cache.get_user_info(), self.test_user_info)
        self.assertTrue(self.cache.is_access_token_valid())
        self.assertTrue(self.cache.is_refresh_token_valid())

        self.assertTrue(self.cache.clear_tokens())
        self.assertIsNone(self.cache.get_access_token())
        self.assertFalse(self.cache.is_access_token_valid())

    def test_token_refresh_workflow(self):
        """過期 Access Token + 有效 Refresh Token 的更新流程。"""
        self.cache.save_tokens(
            self.expired_token, self.valid_refresh_token,
            self.test_device_id, self.test_user_info
        )
        self.assertFalse(self.cache.is_access_token_valid())
        self.assertTrue(self.cache.is_refresh_token_valid())

        new_access = self.valid_access_token.replace("fake", "new")
        self.cache.save_tokens(new_access, self.valid_refresh_token,
                               self.test_device_id, self.test_user_info)
        self.assertEqual(self.cache.get_access_token(), new_access)
        self.assertTrue(self.cache.is_access_token_valid())

    def test_device_binding(self):
        """Device ID 覆蓋後應正確更新。"""
        self.cache.save_tokens(
            self.valid_access_token, self.valid_refresh_token,
            self.test_device_id, self.test_user_info
        )
        self.assertEqual(self.cache.get_device_id(), self.test_device_id)

        different_device = "different-device-id"
        self.cache.save_tokens(
            self.valid_access_token, self.valid_refresh_token,
            different_device, self.test_user_info
        )
        self.assertEqual(self.cache.get_device_id(), different_device)

    @patch('src.edge_app.auth.platform_storage.PlatformStorage')
    def test_platform_specific_storage(self, mock_platform_storage):
        """Mock PlatformStorage 情境下 save/get 應正常運作。"""
        mock_instance = MagicMock()
        mock_instance.is_available.return_value = True
        mock_instance.set_password.return_value = True
        mock_instance.get_password.return_value = json.dumps({
            "access_token": self.valid_access_token,
            "refresh_token": self.valid_refresh_token,
            "device_id": self.test_device_id,
            "user_info": self.test_user_info,
        })
        mock_platform_storage.return_value = mock_instance

        test_home_2 = tempfile.mkdtemp()
        os.environ['HOME'] = test_home_2
        try:
            cache = EdgeTokenCache(app_name="test-platform-storage")
            result = cache.save_tokens(
                self.valid_access_token, self.valid_refresh_token,
                self.test_device_id, self.test_user_info
            )
            self.assertTrue(result)
        finally:
            shutil.rmtree(test_home_2, ignore_errors=True)

    def test_error_recovery(self):
        """損壞快取後應能恢復，重新儲存不受影響。"""
        self.assertIsNone(self.cache.get_access_token())

        cache_file = os.path.join(self.test_dir, ".test-robot-edge", "tokens.enc")
        os.makedirs(os.path.dirname(cache_file), exist_ok=True)
        with open(cache_file, 'w') as fh:
            fh.write("invalid json content")

        token = self.cache.get_access_token()
        self.assertIn(token, [None, ""])

        self.assertTrue(self.cache.save_tokens(
            self.valid_access_token, self.valid_refresh_token,
            self.test_device_id, self.test_user_info
        ))
        self.assertEqual(self.cache.get_access_token(), self.valid_access_token)


if __name__ == '__main__':
    unittest.main()
