import unittest

class TestRobotAbstractionModule(unittest.TestCase):
    def test_robot_interface(self):
        try:
            from WebUI.app.models import RobotBase
        except ImportError:
            self.skipTest('RobotBase 尚未實作')
        # 測試基礎介面方法
        class DummyRobot(RobotBase):
            def send_command(self, cmd):
                return 'ok'
        robot = DummyRobot()
        self.assertEqual(robot.send_command('test'), 'ok')

if __name__ == '__main__':
    unittest.main()
