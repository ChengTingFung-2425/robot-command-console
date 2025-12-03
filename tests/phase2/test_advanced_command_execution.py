"""測試進階指令執行功能

本測試套件驗證：
1. 進階指令展開邏輯正確運作
2. execute_advanced_command 路由正確處理請求
3. 權限檢查正確執行
4. 錯誤處理正確運作
"""

import json
import unittest
import sys
import os

# 添加 WebUI 目錄到路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))


class TestAdvancedCommandExecution(unittest.TestCase):
    """測試進階指令執行功能"""

    def setUp(self):
        """設定測試環境"""
        from WebUI.app import create_app, db
        from WebUI.app.models import User, Robot, AdvancedCommand

        # 建立測試應用（使用 testing 配置）
        self.app = create_app(config_name='testing')
        self.client = self.app.test_client()

        # 建立應用上下文
        self.app_context = self.app.app_context()
        self.app_context.push()

        # 建立資料庫
        db.create_all()

        # 建立測試用戶
        self.user = User(username='testuser', email='test@example.com')
        self.user.set_password('testpass')
        db.session.add(self.user)

        # 建立測試機器人
        self.robot = Robot(name='test_robot', type='test_type', owner=self.user)
        db.session.add(self.robot)

        # 建立測試進階指令
        self.advanced_cmd = AdvancedCommand(
            name='test_command',
            description='Test command',
            category='test',
            author=self.user,
            base_commands=json.dumps([
                {"command": "go_forward"},
                {"command": "turn_left"},
                {"command": "stand"}
            ]),
            status='approved'
        )
        db.session.add(self.advanced_cmd)
        db.session.commit()

    def tearDown(self):
        """清理測試環境"""
        from WebUI.app import db
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def login(self):
        """登入測試用戶"""
        return self.client.post('/login', data={
            'username': 'testuser',
            'password': 'testpass'
        }, follow_redirects=True)

    def test_expand_advanced_command_success(self):
        """測試成功展開進階指令"""
        from WebUI.app.routes import expand_advanced_command

        actions = expand_advanced_command(self.advanced_cmd)

        self.assertEqual(actions, ['go_forward', 'turn_left', 'stand'])

    def test_expand_advanced_command_invalid_action(self):
        """測試展開包含無效動作的進階指令"""
        from WebUI.app import db
        from WebUI.app.models import AdvancedCommand
        from WebUI.app.routes import expand_advanced_command

        # 建立包含無效動作的指令
        invalid_cmd = AdvancedCommand(
            name='invalid_command',
            description='Invalid command',
            category='test',
            author=self.user,
            base_commands=json.dumps([
                {"command": "invalid_action"}
            ]),
            status='approved'
        )
        db.session.add(invalid_cmd)
        db.session.commit()

        with self.assertRaises(ValueError) as context:
            expand_advanced_command(invalid_cmd)

        self.assertIn('不是有效的基礎動作', str(context.exception))

    def test_expand_advanced_command_invalid_format(self):
        """測試展開格式錯誤的進階指令"""
        from WebUI.app import db
        from WebUI.app.models import AdvancedCommand
        from WebUI.app.routes import expand_advanced_command

        # 建立格式錯誤的指令
        invalid_cmd = AdvancedCommand(
            name='malformed_command',
            description='Malformed command',
            category='test',
            author=self.user,
            base_commands='not a json array',
            status='approved'
        )
        db.session.add(invalid_cmd)
        db.session.commit()

        with self.assertRaises(ValueError) as context:
            expand_advanced_command(invalid_cmd)

        self.assertIn('JSON 格式錯誤', str(context.exception))

    def test_execute_advanced_command_requires_login(self):
        """測試未登入無法執行進階指令"""
        response = self.client.post(
            f'/advanced_commands/{self.advanced_cmd.id}/execute',
            json={'robot_id': self.robot.id}
        )

        # 應該重定向到登入頁面或返回 401
        self.assertIn(response.status_code, [302, 401])

    def test_execute_advanced_command_success(self):
        """測試成功執行進階指令"""
        self.login()

        response = self.client.post(
            f'/advanced_commands/{self.advanced_cmd.id}/execute',
            json={'robot_id': self.robot.id}
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)

        self.assertTrue(data['success'])
        self.assertIn('command_id', data)
        self.assertIn('details', data)
        self.assertEqual(data['details']['actions_count'], 3)

    def test_execute_advanced_command_not_approved(self):
        """測試不能執行未批准的進階指令"""
        from WebUI.app import db

        self.login()

        # 將指令狀態改為 pending
        self.advanced_cmd.status = 'pending'
        db.session.commit()

        response = self.client.post(
            f'/advanced_commands/{self.advanced_cmd.id}/execute',
            json={'robot_id': self.robot.id}
        )

        self.assertEqual(response.status_code, 403)
        data = json.loads(response.data)

        self.assertFalse(data['success'])
        self.assertIn('已批准', data['message'])

    def test_execute_advanced_command_missing_robot_id(self):
        """測試缺少 robot_id 參數"""
        self.login()

        response = self.client.post(
            f'/advanced_commands/{self.advanced_cmd.id}/execute',
            json={}
        )

        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)

        self.assertFalse(data['success'])
        self.assertIn('robot_id', data['message'])

    def test_execute_advanced_command_unauthorized_robot(self):
        """測試不能控制其他用戶的機器人"""
        from WebUI.app import db
        from WebUI.app.models import User, Robot

        # 建立另一個用戶和機器人
        other_user = User(username='otheruser', email='other@example.com')
        other_user.set_password('otherpass')
        db.session.add(other_user)

        other_robot = Robot(name='other_robot', type='test_type', owner=other_user)
        db.session.add(other_robot)
        db.session.commit()

        # 以第一個用戶登入
        self.login()

        # 嘗試控制其他用戶的機器人
        response = self.client.post(
            f'/advanced_commands/{self.advanced_cmd.id}/execute',
            json={'robot_id': other_robot.id}
        )

        self.assertEqual(response.status_code, 403)
        data = json.loads(response.data)

        self.assertFalse(data['success'])
        self.assertIn('沒有權限', data['message'])

    def test_send_actions_to_robot(self):
        """測試 send_actions_to_robot 函式"""
        from WebUI.app.routes import send_actions_to_robot

        actions = ['go_forward', 'turn_left', 'stand']
        result = send_actions_to_robot(self.robot, actions)

        self.assertTrue(result['success'])
        self.assertIn('details', result)
        self.assertEqual(result['details']['actions_count'], 3)
        self.assertEqual(result['details']['robot_name'], 'test_robot')

    def test_expand_advanced_command_with_wait(self):
        """測試展開包含 wait 指令的進階指令（應被跳過）"""
        from WebUI.app import db
        from WebUI.app.models import AdvancedCommand
        from WebUI.app.routes import expand_advanced_command

        # 建立包含 wait 指令的指令
        cmd_with_wait = AdvancedCommand(
            name='command_with_wait',
            description='Command with wait',
            category='test',
            author=self.user,
            base_commands=json.dumps([
                {"command": "go_forward"},
                {"command": "wait", "duration_ms": 1000},
                {"command": "turn_left"}
            ]),
            status='approved'
        )
        db.session.add(cmd_with_wait)
        db.session.commit()

        actions = expand_advanced_command(cmd_with_wait)

        # wait 應該被跳過
        self.assertEqual(actions, ['go_forward', 'turn_left'])


if __name__ == '__main__':
    unittest.main()
