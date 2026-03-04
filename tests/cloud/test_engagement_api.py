"""
測試 Cloud engagement API 認證與公開端點行為
"""

import unittest
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from Cloud.api.auth import CloudAuthService
from Cloud.engagement.api import bp


def _make_app(jwt_secret: str = "test-secret-key"):
    """建立測試用 Flask app"""
    from flask import Flask
    app = Flask(__name__)
    app.register_blueprint(bp)
    return app


class TestEngagementAPIAuth(unittest.TestCase):
    """測試 Engagement API JWT 認證行為"""

    def setUp(self):
        """初始化測試"""
        self.jwt_secret = "test-secret-key"
        self.auth_service = CloudAuthService(self.jwt_secret)
        self.app = _make_app(self.jwt_secret)

        # 注入 auth_service，不初始化 DB
        import Cloud.engagement.api as api_module
        api_module.auth_service = self.auth_service

    def _valid_token(self, username: str = "testuser") -> str:
        return self.auth_service.generate_token(
            user_id="test-uid",
            username=username,
            role="user",
        )

    # ──────────────────────────────
    # GET 端點（公開，不需 token）
    # ──────────────────────────────

    @patch('Cloud.engagement.api.get_service')
    def test_get_profile_no_token(self, mock_get_service):
        """GET profile 端點不需 token"""
        mock_profile = MagicMock()
        mock_profile.to_dict.return_value = {"username": "alice", "points": 100}

        @contextmanager
        def _ctx():
            svc = MagicMock()
            svc.get_profile.return_value = mock_profile
            yield svc

        mock_get_service.side_effect = _ctx

        with self.app.test_client() as client:
            resp = client.get('/api/cloud/engagement/profile/alice')
            self.assertEqual(resp.status_code, 200)

    @patch('Cloud.engagement.api.get_service')
    def test_get_leaderboard_no_token(self, mock_get_service):
        """GET leaderboard 端點不需 token"""
        @contextmanager
        def _ctx():
            svc = MagicMock()
            svc.get_leaderboard.return_value = []
            yield svc

        mock_get_service.side_effect = _ctx

        with self.app.test_client() as client:
            resp = client.get('/api/cloud/engagement/leaderboard')
            self.assertEqual(resp.status_code, 200)

    @patch('Cloud.engagement.api.get_service')
    def test_get_posts_no_token(self, mock_get_service):
        """GET posts 端點不需 token"""
        @contextmanager
        def _ctx():
            svc = MagicMock()
            svc.list_posts.return_value = ([], 0)
            yield svc

        mock_get_service.side_effect = _ctx

        with self.app.test_client() as client:
            resp = client.get('/api/cloud/engagement/posts')
            self.assertEqual(resp.status_code, 200)

    @patch('Cloud.engagement.api.get_service')
    def test_get_post_detail_no_token(self, mock_get_service):
        """GET post detail 端點不需 token"""
        mock_post = MagicMock()
        mock_post.to_dict.return_value = {"id": 1, "title": "Test"}

        @contextmanager
        def _ctx():
            svc = MagicMock()
            svc.get_post.return_value = mock_post
            yield svc

        mock_get_service.side_effect = _ctx

        with self.app.test_client() as client:
            resp = client.get('/api/cloud/engagement/posts/1')
            self.assertEqual(resp.status_code, 200)

    @patch('Cloud.engagement.api.get_service')
    def test_get_comments_no_token(self, mock_get_service):
        """GET comments 端點不需 token"""
        @contextmanager
        def _ctx():
            svc = MagicMock()
            svc.get_post.return_value = MagicMock()
            svc.get_comments.return_value = []
            yield svc

        mock_get_service.side_effect = _ctx

        with self.app.test_client() as client:
            resp = client.get('/api/cloud/engagement/posts/1/comments')
            self.assertEqual(resp.status_code, 200)

    # ──────────────────────────────
    # POST/DELETE 端點（需要認證）
    # ──────────────────────────────

    def test_create_post_no_token_returns_401(self):
        """POST /posts 缺少 token 應回 401"""
        with self.app.test_client() as client:
            resp = client.post('/api/cloud/engagement/posts', json={
                'title': 'Hello',
                'body': 'World',
            })
            self.assertEqual(resp.status_code, 401)

    def test_create_post_invalid_token_returns_401(self):
        """POST /posts 無效 token 應回 401"""
        with self.app.test_client() as client:
            resp = client.post(
                '/api/cloud/engagement/posts',
                json={'title': 'Hello', 'body': 'World'},
                headers={'Authorization': 'Bearer invalid.token.here'},
            )
            self.assertEqual(resp.status_code, 401)

    def test_delete_post_no_token_returns_401(self):
        """DELETE /posts/<id> 缺少 token 應回 401"""
        with self.app.test_client() as client:
            resp = client.delete('/api/cloud/engagement/posts/1')
            self.assertEqual(resp.status_code, 401)

    def test_add_comment_no_token_returns_401(self):
        """POST /posts/<id>/comments 缺少 token 應回 401"""
        with self.app.test_client() as client:
            resp = client.post('/api/cloud/engagement/posts/1/comments', json={
                'content': 'Great post!',
            })
            self.assertEqual(resp.status_code, 401)

    def test_like_post_no_token_returns_401(self):
        """POST /posts/<id>/like 缺少 token 應回 401"""
        with self.app.test_client() as client:
            resp = client.post('/api/cloud/engagement/posts/1/like')
            self.assertEqual(resp.status_code, 401)

    # ──────────────────────────────
    # auth_service 未初始化時的行為
    # ──────────────────────────────

    def test_create_post_auth_service_none_returns_503(self):
        """POST /posts 在 auth_service 未初始化時應回 503"""
        import Cloud.engagement.api as api_module
        original = api_module.auth_service
        try:
            api_module.auth_service = None
            with self.app.test_client() as client:
                resp = client.post('/api/cloud/engagement/posts', json={
                    'title': 'Hello',
                    'body': 'World',
                })
                self.assertEqual(resp.status_code, 503)
        finally:
            api_module.auth_service = original

    def test_delete_post_auth_service_none_returns_503(self):
        """DELETE /posts/<id> 在 auth_service 未初始化時應回 503"""
        import Cloud.engagement.api as api_module
        original = api_module.auth_service
        try:
            api_module.auth_service = None
            with self.app.test_client() as client:
                resp = client.delete('/api/cloud/engagement/posts/1')
                self.assertEqual(resp.status_code, 503)
        finally:
            api_module.auth_service = original

    def test_add_comment_auth_service_none_returns_503(self):
        """POST /posts/<id>/comments 在 auth_service 未初始化時應回 503"""
        import Cloud.engagement.api as api_module
        original = api_module.auth_service
        try:
            api_module.auth_service = None
            with self.app.test_client() as client:
                resp = client.post('/api/cloud/engagement/posts/1/comments', json={
                    'content': 'Test',
                })
                self.assertEqual(resp.status_code, 503)
        finally:
            api_module.auth_service = original

    def test_like_post_auth_service_none_returns_503(self):
        """POST /posts/<id>/like 在 auth_service 未初始化時應回 503"""
        import Cloud.engagement.api as api_module
        original = api_module.auth_service
        try:
            api_module.auth_service = None
            with self.app.test_client() as client:
                resp = client.post('/api/cloud/engagement/posts/1/like')
                self.assertEqual(resp.status_code, 503)
        finally:
            api_module.auth_service = original

    # ──────────────────────────────
    # parent_comment_id 型別驗證
    # ──────────────────────────────

    @patch('Cloud.engagement.api.get_service')
    def test_add_comment_invalid_parent_id_returns_400(self, mock_get_service):
        """POST comments 傳入非整數 parent_comment_id 應回 400"""
        @contextmanager
        def _ctx():
            svc = MagicMock()
            svc.get_post.return_value = MagicMock()
            yield svc

        mock_get_service.side_effect = _ctx

        token = self._valid_token()
        with self.app.test_client() as client:
            resp = client.post(
                '/api/cloud/engagement/posts/1/comments',
                json={'content': 'Hi', 'parent_comment_id': 'not-a-number'},
                headers={'Authorization': f'Bearer {token}'},
            )
            self.assertEqual(resp.status_code, 400)
            data = resp.get_json()
            self.assertIn('parent_comment_id', data.get('message', ''))

    @patch('Cloud.engagement.api.get_service')
    def test_add_comment_null_parent_id_ok(self, mock_get_service):
        """POST comments parent_comment_id 為 null 應正常處理"""
        mock_comment = MagicMock()
        mock_comment.to_dict.return_value = {"id": 1, "content": "Hi"}

        @contextmanager
        def _ctx():
            svc = MagicMock()
            svc.get_post.return_value = MagicMock()
            svc.add_comment.return_value = mock_comment
            svc.award_points.return_value = None
            yield svc

        mock_get_service.side_effect = _ctx

        token = self._valid_token()
        with self.app.test_client() as client:
            resp = client.post(
                '/api/cloud/engagement/posts/1/comments',
                json={'content': 'Hi', 'parent_comment_id': None},
                headers={'Authorization': f'Bearer {token}'},
            )
            self.assertEqual(resp.status_code, 201)


if __name__ == '__main__':
    unittest.main()
