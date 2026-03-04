"""
LLM 提供商管理器
負責自動偵測、註冊與管理本地及雲端 LLM 提供商
支援雲端優先/本地備援（cloud-first/local-fallback）路由策略
MCP 可透過此管理器注入到各個提供商
"""

import logging
from enum import Enum
from typing import Dict, List, Optional, Tuple, Type

from .llm_provider_base import (
    LLMProviderBase,
    ProviderConfig,
    ProviderHealth,
    ProviderStatus,
)
from .providers import LMStudioProvider, OllamaProvider
from src.common.llm_manager import LLMManager

logger = logging.getLogger(__name__)


class RoutingMode(str, Enum):
    """
    LLM 路由模式

    決定在有多個提供商時如何選擇提供商：
    - CLOUD_FIRST : 優先使用雲端提供商，雲端不可用時自動切換到本地
    - LOCAL_FIRST : 優先使用本地提供商，本地不可用時自動切換到雲端
    - CLOUD_ONLY  : 僅使用雲端提供商，不使用本地備援
    - LOCAL_ONLY  : 僅使用本地提供商，不使用雲端備援
    """

    CLOUD_FIRST = "cloud_first"
    LOCAL_FIRST = "local_first"
    CLOUD_ONLY = "cloud_only"
    LOCAL_ONLY = "local_only"


# 已知的雲端提供商名稱集合（用於判斷提供商類型）
_CLOUD_PROVIDER_NAMES = frozenset(
    {"cloud", "azure_openai", "gcp_gemini", "aws_bedrock"}
)


class LLMProviderManager:
    """
    LLM 提供商管理器

    負責：
    - 自動偵測本地 LLM 服務
    - 管理提供商實例（本地與雲端）
    - 提供統一的提供商存取介面
    - 健康檢查與狀態監控
    - 注入 MCP 工具介面到提供商
    - 雲端優先/本地備援路由策略（RoutingMode）
    """

    # 預設掃描的提供商類別
    DEFAULT_PROVIDERS: List[Type[LLMProviderBase]] = [
        OllamaProvider,
        LMStudioProvider,
    ]

    def __init__(
        self,
        custom_providers: Optional[List[Type[LLMProviderBase]]] = None,
        mcp_tool_interface=None,
        routing_mode: RoutingMode = RoutingMode.LOCAL_FIRST,
    ):
        """
        初始化提供商管理器

        Args:
            custom_providers: 自訂提供商類別列表（用於擴充）
            mcp_tool_interface: MCP 工具介面，用於注入到提供商
            routing_mode: 路由策略，預設為本地優先（LOCAL_FIRST）
        """
        self.llm_manager = LLMManager()
        self.providers: Dict[str, LLMProviderBase] = {}
        self.provider_classes = self.DEFAULT_PROVIDERS.copy()
        self.routing_mode: RoutingMode = routing_mode

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

    def register_providers(self):
        """
        Register default and custom providers using the unified LLMManager.
        """
        for provider_cls in self.DEFAULT_PROVIDERS:
            provider_instance = provider_cls()
            self.llm_manager.register_provider(provider_instance)

    def check_provider_health(self, provider_name):
        """
        Check health of a provider using the unified LLMManager.
        """
        return self.llm_manager.check_health(provider_name)

    # ------------------------------------------------------------------ #
    #  路由模式 — 雲端優先 / 本地備援                                      #
    # ------------------------------------------------------------------ #

    def is_cloud_provider(self, provider_name: str) -> bool:
        """
        判斷提供商是否為雲端提供商

        優先依據已註冊提供商實例上的 `is_cloud` 屬性判斷，
        允許任何自訂提供商透過設定 `is_cloud = True` 宣告自己為雲端提供商。
        若提供商尚未註冊，則回退至名稱白名單（_CLOUD_PROVIDER_NAMES）。

        Args:
            provider_name: 提供商名稱

        Returns:
            True 表示雲端提供商，False 表示本地提供商
        """
        # 優先依據 provider 實例上的 is_cloud 屬性判斷，若未定義則回退至名稱白名單
        provider = self.providers.get(provider_name) if hasattr(self, "providers") else None

        if provider is not None:
            is_cloud_attr = getattr(provider, "is_cloud", None)
            if isinstance(is_cloud_attr, bool):
                return is_cloud_attr
        provider = self.providers.get(provider_name)
        if provider is not None:
            return bool(getattr(provider, "is_cloud", False))
        return provider_name in _CLOUD_PROVIDER_NAMES

    def set_routing_mode(self, mode: RoutingMode) -> None:
        """
        設定路由模式

        Args:
            mode: RoutingMode 列舉值
        """
        self.routing_mode = mode
        self.logger.info(f"路由模式已設定為: {mode.value}")

    def get_routing_mode(self) -> RoutingMode:
        """
        取得當前路由模式

        Returns:
            目前的 RoutingMode
        """
        return self.routing_mode

    def list_cloud_providers(self) -> List[str]:
        """
        列出所有已註冊的雲端提供商名稱

        Returns:
            雲端提供商名稱列表
        """
        return [name for name in self.providers if self.is_cloud_provider(name)]

    def list_local_providers(self) -> List[str]:
        """
        列出所有已註冊的本地提供商名稱

        Returns:
            本地提供商名稱列表
        """
        return [name for name in self.providers if not self.is_cloud_provider(name)]

    def get_provider_with_routing(self) -> Optional[LLMProviderBase]:
        """
        依照路由模式取得最優先的提供商

        路由邏輯：
        - CLOUD_FIRST : 雲端提供商 → 本地提供商
        - LOCAL_FIRST : 本地提供商 → 雲端提供商
        - CLOUD_ONLY  : 僅返回雲端提供商（無則返回 None）
        - LOCAL_ONLY  : 僅返回本地提供商（無則返回 None）

        Returns:
            選出的提供商實例，無可用提供商時返回 None
        """
        cloud_names = self.list_cloud_providers()
        local_names = self.list_local_providers()

        if self.routing_mode == RoutingMode.CLOUD_ONLY:
            candidates = cloud_names
        elif self.routing_mode == RoutingMode.LOCAL_ONLY:
            candidates = local_names
        elif self.routing_mode == RoutingMode.CLOUD_FIRST:
            candidates = cloud_names + local_names
        else:  # LOCAL_FIRST
            candidates = local_names + cloud_names

        for name in candidates:
            provider = self.providers.get(name)
            if provider is not None:
                return provider

        return None

    async def get_provider_with_routing_and_health(self) -> Optional[LLMProviderBase]:
        """
        依照路由模式取得最優先的**可用**提供商（含即時健康檢查）

        與 get_provider_with_routing() 不同，此方法會進行即時健康檢查，
        跳過不可用的提供商，實現真正的備援切換。

        Returns:
            第一個可用的提供商實例，全部不可用時返回 None
        """
        cloud_names = self.list_cloud_providers()
        local_names = self.list_local_providers()

        if self.routing_mode == RoutingMode.CLOUD_ONLY:
            ordered = cloud_names
        elif self.routing_mode == RoutingMode.LOCAL_ONLY:
            ordered = local_names
        elif self.routing_mode == RoutingMode.CLOUD_FIRST:
            ordered = cloud_names + local_names
        else:  # LOCAL_FIRST
            ordered = local_names + cloud_names

        for name in ordered:
            provider = self.providers.get(name)
            if provider is None:
                continue
            try:
                health = await provider.check_health()
                if health.status == ProviderStatus.AVAILABLE:
                    self.logger.info(f"路由選擇提供商: {name} (模式: {self.routing_mode.value})")
                    return provider
                self.logger.debug(f"提供商 {name} 不可用 ({health.status})，繼續嘗試下一個")
            except Exception as e:
                self.logger.warning(f"健康檢查 {name} 發生例外: {e}")

        self.logger.warning(
            f"路由模式 {self.routing_mode.value} 下沒有可用提供商"
        )
        return None

    async def generate_with_routing(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> Tuple[Optional[str], Optional[str], float]:
        """
        依照路由模式生成文字，含真正的多提供商自動備援

        首先依路由模式與健康檢查選出首選提供商。若該提供商生成時
        發生錯誤（如 rate-limit、暫時性伺服器錯誤），會依順序嘗試
        其他已註冊的提供商，直到成功或全部失敗為止。

        Args:
            prompt: 輸入提示
            model: 使用的模型 ID（選用，None 表示讓提供商自行選擇）
            temperature: 溫度參數
            max_tokens: 最大生成 token 數
            **kwargs: 傳遞給提供商的其他參數

        Returns:
            (生成文字, 使用的提供商名稱, 信心度) 元組；
            若所有提供商都失敗則回傳 (None, None, 0.0)
        """
        # 取得首選提供商（已通過健康檢查）
        primary = await self.get_provider_with_routing_and_health()
        if primary is None:
            self.logger.error("generate_with_routing: 沒有可用提供商")
            return None, None, 0.0

        # 建構候選列表：首選在最前，其餘已註冊提供商作為備援（使用 set 去重）
        # CLOUD_ONLY / LOCAL_ONLY 模式：備援候選也必須符合路由模式的限制
        seen: set = {primary}
        candidates: List[LLMProviderBase] = [primary]
        mode = self.routing_mode
        for candidate in self.providers.values():
            if candidate in seen:
                continue
            if mode == RoutingMode.CLOUD_ONLY and not getattr(candidate, "is_cloud", False):
                continue
            if mode == RoutingMode.LOCAL_ONLY and getattr(candidate, "is_cloud", False):
                continue
            candidates.append(candidate)
            seen.add(candidate)

        for provider in candidates:
            # 若未指定模型，嘗試取得該提供商第一個可用模型
            effective_model = model
            if not effective_model:
                try:
                    models = await provider.list_models()
                    if models:
                        effective_model = models[0].id
                except Exception as e:
                    self.logger.debug(f"無法列出 {provider.provider_name} 模型: {e}")

            if not effective_model:
                self.logger.warning(
                    f"提供商 {provider.provider_name} 無可用模型，嘗試下一個提供商"
                )
                continue

            try:
                text, confidence = await provider.generate(
                    prompt=prompt,
                    model=effective_model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs,
                )
                self.logger.info(
                    f"generate_with_routing 成功: provider={provider.provider_name}, "
                    f"model={effective_model}"
                )
                return text, provider.provider_name, confidence
            except Exception as e:
                self.logger.error(
                    f"提供商 {provider.provider_name} 生成失敗，嘗試下一個備援: {e}",
                    exc_info=True,
                )

        self.logger.error("generate_with_routing: 所有候選提供商皆生成失敗")
        return None, None, 0.0
