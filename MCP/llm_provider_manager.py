"""
LLM 提供商管理器
負責自動偵測、註冊與管理本地 LLM 提供商
MCP 可透過此管理器注入到各個提供商
"""

import logging
from typing import Dict, List, Optional, Type

from .llm_provider_base import (
    LLMProviderBase,
    ProviderConfig,
    ProviderHealth,
    ProviderStatus,
)
from .providers import LMStudioProvider, OllamaProvider

logger = logging.getLogger(__name__)


class LLMProviderManager:
    """
    LLM 提供商管理器
    
    負責：
    - 自動偵測本地 LLM 服務
    - 管理提供商實例
    - 提供統一的提供商存取介面
    - 健康檢查與狀態監控
    - 注入 MCP 工具介面到提供商
    """

    # 預設掃描的提供商類別
    DEFAULT_PROVIDERS: List[Type[LLMProviderBase]] = [
        OllamaProvider,
        LMStudioProvider,
    ]

    def __init__(
        self,
        custom_providers: Optional[List[Type[LLMProviderBase]]] = None,
        mcp_tool_interface=None
    ):
        """
        初始化提供商管理器
        
        Args:
            custom_providers: 自訂提供商類別列表（用於擴充）
            mcp_tool_interface: MCP 工具介面，用於注入到提供商
        """
        self.providers: Dict[str, LLMProviderBase] = {}
        self.provider_classes = self.DEFAULT_PROVIDERS.copy()

        if custom_providers:
            self.provider_classes.extend(custom_providers)

        self.logger = logging.getLogger(__name__)
        self._selected_provider: Optional[str] = None
        self.mcp_tool_interface = mcp_tool_interface

    async def discover_providers(
        self,
        host: str = "localhost",
        timeout: int = 5
    ) -> Dict[str, ProviderHealth]:
        """
        自動偵測可用的本地 LLM 提供商
        
        Args:
            host: 掃描的主機位址
            timeout: 每個提供商的檢查逾時時間（秒）
            
        Returns:
            提供商名稱到健康狀態的對映
        """
        self.logger.info(f"開始掃描本地 LLM 提供商 (host={host})")

        health_results = {}
        tasks = []

        for provider_class in self.provider_classes:
            # 建立提供商實例
            config = ProviderConfig(
                name=provider_class.__name__,
                host=host,
                port=provider_class(ProviderConfig(name="temp", port=0)).default_port,
                timeout=timeout
            )

            provider = provider_class(config)

            # 建立健康檢查任務
            task = self._check_and_register_provider(provider)
            tasks.append((provider.provider_name, task))

        # 並行執行所有健康檢查
        for provider_name, task in tasks:
            try:
                health = await task
                health_results[provider_name] = health

                if health.status == ProviderStatus.AVAILABLE:
                    self.logger.info(
                        f"發現可用提供商: {provider_name} "
                        f"(模型數: {len(health.available_models)}, "
                        f"回應時間: {health.response_time_ms:.1f}ms)"
                    )
            except Exception as e:
                self.logger.error(f"檢查提供商 {provider_name} 時發生錯誤: {e}")
                health_results[provider_name] = ProviderHealth(
                    status=ProviderStatus.ERROR,
                    error_message=str(e)
                )

        self.logger.info(
            f"掃描完成，發現 {len([h for h in health_results.values() if h.status == ProviderStatus.AVAILABLE])} "
            f"個可用提供商，共 {len(health_results)} 個"
        )

        return health_results

    async def _check_and_register_provider(
        self,
        provider: LLMProviderBase
    ) -> ProviderHealth:
        """
        檢查提供商健康狀態並註冊可用的提供商
        
        Args:
            provider: 提供商實例
            
        Returns:
            健康狀態
        """
        try:
            health = await provider.check_health()

            if health.status == ProviderStatus.AVAILABLE:
                # 註冊可用的提供商
                self.providers[provider.provider_name] = provider

                # 如果尚未選擇提供商，自動選擇第一個可用的
                if not self._selected_provider:
                    self._selected_provider = provider.provider_name
                    self.logger.info(f"自動選擇提供商: {provider.provider_name}")

            return health

        except Exception as e:
            self.logger.error(
                f"檢查提供商 {provider.provider_name} 失敗: {e}",
                exc_info=True
            )
            return ProviderHealth(
                status=ProviderStatus.ERROR,
                error_message=str(e)
            )

    def register_provider(
        self,
        provider: LLMProviderBase,
        set_as_default: bool = False
    ) -> None:
        """
        手動註冊提供商
        
        Args:
            provider: 提供商實例
            set_as_default: 是否設為預設提供商
        """
        # 注入 MCP 工具介面（如果提供商支援）
        if self.mcp_tool_interface and hasattr(provider, 'set_mcp_tool_interface'):
            provider.set_mcp_tool_interface(self.mcp_tool_interface)

        self.providers[provider.provider_name] = provider
        self.logger.info(f"已註冊提供商: {provider.provider_name}")

        if set_as_default or not self._selected_provider:
            self._selected_provider = provider.provider_name
            self.logger.info(f"設定預設提供商: {provider.provider_name}")

    def set_mcp_tool_interface(self, tool_interface):
        """
        設定 MCP 工具介面並注入到所有已註冊的提供商
        
        Args:
            tool_interface: MCPToolInterface 實例
        """
        self.mcp_tool_interface = tool_interface

        # 注入到所有已註冊的提供商
        for provider in self.providers.values():
            if hasattr(provider, 'set_mcp_tool_interface'):
                provider.set_mcp_tool_interface(tool_interface)

        self.logger.info(f"已將 MCP 工具介面注入到 {len(self.providers)} 個提供商")

    def get_provider(self, provider_name: Optional[str] = None) -> Optional[LLMProviderBase]:
        """
        取得提供商實例
        
        Args:
            provider_name: 提供商名稱，若未指定則返回當前選擇的提供商
            
        Returns:
            提供商實例，若不存在則返回 None
        """
        if provider_name:
            return self.providers.get(provider_name)

        if self._selected_provider:
            return self.providers.get(self._selected_provider)

        return None

    def select_provider(self, provider_name: str) -> bool:
        """
        選擇要使用的提供商
        
        Args:
            provider_name: 提供商名稱
            
        Returns:
            是否選擇成功
        """
        if provider_name in self.providers:
            self._selected_provider = provider_name
            self.logger.info(f"已切換到提供商: {provider_name}")
            return True

        self.logger.warning(f"提供商不存在: {provider_name}")
        return False

    def get_selected_provider_name(self) -> Optional[str]:
        """
        取得當前選擇的提供商名稱
        
        Returns:
            提供商名稱，若未選擇則返回 None
        """
        return self._selected_provider

    def list_providers(self) -> List[str]:
        """
        列出所有已註冊的提供商
        
        Returns:
            提供商名稱列表
        """
        return list(self.providers.keys())

    async def get_all_provider_health(self) -> Dict[str, ProviderHealth]:
        """
        取得所有已註冊提供商的健康狀態
        
        Returns:
            提供商名稱到健康狀態的對映
        """
        health_results = {}

        tasks = []
        for name, provider in self.providers.items():
            tasks.append((name, provider.check_health()))

        for name, task in tasks:
            try:
                health = await task
                health_results[name] = health
            except Exception as e:
                self.logger.error(f"檢查提供商 {name} 健康狀態失敗: {e}")
                health_results[name] = ProviderHealth(
                    status=ProviderStatus.ERROR,
                    error_message=str(e)
                )

        return health_results

    async def refresh_provider(self, provider_name: str) -> Optional[ProviderHealth]:
        """
        重新檢查特定提供商的健康狀態
        
        Args:
            provider_name: 提供商名稱
            
        Returns:
            健康狀態，若提供商不存在則返回 None
        """
        provider = self.providers.get(provider_name)
        if not provider:
            return None

        try:
            health = await provider.check_health()

            # 如果提供商變為不可用，且它是當前選擇的提供商，則嘗試切換到另一個可用的
            if health.status != ProviderStatus.AVAILABLE and self._selected_provider == provider_name:
                self.logger.warning(f"當前提供商 {provider_name} 不可用，嘗試切換到其他提供商")
                await self._try_fallback_provider()

            return health

        except Exception as e:
            self.logger.error(f"重新檢查提供商 {provider_name} 失敗: {e}")
            return ProviderHealth(
                status=ProviderStatus.ERROR,
                error_message=str(e)
            )

    async def _try_fallback_provider(self) -> bool:
        """
        嘗試切換到另一個可用的提供商
        
        Returns:
            是否成功切換
        """
        all_health = await self.get_all_provider_health()

        for name, health in all_health.items():
            if health.status == ProviderStatus.AVAILABLE and name != self._selected_provider:
                self._selected_provider = name
                self.logger.info(f"已切換到備用提供商: {name}")
                return True

        self.logger.error("沒有可用的備用提供商")
        self._selected_provider = None
        return False
