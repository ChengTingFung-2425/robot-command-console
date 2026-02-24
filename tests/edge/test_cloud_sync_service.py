"""
Edge CloudSyncService 單元測試
"""
import unittest
from unittest.mock import Mock, patch
import sys

# Mock WebUI models before importing CloudSyncService
webui_mock = Mock()
webui_app_mock = Mock()
webui_models_mock = Mock()
webui_app_mock.models = webui_models_mock
webui_mock.app = webui_app_mock
sys.modules['WebUI'] = webui_mock
sys.modules['WebUI.app'] = webui_app_mock
sys.modules['WebUI.app.models'] = webui_models_mock

from Edge.cloud_sync.sync_service import CloudSyncService  # noqa: E402


class TestCloudSyncService(unittest.TestCase):
    """測試 CloudSyncService 類別"""

    def setUp(self):
        """測試前準備"""
        self.cloud_api_url = "https://test.example.com/api"
        self.edge_id = "edge-test-001"
        self.api_key = "test-api-key"

    @patch('Edge.cloud_sync.sync_service.CloudSyncClient')
    @patch('Edge.cloud_sync.sync_service.get_sync_cache_dir')
    def test_init_with_fhs_paths(self, mock_get_cache, mock_client_class):
        """測試初始化時設定 FHS 快取目錄，且同步佇列應使用落盤 SQLite"""
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_cache_dir = Path(tmpdir)
            mock_get_cache.return_value = mock_cache_dir

            with patch('Edge.cloud_sync.sync_service.FHS_PATHS_AVAILABLE', True):
                service = CloudSyncService(
                    cloud_api_url=self.cloud_api_url,
                    edge_id=self.edge_id,
                    api_key=self.api_key
                )

                assert service.cache_dir == mock_cache_dir
                assert service.edge_id == self.edge_id
                mock_get_cache.assert_called_once()
                # 確認佇列 DB 落到 cache_dir/sync_queue.db
                expected_db = str(mock_cache_dir / "sync_queue.db")
                assert service._sync_queue._db_path == expected_db
                service.close()

    @patch('Edge.cloud_sync.sync_service.CloudSyncClient')
    def test_init_without_fhs_paths(self, mock_client_class):
        """測試 FHS paths 不可用時的初始化"""
        with patch('Edge.cloud_sync.sync_service.FHS_PATHS_AVAILABLE', False):
            service = CloudSyncService(
                cloud_api_url=self.cloud_api_url,
                edge_id=self.edge_id
            )

            assert service.cache_dir is None

    @patch('Edge.cloud_sync.sync_service.CloudSyncClient')
    def test_sync_approved_commands_success(self, mock_client_class):
        """測試同步已批准指令 - 成功案例"""
        # Mock client
        mock_client = Mock()
        mock_client.upload_command.return_value = {'success': True, 'data': {'id': 123}}
        mock_client_class.return_value = mock_client

        # Mock database session and models
        mock_db = Mock()
        mock_user = Mock()
        mock_user.username = "testuser"
        mock_user.email = "test@example.com"

        mock_cmd1 = Mock()
        mock_cmd1.id = 1
        mock_cmd1.name = "Test Command 1"
        mock_cmd1.description = "Description 1"
        mock_cmd1.category = "navigation"
        mock_cmd1.base_commands = '["move", "forward"]'
        mock_cmd1.version = 1
        mock_cmd1.author_id = 1
        mock_cmd1.author = mock_user

        mock_db.query.return_value.filter_by.return_value.all.return_value = [mock_cmd1]
        mock_db.query.return_value.get.return_value = mock_user

        service = CloudSyncService(
            cloud_api_url=self.cloud_api_url,
            edge_id=self.edge_id,
            api_key=self.api_key
        )

        with patch('Edge.cloud_sync.sync_service.FHS_PATHS_AVAILABLE', False):
            results = service.sync_approved_commands(mock_db)

        assert results['total'] == 1
        assert results['uploaded'] == 1
        assert results['failed'] == 0
        mock_client.upload_command.assert_called_once()

    @patch('Edge.cloud_sync.sync_service.CloudSyncClient')
    def test_sync_approved_commands_author_not_found(self, mock_client_class):
        """測試同步指令時作者不存在的情況"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Mock database - command exists but author doesn't
        mock_db = Mock()
        mock_cmd = Mock()
        mock_cmd.id = 1
        mock_cmd.name = "Test Command"
        mock_cmd.author_id = 999
        mock_cmd.author = None

        mock_db.query.return_value.filter_by.return_value.all.return_value = [mock_cmd]
        mock_db.query.return_value.get.return_value = None  # Author not found

        service = CloudSyncService(
            cloud_api_url=self.cloud_api_url,
            edge_id=self.edge_id
        )

        results = service.sync_approved_commands(mock_db)

        # Should count as failed
        assert results['total'] == 1
        assert results['uploaded'] == 0
        assert results['failed'] == 1
        assert len(results['errors']) == 1
        assert results['errors'][0]['error'] == 'Author not found'

    @patch('Edge.cloud_sync.sync_service.CloudSyncClient')
    def test_download_and_import_command_success(self, mock_client_class):
        """測試下載並導入指令 - 成功案例"""
        # Mock client
        mock_client = Mock()
        mock_client.download_command.return_value = {
            'success': True,
            'data': {
                'name': 'Cloud Command',
                'description': 'From cloud',
                'category': 'patrol',
                'content': '["patrol", "start"]',
                'version': 1,
                'author_username': 'clouduser'
            }
        }
        mock_client_class.return_value = mock_client

        # Mock database
        mock_db = Mock()
        mock_db.query.return_value.filter_by.return_value.first.return_value = None  # No existing

        # Mock AdvancedCommand model
        mock_advanced_command = Mock()
        mock_cmd_instance = Mock()
        mock_cmd_instance.id = 1
        mock_cmd_instance.name = 'Cloud Command'
        mock_advanced_command.return_value = mock_cmd_instance

        service = CloudSyncService(
            cloud_api_url=self.cloud_api_url,
            edge_id=self.edge_id
        )

        # Mock WebUI models
        import sys
        webui_mock = Mock()
        webui_app_mock = Mock()
        webui_models_mock = Mock()
        webui_models_mock.AdvancedCommand = mock_advanced_command
        webui_models_mock.User = Mock()
        webui_app_mock.models = webui_models_mock
        webui_mock.app = webui_app_mock
        sys.modules['WebUI'] = webui_mock
        sys.modules['WebUI.app'] = webui_app_mock
        sys.modules['WebUI.app.models'] = webui_models_mock

        with patch('Edge.cloud_sync.sync_service.FHS_PATHS_AVAILABLE', False):
            result = service.download_and_import_command(123, mock_db, 1)

        # Verify client was called and command was created
        mock_client.download_command.assert_called_once_with(123)
        assert result == mock_cmd_instance

    @patch('Edge.cloud_sync.sync_service.CloudSyncClient')
    def test_download_and_import_command_missing_field(self, mock_client_class):
        """測試下載指令時缺少必要欄位"""
        # Mock client with incomplete data
        mock_client = Mock()
        mock_client.download_command.return_value = {
            'success': True,
            'data': {
                'name': 'Incomplete Command',
                # Missing: description, category, content, version
            }
        }
        mock_client_class.return_value = mock_client

        mock_db = Mock()

        service = CloudSyncService(
            cloud_api_url=self.cloud_api_url,
            edge_id=self.edge_id
        )

        with patch('Edge.cloud_sync.sync_service.FHS_PATHS_AVAILABLE', False):
            result = service.download_and_import_command(123, mock_db, 1)

        # Should return None due to missing fields
        assert result is None

    @patch('Edge.cloud_sync.sync_service.CloudSyncClient')
    def test_browse_cloud_commands(self, mock_client_class):
        """測試瀏覽雲端指令"""
        mock_client = Mock()
        mock_client.search_commands.return_value = {
            'success': True,
            'data': {
                'commands': [
                    {'id': 1, 'name': 'Command 1'},
                    {'id': 2, 'name': 'Command 2'}
                ],
                'total': 2
            }
        }
        mock_client_class.return_value = mock_client

        service = CloudSyncService(
            cloud_api_url=self.cloud_api_url,
            edge_id=self.edge_id
        )

        commands = service.browse_cloud_commands(
            category='patrol',
            min_rating=4.0,
            limit=10
        )

        assert len(commands) == 2
        assert commands[0]['name'] == 'Command 1'
        mock_client.search_commands.assert_called_once_with(
            query=None,
            category='patrol',
            min_rating=4.0,
            sort_by='rating',
            order='desc',
            limit=10
        )

    @patch('Edge.cloud_sync.sync_service.CloudSyncClient')
    def test_browse_cloud_commands_failure(self, mock_client_class):
        """測試瀏覽雲端指令失敗"""
        mock_client = Mock()
        mock_client.search_commands.return_value = {'success': False}
        mock_client_class.return_value = mock_client

        service = CloudSyncService(
            cloud_api_url=self.cloud_api_url,
            edge_id=self.edge_id
        )

        commands = service.browse_cloud_commands()

        assert commands == []

    @patch('Edge.cloud_sync.sync_service.CloudSyncClient')
    def test_get_cloud_status(self, mock_client_class):
        """測試取得雲端服務狀態"""
        mock_client = Mock()
        mock_client.health_check.return_value = True
        mock_client.get_categories.return_value = {
            'success': True,
            'data': {
                'categories': ['navigation', 'patrol', 'inspection']
            }
        }
        mock_client.get_featured_commands.return_value = {
            'success': True,
            'data': {
                'commands': [{'id': 1, 'name': 'Featured'}]
            }
        }
        mock_client_class.return_value = mock_client

        service = CloudSyncService(
            cloud_api_url=self.cloud_api_url,
            edge_id=self.edge_id
        )

        status = service.get_cloud_status()

        assert status['available'] is True
        assert status['edge_id'] == self.edge_id
        assert 'categories' in status
        assert len(status['categories']) == 3

    @patch('Edge.cloud_sync.sync_service.CloudSyncClient')
    def test_cache_sync_result(self, mock_client_class):
        """測試快取同步結果"""
        from pathlib import Path
        import tempfile
        import json

        mock_client_class.return_value = Mock()

        # Use a temporary directory for testing
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir)

            service = CloudSyncService(
                cloud_api_url=self.cloud_api_url,
                edge_id=self.edge_id
            )
            service.cache_dir = cache_dir

            results = {
                'total': 5,
                'uploaded': 4,
                'failed': 1,
                'errors': []
            }

            service._cache_sync_result(results)

            # Verify cache file was created
            cache_files = list(cache_dir.glob(f"sync_result_{self.edge_id}_*.json"))
            assert len(cache_files) == 1

            # Verify content
            with open(cache_files[0], 'r') as f:
                cached_data = json.load(f)

            assert cached_data['edge_id'] == self.edge_id
            assert cached_data['results']['total'] == 5

    @patch('Edge.cloud_sync.sync_service.CloudSyncClient')
    def test_cleanup_cache(self, mock_client_class):
        """測試清理舊快取檔案"""
        from pathlib import Path
        import tempfile
        import time

        mock_client_class.return_value = Mock()

        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir)

            service = CloudSyncService(
                cloud_api_url=self.cloud_api_url,
                edge_id=self.edge_id
            )
            service.cache_dir = cache_dir

            # Create 15 test cache files
            for i in range(15):
                cache_file = cache_dir / f"sync_result_{self.edge_id}_{i:04d}.json"
                cache_file.write_text('{}')
                time.sleep(0.01)  # Ensure different mtime

            # Cleanup should keep only 10 most recent
            service._cleanup_cache(max_files=10)

            remaining_files = list(cache_dir.glob(f"sync_result_{self.edge_id}_*.json"))
            assert len(remaining_files) == 10

            # Verify oldest files were removed (0000-0004)
            remaining_names = [f.name for f in remaining_files]
            assert f"sync_result_{self.edge_id}_0000.json" not in remaining_names
            assert f"sync_result_{self.edge_id}_0014.json" in remaining_names

    @patch('Edge.cloud_sync.sync_service.CloudSyncClient')
    def test_sync_user_settings_success(self, mock_client_class):
        """測試同步用戶設定 - 成功案例"""
        mock_client = Mock()
        mock_client.upload_user_settings.return_value = {
            'success': True,
            'message': 'Settings synced',
            'updated_at': '2026-01-01T00:00:00Z'
        }
        mock_client_class.return_value = mock_client

        service = CloudSyncService(
            cloud_api_url=self.cloud_api_url,
            edge_id=self.edge_id
        )

        result = service.sync_user_settings(
            user_id='user-123',
            settings={'theme': 'dark', 'language': 'zh-TW'}
        )

        assert result['success'] is True
        mock_client.upload_user_settings.assert_called_once_with(
            user_id='user-123',
            settings={'theme': 'dark', 'language': 'zh-TW'},
            edge_id=self.edge_id
        )

    @patch('Edge.cloud_sync.sync_service.CloudSyncClient')
    def test_sync_user_settings_failure(self, mock_client_class):
        """測試同步用戶設定 - API 異常時自動快取到本地佇列"""
        import requests as req
        mock_client = Mock()
        mock_client.upload_user_settings.side_effect = req.RequestException("Connection failed")
        mock_client_class.return_value = mock_client

        service = CloudSyncService(
            cloud_api_url=self.cloud_api_url,
            edge_id=self.edge_id
        )

        result = service.sync_user_settings(
            user_id='user-123',
            settings={'theme': 'dark'}
        )

        assert result['success'] is False
        # 雲端不可用時應自動快取（queued=True）
        assert result.get('queued') is True
        assert 'op_id' in result

    @patch('Edge.cloud_sync.sync_service.CloudSyncClient')
    def test_restore_user_settings_success(self, mock_client_class):
        """測試從雲端還原用戶設定 - 成功案例"""
        mock_client = Mock()
        mock_client.download_user_settings.return_value = {
            'success': True,
            'data': {
                'user_id': 'user-123',
                'settings': {'theme': 'dark', 'language': 'zh-TW'},
                'updated_at': '2026-01-01T00:00:00Z'
            }
        }
        mock_client_class.return_value = mock_client

        service = CloudSyncService(
            cloud_api_url=self.cloud_api_url,
            edge_id=self.edge_id
        )

        settings = service.restore_user_settings(user_id='user-123')

        assert settings is not None
        assert settings['theme'] == 'dark'
        assert settings['language'] == 'zh-TW'
        mock_client.download_user_settings.assert_called_once_with(user_id='user-123')

    @patch('Edge.cloud_sync.sync_service.CloudSyncClient')
    def test_restore_user_settings_not_found(self, mock_client_class):
        """測試從雲端還原用戶設定 - 設定不存在"""
        mock_client = Mock()
        mock_client.download_user_settings.return_value = {
            'success': False,
            'error': 'Settings not found'
        }
        mock_client_class.return_value = mock_client

        service = CloudSyncService(
            cloud_api_url=self.cloud_api_url,
            edge_id=self.edge_id
        )

        settings = service.restore_user_settings(user_id='new-user')

        assert settings is None

    @patch('Edge.cloud_sync.sync_service.CloudSyncClient')
    def test_sync_command_history_success(self, mock_client_class):
        """測試同步指令歷史 - 成功案例"""
        mock_client = Mock()
        mock_client.upload_command_history.return_value = {
            'success': True,
            'synced_count': 3,
            'total': 10
        }
        mock_client_class.return_value = mock_client

        service = CloudSyncService(
            cloud_api_url=self.cloud_api_url,
            edge_id=self.edge_id
        )

        records = [
            {'command_id': 'cmd-001', 'status': 'succeeded'},
            {'command_id': 'cmd-002', 'status': 'failed'},
            {'command_id': 'cmd-003', 'status': 'succeeded'},
        ]
        result = service.sync_command_history(user_id='user-123', records=records)

        assert result['success'] is True
        assert result['synced_count'] == 3
        mock_client.upload_command_history.assert_called_once_with(
            user_id='user-123',
            records=records,
            edge_id=self.edge_id
        )

    @patch('Edge.cloud_sync.sync_service.CloudSyncClient')
    def test_sync_command_history_empty(self, mock_client_class):
        """測試同步空的指令歷史"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        service = CloudSyncService(
            cloud_api_url=self.cloud_api_url,
            edge_id=self.edge_id
        )

        result = service.sync_command_history(user_id='user-123', records=[])

        assert result['success'] is True
        assert result['synced_count'] == 0
        mock_client.upload_command_history.assert_not_called()

    @patch('Edge.cloud_sync.sync_service.CloudSyncClient')
    def test_sync_command_history_failure(self, mock_client_class):
        """測試同步指令歷史 - API 異常時自動快取到本地佇列"""
        import requests as req
        mock_client = Mock()
        mock_client.upload_command_history.side_effect = req.RequestException("Timeout")
        mock_client_class.return_value = mock_client

        service = CloudSyncService(
            cloud_api_url=self.cloud_api_url,
            edge_id=self.edge_id
        )

        result = service.sync_command_history(
            user_id='user-123',
            records=[{'command_id': 'cmd-001'}]
        )

        assert result['success'] is False
        # 雲端不可用時應自動快取（queued=True）
        assert result.get('queued') is True
        assert 'op_id' in result

    @patch('Edge.cloud_sync.sync_service.CloudSyncClient')
    def test_flush_queue_sends_cached_items(self, mock_client_class):
        """測試 flush_queue 補發快取的失敗操作"""
        import requests as req
        mock_client = Mock()
        # 第一次呼叫失敗，第二次成功（模擬先斷線後恢復）
        mock_client.upload_user_settings.side_effect = [
            req.RequestException("Connection failed"),
            {'success': True, 'updated_at': '2026-01-01T00:00:00Z'}
        ]
        mock_client_class.return_value = mock_client

        service = CloudSyncService(
            cloud_api_url=self.cloud_api_url,
            edge_id=self.edge_id
        )

        # 第一次同步失敗 → 自動快取
        result = service.sync_user_settings(
            user_id='user-123',
            settings={'theme': 'dark'}
        )
        assert result.get('queued') is True

        # 標記雲端恢復並補發
        service.set_cloud_available(True)
        flush_result = service.flush_queue()
        assert flush_result['sent'] == 1
        assert flush_result['remaining'] == 0
        mock_client.upload_user_settings.assert_called()

    @patch('Edge.cloud_sync.sync_service.CloudSyncClient')
    def test_get_queue_statistics(self, mock_client_class):
        """測試 get_queue_statistics 返回正確統計"""
        mock_client_class.return_value = Mock()

        service = CloudSyncService(
            cloud_api_url=self.cloud_api_url,
            edge_id=self.edge_id
        )

        stats = service.get_queue_statistics()
        assert 'pending' in stats
        assert 'total_enqueued' in stats
        assert 'is_online' in stats

    @patch('Edge.cloud_sync.sync_service.CloudSyncClient')
    def test_get_cloud_status_includes_queue_stats(self, mock_client_class):
        """測試 get_cloud_status 包含同步佇列統計"""
        mock_client = Mock()
        mock_client.health_check.return_value = False
        mock_client_class.return_value = mock_client

        service = CloudSyncService(
            cloud_api_url=self.cloud_api_url,
            edge_id=self.edge_id
        )

        status = service.get_cloud_status()
        assert 'sync_queue' in status
        assert 'pending' in status['sync_queue']


if __name__ == '__main__':
    unittest.main()
