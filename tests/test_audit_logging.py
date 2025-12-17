"""
測試審計日誌功能

包括：
- 審計日誌記錄
- 審計日誌查詢
- 權限控管
- CSV 匯出
"""

import unittest
import sys
import os

# 添加專案根目錄到路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# noqa: E402 - imports after sys.path modification
from WebUI.app import create_app, db  # noqa: E402
from WebUI.app.models import User, AuditLog  # noqa: E402
from WebUI.app.audit import (  # noqa: E402
    log_audit_event, log_login_attempt, log_logout,
    log_registration, log_password_reset_request,
    AuditAction, AuditSeverity, AuditCategory, AuditStatus
)


class TestAuditLogging(unittest.TestCase):
    """測試審計日誌記錄功能"""

    def setUp(self):
        """設定測試環境"""
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        db.create_all()

        # 建立測試使用者
        self.test_user = User(username='testuser', email='test@example.com', role='operator')
        self.test_user.set_password('password123')
        db.session.add(self.test_user)

        self.admin_user = User(username='admin', email='admin@example.com', role='admin')
        self.admin_user.set_password('admin123')
        db.session.add(self.admin_user)

        self.auditor_user = User(username='auditor', email='auditor@example.com', role='auditor')
        self.auditor_user.set_password('auditor123')
        db.session.add(self.auditor_user)

        db.session.commit()

    def tearDown(self):
        """清理測試環境"""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_log_audit_event_creates_entry(self):
        """測試建立審計日誌條目"""
        with self.app.test_request_context():
            log = log_audit_event(
                action=AuditAction.LOGIN_SUCCESS,
                message="Test audit log",
                user_id=self.test_user.id
            )

            self.assertIsNotNone(log)
            self.assertEqual(log.action, AuditAction.LOGIN_SUCCESS)
            self.assertEqual(log.message, "Test audit log")
            self.assertEqual(log.user_id, self.test_user.id)
            self.assertEqual(log.severity, AuditSeverity.INFO)
            self.assertEqual(log.category, AuditCategory.AUDIT)

    def test_log_login_success(self):
        """測試記錄成功登入"""
        with self.app.test_request_context():
            log_login_attempt(username='testuser', success=True, user_id=self.test_user.id)

            logs = AuditLog.query.filter_by(action=AuditAction.LOGIN_SUCCESS).all()
            self.assertEqual(len(logs), 1)
            self.assertEqual(logs[0].user_id, self.test_user.id)
            self.assertEqual(logs[0].status, AuditStatus.SUCCESS)

    def test_log_login_failure(self):
        """測試記錄失敗登入"""
        with self.app.test_request_context():
            log_login_attempt(username='wronguser', success=False)

            logs = AuditLog.query.filter_by(action=AuditAction.LOGIN_FAILURE).all()
            self.assertEqual(len(logs), 1)
            self.assertIsNone(logs[0].user_id)
            self.assertEqual(logs[0].severity, AuditSeverity.WARN)
            self.assertEqual(logs[0].status, AuditStatus.FAILURE)

    def test_log_logout(self):
        """測試記錄登出"""
        with self.app.test_request_context():
            log_logout(user_id=self.test_user.id, username='testuser')

            logs = AuditLog.query.filter_by(action=AuditAction.LOGOUT).all()
            self.assertEqual(len(logs), 1)
            self.assertEqual(logs[0].user_id, self.test_user.id)

    def test_log_registration(self):
        """測試記錄註冊"""
        with self.app.test_request_context():
            log_registration(username='newuser', email='new@example.com', user_id=self.test_user.id)

            logs = AuditLog.query.filter_by(action=AuditAction.REGISTER).all()
            self.assertEqual(len(logs), 1)
            self.assertIn('newuser', logs[0].message)

    def test_log_password_reset(self):
        """測試記錄密碼重設請求"""
        with self.app.test_request_context():
            log_password_reset_request(email='test@example.com')

            logs = AuditLog.query.filter_by(action=AuditAction.PASSWORD_RESET_REQUEST).all()
            self.assertEqual(len(logs), 1)
            self.assertIn('test@example.com', logs[0].message)

    def test_audit_log_includes_ip_address(self):
        """測試審計日誌包含 IP 位址"""
        with self.app.test_request_context(environ_base={'REMOTE_ADDR': '192.168.1.100'}):
            log = log_audit_event(
                action=AuditAction.LOGIN_SUCCESS,
                message="Test with IP",
                user_id=self.test_user.id
            )

            self.assertEqual(log.ip_address, '192.168.1.100')

    def test_audit_log_includes_trace_id(self):
        """測試審計日誌包含 trace_id"""
        with self.app.test_request_context():
            log = log_audit_event(
                action=AuditAction.LOGIN_SUCCESS,
                message="Test",
                trace_id='test-trace-123'
            )

            self.assertEqual(log.trace_id, 'test-trace-123')

    def test_audit_log_to_dict(self):
        """測試審計日誌轉換為字典"""
        with self.app.test_request_context():
            log = log_audit_event(
                action=AuditAction.LOGIN_SUCCESS,
                message="Test",
                user_id=self.test_user.id,
                context={'key': 'value'}
            )

            log_dict = log.to_dict()
            self.assertIn('id', log_dict)
            self.assertIn('trace_id', log_dict)
            self.assertIn('username', log_dict)
            self.assertEqual(log_dict['username'], 'testuser')
            self.assertEqual(log_dict['context'], {'key': 'value'})


class TestAuditLogQueryInterface(unittest.TestCase):
    """測試審計日誌查詢介面"""

    def setUp(self):
        """設定測試環境"""
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        db.create_all()

        # 建立測試使用者
        self.operator_user = User(username='operator', email='op@example.com', role='operator')
        self.operator_user.set_password('password123')
        db.session.add(self.operator_user)

        self.admin_user = User(username='admin', email='admin@example.com', role='admin')
        self.admin_user.set_password('admin123')
        db.session.add(self.admin_user)

        self.auditor_user = User(username='auditor', email='auditor@example.com', role='auditor')
        self.auditor_user.set_password('auditor123')
        db.session.add(self.auditor_user)

        db.session.commit()

        # 建立測試審計日誌
        with self.app.test_request_context():
            for i in range(10):
                log_audit_event(
                    action=AuditAction.LOGIN_SUCCESS,
                    message=f"Test login {i}",
                    user_id=self.operator_user.id,
                    severity=AuditSeverity.INFO,
                    category=AuditCategory.AUTH
                )

    def tearDown(self):
        """清理測試環境"""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_operator_cannot_access_audit_logs(self):
        """測試 operator 無法訪問審計日誌"""
        # 登入 operator
        self.client.post('/login', data={
            'username': 'operator',
            'password': 'password123'
        }, follow_redirects=True)

        # 嘗試訪問審計日誌
        response = self.client.get('/audit_logs')
        self.assertEqual(response.status_code, 403)

    def test_admin_can_access_audit_logs(self):
        """測試 admin 可以訪問審計日誌"""
        # 登入 admin
        self.client.post('/login', data={
            'username': 'admin',
            'password': 'admin123'
        }, follow_redirects=True)

        # 訪問審計日誌
        response = self.client.get('/audit_logs')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Test login', response.data)

    def test_auditor_can_access_audit_logs(self):
        """測試 auditor 可以訪問審計日誌"""
        # 登入 auditor
        self.client.post('/login', data={
            'username': 'auditor',
            'password': 'auditor123'
        }, follow_redirects=True)

        # 訪問審計日誌
        response = self.client.get('/audit_logs')
        self.assertEqual(response.status_code, 200)

    def test_audit_log_filtering_by_severity(self):
        """測試按嚴重性過濾審計日誌"""
        # 建立不同嚴重性的日誌
        with self.app.test_request_context():
            log_audit_event(
                action=AuditAction.PERMISSION_DENIED,
                message="Permission denied",
                severity=AuditSeverity.WARN,
                category=AuditCategory.AUTH
            )

        # 登入 admin
        self.client.post('/login', data={
            'username': 'admin',
            'password': 'admin123'
        }, follow_redirects=True)

        # 過濾 WARN 級別
        response = self.client.get('/audit_logs?severity=WARN')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Permission denied', response.data)

    def test_audit_log_detail_page(self):
        """測試審計日誌詳情頁面"""
        # 登入 admin
        self.client.post('/login', data={
            'username': 'admin',
            'password': 'admin123'
        }, follow_redirects=True)

        # 取得第一個日誌
        log = AuditLog.query.first()
        self.assertIsNotNone(log)

        # 訪問詳情頁面
        response = self.client.get(f'/audit_logs/{log.id}')
        self.assertEqual(response.status_code, 200)
        self.assertIn(log.message.encode(), response.data)

    def test_audit_log_export_csv(self):
        """測試匯出審計日誌為 CSV"""
        # 登入 admin
        self.client.post('/login', data={
            'username': 'admin',
            'password': 'admin123'
        }, follow_redirects=True)

        # 匯出 CSV
        response = self.client.get('/audit_logs/export')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'text/csv; charset=utf-8')
        self.assertIn(b'Trace ID', response.data)
        self.assertIn(b'Test login', response.data)

    def test_operator_cannot_export_audit_logs(self):
        """測試 operator 無法匯出審計日誌"""
        # 登入 operator
        self.client.post('/login', data={
            'username': 'operator',
            'password': 'password123'
        }, follow_redirects=True)

        # 嘗試匯出
        response = self.client.get('/audit_logs/export')
        self.assertEqual(response.status_code, 403)


class TestAuditLogIntegration(unittest.TestCase):
    """測試審計日誌整合功能"""

    def setUp(self):
        """設定測試環境"""
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        db.create_all()

    def tearDown(self):
        """清理測試環境"""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_login_creates_audit_log(self):
        """測試登入會建立審計日誌"""
        # 註冊使用者
        self.client.post('/register', data={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'password123',
            'password2': 'password123'
        }, follow_redirects=True)

        # 清除註冊時的日誌
        AuditLog.query.delete()
        db.session.commit()

        # 登入
        self.client.post('/login', data={
            'username': 'testuser',
            'password': 'password123'
        }, follow_redirects=True)

        # 檢查審計日誌
        logs = AuditLog.query.filter_by(action=AuditAction.LOGIN_SUCCESS).all()
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0].status, AuditStatus.SUCCESS)

    def test_failed_login_creates_audit_log(self):
        """測試登入失敗會建立審計日誌"""
        self.client.post('/login', data={
            'username': 'nonexistent',
            'password': 'wrongpassword'
        }, follow_redirects=True)

        # 檢查審計日誌
        logs = AuditLog.query.filter_by(action=AuditAction.LOGIN_FAILURE).all()
        self.assertGreater(len(logs), 0)
        self.assertEqual(logs[0].severity, AuditSeverity.WARN)

    def test_logout_creates_audit_log(self):
        """測試登出會建立審計日誌"""
        # 註冊並登入
        self.client.post('/register', data={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'password123',
            'password2': 'password123'
        }, follow_redirects=True)

        self.client.post('/login', data={
            'username': 'testuser',
            'password': 'password123'
        }, follow_redirects=True)

        # 清除之前的日誌
        AuditLog.query.delete()
        db.session.commit()

        # 登出
        self.client.get('/logout', follow_redirects=True)

        # 檢查審計日誌
        logs = AuditLog.query.filter_by(action=AuditAction.LOGOUT).all()
        self.assertEqual(len(logs), 1)

    def test_registration_creates_audit_log(self):
        """測試註冊會建立審計日誌"""
        self.client.post('/register', data={
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'password123',
            'password2': 'password123'
        }, follow_redirects=True)

        # 檢查審計日誌
        logs = AuditLog.query.filter_by(action=AuditAction.REGISTER).all()
        self.assertEqual(len(logs), 1)
        self.assertIn('newuser', logs[0].message)


if __name__ == '__main__':
    unittest.main()
