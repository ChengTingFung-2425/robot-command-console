"""
Progress Tracker

追蹤批次執行進度。
"""

import logging
from datetime import datetime
from typing import Dict, Optional, Any

from .models import CommandStatus
from common.datetime_utils import utc_now

logger = logging.getLogger(__name__)


class ProgressTracker:
    """
    進度追蹤器

    追蹤批次執行的即時進度，提供統計資訊和進度條渲染。
    """

    def __init__(self):
        """初始化進度追蹤器"""
        self.batch_id: Optional[str] = None
        self.total_commands: int = 0
        self.completed: int = 0
        self.successful: int = 0
        self.failed: int = 0
        self.timeout: int = 0
        self.cancelled: int = 0
        self.start_time: Optional[datetime] = None
        self.command_status: Dict[str, CommandStatus] = {}

    def start_batch(self, batch_id: str, total_commands: int):
        """
        開始追蹤批次

        Args:
            batch_id: 批次 ID
            total_commands: 總指令數
        """
        self.batch_id = batch_id
        self.total_commands = total_commands
        self.completed = 0
        self.successful = 0
        self.failed = 0
        self.timeout = 0
        self.cancelled = 0
        self.start_time = utc_now()
        self.command_status = {}

        logger.info(f"Started tracking batch: {batch_id}, {total_commands} commands")

    def update_progress(self, command_id: str, status: CommandStatus):
        """
        更新指令進度

        Args:
            command_id: 指令 ID
            status: 指令狀態
        """
        terminal_states = {
            CommandStatus.SUCCESS,
            CommandStatus.FAILED,
            CommandStatus.TIMEOUT,
            CommandStatus.CANCELLED
        }

        # 檢查是否已經記錄過此指令
        old_status = self.command_status.get(command_id)

        if old_status is not None:
            # 如果狀態沒變，不需要更新
            if old_status == status:
                return
            # 減少舊狀態的計數
            self._decrease_count(old_status)

        # 更新狀態
        self.command_status[command_id] = status
        self._increase_count(status)

        # 更新完成數：只有在從非終止狀態轉換到終止狀態時才增加
        if status in terminal_states and (old_status is None or old_status not in terminal_states):
            self.completed += 1

    def _increase_count(self, status: CommandStatus):
        """增加狀態計數"""
        if status == CommandStatus.SUCCESS:
            self.successful += 1
        elif status == CommandStatus.FAILED:
            self.failed += 1
        elif status == CommandStatus.TIMEOUT:
            self.timeout += 1
        elif status == CommandStatus.CANCELLED:
            self.cancelled += 1

    def _decrease_count(self, status: CommandStatus):
        """減少狀態計數"""
        if status == CommandStatus.SUCCESS:
            self.successful = max(0, self.successful - 1)
        elif status == CommandStatus.FAILED:
            self.failed = max(0, self.failed - 1)
        elif status == CommandStatus.TIMEOUT:
            self.timeout = max(0, self.timeout - 1)
        elif status == CommandStatus.CANCELLED:
            self.cancelled = max(0, self.cancelled - 1)

    def get_summary(self) -> Dict[str, Any]:
        """
        取得進度摘要

        Returns:
            進度摘要字典
        """
        elapsed_time_ms = 0
        estimated_remaining_ms = 0

        if self.start_time:
            elapsed_time_ms = int((utc_now() - self.start_time).total_seconds() * 1000)

            # 估算剩餘時間
            if self.completed > 0:
                avg_time_per_command = elapsed_time_ms / self.completed
                remaining_commands = self.total_commands - self.completed
                estimated_remaining_ms = int(avg_time_per_command * remaining_commands)

        progress_percentage = 0
        if self.total_commands > 0:
            progress_percentage = int((self.completed / self.total_commands) * 100)

        return {
            "batch_id": self.batch_id,
            "total_commands": self.total_commands,
            "completed": self.completed,
            "successful": self.successful,
            "failed": self.failed,
            "timeout": self.timeout,
            "cancelled": self.cancelled,
            "pending": self.total_commands - self.completed,
            "progress_percentage": progress_percentage,
            "elapsed_time_ms": elapsed_time_ms,
            "estimated_remaining_ms": estimated_remaining_ms,
        }

    def render_progress_bar(self, width: int = 50) -> str:
        """
        渲染文字進度條

        Args:
            width: 進度條寬度（字元數）

        Returns:
            進度條字串
        """
        if self.total_commands == 0:
            return "[" + " " * width + "] 0%"

        progress = self.completed / self.total_commands
        filled = int(width * progress)
        empty = width - filled

        bar = "█" * filled + "░" * empty
        percentage = int(progress * 100)

        return f"[{bar}] {percentage}%"

    def render_summary(self) -> str:
        """
        渲染進度摘要文字

        Returns:
            摘要字串
        """
        summary = self.get_summary()

        lines = [
            f"Batch: {summary['batch_id']}",
            f"Progress: {self.render_progress_bar()} "
            f"({summary['completed']}/{summary['total_commands']} commands)",
            f"Success: {summary['successful']} | "
            f"Failed: {summary['failed']} | "
            f"Timeout: {summary['timeout']} | "
            f"Pending: {summary['pending']}",
        ]

        if summary['estimated_remaining_ms'] > 0:
            remaining_sec = summary['estimated_remaining_ms'] / 1000
            mins = int(remaining_sec // 60)
            secs = int(remaining_sec % 60)
            lines.append(f"Estimated time remaining: {mins:02d}:{secs:02d}")

        return "\n".join(lines)

    def is_complete(self) -> bool:
        """
        檢查批次是否完成

        Returns:
            是否完成
        """
        return self.completed >= self.total_commands
