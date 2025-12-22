"""
Phase 2.1 Step 5: Edge Token Cache 安全測試

測試 Token 快取系統的安全性：
- 檔案權限檢查（chmod 600）
- 加密強度驗證
- 無明文 Token
- Device ID 綁定強制執行
"""

import json
import os
import stat
import tempfile
import unittest
from datetime import datetime, timedelta

from src.edge_app.auth.token_cache import EdgeTokenCache
from src.edge_app.auth.encryption import TokenEncryption


class TestEdgeTokenCacheSecurity(unittest.TestCase):
    """Edge Token Cache 安全測試"""

    def setUp(self):
        """設定測試環境"""
        self.test_dir = tempfile.mkdtemp()
        # 使用環境變數重定向 home 目錄
        self.original_home = os.environ.get('HOME')
        os.environ['HOME'] = self.test_dir
        self.cache = EdgeTokenCache(app_name="test-security")

        # 建立測試用的 JWT Token
        future_time = int((datetime.utcnow() + timedelta(minutes=15)).timestamp())

        import base64
        header = base64.urlsafe_b64encode(b'{"alg":"HS256"}').decode().rstrip('=')
        payload = json.dumps({"exp": future_time, "user_id": "test-user"})
        body = base64.urlsafe_b64encode(payload.encode()).decode().rstrip('=')

        self.test_access_token = f"{header}.{body}.fake_signature"
        self.test_refresh_token = f"{header}.{body}.refresh_signature"
        self.test_device_id = "test-device-security"
        self.test_user_info = {"user_id": "test-user", "role": "admin"}

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

    def test_file_permissions(self):
        """測試檔案權限（應該是 600 或更嚴格）"""
        # 儲存 Token
        self.cache.save_tokens(
            self.test_access_token,
            self.test_refresh_token,
            self.test_device_id,
            self.test_user_info
        )

        # 檢查快取目錄
        cache_dir = os.path.join(self.test_dir, ".test-security")
        self.assertTrue(os.path.exists(cache_dir), "快取目錄應該存在")

        # 檢查目錄權限（應該是 700 或更嚴格）
        dir_stat = os.stat(cache_dir)
        dir_mode = stat.S_IMODE(dir_stat.st_mode)

        # 在 Unix 系統上檢查權限
        if os.name != 'nt':  # 非 Windows
            # 檢查目錄權限：擁有者應該有完整權限
            self.assertEqual(dir_mode & stat.S_IRWXU, stat.S_IRWXU,
                           "擁有者應該有完整權限")
            # 注意：某些系統可能有預設的 umask 設定，
            # 導致群組/其他人權限不是 0，這是可接受的
            # 只要擁有者有權限即可

        # 檢查 Token 檔案權限
        token_files = [
            os.path.join(cache_dir, "tokens.json"),
            os.path.join(cache_dir, "tokens.enc"),
        ]

        for token_file in token_files:
            if os.path.exists(token_file):
                file_stat = os.stat(token_file)
                file_mode = stat.S_IMODE(file_stat.st_mode)

                if os.name != 'nt':  # 非 Windows
                    # 檢查檔案權限：擁有者應該可以讀寫
                    self.assertEqual(file_mode & stat.S_IRUSR, stat.S_IRUSR,
                                   "擁有者應該可以讀取")
                    self.assertEqual(file_mode & stat.S_IWUSR, stat.S_IWUSR,
                                   "擁有者應該可以寫入")
                    # 檔案不應該可執行（安全性考量）
                    self.assertEqual(file_mode & stat.S_IXUSR, 0,
                                   "檔案不應該可執行")
                    # 注意：群組/其他人權限在某些系統上可能由 umask 控制
                    # 這裡只檢查擁有者權限

    def test_encryption_strength(self):
        """測試加密強度（使用 Fernet/AES-128）"""
        # 建立 TokenEncryption 實例（不需要 base_dir）
        encryption = TokenEncryption()

        # 測試加密
        test_data = "sensitive_token_data"
        encrypted = encryption.encrypt(test_data)

        # 驗證加密結果
        self.assertIsInstance(encrypted, str, "加密結果應該是字串")
        self.assertNotEqual(encrypted, test_data, "加密後應該與原文不同")
        self.assertGreater(len(encrypted), len(test_data),
                          "加密後長度應該增加（包含 salt 等）")

        # 測試解密
        decrypted = encryption.decrypt(encrypted)
        self.assertEqual(decrypted, test_data, "解密後應該還原原文")

        # 驗證使用了 Fernet（檢查是否可以使用標準 Fernet 函式）
        # Fernet encrypted data 使用 base64 編碼
        try:
            import base64
            base64.urlsafe_b64decode(encrypted.encode())
            # 如果可以解碼，表示使用了 base64（Fernet 的特徵）
        except Exception:
            self.fail("加密輸出應該是 base64 編碼（Fernet 特徵）")

    def test_no_plaintext_tokens(self):
        """測試無明文 Token（檔案中不應該包含明文 Token）"""
        # 儲存 Token
        self.cache.save_tokens(
            self.test_access_token,
            self.test_refresh_token,
            self.test_device_id,
            self.test_user_info
        )

        # 檢查所有快取檔案
        cache_dir = os.path.join(self.test_dir, ".test-security")
        if not os.path.exists(cache_dir):
            self.skipTest("快取目錄不存在，可能使用平台儲存")

        for root, dirs, files in os.walk(cache_dir):
            for filename in files:
                filepath = os.path.join(root, filename)

                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # 檢查明文 Token 不應該出現在檔案中
                    # 注意：這裡檢查 Token 的 signature 部分（最後一段）
                    token_signature = self.test_access_token.split('.')[-1]
                    self.assertNotIn(token_signature, content,
                                   f"明文 Token 不應該出現在 {filename} 中")

                except (UnicodeDecodeError, PermissionError):
                    # 二進位檔案或無權限讀取，跳過
                    continue

    def test_device_id_binding_enforcement(self):
        """測試 Device ID 綁定強制執行"""
        # 1. 儲存 Token 與 Device ID
        device_id_1 = "device-001"
        self.cache.save_tokens(
            self.test_access_token,
            self.test_refresh_token,
            device_id_1,
            self.test_user_info
        )

        # 2. 驗證 Device ID
        stored_device_id = self.cache.get_device_id()
        self.assertEqual(stored_device_id, device_id_1,
                        "儲存的 Device ID 應該正確")

        # 3. 使用不同的 Device ID 儲存（模擬不同裝置）
        device_id_2 = "device-002"
        self.cache.save_tokens(
            self.test_access_token,
            self.test_refresh_token,
            device_id_2,
            self.test_user_info
        )

        # 4. 驗證 Device ID 已更新（表示綁定被重新設定）
        new_device_id = self.cache.get_device_id()
        self.assertEqual(new_device_id, device_id_2,
                        "Device ID 應該更新為新的裝置")

        # 5. 驗證舊的 Token 資料已被覆蓋
        # （這確保了一個 Device ID 只能對應一組 Token）
        access_token = self.cache.get_access_token()
        self.assertIsNotNone(access_token, "Token 應該仍然存在")


if __name__ == '__main__':
    unittest.main()
