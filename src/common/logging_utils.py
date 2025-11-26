"""
日誌工具模組
提供統一的 JSON 結構化日誌格式器

此模組被 Edge 和 Server 環境共用
"""

import logging
import sys
from datetime import datetime, timezone
from typing import Optional

try:
    from pythonjsonlogger import jsonlogger
    HAS_JSON_LOGGER = True
except ImportError:
    HAS_JSON_LOGGER = False


class CustomJsonFormatter:
    """
    自定義 JSON 日誌格式器
    
    提供統一的結構化日誌格式，包含：
    - timestamp: UTC ISO 格式時間戳
    - level: 日誌級別
    - event: 事件名稱（logger 名稱）
    - service: 服務名稱
    - message: 日誌訊息
    
    如果 pythonjsonlogger 未安裝，則使用基本格式
    """
    
    def __new__(cls, *args, service_name: str = "robot-service", **kwargs):
        """
        建立格式器實例
        
        根據是否有 pythonjsonlogger 選擇實作
        """
        if HAS_JSON_LOGGER:
            return _JsonLoggerFormatter(*args, service_name=service_name, **kwargs)
        else:
            return _BasicFormatter(*args, service_name=service_name, **kwargs)


class _JsonLoggerFormatter(jsonlogger.JsonFormatter if HAS_JSON_LOGGER else object):
    """使用 pythonjsonlogger 的 JSON 格式器"""
    
    def __init__(self, *args, service_name: str = "robot-service", **kwargs):
        if HAS_JSON_LOGGER:
            super().__init__(*args, **kwargs)
        self.service_name = service_name
    
    def add_fields(self, log_record, record, message_dict):
        """添加自定義欄位到日誌記錄"""
        if HAS_JSON_LOGGER:
            super().add_fields(log_record, record, message_dict)
        log_record['timestamp'] = datetime.now(timezone.utc).isoformat()
        log_record['level'] = record.levelname
        log_record['event'] = record.name
        log_record['service'] = self.service_name


class _BasicFormatter(logging.Formatter):
    """基本格式器（當 pythonjsonlogger 不可用時）"""
    
    def __init__(self, *args, service_name: str = "robot-service", **kwargs):
        # 忽略 pythonjsonlogger 格式字串，使用自己的格式
        fmt = '%(asctime)s - %(levelname)s - [%(name)s] - %(message)s'
        super().__init__(fmt)
        self.service_name = service_name


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
    
    if HAS_JSON_LOGGER:
        formatter = CustomJsonFormatter(
            '%(timestamp)s %(level)s %(event)s %(message)s',
            service_name=service_name
        )
    else:
        formatter = CustomJsonFormatter(service_name=service_name)
    
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
