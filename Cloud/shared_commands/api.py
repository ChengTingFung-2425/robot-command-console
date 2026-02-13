# imports
from flask import Blueprint, request, jsonify
import logging

from Cloud.shared_commands.service import SharedCommandService

logger = logging.getLogger(__name__)

# Blueprint
bp = Blueprint('shared_commands_api', __name__, url_prefix='/api/cloud/shared_commands')


def get_service() -> SharedCommandService:
    """取得服務實例

    注意：這個函數需要在實際部署時實作資料庫連接邏輯。
    目前僅作為佔位符。
    """
    # TODO: 實作資料庫連接與 session 管理
    raise NotImplementedError("Database session management not implemented yet")


@bp.route('/upload', methods=['POST'])
def upload_command():
    """上傳進階指令到雲端

    POST /api/cloud/shared_commands/upload
    {
        "name": "指令名稱",
        "description": "指令說明",
        "category": "指令分類",
        "content": "[{"command": "go_forward"}, ...]",
        "author_username": "作者",
        "author_email": "email@example.com",
        "edge_id": "edge-device-123",
        "original_command_id": 1,
        "version": 1
    }
    """
    try:
        data = request.get_json()

        # 驗證必要欄位
        required_fields = [
            'name', 'description', 'category', 'content',
            'author_username', 'author_email', 'edge_id', 'original_command_id'
        ]
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'缺少必要欄位: {field}'
                }), 400

        service = get_service()
        command = service.upload_command(
            name=data['name'],
            description=data['description'],
            category=data['category'],
            content=data['content'],
            author_username=data['author_username'],
            author_email=data['author_email'],
            edge_id=data['edge_id'],
            original_command_id=data['original_command_id'],
            version=data.get('version', 1)
        )

        return jsonify({
            'success': True,
            'message': '指令已成功上傳',
            'data': command.to_dict()
        }), 201

    except ValueError as e:
        logger.error(f"Upload command validation error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Upload command error: {e}", exc_info=True)
        return jsonify({'success': False, 'error': '伺服器錯誤'}), 500


@bp.route('/search', methods=['GET'])
def search_commands():
    """搜尋共享指令

    GET /api/cloud/shared_commands/search?
        query=關鍵字&
        category=分類&
        author=作者&
        min_rating=4.0&
        sort_by=rating&
        order=desc&
        limit=50&
        offset=0
    """
    try:
        query = request.args.get('query')
        category = request.args.get('category')
        author = request.args.get('author')
        min_rating = request.args.get('min_rating', type=float)
        sort_by = request.args.get('sort_by', 'rating')
        order = request.args.get('order', 'desc')
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)

        service = get_service()
        commands, total = service.search_commands(
            query=query,
            category=category,
            author=author,
            min_rating=min_rating,
            sort_by=sort_by,
            order=order,
            limit=limit,
            offset=offset
        )

        return jsonify({
            'success': True,
            'data': {
                'commands': [cmd.to_dict() for cmd in commands],
                'total': total,
                'limit': limit,
                'offset': offset
            }
        }), 200

    except Exception as e:
        logger.error(f"Search commands error: {e}", exc_info=True)
        return jsonify({'success': False, 'error': '伺服器錯誤'}), 500


@bp.route('/<int:command_id>', methods=['GET'])
def get_command(command_id: int):
    """取得指令詳情

    GET /api/cloud/shared_commands/<command_id>
    """
    try:
        service = get_service()
        command = service.get_command(command_id)

        if not command:
            return jsonify({
                'success': False,
                'error': '指令不存在或不公開'
            }), 404

        return jsonify({
            'success': True,
            'data': command.to_dict()
        }), 200

    except Exception as e:
        logger.error(f"Get command error: {e}", exc_info=True)
        return jsonify({'success': False, 'error': '伺服器錯誤'}), 500


@bp.route('/<int:command_id>/download', methods=['POST'])
def download_command(command_id: int):
    """下載共享指令

    POST /api/cloud/shared_commands/<command_id>/download
    {
        "edge_id": "edge-device-123"
    }
    """
    try:
        data = request.get_json()
        edge_id = data.get('edge_id')

        if not edge_id:
            return jsonify({
                'success': False,
                'error': '缺少 edge_id'
            }), 400

        service = get_service()
        command = service.download_command(command_id, edge_id)

        return jsonify({
            'success': True,
            'message': '指令已成功下載',
            'data': command.to_dict()
        }), 200

    except ValueError as e:
        logger.error(f"Download command error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 404
    except Exception as e:
        logger.error(f"Download command error: {e}", exc_info=True)
        return jsonify({'success': False, 'error': '伺服器錯誤'}), 500


@bp.route('/<int:command_id>/rate', methods=['POST'])
def rate_command(command_id: int):
    """對指令評分

    POST /api/cloud/shared_commands/<command_id>/rate
    {
        "user_username": "username",
        "rating": 5,
        "comment": "很好用的指令"
    }
    """
    try:
        data = request.get_json()
        user_username = data.get('user_username')
        rating = data.get('rating')
        comment = data.get('comment')

        if not user_username or rating is None:
            return jsonify({
                'success': False,
                'error': '缺少必要欄位: user_username 或 rating'
            }), 400

        service = get_service()
        rating_obj = service.rate_command(
            command_id=command_id,
            user_username=user_username,
            rating=rating,
            comment=comment
        )

        return jsonify({
            'success': True,
            'message': '評分已提交',
            'data': rating_obj.to_dict()
        }), 201

    except ValueError as e:
        logger.error(f"Rate command error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Rate command error: {e}", exc_info=True)
        return jsonify({'success': False, 'error': '伺服器錯誤'}), 500


@bp.route('/<int:command_id>/ratings', methods=['GET'])
def get_ratings(command_id: int):
    """取得指令的評分列表

    GET /api/cloud/shared_commands/<command_id>/ratings?limit=50&offset=0
    """
    try:
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)

        service = get_service()
        ratings = service.get_ratings(command_id, limit, offset)

        return jsonify({
            'success': True,
            'data': {
                'ratings': [r.to_dict() for r in ratings],
                'limit': limit,
                'offset': offset
            }
        }), 200

    except Exception as e:
        logger.error(f"Get ratings error: {e}", exc_info=True)
        return jsonify({'success': False, 'error': '伺服器錯誤'}), 500


@bp.route('/<int:command_id>/comments', methods=['GET', 'POST'])
def command_comments(command_id: int):
    """取得或新增指令留言

    GET /api/cloud/shared_commands/<command_id>/comments?limit=50&offset=0
    POST /api/cloud/shared_commands/<command_id>/comments
    {
        "user_username": "username",
        "content": "留言內容",
        "parent_comment_id": 1  # 可選，用於回覆
    }
    """
    try:
        service = get_service()

        if request.method == 'GET':
            limit = request.args.get('limit', 50, type=int)
            offset = request.args.get('offset', 0, type=int)

            comments = service.get_comments(command_id, limit, offset)

            return jsonify({
                'success': True,
                'data': {
                    'comments': [c.to_dict(include_replies=True) for c in comments],
                    'limit': limit,
                    'offset': offset
                }
            }), 200

        # POST method
        data = request.get_json()
        user_username = data.get('user_username')
        content = data.get('content')
        parent_comment_id = data.get('parent_comment_id')

        if not user_username or not content:
            return jsonify({
                'success': False,
                'error': '缺少必要欄位: user_username 或 content'
            }), 400

        comment = service.add_comment(
            command_id=command_id,
            user_username=user_username,
            content=content,
            parent_comment_id=parent_comment_id
        )

        return jsonify({
            'success': True,
            'message': '留言已提交',
            'data': comment.to_dict()
        }), 201

    except ValueError as e:
        logger.error(f"Command comments error: {e}")
        return jsonify({'success': False, 'error': '請求參數錯誤'}), 400
    except Exception as e:
        logger.error(f"Command comments error: {e}", exc_info=True)
        return jsonify({'success': False, 'error': '伺服器錯誤'}), 500


@bp.route('/featured', methods=['GET'])
def get_featured_commands():
    """取得精選指令

    GET /api/cloud/shared_commands/featured?limit=10
    """
    try:
        limit = request.args.get('limit', 10, type=int)

        service = get_service()
        commands = service.get_featured_commands(limit)

        return jsonify({
            'success': True,
            'data': {
                'commands': [cmd.to_dict() for cmd in commands]
            }
        }), 200

    except Exception as e:
        logger.error(f"Get featured commands error: {e}", exc_info=True)
        return jsonify({'success': False, 'error': '伺服器錯誤'}), 500


@bp.route('/popular', methods=['GET'])
def get_popular_commands():
    """取得熱門指令

    GET /api/cloud/shared_commands/popular?limit=10
    """
    try:
        limit = request.args.get('limit', 10, type=int)

        service = get_service()
        commands = service.get_popular_commands(limit)

        return jsonify({
            'success': True,
            'data': {
                'commands': [cmd.to_dict() for cmd in commands]
            }
        }), 200

    except Exception as e:
        logger.error(f"Get popular commands error: {e}", exc_info=True)
        return jsonify({'success': False, 'error': '伺服器錯誤'}), 500


@bp.route('/categories', methods=['GET'])
def get_categories():
    """取得所有分類及其指令數量

    GET /api/cloud/shared_commands/categories
    """
    try:
        service = get_service()
        categories = service.get_categories()

        return jsonify({
            'success': True,
            'data': {
                'categories': categories
            }
        }), 200

    except Exception as e:
        logger.error(f"Get categories error: {e}", exc_info=True)
        return jsonify({'success': False, 'error': '伺服器錯誤'}), 500
