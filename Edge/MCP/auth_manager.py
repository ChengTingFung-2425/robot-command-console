"""
MCP 認證授權管理器
負責身份驗證、RBAC/ABAC 與權限審計
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import jwt
from passlib.hash import bcrypt

from .config import MCPConfig
from .utils import utc_now


logger = logging.getLogger(__name__)


class AuthManager:
    """認證授權管理器"""

    def __init__(self, logging_monitor=None):
        """初始化管理器"""
        self.users: Dict[str, Dict[str, Any]] = {}
        self.roles: Dict[str, Dict[str, Any]] = {}
        self.logging_monitor = logging_monitor
        self._init_default_roles()

    def _init_default_roles(self):
        """初始化預設角色"""
        self.roles = {
            "admin": {
                "permissions": ["*"]  # 所有權限
            },
            "operator": {
                "permissions": [
                    "robot.move",
                    "robot.stop",
                    "robot.status",
                    "command.view",
                    "command.create"
                ]
            },
            "viewer": {
                "permissions": [
                    "robot.status",
                    "command.view"
                ]
            }
        }

    async def verify_token(self, token: str, trace_id: Optional[str] = None) -> bool:
        """驗證 Token"""
        try:
            payload = jwt.decode(
                token,
                MCPConfig.JWT_SECRET,
                algorithms=[MCPConfig.JWT_ALGORITHM]
            )

            # 檢查過期時間
            exp = payload.get("exp")
            if exp and datetime.fromtimestamp(exp, tz=timezone.utc) < utc_now():
                logger.warning("Token 已過期")
                await self._log_audit_event(
                    trace_id or "unknown",
                    "token_expired",
                    {"user_id": payload.get("user_id")}
                )
                return False

            # 記錄成功驗證（僅在 DEBUG 模式）
            logger.debug(f"Token 驗證成功: user_id={payload.get('user_id')}")
            return True

        except jwt.InvalidTokenError as e:
            logger.warning(f"Token 驗證失敗: {e}")
            await self._log_audit_event(
                trace_id or "unknown",
                "token_invalid",
                {"error": str(e)}
            )
            return False
        except Exception as e:
            logger.error(f"Token 驗證錯誤: {e}")
            await self._log_audit_event(
                trace_id or "unknown",
                "token_error",
                {"error": str(e)}
            )
            return False

    async def decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        解碼 Token 並返回 payload

        Args:
            token: JWT token

        Returns:
            Token payload，如果無效則返回 None
        """
        try:
            payload = jwt.decode(
                token,
                MCPConfig.JWT_SECRET,
                algorithms=[MCPConfig.JWT_ALGORITHM]
            )

            # 檢查過期時間
            exp = payload.get("exp")
            if exp and datetime.fromtimestamp(exp, tz=timezone.utc) < utc_now():
                return None

            return payload

        except jwt.InvalidTokenError:
            return None
        except Exception as e:
            logger.error(f"Token 解碼錯誤: {e}")
            return None

    async def check_permission(
        self,
        user_id: str,
        action: str,
        resource: Optional[str] = None
    ) -> bool:
        """檢查權限"""
        # 取得使用者資訊
        user = self.users.get(user_id)
        if not user:
            logger.warning(f"使用者不存在: {user_id}")
            return False

        # 取得使用者角色
        role_name = user.get("role", "viewer")
        role = self.roles.get(role_name)
        if not role:
            logger.warning(f"角色不存在: {role_name}")
            return False

        # 檢查權限
        permissions = role.get("permissions", [])

        # 萬用權限
        if "*" in permissions:
            return True

        # 完全匹配
        if action in permissions:
            return True

        # 前綴匹配（例如 "robot.*" 匹配 "robot.move"）
        for perm in permissions:
            if perm.endswith(".*"):
                prefix = perm[:-2]
                if action.startswith(prefix + "."):
                    return True

        logger.warning(f"權限不足: user={user_id}, action={action}, role={role_name}")
        return False

    async def create_token(
        self,
        user_id: str,
        role: str = "viewer",
        expires_in_hours: Optional[int] = None
    ) -> str:
        """建立 Token"""
        if expires_in_hours is None:
            expires_in_hours = MCPConfig.JWT_EXPIRATION_HOURS

        exp = utc_now() + timedelta(hours=expires_in_hours)

        payload = {
            "user_id": user_id,
            "role": role,
            "exp": exp.timestamp()
        }

        token = jwt.encode(
            payload,
            MCPConfig.JWT_SECRET,
            algorithm=MCPConfig.JWT_ALGORITHM
        )

        return token

    async def register_user(
        self,
        user_id: str,
        username: str,
        password: str,
        role: str = "viewer"
    ) -> bool:
        """註冊使用者"""
        if user_id in self.users:
            logger.warning(f"使用者已存在: {user_id}")
            return False

        # 雜湊密碼
        password_hash = self._hash_password(password)

        self.users[user_id] = {
            "user_id": user_id,
            "username": username,
            "password_hash": password_hash,
            "role": role,
            "created_at": utc_now()
        }

        logger.info(f"使用者已註冊: {user_id}")
        return True

    async def authenticate_user(self, username: str, password: str) -> Optional[str]:
        """驗證使用者"""
        for user_id, user in self.users.items():
            if user["username"] == username:
                if self._verify_password(password, user["password_hash"]):
                    return user_id
        return None

    def _hash_password(self, password: str) -> str:
        """
        雜湊密碼（使用 bcrypt，自動產生隨機鹽值）

        bcrypt 限制密碼長度最多 72 bytes，超過會自動截斷
        """
        # bcrypt 限制密碼長度為 72 bytes
        password_bytes = password.encode('utf-8')[:72]
        return bcrypt.hash(password_bytes.decode('utf-8', errors='ignore'))

    def _verify_password(self, password: str, password_hash: str) -> bool:
        """
        驗證密碼（使用 bcrypt）

        需要與 _hash_password 使用相同的截斷邏輯
        """
        # bcrypt 限制密碼長度為 72 bytes
        password_bytes = password.encode('utf-8')[:72]
        return bcrypt.verify(password_bytes.decode('utf-8', errors='ignore'), password_hash)

    async def _log_audit_event(
        self,
        trace_id: str,
        action: str,
        context: Dict[str, Any]
    ):
        """記錄審計事件"""
        if not self.logging_monitor:
            return

        from .models import Event, EventSeverity, EventCategory

        event = Event(
            trace_id=trace_id,
            timestamp=utc_now(),
            severity=EventSeverity.INFO,
            category=EventCategory.AUDIT,
            message=f"Auth action: {action}",
            context=context
        )

        try:
            await self.logging_monitor.emit_event(event)
        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")
