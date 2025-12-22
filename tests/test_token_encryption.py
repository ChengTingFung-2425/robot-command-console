"""
測試 Token Encryption 功能
Step 2: Token Encryption（Phase 2.1 TDD 流程）
"""
import unittest
import os
import sys
import tempfile
import shutil

# 加入專案根目錄至 sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.edge_app.auth.encryption import TokenEncryption


class TestTokenEncryption(unittest.TestCase):
    """測試 Token 加密功能"""

    def setUp(self):
        """測試前準備"""
        self.test_dir = tempfile.mkdtemp()
        self.encryption = TokenEncryption(storage_dir=self.test_dir)

    def tearDown(self):
        """測試後清理"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_encryption_key_generation(self):
        """測試加密金鑰生成"""
        key = self.encryption._get_or_create_key()
        self.assertIsInstance(key, bytes)
        self.assertEqual(len(key), 44)  # Fernet key 是 44 bytes（base64 編碼）

    def test_encrypt_decrypt_roundtrip(self):
        """測試加密解密往返"""
        original_data = "test_access_token_12345"
        encrypted = self.encryption.encrypt(original_data)
        decrypted = self.encryption.decrypt(encrypted)
        self.assertEqual(original_data, decrypted)

    def test_encryption_produces_different_ciphertext(self):
        """測試相同資料加密產生不同密文（驗證 IV/nonce 隨機性）"""
        data = "same_token"
        encrypted1 = self.encryption.encrypt(data)
        encrypted2 = self.encryption.encrypt(data)
        # Fernet 會自動加入 timestamp 和隨機 IV，所以密文應不同
        self.assertNotEqual(encrypted1, encrypted2)

    def test_encryption_key_persistence(self):
        """測試金鑰持久化"""
        # 第一次生成金鑰
        encryption1 = TokenEncryption(storage_dir=self.test_dir)
        key1 = encryption1._get_or_create_key()

        # 第二次應讀取相同金鑰
        encryption2 = TokenEncryption(storage_dir=self.test_dir)
        key2 = encryption2._get_or_create_key()

        self.assertEqual(key1, key2)

    def test_salt_uniqueness(self):
        """測試 Salt 唯一性"""
        # 建立兩個不同目錄的 encryption 實例
        test_dir2 = tempfile.mkdtemp()
        try:
            encryption1 = TokenEncryption(storage_dir=self.test_dir)
            encryption2 = TokenEncryption(storage_dir=test_dir2)

            salt1 = encryption1._get_or_create_salt()
            salt2 = encryption2._get_or_create_salt()

            # 不同實例應有不同 salt
            self.assertNotEqual(salt1, salt2)
        finally:
            if os.path.exists(test_dir2):
                shutil.rmtree(test_dir2)

    def test_decrypt_invalid_data(self):
        """測試解密無效資料"""
        with self.assertRaises(Exception):
            self.encryption.decrypt("invalid_encrypted_data")

    def test_key_file_permissions_linux(self):
        """測試金鑰檔案權限（Linux）"""
        if os.name != 'posix':
            self.skipTest("僅在 Linux 上測試檔案權限")

        encryption = TokenEncryption(storage_dir=self.test_dir)
        encryption._get_or_create_key()  # 觸發金鑰檔案建立

        key_file = os.path.join(self.test_dir, 'encryption.key')
        stat_info = os.stat(key_file)
        file_mode = stat_info.st_mode & 0o777

        # 應為 0o600（僅擁有者可讀寫）
        self.assertEqual(file_mode, 0o600, f"檔案權限應為 600，實際為 {oct(file_mode)}")


if __name__ == '__main__':
    unittest.main()
