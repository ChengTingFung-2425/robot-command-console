"""
Configuration Export and Injection Utility
環境變數匯出與注入工具，支援配置合併與動態注入
"""

import os
from typing import Dict, Any, Optional
from .edge_queue_config import EdgeQueueConfig


class ConfigExporter:
    """配置匯出器，將配置轉換為環境變數格式"""

    @staticmethod
    def export_memory_config(queue_max_size: int = 1000) -> Dict[str, str]:
        """
        匯出 MemoryQueue 配置

        Args:
            queue_max_size: 佇列最大大小

        Returns:
            環境變數字典
        """
        return {
            "EDGE_QUEUE_TYPE": "memory",
            "EDGE_QUEUE_MAX_SIZE": str(queue_max_size),
        }

    @staticmethod
    def export_rabbitmq_config(
        rabbitmq_url: str = "amqp://guest:guest@localhost:5672/",
        exchange_name: str = "robot.edge.commands",
        queue_name: str = "robot.edge.queue",
        dlx_name: str = "robot.edge.dlx",
        dlq_name: str = "robot.edge.dlq",
        prefetch_count: int = 10,
        conn_pool_size: int = 2,
        channel_pool_size: int = 10,
    ) -> Dict[str, str]:
        """
        匯出 RabbitMQ 配置

        Args:
            rabbitmq_url: RabbitMQ 連線 URL
            exchange_name: Exchange 名稱
            queue_name: Queue 名稱
            dlx_name: Dead Letter Exchange 名稱
            dlq_name: Dead Letter Queue 名稱
            prefetch_count: Prefetch 數量
            conn_pool_size: 連線池大小
            channel_pool_size: Channel 池大小

        Returns:
            環境變數字典
        """
        return {
            "EDGE_QUEUE_TYPE": "rabbitmq",
            "RABBITMQ_URL": rabbitmq_url,
            "RABBITMQ_EXCHANGE_NAME": exchange_name,
            "RABBITMQ_QUEUE_NAME": queue_name,
            "RABBITMQ_DLX_NAME": dlx_name,
            "RABBITMQ_DLQ_NAME": dlq_name,
            "RABBITMQ_PREFETCH_COUNT": str(prefetch_count),
            "RABBITMQ_CONN_POOL_SIZE": str(conn_pool_size),
            "RABBITMQ_CHANNEL_POOL_SIZE": str(channel_pool_size),
        }

    @staticmethod
    def export_sqs_config(
        queue_url: Optional[str] = None,
        queue_name: str = "robot-edge-commands-queue",
        dlq_name: str = "robot-edge-commands-dlq",
        region_name: str = "us-east-1",
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        visibility_timeout: int = 30,
        wait_time_seconds: int = 10,
        use_fifo: bool = False,
    ) -> Dict[str, str]:
        """
        匯出 AWS SQS 配置

        Args:
            queue_url: SQS 佇列 URL
            queue_name: 佇列名稱
            dlq_name: Dead Letter Queue 名稱
            region_name: AWS 區域
            aws_access_key_id: AWS Access Key
            aws_secret_access_key: AWS Secret Key
            visibility_timeout: 可見性超時（秒）
            wait_time_seconds: 長輪詢等待時間（秒）
            use_fifo: 是否使用 FIFO 佇列

        Returns:
            環境變數字典
        """
        config = {
            "EDGE_QUEUE_TYPE": "sqs",
            "SQS_QUEUE_NAME": queue_name,
            "SQS_DLQ_NAME": dlq_name,
            "AWS_REGION": region_name,
            "SQS_VISIBILITY_TIMEOUT": str(visibility_timeout),
            "SQS_WAIT_TIME_SECONDS": str(wait_time_seconds),
            "SQS_USE_FIFO": "true" if use_fifo else "false",
        }

        # 可選參數
        if queue_url:
            config["SQS_QUEUE_URL"] = queue_url
        if aws_access_key_id:
            config["AWS_ACCESS_KEY_ID"] = aws_access_key_id
        if aws_secret_access_key:
            config["AWS_SECRET_ACCESS_KEY"] = aws_secret_access_key

        return config

    @staticmethod
    def export_common_config(
        max_workers: int = 5,
        poll_interval: float = 0.1,
    ) -> Dict[str, str]:
        """
        匯出通用配置

        Args:
            max_workers: 最大並行工作數
            poll_interval: 輪詢間隔（秒）

        Returns:
            環境變數字典
        """
        return {
            "EDGE_MAX_WORKERS": str(max_workers),
            "EDGE_POLL_INTERVAL": str(poll_interval),
        }


class ConfigInjector:
    """配置注入器，合併並注入環境變數"""

    @staticmethod
    def merge_configs(*configs: Dict[str, str]) -> Dict[str, str]:
        """
        合併多個配置字典

        後面的配置會覆蓋前面的配置

        Args:
            *configs: 要合併的配置字典

        Returns:
            合併後的配置字典
        """
        merged = {}
        for config in configs:
            merged.update(config)
        return merged

    @staticmethod
    def inject_to_env(config: Dict[str, str], override: bool = True) -> None:
        """
        將配置注入到環境變數

        Args:
            config: 配置字典
            override: 是否覆蓋現有環境變數
        """
        for key, value in config.items():
            if override or key not in os.environ:
                os.environ[key] = value

    @staticmethod
    def export_to_shell_script(config: Dict[str, str], filename: str = "config.sh") -> str:
        """
        將配置匯出為 shell script

        Args:
            config: 配置字典
            filename: 輸出檔案名稱

        Returns:
            Shell script 內容
        """
        lines = ["#!/bin/bash", "# Auto-generated configuration", ""]

        for key, value in sorted(config.items()):
            # 處理特殊字符
            safe_value = value.replace('"', '\\"')
            lines.append(f'export {key}="{safe_value}"')

        script = "\n".join(lines)

        # 寫入檔案
        with open(filename, 'w') as f:
            f.write(script)

        return script

    @staticmethod
    def export_to_docker_env(config: Dict[str, str], filename: str = ".env") -> str:
        """
        將配置匯出為 Docker .env 格式

        Args:
            config: 配置字典
            filename: 輸出檔案名稱

        Returns:
            .env 檔案內容
        """
        lines = ["# Auto-generated configuration for Docker", ""]

        for key, value in sorted(config.items()):
            lines.append(f"{key}={value}")

        content = "\n".join(lines)

        # 寫入檔案
        with open(filename, 'w') as f:
            f.write(content)

        return content

    @staticmethod
    def export_to_kubernetes_configmap(
        config: Dict[str, str],
        name: str = "robot-edge-config",
        namespace: str = "default",
        filename: str = "configmap.yaml"
    ) -> str:
        """
        將配置匯出為 Kubernetes ConfigMap

        Args:
            config: 配置字典
            name: ConfigMap 名稱
            namespace: Kubernetes namespace
            filename: 輸出檔案名稱

        Returns:
            ConfigMap YAML 內容
        """
        lines = [
            "apiVersion: v1",
            "kind: ConfigMap",
            "metadata:",
            f"  name: {name}",
            f"  namespace: {namespace}",
            "data:",
        ]

        for key, value in sorted(config.items()):
            lines.append(f'  {key}: "{value}"')

        content = "\n".join(lines)

        # 寫入檔案
        with open(filename, 'w') as f:
            f.write(content)

        return content


# 便利函式
def create_memory_env() -> Dict[str, str]:
    """建立 MemoryQueue 環境變數配置"""
    return ConfigInjector.merge_configs(
        ConfigExporter.export_memory_config(),
        ConfigExporter.export_common_config()
    )


def create_rabbitmq_env(
    url: str = "amqp://guest:guest@localhost:5672/",
    **kwargs
) -> Dict[str, str]:
    """建立 RabbitMQ 環境變數配置"""
    return ConfigInjector.merge_configs(
        ConfigExporter.export_rabbitmq_config(rabbitmq_url=url, **kwargs),
        ConfigExporter.export_common_config()
    )


def create_sqs_env(
    region: str = "us-east-1",
    **kwargs
) -> Dict[str, str]:
    """建立 AWS SQS 環境變數配置"""
    return ConfigInjector.merge_configs(
        ConfigExporter.export_sqs_config(region_name=region, **kwargs),
        ConfigExporter.export_common_config()
    )


def inject_and_create_manager(config: Dict[str, str]):
    """
    注入配置並建立 ServiceManager

    Args:
        config: 配置字典

    Returns:
        ServiceManager 實例
    """
    ConfigInjector.inject_to_env(config)

    from .edge_queue_config import create_service_manager_from_env
    return create_service_manager_from_env()


# 範例使用
def example_usage():
    """範例：如何使用配置匯出與注入"""

    # 方式 1: 建立並合併配置
    rabbitmq_config = ConfigExporter.export_rabbitmq_config(
        rabbitmq_url="amqp://user:pass@rabbitmq.example.com:5672/",
        exchange_name="production.commands"
    )
    common_config = ConfigExporter.export_common_config(max_workers=10)

    merged = ConfigInjector.merge_configs(rabbitmq_config, common_config)

    # 方式 2: 注入到環境變數
    ConfigInjector.inject_to_env(merged)

    # 方式 3: 匯出為 shell script
    ConfigInjector.export_to_shell_script(merged, "config.sh")

    # 方式 4: 匯出為 Docker .env
    ConfigInjector.export_to_docker_env(merged, ".env")

    # 方式 5: 匯出為 Kubernetes ConfigMap
    ConfigInjector.export_to_kubernetes_configmap(
        merged,
        name="robot-edge-config",
        namespace="production"
    )

    # 方式 6: 便利函式
    sqs_env = create_sqs_env(
        region="us-west-2",
        queue_name="production-robot-commands"
    )
    manager = inject_and_create_manager(sqs_env)

    return manager


if __name__ == "__main__":
    # 示範用法
    print("=== Memory Queue Config ===")
    memory_env = create_memory_env()
    for k, v in memory_env.items():
        print(f"{k}={v}")

    print("\n=== RabbitMQ Config ===")
    rabbitmq_env = create_rabbitmq_env()
    for k, v in rabbitmq_env.items():
        print(f"{k}={v}")

    print("\n=== AWS SQS Config ===")
    sqs_env = create_sqs_env()
    for k, v in sqs_env.items():
        print(f"{k}={v}")
