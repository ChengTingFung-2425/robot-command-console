"""
RabbitMQ Queue Tests
測試 RabbitMQ 佇列實作的單元測試與整合測試
"""

import asyncio
import os
import pytest
from datetime import datetime, timezone

from robot_service.queue.interface import Message, MessagePriority
from robot_service.queue.rabbitmq_queue import RabbitMQQueue


# 測試用的 RabbitMQ URL（可透過環境變數覆蓋）
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")

# 標記：需要真實 RabbitMQ 實例的測試
requires_rabbitmq = pytest.mark.skipif(
    not os.getenv("TEST_WITH_RABBITMQ"),
    reason="Set TEST_WITH_RABBITMQ=1 to run RabbitMQ integration tests"
)


class TestMessage:
    """Message 資料類別測試"""

    def test_create_message(self):
        """測試建立訊息"""
        msg = Message(
            payload={"command": "move_forward"},
            priority=MessagePriority.HIGH,
            trace_id="test-trace-123"
        )

        assert msg.id is not None
        assert msg.payload == {"command": "move_forward"}
        assert msg.priority == MessagePriority.HIGH
        assert msg.trace_id == "test-trace-123"
        assert msg.retry_count == 0
        assert msg.max_retries == 3

    def test_message_to_dict(self):
        """測試訊息序列化"""
        msg = Message(
            payload={"command": "move_forward"},
            priority=MessagePriority.NORMAL
        )

        data = msg.to_dict()

        assert "id" in data
        assert data["payload"] == {"command": "move_forward"}
        assert data["priority"] == MessagePriority.NORMAL.value
        assert "timestamp" in data

    def test_message_from_dict(self):
        """測試訊息反序列化"""
        data = {
            "id": "test-id-123",
            "payload": {"command": "turn_left"},
            "priority": MessagePriority.HIGH.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "trace_id": "trace-456",
            "retry_count": 1,
            "max_retries": 5,
        }

        msg = Message.from_dict(data)

        assert msg.id == "test-id-123"
        assert msg.payload == {"command": "turn_left"}
        assert msg.priority == MessagePriority.HIGH
        assert msg.trace_id == "trace-456"
        assert msg.retry_count == 1
        assert msg.max_retries == 5

    def test_message_roundtrip(self):
        """測試訊息序列化與反序列化往返"""
        original = Message(
            payload={"command": "stop", "speed": 0},
            priority=MessagePriority.URGENT,
            trace_id="roundtrip-test"
        )

        data = original.to_dict()
        restored = Message.from_dict(data)

        assert restored.id == original.id
        assert restored.payload == original.payload
        assert restored.priority == original.priority
        assert restored.trace_id == original.trace_id


class TestRabbitMQQueueUnit:
    """RabbitMQ Queue 單元測試（不需要真實 RabbitMQ）"""

    def test_init(self):
        """測試初始化"""
        queue = RabbitMQQueue(
            url="amqp://test:test@localhost:5672/",
            exchange_name="test.exchange",
            queue_name="test.queue"
        )

        assert queue.url == "amqp://test:test@localhost:5672/"
        assert queue.exchange_name == "test.exchange"
        assert queue.queue_name == "test.queue"
        assert not queue._initialized

    def test_priority_mapping(self):
        """測試優先權映射"""
        assert RabbitMQQueue.PRIORITY_MAP[MessagePriority.LOW] == 2
        assert RabbitMQQueue.PRIORITY_MAP[MessagePriority.NORMAL] == 5
        assert RabbitMQQueue.PRIORITY_MAP[MessagePriority.HIGH] == 8
        assert RabbitMQQueue.PRIORITY_MAP[MessagePriority.URGENT] == 10


@requires_rabbitmq
class TestRabbitMQQueueIntegration:
    """RabbitMQ Queue 整合測試（需要真實 RabbitMQ）"""

    @pytest.fixture
    async def queue(self):
        """建立測試用佇列"""
        q = RabbitMQQueue(
            url=RABBITMQ_URL,
            exchange_name="test.robot.commands",
            queue_name="test.robot.queue",
            dlx_name="test.robot.dlx",
            dlq_name="test.robot.dlq"
        )

        await q.initialize()
        await q.clear()  # 清空測試佇列

        yield q

        # 清理
        await q.clear()
        await q.close()

    @pytest.mark.asyncio
    async def test_enqueue_dequeue(self, queue):
        """測試基本入隊與出隊"""
        msg = Message(
            payload={"command": "move_forward", "distance": 10},
            priority=MessagePriority.NORMAL,
            trace_id="test-trace-001"
        )

        # 入隊
        result = await queue.enqueue(msg)
        assert result is True

        # 出隊
        received = await queue.dequeue(timeout=5)
        assert received is not None
        assert received.id == msg.id
        assert received.payload == msg.payload
        assert received.priority == msg.priority

        # 確認
        if hasattr(received, '_amqp_message'):
            await received._amqp_message.ack()

    @pytest.mark.asyncio
    async def test_priority_ordering(self, queue):
        """測試優先權排序"""
        # 發送不同優先權的訊息
        low_msg = Message(payload={"priority": "low"}, priority=MessagePriority.LOW)
        normal_msg = Message(payload={"priority": "normal"}, priority=MessagePriority.NORMAL)
        high_msg = Message(payload={"priority": "high"}, priority=MessagePriority.HIGH)
        urgent_msg = Message(payload={"priority": "urgent"}, priority=MessagePriority.URGENT)

        await queue.enqueue(low_msg)
        await queue.enqueue(normal_msg)
        await queue.enqueue(urgent_msg)  # 後發但優先權最高
        await queue.enqueue(high_msg)

        # 等待訊息到達
        await asyncio.sleep(0.5)

        # 接收訊息，應按優先權排序
        msg1 = await queue.dequeue(timeout=2)
        msg2 = await queue.dequeue(timeout=2)
        msg3 = await queue.dequeue(timeout=2)
        msg4 = await queue.dequeue(timeout=2)

        assert msg1 is not None
        assert msg2 is not None
        assert msg3 is not None
        assert msg4 is not None

        # 確認優先權順序（URGENT > HIGH > NORMAL > LOW）
        priorities = [msg1.priority, msg2.priority, msg3.priority, msg4.priority]
        assert priorities[0] == MessagePriority.URGENT
        assert priorities[1] == MessagePriority.HIGH
        assert priorities[2] == MessagePriority.NORMAL
        assert priorities[3] == MessagePriority.LOW

        # 清理
        for msg in [msg1, msg2, msg3, msg4]:
            if hasattr(msg, '_amqp_message'):
                await msg._amqp_message.ack()

    @pytest.mark.asyncio
    async def test_queue_size(self, queue):
        """測試佇列大小查詢"""
        # 初始為空
        size = await queue.size()
        assert size == 0

        # 加入訊息
        await queue.enqueue(Message(payload={"test": 1}))
        await queue.enqueue(Message(payload={"test": 2}))
        await queue.enqueue(Message(payload={"test": 3}))

        await asyncio.sleep(0.2)

        size = await queue.size()
        assert size == 3

    @pytest.mark.asyncio
    async def test_clear_queue(self, queue):
        """測試清空佇列"""
        # 加入訊息
        for i in range(5):
            await queue.enqueue(Message(payload={"index": i}))

        await asyncio.sleep(0.2)

        # 確認有訊息
        size = await queue.size()
        assert size == 5

        # 清空
        await queue.clear()

        # 確認已清空
        size = await queue.size()
        assert size == 0

    @pytest.mark.asyncio
    async def test_dequeue_timeout(self, queue):
        """測試出隊超時"""
        # 空佇列，應該超時返回 None
        msg = await queue.dequeue(timeout=1)
        assert msg is None

    @pytest.mark.asyncio
    async def test_dequeue_non_blocking(self, queue):
        """測試非阻塞出隊"""
        # 空佇列，非阻塞模式應立即返回 None
        msg = await queue.dequeue(timeout=0)
        assert msg is None

    @pytest.mark.asyncio
    async def test_persistence(self, queue):
        """測試訊息持久化（需要重啟 broker 才能完整測試）"""
        msg = Message(
            payload={"persistent": True},
            priority=MessagePriority.HIGH
        )

        # 發送持久化訊息
        result = await queue.enqueue(msg)
        assert result is True

        # 確認可以取出
        received = await queue.dequeue(timeout=2)
        assert received is not None
        assert received.payload == {"persistent": True}

        if hasattr(received, '_amqp_message'):
            await received._amqp_message.ack()

    @pytest.mark.asyncio
    async def test_health_check(self, queue):
        """測試健康檢查"""
        health = await queue.health_check()

        assert health["status"] == "healthy"
        assert health["type"] == "rabbitmq"
        assert health["connected"] is True
        assert "queue_size" in health
        assert "statistics" in health


@requires_rabbitmq
class TestRabbitMQQueueConcurrency:
    """RabbitMQ Queue 並發測試"""

    @pytest.fixture
    async def queue(self):
        """建立測試用佇列"""
        q = RabbitMQQueue(
            url=RABBITMQ_URL,
            exchange_name="test.concurrent.commands",
            queue_name="test.concurrent.queue",
            prefetch_count=20
        )

        await q.initialize()
        await q.clear()

        yield q

        await q.clear()
        await q.close()

    @pytest.mark.asyncio
    async def test_concurrent_enqueue(self, queue):
        """測試並發入隊"""
        message_count = 50

        async def enqueue_messages():
            tasks = []
            for i in range(message_count):
                msg = Message(payload={"index": i}, priority=MessagePriority.NORMAL)
                tasks.append(queue.enqueue(msg))

            results = await asyncio.gather(*tasks)
            return results

        results = await enqueue_messages()

        # 所有訊息應該成功入隊
        assert all(results)

        # 確認佇列大小
        await asyncio.sleep(0.5)
        size = await queue.size()
        assert size == message_count

    @pytest.mark.asyncio
    async def test_concurrent_dequeue(self, queue):
        """測試並發出隊"""
        message_count = 30

        # 先入隊
        for i in range(message_count):
            msg = Message(payload={"index": i})
            await queue.enqueue(msg)

        await asyncio.sleep(0.5)

        # 並發出隊
        async def dequeue_worker():
            messages = []
            for _ in range(10):
                msg = await queue.dequeue(timeout=2)
                if msg:
                    messages.append(msg)
                    if hasattr(msg, '_amqp_message'):
                        await msg._amqp_message.ack()
            return messages

        # 啟動 3 個工作者
        results = await asyncio.gather(
            dequeue_worker(),
            dequeue_worker(),
            dequeue_worker()
        )

        # 確認所有訊息都被處理
        total_processed = sum(len(msgs) for msgs in results)
        assert total_processed == message_count

    @pytest.mark.asyncio
    async def test_producer_consumer_pattern(self, queue):
        """測試生產者-消費者模式"""
        produced = []
        consumed = []

        async def producer():
            for i in range(20):
                msg = Message(payload={"value": i})
                await queue.enqueue(msg)
                produced.append(i)
                await asyncio.sleep(0.01)

        async def consumer():
            for _ in range(20):
                msg = await queue.dequeue(timeout=5)
                if msg:
                    consumed.append(msg.payload["value"])
                    if hasattr(msg, '_amqp_message'):
                        await msg._amqp_message.ack()

        # 同時啟動生產者與消費者
        await asyncio.gather(producer(), consumer())

        # 確認所有訊息都被消費
        assert len(produced) == 20
        assert len(consumed) == 20
        assert sorted(consumed) == sorted(produced)


@requires_rabbitmq
class TestRabbitMQQueueFailureHandling:
    """RabbitMQ Queue 錯誤處理測試"""

    @pytest.fixture
    async def queue(self):
        """建立測試用佇列"""
        q = RabbitMQQueue(
            url=RABBITMQ_URL,
            exchange_name="test.failure.commands",
            queue_name="test.failure.queue",
            dlx_name="test.failure.dlx",
            dlq_name="test.failure.dlq"
        )

        await q.initialize()
        await q.clear()

        yield q

        await q.clear()
        await q.close()

    @pytest.mark.asyncio
    async def test_nack_and_requeue(self, queue):
        """測試 nack 與重新入隊"""
        msg = Message(
            payload={"test": "nack"},
            max_retries=3
        )

        await queue.enqueue(msg)

        # 取出訊息
        received = await queue.dequeue(timeout=2)
        assert received is not None

        # Nack（重新入隊）
        if hasattr(received, '_amqp_message'):
            await received._amqp_message.nack(requeue=True)

        # 應該可以再次取出
        await asyncio.sleep(0.5)
        received_again = await queue.dequeue(timeout=2)
        assert received_again is not None
        assert received_again.id == msg.id

        if hasattr(received_again, '_amqp_message'):
            await received_again._amqp_message.ack()

    @pytest.mark.asyncio
    async def test_invalid_connection_url(self):
        """測試無效的連線 URL"""
        queue = RabbitMQQueue(url="amqp://invalid:invalid@nonexistent:5672/")

        with pytest.raises(Exception):
            await queue.initialize()

    @pytest.mark.asyncio
    async def test_health_check_when_unhealthy(self):
        """測試不健康狀態的健康檢查"""
        queue = RabbitMQQueue(url="amqp://invalid:invalid@nonexistent:5672/")

        health = await queue.health_check()

        assert health["status"] == "unhealthy"
        assert "error" in health
