"""
測試 Token 管理模組
測試 Electron/背景服務間權杖與安全通信功能
"""

import sys
import os
import unittest
import time
from datetime import timedelta

# 添加 src 目錄到路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from common.token_manager import (  # noqa: E402
    TokenManager,
    TokenInfo,
    TokenRotationEvent,
    get_edge_token_manager,
    reset_edge_token_manager,
)


class TestTokenGeneration(unittest.TestCase):
    """測試 Token 生成功能"""

    def setUp(self):
        """設定測試環境"""
        self.manager = TokenManager(token_length=32)

    def test_generate_token_returns_valid_token(self):
        """測試生成的 Token 有效"""
        token, info = self.manager.generate_token()

        self.assertIsNotNone(token)
        self.assertEqual(len(token), 64)  # 32 bytes = 64 hex chars
        self.assertIsInstance(info, TokenInfo)
        self.assertTrue(info.is_active)

    def test_generate_token_unique_each_time(self):
        """測試每次生成的 Token 都不同"""
        token1, _ = self.manager.generate_token()
        token2, _ = self.manager.generate_token()

        self.assertNotEqual(token1, token2)

    def test_generate_token_with_expiry(self):
        """測試帶過期時間的 Token 生成"""
        manager = TokenManager(token_expiry_hours=1)
        token, info = manager.generate_token()

        self.assertIsNotNone(info.expires_at)
        self.assertFalse(info.is_expired())

        time_left = info.time_until_expiry()
        self.assertIsNotNone(time_left)
        # 應該接近 1 小時
        self.assertGreater(time_left.total_seconds(), 3500)

    def test_generate_token_without_expiry(self):
        """測試不過期的 Token 生成"""
        manager = TokenManager(token_expiry_hours=None)
        token, info = manager.generate_token()

        self.assertIsNone(info.expires_at)
        self.assertFalse(info.is_expired())
        self.assertIsNone(info.time_until_expiry())


class TestTokenVerification(unittest.TestCase):
    """測試 Token 驗證功能"""

    def setUp(self):
        """設定測試環境"""
        self.manager = TokenManager(token_length=32)
        self.token, self.info = self.manager.generate_token()

    def test_verify_valid_token(self):
        """測試有效 Token 驗證成功"""
        self.assertTrue(self.manager.verify_token(self.token))

    def test_verify_invalid_token(self):
        """測試無效 Token 驗證失敗"""
        self.assertFalse(self.manager.verify_token("invalid_token"))

    def test_verify_empty_token(self):
        """測試空 Token 驗證失敗"""
        self.assertFalse(self.manager.verify_token(""))
        self.assertFalse(self.manager.verify_token(None))

    def test_verify_expired_token(self):
        """測試過期 Token 驗證失敗"""
        # 創建立即過期的 Token
        manager = TokenManager(token_expiry_hours=-1)  # 過去的時間
        token, info = manager.generate_token()

        self.assertTrue(info.is_expired())
        self.assertFalse(manager.verify_token(token))


class TestTokenRotation(unittest.TestCase):
    """測試 Token 輪替功能"""

    def setUp(self):
        """設定測試環境"""
        self.manager = TokenManager(
            token_length=32,
            grace_period_seconds=2,  # 短寬限期用於測試
        )

    def test_rotate_token_generates_new_token(self):
        """測試輪替生成新 Token"""
        old_token, old_info = self.manager.generate_token()
        new_token, new_info = self.manager.rotate_token()

        self.assertNotEqual(old_token, new_token)
        self.assertNotEqual(old_info.token_id, new_info.token_id)
        self.assertEqual(new_info.rotation_count, 1)

    def test_old_token_valid_during_grace_period(self):
        """測試舊 Token 在寬限期內有效"""
        old_token, _ = self.manager.generate_token()
        new_token, _ = self.manager.rotate_token()

        # 新舊 Token 都應該有效
        self.assertTrue(self.manager.verify_token(new_token))
        self.assertTrue(self.manager.verify_token(old_token))

    def test_old_token_invalid_after_grace_period(self):
        """測試舊 Token 在寬限期後失效"""
        old_token, _ = self.manager.generate_token()
        self.manager.rotate_token()

        # 等待寬限期結束
        time.sleep(2.5)

        # 舊 Token 應該失效
        self.assertFalse(self.manager.verify_token(old_token))

    def test_rotation_history_tracked(self):
        """測試輪替歷史被追蹤"""
        self.manager.generate_token()
        self.manager.rotate_token(reason="test1")
        self.manager.rotate_token(reason="test2")

        history = self.manager.get_rotation_history()
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0].reason, "test1")
        self.assertEqual(history[1].reason, "test2")

    def test_rotation_callback_invoked(self):
        """測試輪替時回調被呼叫"""
        callback_called = []

        def callback(new_token, info):
            callback_called.append((new_token, info))

        self.manager.on_token_rotated(callback)
        self.manager.generate_token()
        self.manager.rotate_token()

        self.assertEqual(len(callback_called), 1)
        self.assertIsNotNone(callback_called[0][0])
        self.assertIsInstance(callback_called[0][1], TokenInfo)

    def test_remove_rotation_callback(self):
        """測試移除輪替回調"""
        callback_count = [0]

        def callback(new_token, info):
            callback_count[0] += 1

        self.manager.on_token_rotated(callback)
        self.manager.generate_token()
        self.manager.rotate_token()
        self.assertEqual(callback_count[0], 1)

        # 移除回調
        result = self.manager.remove_rotation_callback(callback)
        self.assertTrue(result)

        # 再次輪替，回調不應被呼叫
        self.manager.rotate_token()
        self.assertEqual(callback_count[0], 1)


class TestTokenInfo(unittest.TestCase):
    """測試 TokenInfo 類別"""

    def test_token_info_to_dict(self):
        """測試 TokenInfo 轉換為字典"""
        manager = TokenManager()
        _, info = manager.generate_token()

        info_dict = info.to_dict()

        self.assertIn("token_id", info_dict)
        self.assertIn("created_at", info_dict)
        self.assertIn("is_active", info_dict)
        self.assertIn("is_expired", info_dict)
        self.assertTrue(info_dict["is_active"])
        self.assertFalse(info_dict["is_expired"])


class TestTokenManagerStatus(unittest.TestCase):
    """測試 Token 管理器狀態功能"""

    def setUp(self):
        """設定測試環境"""
        self.manager = TokenManager()

    def test_get_status_without_token(self):
        """測試無 Token 時的狀態"""
        status = self.manager.get_status()

        self.assertFalse(status["has_token"])
        self.assertIsNone(status["token_info"])
        self.assertEqual(status["rotation_count"], 0)

    def test_get_status_with_token(self):
        """測試有 Token 時的狀態"""
        self.manager.generate_token()
        status = self.manager.get_status()

        self.assertTrue(status["has_token"])
        self.assertIsNotNone(status["token_info"])
        self.assertEqual(status["rotation_count"], 0)

    def test_is_rotation_needed_no_token(self):
        """測試無 Token 時需要輪替"""
        self.assertTrue(self.manager.is_rotation_needed())

    def test_is_rotation_needed_valid_token(self):
        """測試有效 Token 時不需要輪替"""
        manager = TokenManager(token_expiry_hours=24)
        manager.generate_token()

        # 還有 24 小時，不需要輪替
        self.assertFalse(manager.is_rotation_needed(threshold_hours=1.0))

    def test_invalidate_token(self):
        """測試使 Token 失效"""
        token, _ = self.manager.generate_token()

        # Token 應該有效
        self.assertTrue(self.manager.verify_token(token))

        # 使 Token 失效
        self.manager.invalidate_token()

        # Token 應該無效
        self.assertFalse(self.manager.verify_token(token))
        self.assertIsNone(self.manager.get_current_token())


class TestGlobalTokenManager(unittest.TestCase):
    """測試全域 Token 管理器"""

    def setUp(self):
        """重置全域管理器"""
        reset_edge_token_manager()

    def tearDown(self):
        """清理"""
        reset_edge_token_manager()

    def test_get_edge_token_manager_returns_same_instance(self):
        """測試取得相同的全域實例"""
        manager1 = get_edge_token_manager()
        manager2 = get_edge_token_manager()

        self.assertIs(manager1, manager2)

    def test_reset_edge_token_manager(self):
        """測試重置全域管理器"""
        manager1 = get_edge_token_manager()
        manager1.generate_token()

        reset_edge_token_manager()

        manager2 = get_edge_token_manager()
        self.assertIsNot(manager1, manager2)
        self.assertIsNone(manager2.get_current_token())


class TestTokenSecurityFeatures(unittest.TestCase):
    """測試 Token 安全功能"""

    def test_token_is_cryptographically_secure(self):
        """測試 Token 是加密安全的"""
        manager = TokenManager(token_length=32)

        tokens = set()
        for _ in range(100):
            token, _ = manager.generate_token()
            tokens.add(token)

        # 所有 Token 應該都是唯一的
        self.assertEqual(len(tokens), 100)

    def test_timing_safe_comparison(self):
        """測試使用時間安全的比較"""
        manager = TokenManager()
        token, _ = manager.generate_token()

        # 驗證使用 hmac.compare_digest（隱式測試）
        self.assertTrue(manager.verify_token(token))
        self.assertFalse(manager.verify_token(token[:-1] + "X"))

    def test_token_not_stored_in_plain_for_old_tokens(self):
        """測試舊 Token 使用雜湊存儲"""
        manager = TokenManager(grace_period_seconds=60)
        old_token, _ = manager.generate_token()
        manager.rotate_token()

        # 舊 Token 仍然有效（存儲為雜湊）
        self.assertTrue(manager.verify_token(old_token))

        # 內部應該使用雜湊，而不是原始 Token
        self.assertNotIn(old_token, str(manager._previous_tokens))


if __name__ == '__main__':
    unittest.main()
