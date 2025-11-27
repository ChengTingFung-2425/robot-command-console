"""
LM Studio 提供商插件
支援 LM Studio 本地 LLM 服務，並可將 MCP 作為協定層注入
支援 OpenAI function calling，可將 MCP 指令暴露為工具
"""

import asyncio
import json
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


class LMStudioProvider(LLMProviderBase):
    """
    LM Studio 本地 LLM 提供商
    支援透過 OpenAI 相容 API 與 LM Studio 通訊
    MCP 可作為協定適配層注入
    支援 function calling
    """

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.mcp_tool_interface = None

    def set_mcp_tool_interface(self, tool_interface):
        """
        設定 MCP 工具介面
        
        Args:
            tool_interface: MCPToolInterface 實例
        """
        self.mcp_tool_interface = tool_interface
        self.logger.info("已注入 MCP 工具介面到 LM Studio 提供商")

    @property
    def provider_name(self) -> str:
        return "lmstudio"

    @property
    def default_port(self) -> int:
        return 1234

    async def check_health(self) -> ProviderHealth:
        """
        檢查 LM Studio 服務健康狀態
        
        Returns:
            健康狀態資訊
        """
        start_time = time.time()

        try:
            async with aiohttp.ClientSession() as session:
                # LM Studio 使用 OpenAI 相容 API
                url = self.get_api_endpoint("v1/models")
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout)
                ) as response:
                    response_time_ms = (time.time() - start_time) * 1000

                    if response.status == 200:
                        data = await response.json()

                        # 取得可用模型
                        available_models = []
                        if "data" in data:
                            available_models = [model.get("id", "") for model in data["data"]]

                        return ProviderHealth(
                            status=ProviderStatus.AVAILABLE,
                            version=None,  # LM Studio 不提供版本資訊
                            available_models=available_models,
                            response_time_ms=response_time_ms
                        )
                    else:
                        return ProviderHealth(
                            status=ProviderStatus.ERROR,
                            error_message=f"HTTP {response.status}",
                            response_time_ms=response_time_ms
                        )

        except asyncio.TimeoutError:
            return ProviderHealth(
                status=ProviderStatus.UNAVAILABLE,
                error_message="連線逾時"
            )
        except aiohttp.ClientError as e:
            return ProviderHealth(
                status=ProviderStatus.UNAVAILABLE,
                error_message=f"連線錯誤: {str(e)}"
            )
        except Exception as e:
            self.logger.error(f"健康檢查失敗: {e}", exc_info=True)
            return ProviderHealth(
                status=ProviderStatus.ERROR,
                error_message=str(e)
            )

    async def list_models(self) -> List[LLMModel]:
        """
        列出 LM Studio 可用模型
        
        Returns:
            模型列表
        """
        try:
            async with aiohttp.ClientSession() as session:
                url = self.get_api_endpoint("v1/models")
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout)
                ) as response:
                    response.raise_for_status()
                    data = await response.json()

                    models = []
                    for model_data in data.get("data", []):
                        model_id = model_data.get("id", "")

                        # LM Studio 提供有限的模型資訊
                        capabilities = ModelCapability(
                            supports_streaming=True,
                            supports_vision=False,
                            supports_function_calling=False,
                            context_length=model_data.get("context_length", 2048),
                            max_tokens=2048
                        )

                        models.append(LLMModel(
                            id=model_id,
                            name=model_id,
                            size=None,
                            capabilities=capabilities,
                            metadata={
                                "object": model_data.get("object"),
                                "owned_by": model_data.get("owned_by", "lmstudio")
                            }
                        ))

                    return models

        except aiohttp.ClientError as e:
            self.logger.error(f"無法列出 LM Studio 模型: {e}")
            return []
        except Exception as e:
            self.logger.error(f"列出模型時發生錯誤: {e}", exc_info=True)
            return []

    async def generate(
        self,
        prompt: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Tuple[str, float]:
        """
        使用 LM Studio 生成文字
        
        Args:
            prompt: 輸入提示
            model: 使用的模型名稱
            temperature: 溫度參數
            max_tokens: 最大生成 token 數
            **kwargs: 其他參數
                use_tools: 是否使用 MCP 工具（預設 False）
                trace_id: 追蹤 ID
            
        Returns:
            (生成的文字, 信心度) 元組
        """
        use_tools = kwargs.pop("use_tools", False)
        trace_id = kwargs.pop("trace_id", None)

        # 如果啟用工具且有 MCP 工具介面，使用 function calling
        if use_tools and self.mcp_tool_interface:
            return await self._generate_with_tools(
                prompt, model, temperature, max_tokens, trace_id, **kwargs
            )

        # 一般生成
        try:
            async with aiohttp.ClientSession() as session:
                # LM Studio 使用 OpenAI 相容的 Chat Completions API
                url = self.get_api_endpoint("v1/chat/completions")

                messages = [
                    {"role": "user", "content": prompt}
                ]

                # 如果有系統提示，加入 system message
                if "system" in kwargs:
                    messages.insert(0, {"role": "system", "content": kwargs["system"]})

                payload = {
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "stream": False
                }

                if max_tokens:
                    payload["max_tokens"] = max_tokens

                async with session.post(
                    url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout),
                    headers=self.config.custom_headers
                ) as response:
                    response.raise_for_status()
                    data = await response.json()

                    # 從 OpenAI 格式回應中提取文字
                    choices = data.get("choices", [])
                    if not choices:
                        return "", 0.0

                    message = choices[0].get("message", {})
                    generated_text = message.get("content", "")

                    # LM Studio 不提供信心度，使用預設值
                    confidence = 0.85

                    # 如果有 finish_reason，可以根據它調整信心度
                    finish_reason = choices[0].get("finish_reason")
                    if finish_reason == "stop":
                        confidence = 0.9
                    elif finish_reason == "length":
                        confidence = 0.7

                    return generated_text, confidence

        except aiohttp.ClientError as e:
            self.logger.error(f"LM Studio 生成失敗: {e}")
            raise
        except Exception as e:
            self.logger.error(f"生成時發生錯誤: {e}", exc_info=True)
            raise

    async def _generate_with_tools(
        self,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: Optional[int],
        trace_id: Optional[str],
        **kwargs
    ) -> Tuple[str, float]:
        """
        使用工具進行生成（OpenAI function calling）
        
        Args:
            prompt: 輸入提示
            model: 模型名稱
            temperature: 溫度
            max_tokens: 最大 token 數
            trace_id: 追蹤 ID
            **kwargs: 其他參數
            
        Returns:
            (生成的文字, 信心度) 元組
        """
        try:
            # 取得 MCP 工具定義（OpenAI 格式）
            tools = self.mcp_tool_interface.get_tool_definitions()

            async with aiohttp.ClientSession() as session:
                url = self.get_api_endpoint("v1/chat/completions")

                messages = [
                    {
                        "role": "system",
                        "content": kwargs.get("system", "你是一個機器人控制助手。使用提供的工具來執行機器人指令。")
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]

                payload = {
                    "model": model,
                    "messages": messages,
                    "tools": tools,
                    "tool_choice": "auto",
                    "temperature": temperature,
                    "stream": False
                }

                if max_tokens:
                    payload["max_tokens"] = max_tokens

                async with session.post(
                    url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout),
                    headers=self.config.custom_headers
                ) as response:
                    response.raise_for_status()
                    data = await response.json()

                    choices = data.get("choices", [])
                    if not choices:
                        return "", 0.0

                    message = choices[0].get("message", {})

                    # 檢查是否有工具呼叫
                    tool_calls = message.get("tool_calls", [])

                    if tool_calls:
                        # 執行工具呼叫
                        results = []
                        for tool_call in tool_calls:
                            function = tool_call.get("function", {})
                            tool_name = function.get("name")
                            arguments = function.get("arguments", {})

                            if isinstance(arguments, str):
                                arguments = json.loads(arguments)

                            self.logger.info(f"LLM 呼叫工具: {tool_name}")

                            result = await self.mcp_tool_interface.execute_tool_call(
                                tool_name=tool_name,
                                arguments=arguments,
                                trace_id=trace_id
                            )

                            results.append(result)

                        # 將工具執行結果格式化為回應
                        response_text = "已執行以下操作：\n"
                        for i, result in enumerate(results):
                            if result.get("success"):
                                response_text += f"{i + 1}. {result.get('message', '操作完成')}\n"
                            else:
                                response_text += f"{i + 1}. 錯誤: {result.get('error', '未知錯誤')}\n"

                        return response_text, 0.9
                    else:
                        # 沒有工具呼叫，返回一般回應
                        content = message.get("content", "")
                        return content, 0.85

        except Exception as e:
            self.logger.error(f"使用工具生成失敗: {e}", exc_info=True)
            raise
