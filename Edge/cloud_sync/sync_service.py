# imports
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from Edge.cloud_sync.client import CloudSyncClient

logger = logging.getLogger(__name__)


class CloudSyncService:
    """雲端同步服務

    提供本地進階指令與雲端服務的雙向同步功能。
    """

    def __init__(
        self,
        cloud_api_url: str,
        edge_id: str,
        api_key: Optional[str] = None,
        auto_sync: bool = False
    ):
        """初始化同步服務

        Args:
            cloud_api_url: 雲端 API 基礎 URL
            edge_id: Edge 裝置 ID
            api_key: API 金鑰
            auto_sync: 是否自動同步
        """
        self.client = CloudSyncClient(cloud_api_url, edge_id, api_key)
        self.auto_sync = auto_sync
        self.edge_id = edge_id

    def sync_approved_commands(self, db_session) -> Dict[str, Any]:
        """同步已批准的進階指令到雲端

        Args:
            db_session: 資料庫 session（需包含 AdvancedCommand 模型）

        Returns:
            Dict[str, Any]: 同步結果統計
        """
        try:
            # 動態導入以避免循環依賴
            from Edge.WebUI.app.models import AdvancedCommand, User

            # 查詢所有已批准的指令
            commands = db_session.query(AdvancedCommand).filter_by(
                status='approved'
            ).all()

            results = {
                'total': len(commands),
                'uploaded': 0,
                'updated': 0,
                'failed': 0,
                'errors': []
            }

            for cmd in commands:
                try:
                    # 取得作者資訊
                    author = db_session.query(User).get(cmd.author_id)
                    if not author:
                        logger.warning(f"Author not found for command {cmd.id}")
                        continue

                    # 上傳指令
                    response = self.client.upload_command(
                        name=cmd.name,
                        description=cmd.description or '',
                        category=cmd.category or 'uncategorized',
                        content=cmd.base_commands,
                        author_username=author.username,
                        author_email=author.email,
                        original_command_id=cmd.id,
                        version=cmd.version
                    )

                    if response.get('success'):
                        results['uploaded'] += 1
                        logger.info(f"Synced command '{cmd.name}' to cloud")
                    else:
                        results['failed'] += 1
                        logger.warning(f"Failed to sync command '{cmd.name}'")

                except Exception as e:
                    results['failed'] += 1
                    results['errors'].append({
                        'command_id': cmd.id,
                        'command_name': cmd.name,
                        'error': str(e)
                    })
                    logger.error(f"Error syncing command '{cmd.name}': {e}")

            logger.info(
                f"Sync completed: {results['uploaded']} uploaded, "
                f"{results['failed']} failed"
            )
            return results

        except Exception as e:
            logger.error(f"Sync approved commands failed: {e}", exc_info=True)
            return {
                'total': 0,
                'uploaded': 0,
                'updated': 0,
                'failed': 0,
                'errors': [{'error': str(e)}]
            }

    def download_and_import_command(
        self,
        command_id: int,
        db_session,
        user_id: int
    ) -> Optional[Any]:
        """從雲端下載並導入指令到本地

        Args:
            command_id: 雲端指令 ID
            db_session: 資料庫 session
            user_id: 導入用戶 ID

        Returns:
            Optional[Any]: 建立的本地指令物件，失敗則返回 None
        """
        try:
            # 動態導入以避免循環依賴
            from Edge.WebUI.app.models import AdvancedCommand

            # 下載指令
            response = self.client.download_command(command_id)

            if not response.get('success'):
                logger.error(f"Failed to download command {command_id}")
                return None

            data = response.get('data', {})

            # 檢查是否已存在
            existing = db_session.query(AdvancedCommand).filter_by(
                name=data['name']
            ).first()

            if existing:
                logger.info(f"Command '{data['name']}' already exists locally")
                return existing

            # 建立本地指令
            local_cmd = AdvancedCommand(
                name=data['name'],
                description=data['description'],
                category=data['category'],
                base_commands=data['content'],
                version=data['version'],
                author_id=user_id,
                status='approved'  # 從雲端下載的指令預設為已批准
            )

            db_session.add(local_cmd)
            db_session.commit()

            logger.info(
                f"Imported command '{data['name']}' from cloud "
                f"(cloud_id={command_id}, local_id={local_cmd.id})"
            )
            return local_cmd

        except Exception as e:
            logger.error(f"Failed to import command {command_id}: {e}", exc_info=True)
            db_session.rollback()
            return None

    def browse_cloud_commands(
        self,
        category: Optional[str] = None,
        query: Optional[str] = None,
        min_rating: float = 4.0,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """瀏覽雲端共享指令

        Args:
            category: 分類篩選
            query: 搜尋關鍵字
            min_rating: 最低評分
            limit: 筆數

        Returns:
            List[Dict[str, Any]]: 指令列表
        """
        try:
            response = self.client.search_commands(
                query=query,
                category=category,
                min_rating=min_rating,
                sort_by='rating',
                order='desc',
                limit=limit
            )

            if response.get('success'):
                commands = response.get('data', {}).get('commands', [])
                logger.info(f"Retrieved {len(commands)} commands from cloud")
                return commands
            else:
                logger.error("Failed to browse cloud commands")
                return []

        except Exception as e:
            logger.error(f"Error browsing cloud commands: {e}")
            return []

    def get_cloud_status(self) -> Dict[str, Any]:
        """取得雲端服務狀態

        Returns:
            Dict[str, Any]: 狀態資訊
        """
        is_available = self.client.health_check()

        status = {
            'available': is_available,
            'edge_id': self.edge_id,
            'auto_sync': self.auto_sync,
            'last_check': datetime.utcnow().isoformat()
        }

        if is_available:
            try:
                categories_response = self.client.get_categories()
                if categories_response.get('success'):
                    status['categories'] = categories_response.get('data', {}).get('categories', [])

                featured_response = self.client.get_featured_commands(limit=5)
                if featured_response.get('success'):
                    status['featured_count'] = len(
                        featured_response.get('data', {}).get('commands', [])
                    )
            except Exception as e:
                logger.warning(f"Failed to get cloud status details: {e}")

        return status
