"""
Cloud API Flask 路由

提供雲服務 REST API 端點
"""

import logging
from functools import wraps
from io import BytesIO
from typing import Optional

from flask import Blueprint, request, jsonify, send_file

from .auth import CloudAuthService
from .storage import CloudStorageService


logger = logging.getLogger(__name__)

# 建立 Blueprint
cloud_bp = Blueprint('cloud', __name__, url_prefix='/api/cloud')

# 服務實例（需要在初始化時設定）
auth_service: Optional[CloudAuthService] = None
storage_service: Optional[CloudStorageService] = None


def init_cloud_services(jwt_secret: str, storage_path: str):
    """
    初始化雲服務

    Args:
        jwt_secret: JWT 密鑰
        storage_path: 儲存路徑
    """
    global auth_service, storage_service
    auth_service = CloudAuthService(jwt_secret)
    storage_service = CloudStorageService(storage_path)
    logger.info("Cloud services initialized")


def require_auth(f):
    """認證裝飾器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 檢查服務是否已初始化
        if auth_service is None:
            return jsonify({
                "error": "Service Unavailable",
                "message": "Cloud services not initialized. Please call init_cloud_services first."
            }), 503

        # 取得 Token
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"error": "Unauthorized", "message": "Missing or invalid token"}), 401

        token = auth_header[7:]  # 移除 "Bearer "

        # 驗證 Token
        payload = auth_service.verify_token(token)
        if not payload:
            return jsonify({"error": "Unauthorized", "message": "Invalid or expired token"}), 401

        # 將用戶資訊加入 request
        request.user_id = payload.get("user_id")
        request.username = payload.get("username")
        request.role = payload.get("role")

        return f(*args, **kwargs)
    return decorated_function


@cloud_bp.route('/auth/token', methods=['POST'])
def generate_token():
    """
    生成 JWT Token

    注意：此端點為示範用途，生產環境應整合實際的認證系統（帳密驗證、OAuth2 等）

    Request Body:
        {
            "user_id": "user-123",
            "username": "test_user",
            "role": "user"
        }

    Response:
        {
            "token": "eyJ...",
            "expires_in": 86400
        }
    """
    try:
        # 檢查服務是否已初始化
        if auth_service is None:
            return jsonify({
                "error": "Service Unavailable",
                "message": "Cloud services not initialized"
            }), 503

        data = request.get_json(silent=True)

        # 驗證請求資料
        if not data or not isinstance(data, dict):
            return jsonify({"error": "Bad Request", "message": "Invalid JSON body"}), 400

        required_fields = ["user_id", "username"]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": "Bad Request", "message": f"Missing field: {field}"}), 400

        # 限制 expires_in 範圍（最多 7 天）
        expires_in = min(data.get("expires_in", 86400), 7 * 24 * 3600)

        # 生成 Token
        token = auth_service.generate_token(
            user_id=data["user_id"],
            username=data["username"],
            role=data.get("role", "user"),
            expires_in=expires_in
        )

        return jsonify({
            "token": token,
            "expires_in": expires_in
        }), 200

    except Exception as e:
        logger.error(f"Token generation error: {e}")
        return jsonify({"error": "Internal Server Error", "message": "Token generation failed"}), 500


@cloud_bp.route('/storage/upload', methods=['POST'])
@require_auth
def upload_file():
    """
    上傳檔案

    Form Data:
        file: 檔案內容
        category: 檔案類別（可選，預設 "general"）

    Response:
        {
            "file_id": "abc123...",
            "filename": "test.txt",
            "size": 1024,
            "hash": "abc123...",
            "category": "general",
            "uploaded_at": "2025-01-01T00:00:00Z"
        }
    """
    try:
        # 檢查檔案
        if 'file' not in request.files:
            return jsonify({"error": "Bad Request", "message": "No file provided"}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "Bad Request", "message": "Empty filename"}), 400

        # 取得類別
        category = request.form.get('category', 'general')

        # 上傳檔案
        result = storage_service.upload_file(
            file_data=file.stream,
            filename=file.filename,
            user_id=request.user_id,
            category=category
        )

        return jsonify(result), 200

    except ValueError as e:
        logger.warning("File upload validation error", exc_info=True)
        return jsonify({"error": "Bad Request", "message": "Invalid request"}), 400
    except Exception as e:
        logger.error("File upload error", exc_info=True)
        return jsonify({"error": "Internal Server Error", "message": "An internal error has occurred"}), 500


@cloud_bp.route('/storage/download/<file_id>', methods=['GET'])
@require_auth
def download_file(file_id: str):
    """
    下載檔案

    Path Parameters:
        file_id: 檔案 ID

    Query Parameters:
        category: 檔案類別（可選，預設 "general"）

    Response:
        檔案內容（binary）
    """
    try:
        category = request.args.get('category', 'general')

        # 下載檔案
        content = storage_service.download_file(
            file_id=file_id,
            user_id=request.user_id,
            category=category
        )

        if content is None:
            return jsonify({"error": "Not Found", "message": "File not found"}), 404

        # 返回檔案
        return send_file(
            BytesIO(content),
            download_name=f"{file_id}",
            as_attachment=True
        )

    except Exception as e:
        logger.error(f"File download error: {e}")
        return jsonify({"error": "Internal Server Error", "message": "An internal server error occurred"}), 500


@cloud_bp.route('/storage/files', methods=['GET'])
@require_auth
def list_files():
    """
    列出檔案

    Query Parameters:
        category: 檔案類別（可選）

    Response:
        {
            "files": [
                {
                    "file_id": "abc123",
                    "filename": "test.txt",
                    "size": 1024,
                    "category": "general",
                    "modified_at": "2025-01-01T00:00:00Z"
                }
            ],
            "total": 1
        }
    """
    try:
        category = request.args.get('category')

        # 列出檔案
        files = storage_service.list_files(
            user_id=request.user_id,
            category=category
        )

        return jsonify({
            "files": files,
            "total": len(files)
        }), 200

    except Exception as e:
        logger.error(f"File listing error: {e}")
        return jsonify({"error": "Internal Server Error", "message": "An internal server error occurred"}), 500


@cloud_bp.route('/storage/files/<file_id>', methods=['DELETE'])
@require_auth
def delete_file(file_id: str):
    """
    刪除檔案

    Path Parameters:
        file_id: 檔案 ID

    Query Parameters:
        category: 檔案類別（可選，預設 "general"）

    Response:
        {
            "message": "File deleted successfully"
        }
    """
    try:
        category = request.args.get('category', 'general')

        # 刪除檔案
        success = storage_service.delete_file(
            file_id=file_id,
            user_id=request.user_id,
            category=category
        )

        if not success:
            return jsonify({"error": "Not Found", "message": "File not found"}), 404

        return jsonify({"message": "File deleted successfully"}), 200

    except Exception as e:
        logger.error(f"File deletion error: {e}")
        return jsonify({"error": "Internal Server Error", "message": "An internal server error occurred"}), 500


@cloud_bp.route('/storage/stats', methods=['GET'])
@require_auth
def get_stats():
    """
    取得儲存統計

    Response:
        {
            "user_id": "user-123",
            "total_files": 10,
            "total_size": 102400,
            "total_size_mb": 0.1
        }
    """
    try:
        stats = storage_service.get_storage_stats(user_id=request.user_id)
        return jsonify(stats), 200

    except Exception as e:
        logger.error(f"Stats retrieval error: {e}", exc_info=True)
        return jsonify({"error": "Internal Server Error", "message": "Failed to retrieve storage statistics"}), 500


@cloud_bp.route('/health', methods=['GET'])
def health_check():
    """
    健康檢查

    Response:
        {
            "status": "healthy",
            "services": {
                "auth": "ok",
                "storage": "ok"
            }
        }
    """
    return jsonify({
        "status": "healthy",
        "services": {
            "auth": "ok" if auth_service else "not_initialized",
            "storage": "ok" if storage_service else "not_initialized"
        }
    }), 200
