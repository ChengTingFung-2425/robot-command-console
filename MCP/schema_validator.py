"""
MCP Schema 驗證器
提供 JSON Schema 驗證以確保資料契約合規性
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from jsonschema import Draft7Validator, ValidationError
from pydantic import ValidationError as PydanticValidationError

# from .models import (
#     CommandRequest,
#     CommandResponse,
#     Event,
#     EventCategory,
#     EventSeverity,
# )


logger = logging.getLogger(__name__)


# JSON Schema 定義
COMMAND_REQUEST_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["trace_id", "timestamp", "actor", "source", "command"],
    "properties": {
        "trace_id": {
            "type": "string",
            "minLength": 1,
            "description": "全鏈路追蹤 ID (UUIDv4)"
        },
        "timestamp": {
            "type": "string",
            "format": "date-time",
            "description": "ISO8601 時間戳 (UTC)"
        },
        "actor": {
            "type": "object",
            "required": ["type", "id"],
            "properties": {
                "type": {
                    "type": "string",
                    "enum": ["human", "ai", "system"]
                },
                "id": {
                    "type": "string",
                    "minLength": 1
                },
                "name": {
                    "type": "string"
                }
            }
        },
        "source": {
            "type": "string",
            "enum": ["webui", "api", "cli", "scheduler"]
        },
        "command": {
            "type": "object",
            "required": ["id", "type", "target"],
            "properties": {
                "id": {
                    "type": "string",
                    "minLength": 1
                },
                "type": {
                    "type": "string",
                    "pattern": "^[a-z][a-z0-9_.-]+$"
                },
                "target": {
                    "type": "object",
                    "required": ["robot_id"],
                    "properties": {
                        "robot_id": {
                            "type": "string",
                            "minLength": 1
                        },
                        "robot_type": {
                            "type": "string"
                        }
                    }
                },
                "params": {
                    "type": "object"
                },
                "timeout_ms": {
                    "type": "integer",
                    "minimum": 100,
                    "maximum": 600000
                },
                "priority": {
                    "type": "string",
                    "enum": ["low", "normal", "high"]
                }
            }
        },
        "auth": {
            "type": "object",
            "properties": {
                "token": {
                    "type": "string"
                }
            }
        },
        "labels": {
            "type": "object"
        }
    }
}


COMMAND_RESPONSE_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["trace_id", "timestamp", "command"],
    "properties": {
        "trace_id": {
            "type": "string",
            "minLength": 1
        },
        "timestamp": {
            "type": "string",
            "format": "date-time"
        },
        "command": {
            "type": "object",
            "required": ["id", "status"],
            "properties": {
                "id": {
                    "type": "string",
                    "minLength": 1
                },
                "status": {
                    "type": "string",
                    "enum": ["pending", "accepted", "running", "succeeded", "failed", "cancelled"]
                }
            }
        },
        "result": {
            "type": ["object", "null"],
            "properties": {
                "data": {
                    "type": "object"
                },
                "summary": {
                    "type": "string"
                }
            }
        },
        "error": {
            "type": ["object", "null"],
            "properties": {
                "code": {
                    "type": "string",
                    "enum": [
                        "ERR_VALIDATION",
                        "ERR_UNAUTHORIZED",
                        "ERR_ROUTING",
                        "ERR_ROBOT_NOT_FOUND",
                        "ERR_ROBOT_OFFLINE",
                        "ERR_ROBOT_BUSY",
                        "ERR_ACTION_INVALID",
                        "ERR_PROTOCOL",
                        "ERR_TIMEOUT",
                        "ERR_INTERNAL"
                    ]
                },
                "message": {
                    "type": "string"
                },
                "details": {
                    "type": ["object", "null"]
                }
            },
            "required": ["code", "message"]
        }
    }
}


EVENT_LOG_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["trace_id", "timestamp", "severity", "category", "message"],
    "properties": {
        "trace_id": {
            "type": "string",
            "minLength": 1
        },
        "timestamp": {
            "type": "string",
            "format": "date-time"
        },
        "severity": {
            "type": "string",
            "enum": ["DEBUG", "INFO", "WARN", "ERROR"]
        },
        "category": {
            "type": "string",
            "enum": ["command", "auth", "protocol", "robot", "audit"]
        },
        "message": {
            "type": "string",
            "minLength": 1
        },
        "context": {
            "type": "object"
        }
    }
}


class SchemaValidator:
    """Schema 驗證器"""

    def __init__(self):
        """初始化驗證器"""
        self.command_request_validator = Draft7Validator(COMMAND_REQUEST_SCHEMA)
        self.command_response_validator = Draft7Validator(COMMAND_RESPONSE_SCHEMA)
        self.event_log_validator = Draft7Validator(EVENT_LOG_SCHEMA)

    def validate_command_request(
        self,
        data: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        驗證 CommandRequest
        
        Args:
            data: 要驗證的資料
            
        Returns:
            (is_valid, error_message)
        """
        try:
            # 使用 jsonschema 進行驗證
            self.command_request_validator.validate(data)

            # 額外驗證: 確保 timestamp 格式正確
            if "timestamp" in data:
                try:
                    datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))
                except (ValueError, AttributeError) as e:
                    return False, f"timestamp 格式不正確: {str(e)}"

            return True, None

        except ValidationError as e:
            error_msg = f"Schema 驗證失敗: {e.message} at {'.'.join(str(p) for p in e.path)}"
            logger.warning(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"驗證過程發生錯誤: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg

    def validate_command_response(
        self,
        data: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        驗證 CommandResponse
        
        Args:
            data: 要驗證的資料
            
        Returns:
            (is_valid, error_message)
        """
        try:
            self.command_response_validator.validate(data)

            # 額外驗證: 確保 timestamp 格式正確
            if "timestamp" in data:
                try:
                    datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))
                except (ValueError, AttributeError) as e:
                    return False, f"timestamp 格式不正確: {str(e)}"

            return True, None

        except ValidationError as e:
            error_msg = f"Schema 驗證失敗: {e.message} at {'.'.join(str(p) for p in e.path)}"
            logger.warning(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"驗證過程發生錯誤: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg

    def validate_event_log(
        self,
        data: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        驗證 EventLog
        
        Args:
            data: 要驗證的資料
            
        Returns:
            (is_valid, error_message)
        """
        try:
            self.event_log_validator.validate(data)

            # 額外驗證: 確保 timestamp 格式正確
            if "timestamp" in data:
                try:
                    datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))
                except (ValueError, AttributeError) as e:
                    return False, f"timestamp 格式不正確: {str(e)}"

            return True, None

        except ValidationError as e:
            error_msg = f"Schema 驗證失敗: {e.message} at {'.'.join(str(p) for p in e.path)}"
            logger.warning(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"驗證過程發生錯誤: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg

    def validate_pydantic_model(
        self,
        model_class,
        data: Dict[str, Any]
    ) -> Tuple[bool, Optional[str], Optional[Any]]:
        """
        使用 Pydantic 模型驗證資料
        
        Args:
            model_class: Pydantic 模型類別
            data: 要驗證的資料
            
        Returns:
            (is_valid, error_message, model_instance)
        """
        try:
            instance = model_class(**data)
            return True, None, instance
        except PydanticValidationError as e:
            error_msg = f"Pydantic 驗證失敗: {str(e)}"
            logger.warning(error_msg)
            return False, error_msg, None
        except Exception as e:
            error_msg = f"驗證過程發生錯誤: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg, None


# 全域驗證器實例
validator = SchemaValidator()
