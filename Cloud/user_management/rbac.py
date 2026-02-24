"""
Cloud User Management - RBAC 授權工具

定義角色權限矩陣與授權裝飾器，供 Cloud API 路由使用。
"""

import logging
from functools import wraps
from typing import Set

from flask import request, jsonify

from Cloud.api.auth import CloudAuthService
from Cloud.user_management.models import ROLE_LEVEL

logger = logging.getLogger(__name__)

# 全域 auth service 參考（由 init_rbac 設定）
_auth_service = None


# 角色允許的操作（action → 最低所需角色）
PERMISSION_MAP: dict = {
    # 用戶相關
    "user.read": "viewer",
    "user.update_self": "viewer",
    "user.list": "auditor",
    "user.update_role": "admin",
    "user.deactivate": "admin",
    # 信任評分
    "trust.read": "viewer",
    "trust.update": "admin",
    # Edge 身份連結
    "edge.link": "operator",
    "edge.unlink": "operator",
    "edge.list": "viewer",
    # 指令操作
    "command.read": "viewer",
    "command.execute": "operator",
    "command.approve": "admin",
    # 審計
    "audit.read": "auditor",
}


def init_rbac(auth_service: CloudAuthService) -> None:
    """初始化 RBAC 模組

    Args:
        auth_service: 已設定的 CloudAuthService 實例
    """
    global _auth_service
    _auth_service = auth_service


def has_permission(role: str, action: str) -> bool:
    """檢查角色是否具備執行指定操作的權限

    Args:
        role: 用戶角色名稱
        action: 操作名稱（見 PERMISSION_MAP）

    Returns:
        True 若角色層級 >= 所需最低角色層級
    """
    required_role = PERMISSION_MAP.get(action)
    if required_role is None:
        logger.warning("Unknown action '%s' in RBAC check", action)
        return False
    user_level = ROLE_LEVEL.get(role, 0)
    required_level = ROLE_LEVEL.get(required_role, 999)
    return user_level >= required_level


def get_allowed_actions(role: str) -> Set[str]:
    """回傳指定角色所有允許的操作清單

    Args:
        role: 用戶角色名稱

    Returns:
        允許的操作名稱集合
    """
    return {action for action in PERMISSION_MAP if has_permission(role, action)}


def require_role(min_role: str):
    """Flask 路由裝飾器：要求 JWT 中的角色至少達到指定層級

    使用範例：
        @require_role("admin")
        def admin_only_route():
            ...

    Args:
        min_role: 最低所需角色名稱（viewer/operator/auditor/admin）
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if _auth_service is None:
                return jsonify({"error": "Service Unavailable", "message": "RBAC not initialized"}), 503

            auth_header = request.headers.get("Authorization", "")
            if not auth_header.startswith("Bearer "):
                return jsonify({"error": "Unauthorized", "message": "Missing or invalid token"}), 401

            token = auth_header[7:]
            payload = _auth_service.verify_token(token)
            if not payload:
                return jsonify({"error": "Unauthorized", "message": "Invalid or expired token"}), 401

            role = payload.get("role", "viewer")
            user_level = ROLE_LEVEL.get(role, 0)
            required_level = ROLE_LEVEL.get(min_role, 999)

            if user_level < required_level:
                logger.warning(
                    "Access denied: user_id=%s role=%s required=%s",
                    payload.get("user_id"), role, min_role
                )
                return jsonify({"error": "Forbidden", "message": f"Requires '{min_role}' role or higher"}), 403

            # 將 payload 注入 request context
            request.token_payload = payload
            request.current_role = role
            request.current_user_id = payload.get("user_id")

            return f(*args, **kwargs)
        return wrapper
    return decorator
