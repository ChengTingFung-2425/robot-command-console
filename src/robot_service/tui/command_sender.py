"""
TUI Command Sender

負責從 TUI 發送機器人指令到佇列系統。
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import uuid4

from ..queue.interface import Message, MessagePriority
from ..service_manager import ServiceManager
from common.shared_state import SharedStateManager, EventTopics

logger = logging.getLogger(__name__)


class CommandSender:
    """
    TUI 指令發送器

    負責將 TUI 輸入的指令轉換為佇列訊息並發送。
    """

    def __init__(
        self,
        service_manager: Optional[ServiceManager] = None,
        state_manager: Optional[SharedStateManager] = None
    ):
        """
        初始化指令發送器

        Args:
            service_manager: 服務管理器（包含佇列）
            state_manager: 共享狀態管理器
        """
        self.service_manager = service_manager
        self.state_manager = state_manager

        logger.info("CommandSender initialized", extra={
            "has_service_manager": service_manager is not None,
            "has_state_manager": state_manager is not None
        })

    async def send_command(
        self,
        robot_id: str,
        action: str,
        params: Optional[Dict] = None,
        priority: MessagePriority = MessagePriority.NORMAL,
        timeout_seconds: Optional[int] = None
    ) -> Optional[str]:
        """
        發送指令到指定機器人

        Args:
            robot_id: 機器人 ID
            action: 動作名稱
            params: 可選參數
            priority: 訊息優先權
            timeout_seconds: 超時時間（秒）

        Returns:
            指令 ID，如果發送失敗則返回 None
        """
        if not self.service_manager:
            logger.error("ServiceManager not available, cannot send command")
            return None

        # 建立追蹤 ID
        trace_id = str(uuid4())
        command_id = str(uuid4())

        # 建立指令 payload
        payload = {
            "command_id": command_id,
            "robot_id": robot_id,
            "action": action,
            "params": params or {},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        # 建立訊息
        message = Message(
            id=command_id,
            payload=payload,
            priority=priority,
            trace_id=trace_id,
            timeout_seconds=timeout_seconds or 30
        )

        try:
            # 發送到佇列
            success = await self.service_manager.queue.enqueue(message)

            if success:
                logger.info("Command sent successfully", extra={
                    "command_id": command_id,
                    "robot_id": robot_id,
                    "action": action,
                    "trace_id": trace_id
                })

                # 發布事件
                if self.state_manager:
                    await self.state_manager.publish(
                        EventTopics.COMMAND_SENT,
                        {
                            "command_id": command_id,
                            "robot_id": robot_id,
                            "action": action,
                            "trace_id": trace_id,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                    )

                return command_id
            else:
                logger.error("Failed to enqueue command", extra={
                    "robot_id": robot_id,
                    "action": action
                })
                return None

        except Exception as e:
            logger.error("Error sending command", extra={
                "robot_id": robot_id,
                "action": action,
                "error": str(e)
            })
            return None

    async def broadcast_command(
        self,
        action: str,
        params: Optional[Dict] = None,
        priority: MessagePriority = MessagePriority.NORMAL
    ) -> List[str]:
        """
        廣播指令到所有機器人

        Args:
            action: 動作名稱
            params: 可選參數
            priority: 訊息優先權

        Returns:
            成功發送的指令 ID 列表
        """
        if not self.state_manager:
            logger.warning("StateManager not available, using default robot list")
            # 使用預設機器人列表
            robot_ids = ["robot-001", "robot-002", "robot-003"]
        else:
            # 從狀態管理器取得機器人列表
            try:
                robot_ids = await self._get_all_robots()
                if not robot_ids:
                    logger.warning("No robots found, using default list")
                    robot_ids = ["robot-001"]
            except Exception as e:
                logger.error(f"Error getting robot list: {e}")
                robot_ids = ["robot-001"]

        # 對每個機器人發送指令
        command_ids = []
        for robot_id in robot_ids:
            command_id = await self.send_command(
                robot_id=robot_id,
                action=action,
                params=params,
                priority=priority
            )
            if command_id:
                command_ids.append(command_id)

        logger.info(f"Broadcast command to {len(command_ids)}/{len(robot_ids)} robots", extra={
            "action": action,
            "success_count": len(command_ids),
            "total_count": len(robot_ids)
        })

        return command_ids

    async def _get_all_robots(self) -> List[str]:
        """
        從狀態管理器取得所有機器人 ID

        Returns:
            機器人 ID 列表
        """
        # TODO: 實作從 SharedStateManager 取得機器人列表
        # 目前返回預設列表
        return ["robot-001", "robot-002", "robot-003"]
