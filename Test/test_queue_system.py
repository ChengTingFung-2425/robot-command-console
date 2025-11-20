"""
測試 Queue System
驗證佇列系統的核心功能
"""

import asyncio
import sys
import os
import unittest
from datetime import datetime, timezone

# 添加 src 目錄到路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from robot_service.queue import (
    Message,
    MessagePriority,
    MemoryQueue,
    QueueHandler,
)
from robot_service.service_manager import ServiceManager


class TestMessage(unittest.TestCase):
    """測試 Message 類別"""
    
    def test_message_creation(self):
        """測試訊息建立"""
        message = Message(
            payload={"command": "test"},
            priority=MessagePriority.NORMAL,
            trace_id="trace-123",
        )
        
        self.assertIsNotNone(message.id)
        self.assertEqual(message.payload["command"], "test")
        self.assertEqual(message.priority, MessagePriority.NORMAL)
        self.assertEqual(message.trace_id, "trace-123")
        self.assertIsInstance(message.timestamp, datetime)
    
    def test_message_to_dict(self):
        """測試訊息序列化"""
        message = Message(
            payload={"command": "test"},
            priority=MessagePriority.HIGH,
            trace_id="trace-123",
            correlation_id="corr-456",
        )
        
        data = message.to_dict()
        
        self.assertEqual(data["payload"]["command"], "test")
        self.assertEqual(data["priority"], MessagePriority.HIGH.value)
        self.assertEqual(data["trace_id"], "trace-123")
        self.assertEqual(data["correlation_id"], "corr-456")
        self.assertIn("timestamp", data)
    
    def test_message_from_dict(self):
        """測試訊息反序列化"""
        data = {
            "id": "test-id",
            "payload": {"command": "test"},
            "priority": MessagePriority.NORMAL.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "trace_id": "trace-123",
            "retry_count": 0,
            "max_retries": 3,
        }
        
        message = Message.from_dict(data)
        
        self.assertEqual(message.id, "test-id")
        self.assertEqual(message.payload["command"], "test")
        self.assertEqual(message.priority, MessagePriority.NORMAL)
        self.assertEqual(message.trace_id, "trace-123")


class TestMemoryQueue(unittest.TestCase):
    """測試 MemoryQueue"""
    
    def setUp(self):
        """設定測試環境"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
    
    def tearDown(self):
        """清理測試環境"""
        self.loop.close()
    
    def test_enqueue_dequeue(self):
        """測試入隊與出隊"""
        async def test():
            queue = MemoryQueue()
            
            message = Message(payload={"command": "test"})
            success = await queue.enqueue(message)
            
            self.assertTrue(success)
            
            dequeued = await queue.dequeue(timeout=0)
            
            self.assertIsNotNone(dequeued)
            self.assertEqual(dequeued.id, message.id)
        
        self.loop.run_until_complete(test())
    
    def test_priority_ordering(self):
        """測試優先權排序"""
        async def test():
            queue = MemoryQueue()
            
            # 依序加入不同優先權的訊息
            low = Message(payload={"order": 1}, priority=MessagePriority.LOW)
            normal = Message(payload={"order": 2}, priority=MessagePriority.NORMAL)
            high = Message(payload={"order": 3}, priority=MessagePriority.HIGH)
            urgent = Message(payload={"order": 4}, priority=MessagePriority.URGENT)
            
            await queue.enqueue(low)
            await queue.enqueue(normal)
            await queue.enqueue(high)
            await queue.enqueue(urgent)
            
            # 依優先權順序取出
            msg1 = await queue.dequeue(timeout=0)
            msg2 = await queue.dequeue(timeout=0)
            msg3 = await queue.dequeue(timeout=0)
            msg4 = await queue.dequeue(timeout=0)
            
            self.assertEqual(msg1.payload["order"], 4)  # URGENT
            self.assertEqual(msg2.payload["order"], 3)  # HIGH
            self.assertEqual(msg3.payload["order"], 2)  # NORMAL
            self.assertEqual(msg4.payload["order"], 1)  # LOW
        
        self.loop.run_until_complete(test())
    
    def test_ack_message(self):
        """測試確認訊息"""
        async def test():
            queue = MemoryQueue()
            
            message = Message(payload={"command": "test"})
            await queue.enqueue(message)
            
            dequeued = await queue.dequeue(timeout=0)
            success = await queue.ack(dequeued.id)
            
            self.assertTrue(success)
            
            # 再次確認應該失敗（已經確認過）
            success = await queue.ack(dequeued.id)
            self.assertFalse(success)
        
        self.loop.run_until_complete(test())
    
    def test_nack_with_requeue(self):
        """測試拒絕訊息並重新入隊"""
        async def test():
            queue = MemoryQueue()
            
            message = Message(payload={"command": "test"}, max_retries=3)
            await queue.enqueue(message)
            
            dequeued = await queue.dequeue(timeout=0)
            success = await queue.nack(dequeued.id, requeue=True)
            
            self.assertTrue(success)
            
            # 應該能再次取出（重新入隊）
            requeued = await queue.dequeue(timeout=0)
            self.assertIsNotNone(requeued)
            self.assertEqual(requeued.id, message.id)
            self.assertEqual(requeued.retry_count, 1)
        
        self.loop.run_until_complete(test())
    
    def test_max_retries(self):
        """測試最大重試次數"""
        async def test():
            queue = MemoryQueue()
            
            message = Message(payload={"command": "test"}, max_retries=2)
            await queue.enqueue(message)
            
            # 第一次處理失敗
            msg1 = await queue.dequeue(timeout=0)
            await queue.nack(msg1.id, requeue=True)
            
            # 第二次處理失敗
            msg2 = await queue.dequeue(timeout=0)
            await queue.nack(msg2.id, requeue=True)
            
            # 第三次處理失敗（超過 max_retries，不會重新入隊）
            msg3 = await queue.dequeue(timeout=0)
            await queue.nack(msg3.id, requeue=True)
            
            # 佇列應該為空
            msg4 = await queue.dequeue(timeout=0)
            self.assertIsNone(msg4)
        
        self.loop.run_until_complete(test())
    
    def test_queue_size(self):
        """測試佇列大小"""
        async def test():
            queue = MemoryQueue()
            
            self.assertEqual(await queue.size(), 0)
            
            await queue.enqueue(Message(payload={"id": 1}))
            await queue.enqueue(Message(payload={"id": 2}))
            
            self.assertEqual(await queue.size(), 2)
            
            await queue.dequeue(timeout=0)
            
            self.assertEqual(await queue.size(), 1)
        
        self.loop.run_until_complete(test())
    
    def test_max_size_limit(self):
        """測試佇列大小限制"""
        async def test():
            queue = MemoryQueue(max_size=2)
            
            # 加入兩個訊息（應該成功）
            success1 = await queue.enqueue(Message(payload={"id": 1}))
            success2 = await queue.enqueue(Message(payload={"id": 2}))
            
            self.assertTrue(success1)
            self.assertTrue(success2)
            
            # 加入第三個訊息（應該失敗）
            success3 = await queue.enqueue(Message(payload={"id": 3}))
            
            self.assertFalse(success3)
        
        self.loop.run_until_complete(test())
    
    def test_health_check(self):
        """測試健康檢查"""
        async def test():
            queue = MemoryQueue(max_size=100)
            
            await queue.enqueue(Message(payload={"id": 1}))
            
            health = await queue.health_check()
            
            self.assertEqual(health["status"], "healthy")
            self.assertEqual(health["type"], "memory")
            self.assertEqual(health["total_size"], 1)
            self.assertEqual(health["max_size"], 100)
            self.assertIn("statistics", health)
        
        self.loop.run_until_complete(test())


class TestQueueHandler(unittest.TestCase):
    """測試 QueueHandler"""
    
    def setUp(self):
        """設定測試環境"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.processed_messages = []
    
    def tearDown(self):
        """清理測試環境"""
        self.loop.close()
    
    async def processor_for_testing(self, message: Message) -> bool:
        """測試用處理器"""
        self.processed_messages.append(message)
        return True
    
    def test_handler_processing(self):
        """測試處理器處理訊息"""
        async def test():
            queue = MemoryQueue()
            handler = QueueHandler(
                queue=queue,
                processor=self.processor_for_testing,
                max_workers=2,
                poll_interval=0.01,
            )
            
            # 加入訊息
            await queue.enqueue(Message(payload={"id": 1}))
            await queue.enqueue(Message(payload={"id": 2}))
            
            # 啟動處理器
            await handler.start()
            
            # 等待處理完成
            await asyncio.sleep(0.5)
            
            # 停止處理器
            await handler.stop(timeout=5.0)
            
            # 驗證訊息已處理
            self.assertEqual(len(self.processed_messages), 2)
        
        self.loop.run_until_complete(test())


class TestServiceManager(unittest.TestCase):
    """測試 ServiceManager"""
    
    def setUp(self):
        """設定測試環境"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
    
    def tearDown(self):
        """清理測試環境"""
        self.loop.close()
    
    def test_submit_command(self):
        """測試提交指令"""
        async def test():
            manager = ServiceManager(queue_max_size=100)
            await manager.start()
            
            message_id = await manager.submit_command(
                payload={"command": "test"},
                priority=MessagePriority.NORMAL,
                trace_id="trace-123",
            )
            
            self.assertIsNotNone(message_id)
            
            # 檢查佇列
            size = await manager.queue.size()
            self.assertGreaterEqual(size, 0)  # 可能已被處理
            
            await manager.stop()
        
        self.loop.run_until_complete(test())
    
    def test_health_check(self):
        """測試健康檢查"""
        async def test():
            manager = ServiceManager()
            await manager.start()
            
            health = await manager.health_check()
            
            self.assertEqual(health["status"], "healthy")
            self.assertTrue(health["started"])
            self.assertIn("handler", health)
            
            await manager.stop()
        
        self.loop.run_until_complete(test())


if __name__ == '__main__':
    unittest.main()
