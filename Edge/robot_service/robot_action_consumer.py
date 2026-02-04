"""
機器人動作消費者

從佇列中消費 LLM bridge 發送的動作指令，供真實機器人執行
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Callable
from datetime import datetime
import json

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
        polling_interval: float = 0.1,
        state_manager=None
    ):
        """
        初始化機器人動作消費者

        Args:
            service_manager: 服務管理器（用於從佇列讀取）
            robot_connector: 真實機器人連接器
            polling_interval: 輪詢間隔（秒）
            state_manager: 共享狀態管理器（用於回報結果）
        """
        self.service_manager = service_manager
        self.robot_connector = robot_connector
        self.polling_interval = polling_interval
        self.state_manager = state_manager
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

        # 使用 SharedStateManager 回報結果
        if self.state_manager:
            try:
                # 更新指令狀態
                command_key = f"command:{command_id}:result"
                await self.state_manager.state_store.set(command_key, {
                    "command_id": command_id,
                    "robot_id": robot_id,
                    "action": action,
                    "result": result,
                    "status": "completed" if result.get("success") else "failed",
                    "completed_at": datetime.now().isoformat()
                })

                # 發布完成事件
                await self.state_manager.event_bus.publish(
                    "command.completed" if result.get("success") else "command.failed",
                    {
                        "command_id": command_id,
                        "robot_id": robot_id,
                        "action": action,
                        "result": result
                    },
                    source="robot_action_consumer"
                )

                logger.info(f"結果已回報至 SharedStateManager: {command_id}")
            except Exception as e:
                logger.error(f"回報結果失敗: {e}")
        else:
            logger.warning("SharedStateManager 未設定，無法回報結果")

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

        # 使用 SharedStateManager 回報錯誤
        if self.state_manager:
            try:
                # 更新指令狀態
                command_key = f"command:{command_id}:result"
                await self.state_manager.state_store.set(command_key, {
                    "command_id": command_id,
                    "robot_id": robot_id,
                    "action": action,
                    "status": "failed",
                    "error": error,
                    "failed_at": datetime.now().isoformat()
                })

                # 發布失敗事件
                await self.state_manager.event_bus.publish(
                    "command.failed",
                    {
                        "command_id": command_id,
                        "robot_id": robot_id,
                        "action": action,
                        "error": error
                    },
                    source="robot_action_consumer"
                )

                logger.info(f"錯誤已回報至 SharedStateManager: {command_id}")
            except Exception as e:
                logger.error(f"回報錯誤失敗: {e}")
        else:
            logger.warning("SharedStateManager 未設定，無法回報錯誤")


class RobotConnector:
    """
    真實機器人連接器

    負責與真實機器人硬體通訊
    支援多種連接類型：Serial, Bluetooth, WiFi (HTTP/WebSocket)
    """

    def __init__(self, connection_type: str = "serial", config: Optional[Dict[str, Any]] = None):
        """
        初始化機器人連接器

        Args:
            connection_type: 連接類型（serial, bluetooth, wifi, websocket）
            config: 連接配置（port, baudrate, host, etc.）
        """
        self.connection_type = connection_type
        self.config = config or {}
        self._connected = False
        self._connection = None  # 實際連接對象
        
    async def connect(self, robot_id: str) -> bool:
        """
        連接到機器人

        Args:
            robot_id: 機器人 ID

        Returns:
            是否成功連接
        """
        logger.info(f"連接到機器人 {robot_id} (type={self.connection_type})")

        try:
            if self.connection_type == "serial":
                # Serial 連接實作
                # import serial
                # port = self.config.get("port", "/dev/ttyUSB0")
                # baudrate = self.config.get("baudrate", 115200)
                # self._connection = serial.Serial(port, baudrate, timeout=1)
                logger.info(f"Serial 連接: {self.config.get('port', '/dev/ttyUSB0')}")
                
            elif self.connection_type == "bluetooth":
                # Bluetooth 連接實作
                # import bluetooth
                # addr = self.config.get("address")
                # self._connection = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
                # self._connection.connect((addr, 1))
                logger.info(f"Bluetooth 連接: {self.config.get('address')}")
                
            elif self.connection_type == "wifi":
                # WiFi (HTTP) 連接實作
                # import requests
                # host = self.config.get("host", "192.168.1.100")
                # port = self.config.get("port", 8080)
                # self._connection = {"base_url": f"http://{host}:{port}"}
                logger.info(f"WiFi 連接: {self.config.get('host')}:{self.config.get('port', 8080)}")
                
            elif self.connection_type == "websocket":
                # WebSocket 連接實作
                # import websockets
                # uri = self.config.get("uri", "ws://localhost:8080")
                # self._connection = await websockets.connect(uri)
                logger.info(f"WebSocket 連接: {self.config.get('uri')}")
                
            else:
                logger.warning(f"未知的連接類型: {self.connection_type}，使用模擬模式")

            self._connected = True
            logger.info(f"成功連接到機器人 {robot_id}")
            return True
            
        except Exception as e:
            logger.error(f"連接失敗: {e}")
            self._connected = False
            return False

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

        try:
            # 構建指令數據
            command_data = {
                "action": action,
                "params": params,
                "timestamp": datetime.now().isoformat()
            }
            
            if self.connection_type == "serial":
                # Serial 發送實作
                # command_bytes = json.dumps(command_data).encode('utf-8') + b'\n'
                # self._connection.write(command_bytes)
                # response_line = self._connection.readline()
                # response = json.loads(response_line.decode('utf-8'))
                logger.debug(f"Serial 發送: {command_data}")
                
            elif self.connection_type == "bluetooth":
                # Bluetooth 發送實作
                # command_bytes = json.dumps(command_data).encode('utf-8')
                # self._connection.send(command_bytes)
                # response_bytes = self._connection.recv(1024)
                # response = json.loads(response_bytes.decode('utf-8'))
                logger.debug(f"Bluetooth 發送: {command_data}")
                
            elif self.connection_type == "wifi":
                # WiFi (HTTP) 發送實作
                # import requests
                # url = f"{self._connection['base_url']}/command"
                # response = requests.post(url, json=command_data, timeout=5)
                # response = response.json()
                logger.debug(f"WiFi 發送: {command_data}")
                
            elif self.connection_type == "websocket":
                # WebSocket 發送實作
                # await self._connection.send(json.dumps(command_data))
                # response_text = await self._connection.recv()
                # response = json.loads(response_text)
                logger.debug(f"WebSocket 發送: {command_data}")
                
            # 模擬回應（實際實作需要從機器人接收）
            return {
                "status": "success",
                "robot_id": robot_id,
                "action": action,
                "params": params,
                "executed_at": datetime.now().isoformat(),
                "connection_type": self.connection_type
            }
            
        except Exception as e:
            logger.error(f"發送指令失敗: {e}")
            return {
                "status": "error",
                "robot_id": robot_id,
                "action": action,
                "error": str(e),
                "failed_at": datetime.now().isoformat()
            }

    async def disconnect(self, robot_id: str):
        """
        斷開與機器人的連接

        Args:
            robot_id: 機器人 ID
        """
        logger.info(f"斷開與機器人 {robot_id} 的連接")
        self._connected = False
