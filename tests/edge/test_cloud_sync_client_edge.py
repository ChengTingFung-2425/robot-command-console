"""
Edge CloudSyncClient 單元測試（Edge/cloud_client/sync_client.py）

涵蓋：健康檢查、檔案上傳/下載/列表/刪除、統計、同步、異常處理。
"""
import unittest
from unittest.mock import Mock, patch
import requests

from Edge.cloud_client.sync_client import CloudSyncClient


class TestEdgeCloudSyncClientInit(unittest.TestCase):
    """初始化與 token 管理測試"""

    def test_init_stores_url_and_token(self):
        """初始化應正確儲存 URL、token、timeout"""
        client = CloudSyncClient(
            cloud_api_url='https://cloud.example.com/api/',
            token='test-token',
            timeout=60
        )
        # 結尾斜線應被移除
        assert client.cloud_api_url == 'https://cloud.example.com/api'
        assert client.token == 'test-token'
        assert client.timeout == 60

    def test_init_without_token(self):
        """未提供 token 時 token 應為 None"""
        client = CloudSyncClient(cloud_api_url='https://cloud.example.com/api')
        assert client.token is None

    def test_set_token(self):
        """set_token 應更新 token"""
        client = CloudSyncClient(cloud_api_url='https://cloud.example.com/api')
        client.set_token('new-token')
        assert client.token == 'new-token'

    def test_get_headers_with_token(self):
        """有 token 時 _get_headers 應包含 Authorization header"""
        client = CloudSyncClient(
            cloud_api_url='https://cloud.example.com/api',
            token='bearer-token'
        )
        headers = client._get_headers()
        assert headers.get('Authorization') == 'Bearer bearer-token'

    def test_get_headers_without_token(self):
        """無 token 時 _get_headers 應返回空字典"""
        client = CloudSyncClient(cloud_api_url='https://cloud.example.com/api')
        headers = client._get_headers()
        assert 'Authorization' not in headers


class TestEdgeCloudSyncClientHealthCheck(unittest.TestCase):
    """健康檢查測試"""

    def setUp(self):
        self.client = CloudSyncClient(
            cloud_api_url='https://cloud.example.com/api',
            token='test-token'
        )

    @patch('Edge.cloud_client.sync_client.requests.get')
    def test_health_check_success(self, mock_get):
        """健康檢查成功時應返回包含狀態的字典"""
        mock_response = Mock()
        mock_response.json.return_value = {'status': 'healthy', 'version': '1.0'}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = self.client.health_check()

        assert result['status'] == 'healthy'
        mock_get.assert_called_once()

    @patch('Edge.cloud_client.sync_client.requests.get')
    def test_health_check_connection_error(self, mock_get):
        """連線失敗時應返回 unhealthy 狀態而非拋出例外"""
        mock_get.side_effect = requests.ConnectionError("Connection refused")

        result = self.client.health_check()

        assert result['status'] == 'unhealthy'
        assert 'error' in result

    @patch('Edge.cloud_client.sync_client.requests.get')
    def test_health_check_timeout(self, mock_get):
        """超時時應返回 unhealthy 狀態"""
        mock_get.side_effect = requests.Timeout("Request timed out")

        result = self.client.health_check()

        assert result['status'] == 'unhealthy'


class TestEdgeCloudSyncClientFileUpload(unittest.TestCase):
    """檔案上傳測試"""

    def setUp(self):
        self.client = CloudSyncClient(
            cloud_api_url='https://cloud.example.com/api',
            token='test-token'
        )

    @patch('Edge.cloud_client.sync_client.requests.post')
    def test_upload_file_success(self, mock_post):
        """上傳存在的檔案應成功返回結果"""
        import tempfile
        import os

        mock_response = Mock()
        mock_response.json.return_value = {'file_id': 'abc123', 'size': 100}
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as f:
            f.write(b'test content')
            tmp_path = f.name

        try:
            result = self.client.upload_file(tmp_path, category='logs')
            assert result is not None
            assert result['file_id'] == 'abc123'
            mock_post.assert_called_once()
        finally:
            os.unlink(tmp_path)

    def test_upload_file_not_found(self):
        """上傳不存在的檔案應返回 None"""
        result = self.client.upload_file('/nonexistent/path/file.txt')
        assert result is None

    @patch('Edge.cloud_client.sync_client.requests.post')
    def test_upload_file_request_exception(self, mock_post):
        """上傳時遇到網路錯誤應返回 None"""
        import tempfile
        import os

        mock_post.side_effect = requests.RequestException("Upload failed")

        with tempfile.NamedTemporaryFile(delete=False, suffix='.txt') as f:
            f.write(b'content')
            tmp_path = f.name

        try:
            result = self.client.upload_file(tmp_path)
            assert result is None
        finally:
            os.unlink(tmp_path)


class TestEdgeCloudSyncClientFileDownload(unittest.TestCase):
    """檔案下載測試"""

    def setUp(self):
        self.client = CloudSyncClient(
            cloud_api_url='https://cloud.example.com/api',
            token='test-token'
        )

    @patch('Edge.cloud_client.sync_client.requests.get')
    def test_download_file_success(self, mock_get):
        """下載檔案成功時應寫入本地並返回 True"""
        import tempfile
        import os

        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.iter_content.return_value = [b'file', b'content']
        mock_get.return_value = mock_response

        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = os.path.join(tmpdir, 'downloaded.txt')
            result = self.client.download_file(
                file_id='abc123', save_path=save_path, category='logs'
            )
            assert result is True
            assert os.path.exists(save_path)

    @patch('Edge.cloud_client.sync_client.requests.get')
    def test_download_file_request_exception(self, mock_get):
        """下載時遇到網路錯誤應返回 False"""
        mock_get.side_effect = requests.RequestException("Download failed")

        result = self.client.download_file(
            file_id='abc123', save_path='/tmp/test_download.txt'
        )
        assert result is False


class TestEdgeCloudSyncClientListFiles(unittest.TestCase):
    """檔案列表測試"""

    def setUp(self):
        self.client = CloudSyncClient(
            cloud_api_url='https://cloud.example.com/api',
            token='test-token'
        )

    @patch('Edge.cloud_client.sync_client.requests.get')
    def test_list_files_success(self, mock_get):
        """列出檔案成功應返回檔案列表"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'files': [
                {'file_id': 'f1', 'filename': 'a.txt'},
                {'file_id': 'f2', 'filename': 'b.txt'}
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = self.client.list_files(category='logs')

        assert result is not None
        assert len(result['files']) == 2

    @patch('Edge.cloud_client.sync_client.requests.get')
    def test_list_files_with_no_category(self, mock_get):
        """不指定 category 時應不傳遞 category 參數"""
        mock_response = Mock()
        mock_response.json.return_value = {'files': []}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = self.client.list_files()

        assert result is not None
        call_kwargs = mock_get.call_args[1]
        assert call_kwargs.get('params') == {}

    @patch('Edge.cloud_client.sync_client.requests.get')
    def test_list_files_request_exception(self, mock_get):
        """列出檔案時遇到網路錯誤應返回 None"""
        mock_get.side_effect = requests.RequestException("Connection error")

        result = self.client.list_files()
        assert result is None


class TestEdgeCloudSyncClientDeleteFile(unittest.TestCase):
    """檔案刪除測試"""

    def setUp(self):
        self.client = CloudSyncClient(
            cloud_api_url='https://cloud.example.com/api',
            token='test-token'
        )

    @patch('Edge.cloud_client.sync_client.requests.delete')
    def test_delete_file_success(self, mock_delete):
        """刪除檔案成功應返回 True"""
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_delete.return_value = mock_response

        result = self.client.delete_file(file_id='abc123', category='logs')

        assert result is True
        mock_delete.assert_called_once()

    @patch('Edge.cloud_client.sync_client.requests.delete')
    def test_delete_file_request_exception(self, mock_delete):
        """刪除時遇到網路錯誤應返回 False"""
        mock_delete.side_effect = requests.RequestException("Forbidden")

        result = self.client.delete_file(file_id='abc123')
        assert result is False


class TestEdgeCloudSyncClientStorageStats(unittest.TestCase):
    """儲存統計測試"""

    def setUp(self):
        self.client = CloudSyncClient(
            cloud_api_url='https://cloud.example.com/api',
            token='test-token'
        )

    @patch('Edge.cloud_client.sync_client.requests.get')
    def test_get_storage_stats_success(self, mock_get):
        """取得儲存統計成功應返回統計字典"""
        mock_response = Mock()
        mock_response.json.return_value = {'total_files': 10, 'total_size_bytes': 1024}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = self.client.get_storage_stats()

        assert result is not None
        assert result['total_files'] == 10

    @patch('Edge.cloud_client.sync_client.requests.get')
    def test_get_storage_stats_request_exception(self, mock_get):
        """取得統計時遇到網路錯誤應返回 None"""
        mock_get.side_effect = requests.RequestException("Server error")

        result = self.client.get_storage_stats()
        assert result is None


class TestEdgeCloudSyncClientSyncFiles(unittest.TestCase):
    """檔案同步測試"""

    def setUp(self):
        self.client = CloudSyncClient(
            cloud_api_url='https://cloud.example.com/api',
            token='test-token'
        )

    def test_sync_files_invalid_direction(self):
        """無效的 direction 參數應拋出 ValueError"""
        with self.assertRaises(ValueError):
            self.client.sync_files(local_dir='/tmp', direction='invalid')

    @patch.object(CloudSyncClient, 'list_files')
    def test_sync_files_list_files_failure(self, mock_list):
        """list_files 返回 None 時 sync_files 應計入錯誤並返回"""
        import tempfile
        mock_list.return_value = None

        with tempfile.TemporaryDirectory() as tmpdir:
            result = self.client.sync_files(local_dir=tmpdir, direction='both')

        assert result['errors'] >= 1

    @patch.object(CloudSyncClient, 'list_files')
    @patch.object(CloudSyncClient, 'download_file')
    def test_sync_files_download_only(self, mock_download, mock_list):
        """direction='download' 時應下載雲端未存在本地的檔案"""
        import tempfile

        mock_list.return_value = {
            'files': [
                {'file_id': 'f1', 'filename': 'new_file.txt'}
            ]
        }
        mock_download.return_value = True

        with tempfile.TemporaryDirectory() as tmpdir:
            result = self.client.sync_files(
                local_dir=tmpdir, category='logs', direction='download'
            )

        assert result['downloaded'] == 1
        assert result['errors'] == 0

    @patch.object(CloudSyncClient, 'list_files')
    def test_sync_files_upload_only_with_empty_local(self, mock_list):
        """direction='upload' 且本地無檔案時應無上傳無錯誤"""
        import tempfile

        mock_list.return_value = {'files': []}

        with tempfile.TemporaryDirectory() as tmpdir:
            result = self.client.sync_files(
                local_dir=tmpdir, direction='upload'
            )

        assert result['uploaded'] == 0
        assert result['errors'] == 0


if __name__ == '__main__':
    unittest.main()
