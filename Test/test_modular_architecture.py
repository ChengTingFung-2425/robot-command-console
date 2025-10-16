import unittest

class TestModularArchitecture(unittest.TestCase):
    def test_modular_structure_exists(self):
        """驗證專案是否有模組化結構的基本檔案與資料夾。"""
        import os
        modules = [
            'WebUI/app/routes.py',
            'WebUI/app/models.py',
            'WebUI/app/errors.py',
            'WebUI/app/email.py',
            'WebUI/app/forms.py',
            'WebUI/app/config.py',
        ]
        for m in modules:
            self.assertTrue(os.path.exists(m), f"模組檔案不存在: {m}")

if __name__ == '__main__':
    unittest.main()
