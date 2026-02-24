"""
Cloud User Management - REST API

提供用戶管理的 HTTP 端點，含 RBAC 授權保護。

端點清單：
  POST   /api/cloud/users              建立用戶（admin）
  GET    /api/cloud/users              列出用戶（auditor+）
  GET    /api/cloud/users/<user_id>    取得用戶（viewer+，非 admin 只能看自己）
  PUT    /api/cloud/users/<user_id>/role         更新角色（admin）
  POST   /api/cloud/users/<user_id>/deactivate   停用用戶（admin）
  POST   /api/cloud/users/<user_id>/trust        調整信任評分（admin）
  POST   /api/cloud/users/<user_id>/edges        連結 Edge 身份（operator+）
  DELETE /api/cloud/users/<user_id>/edges/<eid>  解除 Edge 連結（operator+）
  POST   /api/cloud/users/<user_id>/token        產生 JWT Token（admin）
  GET    /api/cloud/users/me                     取得自己的資訊（viewer+）
"""

import logging
from typing import Optional

from flask import Blueprint, jsonify, request

from Cloud.user_management.rbac import require_role, init_rbac
from Cloud.user_management.service import (
    CloudUserService,
    UserNotFoundError,
    UserAlreadyExistsError,
    InvalidRoleError,
)

logger = logging.getLogger(__name__)

# Flask Blueprint
user_mgmt_bp = Blueprint("user_management", __name__, url_prefix="/api/cloud/users")

# 服務實例（由 init_user_management 設定）
_service: Optional[CloudUserService] = None


def init_user_management(service: CloudUserService, auth_service) -> None:
    """初始化用戶管理模組

    Args:
        service: CloudUserService 實例
        auth_service: CloudAuthService 實例（供 RBAC 裝飾器使用）
    """
    global _service
    _service = service
    init_rbac(auth_service)
    logger.info("User management API initialized")


def _get_service() -> CloudUserService:
    """取得服務實例，未初始化則拋出錯誤"""
    if _service is None:
        raise RuntimeError("User management service not initialized")
    return _service


# ------------------------------------------------------------------
# 路由
# ------------------------------------------------------------------

@user_mgmt_bp.route("/me", methods=["GET"])
@require_role("viewer")
def get_me():
    """取得當前登入用戶的資訊

    Response 200:
        { "user": { ... } }
    """
    user_id = request.current_user_id
    try:
        user = _get_service().get_user(user_id)
        return jsonify({"user": user.to_dict()}), 200
    except UserNotFoundError:
        return jsonify({"error": "Not Found", "message": "User not found"}), 404
    except Exception:
        logger.exception("Failed to get current user")
        return jsonify({"error": "Internal Server Error"}), 500


@user_mgmt_bp.route("", methods=["POST"])
@require_role("admin")
def create_user():
    """建立新用戶（admin 限定）

    Request Body:
        {
            "username": "string",
            "email": "string",
            "role": "operator",        // 可選
            "trust_score": 50          // 可選
        }

    Response 201:
        { "user": { ... } }
    """
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    email = data.get("email", "").strip()
    role = data.get("role", "operator")
    trust_score = data.get("trust_score", 50)

    if not username or not email:
        return jsonify({"error": "Bad Request", "message": "username and email are required"}), 400

    try:
        user = _get_service().create_user(
            username=username,
            email=email,
            role=role,
            trust_score=int(trust_score),
        )
        return jsonify({"user": user.to_dict()}), 201
    except UserAlreadyExistsError:
        # Do not expose internal exception details to the client
        return jsonify({"error": "Conflict", "message": "User already exists"}), 409
    except (InvalidRoleError, ValueError) as e:
        return jsonify({"error": "Bad Request", "message": str(e)}), 400
    except Exception:
        logger.exception("Failed to create user")
        return jsonify({"error": "Internal Server Error"}), 500


@user_mgmt_bp.route("", methods=["GET"])
@require_role("auditor")
def list_users():
    """列出所有用戶（auditor+ 限定）

    Query Parameters:
        active_only: true/false（預設 false）

    Response 200:
        { "users": [...], "total": int }
    """
    active_only = request.args.get("active_only", "false").lower() == "true"
    try:
        users = _get_service().list_users(active_only=active_only)
        return jsonify({"users": [u.to_dict() for u in users], "total": len(users)}), 200
    except Exception:
        logger.exception("Failed to list users")
        return jsonify({"error": "Internal Server Error"}), 500


@user_mgmt_bp.route("/<user_id>", methods=["GET"])
@require_role("viewer")
def get_user(user_id: str):
    """取得用戶資訊

    非 admin 用戶只能查詢自己的資訊。

    Response 200:
        { "user": { ... } }
    """
    # 非 admin 只能查自己
    if request.current_role != "admin" and request.current_user_id != user_id:
        return jsonify({"error": "Forbidden", "message": "Cannot view other users"}), 403

    try:
        user = _get_service().get_user(user_id)
        return jsonify({"user": user.to_dict()}), 200
    except UserNotFoundError:
        return jsonify({"error": "Not Found", "message": "User not found"}), 404
    except Exception:
        logger.exception("Failed to get user %s", user_id)
        return jsonify({"error": "Internal Server Error"}), 500


@user_mgmt_bp.route("/<user_id>/role", methods=["PUT"])
@require_role("admin")
def update_role(user_id: str):
    """更新用戶角色（admin 限定）

    Request Body:
        { "role": "operator" }

    Response 200:
        { "user": { ... } }
    """
    data = request.get_json(silent=True) or {}
    new_role = data.get("role", "").strip()
    if not new_role:
        return jsonify({"error": "Bad Request", "message": "role is required"}), 400

    try:
        user = _get_service().update_role(user_id, new_role)
        return jsonify({"user": user.to_dict()}), 200
    except UserNotFoundError:
        return jsonify({"error": "Not Found", "message": "User not found"}), 404
    except InvalidRoleError as e:
        return jsonify({"error": "Bad Request", "message": str(e)}), 400
    except Exception:
        logger.exception("Failed to update role for %s", user_id)
        return jsonify({"error": "Internal Server Error"}), 500


@user_mgmt_bp.route("/<user_id>/deactivate", methods=["POST"])
@require_role("admin")
def deactivate_user(user_id: str):
    """停用用戶（admin 限定）

    Response 200:
        { "user": { ... }, "message": "User deactivated" }
    """
    try:
        user = _get_service().deactivate_user(user_id)
        return jsonify({"user": user.to_dict(), "message": "User deactivated"}), 200
    except UserNotFoundError:
        return jsonify({"error": "Not Found", "message": "User not found"}), 404
    except Exception:
        logger.exception("Failed to deactivate user %s", user_id)
        return jsonify({"error": "Internal Server Error"}), 500


@user_mgmt_bp.route("/<user_id>/trust", methods=["POST"])
@require_role("admin")
def adjust_trust(user_id: str):
    """調整信任評分（admin 限定）

    Request Body:
        { "delta": 10 }   // 正數加分，負數扣分

    Response 200:
        { "user": { ... }, "actual_delta": 10 }
    """
    data = request.get_json(silent=True) or {}
    delta = data.get("delta")
    if delta is None or not isinstance(delta, (int, float)):
        return jsonify({"error": "Bad Request", "message": "delta (integer) is required"}), 400

    try:
        user, actual_delta = _get_service().adjust_trust_score(user_id, int(delta))
        return jsonify({"user": user.to_dict(), "actual_delta": actual_delta}), 200
    except UserNotFoundError:
        return jsonify({"error": "Not Found", "message": "User not found"}), 404
    except Exception:
        logger.exception("Failed to adjust trust for %s", user_id)
        return jsonify({"error": "Internal Server Error"}), 500


@user_mgmt_bp.route("/<user_id>/edges", methods=["POST"])
@require_role("operator")
def link_edge(user_id: str):
    """連結 Edge 身份（operator+ 且只能操作自己，admin 可操作所有人）

    Request Body:
        {
            "edge_id": "edge-001",
            "edge_user_id": "local-user-456"
        }

    Response 200:
        { "user": { ... } }
    """
    if request.current_role != "admin" and request.current_user_id != user_id:
        return jsonify({"error": "Forbidden", "message": "Cannot link edge for other users"}), 403

    data = request.get_json(silent=True) or {}
    edge_id = data.get("edge_id", "").strip()
    edge_user_id = data.get("edge_user_id", "").strip()
    if not edge_id or not edge_user_id:
        return jsonify({"error": "Bad Request", "message": "edge_id and edge_user_id are required"}), 400

    try:
        user = _get_service().link_edge_identity(user_id, edge_id, edge_user_id)
        return jsonify({"user": user.to_dict()}), 200
    except UserNotFoundError:
        return jsonify({"error": "Not Found", "message": "User not found"}), 404
    except Exception:
        logger.exception("Failed to link edge for %s", user_id)
        return jsonify({"error": "Internal Server Error"}), 500


@user_mgmt_bp.route("/<user_id>/edges/<edge_id>", methods=["DELETE"])
@require_role("operator")
def unlink_edge(user_id: str, edge_id: str):
    """解除 Edge 連結（operator+ 且只能操作自己，admin 可操作所有人）

    Response 200:
        { "user": { ... }, "message": "Edge identity unlinked" }
    """
    if request.current_role != "admin" and request.current_user_id != user_id:
        return jsonify({"error": "Forbidden", "message": "Cannot unlink edge for other users"}), 403

    try:
        user = _get_service().unlink_edge_identity(user_id, edge_id)
        return jsonify({"user": user.to_dict(), "message": "Edge identity unlinked"}), 200
    except UserNotFoundError:
        return jsonify({"error": "Not Found", "message": "User not found"}), 404
    except ValueError as e:
        return jsonify({"error": "Not Found", "message": str(e)}), 404
    except Exception:
        logger.exception("Failed to unlink edge for %s", user_id)
        return jsonify({"error": "Internal Server Error"}), 500


@user_mgmt_bp.route("/<user_id>/token", methods=["POST"])
@require_role("admin")
def generate_token(user_id: str):
    """為用戶產生雲端 JWT Token（admin 限定）

    Request Body:
        { "expires_in": 86400 }   // 可選，預設 24 小時

    Response 200:
        { "token": "eyJ...", "expires_in": 86400 }
    """
    data = request.get_json(silent=True) or {}
    expires_in = min(int(data.get("expires_in", 86400)), 7 * 24 * 3600)

    try:
        token = _get_service().generate_token(user_id, expires_in=expires_in)
        return jsonify({"token": token, "expires_in": expires_in}), 200
    except UserNotFoundError:
        return jsonify({"error": "Not Found", "message": "User not found or deactivated"}), 404
    except Exception:
        logger.exception("Failed to generate token for %s", user_id)
        return jsonify({"error": "Internal Server Error"}), 500
