"""
MCP 機器人路由器
負責管理機器人註冊、?心跳?、路由與負載均衡
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .config import MCPConfig
from .models import (
    ErrorCode,
    Heartbeat,
    Protocol,
    RobotRegistration,
    RobotStatus,
)


logger = logging.getLogger(__name__)


class RobotRouter:
    """機器人路由器"""

    def __init__(self):
        """初始化路由器"""
        self.robots: Dict[str, RobotRegistration] = {}
        self.robot_locks: Dict[str, asyncio.Lock] = {}
        self._cleanup_task: Optional[asyncio.Task] = None

    def start(self):
        """啟動路由器"""
        self._cleanup_task = asyncio.create_task(self._cleanup_offline_robots())
        logger.info("機器人路由器已啟動")

    async def stop(self):
        """停止路由器"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        logger.info("機器人路由器已停止")

    async def register_robot(self, registration: RobotRegistration) -> bool:
        """註冊機器人"""
        try:
            robot_id = registration.robot_id

            # 檢查是否已註冊
            if robot_id in self.robots:
                logger.info(f"更新機器人註冊: {robot_id}")
            else:
                logger.info(f"新機器人註冊: {robot_id}")
                self.robot_locks[robot_id] = asyncio.Lock()

            # 更新註冊資訊
            registration.last_heartbeat = datetime.utcnow()
            registration.status = RobotStatus.ONLINE
            self.robots[robot_id] = registration

            return True

        except Exception as e:
            logger.error(f"註冊機器人失敗: {e}")
            return False

    async def unregister_robot(self, robot_id: str) -> bool:
        """取消註冊機器人"""
        try:
            if robot_id in self.robots:
                del self.robots[robot_id]
                del self.robot_locks[robot_id]
                logger.info(f"機器人已取消註冊: {robot_id}")
                return True
            return False

        except Exception as e:
            logger.error(f"取消註冊機器人失敗: {e}")
            return False

    async def update_heartbeat(self, heartbeat: Heartbeat) -> bool:
        """更新心跳"""
        robot_id = heartbeat.robot_id

        if robot_id not in self.robots:
            logger.warning(f"收到未註冊機器人的心跳: {robot_id}")
            return False

        try:
            robot = self.robots[robot_id]
            robot.last_heartbeat = heartbeat.timestamp
            robot.status = heartbeat.status

            logger.debug(f"更新機器人心跳: {robot_id}")
            return True

        except Exception as e:
            logger.error(f"更新心跳失敗: {e}")
            return False

    async def get_robot(self, robot_id: str) -> Optional[RobotRegistration]:
        """取得機器人資訊"""
        return self.robots.get(robot_id)

    async def list_robots(
        self,
        robot_type: Optional[str] = None,
        status: Optional[RobotStatus] = None
    ) -> List[RobotRegistration]:
        """列出機器人"""
        robots = list(self.robots.values())

        if robot_type:
            robots = [r for r in robots if r.robot_type == robot_type]

        if status:
            robots = [r for r in robots if r.status == status]

        return robots

    async def route_command(
        self,
        robot_id: str,
        command_type: str,
        params: Dict[str, Any],
        timeout_ms: int,
        trace_id: str
    ) -> Dict[str, Any]:
        """路由指令到機器人"""
        # 檢查機器人是否存在
        robot = await self.get_robot(robot_id)
        if not robot:
            return {
                "error": {
                    "code": ErrorCode.ERR_ROBOT_NOT_FOUND,
                    "message": f"機器人不存在: {robot_id}"
                }
            }

        # 檢查機器人狀態
        if robot.status == RobotStatus.OFFLINE:
            return {
                "error": {
                    "code": ErrorCode.ERR_ROBOT_OFFLINE,
                    "message": f"機器人離線: {robot_id}"
                }
            }

        # 檢查機器人是否忙碌（使用鎖）
        lock = self.robot_locks.get(robot_id)
        if not lock:
            return {
                "error": {
                    "code": ErrorCode.ERR_INTERNAL,
                    "message": "無法取得機器人鎖"
                }
            }

        if lock.locked():
            return {
                "error": {
                    "code": ErrorCode.ERR_ROBOT_BUSY,
                    "message": f"機器人忙碌中: {robot_id}"
                }
            }

        # 執行指令
        async with lock:
            try:
                # 標記為忙碌
                robot.status = RobotStatus.BUSY

                # 依協定下發指令
                result = await self._send_command(robot, command_type, params, timeout_ms, trace_id)

                return result

            except asyncio.TimeoutError:
                return {
                    "error": {
                        "code": ErrorCode.ERR_TIMEOUT,
                        "message": f"指令執行超時: {timeout_ms}ms"
                    }
                }
            except Exception as e:
                logger.error(f"下發指令失敗: {e}", exc_info=True)
                return {
                    "error": {
                        "code": ErrorCode.ERR_INTERNAL,
                        "message": str(e)
                    }
                }
            finally:
                # 恢復為線上
                if robot.status == RobotStatus.BUSY:
                    robot.status = RobotStatus.ONLINE

    async def _send_command(
        self,
        robot: RobotRegistration,
        command_type: str,
        params: Dict[str, Any],
        timeout_ms: int,
        trace_id: str
    ) -> Dict[str, Any]:
        """依協定下發指令"""
        protocol = robot.protocol
        endpoint = robot.endpoint

        logger.info(f"下發指令到 {robot.robot_id} (protocol={protocol}, endpoint={endpoint})")

        if protocol == Protocol.HTTP:
            return await self._send_http_command(endpoint, command_type, params, timeout_ms, trace_id)
        elif protocol == Protocol.MQTT:
            return await self._send_mqtt_command(endpoint, command_type, params, timeout_ms, trace_id)
        elif protocol == Protocol.WEBSOCKET:
            return await self._send_websocket_command(endpoint, command_type, params, timeout_ms, trace_id)
        else:
            return {
                "error": {
                    "code": ErrorCode.ERR_PROTOCOL,
                    "message": f"不支援的協定: {protocol}"
                }
            }

    async def _send_http_command(
        self,
        endpoint: str,
        command_type: str,
        params: Dict[str, Any],
        timeout_ms: int,
        trace_id: str
    ) -> Dict[str, Any]:
        """透過 HTTP 下發指令"""
        import aiohttp
        import ssl

        url = f"{endpoint}/api/command"
        payload = {
            "trace_id": trace_id,
            "command_type": command_type,
            "params": params
        }

        try:
            timeout = aiohttp.ClientTimeout(total=timeout_ms / 1000.0)

            # 設定 SSL 驗證
            ssl_context = None
            if url.startswith("https://"):
                if MCPConfig.SSL_VERIFY:
                    # 使用預設 SSL context，進行完整憑證驗證
                    ssl_context = ssl.create_default_context()
                else:
                    # 明確設定為 False（僅用於開發環境）
                    ssl_context = False

            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, json=payload, ssl=ssl_context) as response:
                    if response.status == 200:
                        result = await response.json()
                        return {"data": result, "summary": "指令執行成功"}
                    else:
                        error_text = await response.text()
                        return {
                            "error": {
                                "code": ErrorCode.ERR_PROTOCOL,
                                "message": f"HTTP 錯誤 {response.status}: {error_text}"
                            }
                        }
        except asyncio.TimeoutError:
            raise
        except Exception as e:
            return {
                "error": {
                    "code": ErrorCode.ERR_PROTOCOL,
                    "message": f"HTTP 請求失敗: {str(e)}"
                }
            }

    async def _send_mqtt_command(
        self,
        endpoint: str,
        command_type: str,
        params: Dict[str, Any],
        timeout_ms: int,
        trace_id: str
    ) -> Dict[str, Any]:
        """透過 MQTT 下發指令"""
        # TODO: 實作 MQTT 指令下發
        logger.warning("MQTT 協定尚未實作")
        return {
            "error": {
                "code": ErrorCode.ERR_PROTOCOL,
                "message": "MQTT 協定尚未實作"
            }
        }

    async def _send_websocket_command(
        self,
        endpoint: str,
        command_type: str,
        params: Dict[str, Any],
        timeout_ms: int,
        trace_id: str
    ) -> Dict[str, Any]:
        """透過 WebSocket 下發指令"""
        # TODO: 實作 WebSocket 指令下發
        logger.warning("WebSocket 協定尚未實作")
        return {
            "error": {
                "code": ErrorCode.ERR_PROTOCOL,
                "message": "WebSocket 協定尚未實作"
            }
        }

    async def _cleanup_offline_robots(self):
        """定期清理離線機器人"""
        while True:
            try:
                await asyncio.sleep(60)  # 每分鐘檢查一次

                threshold = datetime.utcnow() - timedelta(
                    seconds=MCPConfig.ROBOT_OFFLINE_THRESHOLD_SEC
                )

                for robot_id, robot in list(self.robots.items()):
                    if robot.last_heartbeat < threshold and robot.status != RobotStatus.OFFLINE:
                        logger.warning(f"機器人超時未心跳，標記為離線: {robot_id}")
                        robot.status = RobotStatus.OFFLINE

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"清理離線機器人錯誤: {e}")
