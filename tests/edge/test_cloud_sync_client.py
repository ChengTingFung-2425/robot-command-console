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

    # ==================== 各方法失敗案例（異常處理）====================

    @patch('Edge.cloud_sync.client.requests.Session.post')
    def test_upload_command_raises_on_error(self, mock_post, client):
        """upload_command 遇到網路錯誤應拋出 RequestException"""
        mock_post.side_effect = requests.RequestException("Connection refused")

        with pytest.raises(requests.RequestException):
            client.upload_command(
                name='cmd', description='desc', category='test',
                content='[]', author_username='user', author_email='u@e.com',
                original_command_id=1, version=1
            )

    @patch('Edge.cloud_sync.client.requests.Session.get')
    def test_search_commands_raises_on_error(self, mock_get, client):
        """search_commands 遇到 HTTP 錯誤應拋出 RequestException"""
        mock_get.side_effect = requests.HTTPError("500 Server Error")

        with pytest.raises(requests.RequestException):
            client.search_commands(query='test')

    @patch('Edge.cloud_sync.client.requests.Session.get')
    def test_get_command_success(self, mock_get, client):
        """get_command 成功案例"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'success': True,
            'data': {'id': 42, 'name': 'Cloud Cmd', 'category': 'nav'}
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = client.get_command(42)

        assert result['success'] is True
        assert result['data']['id'] == 42
        mock_get.assert_called_once()
        assert '/shared_commands/42' in mock_get.call_args[0][0]

    @patch('Edge.cloud_sync.client.requests.Session.get')
    def test_get_command_raises_on_error(self, mock_get, client):
        """get_command 遇到 HTTP 錯誤應拋出 RequestException"""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
        mock_get.return_value = mock_response

        with pytest.raises(requests.RequestException):
            client.get_command(999)

    @patch('Edge.cloud_sync.client.requests.Session.post')
    def test_download_command_success(self, mock_post, client):
        """download_command 成功案例"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'success': True,
            'data': {
                'name': 'Cloud Cmd', 'description': 'desc',
                'category': 'nav', 'content': '[]', 'version': 1
            }
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        result = client.download_command(42)

        assert result['success'] is True
        mock_post.assert_called_once()
        call_url = mock_post.call_args[0][0]
        assert '/shared_commands/42/download' in call_url

    @patch('Edge.cloud_sync.client.requests.Session.post')
    def test_download_command_raises_on_error(self, mock_post, client):
        """download_command 遇到網路錯誤應拋出 RequestException"""
        mock_post.side_effect = requests.RequestException("Timeout")

        with pytest.raises(requests.RequestException):
            client.download_command(42)

    @patch('Edge.cloud_sync.client.requests.Session.post')
    def test_rate_command_success(self, mock_post, client):
        """rate_command 成功案例"""
        mock_response = Mock()
        mock_response.json.return_value = {'success': True, 'message': 'Rating saved'}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        result = client.rate_command(
            command_id=42, user_username='testuser', rating=5, comment='Great!'
        )

        assert result['success'] is True
        mock_post.assert_called_once()
        assert '/shared_commands/42/rate' in mock_post.call_args[0][0]

    @patch('Edge.cloud_sync.client.requests.Session.post')
    def test_rate_command_raises_on_error(self, mock_post, client):
        """rate_command 遇到 HTTP 錯誤應拋出 RequestException"""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("400 Bad Request")
        mock_post.return_value = mock_response

        with pytest.raises(requests.RequestException):
            client.rate_command(command_id=42, user_username='user', rating=6)

    @patch('Edge.cloud_sync.client.requests.Session.get')
    def test_get_featured_commands_success(self, mock_get, client):
        """get_featured_commands 成功案例"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'success': True,
            'data': {'commands': [{'id': 1, 'name': 'Featured'}]}
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = client.get_featured_commands(limit=5)

        assert result['success'] is True
        assert len(result['data']['commands']) == 1
        assert mock_get.call_args[1]['params'] == {'limit': 5}

    @patch('Edge.cloud_sync.client.requests.Session.get')
    def test_get_featured_commands_raises_on_error(self, mock_get, client):
        """get_featured_commands 遇到網路錯誤應拋出 RequestException"""
        mock_get.side_effect = requests.ConnectionError("Connection refused")

        with pytest.raises(requests.RequestException):
            client.get_featured_commands()

    @patch('Edge.cloud_sync.client.requests.Session.get')
    def test_get_popular_commands_success(self, mock_get, client):
        """get_popular_commands 成功案例"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'success': True,
            'data': {'commands': [{'id': 2, 'name': 'Popular'}]}
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = client.get_popular_commands(limit=3)

        assert result['success'] is True
        assert mock_get.call_args[1]['params'] == {'limit': 3}

    @patch('Edge.cloud_sync.client.requests.Session.get')
    def test_get_popular_commands_raises_on_error(self, mock_get, client):
        """get_popular_commands 遇到 HTTP 錯誤應拋出 RequestException"""
        mock_get.side_effect = requests.HTTPError("503 Service Unavailable")

        with pytest.raises(requests.RequestException):
            client.get_popular_commands()

    @patch('Edge.cloud_sync.client.requests.Session.get')
    def test_get_categories_success(self, mock_get, client):
        """get_categories 成功案例"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'success': True,
            'data': {'categories': ['nav', 'patrol', 'inspection']}
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = client.get_categories()

        assert result['success'] is True
        assert 'nav' in result['data']['categories']
        assert '/shared_commands/categories' in mock_get.call_args[0][0]

    @patch('Edge.cloud_sync.client.requests.Session.get')
    def test_get_categories_raises_on_error(self, mock_get, client):
        """get_categories 遇到網路錯誤應拋出 RequestException"""
        mock_get.side_effect = requests.RequestException("Timeout")

        with pytest.raises(requests.RequestException):
            client.get_categories()

    @patch('Edge.cloud_sync.client.requests.Session.post')
    def test_upload_user_settings_raises_on_error(self, mock_post, client):
        """upload_user_settings 遇到網路錯誤應拋出 RequestException"""
        mock_post.side_effect = requests.RequestException("Connection failed")

        with pytest.raises(requests.RequestException):
            client.upload_user_settings(user_id='user-123', settings={'theme': 'dark'})

    @patch('Edge.cloud_sync.client.requests.Session.get')
    def test_download_user_settings_raises_on_error(self, mock_get, client):
        """download_user_settings 遇到 HTTP 錯誤應拋出 RequestException"""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
        mock_get.return_value = mock_response

        with pytest.raises(requests.RequestException):
            client.download_user_settings(user_id='user-123')

    @patch('Edge.cloud_sync.client.requests.Session.post')
    def test_upload_command_history_raises_on_error(self, mock_post, client):
        """upload_command_history 遇到超時應拋出 RequestException"""
        mock_post.side_effect = requests.Timeout("Read timeout")

        with pytest.raises(requests.RequestException):
            client.upload_command_history(
                user_id='user-123', records=[{'command_id': 'cmd-001'}]
            )

    @patch('Edge.cloud_sync.client.requests.Session.get')
    def test_download_command_history_raises_on_error(self, mock_get, client):
        """download_command_history 遇到網路錯誤應拋出 RequestException"""
        mock_get.side_effect = requests.ConnectionError("Network unreachable")

        with pytest.raises(requests.RequestException):
            client.download_command_history(user_id='user-123')

    # ==================== JWT Token 初始化與更新 ====================

    def test_init_with_jwt_token(self):
        """初始化時設定 JWT token 應自動設定 Authorization header"""
        c = CloudSyncClient(
            cloud_api_url='https://cloud.example.com/api/cloud',
            edge_id='edge-001',
            jwt_token='jwt.token.here'
        )
        assert c.session.headers.get('Authorization') == 'Bearer jwt.token.here'

    def test_init_with_api_key_fallback(self):
        """使用舊版 api_key 參數時應相容（兼容舊接口）"""
        c = CloudSyncClient(
            cloud_api_url='https://cloud.example.com/api/cloud',
            edge_id='edge-001',
            api_key='old-api-key'
        )
        assert c.session.headers.get('Authorization') == 'Bearer old-api-key'

    def test_init_without_token(self):
        """未提供任何 token 時 Authorization header 不應存在"""
        from Edge.cloud_sync.client import CloudSyncClient as C
        c = C(
            cloud_api_url='https://cloud.example.com/api/cloud',
            edge_id='edge-001'
        )
        assert 'Authorization' not in c.session.headers

    def test_update_jwt_token(self):
        """update_jwt_token 應更新客戶端 token 和 session header"""
        from Edge.cloud_sync.client import update_jwt_token
        c = CloudSyncClient(
            cloud_api_url='https://cloud.example.com/api/cloud',
            edge_id='edge-001',
            jwt_token='old-token'
        )
        update_jwt_token(c, 'new-token')
        assert c.jwt_token == 'new-token'
        assert c.session.headers.get('Authorization') == 'Bearer new-token'
