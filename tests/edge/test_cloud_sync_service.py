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
        """測試初始化時設定 FHS 快取目錄"""
        from pathlib import Path
        mock_cache_dir = Path("/tmp/test-cache")
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


if __name__ == '__main__':
    unittest.main()
