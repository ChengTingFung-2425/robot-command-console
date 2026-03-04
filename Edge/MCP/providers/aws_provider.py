"""
Amazon Bedrock 提供商插件
支援 AWS Bedrock 上的 LLM 服務（Claude、Titan 等）
使用 aioboto3（已在 requirements.txt）進行 AWS 認證與請求
"""

import json
import logging
from typing import List, Optional, Tuple

from ..llm_provider_base import (
    LLMModel,
    LLMProviderBase,
    ModelCapability,
    ProviderConfig,
    ProviderHealth,
    ProviderStatus,
)

logger = logging.getLogger(__name__)

# Bedrock 常見模型預設清單（當無法列表時使用）
BEDROCK_DEFAULT_MODELS = [
    "anthropic.claude-3-5-sonnet-20241022-v2:0",
    "anthropic.claude-3-haiku-20240307-v1:0",
    "amazon.titan-text-lite-v1",
]


class AWSBedrockProvider(LLMProviderBase):
    """
    Amazon Bedrock 提供商

    使用 aioboto3 進行 AWS Signature V4 認證，支援：
    - Anthropic Claude 系列
    - Amazon Titan 系列
    - 其他 Bedrock 支援的模型

    ProviderConfig 欄位用途：
        - custom_headers["region"]     : AWS 區域（預設 "us-east-1"）
        - custom_headers["model_id"]   : 預設 Bedrock 模型 ID
        - custom_headers["aws_access_key_id"]    : AWS Access Key（若未設定則從環境變數讀取）
        - custom_headers["aws_secret_access_key"]: AWS Secret Key（若未設定則從環境變數讀取）
    """

    DEFAULT_PORT = 443

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._region = config.custom_headers.get("region", "us-east-1")
        self._model_id = config.custom_headers.get(
            "model_id", BEDROCK_DEFAULT_MODELS[0]
        )
        self._aws_access_key_id = config.custom_headers.get("aws_access_key_id") or None
        self._aws_secret_access_key = config.custom_headers.get("aws_secret_access_key") or None

    @property
    def provider_name(self) -> str:
        return "aws_bedrock"

    @property
    def default_port(self) -> int:
        return self.DEFAULT_PORT

    def _make_boto3_kwargs(self) -> dict:
        """建構 boto3 客戶端參數（支援顯式憑證或環境變數）"""
        kwargs: dict = {"region_name": self._region}
        if self._aws_access_key_id and self._aws_secret_access_key:
            kwargs["aws_access_key_id"] = self._aws_access_key_id
            kwargs["aws_secret_access_key"] = self._aws_secret_access_key
        return kwargs

    async def check_health(self) -> ProviderHealth:
        """
        檢查 AWS Bedrock 服務健康狀態

        透過列出基礎模型來確認連線及認證是否正常。

        Returns:
            健康狀態資訊
        """
        try:
            import aioboto3
        except ImportError:
            return ProviderHealth(
                status=ProviderStatus.ERROR,
                error_message="aioboto3 未安裝，請執行 pip install aioboto3",
            )

        try:
            session = aioboto3.Session(**self._make_boto3_kwargs())
            async with session.client("bedrock") as client:
                response = await client.list_foundation_models(
                    byOutputModality="TEXT"
                )
                model_summaries = response.get("modelSummaries", [])
                available_models = [
                    m.get("modelId", "")
                    for m in model_summaries
                    if m.get("modelId")
                ]
                return ProviderHealth(
                    status=ProviderStatus.AVAILABLE,
                    available_models=available_models or BEDROCK_DEFAULT_MODELS,
                )

        except Exception as e:
            error_str = str(e)
            # 辨別認證錯誤與連線錯誤
            if "credentials" in error_str.lower() or "AuthFailure" in error_str:
                return ProviderHealth(
                    status=ProviderStatus.ERROR,
                    error_message="AWS 憑證無效或未設定",
                )
            if "EndpointResolutionError" in error_str or "could not connect" in error_str.lower():
                return ProviderHealth(
                    status=ProviderStatus.UNAVAILABLE,
                    error_message="無法連線至 AWS Bedrock",
                )
            self.logger.error(f"AWS Bedrock 健康檢查失敗: {e}", exc_info=True)
            return ProviderHealth(
                status=ProviderStatus.ERROR,
                error_message="健康檢查失敗",
            )

    async def list_models(self) -> List[LLMModel]:
        """
        列出 AWS Bedrock 可用的基礎模型

        Returns:
            支援文字輸出的模型列表
        """
        try:
            import aioboto3
        except ImportError:
            return []

        try:
            session = aioboto3.Session(**self._make_boto3_kwargs())
            async with session.client("bedrock") as client:
                response = await client.list_foundation_models(
                    byOutputModality="TEXT"
                )
                models = []
                for item in response.get("modelSummaries", []):
                    model_id = item.get("modelId", "")
                    if not model_id:
                        continue
                    capabilities = ModelCapability(
                        supports_streaming="STREAMING" in item.get("responseStreamingSupported", []),
                        context_length=8192,
                        max_tokens=4096,
                    )
                    models.append(
                        LLMModel(
                            id=model_id,
                            name=item.get("modelName", model_id),
                            capabilities=capabilities,
                            metadata={
                                "provider_name": item.get("providerName", ""),
                                "model_arn": item.get("modelArn", ""),
                            },
                        )
                    )
                return models

        except Exception as e:
            self.logger.error(f"無法列出 AWS Bedrock 模型: {e}", exc_info=True)
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
        使用 AWS Bedrock 生成文字

        根據模型前綴自動選擇對應的請求格式：
        - anthropic.claude-* → Messages API
        - amazon.titan-*     → Titan Text API

        Args:
            prompt: 輸入提示
            model: Bedrock 模型 ID（如 anthropic.claude-3-haiku-20240307-v1:0）
            temperature: 溫度參數
            max_tokens: 最大生成 token 數
            **kwargs: 其他參數（system: 系統提示）

        Returns:
            (生成的文字, 信心度) 元組
        """
        try:
            import aioboto3
        except ImportError:
            raise RuntimeError("aioboto3 未安裝，無法使用 AWS Bedrock")

        effective_model = model or self._model_id
        effective_max_tokens = max_tokens or 1024

        try:
            session = aioboto3.Session(**self._make_boto3_kwargs())
            async with session.client("bedrock-runtime") as client:
                body = self._build_request_body(
                    effective_model, prompt, temperature,
                    effective_max_tokens, kwargs.get("system")
                )
                response = await client.invoke_model(
                    modelId=effective_model,
                    body=json.dumps(body),
                    contentType="application/json",
                    accept="application/json",
                )
                response_body = json.loads(await response["body"].read())
                return self._parse_response(effective_model, response_body)

        except Exception as e:
            self.logger.error(f"AWS Bedrock 生成失敗: {e}", exc_info=True)
            raise

    def _build_request_body(
        self,
        model_id: str,
        prompt: str,
        temperature: float,
        max_tokens: int,
        system: Optional[str],
    ) -> dict:
        """根據模型類型建構請求 body"""
        if model_id.startswith("anthropic."):
            # Anthropic Claude Messages API
            body: dict = {
                "anthropic_version": "bedrock-2023-05-31",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            if system:
                body["system"] = system
            return body

        if model_id.startswith("amazon.titan-"):
            # Amazon Titan Text API
            full_prompt = f"{system}\n\n{prompt}" if system else prompt
            return {
                "inputText": full_prompt,
                "textGenerationConfig": {
                    "temperature": temperature,
                    "maxTokenCount": max_tokens,
                },
            }

        # 其他模型回退為 Anthropic Messages 格式
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if system:
            body["system"] = system
        return body

    def _parse_response(self, model_id: str, response_body: dict) -> Tuple[str, float]:
        """從 Bedrock 回應中提取生成文字與信心度"""
        if model_id.startswith("anthropic."):
            # Claude Messages API 回應格式
            content = response_body.get("content", [])
            text = "".join(
                block.get("text", "") for block in content
                if block.get("type") == "text"
            )
            stop_reason = response_body.get("stop_reason", "")
            confidence = 0.92 if stop_reason == "end_turn" else 0.80
            return text, confidence

        if model_id.startswith("amazon.titan-"):
            # Titan Text 回應格式
            results = response_body.get("results", [])
            text = results[0].get("outputText", "") if results else ""
            completion_reason = results[0].get("completionReason", "") if results else ""
            confidence = 0.90 if completion_reason == "FINISH" else 0.75
            return text, confidence

        # 通用回退
        return str(response_body), 0.80
