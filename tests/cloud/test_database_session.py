# imports
import unittest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os

from Cloud.shared_commands.database import (
    init_db,
    get_db_session,
    session_scope,
    close_db,
    is_initialized,
    get_engine
)


class TestDatabaseSessionManagement(unittest.TestCase):
    """測試資料庫 session 管理功能"""

    def setUp(self):
        """每個測試前的設置"""
        # 關閉任何現有的資料庫連接
        close_db()

    def tearDown(self):
        """每個測試後的清理"""
        close_db()

    def test_init_db_sqlite_memory(self):
        """測試初始化 in-memory SQLite 資料庫"""
        engine = init_db('sqlite:///:memory:', create_tables=True)
        
        self.assertIsNotNone(engine)
        self.assertTrue(is_initialized())
        self.assertEqual(engine, get_engine())

    def test_init_db_sqlite_file(self):
        """測試初始化檔案型 SQLite 資料庫"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, 'test.db')
            db_url = f'sqlite:///{db_path}'
            
            engine = init_db(db_url, create_tables=True)
            
            self.assertIsNotNone(engine)
            self.assertTrue(is_initialized())
            self.assertTrue(os.path.exists(db_path))

    def test_get_db_session_without_init(self):
        """測試在未初始化時取得 session 應拋出錯誤"""
        with self.assertRaises(RuntimeError) as context:
            get_db_session()
        
        self.assertIn("not initialized", str(context.exception))

    def test_get_db_session_after_init(self):
        """測試初始化後可以取得 session"""
        init_db('sqlite:///:memory:', create_tables=True)
        
        session = get_db_session()
        self.assertIsNotNone(session)
        session.close()

    def test_session_scope_context_manager(self):
        """測試 session_scope context manager"""
        init_db('sqlite:///:memory:', create_tables=True)
        
        # 測試正常流程
        with session_scope() as session:
            self.assertIsNotNone(session)
            # Session 應該是可用的
            result = session.execute("SELECT 1").fetchone()
            self.assertEqual(result[0], 1)
        
        # Context manager 退出後 session 應該被關閉

    def test_session_scope_with_exception(self):
        """測試 session_scope 在異常時 rollback"""
        init_db('sqlite:///:memory:', create_tables=True)
        
        try:
            with session_scope() as session:
                # 模擬異常
                raise ValueError("Test error")
        except ValueError:
            pass  # 預期的異常
        
        # Session 應該被 rollback 和關閉，不應影響後續操作
        with session_scope() as session:
            result = session.execute("SELECT 1").fetchone()
            self.assertEqual(result[0], 1)

    def test_close_db(self):
        """測試關閉資料庫連接"""
        init_db('sqlite:///:memory:', create_tables=True)
        self.assertTrue(is_initialized())
        
        close_db()
        
        self.assertFalse(is_initialized())
        self.assertIsNone(get_engine())

    def test_is_initialized_before_init(self):
        """測試初始化前 is_initialized 應返回 False"""
        self.assertFalse(is_initialized())

    def test_is_initialized_after_init(self):
        """測試初始化後 is_initialized 應返回 True"""
        init_db('sqlite:///:memory:', create_tables=True)
        self.assertTrue(is_initialized())

    def test_multiple_init_calls(self):
        """測試多次呼叫 init_db"""
        engine1 = init_db('sqlite:///:memory:', create_tables=True)
        engine2 = init_db('sqlite:///:memory:', create_tables=True)
        
        # 第二次呼叫應該替換第一次的引擎
        self.assertIsNotNone(engine2)
        self.assertEqual(engine2, get_engine())

    def test_create_tables_flag(self):
        """測試 create_tables 參數"""
        # 測試不建立資料表
        engine = init_db('sqlite:///:memory:', create_tables=False)
        self.assertIsNotNone(engine)
        
        # 測試建立資料表
        engine = init_db('sqlite:///:memory:', create_tables=True)
        self.assertIsNotNone(engine)


class TestAPIIntegration(unittest.TestCase):
    """測試 API 與資料庫整合"""

    def setUp(self):
        """每個測試前的設置"""
        close_db()

    def tearDown(self):
        """每個測試後的清理"""
        close_db()

    def test_api_get_service_without_init(self):
        """測試未初始化時呼叫 get_service 應拋出錯誤"""
        from Cloud.shared_commands.api import get_service
        
        with self.assertRaises(RuntimeError) as context:
            with get_service() as service:
                pass
        
        self.assertIn("not initialized", str(context.exception).lower())

    def test_api_init_and_get_service(self):
        """測試初始化後可以取得 service"""
        from Cloud.shared_commands.api import init_shared_commands_api, get_service
        
        # 初始化
        init_shared_commands_api(
            jwt_secret='test-secret',
            database_url='sqlite:///:memory:',
            create_tables=True
        )
        
        # 取得 service
        with get_service() as service:
            self.assertIsNotNone(service)
            # Service 應該有 db session
            self.assertIsNotNone(service.db)


if __name__ == '__main__':
    unittest.main()
