"""
測試 Cloud shared commands API JWT 認證功能
"""

import unittest
from unittest.mock import Mock, patch

from Cloud.api.auth import CloudAuthService
from Cloud.shared_commands.api import (
    init_shared_commands_auth,
    bp as shared_commands_bp
)


class TestSharedCommandsAuth(unittest.TestCase):
    """測試 shared commands API JWT 認證"""

    def setUp(self):
        """初始化測試"""
        self.jwt_secret = "test-secret-key-123"
        self.auth_service = CloudAuthService(self.jwt_secret)

        # 初始化 shared commands 認證
        init_shared_commands_auth(self.jwt_secret)

    def test_generate_token(self):
        """測試生成 JWT token"""
        token = self.auth_service.generate_token(
            user_id="test-user-123",
            username="test_user",
            role="user",
            expires_in=3600
        )

        self.assertIsNotNone(token)
        self.assertIsInstance(token, str)
        self.assertTrue(len(token) > 50)

    def test_verify_valid_token(self):
        """測試驗證有效的 token"""
        token = self.auth_service.generate_token(
            user_id="test-user-123",
            username="test_user",
            role="admin"
        )

        payload = self.auth_service.verify_token(token)

        self.assertIsNotNone(payload)
        self.assertEqual(payload["user_id"], "test-user-123")
        self.assertEqual(payload["username"], "test_user")
        self.assertEqual(payload["role"], "admin")

    def test_verify_expired_token(self):
        """測試驗證過期的 token"""
        # 生成一個已經過期的 token（過期時間 = -1 秒）
        token = self.auth_service.generate_token(
            user_id="test-user",
            username="test",
            expires_in=-1
        )

        # 驗證應該失敗
        payload = self.auth_service.verify_token(token)
        self.assertIsNone(payload)

    def test_verify_invalid_token(self):
        """測試驗證無效的 token"""
        invalid_token = "invalid.token.here"

        payload = self.auth_service.verify_token(invalid_token)
        self.assertIsNone(payload)

    def test_verify_token_with_wrong_secret(self):
        """測試使用錯誤密鑰生成的 token"""
        # 使用不同的密鑰生成 token
        other_auth = CloudAuthService("different-secret")
        token = other_auth.generate_token(
            user_id="test-user",
            username="test"
        )

        # 使用原本的 auth service 驗證應該失敗
        payload = self.auth_service.verify_token(token)
        self.assertIsNone(payload)

    @patch('Cloud.shared_commands.api.get_service')
    def test_upload_command_with_auth(self, mock_get_service):
        """測試上傳指令需要認證"""
        from flask import Flask

        app = Flask(__name__)
        app.register_blueprint(shared_commands_bp)

        # 建立 mock 指令
        mock_command = Mock()
        mock_command.to_dict.return_value = {"id": 1, "name": "test"}

        mock_service = Mock()
        mock_service.upload_command.return_value = mock_command
        mock_get_service.return_value = mock_service

        # 生成有效的 token
        token = self.auth_service.generate_token(
            user_id="test-user",
            username="testuser"
        )

        with app.test_client() as client:
            # 測試沒有 token 的請求
            response = client.post('/api/cloud/shared_commands/upload', json={
                'name': 'Test Command',
                'description': 'Test',
                'category': 'test',
                'content': '[]',
                'author_username': 'test',
                'author_email': 'test@example.com',
                'edge_id': 'edge-001',
                'original_command_id': 1
            })
            self.assertEqual(response.status_code, 401)

            # 測試有 token 的請求
            response = client.post(
                '/api/cloud/shared_commands/upload',
                json={
                    'name': 'Test Command',
                    'description': 'Test',
                    'category': 'test',
                    'content': '[]',
                    'author_username': 'test',
                    'author_email': 'test@example.com',
                    'edge_id': 'edge-001',
                    'original_command_id': 1
                },
                headers={'Authorization': f'Bearer {token}'}
            )
            # 因為 get_service() mock，可能會成功
            self.assertIn(response.status_code, [200, 201])

    @patch('Cloud.shared_commands.api.get_service')
    def test_rate_command_with_auth(self, mock_get_service):
        """測試評分需要認證"""
        from flask import Flask

        app = Flask(__name__)
        app.register_blueprint(shared_commands_bp)

        # 建立 mock 評分
        mock_rating = Mock()
        mock_rating.to_dict.return_value = {"id": 1, "rating": 5}

        mock_service = Mock()
        mock_service.rate_command.return_value = mock_rating
        mock_get_service.return_value = mock_service

        with app.test_client() as client:
            # 測試沒有 token 的請求
            response = client.post('/api/cloud/shared_commands/1/rate', json={
                'user_username': 'test',
                'rating': 5
            })
            self.assertEqual(response.status_code, 401)

            # 測試有效 token 的請求
            token = self.auth_service.generate_token(
                user_id="test-user",
                username="testuser"
            )
            response = client.post(
                '/api/cloud/shared_commands/1/rate',
                json={'user_username': 'test', 'rating': 5},
                headers={'Authorization': f'Bearer {token}'}
            )
            self.assertIn(response.status_code, [200, 201])

    @patch('Cloud.shared_commands.api.get_service')
    def test_download_command_with_auth(self, mock_get_service):
        """測試下載指令需要認證"""
        from flask import Flask

        app = Flask(__name__)
        app.register_blueprint(shared_commands_bp)

        # 建立 mock 指令
        mock_command = Mock()
        mock_command.to_dict.return_value = {"id": 1, "name": "test"}

        mock_service = Mock()
        mock_service.download_command.return_value = mock_command
        mock_get_service.return_value = mock_service

        with app.test_client() as client:
            # 測試沒有 token 的請求
            response = client.post('/api/cloud/shared_commands/1/download', json={
                'edge_id': 'edge-001'
            })
            self.assertEqual(response.status_code, 401)

    @patch('Cloud.shared_commands.api.get_service')
    def test_search_command_no_auth_required(self, mock_get_service):
        """測試搜尋指令不需要認證（公開端點）"""
        from flask import Flask

        app = Flask(__name__)
        app.register_blueprint(shared_commands_bp)

        mock_service = Mock()
        mock_service.search_commands.return_value = ([], 0)
        mock_get_service.return_value = mock_service

        with app.test_client() as client:
            # 測試沒有 token 也可以搜尋
            response = client.get('/api/cloud/shared_commands/search')
            self.assertEqual(response.status_code, 200)

    @patch('Cloud.shared_commands.api.get_service')
    def test_get_featured_commands_no_auth_required(self, mock_get_service):
        """測試取得精選指令不需要認證（公開端點）"""
        from flask import Flask

        app = Flask(__name__)
        app.register_blueprint(shared_commands_bp)

        mock_service = Mock()
        mock_service.get_featured_commands.return_value = []
        mock_get_service.return_value = mock_service

        with app.test_client() as client:
            # 測試沒有 token 也可以取得精選指令
            response = client.get('/api/cloud/shared_commands/featured')
            self.assertEqual(response.status_code, 200)


if __name__ == '__main__':
    unittest.main()
