# imports
import json
import logging
import re
import threading
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
from typing import Any, Dict, List, Optional

from flask import Blueprint, jsonify, request

from .auth import CloudAuthService

logger = logging.getLogger(__name__)

# 僅允許安全的 user_id 字元（A-Z a-z 0-9 _ -），長度 1-64，防止路徑穿越
_SAFE_ID_PATTERN = re.compile(r'^[A-Za-z0-9_-]{1,64}$')

# Blueprint
data_sync_bp = Blueprint('data_sync', __name__, url_prefix='/api/cloud/data_sync')

# 認證服務實例（需在初始化時設定）
_auth_service: Optional[CloudAuthService] = None

# 儲存路徑（需在初始化時設定）
_storage_path: Optional[Path] = None

# 檔案層級的執行緒鎖（防止併發寫入同一個用戶歷史檔案的競態條件）
# 最多保留 MAX_FILE_LOCKS 個鎖以避免記憶體無限成長
_file_locks: Dict[str, threading.Lock] = {}
_file_locks_lock = threading.Lock()
_MAX_FILE_LOCKS = 1024


def _get_file_lock(path: str) -> threading.Lock:
    """取得或建立對應 path 的執行緒鎖

    當鎖字典超過上限時，清除已有的鎖（僅在持有 _file_locks_lock 時安全）。
    """
    with _file_locks_lock:
        if path not in _file_locks:
            if len(_file_locks) >= _MAX_FILE_LOCKS:
                # 超過上限時清除，讓 GC 回收不再被任何執行緒持有的鎖
                _file_locks.clear()
                logger.debug("file_locks evicted (exceeded max size)")
            _file_locks[path] = threading.Lock()
        return _file_locks[path]


def init_data_sync_api(jwt_secret: str, storage_path: str) -> None:
    """初始化資料同步 API

    Args:
        jwt_secret: JWT 密鑰
        storage_path: 儲存根目錄路徑

    Example:
        >>> from Cloud.api.data_sync import data_sync_bp, init_data_sync_api
        >>> app.register_blueprint(data_sync_bp)
        >>> init_data_sync_api(
        ...     jwt_secret='your-secret-key',
        ...     storage_path='/var/data/cloud_sync'
        ... )
    """
    global _auth_service, _storage_path
    _auth_service = CloudAuthService(jwt_secret)
    _storage_path = Path(storage_path)
    _storage_path.mkdir(parents=True, exist_ok=True)
    logger.info(f"Data sync API initialized, storage: {_storage_path}")


def _require_auth(f):
    """JWT 認證裝飾器

    認證成功後在 request 物件上設定：
    - request.user_id: token 中的用戶 ID
    - request.username: token 中的用戶名
    - request.role: token 中的角色（user / admin / auditor 等）
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if _auth_service is None:
            return jsonify({
                "error": "Service Unavailable",
                "message": "Cloud services not initialized"
            }), 503

        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"error": "Unauthorized", "message": "Missing or invalid token"}), 401

        token = auth_header[7:]
        payload = _auth_service.verify_token(token)
        if not payload:
            return jsonify({"error": "Unauthorized", "message": "Invalid or expired token"}), 401

        request.user_id = payload.get("user_id")
        request.username = payload.get("username")
        request.role = payload.get("role", "user")
        return f(*args, **kwargs)
    return decorated


def _validate_user_id(user_id: str) -> bool:
    """驗證 user_id 格式是否安全

    只允許 A-Za-z0-9_- 且長度 1-64，防止路徑穿越攻擊。

    Args:
        user_id: 要驗證的用戶 ID

    Returns:
        是否安全
    """
    return bool(_SAFE_ID_PATTERN.match(user_id))


def _check_user_access(path_user_id: str):
    """授權檢查：確認 token 用戶只能存取自己的資料

    Admin 角色可以存取所有用戶的資料。

    Args:
        path_user_id: URL 路徑中的 user_id

    Returns:
        None 表示通過，否則回傳 Flask Response（403）
    """
    token_user_id = getattr(request, 'user_id', None)
    role = getattr(request, 'role', 'user')

    if role == 'admin':
        return None  # admin 可以存取所有用戶資料

    if token_user_id != path_user_id:
        return jsonify({
            "error": "Forbidden",
            "message": "Access to another user's data is not allowed"
        }), 403

    return None


def _get_settings_path(user_id: str) -> Path:
    """取得用戶設定檔案路徑"""
    # 防止路徑穿越與非法字元，確保設定檔僅建立於 user_settings 目錄下
    if "/" in user_id or "\\" in user_id or ".." in user_id:
        raise ValueError("Invalid user_id for settings path")
    # 僅允許常見安全字元（英數、底線、連字號）；如需支援更多字元可調整此規則
    if not re.fullmatch(r"[A-Za-z0-9_-]+", user_id):
        raise ValueError("Invalid user_id format for settings path")

    settings_dir = _storage_path / "user_settings"
    settings_dir.mkdir(parents=True, exist_ok=True)

    # 構造設定檔案路徑並以實際路徑驗證不會逃出 user_settings 目錄
    candidate = settings_dir / f"settings_{user_id}.json"
    resolved_dir = settings_dir.resolve()
    resolved_file = candidate.resolve()
    if resolved_file.parent != resolved_dir:
        raise ValueError("Resolved settings path escapes settings directory")

    return resolved_file


def _get_history_path(user_id: str) -> Path:
    """取得用戶指令歷史檔案路徑"""
    # 防止路徑穿越與非法字元，確保歷史檔僅建立於 command_history 目錄下
    if "/" in user_id or "\\" in user_id or ".." in user_id:
        raise ValueError("Invalid user_id for history path")
    # 與設定檔相同的格式限制，避免產生包含目錄分隔符的檔名
    if not re.fullmatch(r"[A-Za-z0-9_-]+", user_id):
        raise ValueError("Invalid user_id format for history path")

    history_dir = _storage_path / "command_history"
    history_dir.mkdir(parents=True, exist_ok=True)
    # 構造歷史檔案路徑並以實際路徑驗證不會逃出 command_history 目錄
    candidate = history_dir / f"history_{user_id}.json"
    resolved_dir = history_dir.resolve()
    resolved_file = candidate.resolve()
    if resolved_file.parent != resolved_dir:
        raise ValueError("Resolved history path escapes history directory")
    return resolved_file




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

    access_error = _check_user_access(user_id)
    if access_error is not None:
        return access_error

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

    access_error = _check_user_access(user_id)
    if access_error is not None:
        return access_error

    try:
        settings_path = _get_settings_path(user_id)
        if not settings_path.exists():
            return jsonify({"success": False, "error": "Settings not found"}), 404

        with open(settings_path, 'r', encoding='utf-8') as f:
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

    Note:
        歷史記錄以 command_id 去重。目前使用 JSON 檔案儲存；若記錄量超過
        數千筆，建議遷移至 SQLite 以獲得更好的查詢效能。
    """
    if _storage_path is None:
        return jsonify({"success": False, "error": "Storage not initialized"}), 503

    if not _validate_user_id(user_id):
        return jsonify({"success": False, "error": "Invalid user_id"}), 400

    access_error = _check_user_access(user_id)
    if access_error is not None:
        return access_error

    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return jsonify({"success": False, "error": "Invalid JSON body"}), 400

    records = data.get('records')
    if records is None or not isinstance(records, list):
        return jsonify({"success": False, "error": "Missing or invalid 'records' field"}), 400

    try:
        history_path = _get_history_path(user_id)
        file_lock = _get_file_lock(str(history_path))

        with file_lock:
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
        limit: 返回記錄數上限（預設 100，最大 1000）
        offset: 查詢偏移量（預設 0）

    Response:
        {
            "success": true,
            "data": {
                "records": [...],
                "total": 42
            }
        }

    Note:
        分頁目前在記憶體中切片完成。若歷史量超過數千筆，
        建議遷移至 SQLite 以獲得更好的效能。
    """
    if _storage_path is None:
        return jsonify({"success": False, "error": "Storage not initialized"}), 503

    if not _validate_user_id(user_id):
        return jsonify({"success": False, "error": "Invalid user_id"}), 400

    access_error = _check_user_access(user_id)
    if access_error is not None:
        return access_error

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
