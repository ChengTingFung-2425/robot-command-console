"""
Cloud API 測試

測試雲服務 API 的認證、儲存功能
"""

import io
import tempfile
import unittest

from Cloud.api.auth import CloudAuthService
from Cloud.api.storage import CloudStorageService


class TestCloudAuthService(unittest.TestCase):
    """測試雲服務認證"""

    def setUp(self):
        """設定測試環境"""
        self.auth_service = CloudAuthService(jwt_secret="test-secret-key")

    def test_generate_token(self):
        """測試生成 Token"""
        token = self.auth_service.generate_token(
            user_id="user-123",
            username="test_user",
            role="user"
        )
        self.assertIsInstance(token, str)
        self.assertTrue(len(token) > 0)

    def test_verify_token_valid(self):
        """測試驗證有效 Token"""
        # 生成 Token
        token = self.auth_service.generate_token(
            user_id="user-123",
            username="test_user",
            role="user"
        )

        # 驗證 Token
        payload = self.auth_service.verify_token(token)
        self.assertIsNotNone(payload)
        self.assertEqual(payload["user_id"], "user-123")
        self.assertEqual(payload["username"], "test_user")
        self.assertEqual(payload["role"], "user")

    def test_verify_token_invalid(self):
        """測試驗證無效 Token"""
        payload = self.auth_service.verify_token("invalid-token")
        self.assertIsNone(payload)

    def test_hash_password(self):
        """測試密碼雜湊"""
        password = "test_password"
        hashed = self.auth_service.hash_password(password)
        self.assertIsInstance(hashed, str)
        self.assertNotEqual(hashed, password)

    def test_verify_password(self):
        """測試密碼驗證"""
        password = "test_password"
        hashed = self.auth_service.hash_password(password)

        # 正確密碼
        self.assertTrue(self.auth_service.verify_password(password, hashed))

        # 錯誤密碼
        self.assertFalse(self.auth_service.verify_password("wrong_password", hashed))


class TestCloudStorageService(unittest.TestCase):
    """測試雲服務儲存"""

    def setUp(self):
        """設定測試環境"""
        # 建立臨時目錄
        self.temp_dir = tempfile.mkdtemp()
        self.storage_service = CloudStorageService(
            storage_path=self.temp_dir,
            max_file_size=1024 * 1024  # 1MB
        )

    def tearDown(self):
        """清理測試環境"""
        # 清理臨時目錄
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_upload_file(self):
        """測試上傳檔案"""
        # 建立測試檔案
        file_content = b"Test file content"
        file_data = io.BytesIO(file_content)

        # 上傳檔案
        result = self.storage_service.upload_file(
            file_data=file_data,
            filename="test.txt",
            user_id="user-123",
            category="test"
        )

        # 驗證結果
        self.assertIn("file_id", result)
        self.assertEqual(result["filename"], "test.txt")
        self.assertEqual(result["size"], len(file_content))
        self.assertEqual(result["category"], "test")
        self.assertEqual(result["user_id"], "user-123")

    def test_upload_file_too_large(self):
        """測試上傳過大檔案"""
        # 建立超過限制的檔案
        file_content = b"x" * (2 * 1024 * 1024)  # 2MB
        file_data = io.BytesIO(file_content)

        # 應該拋出 ValueError
        with self.assertRaises(ValueError):
            self.storage_service.upload_file(
                file_data=file_data,
                filename="large.txt",
                user_id="user-123",
                category="test"
            )

    def test_download_file(self):
        """測試下載檔案"""
        # 先上傳檔案
        file_content = b"Test file content"
        file_data = io.BytesIO(file_content)
        result = self.storage_service.upload_file(
            file_data=file_data,
            filename="test.txt",
            user_id="user-123",
            category="test"
        )
        file_id = result["file_id"]

        # 下載檔案
        downloaded_content = self.storage_service.download_file(
            file_id=file_id,
            user_id="user-123",
            category="test"
        )

        # 驗證內容
        self.assertIsNotNone(downloaded_content)
        self.assertEqual(downloaded_content, file_content)

    def test_download_file_not_found(self):
        """測試下載不存在的檔案"""
        content = self.storage_service.download_file(
            file_id="nonexistent",
            user_id="user-123",
            category="test"
        )
        self.assertIsNone(content)

    def test_delete_file(self):
        """測試刪除檔案"""
        # 先上傳檔案
        file_content = b"Test file content"
        file_data = io.BytesIO(file_content)
        result = self.storage_service.upload_file(
            file_data=file_data,
            filename="test.txt",
            user_id="user-123",
            category="test"
        )
        file_id = result["file_id"]

        # 刪除檔案
        success = self.storage_service.delete_file(
            file_id=file_id,
            user_id="user-123",
            category="test"
        )
        self.assertTrue(success)

        # 驗證檔案已刪除
        content = self.storage_service.download_file(
            file_id=file_id,
            user_id="user-123",
            category="test"
        )
        self.assertIsNone(content)

    def test_list_files(self):
        """測試列出檔案"""
        # 上傳多個檔案
        for i in range(3):
            file_data = io.BytesIO(f"Test content {i}".encode())
            self.storage_service.upload_file(
                file_data=file_data,
                filename=f"test_{i}.txt",
                user_id="user-123",
                category="test"
            )

        # 列出檔案
        files = self.storage_service.list_files(
            user_id="user-123",
            category="test"
        )

        # 驗證結果
        self.assertEqual(len(files), 3)
        for file_info in files:
            self.assertIn("file_id", file_info)
            self.assertIn("filename", file_info)
            self.assertIn("size", file_info)

    def test_get_storage_stats(self):
        """測試取得儲存統計"""
        # 上傳檔案
        file_content = b"Test file content"
        file_data = io.BytesIO(file_content)
        self.storage_service.upload_file(
            file_data=file_data,
            filename="test.txt",
            user_id="user-123",
            category="test"
        )

        # 取得統計
        stats = self.storage_service.get_storage_stats(user_id="user-123")

        # 驗證統計
        self.assertEqual(stats["user_id"], "user-123")
        self.assertEqual(stats["total_files"], 1)
        self.assertEqual(stats["total_size"], len(file_content))
        self.assertGreaterEqual(stats["total_size_mb"], 0)  # 允許等於 0（小檔案）


if __name__ == '__main__':
    unittest.main()
