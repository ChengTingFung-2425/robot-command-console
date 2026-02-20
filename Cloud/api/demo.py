"""
Cloud API 示範腳本

示範如何使用雲服務 API 進行檔案上傳、下載、列表等操作
"""

import tempfile
from pathlib import Path

from Cloud.api.auth import CloudAuthService
from Cloud.api.storage import CloudStorageService
from Edge.cloud_client.sync_client import CloudSyncClient


def demo_auth_service():
    """示範認證服務"""
    print("=== 認證服務示範 ===")

    # 建立認證服務
    auth_service = CloudAuthService(jwt_secret="demo-secret-key")

    # 生成 Token
    token = auth_service.generate_token(
        user_id="demo-user-123",
        username="demo_user",
        role="user"
    )
    print(f"生成的 Token: {token[:50]}...")

    # 驗證 Token
    payload = auth_service.verify_token(token)
    print(f"Token 驗證結果: {payload}")

    # 密碼雜湊
    password = "demo_password"
    hashed = auth_service.hash_password(password)
    print(f"密碼雜湊: {hashed[:50]}...")

    # 驗證密碼
    is_valid = auth_service.verify_password(password, hashed)
    print(f"密碼驗證: {'成功' if is_valid else '失敗'}")
    print()


def demo_storage_service():
    """示範儲存服務"""
    print("=== 儲存服務示範 ===")

    # 建立臨時目錄作為儲存路徑
    with tempfile.TemporaryDirectory() as temp_dir:
        # 建立儲存服務
        storage_service = CloudStorageService(storage_path=temp_dir)

        # 建立測試檔案
        test_content = b"Hello, Cloud Storage!"
        import io
        file_data = io.BytesIO(test_content)

        # 上傳檔案
        result = storage_service.upload_file(
            file_data=file_data,
            filename="demo.txt",
            user_id="demo-user",
            category="demo"
        )
        print(f"檔案上傳結果: {result}")

        file_id = result["file_id"]

        # 列出檔案
        files = storage_service.list_files(user_id="demo-user", category="demo")
        print(f"檔案清單: {files}")

        # 下載檔案
        downloaded = storage_service.download_file(
            file_id=file_id,
            user_id="demo-user",
            category="demo"
        )
        print(f"下載的檔案內容: {downloaded}")

        # 取得統計
        stats = storage_service.get_storage_stats(user_id="demo-user")
        print(f"儲存統計: {stats}")

        # 刪除檔案
        deleted = storage_service.delete_file(
            file_id=file_id,
            user_id="demo-user",
            category="demo"
        )
        print(f"檔案刪除: {'成功' if deleted else '失敗'}")
    print()


def demo_sync_client():
    """示範同步客戶端（需要運行的 API 伺服器）"""
    print("=== 同步客戶端示範 ===")
    print("注意：此示範需要運行的 Cloud API 伺服器")

    # 建立同步客戶端
    client = CloudSyncClient(
        cloud_api_url="http://localhost:5000/api/cloud",
        token="demo-token"
    )

    # 健康檢查
    health = client.health_check()
    print(f"健康檢查: {health}")

    # 如果服務健康，繼續示範其他功能
    if health.get("status") == "healthy":
        print("API 服務運行中，可以進行檔案操作...")

        # 建立臨時測試檔案
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.txt"
            test_file.write_text("Test file content")

            # 上傳檔案
            result = client.upload_file(str(test_file), category="demo")
            if result:
                print(f"檔案上傳成功: {result}")

            # 列出檔案
            files = client.list_files(category="demo")
            if files:
                print(f"檔案清單: {files}")

            # 取得統計
            stats = client.get_storage_stats()
            if stats:
                print(f"儲存統計: {stats}")
    else:
        print("API 服務未運行，跳過檔案操作示範")
    print()


if __name__ == "__main__":
    print("雲服務 API 示範\n")

    # 運行各項示範
    demo_auth_service()
    demo_storage_service()
    demo_sync_client()

    print("示範完成！")
