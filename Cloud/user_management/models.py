"""
Cloud User Management - 資料模型

定義雲端用戶的資料結構，包含角色、信任評分與 Edge 身份連結。
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional


# 有效角色清單（依 proposal.md RBAC 定義）
VALID_ROLES = {"viewer", "operator", "admin", "auditor"}

# 角色層級（數字越高、權限越大）
ROLE_LEVEL = {
    "viewer": 1,
    "operator": 2,
    "auditor": 3,
    "admin": 4,
}

# 信任評分範圍
TRUST_SCORE_MIN = 0
TRUST_SCORE_MAX = 100
TRUST_SCORE_DEFAULT = 50


@dataclass
class EdgeIdentity:
    """Edge 身份連結資料

    記錄雲端用戶在特定 Edge 裝置上的對應身份。
    """
    edge_id: str
    edge_user_id: str
    linked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict:
        """轉換為字典格式"""
        return {
            "edge_id": self.edge_id,
            "edge_user_id": self.edge_user_id,
            "linked_at": self.linked_at.isoformat(),
        }


@dataclass
class CloudUser:
    """雲端用戶資料模型

    包含用戶基本資訊、RBAC 角色、信任評分與 Edge 身份連結清單。

    Attributes:
        user_id: 雲端唯一用戶 ID
        username: 用戶名稱
        email: 電子郵件
        role: RBAC 角色（viewer/operator/admin/auditor）
        trust_score: 信任評分 (0–100)
        created_at: 建立時間
        updated_at: 最後更新時間
        is_active: 帳戶是否啟用
        edge_identities: 已連結的 Edge 身份清單
    """
    user_id: str
    username: str
    email: str
    role: str = "operator"
    trust_score: int = TRUST_SCORE_DEFAULT
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True
    edge_identities: List[EdgeIdentity] = field(default_factory=list)

    def __post_init__(self):
        """驗證欄位值"""
        if self.role not in VALID_ROLES:
            raise ValueError(f"Invalid role '{self.role}'. Must be one of: {sorted(VALID_ROLES)}")
        if not (TRUST_SCORE_MIN <= self.trust_score <= TRUST_SCORE_MAX):
            raise ValueError(
                f"trust_score must be between {TRUST_SCORE_MIN} and {TRUST_SCORE_MAX}"
            )

    def to_dict(self) -> Dict:
        """轉換為字典格式（適合 API 回應）"""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "trust_score": self.trust_score,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "edge_identities": [e.to_dict() for e in self.edge_identities],
        }

    def get_role_level(self) -> int:
        """回傳角色層級數值"""
        return ROLE_LEVEL.get(self.role, 0)

    def has_role(self, required_role: str) -> bool:
        """檢查用戶是否擁有至少指定角色的權限

        Args:
            required_role: 所需的最低角色

        Returns:
            True 若用戶角色層級 >= 所需角色層級
        """
        return self.get_role_level() >= ROLE_LEVEL.get(required_role, 0)

    def get_linked_edge(self, edge_id: str) -> Optional[EdgeIdentity]:
        """取得特定 Edge 的身份連結

        Args:
            edge_id: Edge 裝置 ID

        Returns:
            EdgeIdentity 或 None（若未連結）
        """
        for identity in self.edge_identities:
            if identity.edge_id == edge_id:
                return identity
        return None

    def __repr__(self) -> str:
        return f"<CloudUser {self.username} role={self.role} trust={self.trust_score}>"
