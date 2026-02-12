# imports
import logging
from typing import Optional, Dict, Any
import requests

logger = logging.getLogger(__name__)


class CloudSyncClient:
    """Edge ↔ Cloud 同步客戶端

    提供 Edge 應用程式與雲端服務進行指令同步的功能。
    """

    def __init__(self, cloud_api_url: str, edge_id: str, api_key: Optional[str] = None):
        """初始化客戶端

        Args:
            cloud_api_url: 雲端 API 基礎 URL（例如：https://cloud.example.com/api/cloud）
            edge_id: Edge 裝置 ID
            api_key: API 金鑰（可選，用於認證）
        """
        self.cloud_api_url = cloud_api_url.rstrip('/')
        self.edge_id = edge_id
        self.api_key = api_key
        self.session = requests.Session()
        if api_key:
            self.session.headers.update({'Authorization': f'Bearer {api_key}'})

    def upload_command(
        self,
        name: str,
        description: str,
        category: str,
        content: str,
        author_username: str,
        author_email: str,
        original_command_id: int,
        version: int = 1
    ) -> Dict[str, Any]:
        """上傳進階指令到雲端

        Args:
            name: 指令名稱
            description: 指令說明
            category: 指令分類
            content: 指令內容（JSON 格式）
            author_username: 作者用戶名
            author_email: 作者電子郵件
            original_command_id: 原始指令 ID
            version: 版本號

        Returns:
            Dict[str, Any]: API 回應

        Raises:
            requests.HTTPError: API 請求失敗
        """
        url = f'{self.cloud_api_url}/shared_commands/upload'
        payload = {
            'name': name,
            'description': description,
            'category': category,
            'content': content,
            'author_username': author_username,
            'author_email': author_email,
            'edge_id': self.edge_id,
            'original_command_id': original_command_id,
            'version': version
        }

        try:
            response = self.session.post(url, json=payload, timeout=30)
            response.raise_for_status()
            logger.info(f"Uploaded command '{name}' to cloud (ID={original_command_id})")
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to upload command '{name}': {e}")
            raise

    def search_commands(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        author: Optional[str] = None,
        min_rating: Optional[float] = None,
        sort_by: str = 'rating',
        order: str = 'desc',
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """搜尋雲端共享指令

        Args:
            query: 搜尋關鍵字
            category: 指令分類
            author: 作者用戶名
            min_rating: 最低評分
            sort_by: 排序欄位
            order: 排序方向
            limit: 每頁筆數
            offset: 分頁偏移量

        Returns:
            Dict[str, Any]: API 回應（包含指令列表與總筆數）

        Raises:
            requests.HTTPError: API 請求失敗
        """
        url = f'{self.cloud_api_url}/shared_commands/search'
        params = {
            'query': query,
            'category': category,
            'author': author,
            'min_rating': min_rating,
            'sort_by': sort_by,
            'order': order,
            'limit': limit,
            'offset': offset
        }
        # 移除 None 值
        params = {k: v for k, v in params.items() if v is not None}

        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            logger.info(
                f"Searched cloud commands: query={query}, category={category}, "
                f"found={len(response.json().get('data', {}).get('commands', []))}"
            )
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to search commands: {e}")
            raise

    def get_command(self, command_id: int) -> Dict[str, Any]:
        """取得雲端指令詳情

        Args:
            command_id: 指令 ID

        Returns:
            Dict[str, Any]: API 回應（包含指令詳情）

        Raises:
            requests.HTTPError: API 請求失敗
        """
        url = f'{self.cloud_api_url}/shared_commands/{command_id}'

        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            logger.info(f"Retrieved command {command_id} from cloud")
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to get command {command_id}: {e}")
            raise

    def download_command(self, command_id: int) -> Dict[str, Any]:
        """下載雲端指令

        Args:
            command_id: 指令 ID

        Returns:
            Dict[str, Any]: API 回應（包含指令完整內容）

        Raises:
            requests.HTTPError: API 請求失敗
        """
        url = f'{self.cloud_api_url}/shared_commands/{command_id}/download'
        payload = {'edge_id': self.edge_id}

        try:
            response = self.session.post(url, json=payload, timeout=30)
            response.raise_for_status()
            logger.info(f"Downloaded command {command_id} from cloud")
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to download command {command_id}: {e}")
            raise

    def rate_command(
        self,
        command_id: int,
        user_username: str,
        rating: int,
        comment: Optional[str] = None
    ) -> Dict[str, Any]:
        """對雲端指令評分

        Args:
            command_id: 指令 ID
            user_username: 用戶名
            rating: 評分（1-5）
            comment: 評論

        Returns:
            Dict[str, Any]: API 回應

        Raises:
            requests.HTTPError: API 請求失敗
        """
        url = f'{self.cloud_api_url}/shared_commands/{command_id}/rate'
        payload = {
            'user_username': user_username,
            'rating': rating,
            'comment': comment
        }

        try:
            response = self.session.post(url, json=payload, timeout=30)
            response.raise_for_status()
            logger.info(f"Rated command {command_id}: {rating}/5 by {user_username}")
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to rate command {command_id}: {e}")
            raise

    def get_featured_commands(self, limit: int = 10) -> Dict[str, Any]:
        """取得精選指令

        Args:
            limit: 筆數

        Returns:
            Dict[str, Any]: API 回應（包含精選指令列表）

        Raises:
            requests.HTTPError: API 請求失敗
        """
        url = f'{self.cloud_api_url}/shared_commands/featured'
        params = {'limit': limit}

        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            logger.info(f"Retrieved {limit} featured commands from cloud")
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to get featured commands: {e}")
            raise

    def get_popular_commands(self, limit: int = 10) -> Dict[str, Any]:
        """取得熱門指令

        Args:
            limit: 筆數

        Returns:
            Dict[str, Any]: API 回應（包含熱門指令列表）

        Raises:
            requests.HTTPError: API 請求失敗
        """
        url = f'{self.cloud_api_url}/shared_commands/popular'
        params = {'limit': limit}

        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            logger.info(f"Retrieved {limit} popular commands from cloud")
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to get popular commands: {e}")
            raise

    def get_categories(self) -> Dict[str, Any]:
        """取得所有分類

        Returns:
            Dict[str, Any]: API 回應（包含分類列表）

        Raises:
            requests.HTTPError: API 請求失敗
        """
        url = f'{self.cloud_api_url}/shared_commands/categories'

        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            logger.info("Retrieved categories from cloud")
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Failed to get categories: {e}")
            raise

    def health_check(self) -> bool:
        """檢查雲端服務健康狀態

        Returns:
            bool: 服務是否可用

        """
        try:
            response = self.session.get(
                f'{self.cloud_api_url}/shared_commands/categories',
                timeout=5
            )
            response.raise_for_status()
            return True
        except requests.RequestException:
            return False
