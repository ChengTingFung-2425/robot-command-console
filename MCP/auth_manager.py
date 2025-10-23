"""
MCP 認證授權管理器
負責身份驗證、RBAC/ABAC 與權限審計
"""

import hashlib
import hmac
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import jwt

from .config import MCPConfig


logger = logging.getLogger(__name__)


class AuthManager:
    """認證授權管理器"""
    
    def __init__(self):
        """初始化管理器"""
        self.users: Dict[str, Dict[str, Any]] = {}
        self.roles: Dict[str, Dict[str, Any]] = {}
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
    
    async def verify_token(self, token: str) -> bool:
        """驗證 Token"""
        try:
            payload = jwt.decode(
                token,
                MCPConfig.JWT_SECRET,
                algorithms=[MCPConfig.JWT_ALGORITHM]
            )
            
            # 檢查過期時間
            exp = payload.get("exp")
            if exp and datetime.fromtimestamp(exp) < datetime.utcnow():
                logger.warning("Token 已過期")
                return False
            
            return True
            
        except jwt.InvalidTokenError as e:
            logger.warning(f"Token 驗證失敗: {e}")
            return False
        except Exception as e:
            logger.error(f"Token 驗證錯誤: {e}")
            return False
    
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
        
        exp = datetime.utcnow() + timedelta(hours=expires_in_hours)
        
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
            "created_at": datetime.utcnow()
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
        """雜湊密碼"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        """驗證密碼"""
        return self._hash_password(password) == password_hash
