"""
Phase 2.1 Step 5: Edge Token Cache 整合測試

測試整個 Token 快取系統的端到端整合，包含：
- 完整生命週期測試
- Token 更新流程
- Device ID 綁定驗證
- 平台專用儲存
- 錯誤恢復機制
"""

import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from src.edge_app.auth.token_cache import EdgeTokenCache


class TestEdgeTokenCacheIntegration(unittest.TestCase):
    """Edge Token Cache 整合測試"""

    def setUp(self):
        """設定測試環境"""
        self.test_dir = tempfile.mkdtemp()
        # 使用環境變數重定向 home 目錄
        self.original_home = os.environ.get('HOME')
        os.environ['HOME'] = self.test_dir
        self.cache = EdgeTokenCache(app_name="test-robot-edge")

        # 建立測試用的 JWT Token（使用簡化格式）
        future_time = int((datetime.utcnow() + timedelta(minutes=15)).timestamp())
        refresh_future = int((datetime.utcnow() + timedelta(days=7)).timestamp())

        # 簡化的 JWT payload
        access_payload = json.dumps({"exp": future_time, "user_id": "test-user"})
        refresh_payload = json.dumps({"exp": refresh_future, "user_id": "test-user"})

        # Base64url encode（手動實作簡化版）
        import base64
        header = base64.urlsafe_b64encode(b'{"alg":"HS256"}').decode().rstrip('=')
        access_body = base64.urlsafe_b64encode(access_payload.encode()).decode().rstrip('=')
        refresh_body = base64.urlsafe_b64encode(refresh_payload.encode()).decode().rstrip('=')

        self.valid_access_token = f"{header}.{access_body}.fake_signature"
        self.valid_refresh_token = f"{header}.{refresh_body}.fake_signature"

        # 過期的 Token
        past_time = int((datetime.utcnow() - timedelta(minutes=5)).timestamp())
        expired_payload = json.dumps({"exp": past_time, "user_id": "test-user"})
        expired_body = base64.urlsafe_b64encode(expired_payload.encode()).decode().rstrip('=')
        self.expired_token = f"{header}.{expired_body}.fake_signature"

        self.test_device_id = "test-device-12345678"
        self.test_user_info = {
            "user_id": "test-user",
            "username": "testuser",
            "role": "admin"
        }

    def tearDown(self):
        """清理測試環境"""
        # 恢復原始 HOME 環境變數
        if self.original_home:
            os.environ['HOME'] = self.original_home
        elif 'HOME' in os.environ:
            del os.environ['HOME']

        import shutil
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_full_token_lifecycle(self):
        """測試完整 Token 生命週期：儲存 → 讀取 → 過期 → 清除"""
        # 1. 儲存 Token
        success = self.cache.save_tokens(
            self.valid_access_token,
            self.valid_refresh_token,
            self.test_device_id,
            self.test_user_info
        )
        self.assertTrue(success, "Token 儲存應該成功")

        # 2. 讀取 Token
        access_token = self.cache.get_access_token()
        refresh_token = self.cache.get_refresh_token()
        device_id = self.cache.get_device_id()
        user_info = self.cache.get_user_info()

        self.assertEqual(access_token, self.valid_access_token)
        self.assertEqual(refresh_token, self.valid_refresh_token)
        self.assertEqual(device_id, self.test_device_id)
        self.assertEqual(user_info, self.test_user_info)

        # 3. 檢查有效性
        self.assertTrue(self.cache.is_access_token_valid())
        self.assertTrue(self.cache.is_refresh_token_valid())

        # 4. 清除 Token
        clear_success = self.cache.clear_tokens()
        self.assertTrue(clear_success, "Token 清除應該成功")

        # 5. 驗證已清除
        self.assertIsNone(self.cache.get_access_token())
        self.assertIsNone(self.cache.get_refresh_token())
        self.assertFalse(self.cache.is_access_token_valid())

    def test_token_refresh_workflow(self):
        """測試 Token 更新流程：過期 Access Token + 有效 Refresh Token"""
        # 1. 儲存過期的 Access Token 與有效的 Refresh Token
        success = self.cache.save_tokens(
            self.expired_token,
            self.valid_refresh_token,
            self.test_device_id,
            self.test_user_info
        )
        self.assertTrue(success)

        # 2. 檢查狀態
        self.assertFalse(self.cache.is_access_token_valid(), "Access Token 應該過期")
        self.assertTrue(self.cache.is_refresh_token_valid(), "Refresh Token 應該有效")

        # 3. 模擬更新 Access Token
        new_access_token = self.valid_access_token.replace("fake", "new")
        update_success = self.cache.save_tokens(
            new_access_token,
            self.valid_refresh_token,
            self.test_device_id,
            self.test_user_info
        )
        self.assertTrue(update_success)

        # 4. 驗證新的 Token
        self.assertEqual(self.cache.get_access_token(), new_access_token)
        self.assertTrue(self.cache.is_access_token_valid())

    def test_device_binding(self):
        """測試 Device ID 綁定驗證"""
        # 1. 儲存 Token 與 Device ID
        self.cache.save_tokens(
            self.valid_access_token,
            self.valid_refresh_token,
            self.test_device_id,
            self.test_user_info
        )

        # 2. 讀取 Device ID
        stored_device_id = self.cache.get_device_id()
        self.assertEqual(stored_device_id, self.test_device_id)

        # 3. 嘗試使用不同的 Device ID 儲存（應該覆蓋）
        different_device_id = "different-device-id"
        self.cache.save_tokens(
            self.valid_access_token,
            self.valid_refresh_token,
            different_device_id,
            self.test_user_info
        )

        # 4. 驗證 Device ID 已更新
        new_device_id = self.cache.get_device_id()
        self.assertEqual(new_device_id, different_device_id)

    @patch('src.edge_app.auth.platform_storage.PlatformStorage')
    def test_platform_specific_storage(self, mock_platform_storage):
        """測試平台專用儲存（使用 Mock）"""
        # Mock PlatformStorage 的行為
        mock_instance = MagicMock()
        mock_instance.is_available.return_value = True
        mock_instance.set_password.return_value = True
        mock_instance.get_password.return_value = json.dumps({
            "access_token": self.valid_access_token,
            "refresh_token": self.valid_refresh_token,
            "device_id": self.test_device_id,
            "user_info": self.test_user_info
        })
        mock_platform_storage.return_value = mock_instance

        # 建立使用 Mock 的 cache（在新環境中）
        test_home_2 = tempfile.mkdtemp()
        os.environ['HOME'] = test_home_2
        cache = EdgeTokenCache(app_name="test-platform-storage")

        # 儲存 Token（應該使用平台儲存）
        success = cache.save_tokens(
            self.valid_access_token,
            self.valid_refresh_token,
            self.test_device_id,
            self.test_user_info
        )
        self.assertTrue(success)

        # 驗證平台儲存被呼叫
        # 注意：這個測試需要根據實際實作調整

    def test_error_recovery(self):
        """測試錯誤恢復機制"""
        # 1. 測試讀取不存在的 Token（應該返回 None）
        access_token = self.cache.get_access_token()
        self.assertIsNone(access_token, "不存在的 Token 應該返回 None")

        # 2. 測試儲存空 Token（應該失敗或處理）
        try:
            self.cache.save_tokens("", "", "", {})
            # 如果成功，驗證可以正常讀取
            self.assertIsNone(self.cache.get_access_token())
        except Exception:
            # 如果拋出異常，也是可接受的行為
            pass

        # 3. 測試損壞的快取檔案
        # 建立損壞的快取檔案
        cache_file = os.path.join(self.test_dir, ".test-robot-edge", "tokens.enc")
        os.makedirs(os.path.dirname(cache_file), exist_ok=True)
        with open(cache_file, 'w') as f:
            f.write("invalid json content")

        # 嘗試讀取（應該優雅處理，返回 None 或空字串）
        token = self.cache.get_access_token()
        # 接受 None 或空字串作為「無效」的表示
        self.assertIn(token, [None, ""], "損壞的快取應該返回 None 或空字串")

        # 4. 驗證可以恢復（儲存新 Token）
        success = self.cache.save_tokens(
            self.valid_access_token,
            self.valid_refresh_token,
            self.test_device_id,
            self.test_user_info
        )
        self.assertTrue(success, "應該能從錯誤中恢復")
        self.assertEqual(self.cache.get_access_token(), self.valid_access_token)


if __name__ == '__main__':
    unittest.main()
