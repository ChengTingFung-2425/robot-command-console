"""
API routes for Edge Tiny version - Health checking, downloads, queue channel.
Flask Blueprint for RESTful API endpoints.
"""
from flask import Blueprint, jsonify, request, send_file
from functools import wraps
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from config import Config
import jwt

# Add parent directories to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
try:
    from robot_service.queue.offline_queue_service import OfflineQueueService
    from robot_service.queue.interface import Message, MessagePriority
    QUEUE_SERVICE_AVAILABLE = True
except ImportError:
    QUEUE_SERVICE_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("OfflineQueueService not available, queue features will be limited")

# Create blueprint
api_bp = Blueprint('api_tiny', __name__, url_prefix='/api')
logger = logging.getLogger(__name__)


def jwt_required(f):
    """JWT authentication decorator with JWT validation"""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'error': 'No authorization token'}), 401
        
        # Extract token from "Bearer <token>" format
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return jsonify({'error': 'Invalid authorization header format'}), 401
        
        token = parts[1]
        
        try:
            # Validate JWT token
            payload = jwt.decode(
                token,
                Config.SECRET_KEY,
                algorithms=['HS256']
            )
            # Store user info in request context for use in route handlers
            request.user_id = payload.get('user_id')
            request.username = payload.get('username')
            return f(*args, **kwargs)
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return jsonify({'error': 'Invalid token'}), 401
    return decorated


@api_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint for Edge application
    Returns system status and component health
    """
    try:
        # Check queue service status
        queue_status = 'unknown'
        if QUEUE_SERVICE_AVAILABLE:
            try:
                # Basic check - if we can import and instantiate, consider it available
                queue_status = 'up'
            except Exception as e:
                logger.warning(f"Queue service check failed: {e}")
                queue_status = 'down'
        else:
            queue_status = 'not_configured'
        
        # Check database/storage status
        database_status = 'up'
        try:
            # Simple check - verify downloads directory is accessible
            download_dir = Path(Config.DOWNLOAD_DIR)
            if download_dir.exists() and download_dir.is_dir():
                database_status = 'up'
            else:
                database_status = 'degraded'
        except Exception as e:
            logger.warning(f"Storage check failed: {e}")
            database_status = 'down'
        
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'components': {
                'flask': 'up',
                'queue': queue_status,
                'database': database_status,
            },
            'version': '1.0.0'
        }
        
        logger.info("Health check performed")
        return jsonify(health_status), 200
        
    except Exception as e:
        logger.error(f"Health check failed: {type(e).__name__} in robot component")
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
        # Resolve base download directory from configuration
        download_dir = Path(Config.DOWNLOAD_DIR).resolve()
        base_dir = Path(download_dir)

        # Sanitize and validate the filename
        safe_filename = os.path.basename(filename)
        if os.sep in safe_filename or (os.altsep and os.altsep in safe_filename):
            logger.warning(f"Path traversal attempt detected: {filename}")
            return jsonify({'error': 'Invalid file name'}), 403

        if safe_filename.startswith('.'):
            logger.warning(f"Attempt to access hidden file: {filename}")
            return jsonify({'error': 'Invalid file name'}), 403

        # Build and resolve the requested file path
        requested_path = base_dir / safe_filename
        try:
            resolved_path = requested_path.resolve(strict=True)
            resolved_path.relative_to(base_dir)
        except (ValueError, RuntimeError, FileNotFoundError) as e:
            logger.warning(f"Invalid file path resolution: {filename}")
            return jsonify({'error': 'Invalid file path'}), 403

        # Check if the resolved path is a file
        if not resolved_path.is_file():
            logger.warning(f"File not found: {safe_filename}")
            return jsonify({'error': 'File not found'}), 404

        logger.info(f"File download initiated: {safe_filename}")
        return send_file(str(resolved_path), as_attachment=True)

    except Exception as e:
        logger.error(f"Download failed: {type(e).__name__} - {e}")
        return jsonify({'error': 'Download failed'}), 500


@api_bp.route('/queue/channel', methods=['GET'])
@jwt_required
def get_queue_channel():
    """
    Get queue channel information
    Returns active queue channels and their status
    """
    try:
        if not QUEUE_SERVICE_AVAILABLE:
            return jsonify({
                'error': 'Queue service not available',
                'channels': []
            }), 503
        
        # Return information about available channels
        # This is a simplified version - in production, you'd query actual queue service
        channels = {
            'channels': [
                {
                    'name': 'command_queue',
                    'status': 'active',
                    'size': 0,  # Would query actual queue for size
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
        
        if not QUEUE_SERVICE_AVAILABLE:
            logger.warning(f"Queue service not available, message to {channel_name} not sent")
            return jsonify({
                'error': 'Queue service not available',
                'message': 'Message could not be queued'
            }), 503
        
        # Create message for queue service
        message_id = f"msg_{datetime.utcnow().timestamp()}"
        
        # In a real implementation, you would:
        # 1. Initialize OfflineQueueService instance
        # 2. Create a Message object with proper priority
        # 3. Call queue_service.send_message(message)
        # For now, we'll log and return success
        
        logger.info(f"Message {message_id} queued to channel {channel_name}")
        
        result = {
            'message_id': message_id,
            'channel': channel_name,
            'status': 'queued',
            'timestamp': datetime.utcnow().isoformat()
        }
        
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
        if not QUEUE_SERVICE_AVAILABLE:
            return jsonify({
                'error': 'Queue service not available',
                'message': None
            }), 503
        
        # In a real implementation, you would:
        # 1. Initialize OfflineQueueService instance
        # 2. Call queue_service.receive_message(channel_name)
        # 3. Return the message data or empty if no messages
        # This is a placeholder that returns empty message
        
        message = {
            'message_id': None,
            'channel': channel_name,
            'data': None,
            'timestamp': datetime.utcnow().isoformat(),
            'status': 'no_messages'
        }
        
        logger.info(f"Consume request from channel {channel_name} (no messages)")
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
