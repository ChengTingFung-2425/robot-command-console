"""
CloudSyncQueue 單元測試

涵蓋：先後發送機制（FIFO 序號）、本地 SQLite 快取、重試邏輯、
批次發送、統計、邊界條件。
"""
import unittest

from Edge.cloud_sync.sync_queue import CloudSyncQueue


class TestCloudSyncQueueBasic(unittest.TestCase):
    """基本功能測試"""

    def setUp(self):
        """每個測試前建立新的記憶體佇列"""
        self.queue = CloudSyncQueue(db_path=None, max_size=10, max_retry_count=3, batch_size=5)

    def tearDown(self):
        self.queue.close()

    # ==================== 入隊 ====================

    def test_enqueue_returns_op_id(self):
        """enqueue 應返回非空字串 op_id"""
        op_id = self.queue.enqueue('user_settings', {'user_id': 'u1', 'settings': {}})
        self.assertIsNotNone(op_id)
        self.assertIsInstance(op_id, str)

    def test_enqueue_increments_size(self):
        """入隊後 size() 應遞增"""
        self.assertEqual(self.queue.size(), 0)
        self.queue.enqueue('user_settings', {'user_id': 'u1', 'settings': {}})
        self.assertEqual(self.queue.size(), 1)
        self.queue.enqueue('command_history', {'user_id': 'u1', 'records': []})
        self.assertEqual(self.queue.size(), 2)

    def test_enqueue_rejects_when_full(self):
        """佇列已滿時應返回 None"""
        for i in range(10):
            op_id = self.queue.enqueue('user_settings', {'i': i})
            self.assertIsNotNone(op_id, f"Should succeed for item {i}")

        # 第 11 個應被拒絕
        op_id = self.queue.enqueue('user_settings', {'i': 99})
        self.assertIsNone(op_id)
        self.assertEqual(self.queue.size(), 10)

    def test_enqueue_rejects_non_serializable_payload(self):
        """不可 JSON 序列化的 payload 應返回 None"""
        op_id = self.queue.enqueue('user_settings', {'obj': object()})
        self.assertIsNone(op_id)

    def test_enqueue_with_trace_id(self):
        """帶 trace_id 的入隊應成功"""
        op_id = self.queue.enqueue(
            'user_settings',
            {'user_id': 'u1', 'settings': {}},
            trace_id='trace-001'
        )
        self.assertIsNotNone(op_id)

    # ==================== 先後發送機制（FIFO）====================

    def test_flush_sends_in_fifo_order(self):
        """flush 應按入隊順序（seq 升序）發送"""
        sent_order = []

        def handler(op_type, payload):
            sent_order.append(payload['seq_marker'])
            return True

        for i in range(5):
            self.queue.enqueue('user_settings', {'seq_marker': i})

        self.queue.flush(handler)
        self.assertEqual(sent_order, [0, 1, 2, 3, 4])

    def test_flush_respects_order_after_partial_failure(self):
        """當整批發送全部失敗（模擬網路斷線），下次 flush 仍按 FIFO 順序補發"""
        sent_order = []

        def always_fail(op_type, payload):
            return False

        def always_succeed(op_type, payload):
            sent_order.append(payload['seq_marker'])
            return True

        for i in range(3):
            self.queue.enqueue('user_settings', {'seq_marker': i})

        # 第一次 flush：全部失敗（模擬離線）
        result1 = self.queue.flush(always_fail)
        self.assertEqual(result1['sent'], 0)
        self.assertEqual(self.queue.size(), 3)  # 全部仍在佇列

        # 第二次 flush：全部成功，應按入隊順序 [0, 1, 2]
        self.queue.flush(always_succeed)
        self.assertEqual(sent_order, [0, 1, 2])

    def test_flush_returns_correct_stats_all_succeed(self):
        """全部成功時，flush 應返回正確的 sent 計數"""
        for i in range(3):
            self.queue.enqueue('user_settings', {'i': i})

        result = self.queue.flush(lambda op, p: True)
        self.assertEqual(result['sent'], 3)
        self.assertEqual(result['remaining'], 0)

    def test_flush_empty_queue(self):
        """空佇列 flush 應成功並返回 0"""
        result = self.queue.flush(lambda op, p: True)
        self.assertEqual(result, {'sent': 0, 'failed': 0, 'remaining': 0})

    def test_flush_removes_sent_items(self):
        """成功發送的項目應從佇列移除"""
        self.queue.enqueue('user_settings', {'user_id': 'u1', 'settings': {}})
        self.assertEqual(self.queue.size(), 1)

        self.queue.flush(lambda op, p: True)
        self.assertEqual(self.queue.size(), 0)

    # ==================== 重試邏輯 ====================

    def test_item_marked_failed_after_max_retries(self):
        """超出最大重試次數後項目應標記為 FAILED 並從 PENDING 移除"""
        queue = CloudSyncQueue(db_path=None, max_retry_count=2)
        queue.enqueue('user_settings', {'user_id': 'u1', 'settings': {}})

        # 兩次都失敗 → 超出 max_retry_count=2 → FAILED
        queue.flush(lambda op, p: False)
        queue.flush(lambda op, p: False)

        stats = queue.get_statistics()
        self.assertEqual(stats['pending'], 0)
        self.assertEqual(stats['failed'], 1)
        queue.close()

    def test_item_retried_before_max_retries(self):
        """未超出重試次數的項目應保持 PENDING"""
        queue = CloudSyncQueue(db_path=None, max_retry_count=3)
        queue.enqueue('user_settings', {'user_id': 'u1', 'settings': {}})

        # 一次失敗 → retry_cnt=1，仍 PENDING
        queue.flush(lambda op, p: False)

        self.assertEqual(queue.size(), 1)  # 仍在佇列
        queue.close()

    # ==================== 批次發送 ====================

    def test_flush_processes_in_batches(self):
        """flush 應按 batch_size 批次取出並全部發送"""
        queue = CloudSyncQueue(db_path=None, batch_size=3)
        for i in range(7):
            queue.enqueue('user_settings', {'i': i})

        result = queue.flush(lambda op, p: True)
        self.assertEqual(result['sent'], 7)
        self.assertEqual(queue.size(), 0)
        queue.close()

    # ==================== 統計 ====================

    def test_get_statistics(self):
        """get_statistics 應反映正確的計數"""
        self.queue.enqueue('user_settings', {'user_id': 'u1', 'settings': {}})
        self.queue.enqueue('command_history', {'user_id': 'u2', 'records': []})

        stats = self.queue.get_statistics()
        self.assertEqual(stats['pending'], 2)
        self.assertEqual(stats['total_enqueued'], 2)
        self.assertEqual(stats['total_sent'], 0)

        self.queue.flush(lambda op, p: True)

        stats = self.queue.get_statistics()
        self.assertEqual(stats['pending'], 0)
        self.assertEqual(stats['total_sent'], 2)

    # ==================== 在線狀態 ====================

    def test_set_online(self):
        """set_online 應更新 is_online 屬性"""
        self.assertFalse(self.queue.is_online)
        self.queue.set_online(True)
        self.assertTrue(self.queue.is_online)
        self.queue.set_online(False)
        self.assertFalse(self.queue.is_online)

    # ==================== clear ====================

    def test_clear_removes_all_items(self):
        """clear 應清除佇列中所有項目"""
        for i in range(5):
            self.queue.enqueue('user_settings', {'i': i})
        self.assertEqual(self.queue.size(), 5)

        self.queue.clear()
        self.assertEqual(self.queue.size(), 0)

    # ==================== 持久化（檔案資料庫）====================

    def test_persistence_across_instances(self):
        """SQLite 檔案資料庫：重新建立實例後佇列仍保留"""
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name

        try:
            # 建立佇列，入隊後關閉
            q1 = CloudSyncQueue(db_path=db_path)
            q1.enqueue('user_settings', {'user_id': 'u1', 'settings': {'theme': 'dark'}})
            q1.enqueue('command_history', {'user_id': 'u1', 'records': [{'id': 1}]})
            q1.close()

            # 重新開啟同一個資料庫
            q2 = CloudSyncQueue(db_path=db_path)
            self.assertEqual(q2.size(), 2)

            sent = []
            q2.flush(lambda op, p: sent.append(op) or True)
            self.assertEqual(len(sent), 2)
            q2.close()
        finally:
            os.unlink(db_path)


class TestCloudSyncQueueHandlerException(unittest.TestCase):
    """send_handler 拋出例外的處理測試"""

    def setUp(self):
        self.queue = CloudSyncQueue(db_path=None, max_retry_count=2)

    def tearDown(self):
        self.queue.close()

    def test_handler_exception_treated_as_failure(self):
        """send_handler 拋出例外應視為失敗（不中斷佇列，其餘項目仍發送）

        flush 流程：
        1. Batch=[u1, u2]：u1 例外→PENDING(retry=1)，u2 成功→移除；batch_all_failed=False → 繼續
        2. Batch=[u1]：u1 重試→成功→移除；batch_all_failed=False → 繼續
        3. Batch=[] → 結束
        最終：sent=2，佇列清空
        """
        self.queue.enqueue('user_settings', {'user_id': 'u1', 'settings': {}})
        self.queue.enqueue('user_settings', {'user_id': 'u2', 'settings': {}})

        call_count = [0]

        def handler(op_type, payload):
            call_count[0] += 1
            if call_count[0] == 1:
                raise ConnectionError("Network error")
            return True

        result = self.queue.flush(handler)
        self.assertEqual(result['sent'], 2)
        self.assertEqual(self.queue.size(), 0)

    def test_handler_exception_marks_failed_when_max_retries_exceeded(self):
        """send_handler 持續拋例外超過 max_retry_count，項目應標記 FAILED"""
        queue = CloudSyncQueue(db_path=None, max_retry_count=2)
        queue.enqueue('user_settings', {'user_id': 'u1', 'settings': {}})

        def always_raise(op_type, payload):
            raise ConnectionError("Network error")

        # 兩次 flush 都失敗 → 超出 max_retry_count=2 → FAILED
        queue.flush(always_raise)
        queue.flush(always_raise)

        stats = queue.get_statistics()
        self.assertEqual(stats['pending'], 0)
        self.assertEqual(stats['failed'], 1)
        queue.close()


if __name__ == '__main__':
    unittest.main()
