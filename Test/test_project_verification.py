import unittest
import os

class TestProjectVerification(unittest.TestCase):
    def test_project_structure(self):
        # 驗證專案根目錄下重要檔案與資料夾
        required = [
            'app.py',
            'requirements.txt',
            'WebUI/app/',
            'Test/'
        ]
        for path in required:
            self.assertTrue(os.path.exists(path), f"缺少必要檔案或資料夾: {path}")

if __name__ == '__main__':
    unittest.main()
