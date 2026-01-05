"""
Queue Implementation Comparison Tests
比較 MemoryQueue 與 RabbitMQQueue 的行為一致性
"""

import asyncio
import os
import pytest

from src.robot_service.queue import (
    Message,
    MessagePriority,
    MemoryQueue,
    RabbitMQQueue,
)


RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")

requires_rabbitmq = pytest.mark.skipif(
    not os.getenv("TEST_WITH_RABBITMQ"),
    reason="Set TEST_WITH_RABBITMQ=1 to run RabbitMQ integration tests"
)


@pytest.fixture(params=["memory"])
@pytest.mark.asyncio
async def queue_impl(request):
    """參數化 fixture，支援多種佇列實作"""
    impl_type = request.param

    if impl_type == "memory":
        queue = MemoryQueue(max_size=1000)
    elif impl_type == "rabbitmq":
        queue = RabbitMQQueue(
            url=RABBITMQ_URL,
            exchange_name="test.comparison.commands",
            queue_name="test.comparison.queue"
        )
        await queue.initialize()
        await queue.clear()
    else:
        raise ValueError(f"Unknown queue implementation: {impl_type}")

    yield queue

    # 清理
    await queue.clear()
    if hasattr(queue, 'close'):
        await queue.close()


@pytest.fixture(params=["memory", "rabbitmq"])
@pytest.mark.asyncio
async def queue_impl_all(request):
    """參數化 fixture，包含所有實作（需要 RabbitMQ）"""
    impl_type = request.param

    if impl_type == "rabbitmq" and not os.getenv("TEST_WITH_RABBITMQ"):
        pytest.skip("RabbitMQ tests disabled")

    if impl_type == "memory":
        queue = MemoryQueue(max_size=1000)
    elif impl_type == "rabbitmq":
        queue = RabbitMQQueue(
            url=RABBITMQ_URL,
            exchange_name="test.comparison.commands",
            queue_name="test.comparison.queue"
        )
        await queue.initialize()
        await queue.clear()
    else:
        raise ValueError(f"Unknown queue implementation: {impl_type}")

    yield queue

    # 清理
    await queue.clear()
    if hasattr(queue, 'close'):
        await queue.close()


class TestQueueInterfaceCompliance:
    """測試所有佇列實作是否符合 QueueInterface 規範"""

    @pytest.mark.asyncio
    async def test_basic_enqueue_dequeue(self, queue_impl):
        """測試基本入隊與出隊"""
        msg = Message(
            payload={"command": "test"},
            priority=MessagePriority.NORMAL
        )

        # 入隊
        result = await queue_impl.enqueue(msg)
        assert result is True

        # 出隊
        received = await queue_impl.dequeue(timeout=2)
        assert received is not None
        assert received.id == msg.id
        assert received.payload == msg.payload

        # 確認處理
        await queue_impl.ack(received.id)

    @pytest.mark.asyncio
    async def test_priority_ordering(self, queue_impl):
        """測試優先權排序"""
        messages = [
            Message(payload={"p": "low"}, priority=MessagePriority.LOW),
            Message(payload={"p": "normal"}, priority=MessagePriority.NORMAL),
            Message(payload={"p": "high"}, priority=MessagePriority.HIGH),
            Message(payload={"p": "urgent"}, priority=MessagePriority.URGENT),
        ]

        # 以非順序方式入隊
        for msg in [messages[1], messages[3], messages[0], messages[2]]:
            await queue_impl.enqueue(msg)

        # 給 RabbitMQ 時間處理
        if isinstance(queue_impl, RabbitMQQueue):
            await asyncio.sleep(0.5)

        # 出隊應按優先權排序
        received = []
        for _ in range(4):
            msg = await queue_impl.dequeue(timeout=2)
            if msg:
                received.append(msg)
                await queue_impl.ack(msg.id)

        assert len(received) == 4

        # 驗證優先權順序
        priorities = [msg.priority for msg in received]
        expected = [
            MessagePriority.URGENT,
            MessagePriority.HIGH,
            MessagePriority.NORMAL,
            MessagePriority.LOW
        ]
        assert priorities == expected

    @pytest.mark.asyncio
    async def test_queue_size(self, queue_impl):
        """測試佇列大小查詢"""
        # 初始為空
        size = await queue_impl.size()
        assert size == 0

        # 加入訊息
        for i in range(5):
            msg = Message(payload={"index": i})
            await queue_impl.enqueue(msg)

        # 給 RabbitMQ 時間處理
        if isinstance(queue_impl, RabbitMQQueue):
            await asyncio.sleep(0.2)

        size = await queue_impl.size()
        assert size == 5

    @pytest.mark.asyncio
    async def test_clear(self, queue_impl):
        """測試清空佇列"""
        # 加入訊息
        for i in range(10):
            await queue_impl.enqueue(Message(payload={"i": i}))

        if isinstance(queue_impl, RabbitMQQueue):
            await asyncio.sleep(0.2)

        # 清空
        await queue_impl.clear()

        # 驗證
        size = await queue_impl.size()
        assert size == 0

    @pytest.mark.asyncio
    async def test_dequeue_timeout(self, queue_impl):
        """測試出隊超時"""
        # 空佇列，應該超時
        msg = await queue_impl.dequeue(timeout=1)
        assert msg is None

    @pytest.mark.asyncio
    async def test_health_check(self, queue_impl):
        """測試健康檢查"""
        health = await queue_impl.health_check()

        assert "status" in health
        assert health["status"] == "healthy"
        assert "type" in health
        assert "timestamp" in health


class TestQueuePerformance:
    """測試不同佇列實作的效能"""

    @pytest.mark.asyncio
    async def test_throughput(self, queue_impl):
        """測試吞吐量"""
        message_count = 100
        messages = [
            Message(payload={"index": i}, priority=MessagePriority.NORMAL)
            for i in range(message_count)
        ]

        # 入隊
        import time
        start = time.time()
        for msg in messages:
            await queue_impl.enqueue(msg)
        enqueue_time = time.time() - start

        if isinstance(queue_impl, RabbitMQQueue):
            await asyncio.sleep(0.5)

        # 出隊
        start = time.time()
        for _ in range(message_count):
            msg = await queue_impl.dequeue(timeout=2)
            if msg:
                await queue_impl.ack(msg.id)
        dequeue_time = time.time() - start

        # 記錄效能資訊（用於分析）
        impl_type = "Memory" if isinstance(queue_impl, MemoryQueue) else "RabbitMQ"
        print(f"\n{impl_type} Queue Performance:")
        print(f"  Enqueue: {message_count} messages in {enqueue_time:.3f}s "
              f"({message_count / enqueue_time:.1f} msg/s)")
        print(f"  Dequeue: {message_count} messages in {dequeue_time:.3f}s "
              f"({message_count / dequeue_time:.1f} msg/s)")


class TestQueueReliability:
    """測試佇列的可靠性與錯誤處理"""

    @pytest.mark.asyncio
    async def test_message_serialization(self, queue_impl):
        """測試訊息序列化的完整性"""
        original = Message(
            payload={
                "command": "complex_action",
                "params": {
                    "nested": {"value": 123},
                    "list": [1, 2, 3],
                    "string": "test"
                }
            },
            priority=MessagePriority.HIGH,
            trace_id="trace-abc-123",
            correlation_id="corr-def-456",
            max_retries=5,
            timeout_seconds=60
        )

        await queue_impl.enqueue(original)

        if isinstance(queue_impl, RabbitMQQueue):
            await asyncio.sleep(0.2)

        received = await queue_impl.dequeue(timeout=2)

        assert received is not None
        assert received.id == original.id
        assert received.payload == original.payload
        assert received.priority == original.priority
        assert received.trace_id == original.trace_id
        assert received.correlation_id == original.correlation_id
        assert received.max_retries == original.max_retries
        assert received.timeout_seconds == original.timeout_seconds

        await queue_impl.ack(received.id)

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, queue_impl):
        """測試並發操作的正確性"""
        message_count = 50

        async def producer():
            for i in range(message_count):
                msg = Message(payload={"value": i})
                await queue_impl.enqueue(msg)

        async def consumer():
            consumed = []
            for _ in range(message_count):
                msg = await queue_impl.dequeue(timeout=5)
                if msg:
                    consumed.append(msg.payload["value"])
                    await queue_impl.ack(msg.id)
            return consumed

        # 同時運行生產者與消費者
        producer_task = asyncio.create_task(producer())
        consumer_task = asyncio.create_task(consumer())

        await producer_task
        consumed = await consumer_task

        # 驗證所有訊息都被處理
        assert len(consumed) == message_count
        assert sorted(consumed) == list(range(message_count))


class TestMemoryQueueSpecific:
    """MemoryQueue 特定測試"""

    @pytest.mark.asyncio
    async def test_max_size_limit(self):
        """測試最大佇列大小限制"""
        queue = MemoryQueue(max_size=5)

        # 填滿佇列
        for i in range(5):
            result = await queue.enqueue(Message(payload={"i": i}))
            assert result is True

        # 嘗試加入第 6 個訊息（應該失敗）
        result = await queue.enqueue(Message(payload={"i": 6}))
        assert result is False

    @pytest.mark.asyncio
    async def test_in_flight_tracking(self):
        """測試處理中訊息追蹤"""
        queue = MemoryQueue()

        msg = Message(payload={"test": "in_flight"})
        await queue.enqueue(msg)

        # 出隊但不 ack
        received = await queue.dequeue(timeout=1)
        assert received is not None

        # 訊息應該在 in_flight 中
        health = await queue.health_check()
        assert health["in_flight_count"] == 1

        # Ack 後應該移除
        await queue.ack(received.id)
        health = await queue.health_check()
        assert health["in_flight_count"] == 0


@requires_rabbitmq
class TestRabbitMQQueueSpecific:
    """RabbitMQ Queue 特定測試"""

    @pytest.mark.asyncio
    async def test_connection_pool(self):
        """測試連線池功能"""
        queue = RabbitMQQueue(
            url=RABBITMQ_URL,
            connection_pool_size=3,
            channel_pool_size=5
        )

        await queue.initialize()

        # 並發操作應該使用連線池
        tasks = []
        for i in range(10):
            msg = Message(payload={"i": i})
            tasks.append(queue.enqueue(msg))

        results = await asyncio.gather(*tasks)
        assert all(results)

        await queue.close()

    @pytest.mark.asyncio
    async def test_dead_letter_queue_setup(self):
        """測試 DLQ 設置"""
        queue = RabbitMQQueue(
            url=RABBITMQ_URL,
            exchange_name="test.dlq.commands",
            queue_name="test.dlq.queue",
            dlx_name="test.dlq.dlx",
            dlq_name="test.dlq.dlq"
        )

        await queue.initialize()

        health = await queue.health_check()
        assert health["status"] == "healthy"
        assert health["dlx"] == "test.dlq.dlx"
        assert health["dlq"] == "test.dlq.dlq"

        await queue.close()
