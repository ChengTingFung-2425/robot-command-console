"""
Batch Operations Data Models

定義批次操作的資料結構。
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import List, Dict, Any, Optional


class ExecutionMode(str, Enum):
    """執行模式"""
    PARALLEL = "parallel"  # 並行執行
    SEQUENTIAL = "sequential"  # 順序執行
    GROUPED = "grouped"  # 分組並行（組內順序，組間並行）


class CommandStatus(str, Enum):
    """指令狀態"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class BatchStatus(str, Enum):
    """批次狀態"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_WITH_ERRORS = "completed_with_errors"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BatchCommand:
    """批次指令"""
    robot_id: str  # 機器人 ID 或 "all" 表示廣播
    action: str  # 動作名稱
    params: Dict[str, Any] = field(default_factory=dict)  # 動作參數
    priority: str = "normal"  # 優先級: low, normal, high
    timeout_ms: int = 10000  # 超時時間（毫秒）
    command_id: Optional[str] = None  # 指令 ID（自動生成）
    trace_id: Optional[str] = None  # 追蹤 ID（自動生成）

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BatchCommand':
        """從字典創建實例"""
        return cls(
            robot_id=data.get("robot_id", ""),
            action=data.get("action", ""),
            params=data.get("params", {}),
            priority=data.get("priority", "normal"),
            timeout_ms=data.get("timeout_ms", 10000),
            command_id=data.get("command_id"),
            trace_id=data.get("trace_id")
        )


@dataclass
class BatchOptions:
    """批次執行選項"""
    execution_mode: ExecutionMode = ExecutionMode.GROUPED  # 執行模式
    stop_on_error: bool = False  # 遇到錯誤是否停止
    retry_on_failure: int = 0  # 失敗重試次數
    retry_backoff_factor: float = 1.5  # 重試退避係數
    delay_between_commands_ms: int = 0  # 指令間延遲（毫秒）
    max_parallel: int = 10  # 最大並行數
    dry_run: bool = False  # 乾跑模式（不實際執行）

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "execution_mode": self.execution_mode.value,
            "stop_on_error": self.stop_on_error,
            "retry_on_failure": self.retry_on_failure,
            "retry_backoff_factor": self.retry_backoff_factor,
            "delay_between_commands_ms": self.delay_between_commands_ms,
            "max_parallel": self.max_parallel,
            "dry_run": self.dry_run,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BatchOptions':
        """從字典創建實例"""
        execution_mode = data.get("execution_mode", "grouped")
        if isinstance(execution_mode, str):
            execution_mode = ExecutionMode(execution_mode)

        return cls(
            execution_mode=execution_mode,
            stop_on_error=data.get("stop_on_error", False),
            retry_on_failure=data.get("retry_on_failure", 0),
            retry_backoff_factor=data.get("retry_backoff_factor", 1.5),
            delay_between_commands_ms=data.get("delay_between_commands_ms", 0),
            max_parallel=data.get("max_parallel", 10),
            dry_run=data.get("dry_run", False),
        )


@dataclass
class BatchSpec:
    """批次規格"""
    batch_id: str  # 批次 ID
    description: str = ""  # 描述
    robots: List[str] = field(default_factory=list)  # 目標機器人列表
    commands: List[BatchCommand] = field(default_factory=list)  # 指令列表
    options: BatchOptions = field(default_factory=BatchOptions)  # 執行選項
    metadata: Dict[str, Any] = field(default_factory=dict)  # 額外元數據

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "batch_id": self.batch_id,
            "description": self.description,
            "robots": self.robots,
            "commands": [cmd.to_dict() for cmd in self.commands],
            "options": self.options.to_dict(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BatchSpec':
        """從字典創建實例"""
        options_data = data.get("options", {})
        options = BatchOptions.from_dict(options_data) if options_data else BatchOptions()

        commands_data = data.get("commands", [])
        commands = [BatchCommand.from_dict(cmd) for cmd in commands_data]

        return cls(
            batch_id=data.get("batch_id", ""),
            description=data.get("description", ""),
            robots=data.get("robots", []),
            commands=commands,
            options=options,
            metadata=data.get("metadata", {}),
        )


@dataclass
class CommandResult:
    """指令執行結果"""
    command_id: str  # 指令 ID
    trace_id: str  # 追蹤 ID
    robot_id: str  # 機器人 ID
    action: str  # 動作名稱
    status: CommandStatus  # 執行狀態
    start_time: datetime  # 開始時間
    end_time: Optional[datetime] = None  # 結束時間
    duration_ms: Optional[int] = None  # 執行時長（毫秒）
    error: Optional[str] = None  # 錯誤訊息
    retry_count: int = 0  # 重試次數
    result_data: Dict[str, Any] = field(default_factory=dict)  # 結果資料

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "command_id": self.command_id,
            "trace_id": self.trace_id,
            "robot_id": self.robot_id,
            "action": self.action,
            "status": self.status.value,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "error": self.error,
            "retry_count": self.retry_count,
            "result_data": self.result_data,
        }


@dataclass
class BatchResult:
    """批次執行結果"""
    batch_id: str  # 批次 ID
    status: BatchStatus  # 批次狀態
    start_time: datetime  # 開始時間
    end_time: Optional[datetime] = None  # 結束時間
    duration_ms: Optional[int] = None  # 總執行時長（毫秒）
    total_commands: int = 0  # 總指令數
    successful: int = 0  # 成功數
    failed: int = 0  # 失敗數
    timeout: int = 0  # 超時數
    cancelled: int = 0  # 取消數
    commands: List[CommandResult] = field(default_factory=list)  # 指令結果列表
    metadata: Dict[str, Any] = field(default_factory=dict)  # 額外元數據

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "batch_id": self.batch_id,
            "status": self.status.value,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "total_commands": self.total_commands,
            "successful": self.successful,
            "failed": self.failed,
            "timeout": self.timeout,
            "cancelled": self.cancelled,
            "commands": [cmd.to_dict() for cmd in self.commands],
            "metadata": self.metadata,
        }

    def update_statistics(self):
        """更新統計資訊"""
        self.total_commands = len(self.commands)
        self.successful = sum(1 for cmd in self.commands if cmd.status == CommandStatus.SUCCESS)
        self.failed = sum(1 for cmd in self.commands if cmd.status == CommandStatus.FAILED)
        self.timeout = sum(1 for cmd in self.commands if cmd.status == CommandStatus.TIMEOUT)
        self.cancelled = sum(1 for cmd in self.commands if cmd.status == CommandStatus.CANCELLED)

        # 更新批次狀態
        if self.cancelled > 0:
            self.status = BatchStatus.CANCELLED
        elif self.failed > 0 or self.timeout > 0:
            if self.successful > 0:
                self.status = BatchStatus.COMPLETED_WITH_ERRORS
            else:
                self.status = BatchStatus.FAILED
        elif self.successful == self.total_commands:
            self.status = BatchStatus.COMPLETED

        # 計算總時長
        if self.end_time and self.start_time:
            self.duration_ms = int((self.end_time - self.start_time).total_seconds() * 1000)
