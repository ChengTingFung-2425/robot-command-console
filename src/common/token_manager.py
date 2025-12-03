"""
Token 管理模組
提供 Electron 與背景服務間的安全 Token 管理功能

功能：
- Token 生成與驗證
- Token 輪替支援
- Token 過期管理
- Token 資訊查詢
"""

import hashlib
import hmac
import logging
import secrets
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable, Dict, List, Optional

from .datetime_utils import utc_now


logger = logging.getLogger(__name__)


@dataclass
class TokenInfo:
    """Token 資訊"""
    token_id: str
    created_at: datetime
    expires_at: Optional[datetime]
    is_active: bool = True
    rotation_count: int = 0

    def is_expired(self) -> bool:
        """檢查 Token 是否已過期"""
        if self.expires_at is None:
            return False
        return utc_now() > self.expires_at

    def time_until_expiry(self) -> Optional[timedelta]:
        """取得距離過期的時間"""
        if self.expires_at is None:
            return None
        return self.expires_at - utc_now()

    def to_dict(self) -> dict:
        """轉換為字典"""
        return {
            "token_id": self.token_id,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_active": self.is_active,
            "is_expired": self.is_expired(),
            "rotation_count": self.rotation_count,
        }


@dataclass
class TokenRotationEvent:
    """Token 輪替事件"""
    old_token_id: Optional[str]
    new_token_id: str
    timestamp: datetime = field(default_factory=utc_now)
    reason: str = "scheduled"


TokenRotationCallback = Callable[[str, TokenInfo], None]


class TokenManager:
    """
    Token 管理器

    提供安全的 Token 生命週期管理：
    - 生成加密安全的 Token
    - Token 驗證
    - Token 輪替（不中斷服務）
    - Token 過期管理
    - 輪替事件通知

    使用範例：
    ```python
    manager = TokenManager(token_expiry_hours=24)

    # 生成新 Token
    token, info = manager.generate_token()

    # 驗證 Token
    if manager.verify_token(token):
        print("Token valid")

    # 輪替 Token
    new_token, new_info = manager.rotate_token()

    # 訂閱輪替事件
    def on_rotation(new_token, info):
        print(f"New token: {new_token[:8]}...")

    manager.on_token_rotated(on_rotation)
    ```
    """

    def __init__(
        self,
        token_length: int = 32,
        token_expiry_hours: Optional[int] = None,
        grace_period_seconds: int = 60,
        max_rotation_history: int = 10,
    ):
        """
        初始化 Token 管理器

        Args:
            token_length: Token 長度（bytes），預設 32（256 bits）
            token_expiry_hours: Token 有效時間（小時），None 表示永不過期
            grace_period_seconds: 輪替後舊 Token 的寬限期（秒）
            max_rotation_history: 保留的輪替歷史記錄數
        """
        self._token_length = token_length
        self._token_expiry_hours = token_expiry_hours
        self._grace_period_seconds = grace_period_seconds
        self._max_rotation_history = max_rotation_history

        self._current_token: Optional[str] = None
        self._current_info: Optional[TokenInfo] = None
        self._previous_tokens: Dict[str, TokenInfo] = {}  # 寬限期內的舊 Token
        self._rotation_history: List[TokenRotationEvent] = []
        self._rotation_callbacks: List[TokenRotationCallback] = []

        self._lock = threading.Lock()
        self._rotation_count = 0

        logger.info(
            "TokenManager initialized",
            extra={
                "token_length": token_length,
                "expiry_hours": token_expiry_hours,
                "grace_period_seconds": grace_period_seconds,
            },
        )

    def _generate_token_id(self) -> str:
        """生成唯一的 Token ID（用於識別，非 Token 本身）"""
        return secrets.token_hex(8)

    def _calculate_expiry(self) -> Optional[datetime]:
        """計算 Token 過期時間"""
        if self._token_expiry_hours is None:
            return None
        return utc_now() + timedelta(hours=self._token_expiry_hours)

    def _hash_token(self, token: str) -> str:
        """對 Token 進行雜湊（用於安全比較）"""
        return hashlib.sha256(token.encode()).hexdigest()

    def generate_token(self) -> tuple[str, TokenInfo]:
        """
        生成新的 Token

        Returns:
            tuple: (token, token_info)
        """
        with self._lock:
            # 如果已有 Token，先進行輪替處理
            if self._current_token is not None:
                self._archive_current_token()

            # 生成新 Token
            token = secrets.token_hex(self._token_length)
            token_id = self._generate_token_id()
            expires_at = self._calculate_expiry()

            info = TokenInfo(
                token_id=token_id,
                created_at=utc_now(),
                expires_at=expires_at,
                is_active=True,
                rotation_count=self._rotation_count,
            )

            self._current_token = token
            self._current_info = info

            logger.info(
                "Token generated",
                extra={
                    "token_id": token_id,
                    "expires_at": expires_at.isoformat() if expires_at else None,
                },
            )

            return token, info

    def _archive_current_token(self) -> None:
        """將當前 Token 歸檔到寬限期列表"""
        if self._current_token is None or self._current_info is None:
            return

        # 設定寬限期過期時間
        grace_expiry = utc_now() + timedelta(seconds=self._grace_period_seconds)
        self._current_info.expires_at = grace_expiry
        self._current_info.is_active = False

        # 使用 Token hash 作為 key 以避免存儲原始 Token
        token_hash = self._hash_token(self._current_token)
        self._previous_tokens[token_hash] = self._current_info

        # 清理過期的舊 Token
        self._cleanup_expired_tokens()

    def _cleanup_expired_tokens(self) -> None:
        """清理過期的舊 Token"""
        now = utc_now()
        expired_hashes = [
            h for h, info in self._previous_tokens.items()
            if info.expires_at and info.expires_at < now
        ]
        for h in expired_hashes:
            del self._previous_tokens[h]
            logger.debug("Expired token removed from grace period list")

    def rotate_token(self, reason: str = "scheduled") -> tuple[str, TokenInfo]:
        """
        輪替 Token

        保留舊 Token 在寬限期內有效，同時生成新 Token。

        Args:
            reason: 輪替原因

        Returns:
            tuple: (new_token, new_token_info)
        """
        with self._lock:
            old_token_id = self._current_info.token_id if self._current_info else None

            # 增加輪替計數
            self._rotation_count += 1

            # 歸檔舊 Token
            self._archive_current_token()

            # 生成新 Token（不再透過 generate_token 以避免重複獲取鎖）
            token = secrets.token_hex(self._token_length)
            token_id = self._generate_token_id()
            expires_at = self._calculate_expiry()

            new_info = TokenInfo(
                token_id=token_id,
                created_at=utc_now(),
                expires_at=expires_at,
                is_active=True,
                rotation_count=self._rotation_count,
            )

            self._current_token = token
            self._current_info = new_info

            # 記錄輪替事件
            event = TokenRotationEvent(
                old_token_id=old_token_id,
                new_token_id=new_info.token_id,
                reason=reason,
            )
            self._rotation_history.append(event)

            # 限制歷史記錄數量
            if len(self._rotation_history) > self._max_rotation_history:
                self._rotation_history = self._rotation_history[-self._max_rotation_history:]

            logger.info(
                "Token rotated",
                extra={
                    "old_token_id": old_token_id,
                    "new_token_id": new_info.token_id,
                    "reason": reason,
                    "rotation_count": self._rotation_count,
                },
            )

            # 通知訂閱者
            for callback in self._rotation_callbacks:
                try:
                    callback(token, new_info)
                except Exception as e:
                    logger.error(
                        "Token rotation callback error",
                        extra={"error": str(e)},
                    )

            return token, new_info

    def verify_token(self, token: str) -> bool:
        """
        驗證 Token

        驗證順序：
        1. 當前活躍 Token
        2. 寬限期內的舊 Token

        Args:
            token: 要驗證的 Token

        Returns:
            bool: Token 是否有效
        """
        if not token:
            return False

        with self._lock:
            # 檢查當前 Token
            if self._current_token is not None:
                if hmac.compare_digest(token, self._current_token):
                    if self._current_info and not self._current_info.is_expired():
                        return True
                    else:
                        logger.warning("Current token expired")
                        return False

            # 檢查寬限期內的舊 Token
            token_hash = self._hash_token(token)
            if token_hash in self._previous_tokens:
                info = self._previous_tokens[token_hash]
                if not info.is_expired():
                    logger.debug(
                        "Token verified via grace period",
                        extra={"token_id": info.token_id},
                    )
                    return True

            return False

    def get_current_token(self) -> Optional[str]:
        """
        取得當前 Token

        Returns:
            str: 當前 Token，如果沒有則返回 None
        """
        with self._lock:
            return self._current_token

    def get_token_info(self) -> Optional[TokenInfo]:
        """
        取得當前 Token 資訊

        Returns:
            TokenInfo: Token 資訊，如果沒有則返回 None
        """
        with self._lock:
            return self._current_info

    def get_rotation_history(self) -> List[TokenRotationEvent]:
        """
        取得輪替歷史

        Returns:
            List[TokenRotationEvent]: 輪替事件列表
        """
        with self._lock:
            return list(self._rotation_history)

    def is_rotation_needed(self, threshold_hours: float = 1.0) -> bool:
        """
        檢查是否需要輪替

        Args:
            threshold_hours: 剩餘有效時間閾值（小時）

        Returns:
            bool: 是否需要輪替
        """
        with self._lock:
            if self._current_info is None:
                return True

            if self._current_info.is_expired():
                return True

            time_left = self._current_info.time_until_expiry()
            if time_left is None:
                return False

            return time_left < timedelta(hours=threshold_hours)

    def on_token_rotated(self, callback: TokenRotationCallback) -> None:
        """
        訂閱 Token 輪替事件

        Args:
            callback: 輪替時呼叫的回調函式 (new_token, token_info) -> None
        """
        with self._lock:
            self._rotation_callbacks.append(callback)

    def remove_rotation_callback(self, callback: TokenRotationCallback) -> bool:
        """
        移除輪替事件訂閱

        Args:
            callback: 要移除的回調函式

        Returns:
            bool: 是否成功移除
        """
        with self._lock:
            try:
                self._rotation_callbacks.remove(callback)
                return True
            except ValueError:
                return False

    def invalidate_token(self) -> None:
        """
        使當前 Token 失效

        用於安全事件發生時立即廢除所有 Token。
        """
        with self._lock:
            self._current_token = None
            self._current_info = None
            self._previous_tokens.clear()

            logger.warning("All tokens invalidated")

    def get_status(self) -> dict:
        """
        取得 Token 管理器狀態

        Returns:
            dict: 狀態資訊
        """
        with self._lock:
            return {
                "has_token": self._current_token is not None,
                "token_info": self._current_info.to_dict() if self._current_info else None,
                "grace_period_tokens": len(self._previous_tokens),
                "rotation_count": self._rotation_count,
                "rotation_history_count": len(self._rotation_history),
            }


# 全域 Token 管理器實例（用於 Edge 環境）
_edge_token_manager: Optional[TokenManager] = None
_manager_lock = threading.Lock()


def get_edge_token_manager() -> TokenManager:
    """
    取得 Edge 環境的全域 Token 管理器

    Returns:
        TokenManager: Token 管理器實例
    """
    global _edge_token_manager
    with _manager_lock:
        if _edge_token_manager is None:
            _edge_token_manager = TokenManager(
                token_length=32,
                token_expiry_hours=24,  # 24 小時過期
                grace_period_seconds=120,  # 2 分鐘寬限期
            )
        return _edge_token_manager


def reset_edge_token_manager() -> None:
    """
    重置 Edge 環境的全域 Token 管理器

    主要用於測試目的。
    """
    global _edge_token_manager
    with _manager_lock:
        _edge_token_manager = None
