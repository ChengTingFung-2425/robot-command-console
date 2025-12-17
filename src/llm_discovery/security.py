"""
安全模組：防止模型解密攻擊

實作多層安全機制：
1. Prompt Sanitization - 清理和保護用戶 prompt
2. Response Filtering - 過濾可能洩露資訊的回應
3. Memory Cleanup - 清除記憶體中的敏感資料
"""

import gc
import re
import time
import random
from typing import Dict, Any, Optional


class PromptSanitizer:
    """Prompt 清理器 - 確保 prompt 不被記錄或洩露"""

    # 敏感資訊模式
    SENSITIVE_PATTERNS = [
        r"password[:\s]*\S+",
        r"token[:\s]*\S+",
        r"api[_-]?key[:\s]*\S+",
        r"secret[:\s]*\S+",
        r"private[_-]?key[:\s]*\S+",
    ]

    @staticmethod
    def sanitize_for_logging(text: str) -> str:
        """
        清理文字用於日誌記錄

        Args:
            text: 原始文字

        Returns:
            清理後的文字（不包含敏感資訊）
        """
        if not text:
            return "[EMPTY]"

        # 完全隱藏 prompt 內容
        return "[PROMPT_REDACTED]"

    @staticmethod
    def remove_sensitive_info(text: str) -> str:
        """
        移除文字中的敏感資訊

        Args:
            text: 原始文字

        Returns:
            移除敏感資訊後的文字
        """
        result = text
        for pattern in PromptSanitizer.SENSITIVE_PATTERNS:
            result = re.sub(pattern, "[REDACTED]", result, flags=re.IGNORECASE)
        return result

    @staticmethod
    def clear_from_memory(prompt: str):
        """
        從記憶體中清除 prompt

        注意：Python 字符串是不可變的，此方法只能觸發垃圾回收，
        無法保證立即從記憶體中清除。調用者應確保不保留對 prompt 的引用。

        Args:
            prompt: 要清除的 prompt
        """
        if prompt:
            # 此方法無法保證 prompt 會立即或安全地從記憶體中清除。
            # 垃圾回收僅是提示，不能作為安全清除的依據。請勿將此方法用於關鍵安全場景。
            # 調用者必須在自己的作用域中刪除所有 prompt 的引用，否則資料可能仍留在記憶體中。
            gc.collect()


class ResponseFilter:
    """回應過濾器 - 防止回應中洩露 prompt 或模型資訊"""

    # 禁止的元資料鍵（可能洩露模型資訊）
    FORBIDDEN_METADATA_KEYS = [
        "model_weights",
        "model_state",
        "embeddings",
        "logits",
        "attention_weights",
        "prompt_tokens",
        "raw_prompt",
        "internal_state",
    ]

    @staticmethod
    def filter_prompt_echo(response: str, prompt: Optional[str] = None) -> str:
        """
        移除回應中的 prompt 回顯

        Args:
            response: LLM 回應
            prompt: 原始 prompt（如果提供，會檢查是否被回顯）

        Returns:
            過濾後的回應
        """
        if not response:
            return response

        # 如果提供了 prompt，檢查並移除回顯
        if prompt and prompt in response:
            # 移除完全匹配的 prompt
            response = response.replace(prompt, "")

        # 移除常見的 prompt 回顯模式
        patterns = [
            r"^User:\s*.+?\n",  # "User: ..." 格式
            r"^Prompt:\s*.+?\n",  # "Prompt: ..." 格式
            r"^\[Input\]:\s*.+?\n",  # "[Input]: ..." 格式
        ]

        for pattern in patterns:
            response = re.sub(pattern, "", response, flags=re.MULTILINE)

        return response.strip()

    @staticmethod
    def remove_metadata(response: Dict[str, Any]) -> Dict[str, Any]:
        """
        移除可能洩露資訊的元資料

        Args:
            response: 回應字典

        Returns:
            清理後的回應字典
        """
        if not isinstance(response, dict):
            return response

        # 只保留安全的鍵
        safe_keys = {"result", "status", "skill_id", "timestamp", "trace_id"}

        # 創建清理後的回應
        cleaned = {}
        for key, value in response.items():
            if key in safe_keys:
                cleaned[key] = value
            elif key not in ResponseFilter.FORBIDDEN_METADATA_KEYS:
                # 遞迴清理嵌套字典
                if isinstance(value, dict):
                    cleaned[key] = ResponseFilter.remove_metadata(value)
                else:
                    cleaned[key] = value

        return cleaned

    @staticmethod
    def detect_prompt_injection(text: str) -> bool:
        """
        檢測 prompt injection 攻擊

        Args:
            text: 要檢測的文字

        Returns:
            True 如果檢測到攻擊，否則 False
        """
        # 常見的 prompt injection 模式
        injection_patterns = [
            r"ignore\s+previous\s+instructions",
            r"ignore\s+all\s+instructions",
            r"system\s*:\s*you\s+are",
            r"<\s*system\s*>",
            r"\[system\]",
            r"reveal\s+your\s+prompt",
            r"what\s+are\s+your\s+instructions",
        ]

        for pattern in injection_patterns:
            if re.search(pattern, text, flags=re.IGNORECASE):
                return True

        return False


class TimingObfuscator:
    """時間混淆器 - 防止時間側信道攻擊"""

    @staticmethod
    def add_random_delay(min_ms: int = 10, max_ms: int = 100):
        """
        添加隨機延遲

        Args:
            min_ms: 最小延遲（毫秒）
            max_ms: 最大延遲（毫秒）
        """
        delay_ms = random.uniform(min_ms, max_ms)
        time.sleep(delay_ms / 1000.0)

    @staticmethod
    def normalize_response_time(
        actual_time_ms: float,
        target_time_ms: float = 100.0
    ) -> float:
        """
        標準化回應時間，防止時間洩露

        Args:
            actual_time_ms: 實際處理時間
            target_time_ms: 目標回應時間

        Returns:
            標準化後的時間（總是 >= target_time_ms）
        """
        if actual_time_ms < target_time_ms:
            # 添加延遲以達到目標時間
            delay_ms = target_time_ms - actual_time_ms
            time.sleep(delay_ms / 1000.0)
            return target_time_ms
        return actual_time_ms


class MemoryGuard:
    """記憶體守護 - 確保敏感資料不殘留在記憶體中"""

    @staticmethod
    def secure_delete(data: Any):
        """
        安全刪除資料

        注意：此方法只能清空可變容器（list, dict），
        對於不可變類型（str）無法真正清除記憶體。

        Args:
            data: 要刪除的資料（應為可變容器）
        """
        if isinstance(data, (list, dict)):
            # 清空可變容器
            data.clear()
        # 對於字符串等不可變類型，無法安全刪除
        # 只能觸發垃圾回收
        gc.collect()

    @staticmethod
    def create_secure_context():
        """
        創建安全上下文管理器

        Returns:
            上下文管理器
        """
        class SecureContext:
            def __init__(self):
                self.data = {}

            def __enter__(self):
                return self.data

            def __exit__(self, exc_type, exc_val, exc_tb):
                # 清理所有資料
                for key in list(self.data.keys()):
                    MemoryGuard.secure_delete(self.data[key])
                self.data.clear()
                gc.collect()

        return SecureContext()
