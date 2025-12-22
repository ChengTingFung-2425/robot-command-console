"""
Phase 2.1 Step 5: Edge Token Cache 效能測試

測試 Token 快取系統的效能指標：
- Token 讀取效能（<5ms）
- Token 寫入效能（<10ms）
- 記憶體占用（<10MB）
"""

import json
import os
import tempfile
import time
import unittest
from datetime import datetime, timedelta

import psutil

from src.edge_app.auth.token_cache import EdgeTokenCache


class TestEdgeTokenCachePerformance(unittest.TestCase):
    """Edge Token Cache 效能測試"""

    def setUp(self):
        """設定測試環境"""
        self.test_dir = tempfile.mkdtemp()
        # 使用環境變數重定向 home 目錄
        self.original_home = os.environ.get('HOME')
        os.environ['HOME'] = self.test_dir
        self.cache = EdgeTokenCache(app_name="test-performance")

        # 建立測試用的 JWT Token
        future_time = int((datetime.utcnow() + timedelta(minutes=15)).timestamp())

        import base64
        header = base64.urlsafe_b64encode(b'{"alg":"HS256"}').decode().rstrip('=')
        payload = json.dumps({"exp": future_time, "user_id": "test-user"})
        body = base64.urlsafe_b64encode(payload.encode()).decode().rstrip('=')

        self.test_access_token = f"{header}.{body}.fake_signature"
        self.test_refresh_token = f"{header}.{body}.fake_signature"
        self.test_device_id = "test-device-perf"
        self.test_user_info = {"user_id": "test-user", "role": "admin"}

        # 預先儲存 Token 供讀取測試使用
        self.cache.save_tokens(
            self.test_access_token,
            self.test_refresh_token,
            self.test_device_id,
            self.test_user_info
        )

    def tearDown(self):
        """清理測試環境"""
        # 恢復原始 HOME 環境變數
        if self.original_home:
            os.environ['HOME'] = self.original_home
        elif 'HOME' in os.environ:
            del os.environ['HOME']

        import shutil
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_token_read_performance(self):
        """測試 Token 讀取效能（目標：<5ms）"""
        iterations = 100
        total_time = 0

        for _ in range(iterations):
            start_time = time.perf_counter()
            access_token = self.cache.get_access_token()
            end_time = time.perf_counter()

            self.assertIsNotNone(access_token, "Token 讀取應該成功")
            total_time += (end_time - start_time)

        avg_time_ms = (total_time / iterations) * 1000
        print(f"\n平均 Token 讀取時間: {avg_time_ms:.3f} ms")

        # 驗收標準：平均讀取時間 <5ms
        self.assertLess(avg_time_ms, 5.0,
                       f"Token 讀取時間 {avg_time_ms:.3f}ms 超過 5ms 標準")

    def test_token_write_performance(self):
        """測試 Token 寫入效能（目標：<10ms）"""
        iterations = 50
        total_time = 0

        for i in range(iterations):
            # 建立不同的 Token 以避免快取
            token_suffix = f"-{i}"
            test_token = self.test_access_token + token_suffix

            start_time = time.perf_counter()
            success = self.cache.save_tokens(
                test_token,
                self.test_refresh_token,
                self.test_device_id,
                self.test_user_info
            )
            end_time = time.perf_counter()

            self.assertTrue(success, "Token 寫入應該成功")
            total_time += (end_time - start_time)

        avg_time_ms = (total_time / iterations) * 1000
        print(f"\n平均 Token 寫入時間: {avg_time_ms:.3f} ms")

        # 驗收標準：平均寫入時間 <10ms
        self.assertLess(avg_time_ms, 10.0,
                       f"Token 寫入時間 {avg_time_ms:.3f}ms 超過 10ms 標準")

    def test_memory_usage(self):
        """測試記憶體占用（目標：<10MB）"""
        # 取得當前進程
        process = psutil.Process()

        # 記錄開始記憶體
        process.memory_info()  # 先呼叫一次以初始化
        import gc
        gc.collect()  # 強制垃圾回收

        mem_before = process.memory_info().rss / (1024 * 1024)  # MB

        # 執行大量操作
        caches = []
        for i in range(100):
            # 建立不同的 cache 實例
            test_home_i = tempfile.mkdtemp()
            os.environ['HOME'] = test_home_i
            cache = EdgeTokenCache(app_name=f"test-mem-{i}")
            cache.save_tokens(
                self.test_access_token,
                self.test_refresh_token,
                self.test_device_id,
                self.test_user_info
            )
            caches.append(cache)

        # 讀取操作
        for cache in caches:
            cache.get_access_token()
            cache.get_refresh_token()
            cache.get_device_id()
            cache.get_user_info()

        # 記錄結束記憶體
        mem_after = process.memory_info().rss / (1024 * 1024)  # MB
        mem_used = mem_after - mem_before

        print(f"\n記憶體使用: {mem_used:.2f} MB")

        # 驗收標準：記憶體增長 <10MB
        self.assertLess(mem_used, 10.0,
                       f"記憶體使用 {mem_used:.2f}MB 超過 10MB 標準")


if __name__ == '__main__':
    unittest.main()
