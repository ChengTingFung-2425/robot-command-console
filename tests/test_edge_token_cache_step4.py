"""
Phase 2.1 Step 4: Edge Token Cache 測試

整合 Device ID、Encryption 與 Platform Storage，實作完整的 Token 管理。
"""

import unittest
import os
import sys
import tempfile
import shutil
import time
import json
import base64
from unittest.mock import patch

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.edge_app.auth.encryption import TokenEncryption
from src.edge_app.auth.platform_storage import PlatformStorage


class TestEdgeTokenCache(unittest.TestCase):
    """Edge Token Cache 測試"""

    def setUp(self):
        """測試前置作業"""
        self.test_dir = tempfile.mkdtemp()
        self.cache_dir = os.path.join(self.test_dir, '.robot-edge')
        os.makedirs(self.cache_dir, exist_ok=True)

        # Mock cache path
        self.original_home = os.environ.get('HOME')
        os.environ['HOME'] = self.test_dir

    def tearDown(self):
        """測試後置清理"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

        # Restore HOME
        if self.original_home:
            os.environ['HOME'] = self.original_home
        elif 'HOME' in os.environ:
            del os.environ['HOME']

    def test_save_tokens(self):
        """測試：儲存 Token"""
        from src.edge_app.auth.token_cache import EdgeTokenCache

        cache = EdgeTokenCache()

        # JWT format tokens (mock)
        access_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwiZXhwIjoxNzM1MTAwMDAwfQ.signature"
        refresh_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwiZXhwIjoxNzM1MjAwMDAwfQ.signature"
        device_id = "test-device-123"
        user_info = {"username": "testuser", "user_id": 1}

        result = cache.save_tokens(access_token, refresh_token, device_id, user_info)
        self.assertTrue(result)

    def test_get_access_token(self):
        """測試：讀取 Access Token"""
        from src.edge_app.auth.token_cache import EdgeTokenCache

        cache = EdgeTokenCache()

        access_token = "test.access.token"
        refresh_token = "test.refresh.token"
        device_id = "test-device-123"
        user_info = {"username": "testuser"}

        cache.save_tokens(access_token, refresh_token, device_id, user_info)
        retrieved_token = cache.get_access_token()

        self.assertEqual(retrieved_token, access_token)

    def test_get_refresh_token(self):
        """測試：讀取 Refresh Token"""
        from src.edge_app.auth.token_cache import EdgeTokenCache

        cache = EdgeTokenCache()

        access_token = "test.access.token"
        refresh_token = "test.refresh.token"
        device_id = "test-device-123"
        user_info = {"username": "testuser"}

        cache.save_tokens(access_token, refresh_token, device_id, user_info)
        retrieved_token = cache.get_refresh_token()

        self.assertEqual(retrieved_token, refresh_token)

    def test_access_token_expiration_check(self):
        """測試：Access Token 過期檢測"""
        from src.edge_app.auth.token_cache import EdgeTokenCache

        cache = EdgeTokenCache()

        # Create token with past expiration
        past_time = int(time.time()) - 3600  # 1 hour ago
        payload = json.dumps({'exp': past_time})
        payload_b64 = base64.urlsafe_b64encode(payload.encode()).decode().rstrip('=')
        access_token = f"header.{payload_b64}.signature"
        refresh_token = "test.refresh.token"
        device_id = "test-device-123"
        user_info = {"username": "testuser"}

        cache.save_tokens(access_token, refresh_token, device_id, user_info)

        # Should detect expiration
        self.assertFalse(cache.is_access_token_valid())

    def test_refresh_token_expiration_check(self):
        """測試：Refresh Token 過期檢測"""
        from src.edge_app.auth.token_cache import EdgeTokenCache

        cache = EdgeTokenCache()

        # Create token with future expiration for access
        future_time = int(time.time()) + 3600
        # Properly encode JWT payload
        payload_access = json.dumps({'exp': future_time})
        payload_access_b64 = base64.urlsafe_b64encode(payload_access.encode()).decode().rstrip('=')
        access_token = f"header.{payload_access_b64}.signature"

        # Create token with past expiration for refresh
        past_time = int(time.time()) - 3600
        payload_refresh = json.dumps({'exp': past_time})
        payload_refresh_b64 = base64.urlsafe_b64encode(payload_refresh.encode()).decode().rstrip('=')
        refresh_token = f"header.{payload_refresh_b64}.signature"

        device_id = "test-device-123"
        user_info = {"username": "testuser"}

        cache.save_tokens(access_token, refresh_token, device_id, user_info)

        # Access should be valid
        self.assertTrue(cache.is_access_token_valid())
        # Refresh should be expired
        self.assertFalse(cache.is_refresh_token_valid())

    def test_get_device_id(self):
        """測試：取得 Device ID"""
        from src.edge_app.auth.token_cache import EdgeTokenCache

        cache = EdgeTokenCache()

        device_id = cache.get_device_id()

        # Should return a valid device ID (64 char hex)
        self.assertIsInstance(device_id, str)
        self.assertEqual(len(device_id), 64)

    def test_get_user_info(self):
        """測試：取得使用者資訊"""
        from src.edge_app.auth.token_cache import EdgeTokenCache

        cache = EdgeTokenCache()

        access_token = "test.access.token"
        refresh_token = "test.refresh.token"
        device_id = "test-device-123"
        user_info = {"username": "testuser", "email": "test@example.com"}

        cache.save_tokens(access_token, refresh_token, device_id, user_info)
        retrieved_info = cache.get_user_info()

        self.assertEqual(retrieved_info, user_info)

    def test_clear_tokens(self):
        """測試：清除 Token"""
        from src.edge_app.auth.token_cache import EdgeTokenCache

        cache = EdgeTokenCache()

        # Save tokens
        access_token = "test.access.token"
        refresh_token = "test.refresh.token"
        device_id = "test-device-123"
        user_info = {"username": "testuser"}

        cache.save_tokens(access_token, refresh_token, device_id, user_info)

        # Clear tokens
        result = cache.clear_tokens()
        self.assertTrue(result)

        # Verify tokens are cleared
        self.assertIsNone(cache.get_access_token())
        self.assertIsNone(cache.get_refresh_token())
        self.assertIsNone(cache.get_user_info())

    def test_no_tokens_initially(self):
        """測試：初始無 Token"""
        from src.edge_app.auth.token_cache import EdgeTokenCache

        cache = EdgeTokenCache()

        self.assertIsNone(cache.get_access_token())
        self.assertIsNone(cache.get_refresh_token())
        self.assertIsNone(cache.get_user_info())
        self.assertFalse(cache.is_access_token_valid())
        self.assertFalse(cache.is_refresh_token_valid())

    def test_token_overwrite(self):
        """測試：Token 覆寫"""
        from src.edge_app.auth.token_cache import EdgeTokenCache

        cache = EdgeTokenCache()

        # Save first set of tokens
        access_token1 = "test.access.token1"
        refresh_token1 = "test.refresh.token1"
        device_id = "test-device-123"
        user_info1 = {"username": "user1"}

        cache.save_tokens(access_token1, refresh_token1, device_id, user_info1)

        # Overwrite with second set
        access_token2 = "test.access.token2"
        refresh_token2 = "test.refresh.token2"
        user_info2 = {"username": "user2"}

        cache.save_tokens(access_token2, refresh_token2, device_id, user_info2)

        # Verify second set is stored
        self.assertEqual(cache.get_access_token(), access_token2)
        self.assertEqual(cache.get_refresh_token(), refresh_token2)
        self.assertEqual(cache.get_user_info(), user_info2)

    def test_corrupted_token_file(self):
        """測試：損壞檔案處理"""
        from src.edge_app.auth.token_cache import EdgeTokenCache

        cache = EdgeTokenCache()

        # Create corrupted file
        token_file = os.path.join(self.cache_dir, 'tokens.enc')
        with open(token_file, 'wb') as f:
            f.write(b'corrupted data that cannot be decrypted')

        # Should handle gracefully
        self.assertIsNone(cache.get_access_token())
        self.assertIsNone(cache.get_refresh_token())

    def test_invalid_json_in_token_file(self):
        """測試：無效 JSON 處理"""
        from src.edge_app.auth.token_cache import EdgeTokenCache

        cache = EdgeTokenCache()

        # Create file with invalid JSON (but valid encryption)
        token_file = os.path.join(self.cache_dir, 'tokens.enc')
        encryption = TokenEncryption()
        encrypted_str = encryption.encrypt("not valid json")

        with open(token_file, 'w', encoding='utf-8') as f:
            f.write(encrypted_str)

        # Should handle gracefully
        self.assertIsNone(cache.get_access_token())

    def test_token_cache_with_platform_storage(self):
        """測試：平台儲存整合"""
        from src.edge_app.auth.token_cache import EdgeTokenCache

        # This test checks that EdgeTokenCache can work with PlatformStorage
        cache = EdgeTokenCache()

        access_token = "test.access.token"
        refresh_token = "test.refresh.token"
        device_id = "test-device-123"
        user_info = {"username": "testuser"}

        # Should save using platform storage (or fallback)
        result = cache.save_tokens(access_token, refresh_token, device_id, user_info)
        self.assertTrue(result)

        # Should retrieve correctly
        self.assertEqual(cache.get_access_token(), access_token)

    def test_token_cache_fallback_mode(self):
        """測試：Fallback 模式"""
        from src.edge_app.auth.token_cache import EdgeTokenCache

        # Mock platform storage to fail
        with patch.object(PlatformStorage, 'is_available', return_value=False):
            cache = EdgeTokenCache()

            access_token = "test.access.token"
            refresh_token = "test.refresh.token"
            device_id = "test-device-123"
            user_info = {"username": "testuser"}

            # Should fall back to encrypted file storage
            result = cache.save_tokens(access_token, refresh_token, device_id, user_info)
            self.assertTrue(result)

            # Should retrieve correctly
            self.assertEqual(cache.get_access_token(), access_token)


if __name__ == '__main__':
    unittest.main()
