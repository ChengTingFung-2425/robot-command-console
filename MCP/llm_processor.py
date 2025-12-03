"""
LLM 處理器模組
用於處理音訊轉文字與指令解析
整合本地 LLM 提供商（Ollama, LM Studio 等）
支援網路不可用時自動回退到本地 LLM
"""

import asyncio
import json
import logging
import re
import socket
from typing import Dict, Any, List, Optional, Tuple
from .models import CommandSpec, CommandTarget, Priority
from .llm_provider_manager import LLMProviderManager

logger = logging.getLogger(__name__)


class LLMProcessor:
    """
    LLM 處理器，負責語音辨識與指令解析
    支援透過 MCP 注入本地 LLM 提供商
    支援網路不可用時自動回退到本地 LLM
    """

    # 預設配置常數
    DEFAULT_DURATION_MS = 3000  # 預設持續時間（毫秒）
    DEFAULT_CONFIDENCE = 0.95   # 預設信心度
    INTERNET_CHECK_HOSTS = [
        ("8.8.8.8", 53),        # Google DNS
        ("1.1.1.1", 53),        # Cloudflare DNS
        ("208.67.222.222", 53)  # OpenDNS
    ]
    INTERNET_CHECK_TIMEOUT = 3  # 網路檢查逾時（秒）

    def __init__(
        self,
        provider_manager: Optional[LLMProviderManager] = None,
        use_local_fallback: bool = True,
        cloud_provider_url: Optional[str] = None
    ):
        """
        初始化 LLM 處理器

        Args:
            provider_manager: LLM 提供商管理器，用於管理本地 LLM 提供商
            use_local_fallback: 當網路不可用時是否自動使用本地 LLM
            cloud_provider_url: 雲端 LLM 提供商 URL（用於網路連線檢查）
        """
        self.provider_manager = provider_manager or LLMProviderManager()
        self.use_local_fallback = use_local_fallback
        self.cloud_provider_url = cloud_provider_url
        self.logger = logging.getLogger(__name__)
        self._last_internet_check = None
        self._internet_available = None
        self._warnings: List[Dict[str, Any]] = []  # 儲存警告訊息

    def check_internet_connection(self, timeout: Optional[int] = None) -> bool:
        """
        檢查網路連線狀態

        Args:
            timeout: 逾時時間（秒）

        Returns:
            True 如果網路可用，False 如果不可用
        """
        timeout = timeout or self.INTERNET_CHECK_TIMEOUT

        for host, port in self.INTERNET_CHECK_HOSTS:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(timeout)
                result = sock.connect_ex((host, port))
                sock.close()

                if result == 0:
                    self._internet_available = True
                    return True
            except (socket.error, socket.timeout, OSError):
                continue

        self._internet_available = False
        return False

    async def check_internet_connection_async(self, timeout: Optional[int] = None) -> bool:
        """
        非同步檢查網路連線狀態

        Args:
            timeout: 逾時時間（秒）

        Returns:
            True 如果網路可用，False 如果不可用
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.check_internet_connection, timeout)

    def add_warning(self, warning_type: str, message: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        添加警告訊息

        Args:
            warning_type: 警告類型（如 'internet_unavailable', 'local_llm_error'）
            message: 警告訊息
            details: 額外細節

        Returns:
            警告物件
        """
        import time
        warning = {
            "type": warning_type,
            "message": message,
            "timestamp": time.time(),
            "details": details or {}
        }
        self._warnings.append(warning)
        self.logger.warning(f"[{warning_type}] {message}", extra=details or {})
        return warning

    def get_warnings(self, clear: bool = False) -> List[Dict[str, Any]]:
        """
        取得所有警告訊息

        Args:
            clear: 是否清除警告

        Returns:
            警告列表
        """
        warnings = self._warnings.copy()
        if clear:
            self._warnings.clear()
        return warnings

    def clear_warnings(self) -> None:
        """清除所有警告"""
        self._warnings.clear()

    def get_connection_status(self) -> Dict[str, Any]:
        """
        取得連線狀態摘要

        Returns:
            連線狀態資訊
        """
        local_provider = self.provider_manager.get_provider()
        local_available = local_provider is not None

        return {
            "internet_available": self._internet_available,
            "local_llm_available": local_available,
            "local_llm_provider": local_provider.provider_name if local_provider else None,
            "using_fallback": (
                not self._internet_available and local_available
                if self._internet_available is not None else None
            ),
            "warnings_count": len(self._warnings)
        }

    async def transcribe_audio(
        self,
        audio_bytes: bytes,
        audio_format: str = "opus",
        language: str = "zh-TW"
    ) -> Tuple[str, float]:
        """
        將音訊轉換為文字

        Args:
            audio_bytes: 音訊資料（位元組）
            audio_format: 音訊格式
            language: 語言代碼

        Returns:
            (轉錄文字, 信心度) 的元組
        """
        try:
            # 嘗試使用本地 LLM 提供商
            provider = self.provider_manager.get_provider()
            if provider:
                try:
                    return await provider.transcribe_audio(audio_bytes, audio_format, language)
                except NotImplementedError:
                    self.logger.debug(f"提供商 {provider.provider_name} 不支援語音轉文字，使用模擬結果")
                except Exception as e:
                    self.logger.warning(f"提供商語音轉文字失敗: {e}，使用模擬結果")

            # 模擬結果（當沒有可用提供商或提供商不支援時）
            self.logger.info(f"使用模擬音訊轉錄，格式={audio_format}, 語言={language}")
            transcription = "向前移動三秒"
            confidence = 0.95

            return transcription, confidence

        except Exception as e:
            self.logger.error(f"音訊轉錄失敗: {e}", exc_info=True)
            raise

    async def parse_command(
        self,
        transcription: str,
        robot_id: str,
        context: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
        prefer_cloud: bool = False
    ) -> Optional[CommandSpec]:
        """
        使用 LLM 解析指令（透過本地提供商或規則式）
        支援網路不可用時自動回退到本地 LLM

        Args:
            transcription: 轉錄的文字
            robot_id: 目標機器人 ID
            context: 額外的上下文資訊
            model: 使用的模型名稱（選用）
            prefer_cloud: 是否優先使用雲端 LLM（如果可用）

        Returns:
            解析後的指令規格，如果無法解析則返回 None
        """
        try:
            provider = None
            using_fallback = False

            # 如果優先使用雲端，先檢查網路連線
            if prefer_cloud and self.use_local_fallback:
                internet_available = await self.check_internet_connection_async()

                if not internet_available:
                    # 網路不可用，添加警告並使用本地 LLM
                    self.add_warning(
                        warning_type="internet_unavailable",
                        message="網路連線不可用，已切換到本地 LLM 提供商",
                        details={
                            "action": "fallback_to_local",
                            "robot_id": robot_id
                        }
                    )
                    using_fallback = True
                    self.logger.info("網路不可用，使用本地 LLM 作為回退")

            # 取得本地 LLM 提供商
            provider = self.provider_manager.get_provider()

            if provider:
                try:
                    params = await self._llm_parse(transcription, robot_id, provider, model)
                    if params:
                        # 如果使用回退，在結果中標記
                        if using_fallback:
                            params["_using_fallback"] = True
                            params["_fallback_provider"] = provider.provider_name

                        command = CommandSpec(
                            type="robot.action",
                            target=CommandTarget(robot_id=robot_id),
                            params=params,
                            priority=Priority.NORMAL
                        )
                        return command
                except Exception as e:
                    # 本地 LLM 錯誤，添加警告（不向用戶暴露詳細錯誤）
                    self.add_warning(
                        warning_type="local_llm_error",
                        message="本地 LLM 處理失敗，已切換到規則式解析",
                        details={
                            "provider": provider.provider_name if provider else None,
                            "action": "fallback_to_rule_based"
                        }
                    )
                    self.logger.warning(f"LLM 解析失敗，回退到規則式解析: {e}")
            else:
                # 沒有本地 LLM 可用
                self.add_warning(
                    warning_type="no_local_llm",
                    message="沒有可用的本地 LLM 提供商",
                    details={
                        "action": "fallback_to_rule_based",
                        "available_providers": self.provider_manager.list_providers()
                    }
                )

            # 回退到簡單的規則匹配
            params = self._simple_parse(transcription)

            if params:
                params["_parsed_by"] = "rule_based"
                command = CommandSpec(
                    type="robot.action",
                    target=CommandTarget(robot_id=robot_id),
                    params=params,
                    priority=Priority.NORMAL
                )
                return command

            return None

        except Exception as e:
            self.logger.error(f"指令解析失敗: {e}", exc_info=True)
            self.add_warning(
                warning_type="parse_error",
                message="指令解析過程發生錯誤",
                details={}
            )
            return None

    async def _llm_parse(
        self,
        transcription: str,
        robot_id: str,
        provider,
        model: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        使用本地 LLM 提供商解析指令

        Args:
            transcription: 轉錄的文字
            robot_id: 目標機器人 ID
            provider: LLM 提供商實例
            model: 使用的模型名稱

        Returns:
            解析後的參數字典
        """
        # 如果未指定模型，使用第一個可用模型
        if not model:
            models = await provider.list_models()
            if not models:
                raise ValueError("沒有可用的模型")
            model = models[0].id
            self.logger.info(f"使用模型: {model}")

        # 建構提示
        prompt = f"""你是一個機器人指令解析助手。請將以下自然語言指令轉換為結構化指令。

使用者說：{transcription}
目標機器人：{robot_id}

可用的動作包括：
- go_forward: 向前移動
- back_fast: 向後移動
- turn_left: 向左轉
- turn_right: 向右轉
- stop: 停止
- stand: 站立
- wave: 揮手
- bow: 鞠躬
- dance_two: 跳舞

請以 JSON 格式返回，不要包含其他文字：
{{
    "action_name": "動作名稱",
    "duration_ms": 持續時間（毫秒，整數）
}}

如果無法解析，返回空物件 {{}}"""

        # 呼叫 LLM
        response_text, confidence = await provider.generate(
            prompt=prompt,
            model=model,
            temperature=0.3,  # 降低溫度以獲得更確定的結果
            max_tokens=200
        )

        self.logger.debug(f"LLM 回應: {response_text}")

        # 解析 JSON 回應
        try:
            # 嘗試提取 JSON（處理可能有額外文字的情況）
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1

            if json_start >= 0 and json_end > json_start:
                json_text = response_text[json_start:json_end]
                params = json.loads(json_text)

                # 驗證必要欄位
                if params and "action_name" in params and "duration_ms" in params:
                    return params

            return None

        except json.JSONDecodeError as e:
            self.logger.warning(f"無法解析 LLM 回應為 JSON: {e}")
            return None

    def _simple_parse(self, text: str) -> Optional[Dict[str, Any]]:
        """
        簡單的規則式指令解析（示範用）

        Args:
            text: 要解析的文字

        Returns:
            解析後的參數字典
        """
        text = text.lower()

        # 動作對應表
        action_keywords = {
            "向前": "go_forward",
            "前進": "go_forward",
            "往前": "go_forward",
            "後退": "back_fast",
            "向後": "back_fast",
            "左轉": "turn_left",
            "向左": "turn_left",
            "右轉": "turn_right",
            "向右": "turn_right",
            "停止": "stop",
            "站立": "stand",
            "揮手": "wave",
            "鞠躬": "bow",
            "跳舞": "dance_two",
        }

        # 尋找動作
        action_name = None
        for keyword, action in action_keywords.items():
            if keyword in text:
                action_name = action
                break

        if not action_name:
            return None

        # 提取時間（秒）
        duration_ms = self.DEFAULT_DURATION_MS  # 使用類常數

        # 中文數字對應表
        chinese_numbers = {
            '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
            '六': 6, '七': 7, '八': 8, '九': 9, '十': 10
        }

        # 先嘗試匹配中文數字 + 秒
        for chinese, value in chinese_numbers.items():
            if f'{chinese}秒' in text:
                duration_ms = value * 1000
                break
        else:
            # 再嘗試匹配阿拉伯數字 + 秒
            time_match = re.search(r'(\d+)\s*秒', text)
            if time_match:
                seconds = int(time_match.group(1))
                duration_ms = seconds * 1000

        return {
            "action_name": action_name,
            "duration_ms": duration_ms
        }
