"""
GCP Vertex AI / Gemini 提供商插件
支援 Google Cloud 的 Gemini API（Generative Language API）
使用 API 金鑰認證（適用於 Gemini API）
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

# Gemini API 支援的常見模型（用於無法列表時的預設值）
GEMINI_DEFAULT_MODELS = [
    "gemini-1.5-flash",
    "gemini-1.5-pro",
    "gemini-2.0-flash",
]


class GCPGeminiProvider(LLMProviderBase):
    """
    GCP Gemini 提供商（Generative Language API）

    端點格式：
        https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}

    認證方式：API 金鑰附加於查詢參數 key=

    ProviderConfig 欄位用途：
        - api_key   : Google AI Studio / GCP API 金鑰
        - custom_headers["default_model"]: 預設模型（預設 "gemini-1.5-flash"）
    """

    GEMINI_BASE_URL = "https://generativelanguage.googleapis.com"
    DEFAULT_PORT = 443
    is_cloud: bool = True

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._api_key = config.api_key
        self._default_model = config.custom_headers.get(
            "default_model", GEMINI_DEFAULT_MODELS[0]
        )

    @property
    def provider_name(self) -> str:
        return "gcp_gemini"

    @property
    def default_port(self) -> int:
        return self.DEFAULT_PORT

    def get_api_endpoint(self, path: str = "") -> str:
        """覆寫端點建構，固定使用 Gemini API base URL"""
        base = self.GEMINI_BASE_URL.rstrip("/")
        return f"{base}/{path.lstrip('/')}" if path else base

    def _generate_url(self, model: str) -> str:
        """建構生成端點 URL"""
        return (
            f"{self.GEMINI_BASE_URL}/v1beta/models/{model}"
            f":generateContent?key={self._api_key}"
        )

    def _list_models_url(self) -> str:
        """建構模型列表端點 URL"""
        return f"{self.GEMINI_BASE_URL}/v1beta/models?key={self._api_key}"

    async def check_health(self) -> ProviderHealth:
        """
        檢查 GCP Gemini 服務健康狀態

        Returns:
            健康狀態資訊
        """
        if not self._api_key:
            return ProviderHealth(
                status=ProviderStatus.UNAVAILABLE,
                error_message="未設定 GCP API 金鑰",
            )

        start_time = time.time()

        try:
            async with aiohttp.ClientSession() as session:
                url = self._list_models_url()
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout),
                ) as response:
                    response_time_ms = (time.time() - start_time) * 1000

                    if response.status == 200:
                        data = await response.json()
                        available_models = [
                            item.get("name", "").split("/")[-1]
                            for item in data.get("models", [])
                            if "generateContent" in item.get("supportedGenerationMethods", [])
                        ]
                        return ProviderHealth(
                            status=ProviderStatus.AVAILABLE,
                            available_models=available_models or GEMINI_DEFAULT_MODELS,
                            response_time_ms=response_time_ms,
                        )
                    elif response.status in (400, 401, 403):
                        return ProviderHealth(
                            status=ProviderStatus.ERROR,
                            error_message="GCP API 金鑰無效或權限不足",
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
            self.logger.error(f"GCP Gemini 健康檢查失敗: {e}", exc_info=True)
            return ProviderHealth(
                status=ProviderStatus.ERROR,
                error_message="健康檢查失敗",
            )

    async def list_models(self) -> List[LLMModel]:
        """
        列出 GCP Gemini 可用的模型

        Returns:
            支援 generateContent 的模型列表
        """
        if not self._api_key:
            return []

        try:
            async with aiohttp.ClientSession() as session:
                url = self._list_models_url()
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout),
                ) as response:
                    response.raise_for_status()
                    data = await response.json()

                    models = []
                    for item in data.get("models", []):
                        if "generateContent" not in item.get("supportedGenerationMethods", []):
                            continue
                        model_id = item.get("name", "").split("/")[-1]
                        if not model_id:
                            continue
                        capabilities = ModelCapability(
                            supports_streaming=True,
                            supports_vision="vision" in model_id.lower(),
                            context_length=item.get("inputTokenLimit", 8192),
                            max_tokens=item.get("outputTokenLimit", 2048),
                        )
                        models.append(
                            LLMModel(
                                id=model_id,
                                name=item.get("displayName", model_id),
                                capabilities=capabilities,
                                metadata={"full_name": item.get("name", "")},
                            )
                        )
                    return models

        except aiohttp.ClientError as e:
            self.logger.error(f"無法列出 GCP Gemini 模型: {e}")
            return []
        except Exception as e:
            self.logger.error(f"列出 GCP Gemini 模型時發生錯誤: {e}", exc_info=True)
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
        使用 GCP Gemini 生成文字

        Args:
            prompt: 輸入提示
            model: 模型 ID（如 gemini-1.5-flash）
            temperature: 溫度參數
            max_tokens: 最大生成 token 數
            **kwargs: 其他參數（system: 系統提示，合併至使用者訊息）

        Returns:
            (生成的文字, 信心度) 元組
        """
        effective_model = model or self._default_model

        try:
            async with aiohttp.ClientSession() as session:
                url = self._generate_url(effective_model)

                # Gemini API 使用不同的請求格式
                user_content = prompt
                if "system" in kwargs:
                    user_content = f"{kwargs['system']}\n\n{prompt}"

                payload: dict = {
                    "contents": [
                        {"role": "user", "parts": [{"text": user_content}]}
                    ],
                    "generationConfig": {
                        "temperature": temperature,
                    },
                }
                if max_tokens:
                    payload["generationConfig"]["maxOutputTokens"] = max_tokens

                async with session.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout),
                ) as response:
                    response.raise_for_status()
                    data = await response.json()

                    candidates = data.get("candidates", [])
                    if not candidates:
                        return "", 0.0

                    candidate = candidates[0]
                    content = candidate.get("content", {})
                    parts = content.get("parts", [])
                    generated_text = "".join(
                        part.get("text", "") for part in parts
                    )

                    finish_reason = candidate.get("finishReason", "")
                    if finish_reason == "STOP":
                        confidence = 0.92
                    elif finish_reason == "MAX_TOKENS":
                        confidence = 0.70
                    else:
                        confidence = 0.85

                    return generated_text, confidence

        except aiohttp.ClientError as e:
            self.logger.error(f"GCP Gemini 生成失敗: {e}")
            raise
        except Exception as e:
            self.logger.error(f"GCP Gemini 生成時發生錯誤: {e}", exc_info=True)
            raise
