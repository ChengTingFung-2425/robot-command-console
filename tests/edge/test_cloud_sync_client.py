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
