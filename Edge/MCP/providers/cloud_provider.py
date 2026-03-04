"""
雲端 LLM 提供商插件
支援 OpenAI 相容 API 的雲端 LLM 服務（如 OpenAI、Azure OpenAI 等）
實作雲端優先/本地備援策略的雲端端
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


class CloudLLMProvider(LLMProviderBase):
    """
    雲端 LLM 提供商

    支援任何 OpenAI 相容 API 的雲端服務，包括：
    - OpenAI API (api.openai.com)
    - Azure OpenAI
    - 自架共享 LLM 服務

    用於雲端優先/本地備援（cloud-first/local-fallback）策略的雲端端。
    """

    DEFAULT_HOST = "api.openai.com"
    DEFAULT_PORT = 443

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._api_key = config.api_key
        self._default_model: Optional[str] = None

    def set_default_model(self, model: str) -> None:
        """設定預設使用的模型"""
        self._default_model = model

    @property
    def provider_name(self) -> str:
        return "cloud"

    @property
    def default_port(self) -> int:
        return self.DEFAULT_PORT

    def _make_headers(self) -> dict:
        """建構 HTTP 請求標頭，包含授權資訊"""
        headers = {"Content-Type": "application/json"}
        headers.update(self.config.custom_headers)
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    async def check_health(self) -> ProviderHealth:
        """
        檢查雲端服務健康狀態

        透過呼叫 /v1/models 端點確認服務可用性。

        Returns:
            健康狀態資訊
        """
        start_time = time.time()

        if not self._api_key:
            return ProviderHealth(
                status=ProviderStatus.UNAVAILABLE,
                error_message="未設定 API 金鑰",
            )

        try:
            async with aiohttp.ClientSession() as session:
                url = self.get_api_endpoint("v1/models")
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
                            available_models=available_models,
                            response_time_ms=response_time_ms,
                        )
                    elif response.status in (401, 403):
                        return ProviderHealth(
                            status=ProviderStatus.ERROR,
                            error_message="API 金鑰無效或權限不足",
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
            self.logger.error(f"雲端健康檢查失敗: {e}", exc_info=True)
            return ProviderHealth(
                status=ProviderStatus.ERROR,
                error_message="健康檢查失敗",
            )

    async def list_models(self) -> List[LLMModel]:
        """
        列出雲端可用的模型

        Returns:
            模型列表
        """
        if not self._api_key:
            return []

        try:
            async with aiohttp.ClientSession() as session:
                url = self.get_api_endpoint("v1/models")
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
                                metadata={
                                    "owned_by": item.get("owned_by", ""),
                                    "object": item.get("object", "model"),
                                },
                            )
                        )
                    return models

        except aiohttp.ClientError as e:
            self.logger.error(f"無法列出雲端模型: {e}")
            return []
        except Exception as e:
            self.logger.error(f"列出雲端模型時發生錯誤: {e}", exc_info=True)
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
        使用雲端 LLM 生成文字

        Args:
            prompt: 輸入提示
            model: 使用的模型 ID（如 gpt-4o-mini）
            temperature: 溫度參數
            max_tokens: 最大生成 token 數
            **kwargs: 其他參數（system: 系統提示）

        Returns:
            (生成的文字, 信心度) 元組
        """
        effective_model = model or self._default_model
        if not effective_model:
            raise ValueError("未指定模型名稱，請設定 model 參數或透過 set_default_model() 設定預設模型")

        try:
            async with aiohttp.ClientSession() as session:
                url = self.get_api_endpoint("v1/chat/completions")

                messages = []
                if "system" in kwargs:
                    messages.append({"role": "system", "content": kwargs["system"]})
                messages.append({"role": "user", "content": prompt})

                payload: dict = {
                    "model": effective_model,
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
            self.logger.error(f"雲端 LLM 生成失敗: {e}")
            raise
        except Exception as e:
            self.logger.error(f"雲端 LLM 生成時發生錯誤: {e}", exc_info=True)
            raise
