"""
MCP 插件管理器
負責載入、初始化、管理所有插件（指令插件、裝置插件等）
"""

import logging
from typing import Any, Dict, List, Optional, Type

from .plugin_base import (
    CommandPluginBase,
    DevicePluginBase,
    PluginBase,
    PluginConfig,
    PluginStatus,
    PluginType,
)

logger = logging.getLogger(__name__)


class PluginManager:
    """
    插件管理器
    
    負責：
    - 註冊和載入插件
    - 初始化和關閉插件
    - 插件生命週期管理
    - 插件查詢和呼叫
    """

    def __init__(self):
        """初始化插件管理器"""
        self.plugins: Dict[str, PluginBase] = {}
        self.command_plugins: Dict[str, CommandPluginBase] = {}
        self.device_plugins: Dict[str, DevicePluginBase] = {}
        self.logger = logging.getLogger(__name__)

    def register_plugin(
        self,
        plugin_class: Type[PluginBase],
        config: Optional[PluginConfig] = None
    ) -> bool:
        """
        註冊插件
        
        Args:
            plugin_class: 插件類別
            config: 插件配置
            
        Returns:
            是否成功註冊
        """
        try:
            # 建立插件實例
            plugin = plugin_class(config)
            plugin_name = plugin.metadata.name

            # 檢查是否已註冊
            if plugin_name in self.plugins:
                self.logger.warning(f"插件已存在: {plugin_name}")
                return False

            # 註冊插件
            self.plugins[plugin_name] = plugin

            # 根據類型分類
            if isinstance(plugin, CommandPluginBase):
                self.command_plugins[plugin_name] = plugin
            elif isinstance(plugin, DevicePluginBase):
                self.device_plugins[plugin_name] = plugin

            self.logger.info(f"已註冊插件: {plugin_name} ({plugin.metadata.plugin_type.value})")

            return True

        except Exception as e:
            self.logger.error(f"註冊插件失敗: {e}", exc_info=True)
            return False

    async def initialize_all(self) -> Dict[str, bool]:
        """
        初始化所有插件
        
        Returns:
            插件名稱到初始化結果的對映
        """
        results = {}

        for name, plugin in self.plugins.items():
            if not plugin.config.enabled:
                self.logger.info(f"跳過已停用的插件: {name}")
                results[name] = False
                continue

            try:
                success = await plugin.initialize()
                results[name] = success

                if success:
                    self.logger.info(f"插件 {name} 初始化成功")
                else:
                    self.logger.error(f"插件 {name} 初始化失敗")

            except Exception as e:
                self.logger.error(f"初始化插件 {name} 時發生異常: {e}", exc_info=True)
                results[name] = False

        success_count = sum(1 for success in results.values() if success)
        self.logger.info(f"插件初始化完成: {success_count}/{len(results)} 成功")

        return results

    async def shutdown_all(self) -> Dict[str, bool]:
        """
        關閉所有插件
        
        Returns:
            插件名稱到關閉結果的對映
        """
        results = {}

        for name, plugin in self.plugins.items():
            if plugin.status != PluginStatus.ACTIVE:
                continue

            try:
                success = await plugin.shutdown()
                results[name] = success

            except Exception as e:
                self.logger.error(f"關閉插件 {name} 時發生異常: {e}", exc_info=True)
                results[name] = False

        return results

    def get_plugin(self, plugin_name: str) -> Optional[PluginBase]:
        """
        取得插件實例
        
        Args:
            plugin_name: 插件名稱
            
        Returns:
            插件實例，若不存在則返回 None
        """
        return self.plugins.get(plugin_name)

    def get_command_plugin(self, plugin_name: str) -> Optional[CommandPluginBase]:
        """
        取得指令插件實例
        
        Args:
            plugin_name: 插件名稱
            
        Returns:
            指令插件實例，若不存在則返回 None
        """
        return self.command_plugins.get(plugin_name)

    def get_device_plugin(self, plugin_name: str) -> Optional[DevicePluginBase]:
        """
        取得裝置插件實例
        
        Args:
            plugin_name: 插件名稱
            
        Returns:
            裝置插件實例，若不存在則返回 None
        """
        return self.device_plugins.get(plugin_name)

    def list_plugins(
        self,
        plugin_type: Optional[PluginType] = None,
        status: Optional[PluginStatus] = None
    ) -> List[str]:
        """
        列出插件
        
        Args:
            plugin_type: 篩選插件類型
            status: 篩選插件狀態
            
        Returns:
            插件名稱列表
        """
        plugins = []

        for name, plugin in self.plugins.items():
            # 類型篩選
            if plugin_type and plugin.metadata.plugin_type != plugin_type:
                continue

            # 狀態篩選
            if status and plugin.status != status:
                continue

            plugins.append(name)

        return plugins

    async def execute_command(
        self,
        plugin_name: str,
        command_name: str,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        透過插件執行指令
        
        Args:
            plugin_name: 插件名稱
            command_name: 指令名稱
            parameters: 指令參數
            context: 執行上下文
            
        Returns:
            執行結果
        """
        plugin = self.get_command_plugin(plugin_name)

        if not plugin:
            return {
                "success": False,
                "error": f"插件不存在: {plugin_name}"
            }

        if plugin.status != PluginStatus.ACTIVE:
            return {
                "success": False,
                "error": f"插件未啟用: {plugin_name} (狀態: {plugin.status.value})"
            }

        try:
            result = await plugin.execute_command(command_name, parameters, context)
            return result

        except Exception as e:
            self.logger.error(f"執行指令失敗: {e}", exc_info=True)
            # 返回通用錯誤信息，不暴露內部細節
            return {
                "success": False,
                "error": "內部錯誤，請聯絡管理員"
            }

    async def read_device_data(
        self,
        plugin_name: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        從裝置插件讀取資料
        
        Args:
            plugin_name: 插件名稱
            **kwargs: 讀取參數
            
        Returns:
            裝置資料
        """
        plugin = self.get_device_plugin(plugin_name)

        if not plugin:
            return {
                "success": False,
                "error": f"裝置插件不存在: {plugin_name}"
            }

        if plugin.status != PluginStatus.ACTIVE:
            return {
                "success": False,
                "error": f"裝置插件未啟用: {plugin_name}"
            }

        try:
            data = await plugin.read_data(**kwargs)
            return data

            # 返回通用錯誤信息，不暴露內部細節
        except Exception as e:
            self.logger.error(f"讀取裝置資料失敗: {e}", exc_info=True)
            return {
                "success": False,
                "error": "內部錯誤，請聯絡管理員"
            }

    async def get_all_plugin_health(self) -> Dict[str, Dict[str, Any]]:
        """
        取得所有插件的健康狀態
        
        Returns:
            插件名稱到健康狀態的對映
        """
        health_results = {}

        for name, plugin in self.plugins.items():
            try:
                health = await plugin.health_check()
                health_results[name] = health
            except Exception as e:
                self.logger.error(f"檢查插件 {name} 健康狀態失敗: {e}")
                health_results[name] = {
                    "plugin": name,
                    "status": "error",
                    "error": str(e)
                }

        return health_results

    def get_supported_commands(self, plugin_name: str) -> Optional[List[str]]:
        """
        取得插件支援的指令列表
        
        Args:
            plugin_name: 插件名稱
            
        Returns:
            指令列表，若插件不存在則返回 None
        """
        plugin = self.get_command_plugin(plugin_name)

        if not plugin:
            return None

        return plugin.get_supported_commands()

    def get_command_schema(
        self,
        plugin_name: str,
        command_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        取得指令的參數 schema
        
        Args:
            plugin_name: 插件名稱
            command_name: 指令名稱
            
        Returns:
            參數 schema
        """
        plugin = self.get_command_plugin(plugin_name)

        if not plugin:
            return None

        return plugin.get_command_schema(command_name)
