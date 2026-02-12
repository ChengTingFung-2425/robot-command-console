"""
Edge-Cloud 同步客戶端

提供與雲服務 API 通訊的客戶端功能
"""

import logging
from typing import Optional, Dict, Any
from pathlib import Path

import requests


logger = logging.getLogger(__name__)


class CloudSyncClient:
    """Edge-Cloud 同步客戶端"""

    def __init__(
        self,
        cloud_api_url: str,
        token: Optional[str] = None,
        timeout: int = 30
    ):
        """
        初始化客戶端

        Args:
            cloud_api_url: 雲服務 API URL
            token: JWT Token（可選）
            timeout: 請求超時時間（秒）
        """
        self.cloud_api_url = cloud_api_url.rstrip('/')
        self.token = token
        self.timeout = timeout
        logger.info(f"Initialized CloudSyncClient for: {self.cloud_api_url}")

    def set_token(self, token: str):
        """
        設定 JWT Token

        Args:
            token: JWT Token
        """
        self.token = token

    def _get_headers(self) -> Dict[str, str]:
        """
        取得請求標頭

        Returns:
            請求標頭字典
        """
        headers = {}
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'
        return headers

    def health_check(self) -> Dict[str, Any]:
        """
        健康檢查

        Returns:
            健康狀態資訊
        """
        try:
            response = requests.get(
                f'{self.cloud_api_url}/health',
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}

    def upload_file(
        self,
        file_path: str,
        category: str = "general"
    ) -> Optional[Dict[str, Any]]:
        """
        上傳檔案到雲端

        Args:
            file_path: 本地檔案路徑
            category: 檔案類別

        Returns:
            上傳結果或 None（失敗）
        """
        try:
            path = Path(file_path)
            if not path.exists():
                logger.error(f"File not found: {file_path}")
                return None

            with open(path, 'rb') as f:
                files = {'file': (path.name, f)}
                data = {'category': category}

                response = requests.post(
                    f'{self.cloud_api_url}/storage/upload',
                    files=files,
                    data=data,
                    headers=self._get_headers(),
                    timeout=self.timeout
                )
                response.raise_for_status()
                return response.json()

        except requests.RequestException as e:
            logger.error(f"File upload failed: {e}")
            return None

    def download_file(
        self,
        file_id: str,
        save_path: str,
        category: str = "general"
    ) -> bool:
        """
        從雲端下載檔案

        Args:
            file_id: 檔案 ID
            save_path: 儲存路徑
            category: 檔案類別

        Returns:
            是否下載成功
        """
        try:
            params = {'category': category}
            response = requests.get(
                f'{self.cloud_api_url}/storage/download/{file_id}',
                params=params,
                headers=self._get_headers(),
                timeout=self.timeout,
                stream=True
            )
            response.raise_for_status()

            # 儲存檔案
            save_path_obj = Path(save_path)
            save_path_obj.parent.mkdir(parents=True, exist_ok=True)

            with open(save_path_obj, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            logger.info(f"File downloaded to: {save_path}")
            return True

        except requests.RequestException as e:
            logger.error(f"File download failed: {e}")
            return False

    def list_files(
        self,
        category: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        列出雲端檔案

        Args:
            category: 檔案類別（可選）

        Returns:
            檔案清單或 None（失敗）
        """
        try:
            params = {}
            if category:
                params['category'] = category

            response = requests.get(
                f'{self.cloud_api_url}/storage/files',
                params=params,
                headers=self._get_headers(),
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()

        except requests.RequestException as e:
            logger.error(f"File listing failed: {e}")
            return None

    def delete_file(
        self,
        file_id: str,
        category: str = "general"
    ) -> bool:
        """
        刪除雲端檔案

        Args:
            file_id: 檔案 ID
            category: 檔案類別

        Returns:
            是否刪除成功
        """
        try:
            params = {'category': category}
            response = requests.delete(
                f'{self.cloud_api_url}/storage/files/{file_id}',
                params=params,
                headers=self._get_headers(),
                timeout=self.timeout
            )
            response.raise_for_status()
            logger.info(f"File deleted: {file_id}")
            return True

        except requests.RequestException as e:
            logger.error(f"File deletion failed: {e}")
            return False

    def get_storage_stats(self) -> Optional[Dict[str, Any]]:
        """
        取得儲存統計

        Returns:
            統計資訊或 None（失敗）
        """
        try:
            response = requests.get(
                f'{self.cloud_api_url}/storage/stats',
                headers=self._get_headers(),
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()

        except requests.RequestException as e:
            logger.error(f"Stats retrieval failed: {e}")
            return None

    def sync_files(
        self,
        local_dir: str,
        category: str = "general",
        direction: str = "both"
    ) -> Dict[str, Any]:
        """
        同步本地與雲端檔案

        Args:
            local_dir: 本地目錄
            category: 檔案類別
            direction: 同步方向（"upload", "download", "both"）

        Returns:
            同步結果統計
        """
        result = {
            "uploaded": 0,
            "downloaded": 0,
            "errors": 0,
            "skipped": 0
        }

        local_path = Path(local_dir)
        if not local_path.exists():
            local_path.mkdir(parents=True, exist_ok=True)

        try:
            # 取得雲端檔案清單
            cloud_files_data = self.list_files(category=category)
            if cloud_files_data is None:
                logger.error("Failed to list cloud files")
                result["errors"] += 1
                return result

            cloud_files = {f["file_id"]: f for f in cloud_files_data.get("files", [])}

            # 上傳本地檔案（如果需要）
            if direction in ["upload", "both"]:
                for file_path in local_path.glob("*"):
                    if file_path.is_file():
                        # 簡單的檔案名稱匹配（實際應使用雜湊）
                        uploaded = self.upload_file(str(file_path), category=category)
                        if uploaded:
                            result["uploaded"] += 1
                        else:
                            result["errors"] += 1

            # 下載雲端檔案（如果需要）
            if direction in ["download", "both"]:
                for file_id, file_info in cloud_files.items():
                    save_path = local_path / file_info["filename"]
                    if not save_path.exists():
                        downloaded = self.download_file(
                            file_id=file_id,
                            save_path=str(save_path),
                            category=category
                        )
                        if downloaded:
                            result["downloaded"] += 1
                        else:
                            result["errors"] += 1
                    else:
                        result["skipped"] += 1

        except Exception as e:
            logger.error(f"Sync failed: {e}")
            result["errors"] += 1

        logger.info(f"Sync completed: {result}")
        return result
