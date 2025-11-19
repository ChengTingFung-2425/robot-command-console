"""
測試契約合規性
驗證所有 API 請求/回應符合標準 JSON 契約
"""

import sys
import os
import unittest
from datetime import datetime
from uuid import uuid4

# 添加 MCP 目錄到路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from MCP.schema_validator import validator, SchemaValidator
from MCP.models import (
    CommandRequest,
    CommandResponse,
    CommandResult,
    CommandStatus,
    ErrorCode,
    ErrorDetail,
    Event,
    EventCategory,
    EventSeverity,
    Actor,
    ActorType,
    Source,
    CommandSpec,
    CommandTarget,
    Priority,
)


class TestSchemaValidation(unittest.TestCase):
    """測試 Schema 驗證功能"""
    
    def setUp(self):
        """設定測試環境"""
        self.validator = SchemaValidator()
    
    def test_valid_command_request(self):
        """測試有效的 CommandRequest"""
        data = {
            "trace_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "actor": {
                "type": "human",
                "id": "user-123",
                "name": "測試用戶"
            },
            "source": "webui",
            "command": {
                "id": f"cmd-{uuid4()}",
                "type": "robot.move",
                "target": {
                    "robot_id": "robot_1"
                },
                "params": {
                    "action_name": "go_forward",
                    "duration_ms": 3000
                },
                "timeout_ms": 10000,
                "priority": "normal"
            },
            "auth": {
                "token": "test-token"
            },
            "labels": {
                "environment": "test"
            }
        }
        
        is_valid, error = self.validator.validate_command_request(data)
        self.assertTrue(is_valid, f"驗證應該通過，但得到錯誤: {error}")
        self.assertIsNone(error)
    
    def test_missing_required_fields_command_request(self):
        """測試缺少必要欄位的 CommandRequest"""
        # 缺少 trace_id
        data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "actor": {
                "type": "human",
                "id": "user-123"
            },
            "source": "api",
            "command": {
                "id": "cmd-123",
                "type": "robot.stop",
                "target": {
                    "robot_id": "robot_1"
                }
            }
        }
        
        is_valid, error = self.validator.validate_command_request(data)
        self.assertFalse(is_valid)
        self.assertIsNotNone(error)
        self.assertIn("trace_id", error)
    
    def test_invalid_actor_type(self):
        """測試無效的 actor type"""
        data = {
            "trace_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "actor": {
                "type": "invalid_type",  # 無效類型
                "id": "user-123"
            },
            "source": "webui",
            "command": {
                "id": "cmd-123",
                "type": "robot.move",
                "target": {
                    "robot_id": "robot_1"
                }
            }
        }
        
        is_valid, error = self.validator.validate_command_request(data)
        self.assertFalse(is_valid)
        self.assertIsNotNone(error)
    
    def test_invalid_timeout_range(self):
        """測試超時時間超出範圍"""
        data = {
            "trace_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "actor": {
                "type": "system",
                "id": "system"
            },
            "source": "scheduler",
            "command": {
                "id": "cmd-123",
                "type": "robot.move",
                "target": {
                    "robot_id": "robot_1"
                },
                "timeout_ms": 50  # 小於最小值 100
            }
        }
        
        is_valid, error = self.validator.validate_command_request(data)
        self.assertFalse(is_valid)
        self.assertIsNotNone(error)
    
    def test_valid_command_response_success(self):
        """測試有效的成功 CommandResponse"""
        data = {
            "trace_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "command": {
                "id": "cmd-123",
                "status": "succeeded"
            },
            "result": {
                "data": {
                    "execution_time_ms": 2850
                },
                "summary": "執行成功"
            },
            "error": None
        }
        
        is_valid, error = self.validator.validate_command_response(data)
        self.assertTrue(is_valid, f"驗證應該通過，但得到錯誤: {error}")
        self.assertIsNone(error)
    
    def test_valid_command_response_error(self):
        """測試有效的錯誤 CommandResponse"""
        data = {
            "trace_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "command": {
                "id": "cmd-123",
                "status": "failed"
            },
            "result": None,
            "error": {
                "code": "ERR_TIMEOUT",
                "message": "指令執行超時",
                "details": {
                    "timeout_ms": 10000
                }
            }
        }
        
        is_valid, error = self.validator.validate_command_response(data)
        self.assertTrue(is_valid, f"驗證應該通過，但得到錯誤: {error}")
        self.assertIsNone(error)
    
    def test_invalid_error_code(self):
        """測試無效的錯誤代碼"""
        data = {
            "trace_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "command": {
                "id": "cmd-123",
                "status": "failed"
            },
            "result": None,
            "error": {
                "code": "INVALID_ERROR_CODE",  # 無效代碼
                "message": "測試錯誤"
            }
        }
        
        is_valid, error = self.validator.validate_command_response(data)
        self.assertFalse(is_valid)
        self.assertIsNotNone(error)
    
    def test_valid_event_log(self):
        """測試有效的 EventLog"""
        data = {
            "trace_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "severity": "INFO",
            "category": "command",
            "message": "指令已接受",
            "context": {
                "command_id": "cmd-123",
                "robot_id": "robot_1"
            }
        }
        
        is_valid, error = self.validator.validate_event_log(data)
        self.assertTrue(is_valid, f"驗證應該通過，但得到錯誤: {error}")
        self.assertIsNone(error)
    
    def test_event_log_missing_message(self):
        """測試缺少訊息的 EventLog"""
        data = {
            "trace_id": str(uuid4()),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "severity": "ERROR",
            "category": "audit",
            # 缺少 message
            "context": {}
        }
        
        is_valid, error = self.validator.validate_event_log(data)
        self.assertFalse(is_valid)
        self.assertIsNotNone(error)
        self.assertIn("message", error)
    
    def test_pydantic_model_validation(self):
        """測試使用 Pydantic 模型驗證"""
        data = {
            "trace_id": str(uuid4()),
            "timestamp": datetime.utcnow(),
            "actor": Actor(type=ActorType.HUMAN, id="user-123"),
            "source": Source.WEBUI,
            "command": CommandSpec(
                id=f"cmd-{uuid4()}",
                type="robot.move",
                target=CommandTarget(robot_id="robot_1"),
                params={"action": "forward"},
                timeout_ms=5000,
                priority=Priority.NORMAL
            )
        }
        
        is_valid, error, instance = self.validator.validate_pydantic_model(
            CommandRequest,
            data
        )
        
        self.assertTrue(is_valid, f"驗證應該通過，但得到錯誤: {error}")
        self.assertIsNone(error)
        self.assertIsNotNone(instance)
        self.assertIsInstance(instance, CommandRequest)


class TestContractPropagation(unittest.TestCase):
    """測試契約傳播（trace_id 等）"""
    
    def test_trace_id_propagation(self):
        """測試 trace_id 在請求和回應中傳播"""
        trace_id = str(uuid4())
        
        # 建立請求
        request = CommandRequest(
            trace_id=trace_id,
            timestamp=datetime.utcnow(),
            actor=Actor(type=ActorType.HUMAN, id="user-123"),
            source=Source.API,
            command=CommandSpec(
                id=f"cmd-{uuid4()}",
                type="robot.status",
                target=CommandTarget(robot_id="robot_1")
            )
        )
        
        # 建立回應
        response = CommandResponse(
            trace_id=trace_id,
            timestamp=datetime.utcnow(),
            command={
                "id": request.command.id,
                "status": CommandStatus.SUCCEEDED.value
            },
            result=CommandResult(
                data={"status": "online"},
                summary="查詢成功"
            )
        )
        
        # 驗證 trace_id 一致
        self.assertEqual(request.trace_id, response.trace_id)
        self.assertEqual(trace_id, response.trace_id)
    
    def test_event_log_trace_id(self):
        """測試 EventLog 包含正確的 trace_id"""
        trace_id = str(uuid4())
        
        event = Event(
            trace_id=trace_id,
            timestamp=datetime.utcnow(),
            severity=EventSeverity.INFO,
            category=EventCategory.COMMAND,
            message="測試事件",
            context={"test": "data"}
        )
        
        self.assertEqual(event.trace_id, trace_id)
        
        # 驗證事件符合 schema
        event_dict = event.dict()
        event_dict["timestamp"] = event.timestamp.isoformat() + "Z"
        event_dict["severity"] = event.severity.value
        event_dict["category"] = event.category.value
        
        is_valid, error = validator.validate_event_log(event_dict)
        self.assertTrue(is_valid, f"Event 應該符合 schema，但得到錯誤: {error}")


class TestErrorContractCompliance(unittest.TestCase):
    """測試錯誤回應契約合規性"""
    
    def test_validation_error_response(self):
        """測試驗證錯誤回應格式"""
        response = CommandResponse(
            trace_id=str(uuid4()),
            timestamp=datetime.utcnow(),
            command={
                "id": "cmd-123",
                "status": CommandStatus.FAILED.value
            },
            result=None,
            error=ErrorDetail(
                code=ErrorCode.ERR_VALIDATION,
                message="請求資料不符合 Schema",
                details={"field": "timeout_ms", "issue": "too small"}
            )
        )
        
        # 驗證回應符合 schema
        response_dict = response.dict()
        response_dict["timestamp"] = response.timestamp.isoformat() + "Z"
        
        is_valid, error = validator.validate_command_response(response_dict)
        self.assertTrue(is_valid, f"Response 應該符合 schema，但得到錯誤: {error}")
    
    def test_auth_error_response(self):
        """測試認證錯誤回應格式"""
        response = CommandResponse(
            trace_id=str(uuid4()),
            timestamp=datetime.utcnow(),
            command={
                "id": "cmd-456",
                "status": CommandStatus.FAILED.value
            },
            result=None,
            error=ErrorDetail(
                code=ErrorCode.ERR_UNAUTHORIZED,
                message="身份驗證失敗",
                details={"reason": "invalid_token"}
            )
        )
        
        # 驗證回應符合 schema
        response_dict = response.dict()
        response_dict["timestamp"] = response.timestamp.isoformat() + "Z"
        
        is_valid, error = validator.validate_command_response(response_dict)
        self.assertTrue(is_valid, f"Response 應該符合 schema，但得到錯誤: {error}")
    
    def test_timeout_error_response(self):
        """測試超時錯誤回應格式"""
        response = CommandResponse(
            trace_id=str(uuid4()),
            timestamp=datetime.utcnow(),
            command={
                "id": "cmd-789",
                "status": CommandStatus.FAILED.value
            },
            result=None,
            error=ErrorDetail(
                code=ErrorCode.ERR_TIMEOUT,
                message="指令執行超時",
                details={"timeout_ms": 10000, "elapsed_ms": 10100}
            )
        )
        
        # 驗證回應符合 schema
        response_dict = response.dict()
        response_dict["timestamp"] = response.timestamp.isoformat() + "Z"
        
        is_valid, error = validator.validate_command_response(response_dict)
        self.assertTrue(is_valid, f"Response 應該符合 schema，但得到錯誤: {error}")


if __name__ == '__main__':
    unittest.main()
