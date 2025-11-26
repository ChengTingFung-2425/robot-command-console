"""
Ollama 提供商插件
支援 Ollama 本地 LLM 服務，並可將 MCP 作為協定層注入
支援 function calling，可將 MCP 指令暴露為工具
"""

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

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


class OllamaProvider(LLMProviderBase):
    """
    Ollama 本地 LLM 提供商
    支援透過 MCP 協定層與 Ollama 服務通訊
    支援 function calling，可將 MCP 暴露為工具
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
        self.logger.info("已注入 MCP 工具介面到 Ollama 提供商")
    
    @property
    def provider_name(self) -> str:
        return "ollama"
    
    @property
    def default_port(self) -> int:
        return 11434
    
    async def check_health(self) -> ProviderHealth:
        """
        檢查 Ollama 服務健康狀態
        
        Returns:
            健康狀態資訊
        """
        start_time = time.time()
        
        try:
            async with aiohttp.ClientSession() as session:
                url = self.get_api_endpoint()
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout)
                ) as response:
                    response_time_ms = (time.time() - start_time) * 1000
                    
                    if response.status == 200:
                        # Ollama 根路徑回傳簡單訊息
                        
                        # 嘗試取得版本資訊
                        version = None
                        try:
                            async with session.get(
                                self.get_api_endpoint("api/version"),
                                timeout=aiohttp.ClientTimeout(total=5)
                            ) as version_response:
                                if version_response.status == 200:
                                    version_data = await version_response.json()
                                    version = version_data.get("version")
                        except Exception as e:
                            self.logger.debug(f"無法取得 Ollama 版本: {e}")
                        
                        # 取得可用模型列表
                        available_models = []
                        try:
                            models = await self.list_models()
                            available_models = [model.id for model in models]
                        except Exception as e:
                            self.logger.debug(f"無法列出 Ollama 模型: {e}")
                        
                        return ProviderHealth(
                            status=ProviderStatus.AVAILABLE,
                            version=version,
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
        列出 Ollama 可用模型
        
        Returns:
            模型列表
        """
        try:
            async with aiohttp.ClientSession() as session:
                url = self.get_api_endpoint("api/tags")
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout)
                ) as response:
                    response.raise_for_status()
                    data = await response.json()
                    
                    models = []
                    for model_data in data.get("models", []):
                        # 解析模型資訊
                        model_name = model_data.get("name", "")
                        
                        # 嘗試從名稱提取大小資訊（如 llama2:7b）
                        size = None
                        if ":" in model_name:
                            size = model_name.split(":")[1]
                        
                        # 取得模型詳細資訊
                        details = model_data.get("details", {})
                        
                        # 建立能力物件
                        capabilities = ModelCapability(
                            supports_streaming=True,  # Ollama 支援串流
                            supports_vision=False,  # 需根據模型判斷
                            supports_function_calling=False,
                            context_length=details.get("context_length", 2048),
                            max_tokens=2048
                        )
                        
                        models.append(LLMModel(
                            id=model_name,
                            name=model_name,
                            size=size,
                            capabilities=capabilities,
                            metadata={
                                "size_bytes": model_data.get("size", 0),
                                "modified_at": model_data.get("modified_at"),
                                "details": details
                            }
                        ))
                    
                    return models
        
        except aiohttp.ClientError as e:
            self.logger.error(f"無法列出 Ollama 模型: {e}")
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
        使用 Ollama 生成文字
        
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
                url = self.get_api_endpoint("api/generate")
                
                payload = {
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                    }
                }
                
                if max_tokens:
                    payload["options"]["num_predict"] = max_tokens
                
                # 加入其他 Ollama 特定選項
                if "system" in kwargs:
                    payload["system"] = kwargs["system"]
                
                async with session.post(
                    url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout),
                    headers=self.config.custom_headers
                ) as response:
                    response.raise_for_status()
                    data = await response.json()
                    
                    generated_text = data.get("response", "")
                    
                    # Ollama 不直接提供信心度，使用預設值
                    confidence = 0.85
                    
                    # 如果回應中有評估資訊，可以根據評估調整信心度
                    if data.get("done", False):
                        # 可以根據 total_duration, load_duration 等調整
                        pass
                    
                    return generated_text, confidence
        
        except aiohttp.ClientError as e:
            self.logger.error(f"Ollama 生成失敗: {e}")
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
        使用工具進行生成（function calling）
        
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
            # 取得 MCP 工具定義
            tools = self.mcp_tool_interface.get_ollama_tool_definitions()
            
            async with aiohttp.ClientSession() as session:
                url = self.get_api_endpoint("api/chat")
                
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
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                    }
                }
                
                if max_tokens:
                    payload["options"]["num_predict"] = max_tokens
                
                async with session.post(
                    url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout),
                    headers=self.config.custom_headers
                ) as response:
                    response.raise_for_status()
                    data = await response.json()
                    
                    message = data.get("message", {})
                    
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
                                response_text += f"{i+1}. {result.get('message', '操作完成')}\n"
                            else:
                                response_text += f"{i+1}. 錯誤: {result.get('error', '未知錯誤')}\n"
                        
                        return response_text, 0.9
                    else:
                        # 沒有工具呼叫，返回一般回應
                        content = message.get("content", "")
                        return content, 0.85
        
        except Exception as e:
            self.logger.error(f"使用工具生成失敗: {e}", exc_info=True)
            raise
