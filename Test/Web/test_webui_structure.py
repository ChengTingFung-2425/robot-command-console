import unittest
import os

class TestWebUIFolderStructure(unittest.TestCase):
    def test_webui_main_folders(self):
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../WebUI'))
        required = [
            'app',
            'templates',
            'translations',
            'migrations',
        ]
        for folder in required:
            self.assertTrue(os.path.isdir(os.path.join(base, folder)), f"缺少 WebUI 子目錄: {folder}")

    def test_app_main_modules(self):
        app_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../WebUI/app'))
        modules = [
            'routes.py',
            'models.py',
            'errors.py',
            'email.py',
            'forms.py',
        ]
        for m in modules:
            self.assertTrue(os.path.isfile(os.path.join(app_dir, m)), f"缺少 app 模組檔案: {m}")

    def test_config_py_at_root(self):
        # Check that config.py exists at the project root
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
        config_path = os.path.join(project_root, 'config.py')
        self.assertTrue(os.path.isfile(config_path), "缺少 config.py 檔案於專案根目錄")
if __name__ == '__main__':
    unittest.main()
