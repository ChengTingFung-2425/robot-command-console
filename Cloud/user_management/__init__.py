"""
User Management Module - 用戶管理模組

包含雲端用戶的 CRUD、RBAC 授權、信任評分與 Edge 身份連結整合。

快速使用：
    from Cloud.user_management import (
        CloudUser, CloudUserService, user_mgmt_bp, init_user_management
    )
"""

from Cloud.user_management.models import (
    CloudUser,
    EdgeIdentity,
    VALID_ROLES,
    ROLE_LEVEL,
    TRUST_SCORE_MIN,
    TRUST_SCORE_MAX,
    TRUST_SCORE_DEFAULT,
)
from Cloud.user_management.service import (
    CloudUserService,
    UserNotFoundError,
    UserAlreadyExistsError,
    InvalidRoleError,
)
from Cloud.user_management.rbac import (
    has_permission,
    get_allowed_actions,
    require_role,
    init_rbac,
    PERMISSION_MAP,
)
from Cloud.user_management.api import user_mgmt_bp, init_user_management

__all__ = [
    # Models
    "CloudUser",
    "EdgeIdentity",
    "VALID_ROLES",
    "ROLE_LEVEL",
    "TRUST_SCORE_MIN",
    "TRUST_SCORE_MAX",
    "TRUST_SCORE_DEFAULT",
    # Service
    "CloudUserService",
    "UserNotFoundError",
    "UserAlreadyExistsError",
    "InvalidRoleError",
    # RBAC
    "has_permission",
    "get_allowed_actions",
    "require_role",
    "init_rbac",
    "PERMISSION_MAP",
    # API
    "user_mgmt_bp",
    "init_user_management",
]
