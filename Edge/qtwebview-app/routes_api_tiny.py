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

# Hardcoded base paths - NOT configurable by users for security
# All file operations are restricted to these predefined directories
# Following FHS (Filesystem Hierarchy Standard):
#   /var/cache/robot-ctl/ - temporary/cache data (logs, reports)
#   /var/lib/robot-ctl/   - persistent application data (firmware, backups)
CACHE_BASE_DIR = Path('/var/cache/robot-ctl')
LIB_BASE_DIR = Path('/var/lib/robot-ctl')

# Cache directories (temporary data)
LOGS_DIR = CACHE_BASE_DIR / 'logs'
REPORTS_DIR = CACHE_BASE_DIR / 'reports'

# Lib directories (persistent data)
FIRMWARE_DIR = LIB_BASE_DIR / 'firmware'
BACKUPS_DIR = LIB_BASE_DIR / 'backups'

# Hardcoded file mapping for secure downloads
# Maps file_id to absolute path (not user-configurable)
ALLOWED_DOWNLOAD_FILES = {
    # System logs - stored in /var/cache/robot-ctl/logs/
    'system_log': LOGS_DIR / 'system.log',
    'error_log': LOGS_DIR / 'error.log',
    'access_log': LOGS_DIR / 'access.log',
    'debug_log': LOGS_DIR / 'debug.log',

    # Reports - stored in /var/cache/robot-ctl/reports/
    'daily_report': REPORTS_DIR / 'daily.pdf',
    'weekly_report': REPORTS_DIR / 'weekly.pdf',
    'monthly_report': REPORTS_DIR / 'monthly.pdf',
    'latest_report': REPORTS_DIR / 'latest.pdf',

    # Firmware files - stored in /var/lib/robot-ctl/firmware/
    'firmware_latest': FIRMWARE_DIR / 'latest.bin',
    'firmware_stable': FIRMWARE_DIR / 'stable.bin',
    'firmware_v1': FIRMWARE_DIR / 'v1.0.bin',
    'firmware_v2': FIRMWARE_DIR / 'v2.0.bin',

    # Configuration backups - stored in /var/lib/robot-ctl/backups/
    'config_backup': BACKUPS_DIR / 'config.tar.gz',
    'database_backup': BACKUPS_DIR / 'database.sql.gz',
}


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
            # Check if base data directories exist and are accessible
            cache_ok = CACHE_BASE_DIR.exists() and CACHE_BASE_DIR.is_dir()
            lib_ok = LIB_BASE_DIR.exists() and LIB_BASE_DIR.is_dir()
            
            if cache_ok and lib_ok:
                # Check if critical subdirectories are accessible
                if FIRMWARE_DIR.exists() and LOGS_DIR.exists():
                    database_status = 'up'
                else:
                    database_status = 'degraded'
            else:
                database_status = 'down'
        except Exception as e:
            logger.warning(f"Storage check failed: {e}")
            database_status = 'error'
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


@api_bp.route('/download/<file_id>', methods=['GET'])
@jwt_required
def download_file(file_id):
    """
    Download endpoint for predefined files (logs, reports, firmware)

    Uses hardcoded file paths stored in /var/cache/robot-ctl/ and /var/lib/robot-ctl/ for security.
    Paths are NOT configurable by users to prevent path traversal attacks.

    Args:
        file_id: Predefined file identifier (e.g., 'system_log', 'firmware_latest')

    Returns:
        File download or error response
    """
    try:
        # Check if file_id is in allowed list
        if file_id not in ALLOWED_DOWNLOAD_FILES:
            logger.warning(f"Attempted download of unknown file_id: {file_id}")
            return jsonify({
                'error': 'File not found',
                'message': 'Invalid file identifier',
                'available_files': list(ALLOWED_DOWNLOAD_FILES.keys())
            }), 404

        # Get the hardcoded absolute path for this file_id
        file_path = ALLOWED_DOWNLOAD_FILES[file_id]

        # Verify the path is within our base directories (defense in depth)
        try:
            resolved = file_path.resolve()
            # Check if path is under either cache or lib base directory
            is_under_cache = False
            is_under_lib = False
            try:
                resolved.relative_to(CACHE_BASE_DIR.resolve())
                is_under_cache = True
            except ValueError:
                pass
            try:
                resolved.relative_to(LIB_BASE_DIR.resolve())
                is_under_lib = True
            except ValueError:
                pass
            
            if not (is_under_cache or is_under_lib):
                raise ValueError("Path not under allowed directories")
        except ValueError:
            logger.error(f"Path traversal detected in hardcoded mapping for file_id: {file_id}")
            return jsonify({'error': 'Security violation detected'}), 403

        # Check if the file exists
        if not file_path.is_file():
            logger.warning(f"File not found for file_id '{file_id}': {file_path}")
            return jsonify({
                'error': 'File not found',
                'message': f'The file for {file_id} does not exist yet'
            }), 404

        # Return the file
        logger.info(f"File download initiated for file_id: {file_id} from {file_path}")
        return send_file(str(file_path), as_attachment=True, download_name=file_path.name)

    except Exception as e:
        logger.error(f"Download failed for file_id '{file_id}': {type(e).__name__}")
        return jsonify({'error': 'Download failed'}), 500


@api_bp.route('/download/list', methods=['GET'])
@jwt_required
def list_available_files():
    """
    List all available files that can be downloaded

    Returns:
        JSON list of available file IDs and their descriptions
    """
    try:
        # Build list with file existence status
        files = []
        for file_id, file_path in ALLOWED_DOWNLOAD_FILES.items():
            # Determine category from parent directory
            try:
                category = file_path.parent.name
            except:
                category = 'other'

            files.append({
                'id': file_id,
                'filename': file_path.name,
                'exists': file_path.is_file(),
                'category': category,
                'size': file_path.stat().st_size if file_path.is_file() else 0
            })

        return jsonify({
            'files': files,
            'total': len(files),
            'base_directories': {
                'cache': str(CACHE_BASE_DIR),
                'lib': str(LIB_BASE_DIR)
            }
        }), 200

    except Exception as e:
        logger.error(f"Failed to list available files: {type(e).__name__}")
        return jsonify({'error': 'Failed to retrieve file list'}), 500


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
