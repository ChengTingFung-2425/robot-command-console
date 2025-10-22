"""
MCP 資料模型
定義指令、機器人、事件等核心資料結構
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, validator


class ActorType(str, Enum):
    """執行者類型"""
    HUMAN = "human"
    AI = "ai"
    SYSTEM = "system"


class Source(str, Enum):
    """指令來源"""
    WEBUI = "webui"
    API = "api"
    CLI = "cli"
    SCHEDULER = "scheduler"


class CommandStatus(str, Enum):
    """指令狀態"""
    PENDING = "pending"
    ACCEPTED = "accepted"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Priority(str, Enum):
    """優先權"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class RobotStatus(str, Enum):
    """機器人狀態"""
    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"
    MAINTENANCE = "maintenance"


class Protocol(str, Enum):
    """通訊協定"""
    HTTP = "http"
    MQTT = "mqtt"
    WEBSOCKET = "websocket"
    GRPC = "grpc"
    ROS = "ros"


class ErrorCode(str, Enum):
    """錯誤代碼"""
    ERR_VALIDATION = "ERR_VALIDATION"
    ERR_UNAUTHORIZED = "ERR_UNAUTHORIZED"
    ERR_ROUTING = "ERR_ROUTING"
    ERR_ROBOT_NOT_FOUND = "ERR_ROBOT_NOT_FOUND"
    ERR_ROBOT_OFFLINE = "ERR_ROBOT_OFFLINE"
    ERR_ROBOT_BUSY = "ERR_ROBOT_BUSY"
    ERR_ACTION_INVALID = "ERR_ACTION_INVALID"
    ERR_PROTOCOL = "ERR_PROTOCOL"
    ERR_TIMEOUT = "ERR_TIMEOUT"
    ERR_INTERNAL = "ERR_INTERNAL"


# ===== 請求與回應模型 =====

class Actor(BaseModel):
    """執行者"""
    type: ActorType
    id: str = Field(..., min_length=1)


class CommandTarget(BaseModel):
    """指令目標"""
    robot_id: str = Field(..., min_length=1)


class CommandSpec(BaseModel):
    """指令規格"""
    id: str = Field(default_factory=lambda: f"cmd-{uuid4()}")
    type: str = Field(..., pattern=r"^[a-z][a-z0-9_.-]+$")
    target: CommandTarget
    params: Dict[str, Any] = Field(default_factory=dict)
    timeout_ms: int = Field(default=10000, ge=100, le=600000)
    priority: Priority = Priority.NORMAL


class CommandRequest(BaseModel):
    """指令請求"""
    trace_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    actor: Actor
    source: Source
    command: CommandSpec
    auth: Optional[Dict[str, Any]] = None
    labels: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ErrorDetail(BaseModel):
    """錯誤詳情"""
    code: ErrorCode
    message: str
    details: Optional[Dict[str, Any]] = None


class CommandResult(BaseModel):
    """指令結果"""
    data: Optional[Dict[str, Any]] = None
    summary: str = ""


class CommandResponse(BaseModel):
    """指令回應"""
    trace_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    command: Dict[str, Any]  # id + status
    result: Optional[CommandResult] = None
    error: Optional[ErrorDetail] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class StatusResponse(BaseModel):
    """狀態查詢回應"""
    trace_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    command: Dict[str, Any]  # id + status
    progress: Optional[Dict[str, Any]] = None
    error: Optional[ErrorDetail] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# ===== 機器人模型 =====

class RobotCapability(BaseModel):
    """機器人能力"""
    actions: list[str] = Field(default_factory=list)
    sensors: list[str] = Field(default_factory=list)
    max_speed: Optional[float] = None
    payload_kg: Optional[float] = None


class RobotRegistration(BaseModel):
    """機器人註冊資訊"""
    robot_id: str = Field(..., min_length=1)
    robot_type: str = Field(..., min_length=1)
    capabilities: RobotCapability = Field(default_factory=RobotCapability)
    status: RobotStatus = RobotStatus.ONLINE
    endpoint: str = Field(..., min_length=1)
    protocol: Protocol = Protocol.HTTP
    last_heartbeat: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class Heartbeat(BaseModel):
    """心跳訊息"""
    robot_id: str = Field(..., min_length=1)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    status: RobotStatus = RobotStatus.ONLINE
    metrics: Optional[Dict[str, Any]] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# ===== 事件模型 =====

class EventSeverity(str, Enum):
    """事件嚴重程度"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"


class EventCategory(str, Enum):
    """事件類別"""
    COMMAND = "command"
    AUTH = "auth"
    PROTOCOL = "protocol"
    ROBOT = "robot"
    AUDIT = "audit"


class Event(BaseModel):
    """事件"""
    trace_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    severity: EventSeverity
    category: EventCategory
    message: str
    context: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
