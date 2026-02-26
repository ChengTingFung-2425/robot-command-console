# imports
import pytest
from unittest.mock import Mock, patch
import requests

from Edge.cloud_sync.client import CloudSyncClient


class TestCloudSyncClient:
    """測試雲端同步客戶端"""

    @pytest.fixture
    def client(self):
        """建立客戶端實例"""
        return CloudSyncClient(
            cloud_api_url='https://cloud.example.com/api/cloud',
            edge_id='edge-001',
            api_key='test-api-key'
        )

    @patch('Edge.cloud_sync.client.requests.Session.post')
    def test_upload_command_success(self, mock_post, client):
        """測試上傳指令成功"""
        # Arrange
        mock_response = Mock()
        mock_response.json.return_value = {'success': True, 'data': {'id': 123}}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        # Act
        result = client.upload_command(
            name='test_cmd',
            description='Test',
            category='test',
            content='[{"command": "bow"}]',
            author_username='testuser',
            author_email='test@example.com',
            original_command_id=1,
            version=1
        )

        # Assert
        assert result['success'] is True
        mock_post.assert_called_once()

    @patch('Edge.cloud_sync.client.requests.Session.get')
    def test_search_commands_success(self, mock_get, client):
        """測試搜尋指令成功"""
        # Arrange
        mock_response = Mock()
        mock_response.json.return_value = {
            'success': True,
            'data': {'commands': [], 'total': 0}
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Act
        result = client.search_commands(query='test')

        # Assert
        assert result['success'] is True
        mock_get.assert_called_once()

    @patch('Edge.cloud_sync.client.requests.Session.get')
    def test_health_check_success(self, mock_get, client):
        """測試健康檢查成功"""
        # Arrange
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Act
        result = client.health_check()

        # Assert
        assert result is True

    @patch('Edge.cloud_sync.client.requests.Session.get')
    def test_health_check_failure(self, mock_get, client):
        """測試健康檢查失敗"""
        # Arrange
        mock_get.side_effect = requests.RequestException("Connection failed")

        # Act
        result = client.health_check()

        # Assert
        assert result is False

    @patch('Edge.cloud_sync.client.requests.Session.post')
    def test_upload_user_settings_success(self, mock_post, client):
        """測試上傳用戶設定 - 成功案例"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'success': True,
            'message': 'Settings synced',
            'updated_at': '2026-01-01T00:00:00Z'
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        result = client.upload_user_settings(
            user_id='user-123',
            settings={'theme': 'dark', 'language': 'zh-TW'},
            edge_id='edge-001'
        )

        assert result['success'] is True
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert 'settings/user-123' in call_args[0][0]

    @patch('Edge.cloud_sync.client.requests.Session.get')
    def test_download_user_settings_success(self, mock_get, client):
        """測試下載用戶設定 - 成功案例"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'success': True,
            'data': {
                'user_id': 'user-123',
                'settings': {'theme': 'dark'},
                'updated_at': '2026-01-01T00:00:00Z'
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = client.download_user_settings(user_id='user-123')

        assert result['success'] is True
        assert result['data']['settings']['theme'] == 'dark'
        mock_get.assert_called_once()

    @patch('Edge.cloud_sync.client.requests.Session.post')
    def test_upload_command_history_success(self, mock_post, client):
        """測試上傳指令歷史 - 成功案例"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'success': True,
            'synced_count': 2,
            'total': 5
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        records = [
            {'command_id': 'cmd-001', 'status': 'succeeded'},
            {'command_id': 'cmd-002', 'status': 'failed'},
        ]
        result = client.upload_command_history(
            user_id='user-123',
            records=records,
            edge_id='edge-001'
        )

        assert result['success'] is True
        assert result['synced_count'] == 2
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert 'history/user-123' in call_args[0][0]

    @patch('Edge.cloud_sync.client.requests.Session.get')
    def test_download_command_history_success(self, mock_get, client):
        """測試下載指令歷史 - 成功案例"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'success': True,
            'data': {
                'records': [{'command_id': 'cmd-001', 'status': 'succeeded'}],
                'total': 1
            }
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = client.download_command_history(user_id='user-123', limit=50, offset=0)

        assert result['success'] is True
        assert result['data']['total'] == 1
        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args[1]
        assert call_kwargs['params'] == {'limit': 50, 'offset': 0}
