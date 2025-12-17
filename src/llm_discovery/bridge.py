"""
LLM IPC Bridge - 連接 LLM 和專案的橋樑

提供真實的 HTTP/IPC 呼叫實作，讓 LLM 能透過 MCP 協定操作專案功能
"""

import asyncio
import aiohttp
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from .discovery_service import DiscoveryService

logger = logging.getLogger(__name__)


class LLMIPCBridge:
    """
    LLM IPC 橋樑

    作為 LLM 和專案之間的橋樑：
    - 接收 LLM function calls
    - 透過 HTTP/IPC 呼叫專案 skills
    - 返回結果給 LLM

    使用真實的 HTTP 實作，支援：
    - GET/POST 請求
    - JSON-RPC 2.0 協定
    - 超時控制
    - 錯誤處理
    - 重試機制
    """

    def __init__(
        self,
        project_endpoint: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3
    ):
        """
        初始化橋樑

        Args:
            project_endpoint: 專案端點 URL（如: http://localhost:9001）
            timeout: HTTP 請求超時時間（秒）
            max_retries: 最大重試次數
        """
        self.project_endpoint = project_endpoint or "http://localhost:9001"
        self.timeout = timeout
        self.max_retries = max_retries
        self.discovery = DiscoveryService()
        self._session: Optional[aiohttp.ClientSession] = None

    async def _ensure_session(self) -> aiohttp.ClientSession:
        """確保 HTTP session 存在"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            )
        return self._session

    async def close(self):
        """關閉 HTTP session"""
        if self._session and not self._session.closed:
            await self._session.close()

    async def call_from_llm(
        self,
        function_call: Dict[str, Any],
        provider_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        從 LLM 接收 function call，轉換並執行

        Args:
            function_call: LLM function call 格式
                {
                    "name": "robot_command",
                    "arguments": {"robot_id": "robot-001", "action": "go_forward"}
                }
            provider_id: 指定的 provider ID（若未指定則自動選擇）

        Returns:
            執行結果
                {
                    "success": true,
                    "result": {...},
                    "error": null
                }
        """
        skill_name = function_call.get("name")
        arguments = function_call.get("arguments", {})

        logger.info(f"LLM 呼叫: {skill_name}, 參數: {arguments}")

        # 如果未指定 provider，掃描並選擇第一個可用的
        if not provider_id:
            providers = await self.discovery.scan_providers()
            if not providers:
                return {
                    "success": False,
                    "result": None,
                    "error": "No llm-cop providers found"
                }
            provider_id = providers[0].provider_id

        # 取得 provider manifest
        providers = await self.discovery.scan_providers()
        provider = next((p for p in providers if p.provider_id == provider_id), None)

        if not provider:
            return {
                "success": False,
                "result": None,
                "error": f"Provider {provider_id} not found"
            }

        # 找到對應的 skill
        skill = next((s for s in provider.skills if s.skill_id == skill_name), None)
        if not skill:
            return {
                "success": False,
                "result": None,
                "error": f"Skill {skill_name} not found in provider {provider_id}"
            }

        # 構建 MCP JSON-RPC 請求
        endpoint = provider.endpoints.get("invoke", provider.endpoints.get("default", ""))
        invoke_url = f"{endpoint.rstrip('/')}/invoke/{skill_name}"

        # 執行 HTTP 呼叫
        return await self._invoke_skill_http(invoke_url, arguments)

    async def _invoke_skill_http(
        self,
        url: str,
        parameters: Dict[str, Any],
        retry_count: int = 0
    ) -> Dict[str, Any]:
        """
        透過 HTTP POST 呼叫 skill

        Args:
            url: Skill invoke URL
            parameters: Skill 參數
            retry_count: 當前重試次數

        Returns:
            執行結果
        """
        session = await self._ensure_session()

        # 構建 JSON-RPC 2.0 請求
        request_payload = {
            "jsonrpc": "2.0",
            "id": f"req-{datetime.now().timestamp()}",
            "method": "invoke",
            "params": parameters
        }

        try:
            logger.debug(f"HTTP POST {url}: {request_payload}")

            async with session.post(url, json=request_payload) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"Skill 執行成功: {url}")
                    return {
                        "success": True,
                        "result": result.get("result", result),
                        "error": None
                    }
                else:
                    error_text = await response.text()
                    logger.warning(f"Skill 執行失敗 ({response.status}): {error_text}")

                    # 重試邏輯
                    if retry_count < self.max_retries and response.status >= 500:
                        logger.info(f"重試 ({retry_count + 1}/{self.max_retries})")
                        await asyncio.sleep(2 ** retry_count)  # 指數退避
                        return await self._invoke_skill_http(url, parameters, retry_count + 1)

                    return {
                        "success": False,
                        "result": None,
                        "error": f"HTTP {response.status}: {error_text}"
                    }

        except asyncio.TimeoutError:
            logger.error(f"HTTP 請求超時: {url}")
            return {
                "success": False,
                "result": None,
                "error": "Request timeout"
            }

        except aiohttp.ClientError as e:
            logger.error(f"HTTP 請求錯誤: {e}")

            # 重試邏輯
            if retry_count < self.max_retries:
                logger.info(f"重試 ({retry_count + 1}/{self.max_retries})")
                await asyncio.sleep(2 ** retry_count)
                return await self._invoke_skill_http(url, parameters, retry_count + 1)

            return {
                "success": False,
                "result": None,
                "error": f"Network error: {str(e)}"
            }

        except Exception as e:
            logger.exception(f"Skill 執行異常: {e}")
            return {
                "success": False,
                "result": None,
                "error": f"Unexpected error: {str(e)}"
            }

    async def expose_to_llm(self) -> List[Dict[str, Any]]:
        """
        將專案 skills 暴露給 LLM（OpenAI function calling 格式）

        Returns:
            OpenAI function definitions
        """
        # 掃描所有 providers
        providers = await self.discovery.scan_providers()

        functions = []
        for provider in providers:
            for skill in provider.skills:
                # 轉換為 OpenAI function calling 格式
                function_def = {
                    "name": skill.skill_id,
                    "description": skill.description,
                    "parameters": skill.parameters,
                    "_provider_id": provider.provider_id,  # 內部使用
                    "_provider_name": provider.name
                }
                functions.append(function_def)

        logger.info(f"暴露 {len(functions)} 個 skills 給 LLM")
        return functions

    async def health_check(self, provider_id: str) -> Dict[str, Any]:
        """
        檢查 provider 健康狀態

        Args:
            provider_id: Provider ID

        Returns:
            健康狀態資訊
        """
        health = await self.discovery.check_health(provider_id)

        if not health:
            return {
                "healthy": False,
                "error": f"Provider {provider_id} not found"
            }

        return {
            "healthy": health.healthy,
            "status": health.status.value,
            "response_time_ms": health.response_time_ms,
            "last_check": health.last_check_time.isoformat() if health.last_check_time else None,
            "consecutive_failures": health.consecutive_failures
        }

    async def list_available_skills(self) -> Dict[str, List[str]]:
        """
        列出所有可用的 skills

        Returns:
            provider_id -> [skill_ids] 的字典
        """
        providers = await self.discovery.scan_providers()

        result = {}
        for provider in providers:
            result[provider.provider_id] = [skill.skill_id for skill in provider.skills]

        return result

    async def __aenter__(self):
        """Context manager 支援"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager 支援"""
        await self.close()
