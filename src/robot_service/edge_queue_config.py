"""
Edge Queue Configuration
邊緣層佇列配置管理
"""

import os
from typing import Dict, Any


class EdgeQueueConfig:
    """Edge 層佇列配置"""

    @staticmethod
    def get_queue_type() -> str:
        """
        取得佇列類型

        從環境變數 EDGE_QUEUE_TYPE 讀取，預設為 memory

        Returns:
            "memory" 或 "rabbitmq"
        """
        return os.getenv("EDGE_QUEUE_TYPE", "memory").lower()

    @staticmethod
    def get_rabbitmq_url() -> str:
        """
        取得 RabbitMQ 連線 URL

        從環境變數 RABBITMQ_URL 讀取，預設為本地開發環境

        Returns:
            RabbitMQ 連線 URL
        """
        return os.getenv(
            "RABBITMQ_URL",
            "amqp://guest:guest@localhost:5672/"
        )

    @staticmethod
    def get_rabbitmq_config() -> Dict[str, Any]:
        """
        取得 RabbitMQ 詳細配置

        支援透過環境變數自訂：
        - RABBITMQ_EXCHANGE_NAME: Exchange 名稱
        - RABBITMQ_QUEUE_NAME: Queue 名稱
        - RABBITMQ_DLX_NAME: Dead Letter Exchange 名稱
        - RABBITMQ_DLQ_NAME: Dead Letter Queue 名稱
        - RABBITMQ_PREFETCH_COUNT: Prefetch 數量
        - RABBITMQ_CONN_POOL_SIZE: 連線池大小
        - RABBITMQ_CHANNEL_POOL_SIZE: Channel 池大小

        Returns:
            RabbitMQ 配置字典
        """
        return {
            "exchange_name": os.getenv("RABBITMQ_EXCHANGE_NAME", "robot.edge.commands"),
            "queue_name": os.getenv("RABBITMQ_QUEUE_NAME", "robot.edge.queue"),
            "dlx_name": os.getenv("RABBITMQ_DLX_NAME", "robot.edge.dlx"),
            "dlq_name": os.getenv("RABBITMQ_DLQ_NAME", "robot.edge.dlq"),
            "prefetch_count": int(os.getenv("RABBITMQ_PREFETCH_COUNT", "10")),
            "connection_pool_size": int(os.getenv("RABBITMQ_CONN_POOL_SIZE", "2")),
            "channel_pool_size": int(os.getenv("RABBITMQ_CHANNEL_POOL_SIZE", "10")),
        }

    @staticmethod
    def get_service_manager_config() -> Dict[str, Any]:
        """
        取得 ServiceManager 完整配置

        整合所有配置選項，方便直接傳入 ServiceManager

        Returns:
            ServiceManager 配置字典
        """
        queue_type = EdgeQueueConfig.get_queue_type()

        config = {
            "queue_type": queue_type,
            "max_workers": int(os.getenv("EDGE_MAX_WORKERS", "5")),
            "poll_interval": float(os.getenv("EDGE_POLL_INTERVAL", "0.1")),
        }

        if queue_type == "rabbitmq":
            config["rabbitmq_url"] = EdgeQueueConfig.get_rabbitmq_url()
            config["rabbitmq_config"] = EdgeQueueConfig.get_rabbitmq_config()
        else:
            config["queue_max_size"] = int(os.getenv("EDGE_QUEUE_MAX_SIZE", "1000"))

        return config

    @staticmethod
    def is_rabbitmq_enabled() -> bool:
        """
        檢查是否啟用 RabbitMQ

        Returns:
            是否啟用 RabbitMQ
        """
        return EdgeQueueConfig.get_queue_type() == "rabbitmq"

    @staticmethod
    def get_health_check_config() -> Dict[str, Any]:
        """
        取得健康檢查配置

        Returns:
            健康檢查配置
        """
        return {
            "enabled": os.getenv("EDGE_HEALTH_CHECK_ENABLED", "true").lower() == "true",
            "interval": int(os.getenv("EDGE_HEALTH_CHECK_INTERVAL", "30")),
            "timeout": int(os.getenv("EDGE_HEALTH_CHECK_TIMEOUT", "5")),
        }


# 快捷函式
def create_service_manager_from_env():
    """
    從環境變數建立 ServiceManager

    這是最簡單的初始化方式，讀取所有環境變數配置

    Returns:
        ServiceManager 實例
    """
    from .service_manager import ServiceManager

    config = EdgeQueueConfig.get_service_manager_config()
    return ServiceManager(**config)


def get_queue_info() -> Dict[str, Any]:
    """
    取得當前佇列配置資訊（用於除錯與監控）

    Returns:
        佇列配置資訊
    """
    queue_type = EdgeQueueConfig.get_queue_type()

    info = {
        "queue_type": queue_type,
        "rabbitmq_enabled": EdgeQueueConfig.is_rabbitmq_enabled(),
    }

    if queue_type == "rabbitmq":
        info.update({
            "rabbitmq_url": EdgeQueueConfig.get_rabbitmq_url(),
            "rabbitmq_config": EdgeQueueConfig.get_rabbitmq_config(),
        })

    return info
