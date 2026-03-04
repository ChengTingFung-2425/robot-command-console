"""
Azure OpenAI 提供商插件
支援 Microsoft Azure OpenAI Service
使用部署專屬端點與 api-key 標頭認證
"""

import asyncio
import logging
import time
from typing import List, Optional, Tuple

import aiohttp

from ..llm_provider_base import (
    LLMModel,
    LLMProviderBase,
    ModelCapability,
    ProviderConfig,
    ProviderHealth,
    ProviderStatus,
)

logger = logging.getLogger(__name__)


class AzureOpenAIProvider(LLMProviderBase):
    """
    Azure OpenAI Service 提供商

    Azure OpenAI 使用部署（Deployment）而非直接的模型名稱。
    端點格式：
        https://{resource_name}.openai.azure.com/openai/deployments/{deployment}/chat/completions
        ?api-version={api_version}

    認證方式：api-key 標頭。

    ProviderConfig 欄位用途：
        - api_base  : 完整資源 URL，如 https://my-resource.openai.azure.com
        - api_key   : Azure OpenAI API 金鑰
        - custom_headers["deployment"] : 部署名稱（預設 "gpt-4o-mini"）
        - custom_headers["api_version"]: API 版本（預設 "2024-02-01"）
    """

    DEFAULT_API_VERSION = "2024-02-01"
    DEFAULT_DEPLOYMENT = "gpt-4o-mini"
    DEFAULT_PORT = 443
    is_cloud: bool = True

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._api_key = config.api_key
        self._deployment = config.custom_headers.get("deployment", self.DEFAULT_DEPLOYMENT)
        self._api_version = config.custom_headers.get("api_version", self.DEFAULT_API_VERSION)

    @property
    def provider_name(self) -> str:
        return "azure_openai"

    @property
    def default_port(self) -> int:
        return self.DEFAULT_PORT

    def _get_chat_url(self) -> str:
        """建構 Azure OpenAI Chat Completions 端點 URL"""
        base = (self.config.api_base or "").rstrip("/")
        return (
            f"{base}/openai/deployments/{self._deployment}"
            f"/chat/completions?api-version={self._api_version}"
        )

    def _get_models_url(self) -> str:
        """建構 Azure OpenAI 模型列表端點 URL"""
        base = (self.config.api_base or "").rstrip("/")
        return f"{base}/openai/models?api-version={self._api_version}"

    def _make_headers(self) -> dict:
        """建構請求標頭，使用 api-key 認證"""
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["api-key"] = self._api_key
        return headers

    async def check_health(self) -> ProviderHealth:
        """
        檢查 Azure OpenAI 服務健康狀態

        Returns:
            健康狀態資訊
        """
        if not self._api_key or not self.config.api_base:
            return ProviderHealth(
                status=ProviderStatus.UNAVAILABLE,
                error_message="未設定 Azure OpenAI 資源 URL 或 API 金鑰",
            )

        start_time = time.time()

        try:
            async with aiohttp.ClientSession() as session:
                url = self._get_models_url()
                async with session.get(
                    url,
                    headers=self._make_headers(),
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout),
                ) as response:
                    response_time_ms = (time.time() - start_time) * 1000

                    if response.status == 200:
                        data = await response.json()
                        available_models = [
                            item.get("id", "")
                            for item in data.get("data", [])
                            if item.get("id")
                        ]
                        return ProviderHealth(
                            status=ProviderStatus.AVAILABLE,
                            available_models=available_models or [self._deployment],
                            response_time_ms=response_time_ms,
                        )
                    elif response.status in (401, 403):
                        return ProviderHealth(
                            status=ProviderStatus.ERROR,
                            error_message="Azure API 金鑰無效或權限不足",
                            response_time_ms=response_time_ms,
                        )
                    else:
                        return ProviderHealth(
                            status=ProviderStatus.ERROR,
                            error_message=f"HTTP {response.status}",
                            response_time_ms=response_time_ms,
                        )

        except asyncio.TimeoutError:
            return ProviderHealth(
                status=ProviderStatus.UNAVAILABLE,
                error_message="連線逾時",
            )
        except aiohttp.ClientError as e:
            return ProviderHealth(
                status=ProviderStatus.UNAVAILABLE,
                error_message=f"連線錯誤: {str(e)}",
            )
        except Exception as e:
            self.logger.error(f"Azure OpenAI 健康檢查失敗: {e}", exc_info=True)
            return ProviderHealth(
                status=ProviderStatus.ERROR,
                error_message="健康檢查失敗",
            )

    async def list_models(self) -> List[LLMModel]:
        """
        列出 Azure OpenAI 可用的部署（模型）

        Returns:
            模型列表（以部署名稱作為模型 ID）
        """
        if not self._api_key or not self.config.api_base:
            return []

        try:
            async with aiohttp.ClientSession() as session:
                url = self._get_models_url()
                async with session.get(
                    url,
                    headers=self._make_headers(),
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout),
                ) as response:
                    response.raise_for_status()
                    data = await response.json()

                    models = []
                    for item in data.get("data", []):
                        model_id = item.get("id", "")
                        if not model_id:
                            continue
                        capabilities = ModelCapability(
                            supports_streaming=True,
                            supports_function_calling=True,
                            context_length=item.get("context_length", 4096),
                            max_tokens=item.get("max_tokens", 4096),
                        )
                        models.append(
                            LLMModel(
                                id=model_id,
                                name=model_id,
                                capabilities=capabilities,
                                metadata={"deployment": self._deployment},
                            )
                        )
                    return models

        except aiohttp.ClientError as e:
            self.logger.error(f"無法列出 Azure OpenAI 模型: {e}")
            # 回傳目前設定的部署名稱作為預設
            return [
                LLMModel(
                    id=self._deployment,
                    name=self._deployment,
                    capabilities=ModelCapability(
                        supports_streaming=True,
                        supports_function_calling=True,
                    ),
                )
            ]
        except Exception as e:
            self.logger.error(f"列出 Azure OpenAI 模型時發生錯誤: {e}", exc_info=True)
            return []

    async def generate(
        self,
        prompt: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> Tuple[str, float]:
        """
        使用 Azure OpenAI 生成文字

        Args:
            prompt: 輸入提示
            model: 忽略（Azure 固定使用初始化時指定的部署名稱；如需切換部署請建立新實例）
            temperature: 溫度參數
            max_tokens: 最大生成 token 數
            **kwargs: 其他參數（system: 系統提示）

        Returns:
            (生成的文字, 信心度) 元組
        """
        try:
            async with aiohttp.ClientSession() as session:
                url = self._get_chat_url()

                messages = []
                if "system" in kwargs:
                    messages.append({"role": "system", "content": kwargs["system"]})
                messages.append({"role": "user", "content": prompt})

                payload: dict = {
                    "messages": messages,
                    "temperature": temperature,
                    "stream": False,
                }
                if max_tokens:
                    payload["max_tokens"] = max_tokens

                async with session.post(
                    url,
                    json=payload,
                    headers=self._make_headers(),
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout),
                ) as response:
                    response.raise_for_status()
                    data = await response.json()

                    choices = data.get("choices", [])
                    if not choices:
                        return "", 0.0

                    message = choices[0].get("message", {})
                    generated_text = message.get("content", "")

                    finish_reason = choices[0].get("finish_reason")
                    if finish_reason == "stop":
                        confidence = 0.92
                    elif finish_reason == "length":
                        confidence = 0.70
                    else:
                        confidence = 0.85

                    return generated_text, confidence

        except aiohttp.ClientError as e:
            self.logger.error(f"Azure OpenAI 生成失敗: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Azure OpenAI 生成時發生錯誤: {e}", exc_info=True)
            raise
