# imports
import os
import sys
import unittest
import json

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

try:
    from WebUI.app import create_app, db
    from WebUI.app.models import User
    from WebUI.app.auth_api import create_access_token, create_refresh_token, verify_token
    WEBUI_AVAILABLE = True
except ImportError as e:
    WEBUI_AVAILABLE = False
    SKIP_REASON = f"WebUI dependencies not available: {e}"


@unittest.skipUnless(WEBUI_AVAILABLE, "WebUI dependencies not installed")
class TestAuthAPI(unittest.TestCase):
    """測試 Cloud-First 認證 API"""

    def setUp(self):
        """建立測試環境"""
        self.app = create_app('testing')
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        # 建立測試使用者
        self.test_user = User(
            username='testuser',
            email='test@example.com',
            role='operator'
        )
        self.test_user.set_password('testpass123')
        db.session.add(self.test_user)
        db.session.commit()

    def tearDown(self):
        """清理測試環境"""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_login_success(self):
        """測試成功登入"""
        response = self.client.post(
            '/api/auth/login',
            data=json.dumps({
                'username': 'testuser',
                'password': 'testpass123'
            }),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)

        self.assertTrue(data['success'])
        self.assertIn('access_token', data)
        self.assertIn('refresh_token', data)
        self.assertIn('user', data)
        self.assertIn('device_id', data)
        self.assertEqual(data['user']['username'], 'testuser')
        self.assertEqual(data['user']['role'], 'operator')
        self.assertEqual(data['expires_in'], 15 * 60)  # 15 分鐘 = 900 秒

    def test_login_failure_invalid_credentials(self):
        """測試登入失敗（無效憑證）"""
        response = self.client.post(
            '/api/auth/login',
            data=json.dumps({
                'username': 'testuser',
                'password': 'wrongpassword'
            }),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 401)
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'Invalid username or password')

    def test_login_failure_missing_fields(self):
        """測試登入失敗（缺少欄位）"""
        response = self.client.post(
            '/api/auth/login',
            data=json.dumps({'username': 'testuser'}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)

    def test_refresh_token(self):
        """測試 Token 更新"""
        # 先登入取得 tokens
        login_response = self.client.post(
            '/api/auth/login',
            data=json.dumps({
                'username': 'testuser',
                'password': 'testpass123'
            }),
            content_type='application/json'
        )
        login_data = json.loads(login_response.data)
        refresh_token = login_data['refresh_token']

        # 使用 refresh token 更新 access token
        response = self.client.post(
            '/api/auth/refresh',
            data=json.dumps({'refresh_token': refresh_token}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)

        self.assertTrue(data['success'])
        self.assertIn('access_token', data)
        self.assertIn('user', data)
        self.assertEqual(data['user']['username'], 'testuser')

    def test_refresh_token_failure_invalid_token(self):
        """測試 Token 更新失敗（無效 token）"""
        response = self.client.post(
            '/api/auth/refresh',
            data=json.dumps({'refresh_token': 'invalid_token'}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 401)
        data = json.loads(response.data)
        self.assertIn('error', data)

    def test_verify_token(self):
        """測試 Token 驗證"""
        # 先登入取得 token
        login_response = self.client.post(
            '/api/auth/login',
            data=json.dumps({
                'username': 'testuser',
                'password': 'testpass123'
            }),
            content_type='application/json'
        )
        login_data = json.loads(login_response.data)
        access_token = login_data['access_token']

        # 驗證 token
        response = self.client.post(
            '/api/auth/verify',
            headers={'Authorization': f'Bearer {access_token}'}
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)

        self.assertTrue(data['valid'])
        self.assertIn('user', data)
        self.assertEqual(data['user']['username'], 'testuser')

    def test_verify_token_failure_missing_header(self):
        """測試 Token 驗證失敗（缺少 header）"""
        response = self.client.post('/api/auth/verify')

        self.assertEqual(response.status_code, 401)
        data = json.loads(response.data)
        self.assertIn('error', data)

    def test_get_current_user(self):
        """測試取得當前使用者資訊"""
        # 先登入
        login_response = self.client.post(
            '/api/auth/login',
            data=json.dumps({
                'username': 'testuser',
                'password': 'testpass123'
            }),
            content_type='application/json'
        )
        login_data = json.loads(login_response.data)
        access_token = login_data['access_token']

        # 取得使用者資訊
        response = self.client.get(
            '/api/auth/me',
            headers={'Authorization': f'Bearer {access_token}'}
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)

        self.assertIn('user', data)
        self.assertEqual(data['user']['username'], 'testuser')
        self.assertEqual(data['user']['email'], 'test@example.com')
        self.assertIn('ui_preferences', data['user'])

    def test_revoke_token(self):
        """測試 Token 撤銷（登出）"""
        # 先登入
        login_response = self.client.post(
            '/api/auth/login',
            data=json.dumps({
                'username': 'testuser',
                'password': 'testpass123'
            }),
            content_type='application/json'
        )
        login_data = json.loads(login_response.data)
        access_token = login_data['access_token']

        # 登出
        response = self.client.post(
            '/api/auth/revoke',
            headers={'Authorization': f'Bearer {access_token}'}
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)

        self.assertTrue(data['success'])
        self.assertIn('message', data)

    def test_token_with_device_id(self):
        """測試使用自訂 device_id 登入"""
        custom_device_id = 'my-device-123'

        response = self.client.post(
            '/api/auth/login',
            data=json.dumps({
                'username': 'testuser',
                'password': 'testpass123',
                'device_id': custom_device_id
            }),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)

        self.assertEqual(data['device_id'], custom_device_id)


@unittest.skipUnless(WEBUI_AVAILABLE, "WebUI dependencies not installed")
class TestTokenHelpers(unittest.TestCase):
    """測試 Token 工具函數"""

    def setUp(self):
        """建立測試環境"""
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        os.environ['SECRET_KEY'] = 'test-secret-key'

    def tearDown(self):
        """清理測試環境"""
        self.app_context.pop()

    def test_create_and_verify_access_token(self):
        """測試建立和驗證 Access Token"""
        user_id = 1
        role = 'admin'

        token = create_access_token(user_id, role)
        self.assertIsNotNone(token)

        payload = verify_token(token, 'access')
        self.assertIsNotNone(payload)
        self.assertEqual(payload['user_id'], user_id)
        self.assertEqual(payload['role'], role)
        self.assertEqual(payload['type'], 'access')

    def test_create_and_verify_refresh_token(self):
        """測試建立和驗證 Refresh Token"""
        user_id = 1
        device_id = 'test-device-123'

        token = create_refresh_token(user_id, device_id)
        self.assertIsNotNone(token)

        payload = verify_token(token, 'refresh')
        self.assertIsNotNone(payload)
        self.assertEqual(payload['user_id'], user_id)
        self.assertEqual(payload['device_id'], device_id)
        self.assertEqual(payload['type'], 'refresh')

    def test_verify_token_wrong_type(self):
        """測試驗證錯誤類型的 Token"""
        access_token = create_access_token(1, 'admin')

        # 嘗試以 refresh 類型驗證 access token
        payload = verify_token(access_token, 'refresh')
        self.assertIsNone(payload)

    def test_verify_invalid_token(self):
        """測試驗證無效 Token"""
        payload = verify_token('invalid_token_string', 'access')
        self.assertIsNone(payload)


if __name__ == '__main__':
    unittest.main()
