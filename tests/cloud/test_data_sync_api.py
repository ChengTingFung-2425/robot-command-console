# imports
import tempfile

import pytest
from flask import Flask

from Cloud.api.data_sync import _validate_user_id, data_sync_bp, init_data_sync_api


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


def _make_token(user_id: str = 'user-123', role: str = 'user') -> str:
    """產生測試用 JWT token"""
    from Cloud.api.auth import CloudAuthService
    auth = CloudAuthService('test-secret-key')
    return auth.generate_token(user_id=user_id, username=user_id, role=role)


class TestValidateUserId:
    """測試 _validate_user_id 函式的安全驗證邏輯"""

    def test_valid_alphanumeric(self):
        assert _validate_user_id('user123') is True

    def test_valid_with_dash(self):
        assert _validate_user_id('user-123') is True

    def test_valid_with_underscore(self):
        assert _validate_user_id('user_123') is True

    def test_rejects_dot(self):
        """user_id 不允許點號，防止 .. 路徑穿越"""
        assert _validate_user_id('user.name') is False

    def test_rejects_double_dot(self):
        assert _validate_user_id('..') is False

    def test_rejects_slash(self):
        assert _validate_user_id('user/admin') is False

    def test_rejects_backslash(self):
        assert _validate_user_id('user\\admin') is False

    def test_rejects_empty(self):
        assert _validate_user_id('') is False

    def test_rejects_too_long(self):
        assert _validate_user_id('a' * 65) is False

    def test_accepts_max_length(self):
        assert _validate_user_id('a' * 64) is True

    def test_rejects_path_traversal_pattern(self):
        assert _validate_user_id('../etc/passwd') is False


class TestDataSyncSettingsAPI:
    """測試用戶設定同步端點"""

    def test_upload_settings_success(self, client, app):
        """測試上傳設定 - 成功案例"""
        token = _make_token('user-123')
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
        token = _make_token('user-123')
        response = client.post(
            '/api/cloud/data_sync/settings/user-123',
            json={'edge_id': 'edge-001'},
            headers={'Authorization': f'Bearer {token}'}
        )
        assert response.status_code == 400

    def test_upload_settings_invalid_user_id_rejected(self, client, app):
        """測試端點拒絕含不合法字元的 path user_id（驗證 _validate_user_id 運作）"""
        # 使用合法的 user-123 token，但嘗試 POST 到含點號的 user_id 路徑
        # 預期端點在 _validate_user_id 驗證階段回傳 400
        token = _make_token('user-123')
        response = client.post(
            '/api/cloud/data_sync/settings/user.invalid',
            json={'settings': {}},
            headers={'Authorization': f'Bearer {token}'}
        )
        # user.invalid 含點號，被 _validate_user_id 拒絕 → 400
        assert response.status_code == 400

    def test_download_settings_success(self, client, app):
        """測試下載設定 - 成功案例（先上傳再下載）"""
        token = _make_token('user-456')
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
        token = _make_token('nonexistent-user')
        response = client.get(
            '/api/cloud/data_sync/settings/nonexistent-user',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert response.status_code == 404

    def test_settings_requires_auth(self, client):
        """測試設定端點需要認證"""
        response = client.get('/api/cloud/data_sync/settings/user-123')
        assert response.status_code == 401

    def test_download_settings_forbidden_other_user(self, client, app):
        """測試下載其他用戶的設定 - 應被拒絕（403）"""
        # user-123 嘗試存取 user-456 的設定
        token = _make_token('user-123')
        response = client.get(
            '/api/cloud/data_sync/settings/user-456',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert response.status_code == 403

    def test_upload_settings_forbidden_other_user(self, client, app):
        """測試上傳到其他用戶的設定 - 應被拒絕（403）"""
        token = _make_token('user-123')
        response = client.post(
            '/api/cloud/data_sync/settings/user-999',
            json={'settings': {'theme': 'dark'}},
            headers={'Authorization': f'Bearer {token}'}
        )
        assert response.status_code == 403

    def test_admin_can_access_other_user_settings(self, client, app):
        """測試 admin 角色可以存取其他用戶的設定"""
        # 先用 user-456 上傳設定
        user_token = _make_token('user-456')
        client.post(
            '/api/cloud/data_sync/settings/user-456',
            json={'settings': {'theme': 'light'}},
            headers={'Authorization': f'Bearer {user_token}'}
        )

        # admin 應可下載 user-456 的設定
        admin_token = _make_token('admin-001', role='admin')
        response = client.get(
            '/api/cloud/data_sync/settings/user-456',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        assert response.status_code == 200


class TestDataSyncHistoryAPI:
    """測試指令歷史同步端點"""

    def test_upload_history_success(self, client, app):
        """測試上傳歷史 - 成功案例"""
        token = _make_token('user-123')
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
        token = _make_token('user-123')
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
        token = _make_token('user-123')
        response = client.post(
            '/api/cloud/data_sync/history/user-123',
            json={'edge_id': 'edge-001'},
            headers={'Authorization': f'Bearer {token}'}
        )
        assert response.status_code == 400

    def test_download_history_success(self, client, app):
        """測試下載歷史 - 成功案例"""
        token = _make_token('user-789')
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
        token = _make_token('no-history-user')
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
        token = _make_token('user-page')
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

    def test_download_history_forbidden_other_user(self, client, app):
        """測試下載其他用戶的歷史 - 應被拒絕（403）"""
        token = _make_token('user-123')
        response = client.get(
            '/api/cloud/data_sync/history/user-456',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert response.status_code == 403

    def test_upload_history_forbidden_other_user(self, client, app):
        """測試上傳到其他用戶的歷史 - 應被拒絕（403）"""
        token = _make_token('user-123')
        response = client.post(
            '/api/cloud/data_sync/history/user-999',
            json={'records': [{'command_id': 'cmd-001'}]},
            headers={'Authorization': f'Bearer {token}'}
        )
        assert response.status_code == 403

    def test_admin_can_access_other_user_history(self, client, app):
        """測試 admin 角色可以存取其他用戶的歷史"""
        # 先用 user-789 上傳
        user_token = _make_token('user-789')
        client.post(
            '/api/cloud/data_sync/history/user-789',
            json={'records': [{'command_id': 'cmd-001'}]},
            headers={'Authorization': f'Bearer {user_token}'}
        )

        # admin 應可下載 user-789 的歷史
        admin_token = _make_token('admin-001', role='admin')
        response = client.get(
            '/api/cloud/data_sync/history/user-789',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        assert response.status_code == 200
