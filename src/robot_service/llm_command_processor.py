"""
LLM Command Processor

處理原生語音/文字指令，透過 LLM IPC Bridge 與 LLM 互動
整合追蹤功能，記錄完整的處理流程
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import time

from .llm_trace_manager import LLMTraceManager, TraceEventType

logger = logging.getLogger(__name__)


class LLMCommandProcessor:
    """
    LLM 指令處理器
    
    功能：
    - 接收原生語音指令
    - 接收原生文字指令
    - 透過 LLM IPC Bridge 發送給 LLM
    - 處理 LLM 返回的 function calls
    - 執行對應的 skills
    """
    
    def __init__(
        self,
        bridge=None,
        llm_provider: Optional[str] = None,
        enable_speech: bool = False,
        trace_manager: Optional[LLMTraceManager] = None
    ):
        """
        初始化 LLM 指令處理器
        
        Args:
            bridge: LLMIPCBridge 實例
            llm_provider: LLM 提供商（如 "openai", "anthropic" 等）
            enable_speech: 是否啟用語音處理
            trace_manager: 追蹤管理器（用於記錄處理流程）
        """
        self.bridge = bridge
        self.llm_provider = llm_provider or "openai"
        self.enable_speech = enable_speech
        self.trace_manager = trace_manager or LLMTraceManager()
        self._conversation_history: List[Dict[str, Any]] = []
        self._available_functions: List[Dict[str, Any]] = []
        
    async def initialize(self) -> bool:
        """
        初始化處理器
        
        Returns:
            是否成功初始化
        """
        try:
            if not self.bridge:
                logger.warning("LLM Bridge 未設定，部分功能將無法使用")
                return False
            
            # 從 bridge 取得可用的 functions
            self._available_functions = await self.bridge.expose_to_llm()
            logger.info(f"載入 {len(self._available_functions)} 個可用 functions")
            
            return True
            
        except Exception as e:
            logger.error(f"初始化 LLM Command Processor 失敗: {e}")
            return False
    
    async def process_text_command(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        處理原生文字指令（帶追蹤）
        
        Args:
            text: 使用者輸入的文字指令
            context: 額外的上下文資訊
        
        Returns:
            處理結果
                {
                    "success": bool,
                    "response": str,  # LLM 的回應
                    "executed_functions": List[Dict],  # 執行的 functions
                    "error": Optional[str],
                    "trace_id": str  # 追蹤 ID
                }
        """
        # 開始追蹤
        trace_id = await self.trace_manager.start_trace(
            input_type="text",
            input_data=text,
            metadata=context
        )
        
        logger.info(f"處理文字指令 [trace={trace_id}]: {text}")
        
        try:
            # 構建 LLM 請求
            messages = self._build_messages(text, context)
            
            # 追蹤 LLM 請求
            await self.trace_manager.trace_llm_request(
                trace_id,
                messages,
                self._available_functions,
                self.llm_provider
            )
            
            # 呼叫 LLM
            start_time = time.time()
            llm_response = await self._call_llm(messages)
            processing_time_ms = (time.time() - start_time) * 1000
            
            # 追蹤 LLM 回應
            await self.trace_manager.trace_llm_response(
                trace_id,
                llm_response,
                processing_time_ms
            )
            
            # 處理 LLM 返回的 function calls
            executed_functions = []
            if "function_call" in llm_response:
                function_result = await self._execute_function_call_with_trace(
                    trace_id,
                    llm_response["function_call"]
                )
                executed_functions.append(function_result)
            
            # 提取 LLM 的文字回應
            response_text = llm_response.get("content", "指令已處理")
            
            # 記錄到對話歷史
            self._conversation_history.append({
                "role": "user",
                "content": text,
                "timestamp": datetime.now().isoformat(),
                "trace_id": trace_id
            })
            self._conversation_history.append({
                "role": "assistant",
                "content": response_text,
                "timestamp": datetime.now().isoformat(),
                "trace_id": trace_id
            })
            
            # 完成追蹤
            await self.trace_manager.complete_trace(
                trace_id,
                success=True,
                final_result={
                    "response": response_text,
                    "executed_functions": len(executed_functions)
                }
            )
            
            return {
                "success": True,
                "response": response_text,
                "executed_functions": executed_functions,
                "error": None,
                "trace_id": trace_id
            }
            
        except Exception as e:
            logger.exception(f"處理文字指令失敗 [trace={trace_id}]: {e}")
            
            # 追蹤錯誤
            await self.trace_manager.trace_error(
                trace_id,
                str(e),
                {"input": text, "context": context}
            )
            
            # 完成追蹤（失敗）
            await self.trace_manager.complete_trace(
                trace_id,
                success=False,
                final_result={"error": str(e)}
            )
            
            return {
                "success": False,
                "response": f"處理指令時發生錯誤: {str(e)}",
                "executed_functions": [],
                "error": str(e),
                "trace_id": trace_id
            }
    
    async def process_speech_command(
        self,
        audio_data: bytes,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        處理原生語音指令（帶追蹤）
        
        Args:
            audio_data: 音訊資料（bytes）
            context: 額外的上下文資訊
        
        Returns:
            處理結果（格式同 process_text_command）
        """
        if not self.enable_speech:
            return {
                "success": False,
                "response": "語音功能未啟用",
                "executed_functions": [],
                "error": "Speech processing disabled"
            }
        
        # 開始追蹤
        trace_id = await self.trace_manager.start_trace(
            input_type="speech",
            input_data=f"<audio data: {len(audio_data)} bytes>",
            metadata=context
        )
        
        logger.info(f"處理語音指令 [trace={trace_id}]")
        
        try:
            # 1. 語音轉文字（STT）
            text = await self._speech_to_text(audio_data)
            logger.info(f"語音辨識結果 [trace={trace_id}]: {text}")
            
            # 追蹤語音轉文字結果
            await self.trace_manager._add_event(
                trace_id,
                TraceEventType.LLM_RESPONSE,  # 重用類型
                {"speech_to_text": text, "audio_size": len(audio_data)}
            )
            
            # 2. 處理文字指令（會創建新的 sub-trace）
            result = await self.process_text_command(text, context)
            
            # 將 sub-trace 關聯到主 trace
            result["parent_trace_id"] = trace_id
            result["input_type"] = "speech"
            
            # 3. 文字轉語音（TTS）- 可選
            if result["success"] and self.enable_speech:
                await self._text_to_speech(result["response"])
            
            # 完成主追蹤
            await self.trace_manager.complete_trace(
                trace_id,
                success=result["success"],
                final_result={"text_trace_id": result.get("trace_id")}
            )
            
            return result
            
        except Exception as e:
            logger.exception(f"處理語音指令失敗 [trace={trace_id}]: {e}")
            
            await self.trace_manager.trace_error(trace_id, str(e))
            await self.trace_manager.complete_trace(trace_id, success=False)
            
            return {
                "success": False,
                "response": f"處理語音指令時發生錯誤: {str(e)}",
                "executed_functions": [],
                "error": str(e),
                "trace_id": trace_id
            }
    
    async def _call_llm(
        self,
        messages: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        呼叫 LLM API
        
        Args:
            messages: 對話訊息列表
        
        Returns:
            LLM 回應
        """
        # 這裡需要整合實際的 LLM API
        # 例如 OpenAI, Anthropic, 或本地 LLM
        
        if self.llm_provider == "openai":
            return await self._call_openai(messages)
        elif self.llm_provider == "anthropic":
            return await self._call_anthropic(messages)
        elif self.llm_provider == "local":
            return await self._call_local_llm(messages)
        else:
            raise ValueError(f"不支援的 LLM 提供商: {self.llm_provider}")
    
    async def _call_openai(
        self,
        messages: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        呼叫 OpenAI API
        
        Args:
            messages: 對話訊息列表
        
        Returns:
            OpenAI 回應
        """
        try:
            # 動態導入 openai（避免強制依賴）
            import openai
            
            # 構建 API 請求
            response = await openai.ChatCompletion.acreate(
                model="gpt-4",
                messages=messages,
                functions=self._available_functions if self._available_functions else None,
                function_call="auto" if self._available_functions else None,
                temperature=0.7
            )
            
            # 提取回應
            message = response.choices[0].message
            
            result = {
                "content": message.get("content", ""),
                "role": message.get("role", "assistant")
            }
            
            # 如果有 function call
            if message.get("function_call"):
                result["function_call"] = {
                    "name": message["function_call"]["name"],
                    "arguments": message["function_call"]["arguments"]
                }
            
            return result
            
        except ImportError:
            logger.error("OpenAI SDK 未安裝，請執行: pip install openai")
            return {
                "content": "OpenAI SDK 未安裝，無法處理指令",
                "role": "assistant"
            }
        except Exception as e:
            logger.exception(f"呼叫 OpenAI API 失敗: {e}")
            return {
                "content": f"LLM 處理失敗: {str(e)}",
                "role": "assistant"
            }
    
    async def _call_anthropic(
        self,
        messages: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        呼叫 Anthropic (Claude) API
        
        Args:
            messages: 對話訊息列表
        
        Returns:
            Anthropic 回應
        """
        # TODO: 實作 Anthropic API 整合
        logger.warning("Anthropic API 整合尚未實作")
        return {
            "content": "Anthropic API 整合尚未實作",
            "role": "assistant"
        }
    
    async def _call_local_llm(
        self,
        messages: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        呼叫本地 LLM（透過 Ollama 或 LM Studio）
        
        Args:
            messages: 對話訊息列表
        
        Returns:
            本地 LLM 回應
        """
        # TODO: 整合 LLMProviderManager
        logger.warning("本地 LLM 整合尚未實作")
        return {
            "content": "本地 LLM 整合尚未實作",
            "role": "assistant"
        }
    
    async def _execute_function_call_with_trace(
        self,
        trace_id: str,
        function_call: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        執行 LLM 返回的 function call（帶追蹤）
        
        Args:
            trace_id: 追蹤 ID
            function_call: Function call 資訊
        
        Returns:
            執行結果
        """
        function_name = function_call["name"]
        logger.info(f"執行 function [trace={trace_id}]: {function_name}")
        
        # 追蹤 function call
        await self.trace_manager.trace_function_call(
            trace_id,
            function_name,
            function_call.get("arguments", {})
        )
        
        try:
            # 透過 bridge 執行 function
            start_time = time.time()
            result = await self.bridge.call_from_llm(function_call)
            execution_time_ms = (time.time() - start_time) * 1000
            
            # 追蹤 bridge 呼叫（如果有端點資訊）
            if hasattr(self.bridge, 'project_endpoint'):
                await self.trace_manager.trace_bridge_call(
                    trace_id,
                    self.bridge.project_endpoint,
                    function_call,
                    result
                )
            
            # 追蹤 function 執行結果
            await self.trace_manager.trace_function_executed(
                trace_id,
                function_name,
                result,
                execution_time_ms
            )
            
            return {
                "function_name": function_name,
                "success": result["success"],
                "result": result["result"],
                "error": result["error"],
                "execution_time_ms": execution_time_ms
            }
            
        except Exception as e:
            logger.exception(f"執行 function 失敗 [trace={trace_id}]: {e}")
            
            # 追蹤錯誤
            await self.trace_manager.trace_error(
                trace_id,
                f"Function execution failed: {str(e)}",
                {"function_name": function_name}
            )
            
            return {
                "function_name": function_name,
                "success": False,
                "result": None,
                "error": str(e)
            }
    
    async def _execute_function_call(
        self,
        function_call: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        執行 LLM 返回的 function call（無追蹤，向後相容）
        
        Args:
            function_call: Function call 資訊
        
        Returns:
            執行結果
        """
        function_name = function_call["name"]
        logger.info(f"執行 function: {function_name}")
        
        try:
            # 透過 bridge 執行 function
            result = await self.bridge.call_from_llm(function_call)
            
            return {
                "function_name": function_name,
                "success": result["success"],
                "result": result["result"],
                "error": result["error"]
            }
            
        except Exception as e:
            logger.exception(f"執行 function 失敗: {e}")
            return {
                "function_name": function_name,
                "success": False,
                "result": None,
                "error": str(e)
            }
    
    async def _speech_to_text(self, audio_data: bytes) -> str:
        """
        語音轉文字
        
        Args:
            audio_data: 音訊資料
        
        Returns:
            辨識的文字
        """
        # TODO: 整合語音辨識服務
        # 可以使用 OpenAI Whisper, Google Speech-to-Text 等
        logger.warning("語音轉文字功能尚未實作")
        return "語音辨識功能尚未實作"
    
    async def _text_to_speech(self, text: str) -> bytes:
        """
        文字轉語音
        
        Args:
            text: 要轉換的文字
        
        Returns:
            音訊資料
        """
        # TODO: 整合語音合成服務
        # 可以使用 OpenAI TTS, Google Text-to-Speech 等
        logger.warning("文字轉語音功能尚未實作")
        return b""
    
    def _build_messages(
        self,
        user_input: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, str]]:
        """
        構建 LLM 訊息列表
        
        Args:
            user_input: 使用者輸入
            context: 上下文資訊
        
        Returns:
            訊息列表
        """
        messages = []
        
        # 系統提示詞
        system_prompt = (
            "你是一個機器人控制助手。你可以理解使用者的指令，"
            "並透過提供的 functions 來控制機器人。"
            "請根據使用者的需求選擇合適的 function 並提供正確的參數。"
        )
        
        # 如果有上下文，加入系統提示詞
        if context:
            system_prompt += f"\n\n當前上下文: {context}"
        
        messages.append({
            "role": "system",
            "content": system_prompt
        })
        
        # 加入對話歷史（最近 10 條）
        recent_history = self._conversation_history[-10:]
        messages.extend(recent_history)
        
        # 加入當前使用者輸入
        messages.append({
            "role": "user",
            "content": user_input
        })
        
        return messages
    
    def clear_history(self):
        """清除對話歷史"""
        self._conversation_history.clear()
        logger.info("對話歷史已清除")
    
    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """取得對話歷史"""
        return self._conversation_history.copy()
    
    async def get_trace(self, trace_id: str) -> Optional[List]:
        """
        取得追蹤記錄
        
        Args:
            trace_id: 追蹤 ID
        
        Returns:
            追蹤事件列表
        """
        return await self.trace_manager.get_trace(trace_id)
    
    async def get_trace_summary(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """
        取得追蹤摘要
        
        Args:
            trace_id: 追蹤 ID
        
        Returns:
            追蹤摘要
        """
        return await self.trace_manager.get_trace_summary(trace_id)
    
    async def export_trace(self, trace_id: str, format: str = "json") -> str:
        """
        匯出追蹤記錄
        
        Args:
            trace_id: 追蹤 ID
            format: 匯出格式（json, text）
        
        Returns:
            匯出的追蹤資料
        """
        return await self.trace_manager.export_trace(trace_id, format)
