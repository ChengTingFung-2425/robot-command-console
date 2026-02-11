"""
Edge RabbitMQ Integration Tests
測試 Edge 層的 RabbitMQ 整合
"""

import asyncio
import os
import pytest

from robot_service.service_manager import ServiceManager
from robot_service.edge_queue_config import EdgeQueueConfig, create_service_manager_from_env
from robot_service.queue import MessagePriority


RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")

requires_rabbitmq = pytest.mark.skipif(
    not os.getenv("TEST_WITH_RABBITMQ"),
    reason="Set TEST_WITH_RABBITMQ=1 to run RabbitMQ integration tests"
)


class TestEdgeQueueConfig:
    """測試 Edge 佇列配置"""

    def test_default_queue_type(self):
        """測試預設佇列類型"""
        queue_type = EdgeQueueConfig.get_queue_type()
        assert queue_type in ["memory", "rabbitmq"]

    def test_get_rabbitmq_url(self):
        """測試取得 RabbitMQ URL"""
        url = EdgeQueueConfig.get_rabbitmq_url()
        assert url.startswith("amqp://")

    def test_get_rabbitmq_config(self):
        """測試取得 RabbitMQ 配置"""
        config = EdgeQueueConfig.get_rabbitmq_config()

        assert "exchange_name" in config
        assert "queue_name" in config
        assert "dlx_name" in config
        assert "dlq_name" in config
        assert "prefetch_count" in config

    def test_get_service_manager_config(self):
        """測試取得 ServiceManager 配置"""
        config = EdgeQueueConfig.get_service_manager_config()

        assert "queue_type" in config
        assert "max_workers" in config
        assert "poll_interval" in config

    def test_get_queue_info(self):
        """測試取得佇列資訊"""
        from src.robot_service.edge_queue_config import get_queue_info

        info = get_queue_info()

        assert "queue_type" in info
        assert "rabbitmq_enabled" in info


class TestServiceManagerWithMemoryQueue:
    """測試 ServiceManager 與 MemoryQueue"""

    @pytest.mark.asyncio
    async def test_create_with_memory_queue(self):
        """測試建立 MemoryQueue ServiceManager"""
        manager = ServiceManager(
            queue_type="memory",
            queue_max_size=100,
            max_workers=3
        )

        assert manager.queue_type == "memory"
        assert manager.max_workers == 3

        await manager.start()

        # 提交測試指令
        message_id = await manager.submit_command(
            payload={"command": "test", "value": 123},
            priority=MessagePriority.NORMAL
        )

        assert message_id is not None

        await asyncio.sleep(0.5)
        await manager.stop()

    @pytest.mark.asyncio
    async def test_memory_queue_operations(self):
        """測試 MemoryQueue 基本操作"""
        manager = ServiceManager(queue_type="memory", max_workers=2)

        await manager.start()

        # 提交多個指令
        ids = []
        for i in range(5):
            msg_id = await manager.submit_command(
                payload={"index": i},
                priority=MessagePriority.NORMAL
            )
            ids.append(msg_id)

        assert len(ids) == 5
        assert all(id is not None for id in ids)

        # 等待處理
        await asyncio.sleep(1)

        # 檢查健康狀態
        health = await manager.health_check()
        assert health["status"] == "healthy"

        await manager.stop()


@requires_rabbitmq
class TestServiceManagerWithRabbitMQ:
    """測試 ServiceManager 與 RabbitMQ"""

    @pytest.mark.asyncio
    async def test_create_with_rabbitmq(self):
        """測試建立 RabbitMQ ServiceManager"""
        manager = ServiceManager(
            queue_type="rabbitmq",
            rabbitmq_url=RABBITMQ_URL,
            rabbitmq_config={
                "exchange_name": "test.edge.commands",
                "queue_name": "test.edge.queue",
                "dlx_name": "test.edge.dlx",
                "dlq_name": "test.edge.dlq"
            },
            max_workers=3
        )

        assert manager.queue_type == "rabbitmq"
        assert manager.max_workers == 3

        await manager.start()

        # 清空佇列
        await manager.queue.clear()

        # 提交測試指令
        message_id = await manager.submit_command(
            payload={"command": "rabbitmq_test", "value": 456},
            priority=MessagePriority.HIGH
        )

        assert message_id is not None

        await asyncio.sleep(1)
        await manager.stop()

    @pytest.mark.asyncio
    async def test_rabbitmq_queue_operations(self):
        """測試 RabbitMQ 佇列操作"""
        manager = ServiceManager(
            queue_type="rabbitmq",
            rabbitmq_url=RABBITMQ_URL,
            rabbitmq_config={
                "exchange_name": "test.edge.ops.commands",
                "queue_name": "test.edge.ops.queue"
            },
            max_workers=5
        )

        await manager.start()
        await manager.queue.clear()

        # 提交不同優先權的指令
        priorities = [
            MessagePriority.LOW,
            MessagePriority.NORMAL,
            MessagePriority.HIGH,
            MessagePriority.URGENT
        ]

        ids = []
        for i, priority in enumerate(priorities):
            msg_id = await manager.submit_command(
                payload={"index": i, "priority": priority.name},
                priority=priority
            )
            ids.append(msg_id)

        assert len(ids) == 4
        assert all(id is not None for id in ids)

        # 等待處理
        await asyncio.sleep(2)

        # 檢查健康狀態
        health = await manager.health_check()
        assert health["status"] == "healthy"
        assert health["type"] == "rabbitmq"

        await manager.stop()

    @pytest.mark.asyncio
    async def test_rabbitmq_connection_pooling(self):
        """測試 RabbitMQ 連線池"""
        manager = ServiceManager(
            queue_type="rabbitmq",
            rabbitmq_url=RABBITMQ_URL,
            rabbitmq_config={
                "exchange_name": "test.edge.pool.commands",
                "queue_name": "test.edge.pool.queue",
                "connection_pool_size": 3,
                "channel_pool_size": 10
            },
            max_workers=10
        )

        await manager.start()
        await manager.queue.clear()

        # 並發提交大量指令
        tasks = []
        for i in range(50):
            task = manager.submit_command(
                payload={"index": i},
                priority=MessagePriority.NORMAL
            )
            tasks.append(task)

        ids = await asyncio.gather(*tasks)

        assert len(ids) == 50
        assert all(id is not None for id in ids)

        # 等待處理
        await asyncio.sleep(3)

        await manager.stop()

    @pytest.mark.asyncio
    async def test_create_from_env(self):
        """測試從環境變數建立 ServiceManager"""
        # 設定環境變數
        os.environ["EDGE_QUEUE_TYPE"] = "rabbitmq"
        os.environ["RABBITMQ_URL"] = RABBITMQ_URL
        os.environ["RABBITMQ_EXCHANGE_NAME"] = "test.edge.env.commands"
        os.environ["RABBITMQ_QUEUE_NAME"] = "test.edge.env.queue"
        os.environ["EDGE_MAX_WORKERS"] = "4"

        manager = create_service_manager_from_env()

        assert manager.queue_type == "rabbitmq"
        assert manager.max_workers == 4

        await manager.start()

        # 測試提交指令
        msg_id = await manager.submit_command(
            payload={"test": "env_config"},
            priority=MessagePriority.NORMAL
        )

        assert msg_id is not None

        await asyncio.sleep(1)
        await manager.stop()

        # 清理環境變數
        del os.environ["EDGE_QUEUE_TYPE"]
        del os.environ["RABBITMQ_EXCHANGE_NAME"]
        del os.environ["RABBITMQ_QUEUE_NAME"]
        del os.environ["EDGE_MAX_WORKERS"]


@requires_rabbitmq
class TestEdgeRabbitMQReliability:
    """測試 Edge RabbitMQ 可靠性"""

    @pytest.mark.asyncio
    async def test_message_persistence(self):
        """測試訊息持久化"""
        manager = ServiceManager(
            queue_type="rabbitmq",
            rabbitmq_url=RABBITMQ_URL,
            rabbitmq_config={
                "exchange_name": "test.edge.persist.commands",
                "queue_name": "test.edge.persist.queue"
            }
        )

        await manager.start()
        await manager.queue.clear()

        # 發送持久化訊息
        msg_id = await manager.submit_command(
            payload={"persistent": True, "data": "important"},
            priority=MessagePriority.HIGH
        )

        assert msg_id is not None

        # 訊息應該在佇列中
        size = await manager.queue.size()
        assert size > 0

        await manager.stop()

    @pytest.mark.asyncio
    async def test_dead_letter_queue(self):
        """測試 Dead Letter Queue"""
        manager = ServiceManager(
            queue_type="rabbitmq",
            rabbitmq_url=RABBITMQ_URL,
            rabbitmq_config={
                "exchange_name": "test.edge.dlq.commands",
                "queue_name": "test.edge.dlq.queue",
                "dlx_name": "test.edge.dlq.dlx",
                "dlq_name": "test.edge.dlq.dlq"
            }
        )

        await manager.start()

        # 檢查 DLQ 設置
        health = await manager.health_check()
        assert "dlx" in health
        assert "dlq" in health

        await manager.stop()

    @pytest.mark.asyncio
    async def test_health_check(self):
        """測試健康檢查"""
        manager = ServiceManager(
            queue_type="rabbitmq",
            rabbitmq_url=RABBITMQ_URL,
            rabbitmq_config={
                "exchange_name": "test.edge.health.commands",
                "queue_name": "test.edge.health.queue"
            }
        )

        await manager.start()

        health = await manager.health_check()

        assert health["status"] == "healthy"
        assert health["type"] == "rabbitmq"
        assert "connected" in health
        assert health["connected"] is True
        assert "queue_size" in health
        assert "statistics" in health

        await manager.stop()
