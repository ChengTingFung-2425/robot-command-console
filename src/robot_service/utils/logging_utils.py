"""
日誌工具模組
提供統一的 JSON 結構化日誌格式器
"""

import logging
import sys
from datetime import datetime, timezone
from typing import Optional

from pythonjsonlogger import jsonlogger


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """
    自定義 JSON 日誌格式器
    
    提供統一的結構化日誌格式，包含：
    - timestamp: UTC ISO 格式時間戳
    - level: 日誌級別
    - event: 事件名稱（logger 名稱）
    - service: 服務名稱
    - message: 日誌訊息
    """
    
    def __init__(
        self,
        *args,
        service_name: str = "robot-service",
        **kwargs
    ):
        """
        初始化格式器
        
        Args:
            service_name: 服務名稱，用於日誌中的 service 欄位
        """
        super().__init__(*args, **kwargs)
        self.service_name = service_name
    
    def add_fields(self, log_record, record, message_dict):
        """添加自定義欄位到日誌記錄"""
        super().add_fields(log_record, record, message_dict)
        log_record['timestamp'] = datetime.now(timezone.utc).isoformat()
        log_record['level'] = record.levelname
        log_record['event'] = record.name
        log_record['service'] = self.service_name


def setup_json_logging(
    logger_name: Optional[str] = None,
    service_name: str = "robot-service",
    level: int = logging.INFO,
    stream=None,
) -> logging.Logger:
    """
    設定 JSON 結構化日誌
    
    Args:
        logger_name: Logger 名稱，None 則使用 root logger
        service_name: 服務名稱
        level: 日誌級別
        stream: 輸出流，默認為 sys.stdout
        
    Returns:
        配置好的 Logger 實例
    """
    if stream is None:
        stream = sys.stdout
    
    # 建立處理器
    handler = logging.StreamHandler(stream)
    formatter = CustomJsonFormatter(
        '%(timestamp)s %(level)s %(event)s %(message)s',
        service_name=service_name
    )
    handler.setFormatter(formatter)
    
    # 取得或建立 logger
    logger = logging.getLogger(logger_name)
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(level)
    
    return logger


def get_logger(name: str, service_name: str = "robot-service") -> logging.Logger:
    """
    取得配置好 JSON 格式的 logger
    
    Args:
        name: Logger 名稱
        service_name: 服務名稱
        
    Returns:
        配置好的 Logger 實例
    """
    return setup_json_logging(
        logger_name=name,
        service_name=service_name
    )
