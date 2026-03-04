# imports
import logging
from contextlib import contextmanager
from functools import wraps
from typing import Optional

from flask import Blueprint, jsonify, request

from Cloud.api.auth import CloudAuthService
from Cloud.engagement.database import init_db, is_initialized, session_scope
from Cloud.engagement.service import EngagementService

logger = logging.getLogger(__name__)

# Blueprint
bp = Blueprint('engagement_api', __name__, url_prefix='/api/cloud/engagement')

# 認證服務（需要在初始化時設定）
auth_service: Optional[CloudAuthService] = None


def init_engagement_api(jwt_secret: str, database_url: str, create_tables: bool = True):
    """初始化 Engagement API（認證 + 資料庫）

    Args:
        jwt_secret: JWT 密鑰
        database_url: 資料庫 URL（例如: sqlite:///engagement.db）
        create_tables: 是否自動建立資料表

    Example:
        >>> from Cloud.engagement.api import init_engagement_api, bp
        >>> app.register_blueprint(bp)
        >>> init_engagement_api('secret', 'sqlite:///engagement.db')
    """
    global auth_service
    auth_service = CloudAuthService(jwt_secret)
    init_db(database_url, create_tables=create_tables)
    logger.info("Engagement API initialized")


@contextmanager
def get_service():
    """取得 EngagementService 實例的 context manager

    Raises:
        RuntimeError: 如果資料庫尚未初始化
    """
    if not is_initialized():
        raise RuntimeError("Database not initialized. Call init_engagement_api() first.")
    with session_scope() as session:
        yield EngagementService(session)


def require_auth(f):
    """認證裝飾器（需要有效的 Bearer Token）"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if auth_service is None:
            return jsonify({
                "success": False,
                "error": "Service Unavailable",
                "message": "Auth service not initialized",
            }), 503

        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                "success": False,
                "error": "Unauthorized",
                "message": "Missing or invalid token",
            }), 401

        token = auth_header[7:]
        payload = auth_service.verify_token(token)
        if not payload:
            return jsonify({
                "success": False,
                "error": "Unauthorized",
                "message": "Invalid or expired token",
            }), 401

        request.user_id = payload.get("user_id")
        request.username = payload.get("username")
        request.role = payload.get("role")
        return f(*args, **kwargs)
    return decorated_function


def _get_authenticated_username():
    """從請求 Header 中取得已驗證的用戶名稱（用於同時支援 GET/POST 的端點）

    Returns:
        (username, None) 驗證成功
        (None, response_tuple) 驗證失敗，回傳對應的 Flask response tuple
    """
    if auth_service is None:
        return None, (jsonify({
            "success": False,
            "error": "Service Unavailable",
            "message": "Auth service not initialized",
        }), 503)
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return None, (jsonify({
            "success": False,
            "error": "Unauthorized",
            "message": "Missing or invalid token",
        }), 401)
    payload = auth_service.verify_token(auth_header[7:])
    if not payload:
        return None, (jsonify({
            "success": False,
            "error": "Unauthorized",
            "message": "Invalid or expired token",
        }), 401)
    return payload.get("username"), None


# ──────────────────────────────
# 用戶積分檔案
# ──────────────────────────────

@bp.route('/profile/<username>', methods=['GET'])
def get_profile(username: str):
    """取得用戶積分檔案

    GET /api/cloud/engagement/profile/<username>
    """
    try:
        with get_service() as service:
            profile = service.get_profile(username)
            if not profile:
                return jsonify({'success': False, 'error': '用戶檔案不存在'}), 404

        return jsonify({'success': True, 'data': profile.to_dict()}), 200
    except Exception:
        logger.error("Get profile error", exc_info=True)
        return jsonify({'success': False, 'error': '伺服器錯誤'}), 500


@bp.route('/leaderboard', methods=['GET'])
def get_leaderboard():
    """取得排行榜

    GET /api/cloud/engagement/leaderboard?sort_by=points&limit=10
    """
    try:
        sort_by = request.args.get('sort_by', 'points')
        limit = request.args.get('limit', 10, type=int)

        with get_service() as service:
            profiles = service.get_leaderboard(limit=limit, sort_by=sort_by)

        return jsonify({
            'success': True,
            'data': {
                'leaderboard': [p.to_dict() for p in profiles],
                'sort_by': sort_by,
            },
        }), 200
    except Exception:
        logger.error("Get leaderboard error", exc_info=True)
        return jsonify({'success': False, 'error': '伺服器錯誤'}), 500


# ──────────────────────────────
# 討論區貼文
# ──────────────────────────────

@bp.route('/posts', methods=['GET', 'POST'])
def posts():
    """列出或建立討論區貼文

    GET /api/cloud/engagement/posts?category=general&sort_by=created_at&order=desc&limit=50&offset=0
    POST /api/cloud/engagement/posts  （需要認證）
    {
        "title": "貼文標題",
        "body": "貼文內容",
        "category": "general"
    }
    """
    try:
        if request.method == 'GET':
            category = request.args.get('category')
            author_username = request.args.get('author')
            sort_by = request.args.get('sort_by', 'created_at')
            order = request.args.get('order', 'desc')
            limit = request.args.get('limit', 50, type=int)
            offset = request.args.get('offset', 0, type=int)

            with get_service() as service:
                post_list, total = service.list_posts(
                    category=category,
                    author_username=author_username,
                    sort_by=sort_by,
                    order=order,
                    limit=limit,
                    offset=offset,
                )

            return jsonify({
                'success': True,
                'data': {
                    'posts': [p.to_dict() for p in post_list],
                    'total': total,
                    'limit': limit,
                    'offset': offset,
                },
            }), 200

        # POST - 需要認證
        username, err = _get_authenticated_username()
        if err:
            return err

        data = request.get_json(silent=True) or {}
        title = data.get('title')
        body = data.get('body')
        category = data.get('category', 'general')

        if not title or not body:
            return jsonify({'success': False, 'error': '缺少必要欄位: title 或 body'}), 400

        with get_service() as service:
            post = service.create_post(
                author_username=username,
                title=title,
                body=body,
                category=category,
            )
            # 給予積分獎勵
            service.award_points(username, 'post_created')

        return jsonify({
            'success': True,
            'message': '貼文已建立',
            'data': post.to_dict(),
        }), 201

    except ValueError:
        logger.warning("Posts endpoint validation error", exc_info=True)
        return jsonify({'success': False, 'error': '請求參數錯誤'}), 400
    except Exception:
        logger.error("Posts endpoint error", exc_info=True)
        return jsonify({'success': False, 'error': '伺服器錯誤'}), 500


@bp.route('/posts/<int:post_id>', methods=['GET', 'DELETE'])
def post_detail(post_id: int):
    """取得或刪除特定貼文

    GET /api/cloud/engagement/posts/<post_id>
    DELETE /api/cloud/engagement/posts/<post_id>  （需要認證，只有作者可刪除）
    """
    try:
        if request.method == 'GET':
            with get_service() as service:
                post = service.get_post(post_id)
                if not post:
                    return jsonify({'success': False, 'error': '貼文不存在'}), 404
            return jsonify({'success': True, 'data': post.to_dict()}), 200

        # DELETE - 需要認證
        username, err = _get_authenticated_username()
        if err:
            return err

        with get_service() as service:
            service.delete_post(post_id, username)

        return jsonify({'success': True, 'message': '貼文已刪除'}), 200

    except ValueError as e:
        msg = str(e)
        logger.warning("Post detail validation error: %s", msg, exc_info=True)
        if '無權限' in msg:
            return jsonify({'success': False, 'error': '無權限刪除此貼文'}), 403
        return jsonify({'success': False, 'error': '貼文不存在'}), 404
    except Exception:
        logger.error("Post detail error", exc_info=True)
        return jsonify({'success': False, 'error': '伺服器錯誤'}), 500


# ──────────────────────────────
# 評論
# ──────────────────────────────

@bp.route('/posts/<int:post_id>/comments', methods=['GET', 'POST'])
def post_comments(post_id: int):
    """取得或新增貼文評論

    GET /api/cloud/engagement/posts/<post_id>/comments?limit=50&offset=0
    POST /api/cloud/engagement/posts/<post_id>/comments  （需要認證）
    {
        "content": "評論內容",
        "parent_comment_id": null
    }
    """
    try:
        if request.method == 'GET':
            with get_service() as service:
                limit = request.args.get('limit', 50, type=int)
                offset = request.args.get('offset', 0, type=int)
                comments = service.get_comments(post_id, limit, offset)
            return jsonify({
                'success': True,
                'data': {
                    'comments': [c.to_dict(include_replies=True) for c in comments],
                    'limit': limit,
                    'offset': offset,
                },
            }), 200

        # POST - 需要認證（在取得 service 前先驗證，確保語意一致）
        username, err = _get_authenticated_username()
        if err:
            return err

        data = request.get_json(silent=True) or {}
        content = data.get('content')
        parent_comment_id_raw = data.get('parent_comment_id')
        parent_comment_id: Optional[int] = None
        if parent_comment_id_raw is not None:
            try:
                parent_comment_id = int(parent_comment_id_raw)
            except (TypeError, ValueError):
                return jsonify({
                    'success': False,
                    'error': '請求參數錯誤',
                    'message': 'parent_comment_id 必須為整數或 null',
                }), 400

        if not content:
            return jsonify({'success': False, 'error': '缺少必要欄位: content'}), 400

        with get_service() as service:
            comment = service.add_comment(
                post_id=post_id,
                author_username=username,
                content=content,
                parent_comment_id=parent_comment_id,
            )
            service.award_points(username, 'comment_created')

        return jsonify({
            'success': True,
            'message': '評論已提交',
            'data': comment.to_dict(),
        }), 201

    except ValueError as e:
        msg = str(e)
        logger.warning("Post comments validation error: %s", msg, exc_info=True)
        if '貼文不存在' in msg:
            return jsonify({'success': False, 'error': '貼文不存在'}), 404
        return jsonify({'success': False, 'error': '請求參數錯誤'}), 400
    except Exception:
        logger.error("Post comments error", exc_info=True)
        return jsonify({'success': False, 'error': '伺服器錯誤'}), 500


# ──────────────────────────────
# 點讚
# ──────────────────────────────

@bp.route('/posts/<int:post_id>/like', methods=['POST'])
@require_auth
def like_post(post_id: int):
    """對貼文點讚或取消點讚（切換）

    POST /api/cloud/engagement/posts/<post_id>/like  （需要認證）
    """
    try:
        with get_service() as service:
            result = service.like_post(post_id, request.username)
            if result['liked']:
                service.award_points(request.username, 'post_liked')

        return jsonify({'success': True, 'data': result}), 200

    except ValueError:
        logger.warning("Like post validation error", exc_info=True)
        return jsonify({'success': False, 'error': '貼文不存在'}), 404
    except Exception:
        logger.error("Like post error", exc_info=True)
        return jsonify({'success': False, 'error': '伺服器錯誤'}), 500


# ──────────────────────────────
# 健康檢查
# ──────────────────────────────

@bp.route('/health', methods=['GET'])
def health_check():
    """健康檢查

    GET /api/cloud/engagement/health
    """
    return jsonify({
        'status': 'healthy',
        'services': {
            'auth': 'ok' if auth_service else 'not_initialized',
            'database': 'ok' if is_initialized() else 'not_initialized',
        },
    }), 200
