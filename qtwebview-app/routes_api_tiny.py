"""
API routes for Edge Tiny version - Health checking, downloads, queue channel.
Flask Blueprint for RESTful API endpoints.
"""
from flask import Blueprint, jsonify, request, send_file
from functools import wraps
import logging
import os
from datetime import datetime
from pathlib import Path

# Create blueprint
api_bp = Blueprint('api_tiny', __name__, url_prefix='/api')
logger = logging.getLogger(__name__)


def jwt_required(f):
    """JWT authentication decorator"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'No authorization token'}), 401
        # TODO: Implement JWT validation
        return f(*args, **kwargs)
    return decorated


@api_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint for Edge application
    Returns system status and component health
    """
    try:
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'components': {
                'flask': 'up',
                'queue': 'up',  # TODO: Check actual queue status
                'database': 'up',  # TODO: Check actual DB status
            },
            'version': '1.0.0'
        }
        
        logger.info("Health check performed")
        return jsonify(health_status), 200
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': '健康檢查失敗',
            'timestamp': datetime.utcnow().isoformat()
        }), 503


@api_bp.route('/download/<path:filename>', methods=['GET'])
@jwt_required
def download_file(filename):
    """
    Download endpoint for files (logs, reports, firmware)
    
    Args:
        filename: File path to download
    """
    try:
        # Security: Sanitize filename to prevent directory traversal
        # Use os.path.basename to get only the filename without path
        safe_filename = os.path.basename(filename)
        
        # Additional validation: ensure safe_filename contains no path separators
        if os.sep in safe_filename or (os.altsep and os.altsep in safe_filename):
            logger.warning(f"Path traversal attempt detected (path separator found): {filename}")
            return jsonify({'error': '檔案名稱無效'}), 403
        
        # Validate filename doesn't start with dot (hidden files)
        if safe_filename.startswith('.'):
            logger.warning(f"Attempt to access hidden file: {filename}")
            return jsonify({'error': '檔案名稱無效'}), 403
        
        # Resolve base download directory
        download_dir = os.getenv('DOWNLOAD_DIR', '/tmp/downloads')
        base_dir = Path(download_dir).resolve()
        
        # Build path using validated filename only
        requested_path = base_dir / safe_filename
        
        # Resolve and verify the path is within base_dir (defense in depth)
        try:
            resolved_path = requested_path.resolve()
            # CRITICAL: Verify resolved path is still within base_dir
            resolved_path.relative_to(base_dir)
        except (ValueError, RuntimeError) as e:
            logger.warning(f"Path traversal attempt detected during resolution: {filename}")
            return jsonify({'error': '檔案路徑無效'}), 403

        # Additional check: Ensure resolved path starts with base_dir (extra safety)
        if not str(resolved_path).startswith(str(base_dir)):
            logger.warning(f"Path traversal attempt: resolved path outside base_dir: {filename}")
            return jsonify({'error': '檔案路徑無效'}), 403

        if not resolved_path.is_file():
            logger.warning(f"File not found: {safe_filename}")
            return jsonify({'error': '檔案不存在'}), 404

        # Use the validated safe_filename with base_dir for final file access
        # This ensures we're always using the sanitized filename, not the resolved path
        final_path = base_dir / safe_filename
        logger.info(f"Downloading file: {safe_filename}")
        return send_file(str(final_path), as_attachment=True)
        
    except Exception as e:
        logger.error(f"Download failed: {e}")
        return jsonify({'error': '下載失敗'}), 500


@api_bp.route('/queue/channel', methods=['GET'])
@jwt_required
def get_queue_channel():
    """
    Get queue channel information
    Returns active queue channels and their status
    """
    try:
        # TODO: Integrate with actual queue service
        channels = {
            'channels': [
                {
                    'name': 'command_queue',
                    'status': 'active',
                    'size': 0,
                    'consumers': 1
                },
                {
                    'name': 'event_queue',
                    'status': 'active',
                    'size': 0,
                    'consumers': 1
                }
            ],
            'timestamp': datetime.utcnow().isoformat()
        }
        
        logger.info("Queue channel status retrieved")
        return jsonify(channels), 200
        
    except Exception as e:
        logger.error(f"Failed to get queue channels: {e}")
        return jsonify({'error': '獲取佇列通道狀態失敗'}), 500


@api_bp.route('/queue/channel/<channel_name>', methods=['POST'])
@jwt_required
def send_to_queue(channel_name):
    """
    Send message to specific queue channel
    
    Args:
        channel_name: Target queue channel name
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # TODO: Integrate with actual queue service
        message_id = f"msg_{datetime.utcnow().timestamp()}"
        
        result = {
            'message_id': message_id,
            'channel': channel_name,
            'status': 'queued',
            'timestamp': datetime.utcnow().isoformat()
        }
        
        logger.info(f"Message {message_id} sent to channel {channel_name}")
        return jsonify(result), 201
        
    except Exception as e:
        logger.error(f"Failed to send message to {channel_name}: {e}")
        return jsonify({'error': '發送訊息到佇列失敗'}), 500


@api_bp.route('/queue/channel/<channel_name>/consume', methods=['GET'])
@jwt_required
def consume_from_queue(channel_name):
    """
    Consume message from specific queue channel
    
    Args:
        channel_name: Source queue channel name
    """
    try:
        # TODO: Integrate with actual queue service
        # This is a placeholder for long-polling or SSE implementation
        
        message = {
            'message_id': f"msg_{datetime.utcnow().timestamp()}",
            'channel': channel_name,
            'data': {},
            'timestamp': datetime.utcnow().isoformat()
        }
        
        logger.info(f"Message consumed from channel {channel_name}")
        return jsonify(message), 200
        
    except Exception as e:
        logger.error(f"Failed to consume from {channel_name}: {e}")
        return jsonify({'error': '從佇列消費訊息失敗'}), 500


# Error handlers
@api_bp.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404


@api_bp.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500
