"""
雲服務認證 API

提供 JWT Token 驗證、用戶認證等功能
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

import jwt
from passlib.hash import bcrypt


logger = logging.getLogger(__name__)


class CloudAuthService:
    """雲服務認證服務"""

    def __init__(self, jwt_secret: str, jwt_algorithm: str = "HS256"):
        """
        初始化認證服務

        Args:
            jwt_secret: JWT 密鑰
            jwt_algorithm: JWT 演算法
        """
        self.jwt_secret = jwt_secret
        self.jwt_algorithm = jwt_algorithm

    def generate_token(
        self,
        user_id: str,
        username: str,
        role: str = "user",
        expires_in: int = 86400
    ) -> str:
        """
        生成 JWT Token

        Args:
            user_id: 用戶 ID
            username: 用戶名稱
            role: 用戶角色
            expires_in: 過期時間（秒），預設 24 小時

        Returns:
            JWT Token 字串
        """
        now = datetime.now(timezone.utc)
        payload = {
            "user_id": user_id,
            "username": username,
            "role": role,
            "iat": now,
            "exp": now + timedelta(seconds=expires_in)
        }

        token = jwt.encode(
            payload,
            self.jwt_secret,
            algorithm=self.jwt_algorithm
        )

        logger.info(f"Generated token for user: {username}")
        return token

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        驗證 JWT Token

        Args:
            token: JWT Token

        Returns:
            Token payload 或 None（驗證失敗）
        """
        try:
            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=[self.jwt_algorithm]
            )
            # PyJWT 已自動驗證 exp，無需手動檢查
            return payload

        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            return None

    def hash_password(self, password: str) -> str:
        """
        雜湊密碼

        Args:
            password: 明文密碼

        Returns:
            雜湊後的密碼
        """
        return bcrypt.hash(password)

    def verify_password(self, password: str, hashed: str) -> bool:
        """
        驗證密碼

        Args:
            password: 明文密碼
            hashed: 雜湊密碼

        Returns:
            是否匹配
        """
        try:
            return bcrypt.verify(password, hashed)
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False
