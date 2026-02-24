# imports
import json
import logging
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from functools import wraps
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename

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
    """取得用戶設定檔案路徑

    使用 secure_filename 截斷 user-provided value 的 taint flow，
    再以 _SAFE_ID_PATTERN 與 resolve() 進行 defence-in-depth 驗證。
    """
    # secure_filename 去除路徑分隔符與危險字元（CodeQL 認可的 sanitizer）
    safe_id = secure_filename(user_id)
    # 再以白名單正規表達式確保格式正確（不允許點號、有長度限制）
    if not safe_id or not _SAFE_ID_PATTERN.match(safe_id):
        raise ValueError("Invalid user_id for settings path")

    settings_dir = _storage_path / "user_settings"
    settings_dir.mkdir(parents=True, exist_ok=True)

    # 以實際路徑驗證構造後的路徑不會逃出 user_settings 目錄
    candidate = settings_dir / f"settings_{safe_id}.json"
    resolved_dir = settings_dir.resolve()
    resolved_file = candidate.resolve()
    if resolved_file.parent != resolved_dir:
        raise ValueError("Resolved settings path escapes settings directory")

    return resolved_file


# ==================== 歷史記錄 SQLite 儲存 ====================

def _get_history_db_path() -> Path:
    """取得歷史記錄 SQLite 資料庫路徑（所有用戶共用同一個 DB）"""
    history_dir = _storage_path / "command_history"
    history_dir.mkdir(parents=True, exist_ok=True)
    return history_dir / "history.db"


@contextmanager
def _history_db_conn() -> Generator[sqlite3.Connection, None, None]:
    """取得 SQLite 連線（context manager）

    每次呼叫都建立新的連線並在結束後關閉，確保連線不跨執行緒共用。
    `check_same_thread=False` 允許 Flask 的執行緒池服務請求——
    此處是安全的，因為每個請求使用獨立的 conn 物件，不存在共用狀態。
    WAL 模式支援多讀單寫並行，避免 SQLITE_BUSY。
    """
    db_path = _get_history_db_path()
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        _ensure_history_table(conn)
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _ensure_history_table(conn: sqlite3.Connection) -> None:
    """確保 command_history 資料表存在"""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS command_history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     TEXT    NOT NULL,
            command_id  TEXT    NOT NULL,
            edge_id     TEXT,
            record_json TEXT    NOT NULL,
            synced_at   TEXT    NOT NULL,
            UNIQUE (user_id, command_id)
        )
    """)
    conn.execute(
        # 僅對 user_id 建立索引；id 是主鍵，SQLite 已自動索引，無需重複包含
        "CREATE INDEX IF NOT EXISTS idx_history_user ON command_history (user_id)"
    )


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
        歷史記錄儲存於 SQLite，以 (user_id, command_id) 為唯一鍵自動去重。
        SQLite WAL 模式支援多讀單寫並行，不需額外執行緒鎖。
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

    edge_id = data.get('edge_id', '')
    synced_at = datetime.now(timezone.utc).isoformat()

    try:
        synced_count = 0
        with _history_db_conn() as conn:
            for record in records:
                command_id = record.get('command_id')
                if not command_id:
                    continue
                cursor = conn.execute(
                    """
                    INSERT OR IGNORE INTO command_history
                        (user_id, command_id, edge_id, record_json, synced_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    # INSERT OR IGNORE 以「第一次寫入為準」的策略去重：
                    # 歷史記錄一旦寫入即視為不可變，後續相同 command_id 的上傳
                    # 不會覆蓋既有資料。若需更新舊紀錄，應改用 INSERT OR REPLACE。
                    (user_id, command_id, edge_id, json.dumps(record), synced_at)
                )
                synced_count += cursor.rowcount

            total = conn.execute(
                "SELECT COUNT(*) FROM command_history WHERE user_id = ?", (user_id,)
            ).fetchone()[0]

        logger.info(
            f"History synced for user '{user_id}': "
            f"{synced_count} new records added, total {total}"
        )
        return jsonify({
            "success": True,
            "synced_count": synced_count,
            "total": total
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
        分頁查詢透過 SQLite LIMIT/OFFSET 實作，僅讀取所需資料列，
        不需將全部記錄載入記憶體。
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

        with _history_db_conn() as conn:
            total = conn.execute(
                "SELECT COUNT(*) FROM command_history WHERE user_id = ?", (user_id,)
            ).fetchone()[0]

            rows = conn.execute(
                """
                SELECT record_json FROM command_history
                WHERE user_id = ?
                ORDER BY id
                LIMIT ? OFFSET ?
                """,
                (user_id, limit, offset)
            ).fetchall()

        page: List[Dict[str, Any]] = [json.loads(row["record_json"]) for row in rows]

        return jsonify({
            "success": True,
            "data": {
                "records": page,
                "total": total
            }
        })

    except Exception as e:
        logger.error(f"Failed to load history for user '{user_id}': {e}")
        return jsonify({"success": False, "error": "Failed to load history"}), 500
