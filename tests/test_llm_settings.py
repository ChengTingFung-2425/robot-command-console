"""
測試 LLM 設定介面

本測試套件驗證 WebUI 中的 LLM 設定功能，包括：
- 頁面路由和認證（登入要求、頁面訪問）
- API 端點（提供商列表、健康狀態、選擇、偵測、刷新）
- 錯誤處理（連線錯誤、參數驗證）
- MCP API 整合
"""

# Standard library imports
import os
import sys
from unittest.mock import MagicMock, patch

# Path manipulation (before project imports)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Third-party imports
import pytest  # noqa: E402


class TestLLMSettingsRoutes:
    """測試 LLM 設定相關路由"""

    @pytest.fixture
    def app(self):
        """建立測試應用"""
        from WebUI.app import create_app, db

        app = create_app(config_name='testing')

        with app.app_context():
            db.create_all()
            yield app
            db.drop_all()

    @pytest.fixture
    def client(self, app):
        """建立測試客戶端"""
        return app.test_client()

    @pytest.fixture
    def authenticated_client(self, app, client):
        """建立已認證的測試客戶端"""
        from WebUI.app import db
        from WebUI.app.models import User, UserProfile

        with app.app_context():
            # 建立測試用戶
            user = User(username='testuser', email='test@example.com')
            user.set_password('testpassword')
            db.session.add(user)
            db.session.flush()

            profile = UserProfile(user_id=user.id)
            db.session.add(profile)
            db.session.commit()

        # 登入
        client.post('/login', data={
            'username': 'testuser',
            'password': 'testpassword'
        }, follow_redirects=True)

        return client

    def test_llm_settings_page_requires_login(self, client):
        """測試 LLM 設定頁面需要登入"""
        response = client.get('/llm_settings')
        # 應該重新導向到登入頁面
        assert response.status_code == 302
        assert 'login' in response.location.lower()

    def test_llm_settings_page_accessible_when_logged_in(
            self, authenticated_client):
        """測試登入後可以存取 LLM 設定頁面"""
        response = authenticated_client.get('/llm_settings')
        assert response.status_code == 200
        assert 'LLM 設定'.encode('utf-8') in response.data

    def test_llm_settings_page_contains_required_elements(
            self, authenticated_client):
        """測試 LLM 設定頁面包含必要元素"""
        response = authenticated_client.get('/llm_settings')
        assert response.status_code == 200

        # 檢查頁面包含必要的元素
        html = response.data.decode('utf-8')
        assert '連線狀態' in html
        assert 'LLM 提供商' in html
        assert '重新掃描' in html
        assert 'Ollama' in html
        assert 'LM Studio' in html

    @patch('WebUI.app.routes.requests.get')
    def test_get_llm_providers_api(self, mock_get, client):
        """測試取得 LLM 提供商列表 API"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'providers': ['ollama', 'lmstudio'],
            'selected': 'ollama',
            'count': 2
        }
        mock_get.return_value = mock_response

        response = client.get('/api/llm/providers')
        assert response.status_code == 200

        data = response.get_json()
        assert 'providers' in data
        assert 'ollama' in data['providers']

    @patch('WebUI.app.routes.requests.get')
    def test_get_llm_providers_health_api(self, mock_get, client):
        """測試取得 LLM 提供商健康狀態 API"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'providers': {
                'ollama': {
                    'status': 'available',
                    'version': '0.1.0',
                    'available_models': ['llama2', 'mistral'],
                    'response_time_ms': 50.5
                }
            },
            'timestamp': '2024-01-01T00:00:00Z'
        }
        mock_get.return_value = mock_response

        response = client.get('/api/llm/providers/health')
        assert response.status_code == 200

        data = response.get_json()
        assert 'providers' in data
        assert 'ollama' in data['providers']
        assert data['providers']['ollama']['status'] == 'available'

    @patch('WebUI.app.routes.requests.get')
    def test_get_llm_providers_connection_error(self, mock_get, client):
        """測試 MCP 伺服器連線失敗時的處理"""
        from WebUI.app.routes import requests as routes_requests
        mock_get.side_effect = routes_requests.exceptions.ConnectionError()

        response = client.get('/api/llm/providers')
        assert response.status_code == 503

        data = response.get_json()
        assert data['mcp_available'] is False
        assert 'error' in data

    @patch('WebUI.app.routes.requests.post')
    def test_select_llm_provider_requires_login(self, mock_post, client):
        """測試選擇 LLM 提供商需要登入"""
        response = client.post(
            '/api/llm/providers/select',
            json={'provider_name': 'ollama'}
        )
        # 應該重新導向到登入頁面
        assert response.status_code == 302

    @patch('WebUI.app.routes.requests.post')
    def test_select_llm_provider_api(self, mock_post, authenticated_client):
        """測試選擇 LLM 提供商 API"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'message': '提供商切換成功',
            'provider': 'ollama'
        }
        mock_post.return_value = mock_response

        response = authenticated_client.post(
            '/api/llm/providers/select',
            json={'provider_name': 'ollama'}
        )
        assert response.status_code == 200

        data = response.get_json()
        assert data['provider'] == 'ollama'

    @patch('WebUI.app.routes.requests.post')
    def test_select_llm_provider_missing_param(
            self, mock_post, authenticated_client):
        """測試選擇 LLM 提供商缺少參數"""
        response = authenticated_client.post('/api/llm/providers/select')
        assert response.status_code == 400

        data = response.get_json()
        assert 'error' in data

    @patch('WebUI.app.routes.requests.post')
    def test_discover_llm_providers_api(self, mock_post, authenticated_client):
        """測試偵測 LLM 提供商 API"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'discovered': {
                'ollama': {'status': 'available'},
                'lmstudio': {'status': 'unavailable'}
            },
            'available_count': 1,
            'total_count': 2
        }
        mock_post.return_value = mock_response

        response = authenticated_client.post('/api/llm/providers/discover')
        assert response.status_code == 200

        data = response.get_json()
        assert data['available_count'] == 1

    @patch('WebUI.app.routes.requests.post')
    def test_refresh_llm_provider_api(self, mock_post, authenticated_client):
        """測試重新檢查 LLM 提供商 API"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'provider': 'ollama',
            'status': 'available',
            'response_time_ms': 45.2
        }
        mock_post.return_value = mock_response

        response = authenticated_client.post(
            '/api/llm/providers/ollama/refresh'
        )
        assert response.status_code == 200

        data = response.get_json()
        assert data['provider'] == 'ollama'
        assert data['status'] == 'available'

    def test_cors_status_api(self, app, client):
        """測試取得 CORS 狀態 API"""
        response = client.get('/api/llm/cors/status')
        assert response.status_code == 200

        data = response.get_json()
        assert 'enabled' in data

    def test_cors_toggle_requires_login(self, client):
        """測試切換 CORS 需要登入"""
        response = client.post(
            '/api/llm/cors/toggle',
            json={'enabled': True}
        )
        assert response.status_code == 302

    def test_cors_toggle_api(self, authenticated_client):
        """測試切換 CORS API - 簡單開關切換"""
        # 開啟 CORS
        response = authenticated_client.post(
            '/api/llm/cors/toggle',
            json={'enabled': True},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['enabled'] is True

        # 檢查狀態
        response = authenticated_client.get('/api/llm/cors/status')
        assert response.status_code == 200
        data = response.get_json()
        assert data['enabled'] is True

        # 關閉 CORS
        response = authenticated_client.post(
            '/api/llm/cors/toggle',
            json={'enabled': False},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['enabled'] is False


class TestLLMSettingsIntegration:
    """整合測試 - 測試 LLM 設定頁面與 MCP API 的整合"""

    @pytest.fixture
    def app(self):
        """建立測試應用"""
        from WebUI.app import create_app, db

        app = create_app(config_name='testing')

        with app.app_context():
            db.create_all()
            yield app
            db.drop_all()

    def test_llm_settings_route_registered(self, app):
        """測試 LLM 設定路由已註冊"""
        with app.test_client() as client:
            # 檢查路由存在（即使未登入會重新導向）
            response = client.get('/llm_settings')
            assert response.status_code in [200, 302]

    def test_api_endpoints_registered(self, app):
        """測試 API 端點已註冊"""
        with app.test_client() as client:
            # 測試 GET 端點
            response = client.get('/api/llm/providers')
            # 可能會失敗（因為 MCP 未運行），但路由應該存在
            assert response.status_code in [200, 503, 500]

            response = client.get('/api/llm/providers/health')
            assert response.status_code in [200, 503, 500]


class TestLLMPreferences:
    """測試 LLM 偏好設定功能"""

    @pytest.fixture
    def app(self):
        """建立測試應用"""
        from WebUI.app import create_app, db

        app = create_app(config_name='testing')

        with app.app_context():
            db.create_all()
            yield app
            db.drop_all()

    @pytest.fixture
    def client(self, app):
        """建立測試客戶端"""
        return app.test_client()

    @pytest.fixture
    def authenticated_client(self, app, client):
        """建立已認證的測試客戶端"""
        from WebUI.app import db
        from WebUI.app.models import User, UserProfile

        with app.app_context():
            # 建立測試用戶
            user = User(username='testuser', email='test@example.com')
            user.set_password('testpassword')
            db.session.add(user)
            db.session.flush()

            profile = UserProfile(user_id=user.id)
            db.session.add(profile)
            db.session.commit()

        # 登入
        client.post('/login', data={
            'username': 'testuser',
            'password': 'testpassword'
        }, follow_redirects=True)

        return client

    def test_get_preferences_requires_login(self, client):
        """測試取得 LLM 偏好設定需要登入"""
        response = client.get('/api/llm/preferences')
        # 應該重新導向到登入頁面
        assert response.status_code == 302

    def test_get_preferences_when_logged_in(self, authenticated_client):
        """測試登入後可以取得 LLM 偏好設定"""
        response = authenticated_client.get('/api/llm/preferences')
        assert response.status_code == 200

        data = response.get_json()
        assert 'provider' in data
        assert 'model' in data
        assert data['success'] is True

    def test_save_preferences_requires_login(self, client):
        """測試保存 LLM 偏好設定需要登入"""
        response = client.post(
            '/api/llm/preferences',
            json={'provider': 'ollama', 'model': 'llama2'}
        )
        assert response.status_code == 302

    def test_save_preferences_api(self, authenticated_client):
        """測試保存 LLM 偏好設定 API"""
        # 保存偏好設定
        response = authenticated_client.post(
            '/api/llm/preferences',
            json={'provider': 'ollama', 'model': 'llama2:latest'},
            content_type='application/json'
        )
        assert response.status_code == 200

        data = response.get_json()
        assert data['success'] is True
        assert data['provider'] == 'ollama'
        assert data['model'] == 'llama2:latest'

        # 驗證偏好已保存
        response = authenticated_client.get('/api/llm/preferences')
        assert response.status_code == 200

        data = response.get_json()
        assert data['provider'] == 'ollama'
        assert data['model'] == 'llama2:latest'

    def test_save_preferences_partial_update(self, authenticated_client):
        """測試部分更新 LLM 偏好設定"""
        # 先保存完整偏好
        authenticated_client.post(
            '/api/llm/preferences',
            json={'provider': 'ollama', 'model': 'llama2:latest'},
            content_type='application/json'
        )

        # 只更新模型
        response = authenticated_client.post(
            '/api/llm/preferences',
            json={'model': 'mistral:latest'},
            content_type='application/json'
        )
        assert response.status_code == 200

        data = response.get_json()
        assert data['success'] is True
        assert data['provider'] == 'ollama'  # 保持不變
        assert data['model'] == 'mistral:latest'  # 已更新

    def test_clear_preferences(self, authenticated_client):
        """測試清除 LLM 偏好設定"""
        # 先保存偏好
        authenticated_client.post(
            '/api/llm/preferences',
            json={'provider': 'ollama', 'model': 'llama2:latest'},
            content_type='application/json'
        )

        # 清除偏好
        response = authenticated_client.post(
            '/api/llm/preferences',
            json={'provider': None, 'model': None},
            content_type='application/json'
        )
        assert response.status_code == 200

        data = response.get_json()
        assert data['success'] is True
        assert data['provider'] is None
        assert data['model'] is None

    @patch('WebUI.app.routes.requests.get')
    def test_get_provider_models_api(self, mock_get, client):
        """測試取得提供商模型列表 API"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'provider': 'ollama',
            'models': [
                {'id': 'llama2:latest', 'name': 'llama2:latest', 'size': '7B'},
                {'id': 'mistral:latest', 'name': 'mistral:latest', 'size': '7B'}
            ],
            'count': 2
        }
        mock_get.return_value = mock_response

        response = client.get('/api/llm/providers/ollama/models')
        assert response.status_code == 200

        data = response.get_json()
        assert data['provider'] == 'ollama'
        assert len(data['models']) == 2
        assert data['models'][0]['id'] == 'llama2:latest'

    def test_get_provider_models_invalid_name(self, client):
        """測試無效的提供商名稱被拒絕"""
        response = client.get('/api/llm/providers/invalid<script>/models')
        assert response.status_code == 400

        data = response.get_json()
        assert 'error' in data

    def test_get_provider_models_hyphen_at_start_rejected(self, client):
        """測試以連字號開頭的提供商名稱被拒絕"""
        response = client.get('/api/llm/providers/-invalid/models')
        assert response.status_code == 400

        data = response.get_json()
        assert 'error' in data


class TestUserModelWithLLMPreferences:
    """測試 User 模型的 LLM 偏好欄位"""

    @pytest.fixture
    def app(self):
        """建立測試應用"""
        from WebUI.app import create_app, db

        app = create_app(config_name='testing')

        with app.app_context():
            db.create_all()
            yield app
            db.drop_all()

    def test_user_has_llm_preference_fields(self, app):
        """測試 User 模型有 LLM 偏好欄位"""
        from WebUI.app import db
        from WebUI.app.models import User

        with app.app_context():
            user = User(username='testuser', email='test@example.com')
            user.set_password('testpassword')
            user.llm_provider = 'ollama'
            user.llm_model = 'llama2:latest'

            db.session.add(user)
            db.session.commit()

            # 重新查詢確認欄位已保存
            saved_user = User.query.filter_by(username='testuser').first()
            assert saved_user.llm_provider == 'ollama'
            assert saved_user.llm_model == 'llama2:latest'

    def test_user_llm_preferences_default_null(self, app):
        """測試 User 的 LLM 偏好預設為 null"""
        from WebUI.app import db
        from WebUI.app.models import User

        with app.app_context():
            user = User(username='testuser', email='test@example.com')
            user.set_password('testpassword')

            db.session.add(user)
            db.session.commit()

            saved_user = User.query.filter_by(username='testuser').first()
            assert saved_user.llm_provider is None
            assert saved_user.llm_model is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
