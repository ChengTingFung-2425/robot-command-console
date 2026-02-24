"""
tests/cloud/test_user_management.py

測試 Cloud 用戶管理模組：
- CloudUser 資料模型（角色驗證、信任評分、Edge 身份連結）
- CloudUserService（CRUD、信任調整、身份連結）
- RBAC（has_permission、get_allowed_actions）
- Flask API 端點（require_role 裝飾器、各路由）
"""

import unittest
from flask import Flask

from Cloud.api.auth import CloudAuthService
from Cloud.user_management.models import (
    CloudUser,
    EdgeIdentity,
    TRUST_SCORE_MAX,
)
from Cloud.user_management.service import (
    CloudUserService,
    UserNotFoundError,
    UserAlreadyExistsError,
    InvalidRoleError,
)
from Cloud.user_management.rbac import has_permission, get_allowed_actions
from Cloud.user_management.api import user_mgmt_bp, init_user_management

JWT_SECRET = "test-secret-for-user-mgmt"


def _make_app(service, auth_service):
    """建立測試用 Flask 應用程式"""
    app = Flask(__name__)
    app.register_blueprint(user_mgmt_bp)
    init_user_management(service, auth_service)
    return app


class TestCloudUserModel(unittest.TestCase):
    """測試 CloudUser 資料模型"""

    def test_create_valid_user(self):
        """建立有效用戶"""
        user = CloudUser(user_id="u1", username="alice", email="alice@example.com", role="operator")
        self.assertEqual(user.username, "alice")
        self.assertEqual(user.role, "operator")
        self.assertEqual(user.trust_score, 50)
        self.assertTrue(user.is_active)

    def test_invalid_role_raises(self):
        """無效角色應拋出 ValueError"""
        with self.assertRaises(ValueError):
            CloudUser(user_id="u2", username="bob", email="b@b.com", role="superuser")

    def test_trust_score_out_of_range_raises(self):
        """超出範圍的信任評分應拋出 ValueError"""
        with self.assertRaises(ValueError):
            CloudUser(user_id="u3", username="c", email="c@c.com", trust_score=101)
        with self.assertRaises(ValueError):
            CloudUser(user_id="u4", username="d", email="d@d.com", trust_score=-1)

    def test_has_role(self):
        """has_role 應正確比較層級"""
        admin = CloudUser(user_id="a", username="a", email="a@a.com", role="admin")
        viewer = CloudUser(user_id="v", username="v", email="v@v.com", role="viewer")
        self.assertTrue(admin.has_role("viewer"))
        self.assertTrue(admin.has_role("admin"))
        self.assertFalse(viewer.has_role("operator"))

    def test_edge_identity_link(self):
        """get_linked_edge 應能找到已連結的 Edge"""
        user = CloudUser(user_id="u5", username="e", email="e@e.com")
        user.edge_identities.append(EdgeIdentity(edge_id="edge-1", edge_user_id="local-99"))
        found = user.get_linked_edge("edge-1")
        self.assertIsNotNone(found)
        self.assertEqual(found.edge_user_id, "local-99")
        self.assertIsNone(user.get_linked_edge("edge-999"))

    def test_to_dict(self):
        """to_dict 應包含所有必要欄位"""
        user = CloudUser(user_id="u6", username="f", email="f@f.com", role="auditor")
        d = user.to_dict()
        for key in ("user_id", "username", "email", "role", "trust_score", "is_active",
                    "created_at", "updated_at", "edge_identities"):
            self.assertIn(key, d)


class TestCloudUserService(unittest.TestCase):
    """測試 CloudUserService 業務邏輯"""

    def setUp(self):
        self.auth = CloudAuthService(JWT_SECRET)
        self.svc = CloudUserService(self.auth)

    def test_create_and_get_user(self):
        """建立用戶後可依 ID 取得"""
        user = self.svc.create_user("alice", "alice@example.com", role="operator")
        fetched = self.svc.get_user(user.user_id)
        self.assertEqual(fetched.username, "alice")

    def test_duplicate_username_raises(self):
        """重複 username 應拋出 UserAlreadyExistsError"""
        self.svc.create_user("dup", "dup@example.com")
        with self.assertRaises(UserAlreadyExistsError):
            self.svc.create_user("dup", "dup2@example.com")

    def test_invalid_role_raises(self):
        """無效角色應拋出 InvalidRoleError"""
        with self.assertRaises(InvalidRoleError):
            self.svc.create_user("bad", "bad@example.com", role="superadmin")

    def test_get_nonexistent_user_raises(self):
        """取得不存在用戶應拋出 UserNotFoundError"""
        with self.assertRaises(UserNotFoundError):
            self.svc.get_user("nonexistent-id")

    def test_get_user_by_username(self):
        """依 username 查詢"""
        self.svc.create_user("byname", "bn@example.com")
        found = self.svc.get_user_by_username("byname")
        self.assertIsNotNone(found)
        self.assertIsNone(self.svc.get_user_by_username("nobody"))

    def test_list_users(self):
        """list_users 應回傳所有用戶"""
        self.svc.create_user("u1", "u1@e.com")
        self.svc.create_user("u2", "u2@e.com")
        users = self.svc.list_users()
        self.assertGreaterEqual(len(users), 2)

    def test_list_active_only(self):
        """active_only=True 應過濾停用用戶"""
        u = self.svc.create_user("inactive", "i@e.com")
        self.svc.deactivate_user(u.user_id)
        active = self.svc.list_users(active_only=True)
        ids = [x.user_id for x in active]
        self.assertNotIn(u.user_id, ids)

    def test_update_role(self):
        """更新角色"""
        user = self.svc.create_user("ruser", "r@e.com", role="viewer")
        updated = self.svc.update_role(user.user_id, "admin")
        self.assertEqual(updated.role, "admin")

    def test_deactivate_user(self):
        """停用用戶後 is_active 為 False"""
        user = self.svc.create_user("duser", "d@e.com")
        self.svc.deactivate_user(user.user_id)
        self.assertFalse(self.svc.get_user(user.user_id).is_active)

    def test_adjust_trust_score(self):
        """信任評分調整"""
        user = self.svc.create_user("tuser", "t@e.com", trust_score=50)
        updated, delta = self.svc.adjust_trust_score(user.user_id, 20)
        self.assertEqual(updated.trust_score, 70)
        self.assertEqual(delta, 20)

    def test_trust_score_clamped(self):
        """信任評分應被箝制在 [0, 100]"""
        user = self.svc.create_user("cuser", "c@e.com", trust_score=95)
        updated, delta = self.svc.adjust_trust_score(user.user_id, 20)
        self.assertEqual(updated.trust_score, TRUST_SCORE_MAX)
        self.assertEqual(delta, 5)

    def test_link_and_unlink_edge(self):
        """連結與解除 Edge 身份"""
        user = self.svc.create_user("euser", "e@e.com")
        self.svc.link_edge_identity(user.user_id, "edge-001", "local-123")
        fetched = self.svc.get_user(user.user_id)
        self.assertIsNotNone(fetched.get_linked_edge("edge-001"))

        self.svc.unlink_edge_identity(user.user_id, "edge-001")
        self.assertIsNone(self.svc.get_user(user.user_id).get_linked_edge("edge-001"))

    def test_unlink_nonexistent_edge_raises(self):
        """解除未連結的 Edge 應拋出 ValueError"""
        user = self.svc.create_user("noedge", "ne@e.com")
        with self.assertRaises(ValueError):
            self.svc.unlink_edge_identity(user.user_id, "edge-999")

    def test_generate_token(self):
        """應為活躍用戶產生有效 JWT"""
        user = self.svc.create_user("tokenuser", "tok@e.com")
        token = self.svc.generate_token(user.user_id)
        payload = self.auth.verify_token(token)
        self.assertIsNotNone(payload)
        self.assertEqual(payload["user_id"], user.user_id)
        self.assertEqual(payload["role"], user.role)

    def test_generate_token_deactivated_raises(self):
        """停用用戶不應能產生 Token"""
        user = self.svc.create_user("deaduser", "dead@e.com")
        self.svc.deactivate_user(user.user_id)
        with self.assertRaises(UserNotFoundError):
            self.svc.generate_token(user.user_id)


class TestRBAC(unittest.TestCase):
    """測試 RBAC 權限檢查函式"""

    def test_admin_has_all_permissions(self):
        """admin 應擁有所有操作的權限"""
        from Cloud.user_management.rbac import PERMISSION_MAP
        for action in PERMISSION_MAP:
            self.assertTrue(has_permission("admin", action), f"admin missing: {action}")

    def test_viewer_limited_permissions(self):
        """viewer 只有讀取類操作"""
        self.assertTrue(has_permission("viewer", "user.read"))
        self.assertFalse(has_permission("viewer", "user.update_role"))
        self.assertFalse(has_permission("viewer", "command.execute"))

    def test_operator_can_execute(self):
        """operator 可以執行指令與連結 Edge"""
        self.assertTrue(has_permission("operator", "command.execute"))
        self.assertTrue(has_permission("operator", "edge.link"))
        self.assertFalse(has_permission("operator", "user.update_role"))

    def test_auditor_can_read_audit(self):
        """auditor 可以讀取審計日誌"""
        self.assertTrue(has_permission("auditor", "audit.read"))
        self.assertFalse(has_permission("auditor", "user.update_role"))

    def test_unknown_action_returns_false(self):
        """未知操作應回傳 False"""
        self.assertFalse(has_permission("admin", "unknown.action"))

    def test_get_allowed_actions(self):
        """get_allowed_actions 應回傳對應角色的允許操作集合"""
        admin_actions = get_allowed_actions("admin")
        viewer_actions = get_allowed_actions("viewer")
        self.assertGreater(len(admin_actions), len(viewer_actions))
        self.assertIn("user.update_role", admin_actions)
        self.assertNotIn("user.update_role", viewer_actions)


class TestUserManagementAPI(unittest.TestCase):
    """測試 Flask API 端點"""

    def setUp(self):
        self.auth = CloudAuthService(JWT_SECRET)
        self.svc = CloudUserService(self.auth)
        self.app = _make_app(self.svc, self.auth)
        self.client = self.app.test_client()

        # 預建用戶
        self.admin = self.svc.create_user("admin_user", "admin@e.com", role="admin")
        self.operator = self.svc.create_user("op_user", "op@e.com", role="operator")
        self.viewer = self.svc.create_user("view_user", "view@e.com", role="viewer")

        # 產生對應 Token
        self.admin_token = self.svc.generate_token(self.admin.user_id)
        self.op_token = self.svc.generate_token(self.operator.user_id)
        self.viewer_token = self.svc.generate_token(self.viewer.user_id)

    def _auth_header(self, token):
        return {"Authorization": f"Bearer {token}"}

    # --- /me ---

    def test_get_me_success(self):
        """GET /me 應回傳自己的資訊"""
        resp = self.client.get("/api/cloud/users/me", headers=self._auth_header(self.viewer_token))
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["user"]["username"], "view_user")

    def test_get_me_no_token(self):
        """GET /me 無 token 應回傳 401"""
        resp = self.client.get("/api/cloud/users/me")
        self.assertEqual(resp.status_code, 401)

    def test_get_me_invalid_token(self):
        """GET /me 使用格式錯誤的 token 應回傳 401"""
        resp = self.client.get("/api/cloud/users/me", headers={"Authorization": "Bearer not.a.valid.jwt"})
        self.assertEqual(resp.status_code, 401)

    def test_get_me_wrong_secret_token(self):
        """GET /me 使用不同密鑰簽署的 token 應回傳 401"""
        other_auth = CloudAuthService("wrong-secret")
        bad_token = other_auth.generate_token("x", "x", "viewer")
        resp = self.client.get("/api/cloud/users/me", headers=self._auth_header(bad_token))
        self.assertEqual(resp.status_code, 401)

    # --- POST / (create user) ---

    def test_create_user_as_admin(self):
        """admin 可建立新用戶"""
        resp = self.client.post(
            "/api/cloud/users",
            json={"username": "newbie", "email": "newbie@e.com", "role": "viewer"},
            headers=self._auth_header(self.admin_token),
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.get_json()["user"]["username"], "newbie")

    def test_create_user_forbidden_for_operator(self):
        """operator 不可建立用戶（需 admin）"""
        resp = self.client.post(
            "/api/cloud/users",
            json={"username": "x", "email": "x@e.com"},
            headers=self._auth_header(self.op_token),
        )
        self.assertEqual(resp.status_code, 403)

    def test_create_user_conflict(self):
        """重複 username 應回傳 409"""
        resp = self.client.post(
            "/api/cloud/users",
            json={"username": "admin_user", "email": "another@e.com"},
            headers=self._auth_header(self.admin_token),
        )
        self.assertEqual(resp.status_code, 409)

    def test_create_user_missing_fields(self):
        """缺少必要欄位應回傳 400"""
        resp = self.client.post(
            "/api/cloud/users",
            json={"username": "onlyname"},
            headers=self._auth_header(self.admin_token),
        )
        self.assertEqual(resp.status_code, 400)

    # --- GET /<user_id> ---

    def test_get_own_user_as_viewer(self):
        """viewer 可查自己"""
        resp = self.client.get(
            f"/api/cloud/users/{self.viewer.user_id}",
            headers=self._auth_header(self.viewer_token),
        )
        self.assertEqual(resp.status_code, 200)

    def test_get_other_user_forbidden_for_viewer(self):
        """viewer 不可查他人"""
        resp = self.client.get(
            f"/api/cloud/users/{self.admin.user_id}",
            headers=self._auth_header(self.viewer_token),
        )
        self.assertEqual(resp.status_code, 403)

    def test_get_any_user_as_admin(self):
        """admin 可查所有人"""
        resp = self.client.get(
            f"/api/cloud/users/{self.viewer.user_id}",
            headers=self._auth_header(self.admin_token),
        )
        self.assertEqual(resp.status_code, 200)

    # --- PUT /<user_id>/role ---

    def test_update_role_as_admin(self):
        """admin 可更新角色"""
        resp = self.client.put(
            f"/api/cloud/users/{self.viewer.user_id}/role",
            json={"role": "operator"},
            headers=self._auth_header(self.admin_token),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["user"]["role"], "operator")

    def test_update_role_forbidden_for_operator(self):
        """operator 不可更新角色"""
        resp = self.client.put(
            f"/api/cloud/users/{self.viewer.user_id}/role",
            json={"role": "admin"},
            headers=self._auth_header(self.op_token),
        )
        self.assertEqual(resp.status_code, 403)

    # --- POST /<user_id>/deactivate ---

    def test_deactivate_user_as_admin(self):
        """admin 可停用用戶"""
        target = self.svc.create_user("todelete", "td@e.com")
        resp = self.client.post(
            f"/api/cloud/users/{target.user_id}/deactivate",
            headers=self._auth_header(self.admin_token),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.get_json()["user"]["is_active"])

    # --- POST /<user_id>/trust ---

    def test_adjust_trust_as_admin(self):
        """admin 可調整信任評分"""
        resp = self.client.post(
            f"/api/cloud/users/{self.viewer.user_id}/trust",
            json={"delta": 15},
            headers=self._auth_header(self.admin_token),
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["actual_delta"], 15)
        self.assertEqual(data["user"]["trust_score"], 65)

    def test_adjust_trust_missing_delta(self):
        """缺少 delta 應回傳 400"""
        resp = self.client.post(
            f"/api/cloud/users/{self.viewer.user_id}/trust",
            json={},
            headers=self._auth_header(self.admin_token),
        )
        self.assertEqual(resp.status_code, 400)

    # --- Edge identity ---

    def test_link_edge_as_operator(self):
        """operator 可連結自己的 Edge 身份"""
        resp = self.client.post(
            f"/api/cloud/users/{self.operator.user_id}/edges",
            json={"edge_id": "edge-001", "edge_user_id": "local-xyz"},
            headers=self._auth_header(self.op_token),
        )
        self.assertEqual(resp.status_code, 200)
        identities = resp.get_json()["user"]["edge_identities"]
        self.assertEqual(len(identities), 1)
        self.assertEqual(identities[0]["edge_id"], "edge-001")

    def test_link_edge_forbidden_for_other_user(self):
        """operator 不可為他人連結 Edge"""
        resp = self.client.post(
            f"/api/cloud/users/{self.viewer.user_id}/edges",
            json={"edge_id": "edge-002", "edge_user_id": "local-abc"},
            headers=self._auth_header(self.op_token),
        )
        self.assertEqual(resp.status_code, 403)

    def test_unlink_edge(self):
        """連結後可解除"""
        self.svc.link_edge_identity(self.operator.user_id, "edge-del", "local-del")
        resp = self.client.delete(
            f"/api/cloud/users/{self.operator.user_id}/edges/edge-del",
            headers=self._auth_header(self.op_token),
        )
        self.assertEqual(resp.status_code, 200)

    # --- POST /<user_id>/token ---

    def test_generate_token_as_admin(self):
        """admin 可為用戶產生 Token"""
        resp = self.client.post(
            f"/api/cloud/users/{self.operator.user_id}/token",
            json={"expires_in": 3600},
            headers=self._auth_header(self.admin_token),
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("token", data)
        payload = self.auth.verify_token(data["token"])
        self.assertIsNotNone(payload)
        self.assertEqual(payload["user_id"], self.operator.user_id)

    # --- GET / (list users) ---

    def test_list_users_as_auditor(self):
        """auditor 可列出用戶"""
        auditor = self.svc.create_user("auditor_u", "aud@e.com", role="auditor")
        aud_token = self.svc.generate_token(auditor.user_id)
        resp = self.client.get("/api/cloud/users", headers=self._auth_header(aud_token))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("users", resp.get_json())

    def test_list_users_forbidden_for_operator(self):
        """operator 不可列出所有用戶"""
        resp = self.client.get("/api/cloud/users", headers=self._auth_header(self.op_token))
        self.assertEqual(resp.status_code, 403)


if __name__ == "__main__":
    unittest.main()
