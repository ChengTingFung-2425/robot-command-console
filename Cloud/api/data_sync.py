# imports
import json
import logging
import re
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
from typing import Any, Dict, List, Optional

from flask import Blueprint, jsonify, request

from .auth import CloudAuthService

logger = logging.getLogger(__name__)

# 僅允許安全的 user_id 字元（避免路徑遍歷等問題）
_SAFE_ID_PATTERN = re.compile(r'^[A-Za-z0-9_-]{1,64}$')

# Blueprint
data_sync_bp = Blueprint('data_sync', __name__, url_prefix='/api/cloud/data_sync')

# 認證服務實例（需在初始化時設定）
_auth_service: Optional[CloudAuthService] = None

# 安全路徑字元驗證（防止路徑穿越）
_SAFE_ID_PATTERN = re.compile(r'^[A-Za-z0-9._-]+$')

# 儲存路徑（需在初始化時設定）
_storage_path: Optional[Path] = None


def init_data_sync_api(jwt_secret: str, storage_path: str) -> None:
    """初始化資料同步 API

    Args:
        jwt_secret: JWT 密鑰
        storage_path: 儲存根目錄路徑
    """
    global _auth_service, _storage_path
    _auth_service = CloudAuthService(jwt_secret)
    _storage_path = Path(storage_path)
    _storage_path.mkdir(parents=True, exist_ok=True)
    logger.info(f"Data sync API initialized, storage: {_storage_path}")


def _require_auth(f):
    """JWT 認證裝飾器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if _auth_service is None:
            return jsonify({"success": False, "error": "Service not initialized"}), 503

        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"success": False, "error": "Unauthorized"}), 401

        token = auth_header[7:]
        payload = _auth_service.verify_token(token)
        if not payload:
            return jsonify({"success": False, "error": "Invalid or expired token"}), 401

        request.token_user_id = payload.get("user_id")
        return f(*args, **kwargs)
    return decorated


def _validate_user_id(user_id: str) -> bool:
    """驗證 user_id 格式是否安全

    Args:
        user_id: 要驗證的用戶 ID

    Returns:
        是否安全
    """
    return bool(_SAFE_ID_PATTERN.match(user_id))


def _get_settings_path(user_id: str) -> Path:
    """取得用戶設定檔案路徑

    Args:
        user_id: 用戶 ID

    Returns:
        設定檔案路徑
    """
    # 防禦性檢查：確保 user_id 為安全字元，避免路徑遍歷
    if not _validate_user_id(user_id):
        raise ValueError(f"Invalid user_id for settings path: {user_id!r}")

    settings_dir = _storage_path / "user_settings"
    settings_dir.mkdir(parents=True, exist_ok=True)
    return settings_dir / f"settings_{user_id}.json"


def _get_history_path(user_id: str) -> Path:
    """取得用戶指令歷史檔案路徑

    Args:
        user_id: 用戶 ID

    Returns:
        歷史檔案路徑
    """
    # 防禦性檢查：確保 user_id 為安全字元，避免路徑遍歷
    if not _validate_user_id(user_id):
        raise ValueError(f"Invalid user_id for history path: {user_id!r}")

    history_dir = _storage_path / "command_history"
    history_dir.mkdir(parents=True, exist_ok=True)
    return history_dir / f"history_{user_id}.json"


# ==================== 用戶設定同步端點 ====================

@data_sync_bp.route('/settings/<user_id>', methods=['POST'])
@_require_auth
def upload_settings(user_id: str):
    """上傳用戶設定到雲端（備份）

    Path Parameters:
        user_id: 用戶 ID

    Request Body:
        {
            "settings": { ... },
            "edge_id": "edge-001"
        }

    Response:
        {
            "success": true,
            "message": "Settings synced",
            "updated_at": "2026-01-01T00:00:00Z"
        }
    """
    if _storage_path is None:
        return jsonify({"success": False, "error": "Storage not initialized"}), 503

    if not _validate_user_id(user_id):
        return jsonify({"success": False, "error": "Invalid user_id"}), 400

    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return jsonify({"success": False, "error": "Invalid JSON body"}), 400

    settings = data.get('settings')
    if settings is None or not isinstance(settings, dict):
        return jsonify({"success": False, "error": "Missing or invalid 'settings' field"}), 400

    try:
        updated_at = datetime.now(timezone.utc).isoformat()
        payload: Dict[str, Any] = {
            'user_id': user_id,
            'settings': settings,
            'edge_id': data.get('edge_id'),
            'updated_at': updated_at
        }

        settings_path = _get_settings_path(user_id)
        with open(settings_path, 'w', encoding='utf-8') as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

        logger.info(f"Settings synced for user '{user_id}'")
        return jsonify({
            "success": True,
            "message": "Settings synced",
            "updated_at": updated_at
        })

    except Exception as e:
        logger.error(f"Failed to save settings for user '{user_id}': {e}")
        return jsonify({"success": False, "error": "Failed to save settings"}), 500


@data_sync_bp.route('/settings/<user_id>', methods=['GET'])
@_require_auth
def download_settings(user_id: str):
    """從雲端下載用戶設定（還原）

    Path Parameters:
        user_id: 用戶 ID

    Response:
        {
            "success": true,
            "data": {
                "user_id": "user-123",
                "settings": { ... },
                "edge_id": "edge-001",
                "updated_at": "2026-01-01T00:00:00Z"
            }
        }
    """
    if _storage_path is None:
        return jsonify({"success": False, "error": "Storage not initialized"}), 503

    if not _validate_user_id(user_id):
        return jsonify({"success": False, "error": "Invalid user_id"}), 400

    try:
        settings_path = _get_settings_path(user_id)
        # 防禦性檢查：確保路徑位於 _storage_path 根目錄之下
        root_path = _storage_path.resolve()
        resolved_settings_path = settings_path.resolve()
        try:
            resolved_settings_path.relative_to(root_path)
        except ValueError:
            return jsonify({"success": False, "error": "Invalid user_id"}), 400

        if not resolved_settings_path.exists():
            return jsonify({"success": False, "error": "Settings not found"}), 404

        with open(resolved_settings_path, 'r', encoding='utf-8') as f:
            payload = json.load(f)

        return jsonify({"success": True, "data": payload})

    except Exception as e:
        logger.error(f"Failed to load settings for user '{user_id}': {e}")
        return jsonify({"success": False, "error": "Failed to load settings"}), 500


# ==================== 指令歷史同步端點 ====================

@data_sync_bp.route('/history/<user_id>', methods=['POST'])
@_require_auth
def upload_history(user_id: str):
    """上傳指令執行歷史到雲端

    Path Parameters:
        user_id: 用戶 ID

    Request Body:
        {
            "records": [
                {
                    "command_id": "cmd-001",
                    "trace_id": "trace-001",
                    "robot_id": "robot-1",
                    "command_type": "robot.action",
                    "status": "succeeded",
                    ...
                }
            ],
            "edge_id": "edge-001"
        }

    Response:
        {
            "success": true,
            "synced_count": 5,
            "total": 42
        }
    """
    if _storage_path is None:
        return jsonify({"success": False, "error": "Storage not initialized"}), 503

    if not _validate_user_id(user_id):
        return jsonify({"success": False, "error": "Invalid user_id"}), 400

    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return jsonify({"success": False, "error": "Invalid JSON body"}), 400

    records = data.get('records')
    if records is None or not isinstance(records, list):
        return jsonify({"success": False, "error": "Missing or invalid 'records' field"}), 400

    try:
        history_path = _get_history_path(user_id)

        # 讀取現有歷史記錄
        existing: List[Dict[str, Any]] = []
        if history_path.exists():
            with open(history_path, 'r', encoding='utf-8') as f:
                stored = json.load(f)
                existing = stored.get('records', [])

        # 合併新記錄（以 command_id 去重）
        existing_ids = {r.get('command_id') for r in existing if r.get('command_id')}
        new_records = [r for r in records if r.get('command_id') not in existing_ids]
        merged = existing + new_records

        payload = {
            'user_id': user_id,
            'edge_id': data.get('edge_id'),
            'updated_at': datetime.now(timezone.utc).isoformat(),
            'records': merged
        }

        with open(history_path, 'w', encoding='utf-8') as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

        logger.info(
            f"History synced for user '{user_id}': "
            f"{len(new_records)} new records added, total {len(merged)}"
        )
        return jsonify({
            "success": True,
            "synced_count": len(new_records),
            "total": len(merged)
        })

    except Exception as e:
        logger.error(f"Failed to save history for user '{user_id}': {e}")
        return jsonify({"success": False, "error": "Failed to save history"}), 500


@data_sync_bp.route('/history/<user_id>', methods=['GET'])
@_require_auth
def download_history(user_id: str):
    """從雲端下載指令執行歷史

    Path Parameters:
        user_id: 用戶 ID

    Query Parameters:
        limit: 返回記錄數上限（預設 100）
        offset: 查詢偏移量（預設 0）

    Response:
        {
            "success": true,
            "data": {
                "records": [...],
                "total": 42
            }
        }
    """
    if _storage_path is None:
        return jsonify({"success": False, "error": "Storage not initialized"}), 503

    if not _validate_user_id(user_id):
        return jsonify({"success": False, "error": "Invalid user_id"}), 400

    try:
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        limit = min(max(limit, 1), 1000)
        offset = max(offset, 0)

        history_path = _get_history_path(user_id)
        if not history_path.exists():
            return jsonify({
                "success": True,
                "data": {"records": [], "total": 0}
            })

        with open(history_path, 'r', encoding='utf-8') as f:
            stored = json.load(f)

        all_records = stored.get('records', [])
        page = all_records[offset:offset + limit]

        return jsonify({
            "success": True,
            "data": {
                "records": page,
                "total": len(all_records)
            }
        })

    except Exception as e:
        logger.error(f"Failed to load history for user '{user_id}': {e}")
        return jsonify({"success": False, "error": "Failed to load history"}), 500
