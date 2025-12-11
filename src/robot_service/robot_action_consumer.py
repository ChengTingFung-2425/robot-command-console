"""
機器人動作消費者

從佇列中消費 LLM bridge 發送的動作指令，供真實機器人執行
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Callable
from datetime import datetime

logger = logging.getLogger(__name__)


class RobotActionConsumer:
    """
    機器人動作消費者
    
    功能：
    - 從佇列中讀取 LLM bridge 發送的動作
    - 轉換為真實機器人可理解的格式
    - 將動作發送給真實機器人
    - 回報執行結果
    """
    
    def __init__(
        self,
        service_manager=None,
        robot_connector=None,
        polling_interval: float = 0.1
    ):
        """
        初始化機器人動作消費者
        
        Args:
            service_manager: 服務管理器（用於從佇列讀取）
            robot_connector: 真實機器人連接器
            polling_interval: 輪詢間隔（秒）
        """
        self.service_manager = service_manager
        self.robot_connector = robot_connector
        self.polling_interval = polling_interval
        self._running = False
        self._consumer_task: Optional[asyncio.Task] = None
        self._handlers: Dict[str, Callable] = {}
        
    def register_action_handler(self, action: str, handler: Callable):
        """
        註冊動作處理器
        
        Args:
            action: 動作名稱（如 "go_forward", "turn_left"）
            handler: 處理器函數
        """
        self._handlers[action] = handler
        logger.info(f"註冊動作處理器: {action}")
    
    async def start(self):
        """啟動消費者"""
        if self._running:
            logger.warning("消費者已在運行")
            return
        
        self._running = True
        self._consumer_task = asyncio.create_task(self._consume_loop())
        logger.info("機器人動作消費者已啟動")
    
    async def stop(self):
        """停止消費者"""
        self._running = False
        
        if self._consumer_task:
            self._consumer_task.cancel()
            try:
                await self._consumer_task
            except asyncio.CancelledError:
                pass
        
        logger.info("機器人動作消費者已停止")
    
    async def _consume_loop(self):
        """消費循環"""
        logger.info("開始消費佇列中的機器人動作")
        
        while self._running:
            try:
                # 從佇列中讀取訊息
                message = await self._fetch_from_queue()
                
                if message:
                    await self._process_message(message)
                else:
                    # 沒有訊息，短暫休眠
                    await asyncio.sleep(self.polling_interval)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"消費循環發生錯誤: {e}")
                await asyncio.sleep(1)  # 錯誤後休眠 1 秒
    
    async def _fetch_from_queue(self) -> Optional[Dict[str, Any]]:
        """
        從佇列中讀取訊息
        
        Returns:
            訊息字典或 None
        """
        if not self.service_manager:
            return None
        
        try:
            # 從 service_manager 的佇列中讀取
            # 假設 service_manager 有 get_message() 方法
            message = await self.service_manager.get_message(timeout=self.polling_interval)
            
            if message:
                logger.debug(f"從佇列讀取訊息: {message}")
                return message
            
        except asyncio.TimeoutError:
            # 超時是正常的，沒有訊息
            return None
        except Exception as e:
            logger.error(f"從佇列讀取訊息失敗: {e}")
            return None
        
        return None
    
    async def _process_message(self, message: Dict[str, Any]):
        """
        處理訊息
        
        Args:
            message: 訊息字典
                {
                    "robot_id": "robot-001",
                    "action": "go_forward",
                    "params": {"duration_ms": 3000},
                    "command_id": "cmd-abc123",
                    "timestamp": "2025-01-01T00:00:00"
                }
        """
        robot_id = message.get("robot_id")
        action = message.get("action")
        params = message.get("params", {})
        command_id = message.get("command_id")
        
        logger.info(f"處理機器人動作: robot={robot_id}, action={action}, params={params}")
        
        try:
            # 1. 檢查是否有註冊的處理器
            if action in self._handlers:
                handler = self._handlers[action]
                result = await handler(robot_id, params)
            else:
                # 2. 使用預設處理器（發送給真實機器人）
                result = await self._send_to_real_robot(robot_id, action, params)
            
            # 3. 回報執行結果
            await self._report_result(command_id, robot_id, action, result)
            
        except Exception as e:
            logger.exception(f"處理機器人動作失敗: {e}")
            await self._report_error(command_id, robot_id, action, str(e))
    
    async def _send_to_real_robot(
        self,
        robot_id: str,
        action: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        發送動作給真實機器人
        
        Args:
            robot_id: 機器人 ID
            action: 動作名稱
            params: 參數
        
        Returns:
            執行結果
        """
        if not self.robot_connector:
            logger.warning("機器人連接器未設定，模擬執行")
            return {
                "success": True,
                "message": "Simulated execution (no robot connector)",
                "robot_id": robot_id,
                "action": action
            }
        
        try:
            # 透過機器人連接器發送指令
            logger.info(f"發送動作給真實機器人 {robot_id}: {action}")
            result = await self.robot_connector.send_command(robot_id, action, params)
            
            return {
                "success": True,
                "message": "Command sent to real robot",
                "robot_id": robot_id,
                "action": action,
                "result": result
            }
            
        except Exception as e:
            logger.error(f"發送給真實機器人失敗: {e}")
            return {
                "success": False,
                "error": str(e),
                "robot_id": robot_id,
                "action": action
            }
    
    async def _report_result(
        self,
        command_id: str,
        robot_id: str,
        action: str,
        result: Dict[str, Any]
    ):
        """
        回報執行結果
        
        Args:
            command_id: 指令 ID
            robot_id: 機器人 ID
            action: 動作名稱
            result: 執行結果
        """
        logger.info(f"回報結果: command_id={command_id}, success={result.get('success')}")
        
        # 可以透過 state_manager 或其他機制回報結果
        # 供 LLM bridge 或 UI 顯示
        
        # TODO: 實作結果回報機制
        pass
    
    async def _report_error(
        self,
        command_id: str,
        robot_id: str,
        action: str,
        error: str
    ):
        """
        回報執行錯誤
        
        Args:
            command_id: 指令 ID
            robot_id: 機器人 ID
            action: 動作名稱
            error: 錯誤訊息
        """
        logger.error(f"回報錯誤: command_id={command_id}, error={error}")
        
        # TODO: 實作錯誤回報機制
        pass


class RobotConnector:
    """
    真實機器人連接器
    
    負責與真實機器人硬體通訊
    """
    
    def __init__(self, connection_type: str = "serial"):
        """
        初始化機器人連接器
        
        Args:
            connection_type: 連接類型（serial, bluetooth, wifi等）
        """
        self.connection_type = connection_type
        self._connected = False
    
    async def connect(self, robot_id: str) -> bool:
        """
        連接到機器人
        
        Args:
            robot_id: 機器人 ID
        
        Returns:
            是否成功連接
        """
        logger.info(f"連接到機器人 {robot_id} (type={self.connection_type})")
        
        # TODO: 實作實際的連接邏輯
        # 例如：serial port, bluetooth, TCP/IP 等
        
        self._connected = True
        return True
    
    async def send_command(
        self,
        robot_id: str,
        action: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        發送指令給機器人
        
        Args:
            robot_id: 機器人 ID
            action: 動作名稱
            params: 參數
        
        Returns:
            機器人回應
        """
        if not self._connected:
            await self.connect(robot_id)
        
        logger.info(f"發送指令給機器人 {robot_id}: {action} with params {params}")
        
        # TODO: 實作實際的指令發送
        # 例如：
        # - Serial: 透過 serial port 發送字節
        # - Bluetooth: 透過 bluetooth socket 發送
        # - WiFi: 透過 HTTP/WebSocket 發送
        
        # 模擬回應
        return {
            "status": "success",
            "robot_id": robot_id,
            "action": action,
            "executed_at": datetime.now().isoformat()
        }
    
    async def disconnect(self, robot_id: str):
        """
        斷開與機器人的連接
        
        Args:
            robot_id: 機器人 ID
        """
        logger.info(f"斷開與機器人 {robot_id} 的連接")
        self._connected = False
