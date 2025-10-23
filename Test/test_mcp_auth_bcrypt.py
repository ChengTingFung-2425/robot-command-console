"""
測試 MCP 認證管理器的 bcrypt 密碼雜湊功能
"""
import unittest
import sys
import asyncio

sys.path.insert(0, '/home/runner/work/robot-command-console/robot-command-console')

from MCP.auth_manager import AuthManager


class TestMCPAuthBcrypt(unittest.TestCase):
    """測試 bcrypt 密碼雜湊"""

    def setUp(self):
        """測試前準備"""
        self.auth = AuthManager()

    def test_password_hashing_with_bcrypt(self):
        """測試密碼使用 bcrypt 雜湊"""
        async def run_test():
            # 註冊使用者
            success = await self.auth.register_user(
                'user1', 'testuser', 'password123', 'admin'
            )
            self.assertTrue(success, "使用者註冊應該成功")
            
            # 檢查密碼雜湊格式（bcrypt 格式以 $2b$ 開頭）
            password_hash = self.auth.users['user1']['password_hash']
            self.assertTrue(
                password_hash.startswith('$2b$'),
                f"密碼雜湊應使用 bcrypt 格式，實際為: {password_hash[:10]}"
            )
            
            # 驗證密碼長度（bcrypt 雜湊長度為 60 字元）
            self.assertEqual(
                len(password_hash), 60,
                f"bcrypt 雜湊長度應為 60 字元，實際為: {len(password_hash)}"
            )

        asyncio.run(run_test())

    def test_password_authentication(self):
        """測試密碼驗證功能"""
        async def run_test():
            # 註冊使用者
            await self.auth.register_user(
                'user2', 'testuser2', 'mypassword', 'operator'
            )
            
            # 使用正確密碼驗證
            user_id = await self.auth.authenticate_user('testuser2', 'mypassword')
            self.assertEqual(user_id, 'user2', "正確密碼應該驗證成功")
            
            # 使用錯誤密碼驗證
            user_id = await self.auth.authenticate_user('testuser2', 'wrongpassword')
            self.assertIsNone(user_id, "錯誤密碼應該驗證失敗")

        asyncio.run(run_test())

    def test_salt_is_random(self):
        """測試鹽值是隨機的（相同密碼產生不同雜湊）"""
        async def run_test():
            # 註冊兩個使用者，使用相同密碼
            await self.auth.register_user(
                'user3', 'testuser3', 'samepassword', 'viewer'
            )
            await self.auth.register_user(
                'user4', 'testuser4', 'samepassword', 'viewer'
            )
            
            # 取得兩個密碼雜湊
            hash1 = self.auth.users['user3']['password_hash']
            hash2 = self.auth.users['user4']['password_hash']
            
            # 驗證雜湊不同（因為鹽值不同）
            self.assertNotEqual(
                hash1, hash2,
                "相同密碼應該產生不同的雜湊值（因為使用隨機鹽值）"
            )
            
            # 但兩個密碼都應該能驗證成功
            self.assertTrue(
                self.auth._verify_password('samepassword', hash1),
                "第一個密碼應該驗證成功"
            )
            self.assertTrue(
                self.auth._verify_password('samepassword', hash2),
                "第二個密碼應該驗證成功"
            )

        asyncio.run(run_test())

    def test_bcrypt_computational_cost(self):
        """測試 bcrypt 具有運算成本（防止暴力破解）"""
        import time
        
        async def run_test():
            # 測量密碼雜湊所需時間
            start_time = time.time()
            await self.auth.register_user(
                'user5', 'testuser5', 'testpassword', 'admin'
            )
            hash_time = time.time() - start_time
            
            # bcrypt 應該需要一定的運算時間（通常 > 0.05 秒）
            # 這確保了有運算成本，防止快速暴力破解
            self.assertGreater(
                hash_time, 0.01,
                f"bcrypt 雜湊應具有運算成本，實際時間: {hash_time:.4f} 秒"
            )
            
            print(f"bcrypt 雜湊運算時間: {hash_time:.4f} 秒")

        asyncio.run(run_test())


if __name__ == '__main__':
    unittest.main()
