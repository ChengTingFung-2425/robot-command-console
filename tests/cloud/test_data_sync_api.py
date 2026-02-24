# imports
import tempfile

import pytest
from flask import Flask

from Cloud.api.data_sync import data_sync_bp, init_data_sync_api


@pytest.fixture
def storage_dir():
    """建立臨時儲存目錄"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def app(storage_dir):
    """建立 Flask 測試應用"""
    flask_app = Flask(__name__)
    flask_app.config['TESTING'] = True
    flask_app.register_blueprint(data_sync_bp)

    # 使用固定的 JWT 密鑰初始化
    init_data_sync_api(jwt_secret='test-secret-key', storage_path=storage_dir)
    return flask_app


@pytest.fixture
def client(app):
    """建立 Flask 測試客戶端"""
    return app.test_client()


def _make_token(app_instance) -> str:
    """產生測試用 JWT token"""
    from Cloud.api.auth import CloudAuthService
    auth = CloudAuthService('test-secret-key')
    return auth.generate_token(user_id='user-123', username='testuser', role='user')


class TestDataSyncSettingsAPI:
    """測試用戶設定同步端點"""

    def test_upload_settings_success(self, client, app):
        """測試上傳設定 - 成功案例"""
        token = _make_token(app)
        response = client.post(
            '/api/cloud/data_sync/settings/user-123',
            json={
                'settings': {'theme': 'dark', 'language': 'zh-TW'},
                'edge_id': 'edge-001'
            },
            headers={'Authorization': f'Bearer {token}'}
        )
        data = response.get_json()
        assert response.status_code == 200
        assert data['success'] is True
        assert 'updated_at' in data

    def test_upload_settings_missing_settings_field(self, client, app):
        """測試上傳設定 - 缺少 settings 欄位"""
        token = _make_token(app)
        response = client.post(
            '/api/cloud/data_sync/settings/user-123',
            json={'edge_id': 'edge-001'},
            headers={'Authorization': f'Bearer {token}'}
        )
        assert response.status_code == 400

    def test_upload_settings_invalid_user_id(self, client, app):
        """測試上傳設定 - 含路徑穿越字元的 user_id"""
        token = _make_token(app)
        response = client.post(
            '/api/cloud/data_sync/settings/../../../etc/passwd',
            json={'settings': {}},
            headers={'Authorization': f'Bearer {token}'}
        )
        # Flask 不允許含 .. 的路由，回傳 404
        assert response.status_code == 404

    def test_download_settings_success(self, client, app):
        """測試下載設定 - 成功案例（先上傳再下載）"""
        token = _make_token(app)
        settings = {'theme': 'light', 'language': 'en'}

        # 先上傳
        client.post(
            '/api/cloud/data_sync/settings/user-456',
            json={'settings': settings, 'edge_id': 'edge-001'},
            headers={'Authorization': f'Bearer {token}'}
        )

        # 再下載
        response = client.get(
            '/api/cloud/data_sync/settings/user-456',
            headers={'Authorization': f'Bearer {token}'}
        )
        data = response.get_json()
        assert response.status_code == 200
        assert data['success'] is True
        assert data['data']['settings'] == settings
        assert data['data']['user_id'] == 'user-456'

    def test_download_settings_not_found(self, client, app):
        """測試下載設定 - 設定不存在"""
        token = _make_token(app)
        response = client.get(
            '/api/cloud/data_sync/settings/nonexistent-user',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert response.status_code == 404

    def test_settings_requires_auth(self, client):
        """測試設定端點需要認證"""
        response = client.get('/api/cloud/data_sync/settings/user-123')
        assert response.status_code == 401


class TestDataSyncHistoryAPI:
    """測試指令歷史同步端點"""

    def test_upload_history_success(self, client, app):
        """測試上傳歷史 - 成功案例"""
        token = _make_token(app)
        records = [
            {'command_id': 'cmd-001', 'status': 'succeeded', 'robot_id': 'robot-1'},
            {'command_id': 'cmd-002', 'status': 'failed', 'robot_id': 'robot-1'},
        ]
        response = client.post(
            '/api/cloud/data_sync/history/user-123',
            json={'records': records, 'edge_id': 'edge-001'},
            headers={'Authorization': f'Bearer {token}'}
        )
        data = response.get_json()
        assert response.status_code == 200
        assert data['success'] is True
        assert data['synced_count'] == 2
        assert data['total'] == 2

    def test_upload_history_deduplication(self, client, app):
        """測試上傳歷史 - 重複記錄去重"""
        token = _make_token(app)
        records = [{'command_id': 'cmd-001', 'status': 'succeeded'}]

        # 上傳兩次相同的記錄
        client.post(
            '/api/cloud/data_sync/history/user-123',
            json={'records': records, 'edge_id': 'edge-001'},
            headers={'Authorization': f'Bearer {token}'}
        )
        response = client.post(
            '/api/cloud/data_sync/history/user-123',
            json={'records': records, 'edge_id': 'edge-001'},
            headers={'Authorization': f'Bearer {token}'}
        )
        data = response.get_json()
        assert response.status_code == 200
        assert data['synced_count'] == 0  # 第二次不新增
        assert data['total'] == 1           # 總共仍是 1 筆

    def test_upload_history_missing_records_field(self, client, app):
        """測試上傳歷史 - 缺少 records 欄位"""
        token = _make_token(app)
        response = client.post(
            '/api/cloud/data_sync/history/user-123',
            json={'edge_id': 'edge-001'},
            headers={'Authorization': f'Bearer {token}'}
        )
        assert response.status_code == 400

    def test_download_history_success(self, client, app):
        """測試下載歷史 - 成功案例"""
        token = _make_token(app)
        records = [
            {'command_id': 'cmd-001', 'status': 'succeeded'},
            {'command_id': 'cmd-002', 'status': 'failed'},
        ]

        # 先上傳
        client.post(
            '/api/cloud/data_sync/history/user-789',
            json={'records': records},
            headers={'Authorization': f'Bearer {token}'}
        )

        # 再下載
        response = client.get(
            '/api/cloud/data_sync/history/user-789',
            headers={'Authorization': f'Bearer {token}'}
        )
        data = response.get_json()
        assert response.status_code == 200
        assert data['success'] is True
        assert data['data']['total'] == 2
        assert len(data['data']['records']) == 2

    def test_download_history_empty(self, client, app):
        """測試下載歷史 - 無歷史記錄"""
        token = _make_token(app)
        response = client.get(
            '/api/cloud/data_sync/history/no-history-user',
            headers={'Authorization': f'Bearer {token}'}
        )
        data = response.get_json()
        assert response.status_code == 200
        assert data['success'] is True
        assert data['data']['total'] == 0
        assert data['data']['records'] == []

    def test_download_history_pagination(self, client, app):
        """測試下載歷史 - 分頁查詢"""
        token = _make_token(app)
        records = [{'command_id': f'cmd-{i:03d}', 'status': 'succeeded'} for i in range(10)]

        client.post(
            '/api/cloud/data_sync/history/user-page',
            json={'records': records},
            headers={'Authorization': f'Bearer {token}'}
        )

        # 取第一頁（5 筆）
        response = client.get(
            '/api/cloud/data_sync/history/user-page?limit=5&offset=0',
            headers={'Authorization': f'Bearer {token}'}
        )
        data = response.get_json()
        assert response.status_code == 200
        assert data['data']['total'] == 10
        assert len(data['data']['records']) == 5

        # 取第二頁（5 筆）
        response2 = client.get(
            '/api/cloud/data_sync/history/user-page?limit=5&offset=5',
            headers={'Authorization': f'Bearer {token}'}
        )
        data2 = response2.get_json()
        assert len(data2['data']['records']) == 5

    def test_history_requires_auth(self, client):
        """測試歷史端點需要認證"""
        response = client.get('/api/cloud/data_sync/history/user-123')
        assert response.status_code == 401
