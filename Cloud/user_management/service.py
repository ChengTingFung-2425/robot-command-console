"""
Cloud User Management - 用戶服務層

提供雲端用戶的 CRUD、信任評分調整與 Edge 身份連結管理。
使用記憶體字典儲存（生產環境可替換為 SQLAlchemy 後端）。
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from Cloud.api.auth import CloudAuthService
from Cloud.user_management.models import (
    CloudUser,
    EdgeIdentity,
    TRUST_SCORE_MIN,
    TRUST_SCORE_MAX,
    VALID_ROLES,
)

logger = logging.getLogger(__name__)


class UserNotFoundError(Exception):
    """用戶不存在"""


class UserAlreadyExistsError(Exception):
    """用戶已存在"""


class InvalidRoleError(Exception):
    """無效角色"""


class CloudUserService:
    """雲端用戶管理服務

    職責：
    - 用戶的建立、讀取、更新、停用（CRUD）
    - RBAC 角色指派與驗證
    - 信任評分的讀取與調整
    - Edge 身份連結（link / unlink）
    - 產生雲端 JWT Token
    """

    def __init__(self, auth_service: CloudAuthService):
        """初始化用戶服務

        Args:
            auth_service: 已設定的 CloudAuthService，用於產生 JWT
        """
        self._auth = auth_service
        # user_id -> CloudUser（記憶體儲存；可替換為 DB Session）
        self._users: Dict[str, CloudUser] = {}

    # ------------------------------------------------------------------
    # 用戶 CRUD
    # ------------------------------------------------------------------

    def create_user(
        self,
        username: str,
        email: str,
        role: str = "operator",
        trust_score: int = 50,
        user_id: Optional[str] = None,
    ) -> CloudUser:
        """建立新的雲端用戶

        Args:
            username: 用戶名稱（唯一）
            email: 電子郵件
            role: RBAC 角色（預設 operator）
            trust_score: 初始信任評分（預設 50）
            user_id: 指定 ID（省略則自動產生 UUID）

        Returns:
            建立的 CloudUser 物件

        Raises:
            UserAlreadyExistsError: username 已存在
            InvalidRoleError: 角色名稱無效
            ValueError: 信任評分超出範圍
        """
        if role not in VALID_ROLES:
            raise InvalidRoleError(f"Invalid role '{role}'. Must be one of: {sorted(VALID_ROLES)}")

        for existing in self._users.values():
            if existing.username == username:
                raise UserAlreadyExistsError(f"Username '{username}' already exists")

        uid = user_id or str(uuid.uuid4())
        if uid in self._users:
            raise UserAlreadyExistsError(f"User ID '{uid}' already exists")
        user = CloudUser(
            user_id=uid,
            username=username,
            email=email,
            role=role,
            trust_score=trust_score,
        )
        self._users[uid] = user
        logger.info("Created cloud user: %s (role=%s)", username, role)
        return user

    def get_user(self, user_id: str) -> CloudUser:
        """依 user_id 取得用戶

        Raises:
            UserNotFoundError: 用戶不存在
        """
        user = self._users.get(user_id)
        if user is None:
            raise UserNotFoundError(f"User '{user_id}' not found")
        return user

    def get_user_by_username(self, username: str) -> Optional[CloudUser]:
        """依 username 查找用戶（找不到回傳 None）"""
        for user in self._users.values():
            if user.username == username:
                return user
        return None

    def list_users(self, active_only: bool = False) -> List[CloudUser]:
        """列出所有用戶

        Args:
            active_only: True 則只回傳 is_active=True 的用戶

        Returns:
            CloudUser 清單（按建立時間排序）
        """
        users = list(self._users.values())
        if active_only:
            users = [u for u in users if u.is_active]
        return sorted(users, key=lambda u: u.created_at)

    def update_role(self, user_id: str, new_role: str) -> CloudUser:
        """更新用戶角色（需 admin 權限，由路由層控制）

        Args:
            user_id: 目標用戶 ID
            new_role: 新角色名稱

        Returns:
            更新後的 CloudUser

        Raises:
            UserNotFoundError: 用戶不存在
            InvalidRoleError: 角色無效
        """
        if new_role not in VALID_ROLES:
            raise InvalidRoleError(f"Invalid role '{new_role}'")
        user = self.get_user(user_id)
        old_role = user.role
        user.role = new_role
        user.updated_at = datetime.now(timezone.utc)
        logger.info("Role updated: %s %s -> %s", user.username, old_role, new_role)
        return user

    def deactivate_user(self, user_id: str) -> CloudUser:
        """停用用戶（不刪除記錄，保留審計軌跡）

        Raises:
            UserNotFoundError: 用戶不存在
        """
        user = self.get_user(user_id)
        user.is_active = False
        user.updated_at = datetime.now(timezone.utc)
        logger.info("Deactivated cloud user: %s", user.username)
        return user

    # ------------------------------------------------------------------
    # 信任評分
    # ------------------------------------------------------------------

    def adjust_trust_score(self, user_id: str, delta: int) -> Tuple[CloudUser, int]:
        """調整信任評分

        評分自動箝制在 [0, 100] 範圍內。

        Args:
            user_id: 目標用戶 ID
            delta: 變化量（正數 = 加分，負數 = 扣分）

        Returns:
            (更新後的 CloudUser, 實際變化量)

        Raises:
            UserNotFoundError: 用戶不存在
        """
        user = self.get_user(user_id)
        old_score = user.trust_score
        new_score = max(TRUST_SCORE_MIN, min(TRUST_SCORE_MAX, old_score + delta))
        user.trust_score = new_score
        user.updated_at = datetime.now(timezone.utc)
        actual_delta = new_score - old_score
        logger.info(
            "Trust score adjusted: %s %d -> %d (delta=%+d)",
            user.username, old_score, new_score, actual_delta,
        )
        return user, actual_delta

    # ------------------------------------------------------------------
    # Edge 身份連結
    # ------------------------------------------------------------------

    def link_edge_identity(
        self,
        user_id: str,
        edge_id: str,
        edge_user_id: str,
    ) -> CloudUser:
        """連結 Edge 身份到雲端用戶

        若同一 edge_id 已存在連結，則更新 edge_user_id。

        Args:
            user_id: 雲端用戶 ID
            edge_id: Edge 裝置 ID
            edge_user_id: 在 Edge 上的對應用戶 ID

        Returns:
            更新後的 CloudUser

        Raises:
            UserNotFoundError: 用戶不存在
        """
        user = self.get_user(user_id)
        existing = user.get_linked_edge(edge_id)
        if existing:
            existing.edge_user_id = edge_user_id
            existing.linked_at = datetime.now(timezone.utc)
            logger.info("Updated edge identity: user=%s edge=%s", user.username, edge_id)
        else:
            user.edge_identities.append(EdgeIdentity(edge_id=edge_id, edge_user_id=edge_user_id))
            logger.info("Linked edge identity: user=%s edge=%s", user.username, edge_id)
        user.updated_at = datetime.now(timezone.utc)
        return user

    def unlink_edge_identity(self, user_id: str, edge_id: str) -> CloudUser:
        """解除 Edge 身份連結

        Args:
            user_id: 雲端用戶 ID
            edge_id: 要解除的 Edge 裝置 ID

        Returns:
            更新後的 CloudUser

        Raises:
            UserNotFoundError: 用戶不存在
            ValueError: 該 edge_id 未連結
        """
        user = self.get_user(user_id)
        before = len(user.edge_identities)
        user.edge_identities = [e for e in user.edge_identities if e.edge_id != edge_id]
        if len(user.edge_identities) == before:
            raise ValueError(f"Edge identity '{edge_id}' not linked to user '{user_id}'")
        user.updated_at = datetime.now(timezone.utc)
        logger.info("Unlinked edge identity: user=%s edge=%s", user.username, edge_id)
        return user

    # ------------------------------------------------------------------
    # Token 產生
    # ------------------------------------------------------------------

    def generate_token(self, user_id: str, expires_in: int = 86400) -> str:
        """為用戶產生雲端 JWT Token

        Args:
            user_id: 雲端用戶 ID
            expires_in: Token 有效秒數（預設 24 小時）

        Returns:
            JWT Token 字串

        Raises:
            UserNotFoundError: 用戶不存在或已停用
        """
        user = self.get_user(user_id)
        if not user.is_active:
            raise UserNotFoundError(f"User '{user_id}' is deactivated")
        return self._auth.generate_token(
            user_id=user.user_id,
            username=user.username,
            role=user.role,
            expires_in=expires_in,
        )
