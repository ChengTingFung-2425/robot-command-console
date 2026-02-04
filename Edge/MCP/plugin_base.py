"""
MCP 插件基底類別
定義指令插件和裝置驅動插件的標準介面
"""

import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class PluginType(str, Enum):
    """插件類型"""
    COMMAND = "command"  # 指令插件（如進階指令）
    DEVICE = "device"    # 裝置插件（如攝影機、感測器）
    INTEGRATION = "integration"  # 整合插件（如 WebUI 整合）


class PluginStatus(str, Enum):
    """插件狀態"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    DISABLED = "disabled"


class PluginCapability(BaseModel):
    """插件能力描述"""
    supports_streaming: bool = False
    supports_async: bool = True
    supports_batch: bool = False
    requires_hardware: bool = False
    configurable: bool = True


class PluginMetadata(BaseModel):
    """插件元資料"""
    name: str = Field(..., description="插件名稱")
    version: str = Field(..., description="插件版本")
    author: Optional[str] = Field(None, description="作者")
    description: Optional[str] = Field(None, description="描述")
    plugin_type: PluginType = Field(..., description="插件類型")
    capabilities: PluginCapability = Field(default_factory=PluginCapability)
    dependencies: List[str] = Field(default_factory=list, description="依賴項")
    config_schema: Optional[Dict[str, Any]] = Field(None, description="配置 schema")


class PluginConfig(BaseModel):
    """插件配置"""
    enabled: bool = Field(default=True, description="是否啟用")
    priority: int = Field(default=100, description="優先級（越小越優先）")
    config: Dict[str, Any] = Field(default_factory=dict, description="自訂配置")
    tags: List[str] = Field(default_factory=list, description="標籤")


class PluginBase(ABC):
    """
    MCP 插件基底抽象類別
    所有插件（指令、裝置驅動等）必須繼承此類別
    """

    def __init__(self, config: Optional[PluginConfig] = None):
        """
        初始化插件

        Args:
            config: 插件配置
        """
        self.config = config or PluginConfig()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._status = PluginStatus.INACTIVE
        self._error_message: Optional[str] = None

    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """
        插件元資料

        Returns:
            PluginMetadata 物件
        """
        pass

    @property
    def status(self) -> PluginStatus:
        """取得插件狀態"""
        return self._status

    @property
    def error_message(self) -> Optional[str]:
        """取得錯誤訊息"""
        return self._error_message

    async def initialize(self) -> bool:
        """
        初始化插件

        Returns:
            是否成功初始化
        """
        try:
            self.logger.info(f"初始化插件: {self.metadata.name}")
            success = await self._on_initialize()

            if success:
                self._status = PluginStatus.ACTIVE
                self.logger.info(f"插件 {self.metadata.name} 初始化成功")
            else:
                self._status = PluginStatus.ERROR
                self.logger.error(f"插件 {self.metadata.name} 初始化失敗")

            return success

        except Exception as e:
            self._status = PluginStatus.ERROR
            self._error_message = str(e)
            self.logger.error(f"插件初始化異常: {e}", exc_info=True)
            return False

    async def shutdown(self) -> bool:
        """
        關閉插件

        Returns:
            是否成功關閉
        """
        try:
            self.logger.info(f"關閉插件: {self.metadata.name}")
            success = await self._on_shutdown()

            if success:
                self._status = PluginStatus.INACTIVE
                self.logger.info(f"插件 {self.metadata.name} 關閉成功")

            return success

        except Exception as e:
            self.logger.error(f"插件關閉異常: {e}", exc_info=True)
            return False

    @abstractmethod
    async def _on_initialize(self) -> bool:
        """
        插件初始化實作

        Returns:
            是否成功
        """
        pass

    @abstractmethod
    async def _on_shutdown(self) -> bool:
        """
        插件關閉實作

        Returns:
            是否成功
        """
        pass

    async def health_check(self) -> Dict[str, Any]:
        """
        健康檢查

        Returns:
            健康狀態資訊
        """
        return {
            "plugin": self.metadata.name,
            "status": self._status.value,
            "error": self._error_message,
            "enabled": self.config.enabled
        }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}({self.metadata.name}, status={self._status.value})>"


class CommandPluginBase(PluginBase):
    """
    指令插件基底類別
    用於擴充進階指令處理能力
    """

    @abstractmethod
    async def execute_command(
        self,
        command_name: str,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        執行指令

        Args:
            command_name: 指令名稱
            parameters: 指令參數
            context: 執行上下文

        Returns:
            執行結果
        """
        pass

    @abstractmethod
    def get_supported_commands(self) -> List[str]:
        """
        取得支援的指令列表

        Returns:
            指令名稱列表
        """
        pass

    def get_command_schema(self, command_name: str) -> Optional[Dict[str, Any]]:
        """
        取得指令的參數 schema

        Args:
            command_name: 指令名稱

        Returns:
            參數 schema（JSON Schema 格式）
        """
        return None


class DevicePluginBase(PluginBase):
    """
    裝置插件基底類別
    用於整合機器人物理模組（攝影機、感測器等）
    """

    @property
    @abstractmethod
    def device_type(self) -> str:
        """
        裝置類型

        Returns:
            裝置類型（如 camera, sensor, motor）
        """
        pass

    @abstractmethod
    async def read_data(self, **kwargs) -> Dict[str, Any]:
        """
        讀取裝置資料

        Args:
            **kwargs: 讀取參數

        Returns:
            裝置資料
        """
        pass

    async def write_data(self, data: Dict[str, Any], **kwargs) -> bool:
        """
        寫入裝置資料（選用，並非所有裝置都支援）

        Args:
            data: 要寫入的資料
            **kwargs: 寫入參數

        Returns:
            是否成功
        """
        raise NotImplementedError(f"{self.metadata.name} 不支援寫入操作")

    @abstractmethod
    async def get_device_info(self) -> Dict[str, Any]:
        """
        取得裝置資訊

        Returns:
            裝置資訊
        """
        pass

    async def start_stream(self) -> bool:
        """
        啟動串流（選用）

        Returns:
            是否成功
        """
        if not self.metadata.capabilities.supports_streaming:
            raise NotImplementedError(f"{self.metadata.name} 不支援串流")
        return False

    async def stop_stream(self) -> bool:
        """
        停止串流（選用）

        Returns:
            是否成功
        """
        if not self.metadata.capabilities.supports_streaming:
            raise NotImplementedError(f"{self.metadata.name} 不支援串流")
        return False
