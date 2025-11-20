"""
測試安全功能
包括 token rotation、token expiry、auth enforcement 和 secret storage
"""

import sys
import os
import unittest
import asyncio
from datetime import datetime, timedelta
from uuid import uuid4

# 添加 MCP 目錄到路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from MCP.auth_manager import AuthManager
from MCP.logging_monitor import LoggingMonitor
from MCP.secret_storage import (
    EnvironmentSecretStorage,
    FileSecretStorage,
    KeychainSecretStorage,
    DPAPISecretStorage,
    ChainedSecretStorage,
    create_default_storage
)
import tempfile
import shutil


class TestTokenRotation(unittest.TestCase):
    """測試 Token 輪替功能"""
    
    def setUp(self):
        """設定測試環境"""
        self.logging_monitor = LoggingMonitor()
        self.auth_manager = AuthManager(logging_monitor=self.logging_monitor)
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # 註冊測試使用者
        self.loop.run_until_complete(
            self.auth_manager.register_user(
                user_id="test-user",
                username="testuser",
                password="testpass123",
                role="operator"
            )
        )
    
    def tearDown(self):
        """清理測試環境"""
        self.loop.close()
    
    def test_token_rotation_with_valid_token(self):
        """測試使用有效 token 進行輪替"""
        # 建立初始 token
        token1 = self.loop.run_until_complete(
            self.auth_manager.create_token("test-user", "operator")
        )
        
        # 驗證 token1 有效
        is_valid = self.loop.run_until_complete(
            self.auth_manager.verify_token(token1)
        )
        self.assertTrue(is_valid)
        
        # 解碼 token1 獲取資訊
        payload1 = self.loop.run_until_complete(
            self.auth_manager.decode_token(token1)
        )
        self.assertIsNotNone(payload1)
        self.assertEqual(payload1["user_id"], "test-user")
        self.assertEqual(payload1["role"], "operator")
        
        # 建立新 token（模擬輪替）
        token2 = self.loop.run_until_complete(
            self.auth_manager.create_token(
                payload1["user_id"],
                payload1["role"]
            )
        )
        
        # 驗證兩個 token 都有效
        self.assertTrue(self.loop.run_until_complete(
            self.auth_manager.verify_token(token1)
        ))
        self.assertTrue(self.loop.run_until_complete(
            self.auth_manager.verify_token(token2)
        ))
        
        # 驗證新 token 包含相同的使用者資訊
        payload2 = self.loop.run_until_complete(
            self.auth_manager.decode_token(token2)
        )
        self.assertEqual(payload2["user_id"], payload1["user_id"])
        self.assertEqual(payload2["role"], payload1["role"])
    
    def test_token_rotation_with_expired_token(self):
        """測試使用過期 token 進行輪替應該失敗"""
        # 建立過期 token
        expired_token = self.loop.run_until_complete(
            self.auth_manager.create_token("test-user", "operator", expires_in_hours=-1)
        )
        
        # 驗證 token 已過期
        is_valid = self.loop.run_until_complete(
            self.auth_manager.verify_token(expired_token)
        )
        self.assertFalse(is_valid)
        
        # 嘗試解碼過期 token
        payload = self.loop.run_until_complete(
            self.auth_manager.decode_token(expired_token)
        )
        self.assertIsNone(payload)
    
    def test_token_expiry_configurable(self):
        """測試 token 過期時間可配置"""
        # 建立不同過期時間的 token
        token_1h = self.loop.run_until_complete(
            self.auth_manager.create_token("test-user", "operator", expires_in_hours=1)
        )
        token_24h = self.loop.run_until_complete(
            self.auth_manager.create_token("test-user", "operator", expires_in_hours=24)
        )
        
        # 解碼並檢查過期時間
        payload_1h = self.loop.run_until_complete(
            self.auth_manager.decode_token(token_1h)
        )
        payload_24h = self.loop.run_until_complete(
            self.auth_manager.decode_token(token_24h)
        )
        
        self.assertIsNotNone(payload_1h)
        self.assertIsNotNone(payload_24h)
        
        # 檢查過期時間差異
        exp_1h = datetime.fromtimestamp(payload_1h["exp"])
        exp_24h = datetime.fromtimestamp(payload_24h["exp"])
        
        time_diff = (exp_24h - exp_1h).total_seconds()
        expected_diff = 23 * 3600  # 23 小時
        
        # 允許一些誤差
        self.assertGreater(time_diff, expected_diff - 60)
        self.assertLess(time_diff, expected_diff + 60)


class TestAuthEnforcement(unittest.TestCase):
    """測試認證強制執行"""
    
    def setUp(self):
        """設定測試環境"""
        self.logging_monitor = LoggingMonitor()
        self.auth_manager = AuthManager(logging_monitor=self.logging_monitor)
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
    
    def tearDown(self):
        """清理測試環境"""
        self.loop.close()
    
    def test_invalid_token_rejected(self):
        """測試無效 token 被拒絕"""
        invalid_token = "invalid.token.string"
        trace_id = str(uuid4())
        
        is_valid = self.loop.run_until_complete(
            self.auth_manager.verify_token(invalid_token, trace_id=trace_id)
        )
        
        self.assertFalse(is_valid)
        
        # 檢查審計日誌
        events = self.loop.run_until_complete(
            self.logging_monitor.get_events(trace_id=trace_id)
        )
        self.assertGreater(len(events), 0)
    
    def test_expired_token_rejected(self):
        """測試過期 token 被拒絕"""
        # 註冊使用者
        self.loop.run_until_complete(
            self.auth_manager.register_user(
                user_id="expired-user",
                username="expireduser",
                password="pass123",
                role="viewer"
            )
        )
        
        # 建立過期 token
        expired_token = self.loop.run_until_complete(
            self.auth_manager.create_token("expired-user", "viewer", expires_in_hours=-1)
        )
        
        trace_id = str(uuid4())
        is_valid = self.loop.run_until_complete(
            self.auth_manager.verify_token(expired_token, trace_id=trace_id)
        )
        
        self.assertFalse(is_valid)
        
        # 檢查審計日誌
        events = self.loop.run_until_complete(
            self.logging_monitor.get_events(trace_id=trace_id)
        )
        self.assertGreater(len(events), 0)
    
    def test_missing_token_rejected(self):
        """測試缺少 token 的請求被拒絕"""
        # 在實際的 HTTP 請求中，middleware 會檢查 Authorization header
        # 這裡我們只測試 verify_token 需要有效的 token
        is_valid = self.loop.run_until_complete(
            self.auth_manager.verify_token("")
        )
        self.assertFalse(is_valid)
    
    def test_valid_token_accepted(self):
        """測試有效 token 被接受"""
        # 註冊使用者
        self.loop.run_until_complete(
            self.auth_manager.register_user(
                user_id="valid-user",
                username="validuser",
                password="pass123",
                role="operator"
            )
        )
        
        # 建立有效 token
        valid_token = self.loop.run_until_complete(
            self.auth_manager.create_token("valid-user", "operator")
        )
        
        is_valid = self.loop.run_until_complete(
            self.auth_manager.verify_token(valid_token)
        )
        
        self.assertTrue(is_valid)


class TestSecretStorage(unittest.TestCase):
    """測試秘密儲存功能"""
    
    def setUp(self):
        """設定測試環境"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.temp_dir, "secrets.json")
    
    def tearDown(self):
        """清理測試環境"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_environment_secret_storage_read_only(self):
        """測試環境變數儲存只讀"""
        storage = EnvironmentSecretStorage()
        
        # 設定環境變數
        os.environ["TEST_SECRET"] = "test-value"
        
        # 讀取成功
        value = storage.get_secret("TEST_SECRET")
        self.assertEqual(value, "test-value")
        
        # 寫入失敗
        success = storage.set_secret("NEW_SECRET", "new-value")
        self.assertFalse(success)
        
        # 刪除失敗
        success = storage.delete_secret("TEST_SECRET")
        self.assertFalse(success)
        
        # 清理
        del os.environ["TEST_SECRET"]
    
    def test_file_secret_storage_crud(self):
        """測試檔案儲存的 CRUD 操作"""
        storage = FileSecretStorage(self.test_file)
        
        # 設定秘密
        success = storage.set_secret("key1", "value1")
        self.assertTrue(success)
        
        # 讀取秘密
        value = storage.get_secret("key1")
        self.assertEqual(value, "value1")
        
        # 更新秘密
        success = storage.set_secret("key1", "value2")
        self.assertTrue(success)
        value = storage.get_secret("key1")
        self.assertEqual(value, "value2")
        
        # 設定多個秘密
        storage.set_secret("key2", "value2")
        storage.set_secret("key3", "value3")
        
        # 列出秘密
        keys = storage.list_secrets()
        self.assertEqual(sorted(keys), ["key1", "key2", "key3"])
        
        # 刪除秘密
        success = storage.delete_secret("key2")
        self.assertTrue(success)
        value = storage.get_secret("key2")
        self.assertIsNone(value)
        
        # 驗證檔案權限
        file_stat = os.stat(self.test_file)
        file_mode = oct(file_stat.st_mode)[-3:]
        self.assertEqual(file_mode, "600")
    
    def test_file_secret_storage_nonexistent_key(self):
        """測試讀取不存在的秘密"""
        storage = FileSecretStorage(self.test_file)
        
        value = storage.get_secret("nonexistent")
        self.assertIsNone(value)
    
    def test_chained_secret_storage(self):
        """測試鏈式秘密儲存"""
        # 設定環境變數
        os.environ["ENV_SECRET"] = "env-value"
        
        # 建立鏈式儲存
        env_storage = EnvironmentSecretStorage()
        file_storage = FileSecretStorage(self.test_file)
        chained = ChainedSecretStorage([env_storage, file_storage])
        
        # 從環境變數讀取
        value = chained.get_secret("ENV_SECRET")
        self.assertEqual(value, "env-value")
        
        # 寫入到檔案儲存（環境變數儲存不支援寫入）
        success = chained.set_secret("FILE_SECRET", "file-value")
        self.assertTrue(success)
        
        # 從檔案讀取
        value = chained.get_secret("FILE_SECRET")
        self.assertEqual(value, "file-value")
        
        # 列出所有秘密
        keys = chained.list_secrets()
        self.assertIn("FILE_SECRET", keys)
        
        # 清理
        del os.environ["ENV_SECRET"]
    
    def test_keychain_storage_stub(self):
        """測試 Keychain 儲存 stub"""
        storage = KeychainSecretStorage()
        
        # Stub 實作應該返回 None/False
        value = storage.get_secret("test")
        self.assertIsNone(value)
        
        success = storage.set_secret("test", "value")
        self.assertFalse(success)
        
        success = storage.delete_secret("test")
        self.assertFalse(success)
        
        keys = storage.list_secrets()
        self.assertEqual(keys, [])
    
    def test_dpapi_storage_stub(self):
        """測試 DPAPI 儲存 stub"""
        storage = DPAPISecretStorage()
        
        # Stub 實作應該返回 None/False
        value = storage.get_secret("test")
        self.assertIsNone(value)
        
        success = storage.set_secret("test", "value")
        self.assertFalse(success)
        
        success = storage.delete_secret("test")
        self.assertFalse(success)
        
        keys = storage.list_secrets()
        self.assertEqual(keys, [])
    
    def test_create_default_storage(self):
        """測試建立預設儲存"""
        storage = create_default_storage()
        
        # 預設儲存應該是鏈式儲存
        self.assertIsInstance(storage, ChainedSecretStorage)
        
        # 應該包含環境變數和檔案儲存
        self.assertEqual(len(storage.storages), 2)
        self.assertIsInstance(storage.storages[0], EnvironmentSecretStorage)
        self.assertIsInstance(storage.storages[1], FileSecretStorage)


class TestSecurityIntegration(unittest.TestCase):
    """測試安全功能整合"""
    
    def setUp(self):
        """設定測試環境"""
        self.logging_monitor = LoggingMonitor()
        self.auth_manager = AuthManager(logging_monitor=self.logging_monitor)
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        # 註冊測試使用者
        self.loop.run_until_complete(
            self.auth_manager.register_user(
                user_id="integration-user",
                username="integrationuser",
                password="integrationpass",
                role="operator"
            )
        )
    
    def tearDown(self):
        """清理測試環境"""
        self.loop.close()
    
    def test_complete_auth_flow_with_rotation(self):
        """測試完整的認證流程包含 token 輪替"""
        trace_id = str(uuid4())
        
        # 1. 使用者認證
        user_id = self.loop.run_until_complete(
            self.auth_manager.authenticate_user("integrationuser", "integrationpass")
        )
        self.assertEqual(user_id, "integration-user")
        
        # 2. 建立初始 token
        token1 = self.loop.run_until_complete(
            self.auth_manager.create_token(user_id, "operator", expires_in_hours=1)
        )
        self.assertIsNotNone(token1)
        
        # 3. 驗證 token1
        is_valid = self.loop.run_until_complete(
            self.auth_manager.verify_token(token1, trace_id=trace_id)
        )
        self.assertTrue(is_valid)
        
        # 4. 解碼 token1 獲取使用者資訊
        payload1 = self.loop.run_until_complete(
            self.auth_manager.decode_token(token1)
        )
        self.assertIsNotNone(payload1)
        self.assertEqual(payload1["user_id"], user_id)
        
        # 5. Token 輪替
        token2 = self.loop.run_until_complete(
            self.auth_manager.create_token(
                payload1["user_id"],
                payload1["role"],
                expires_in_hours=2
            )
        )
        self.assertIsNotNone(token2)
        
        # 6. 驗證新 token
        is_valid = self.loop.run_until_complete(
            self.auth_manager.verify_token(token2, trace_id=trace_id)
        )
        self.assertTrue(is_valid)
        
        # 7. 檢查權限
        has_perm = self.loop.run_until_complete(
            self.auth_manager.check_permission(user_id, "robot.move")
        )
        self.assertTrue(has_perm)
    
    def test_unauthorized_access_rejected_and_logged(self):
        """測試未授權存取被拒絕並記錄"""
        trace_id = str(uuid4())
        
        # 嘗試使用無效 token
        invalid_token = "completely.invalid.token"
        is_valid = self.loop.run_until_complete(
            self.auth_manager.verify_token(invalid_token, trace_id=trace_id)
        )
        self.assertFalse(is_valid)
        
        # 檢查審計日誌
        events = self.loop.run_until_complete(
            self.logging_monitor.get_events(trace_id=trace_id)
        )
        self.assertGreater(len(events), 0)
        
        # 驗證事件包含認證失敗資訊
        audit_event = events[0]
        self.assertIn("token", audit_event.message.lower())


if __name__ == '__main__':
    unittest.main()
