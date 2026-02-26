"""
Firmware management routes for Edge Tiny version - SFTP and SSH for auto-exec.
Flask Blueprint for firmware upload, deployment, and remote execution.
"""
from flask import Blueprint, jsonify, request
from functools import wraps
import logging
from datetime import datetime
import paramiko
import os
import sys
import shlex
import json
import hashlib
from pathlib import Path
from typing import Optional
from werkzeug.utils import secure_filename, safe_join
import re

# Add parent directories to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
try:
    from config import Config
except ImportError:
    # Fallback if config not available
    class Config:
        SECRET_KEY = 'dev-secret-key'
        FIRMWARE_DIR = '/tmp/firmware'
        ROBOT_VARS_DIR = '/tmp/robot_vars'

try:
    import jwt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False

# Create blueprint
firmware_bp = Blueprint('firmware_tiny', __name__, url_prefix='/firmware')
logger = logging.getLogger(__name__)

# Global task tracking (in production, use Redis or database)
_deployment_tasks = {}


def _validate_and_sanitize_filename(filename: str) -> Optional[str]:
    """
    Validate and sanitize firmware filename using secure practices.
    
    Rules enforced:
    - Only one "." allowed (for extension)
    - No directory separators (/, \\)
    - Alphanumeric characters, dash, underscore, and one dot only
    - Use allowlist pattern validation
    
    Args:
        filename: Original filename from upload
    
    Returns:
        Sanitized filename if safe, None otherwise
    """
    if not filename:
        return None
    
    # First pass: use werkzeug's secure_filename
    safe_name = secure_filename(filename)
    if not safe_name or safe_name == '':
        return None
    
    # Second pass: enforce stricter rules
    # Rule 1: Only allow one dot (for extension)
    if safe_name.count('.') != 1:
        logger.warning(f"Filename has invalid dot count: {filename}")
        return None
    
    # Rule 2: No directory separators (already handled by secure_filename, but double-check)
    if '/' in safe_name or '\\' in safe_name:
        logger.warning(f"Filename contains directory separators: {filename}")
        return None
    
    # Rule 3: Use allowlist - alphanumeric, dash, underscore, single dot
    if not re.match(r'^[a-zA-Z0-9_-]+\.[a-zA-Z0-9]+$', safe_name):
        logger.warning(f"Filename doesn't match allowlist pattern: {filename}")
        return None
    
    # Rule 4: Prevent sequences like "..", even after replacement
    if '..' in safe_name or safe_name.startswith('.') or safe_name.endswith('.'):
        logger.warning(f"Filename contains dangerous sequences: {filename}")
        return None
    
    # Rule 5: Validate extension is in allowed list
    allowed_extensions = {'.bin', '.hex', '.fw', '.img'}
    file_ext = Path(safe_name).suffix.lower()
    if file_ext not in allowed_extensions:
        logger.warning(f"Filename has invalid extension: {filename}")
        return None
    
    return safe_name


def _validate_and_sanitize_identifier(identifier: str) -> Optional[str]:
    """
    Validate and sanitize identifier for safe use in file paths.
    Prevents path traversal attacks by rejecting dangerous characters.
    
    Args:
        identifier: String to validate (e.g., robot_id)
    
    Returns:
        Sanitized identifier if safe, None otherwise
    """
    if not identifier:
        return None
    
    # Only allow alphanumeric, dash, underscore
    if not re.match(r'^[a-zA-Z0-9_-]+$', identifier):
        return None
    
    # Reject path traversal attempts
    dangerous_patterns = ['..', '/', '\\', '\0']
    if any(pattern in identifier for pattern in dangerous_patterns):
        return None
    
    # Return sanitized identifier (already validated to be safe)
    return identifier


def _validate_remote_path(remote_path: str) -> Optional[str]:
    """
    Validate a remote SFTP path to prevent path traversal.

    Only allows Unix absolute paths composed of safe characters.
    Rejects paths containing '..', null bytes, or shell-special characters.

    Args:
        remote_path: The remote path string supplied by the caller.

    Returns:
        The original path if it is safe, None otherwise.
    """
    if not remote_path:
        return None

    # Must be an absolute path on the remote host
    if not remote_path.startswith('/'):
        logger.warning(f"Remote path is not absolute: {remote_path}")
        return None

    # Reject null bytes and path-traversal sequences
    if '\0' in remote_path or '..' in remote_path:
        logger.warning(f"Remote path contains dangerous sequence: {remote_path}")
        return None

    # Reject single-dot path components (e.g. /path/./etc) and hidden-entry tricks
    if '/.' in remote_path:
        logger.warning(f"Remote path contains dot-component: {remote_path}")
        return None

    # Allowlist: slash, alphanumeric, dash, underscore, dot (for file extensions / hidden dirs)
    if not re.match(r'^[a-zA-Z0-9/_.\-]+$', remote_path):
        logger.warning(f"Remote path contains unsafe characters: {remote_path}")
        return None

    # Final check: normalise and confirm no traversal survived
    normalised = os.path.normpath(remote_path)
    if '..' in normalised.split(os.sep):
        logger.warning(f"Remote path traversal detected after normalisation: {remote_path}")
        return None

    return remote_path


# Ensure firmware and vars directories exist
def _ensure_directories():
    """Ensure firmware and robot vars directories exist"""
    firmware_dir = getattr(Config, 'FIRMWARE_DIR', '/tmp/firmware')
    vars_dir = getattr(Config, 'ROBOT_VARS_DIR', '/tmp/robot_vars')
    
    Path(firmware_dir).mkdir(parents=True, exist_ok=True)
    Path(vars_dir).mkdir(parents=True, exist_ok=True)
    
    return firmware_dir, vars_dir


def _build_remote_firmware_path(safe_remote_path: str, local_firmware_path: str) -> str:
    """Construct the remote destination path for a firmware file.

    Args:
        safe_remote_path: Validated remote directory (from _validate_remote_path).
        local_firmware_path: Local firmware file path (basename is used).

    Returns:
        Full remote path string.
    """
    return safe_remote_path.rstrip('/') + '/' + os.path.basename(local_firmware_path)


def _get_firmware_metadata(firmware_path):
    """Get metadata for a firmware file"""
    try:
        stat = firmware_path.stat()
        
        # Calculate file hash (MD5 for file integrity check, not security)
        hash_md5 = hashlib.md5(usedforsecurity=False)
        with open(firmware_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        
        return {
            'id': firmware_path.stem,
            'filename': firmware_path.name,
            'version': firmware_path.stem,  # Could parse from filename
            'upload_date': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            'size': f"{stat.st_size / (1024 * 1024):.2f}MB",
            'size_bytes': stat.st_size,
            'checksum': hash_md5.hexdigest(),
            'status': 'available'
        }
    except Exception as e:
        logger.error(f"Failed to get metadata for {firmware_path}: {e}")
        return None


def admin_required(f):
    """Admin permission decorator with role check"""
    @wraps(f)
    def decorated(*args, **kwargs):
        # Check for admin role in JWT token or session
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return jsonify({'error': 'No authorization token'}), 401
        
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return jsonify({'error': 'Invalid authorization header format'}), 401
        
        token = parts[1]
        
        if not JWT_AVAILABLE:
            logger.warning("JWT not available, skipping admin check")
            return f(*args, **kwargs)
        
        try:
            # Decode and validate JWT token
            payload = jwt.decode(
                token,
                Config.SECRET_KEY,
                algorithms=['HS256']
            )
            
            # Check for admin role
            user_role = payload.get('role', 'user')
            is_admin = payload.get('is_admin', False)
            
            if user_role != 'admin' and not is_admin:
                return jsonify({'error': 'Admin permission required'}), 403
            
            # Store user info in request context
            request.user_id = payload.get('user_id')
            request.username = payload.get('username')
            request.is_admin = True
            
            return f(*args, **kwargs)
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token for admin check: {e}")
            return jsonify({'error': 'Invalid token'}), 401
    return decorated


def jwt_required(f):
    """JWT authentication decorator"""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'error': 'No authorization token'}), 401
        
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return jsonify({'error': 'Invalid authorization header format'}), 401
        
        token = parts[1]
        
        if not JWT_AVAILABLE:
            logger.warning("JWT not available, skipping token validation")
            return f(*args, **kwargs)
        
        try:
            payload = jwt.decode(
                token,
                Config.SECRET_KEY,
                algorithms=['HS256']
            )
            request.user_id = payload.get('user_id')
            request.username = payload.get('username')
            return f(*args, **kwargs)
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return jsonify({'error': 'Invalid token'}), 401
    return decorated


@firmware_bp.route('/', methods=['GET'])
@jwt_required
def list_firmware():
    """
    List available firmware versions from storage
    """
    try:
        firmware_dir, _ = _ensure_directories()
        firmware_path = Path(firmware_dir)
        
        # Scan directory for firmware files
        firmware_list = []
        for file_path in firmware_path.glob('*.bin'):
            metadata = _get_firmware_metadata(file_path)
            if metadata:
                firmware_list.append(metadata)
        
        # Also check for .hex, .fw, .img files
        for ext in ['*.hex', '*.fw', '*.img']:
            for file_path in firmware_path.glob(ext):
                metadata = _get_firmware_metadata(file_path)
                if metadata:
                    firmware_list.append(metadata)
        
        result = {
            'firmware': firmware_list,
            'count': len(firmware_list),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        logger.info(f"Listed {len(firmware_list)} firmware files")
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Failed to list firmware: {e}")
        return jsonify({'error': 'Failed to list firmware'}), 500


@firmware_bp.route('/upload', methods=['POST'])
@jwt_required
@admin_required
def upload_firmware():
    """
    Upload new firmware file with validation
    Admin only
    """
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Empty filename'}), 400
        
        # Validate and sanitize filename using strict validation
        safe_filename = _validate_and_sanitize_filename(file.filename)
        if not safe_filename:
            logger.warning(f"Invalid firmware filename rejected: {file.filename}")
            return jsonify({'error': 'Invalid filename format'}), 400
        
        firmware_dir, _ = _ensure_directories()
        
        # Generate unique firmware ID and use validated filename extension
        file_ext = Path(safe_filename).suffix.lower()
        firmware_id = f"fw_{int(datetime.utcnow().timestamp())}"
        final_filename = f"{firmware_id}{file_ext}"
        file_path = Path(firmware_dir) / final_filename
        
        # Save file
        file.save(str(file_path))
        
        # Validate file (check it's not empty and has reasonable size)
        file_size = file_path.stat().st_size
        if file_size == 0:
            file_path.unlink()
            return jsonify({'error': 'Empty file'}), 400
        
        # Calculate checksum (MD5 for file integrity, not security)
        hash_md5 = hashlib.md5(usedforsecurity=False)
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        
        result = {
            'firmware_id': firmware_id,
            'filename': final_filename,
            'original_filename': file.filename,
            'sanitized_filename': safe_filename,
            'size': f"{file_size / (1024 * 1024):.2f}MB",
            'size_bytes': file_size,
            'checksum': hash_md5.hexdigest(),
            'status': 'uploaded',
            'path': str(file_path),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        logger.info(f"Firmware uploaded: {firmware_id} ({file.filename})")
        return jsonify(result), 201
        
    except Exception as e:
        logger.error(f"Firmware upload failed: {e}")
        return jsonify({'error': 'Firmware upload failed'}), 500


@firmware_bp.route('/deploy/sftp', methods=['POST'])
@jwt_required
@admin_required
def deploy_via_sftp():
    """
    Deploy firmware to robot via SFTP
    
    Request body:
    {
        "robot_id": "robot_001",
        "firmware_id": "fw_001",
        "host": "192.168.1.100",
        "port": 22,
        "username": "robot",
        "password": "secret",  # or use key_file
        "remote_path": "/opt/firmware/"
    }
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        required = ['robot_id', 'firmware_id', 'host', 'username', 'remote_path']
        if not all(field in data for field in required):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Initialize SFTP connection
        transport = paramiko.Transport((data['host'], data.get('port', 22)))
        
        # Authentication
        if 'key_file' in data:
            private_key = paramiko.RSAKey.from_private_key_file(data['key_file'])
            transport.connect(username=data['username'], pkey=private_key)
        else:
            transport.connect(username=data['username'], password=data.get('password'))
        
        sftp = paramiko.SFTPClient.from_transport(transport)
        
        # Get actual firmware file path from storage
        firmware_dir, _ = _ensure_directories()
        firmware_path = Path(firmware_dir)
        
        # Validate firmware_id with strict allowlist (no path traversal via os.path.basename)
        safe_firmware_id = _validate_and_sanitize_identifier(data['firmware_id'])
        if not safe_firmware_id:
            sftp.close()
            transport.close()
            return jsonify({'error': 'Invalid firmware_id'}), 400
        
        # Find the firmware file (check multiple extensions)
        local_firmware_path = None
        for ext in ['.bin', '.hex', '.fw', '.img']:
            candidate = firmware_path / f"{safe_firmware_id}{ext}"
            if candidate.exists():
                local_firmware_path = str(candidate)
                break
        
        if not local_firmware_path:
            sftp.close()
            transport.close()
            return jsonify({'error': f'Firmware file not found: {safe_firmware_id}'}), 404
        
        # Validate remote_path before using it in path expression
        safe_remote_path = _validate_remote_path(data['remote_path'])
        if not safe_remote_path:
            sftp.close()
            transport.close()
            return jsonify({'error': 'Invalid remote_path'}), 400
        remote_firmware_path = _build_remote_firmware_path(safe_remote_path, local_firmware_path)
        
        # Upload firmware
        sftp.put(local_firmware_path, remote_firmware_path)
        
        sftp.close()
        transport.close()
        
        task_id = f"deploy_{int(datetime.utcnow().timestamp())}"
        
        result = {
            'task_id': task_id,
            'robot_id': data['robot_id'],
            'firmware_id': data['firmware_id'],
            'method': 'sftp',
            'status': 'uploaded',
            'remote_path': remote_firmware_path,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Store task status for tracking
        _deployment_tasks[task_id] = {
            'task_id': task_id,
            'status': 'completed',
            'progress': 100,
            'robot_id': data['robot_id'],
            'firmware_id': data['firmware_id'],
            'method': 'sftp',
            'timestamp': datetime.utcnow().isoformat()
        }
        
        logger.info(f"Firmware {data['firmware_id']} deployed via SFTP to {data['robot_id']}")
        return jsonify(result), 201
        
    except paramiko.AuthenticationException:
        logger.error("SFTP authentication failed")
        return jsonify({'error': 'Authentication failed'}), 401
    except paramiko.SSHException as e:
        logger.error(f"SFTP connection error: {e}")
        return jsonify({'error': 'SFTP connection failed'}), 500
    except Exception as e:
        logger.error(f"SFTP deployment failed: {e}")
        return jsonify({'error': 'SFTP deployment failed'}), 500


@firmware_bp.route('/deploy/ssh/exec', methods=['POST'])
@jwt_required
@admin_required
def deploy_and_execute_via_ssh():
    """
    Deploy firmware via SFTP and execute installation script via SSH
    Auto-exec workflow for unattended firmware updates
    
    Request body:
    {
        "robot_id": "robot_001",
        "firmware_id": "fw_001",
        "host": "192.168.1.100",
        "port": 22,
        "username": "robot",
        "password": "secret",  # or use key_file
        "remote_path": "/opt/firmware/",
        "install_script": "/opt/firmware/install.sh",
        "auto_reboot": false
    }
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        required = ['robot_id', 'firmware_id', 'host', 'username', 'remote_path', 'install_script']
        if not all(field in data for field in required):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Step 1: SFTP upload
        transport = paramiko.Transport((data['host'], data.get('port', 22)))
        
        if 'key_file' in data:
            private_key = paramiko.RSAKey.from_private_key_file(data['key_file'])
            transport.connect(username=data['username'], pkey=private_key)
        else:
            transport.connect(username=data['username'], password=data.get('password'))
        
        sftp = paramiko.SFTPClient.from_transport(transport)
        
        # Get actual firmware file path from storage
        firmware_dir, _ = _ensure_directories()
        firmware_path = Path(firmware_dir)
        
        # Validate firmware_id with strict allowlist (no path traversal via os.path.basename)
        safe_firmware_id = _validate_and_sanitize_identifier(data['firmware_id'])
        if not safe_firmware_id:
            sftp.close()
            transport.close()
            return jsonify({'error': 'Invalid firmware_id'}), 400
        
        # Find the firmware file (check multiple extensions)
        local_firmware_path = None
        for ext in ['.bin', '.hex', '.fw', '.img']:
            candidate = firmware_path / f"{safe_firmware_id}{ext}"
            if candidate.exists():
                local_firmware_path = str(candidate)
                break
        
        if not local_firmware_path:
            sftp.close()
            transport.close()
            return jsonify({'error': f'Firmware file not found: {safe_firmware_id}'}), 404
        
        # Validate remote_path before using it in path expression
        safe_remote_path = _validate_remote_path(data['remote_path'])
        if not safe_remote_path:
            sftp.close()
            transport.close()
            return jsonify({'error': 'Invalid remote_path'}), 400
        remote_firmware_path = _build_remote_firmware_path(safe_remote_path, local_firmware_path)
        sftp.put(local_firmware_path, remote_firmware_path)
        
        sftp.close()
        
        # Step 2: SSH execution
        ssh_client = paramiko.SSHClient()
        # Security: Reject unknown host keys instead of auto-accepting
        ssh_client.set_missing_host_key_policy(paramiko.RejectPolicy())
        
        if 'key_file' in data:
            private_key = paramiko.RSAKey.from_private_key_file(data['key_file'])
            ssh_client.connect(
                hostname=data['host'],
                port=data.get('port', 22),
                username=data['username'],
                pkey=private_key
            )
        else:
            ssh_client.connect(
                hostname=data['host'],
                port=data.get('port', 22),
                username=data['username'],
                password=data.get('password')
            )
        
        # Execute installation script
        # Security: Use shlex built-in command escaping
        install_script_safe = shlex.quote(data['install_script'])
        firmware_path_safe = shlex.quote(remote_firmware_path)
        install_cmd = f"{install_script_safe} {firmware_path_safe}"
        if data.get('auto_reboot'):
            install_cmd += " && sudo reboot"
        
        stdin, stdout, stderr = ssh_client.exec_command(install_cmd)
        
        # Get execution results
        exit_code = stdout.channel.recv_exit_status()
        output = stdout.read().decode('utf-8')
        error = stderr.read().decode('utf-8')
        
        ssh_client.close()
        transport.close()
        
        task_id = f"deploy_{int(datetime.utcnow().timestamp())}"
        
        task_status = 'completed' if exit_code == 0 else 'failed'
        
        result = {
            'task_id': task_id,
            'robot_id': data['robot_id'],
            'firmware_id': data['firmware_id'],
            'method': 'ssh_auto_exec',
            'status': task_status,
            'exit_code': exit_code,
            'output': output,
            'error': error if error else None,
            'remote_path': remote_firmware_path,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Store task status for tracking
        _deployment_tasks[task_id] = {
            'task_id': task_id,
            'status': task_status,
            'progress': 100,
            'robot_id': data['robot_id'],
            'firmware_id': data['firmware_id'],
            'method': 'ssh_auto_exec',
            'exit_code': exit_code,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        logger.info(f"Firmware {data['firmware_id']} deployed and executed on {data['robot_id']}")
        return jsonify(result), 201 if exit_code == 0 else 500
        
    except paramiko.AuthenticationException:
        logger.error("SSH authentication failed")
        return jsonify({'error': 'Authentication failed'}), 401
    except paramiko.SSHException as e:
        logger.error(f"SSH connection error: {e}")
        return jsonify({'error': 'SSH connection failed'}), 500
    except Exception as e:
        logger.error(f"SSH deployment failed: {e}")
        return jsonify({'error': 'SSH deployment failed'}), 500


@firmware_bp.route('/deploy/status/<task_id>', methods=['GET'])
@jwt_required
def get_deployment_status(task_id):
    """
    Get firmware deployment task status
    
    Args:
        task_id: Deployment task ID
    """
    try:
        # Get actual task status from tracking dictionary
        if task_id in _deployment_tasks:
            status_data = _deployment_tasks[task_id]
            logger.info(f"Retrieved status for task {task_id}")
            return jsonify(status_data), 200
        else:
            # Task not found - might have completed and been cleaned up
            status = {
                'task_id': task_id,
                'status': 'unknown',
                'message': 'Task not found or expired',
                'timestamp': datetime.utcnow().isoformat()
            }
            return jsonify(status), 404
        
    except Exception as e:
        logger.error(f"Failed to get deployment status: {e}")
        return jsonify({'error': 'Failed to get deployment status'}), 500


@firmware_bp.route('/robot/<robot_id>/vars', methods=['GET', 'POST'])
@jwt_required
def robot_variables(robot_id):
    """
    Get or set environment variables for robot
    Used to cast configuration to robot before firmware deployment
    
    GET: Retrieve current robot variables from storage
    POST: Set/update robot variables to storage
    
    Args:
        robot_id: Target robot identifier
    """
    # Validate and sanitize robot_id to prevent path traversal
    safe_robot_id = _validate_and_sanitize_identifier(robot_id)
    if not safe_robot_id:
        logger.warning(f"Invalid robot_id attempted: {robot_id}")
        return jsonify({'error': 'Invalid robot_id format'}), 400
    
    try:
        _, vars_dir = _ensure_directories()
        # Use werkzeug.safe_join to construct path and prevent traversal in one step
        safe_path = safe_join(vars_dir, f"{safe_robot_id}.json")
        if safe_path is None:
            logger.error(f"Path traversal attempt detected: {robot_id}")
            return jsonify({'error': 'Invalid robot_id'}), 400
        vars_file = Path(safe_path)

        if request.method == 'GET':
            # Get actual robot variables from storage
            if vars_file.exists():
                with open(vars_file, 'r') as f:
                    stored_vars = json.load(f)
                
                variables = {
                    'robot_id': safe_robot_id,
                    'variables': stored_vars.get('variables', {}),
                    'last_updated': stored_vars.get('last_updated'),
                    'timestamp': datetime.utcnow().isoformat()
                }
            else:
                # Return empty variables if no file exists
                variables = {
                    'robot_id': safe_robot_id,
                    'variables': {},
                    'last_updated': None,
                    'timestamp': datetime.utcnow().isoformat()
                }
            
            logger.info(f"Retrieved variables for robot {safe_robot_id}")
            return jsonify(variables), 200
            
        elif request.method == 'POST':
            data = request.get_json()
            
            if not data or 'variables' not in data:
                return jsonify({'error': 'No variables provided'}), 400
            
            # Store variables for robot in JSON file
            storage_data = {
                'robot_id': safe_robot_id,
                'variables': data['variables'],
                'last_updated': datetime.utcnow().isoformat()
            }
            
            with open(vars_file, 'w') as f:
                json.dump(storage_data, f, indent=2)
            
            result = {
                'robot_id': safe_robot_id,
                'variables': data['variables'],
                'status': 'updated',
                'timestamp': datetime.utcnow().isoformat()
            }
            
            logger.info(f"Updated variables for robot {safe_robot_id}")
            return jsonify(result), 200
            
    except Exception as e:
        logger.error(f"Failed to manage variables for robot {safe_robot_id}: {e}")
        return jsonify({'error': 'Failed to manage robot variables'}), 500


@firmware_bp.route('/robot/<robot_id>/vars/cast', methods=['POST'])
@jwt_required
@admin_required
def cast_variables_to_robot(robot_id):
    """
    Cast (apply) environment variables to robot via SSH
    Writes variables to robot's environment configuration
    
    Request body:
    {
        "host": "192.168.1.100",
        "port": 22,
        "username": "robot",
        "password": "secret",  # or use key_file
        "variables": {
            "VAR_NAME": "value",
            ...
        },
        "config_file": "/etc/robot/config.env",  # Target config file
        "reload_service": "robot.service"  # Optional: service to reload after update
    }
    """
    # Validate and sanitize robot_id to prevent path traversal
    safe_robot_id = _validate_and_sanitize_identifier(robot_id)
    if not safe_robot_id:
        logger.warning(f"Invalid robot_id attempted in cast: {robot_id}")
        return jsonify({'error': 'Invalid robot_id format'}), 400
    
    try:
        data = request.get_json()
        
        # Validate required fields
        required = ['host', 'username', 'variables', 'config_file']
        if not all(field in data for field in required):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Initialize SSH connection
        ssh_client = paramiko.SSHClient()
        # Security: Reject unknown host keys instead of auto-accepting
        ssh_client.set_missing_host_key_policy(paramiko.RejectPolicy())
        
        if 'key_file' in data:
            private_key = paramiko.RSAKey.from_private_key_file(data['key_file'])
            ssh_client.connect(
                hostname=data['host'],
                port=data.get('port', 22),
                username=data['username'],
                pkey=private_key
            )
        else:
            ssh_client.connect(
                hostname=data['host'],
                port=data.get('port', 22),
                username=data['username'],
                password=data.get('password')
            )
        
        # Build variable export commands
        var_commands = []
        for key, value in data['variables'].items():
            # Validate variable name (alphanumeric and underscore only)
            if not key.replace('_', '').isalnum():
                ssh_client.close()
                return jsonify({'error': f'Invalid variable name: {key}'}), 400
            # Safely quote the value
            safe_value = shlex.quote(str(value))
            var_commands.append(f'export {key}={safe_value}')
        
        # Create backup of existing config (safely quote config_file path)
        config_file_safe = shlex.quote(data['config_file'])
        backup_cmd = f"sudo cp {config_file_safe} {config_file_safe}.backup"
        stdin, stdout, stderr = ssh_client.exec_command(backup_cmd)
        stdout.channel.recv_exit_status()
        
        # Write variables to config file (using safe quoting)
        config_content = '\n'.join(var_commands)
        config_content_safe = shlex.quote(config_content)
        write_cmd = f"echo {config_content_safe} | sudo tee {config_file_safe}"
        stdin, stdout, stderr = ssh_client.exec_command(write_cmd)
        write_exit_code = stdout.channel.recv_exit_status()
        
        if write_exit_code != 0:
            error_output = stderr.read().decode('utf-8')
            ssh_client.close()
            return jsonify({
                'error': 'Failed to write variables',
                'details': error_output
            }), 500
        
        # Optionally reload service
        reload_output = None
        if 'reload_service' in data:
            service_name_safe = shlex.quote(data['reload_service'])
            reload_cmd = f"sudo systemctl reload {service_name_safe}"
            stdin, stdout, stderr = ssh_client.exec_command(reload_cmd)
            reload_exit_code = stdout.channel.recv_exit_status()
            reload_output = {
                'exit_code': reload_exit_code,
                'output': stdout.read().decode('utf-8'),
                'error': stderr.read().decode('utf-8') if reload_exit_code != 0 else None
            }
        
        ssh_client.close()
        
        result = {
            'robot_id': robot_id,
            'status': 'casted',
            'variables_count': len(data['variables']),
            'config_file': data['config_file'],
            'backup_created': True,
            'service_reloaded': reload_output is not None,
            'reload_status': reload_output,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        logger.info(f"Variables casted to robot {robot_id} at {data['host']}")
        return jsonify(result), 200
        
    except paramiko.AuthenticationException:
        logger.error("SSH authentication failed")
        return jsonify({'error': 'Authentication failed'}), 401
    except paramiko.SSHException as e:
        logger.error(f"SSH connection error: {e}")
        return jsonify({'error': 'SSH connection failed'}), 500
    except Exception as e:
        logger.error(f"Failed to cast variables to robot {robot_id}: {e}")
        return jsonify({'error': 'Failed to cast variables to robot'}), 500


# Error handlers
@firmware_bp.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404


@firmware_bp.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500
