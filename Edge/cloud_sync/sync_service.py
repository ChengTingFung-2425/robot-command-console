# imports
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import json

from Edge.cloud_sync.client import CloudSyncClient
from Edge.cloud_sync.sync_queue import CloudSyncQueue

# 嘗試導入 FHS 路徑管理
try:
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
    from src.common.fhs_paths import get_sync_cache_dir, get_sync_log_path
    FHS_PATHS_AVAILABLE = True
except ImportError:
    FHS_PATHS_AVAILABLE = False
    get_sync_cache_dir = None
    get_sync_log_path = None

logger = logging.getLogger(__name__)


class CloudSyncService:
    """雲端同步服務

    提供本地進階指令與雲端服務的雙向同步功能。

    雲端同步採用「先後發送機制＋本地快取」設計：
    - 寫入操作（user_settings、command_history）若雲端不可用，
      自動快取到本地 SQLite 佇列，確保資料不遺失。
    - 佇列以 FIFO 序號排序，flush_queue() 時按原始入隊順序依序發送。
    - 呼叫 set_cloud_available(True) 後可手動或定期呼叫 flush_queue()
      將快取資料補發到雲端。
    """

    def __init__(
        self,
        cloud_api_url: str,
        edge_id: str,
        api_key: Optional[str] = None,
        jwt_token: Optional[str] = None,
        auto_sync: bool = False,
        queue_db_path: Optional[str] = None,
    ):
        """初始化同步服務

        Args:
            cloud_api_url: 雲端 API 基礎 URL
            edge_id: Edge 裝置 ID
            api_key: API 金鑰（已棄用，請使用 jwt_token）
            jwt_token: JWT token（推薦使用）
            auto_sync: 是否自動同步
            queue_db_path: 同步佇列 SQLite 路徑；None 使用記憶體資料庫
        """
        self.client = CloudSyncClient(cloud_api_url, edge_id, api_key=api_key, jwt_token=jwt_token)
        self.auto_sync = auto_sync
        self.edge_id = edge_id

        # 初始化先後發送佇列（本地快取）
        self._sync_queue = CloudSyncQueue(db_path=queue_db_path)

        # 初始化 FHS 標準路徑
        if FHS_PATHS_AVAILABLE and get_sync_cache_dir:
            try:
                self.cache_dir = get_sync_cache_dir()
                logger.info(f"Sync cache directory: {self.cache_dir}")
            except Exception as e:
                logger.warning(f"Failed to initialize FHS cache dir: {e}")
                self.cache_dir = None
        else:
            self.cache_dir = None
            logger.debug("FHS paths not available, cache disabled")

    def sync_approved_commands(self, db_session) -> Dict[str, Any]:
        """同步已批准的進階指令到雲端

        Args:
            db_session: 資料庫 session（需包含 AdvancedCommand 模型）

        Returns:
            Dict[str, Any]: 同步結果統計
        """
        try:
            # 動態導入以避免循環依賴
            from WebUI.app.models import AdvancedCommand, User

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
                        results['failed'] += 1
                        results['errors'].append({
                            'command_id': cmd.id,
                            'command_name': cmd.name,
                            'error': 'Author not found'
                        })
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

            # 儲存同步結果到 FHS 快取
            self._cache_sync_result(results)

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
            from WebUI.app.models import AdvancedCommand

            # 下載指令
            response = self.client.download_command(command_id)

            if not response.get('success'):
                logger.error(f"Failed to download command {command_id}")
                return None

            data = response.get('data', {})

            # 驗證必要欄位
            required_fields = ['name', 'description', 'category', 'content', 'version']
            for field in required_fields:
                if field not in data:
                    logger.error(f"Missing required field '{field}' in downloaded command {command_id}")
                    return None

            # 檢查是否已存在
            existing = db_session.query(AdvancedCommand).filter_by(
                name=data['name']
            ).first()

            if existing:
                logger.info(f"Command '{data['name']}' already exists locally")
                return existing

            # 建立本地指令
            # 從雲端下載的指令需要本地審核，預設為 pending 狀態
            # 在 description 中記錄原始作者資訊以保持追蹤
            original_author_note = f"\n\n[從雲端下載 - 原始作者: {data.get('author_username', 'unknown')}]"
            description_with_source = (data['description'] or '') + original_author_note

            local_cmd = AdvancedCommand(
                name=data['name'],
                description=description_with_source,
                category=data['category'],
                base_commands=data['content'],
                version=data['version'],
                author_id=user_id,
                status='pending'  # 從雲端下載的指令需經過本地審核
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

    def _cache_sync_result(self, results: Dict[str, Any]) -> None:
        """將同步結果儲存到 FHS 快取目錄

        Args:
            results: 同步結果統計
        """
        if not self.cache_dir:
            return

        try:
            timestamp_str = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
            cache_file = self.cache_dir / f"sync_result_{self.edge_id}_{timestamp_str}.json"
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'edge_id': self.edge_id,
                    'results': results
                }, f, indent=2)
            logger.debug(f"Cached sync results to: {cache_file}")

            # 清理舊的快取檔案（保留最近 10 個）
            self._cleanup_cache(max_files=10)
        except Exception as e:
            logger.warning(f"Failed to cache sync results: {e}")

    def _cleanup_cache(self, max_files: int = 10) -> None:
        """清理舊的快取檔案

        Args:
            max_files: 保留的最大檔案數
        """
        if not self.cache_dir:
            return

        try:
            cache_files = sorted(
                self.cache_dir.glob(f"sync_result_{self.edge_id}_*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )

            # 刪除超過限制的舊檔案
            for old_file in cache_files[max_files:]:
                old_file.unlink()
                logger.debug(f"Removed old cache file: {old_file}")
        except Exception as e:
            logger.warning(f"Failed to cleanup cache: {e}")

    # ==================== 先後發送佇列 ====================

    def set_cloud_available(self, is_available: bool) -> None:
        """設定雲端可用狀態（更新同步佇列的在線標記）

        Args:
            is_available: 雲端是否可用
        """
        self._sync_queue.set_online(is_available)

    def flush_queue(self) -> Dict[str, Any]:
        """清空同步佇列：按先後順序補發所有快取的同步操作

        呼叫時機：
        - 網路恢復後
        - 定期排程（例如每 5 分鐘）
        - 應用程式啟動時

        Returns:
            Dict[str, Any]: 結果統計 {sent, failed, remaining}
        """
        return self._sync_queue.flush(self._dispatch_queued_item)

    def get_queue_statistics(self) -> Dict[str, Any]:
        """取得同步佇列統計資訊

        Returns:
            Dict[str, Any]: 統計資訊（pending、failed、total_sent 等）
        """
        return self._sync_queue.get_statistics()

    def _dispatch_queued_item(self, op_type: str, payload: Dict[str, Any]) -> bool:
        """將佇列中的項目實際發送到雲端

        由 flush_queue() 的 send_handler 回呼此方法。

        Args:
            op_type: 操作類型
            payload: 操作資料

        Returns:
            是否成功
        """
        try:
            if op_type == 'user_settings':
                response = self.client.upload_user_settings(
                    user_id=payload['user_id'],
                    settings=payload['settings'],
                    edge_id=payload.get('edge_id', self.edge_id),
                )
                return bool(response.get('success'))

            if op_type == 'command_history':
                response = self.client.upload_command_history(
                    user_id=payload['user_id'],
                    records=payload['records'],
                    edge_id=payload.get('edge_id', self.edge_id),
                )
                return bool(response.get('success'))

            logger.warning("Unknown op_type in sync queue", extra={
                "op_type": op_type,
                "service": "cloud_sync_service",
            })
            return False
        except Exception as e:
            logger.error("Failed to dispatch queued sync item", extra={
                "op_type": op_type,
                "error": str(e),
                "service": "cloud_sync_service",
            })
            return False

    # ==================== 用戶設定同步 ====================

    def sync_user_settings(
        self,
        user_id: str,
        settings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """將本地用戶設定同步（備份）到雲端

        Edge 為主要來源，雲端為備份。當用戶更新設定後呼叫此方法
        將最新設定上傳到雲端，供日後還原或在新裝置上使用。

        雲端不可用時自動快取到本地 SQLite 佇列（先後發送機制），
        呼叫 flush_queue() 後按入隊順序補發。

        Args:
            user_id: 用戶 ID
            settings: 用戶設定字典（例如語言、主題、通知偏好等）

        Returns:
            Dict[str, Any]: 同步結果
                - success: 是否成功
                - queued: True 表示已快取到佇列（離線時）
                - updated_at: 更新時間（成功時）
                - error: 錯誤訊息（失敗時）
        """
        try:
            response = self.client.upload_user_settings(
                user_id=user_id,
                settings=settings,
                edge_id=self.edge_id
            )
            if response.get('success'):
                logger.info(f"User settings synced to cloud for user '{user_id}'")
            else:
                logger.warning(f"Failed to sync settings for user '{user_id}'")
            return response
        except Exception as e:
            logger.warning(
                f"Cloud unavailable, queuing user settings for '{user_id}': {e}"
            )
            op_id = self._sync_queue.enqueue(
                op_type='user_settings',
                payload={
                    'user_id': user_id,
                    'settings': settings,
                    'edge_id': self.edge_id,
                },
            )
            if op_id:
                return {'success': False, 'queued': True, 'op_id': op_id}
            return {'success': False, 'queued': False, 'error': 'Queue full'}

    def restore_user_settings(self, user_id: str) -> Optional[Dict[str, Any]]:
        """從雲端下載用戶設定（還原備份）

        從雲端備份還原用戶設定，適用於新裝置初始化或設定重置後的還原。

        Args:
            user_id: 用戶 ID

        Returns:
            Optional[Dict[str, Any]]: 用戶設定字典，若雲端無備份則返回 None
        """
        try:
            response = self.client.download_user_settings(user_id=user_id)
            if response.get('success'):
                data = response.get('data', {})
                settings = data.get('settings')
                logger.info(f"Restored settings from cloud for user '{user_id}'")
                return settings
            else:
                logger.warning(f"No cloud settings found for user '{user_id}'")
                return None
        except Exception as e:
            logger.error(f"Error restoring user settings for '{user_id}': {e}")
            return None

    # ==================== 指令歷史同步 ====================

    def sync_command_history(
        self,
        user_id: str,
        records: list
    ) -> Dict[str, Any]:
        """將指令執行歷史上傳到雲端

        將本地 CommandRecord 記錄批次上傳到雲端，用於分析、備份及跨裝置查詢。
        雲端會自動以 command_id 去重，避免重複記錄。

        雲端不可用時自動快取到本地 SQLite 佇列（先後發送機制），
        呼叫 flush_queue() 後按入隊順序補發。

        Args:
            user_id: 用戶 ID
            records: 指令歷史記錄列表，每筆為 dict 格式（CommandRecord.to_dict()）

        Returns:
            Dict[str, Any]: 同步結果
                - success: 是否成功
                - queued: True 表示已快取到佇列（離線時）
                - synced_count: 本次新增的記錄數（成功時）
                - total: 雲端總記錄數（成功時）
                - error: 錯誤訊息（失敗時）
        """
        if not records:
            return {'success': True, 'synced_count': 0, 'total': 0}

        try:
            response = self.client.upload_command_history(
                user_id=user_id,
                records=records,
                edge_id=self.edge_id
            )
            if response.get('success'):
                logger.info(
                    f"Command history synced for user '{user_id}': "
                    f"{response.get('synced_count', 0)} records added"
                )
            else:
                logger.warning(f"Failed to sync history for user '{user_id}'")
            return response
        except Exception as e:
            logger.warning(
                f"Cloud unavailable, queuing command history for '{user_id}': {e}"
            )
            op_id = self._sync_queue.enqueue(
                op_type='command_history',
                payload={
                    'user_id': user_id,
                    'records': records,
                    'edge_id': self.edge_id,
                },
            )
            if op_id:
                return {'success': False, 'queued': True, 'op_id': op_id}
            return {'success': False, 'queued': False, 'error': 'Queue full'}

    def get_cloud_status(self) -> Dict[str, Any]:
        """取得雲端服務狀態

        Returns:
            Dict[str, Any]: 狀態資訊（含同步佇列統計）
        """
        is_available = self.client.health_check()

        status = {
            'available': is_available,
            'edge_id': self.edge_id,
            'auto_sync': self.auto_sync,
            'last_check': datetime.now(timezone.utc).isoformat(),
            'sync_queue': self._sync_queue.get_statistics(),
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
