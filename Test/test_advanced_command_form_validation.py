import unittest
import json
from wtforms.validators import ValidationError
from WebUI.app import app
from WebUI.app.forms import AdvancedCommandForm


class TestAdvancedCommandFormValidation(unittest.TestCase):
    """測試 AdvancedCommandForm 的 validate_base_commands 方法"""
    
    def setUp(self):
        """設置測試環境"""
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.app_context = app.app_context()
        self.app_context.push()
    
    def tearDown(self):
        """清理測試環境"""
        self.app_context.pop()
    
    def test_valid_advanced_command(self):
        """測試 advanced_command 指令應該被接受"""
        form = AdvancedCommandForm()
        
        # 模擬包含 advanced_command 的指令序列
        test_commands = [
            {"command": "go_forward"},
            {"command": "advanced_command", "name": "patrol", "advanced": True, "verified": True},
            {"command": "turn_left"}
        ]
        
        # 建立模擬的 field 物件
        class MockField:
            def __init__(self, data):
                self.data = data
        
        field = MockField(json.dumps(test_commands))
        
        # 這個不應該拋出 ValidationError
        try:
            form.validate_base_commands(field)
        except ValidationError as e:
            self.fail(f"validate_base_commands 對合法的 advanced_command 拋出了 ValidationError: {str(e)}")
    
    def test_invalid_command(self):
        """測試無效的指令應該被拒絕"""
        form = AdvancedCommandForm()
        
        test_commands = [
            {"command": "invalid_command"}
        ]
        
        class MockField:
            def __init__(self, data):
                self.data = data
        
        field = MockField(json.dumps(test_commands))
        
        # 這應該拋出 ValidationError
        with self.assertRaises(ValidationError) as context:
            form.validate_base_commands(field)
        
        self.assertIn('不是有效的動作', str(context.exception))
    
    def test_mixed_commands_with_advanced(self):
        """測試混合基礎指令與進階指令"""
        form = AdvancedCommandForm()
        
        test_commands = [
            {"command": "stand"},
            {"command": "advanced_command", "name": "complex_move", "advanced": True, "verified": False},
            {"command": "wait", "duration_ms": 1000},
            {"command": "bow"}
        ]
        
        class MockField:
            def __init__(self, data):
                self.data = data
        
        field = MockField(json.dumps(test_commands))
        
        try:
            form.validate_base_commands(field)
        except ValidationError as e:
            self.fail(f"validate_base_commands 對混合指令拋出了 ValidationError: {str(e)}")
    
    def test_empty_command_list(self):
        """測試空指令列表（應該被允許）"""
        form = AdvancedCommandForm()
        
        test_commands = []
        
        class MockField:
            def __init__(self, data):
                self.data = data
        
        field = MockField(json.dumps(test_commands))
        
        try:
            form.validate_base_commands(field)
        except ValidationError as e:
            self.fail(f"validate_base_commands 對空列表拋出了 ValidationError: {str(e)}")


if __name__ == '__main__':
    unittest.main()
