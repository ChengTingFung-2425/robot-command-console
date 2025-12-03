"""
測試認證授權合規性
驗證 JWT Token 檢查、審計日誌和錯誤處理
"""

import sys
import os
import unittest
import asyncio
from uuid import uuid4

# 添加 MCP 目錄到路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from MCP.auth_manager import AuthManager  # noqa: E402
from MCP.logging_monitor import LoggingMonitor  # noqa: E402
from MCP.models import (  # noqa: E402
    EventCategory,
)


class TestAuthManager(unittest.TestCase):
    """測試 AuthManager 功能"""

    def setUp(self):
        """設定測試環境"""
        self.logging_monitor = LoggingMonitor()
        self.auth_manager = AuthManager(logging_monitor=self.logging_monitor)

        # 建立事件迴圈
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        """清理測試環境"""
        self.loop.close()

    def test_register_user(self):
        """測試用戶註冊"""
        result = self.loop.run_until_complete(
            self.auth_manager.register_user(
                user_id="user-123",
                username="testuser",
                password="testpass123",
                role="operator"
            )
        )

        self.assertTrue(result)
        self.assertIn("user-123", self.auth_manager.users)

        user = self.auth_manager.users["user-123"]
        self.assertEqual(user["username"], "testuser")
        self.assertEqual(user["role"], "operator")
        self.assertIsNotNone(user["password_hash"])

    def test_register_duplicate_user(self):
        """測試重複註冊用戶"""
        self.loop.run_until_complete(
            self.auth_manager.register_user(
                user_id="user-456",
                username="duplicate",
                password="pass123",
                role="viewer"
            )
        )

        # 嘗試重複註冊
        result = self.loop.run_until_complete(
            self.auth_manager.register_user(
                user_id="user-456",
                username="duplicate2",
                password="pass456",
                role="operator"
            )
        )

        self.assertFalse(result)

    def test_authenticate_user(self):
        """測試用戶認證"""
        self.loop.run_until_complete(
            self.auth_manager.register_user(
                user_id="user-789",
                username="authuser",
                password="correctpass",
                role="admin"
            )
        )

        # 正確密碼
        user_id = self.loop.run_until_complete(
            self.auth_manager.authenticate_user("authuser", "correctpass")
        )
        self.assertEqual(user_id, "user-789")

        # 錯誤密碼
        user_id = self.loop.run_until_complete(
            self.auth_manager.authenticate_user("authuser", "wrongpass")
        )
        self.assertIsNone(user_id)

        # 不存在的用戶
        user_id = self.loop.run_until_complete(
            self.auth_manager.authenticate_user("nonexistent", "anypass")
        )
        self.assertIsNone(user_id)

    def test_create_token(self):
        """測試創建 Token"""
        token = self.loop.run_until_complete(
            self.auth_manager.create_token(
                user_id="user-999",
                role="operator",
                expires_in_hours=1
            )
        )

        self.assertIsNotNone(token)
        self.assertIsInstance(token, str)
        self.assertGreater(len(token), 0)

    def test_verify_valid_token(self):
        """測試驗證有效 Token"""
        # 創建 token
        token = self.loop.run_until_complete(
            self.auth_manager.create_token(
                user_id="user-valid",
                role="operator",
                expires_in_hours=1
            )
        )

        # 驗證 token
        trace_id = str(uuid4())
        is_valid = self.loop.run_until_complete(
            self.auth_manager.verify_token(token, trace_id=trace_id)
        )

        self.assertTrue(is_valid)

    def test_verify_expired_token(self):
        """測試驗證過期 Token"""
        # 創建過期 token（已過期）
        token = self.loop.run_until_complete(
            self.auth_manager.create_token(
                user_id="user-expired",
                role="viewer",
                expires_in_hours=-1  # 負數小時 = 已過期
            )
        )

        # 驗證 token
        trace_id = str(uuid4())
        is_valid = self.loop.run_until_complete(
            self.auth_manager.verify_token(token, trace_id=trace_id)
        )

        self.assertFalse(is_valid)

        # 檢查是否記錄了審計事件
        events = self.loop.run_until_complete(
            self.logging_monitor.get_events(trace_id=trace_id)
        )
        self.assertGreater(len(events), 0)

    def test_verify_invalid_token(self):
        """測試驗證無效 Token"""
        invalid_token = "invalid.token.string"
        trace_id = str(uuid4())

        is_valid = self.loop.run_until_complete(
            self.auth_manager.verify_token(invalid_token, trace_id=trace_id)
        )

        self.assertFalse(is_valid)

        # 檢查是否記錄了審計事件
        events = self.loop.run_until_complete(
            self.logging_monitor.get_events(trace_id=trace_id)
        )
        self.assertGreater(len(events), 0)

    def test_check_permission_admin(self):
        """測試管理員權限檢查"""
        self.loop.run_until_complete(
            self.auth_manager.register_user(
                user_id="admin-user",
                username="admin",
                password="adminpass",
                role="admin"
            )
        )

        # Admin 應該有所有權限
        has_perm = self.loop.run_until_complete(
            self.auth_manager.check_permission(
                user_id="admin-user",
                action="robot.move",
                resource="robot_1"
            )
        )
        self.assertTrue(has_perm)

        has_perm = self.loop.run_until_complete(
            self.auth_manager.check_permission(
                user_id="admin-user",
                action="any.action",
                resource="any_resource"
            )
        )
        self.assertTrue(has_perm)

    def test_check_permission_operator(self):
        """測試操作員權限檢查"""
        self.loop.run_until_complete(
            self.auth_manager.register_user(
                user_id="operator-user",
                username="operator",
                password="operpass",
                role="operator"
            )
        )

        # Operator 應該有 robot.move 權限
        has_perm = self.loop.run_until_complete(
            self.auth_manager.check_permission(
                user_id="operator-user",
                action="robot.move",
                resource="robot_1"
            )
        )
        self.assertTrue(has_perm)

        # Operator 應該有 robot.stop 權限
        has_perm = self.loop.run_until_complete(
            self.auth_manager.check_permission(
                user_id="operator-user",
                action="robot.stop",
                resource="robot_1"
            )
        )
        self.assertTrue(has_perm)

    def test_check_permission_viewer(self):
        """測試觀察者權限檢查"""
        self.loop.run_until_complete(
            self.auth_manager.register_user(
                user_id="viewer-user",
                username="viewer",
                password="viewpass",
                role="viewer"
            )
        )

        # Viewer 應該有 robot.status 權限
        has_perm = self.loop.run_until_complete(
            self.auth_manager.check_permission(
                user_id="viewer-user",
                action="robot.status",
                resource="robot_1"
            )
        )
        self.assertTrue(has_perm)

        # Viewer 不應該有 robot.move 權限
        has_perm = self.loop.run_until_complete(
            self.auth_manager.check_permission(
                user_id="viewer-user",
                action="robot.move",
                resource="robot_1"
            )
        )
        self.assertFalse(has_perm)

    def test_check_permission_nonexistent_user(self):
        """測試不存在用戶的權限檢查"""
        has_perm = self.loop.run_until_complete(
            self.auth_manager.check_permission(
                user_id="nonexistent",
                action="robot.status",
                resource="robot_1"
            )
        )

        self.assertFalse(has_perm)

    def test_audit_logging_on_auth_failure(self):
        """測試認證失敗時的審計日誌"""
        trace_id = str(uuid4())

        # 驗證無效 token
        invalid_token = "totally.invalid.token"
        self.loop.run_until_complete(
            self.auth_manager.verify_token(invalid_token, trace_id=trace_id)
        )

        # 檢查審計事件
        events = self.loop.run_until_complete(
            self.logging_monitor.get_events(
                trace_id=trace_id,
                category=EventCategory.AUDIT
            )
        )

        self.assertGreater(len(events), 0)

        # 驗證事件內容
        audit_event = events[0]
        self.assertEqual(audit_event.category, EventCategory.AUDIT)
        self.assertEqual(audit_event.trace_id, trace_id)
        self.assertIn("token", audit_event.message.lower())


class TestAuthIntegration(unittest.TestCase):
    """測試認證整合場景"""

    def setUp(self):
        """設定測試環境"""
        self.logging_monitor = LoggingMonitor()
        self.auth_manager = AuthManager(logging_monitor=self.logging_monitor)
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        """清理測試環境"""
        self.loop.close()

    def test_full_auth_flow(self):
        """測試完整的認證流程"""
        trace_id = str(uuid4())

        # 1. 註冊用戶
        register_result = self.loop.run_until_complete(
            self.auth_manager.register_user(
                user_id="flow-user",
                username="flowuser",
                password="flowpass123",
                role="operator"
            )
        )
        self.assertTrue(register_result)

        # 2. 認證用戶
        user_id = self.loop.run_until_complete(
            self.auth_manager.authenticate_user("flowuser", "flowpass123")
        )
        self.assertEqual(user_id, "flow-user")

        # 3. 創建 token
        token = self.loop.run_until_complete(
            self.auth_manager.create_token(
                user_id=user_id,
                role="operator"
            )
        )
        self.assertIsNotNone(token)

        # 4. 驗證 token
        is_valid = self.loop.run_until_complete(
            self.auth_manager.verify_token(token, trace_id=trace_id)
        )
        self.assertTrue(is_valid)

        # 5. 檢查權限
        has_perm = self.loop.run_until_complete(
            self.auth_manager.check_permission(
                user_id=user_id,
                action="robot.move",
                resource="robot_1"
            )
        )
        self.assertTrue(has_perm)

    def test_auth_failure_flow(self):
        """測試認證失敗流程"""
        trace_id = str(uuid4())

        # 1. 嘗試用錯誤密碼認證
        user_id = self.loop.run_until_complete(
            self.auth_manager.authenticate_user("nonexistent", "wrongpass")
        )
        self.assertIsNone(user_id)

        # 2. 使用無效 token
        is_valid = self.loop.run_until_complete(
            self.auth_manager.verify_token("invalid.token", trace_id=trace_id)
        )
        self.assertFalse(is_valid)

        # 3. 檢查審計日誌
        events = self.loop.run_until_complete(
            self.logging_monitor.get_events(trace_id=trace_id)
        )
        self.assertGreater(len(events), 0)


if __name__ == '__main__':
    unittest.main()
