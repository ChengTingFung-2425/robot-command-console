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
import shlex

# Create blueprint
firmware_bp = Blueprint('firmware_tiny', __name__, url_prefix='/firmware')
logger = logging.getLogger(__name__)


def admin_required(f):
    """Admin permission decorator"""
    @wraps(f)
    def decorated(*args, **kwargs):
        # TODO: Implement actual admin check
        return f(*args, **kwargs)
    return decorated


def jwt_required(f):
    """JWT authentication decorator"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'No authorization token'}), 401
        return f(*args, **kwargs)
    return decorated


@firmware_bp.route('/', methods=['GET'])
@jwt_required
def list_firmware():
    """
    List available firmware versions
    """
    try:
        # TODO: Get actual firmware list from storage
        firmware_list = {
            'firmware': [
                {
                    'id': 'fw_001',
                    'version': '1.0.0',
                    'upload_date': '2025-01-01T00:00:00Z',
                    'size': '10MB',
                    'status': 'available'
                }
            ],
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return jsonify(firmware_list), 200
        
    except Exception as e:
        logger.error(f"Failed to list firmware: {e}")
        return jsonify({'error': 'Failed to list firmware'}), 500


@firmware_bp.route('/upload', methods=['POST'])
@jwt_required
@admin_required
def upload_firmware():
    """
    Upload new firmware file
    Admin only
    """
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Empty filename'}), 400
        
        # TODO: Implement actual file upload and validation
        firmware_id = f"fw_{datetime.utcnow().timestamp()}"
        
        result = {
            'firmware_id': firmware_id,
            'filename': file.filename,
            'status': 'uploaded',
            'timestamp': datetime.utcnow().isoformat()
        }
        
        logger.info(f"Firmware uploaded: {firmware_id}")
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
        
        # TODO: Get actual firmware file path
        # Sanitize firmware_id to prevent path traversal
        safe_firmware_id = os.path.basename(data['firmware_id'])
        local_firmware_path = f"/tmp/firmware/{safe_firmware_id}.bin"
        remote_firmware_path = os.path.join(data['remote_path'], f"{safe_firmware_id}.bin")
        
        # Upload firmware
        sftp.put(local_firmware_path, remote_firmware_path)
        
        sftp.close()
        transport.close()
        
        task_id = f"deploy_{datetime.utcnow().timestamp()}"
        
        result = {
            'task_id': task_id,
            'robot_id': data['robot_id'],
            'firmware_id': data['firmware_id'],
            'method': 'sftp',
            'status': 'uploaded',
            'remote_path': remote_firmware_path,
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
        
        # Upload firmware
        # Sanitize firmware_id to prevent path traversal
        safe_firmware_id = os.path.basename(data['firmware_id'])
        local_firmware_path = f"/tmp/firmware/{safe_firmware_id}.bin"
        remote_firmware_path = os.path.join(data['remote_path'], f"{safe_firmware_id}.bin")
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
        
        task_id = f"deploy_{datetime.utcnow().timestamp()}"
        
        result = {
            'task_id': task_id,
            'robot_id': data['robot_id'],
            'firmware_id': data['firmware_id'],
            'method': 'ssh_auto_exec',
            'status': 'completed' if exit_code == 0 else 'failed',
            'exit_code': exit_code,
            'output': output,
            'error': error if error else None,
            'remote_path': remote_firmware_path,
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
        # TODO: Implement actual task status tracking
        status = {
            'task_id': task_id,
            'status': 'completed',
            'progress': 100,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return jsonify(status), 200
        
    except Exception as e:
        logger.error(f"Failed to get deployment status: {e}")
        return jsonify({'error': 'Failed to get deployment status'}), 500


@firmware_bp.route('/robot/<robot_id>/vars', methods=['GET', 'POST'])
@jwt_required
def robot_variables(robot_id):
    """
    Get or set environment variables for robot
    Used to cast configuration to robot before firmware deployment
    
    GET: Retrieve current robot variables
    POST: Set/update robot variables
    
    Args:
        robot_id: Target robot identifier
    """
    try:
        if request.method == 'GET':
            # TODO: Get actual robot variables from storage/cache
            variables = {
                'robot_id': robot_id,
                'variables': {
                    'FIRMWARE_VERSION': '1.0.0',
                    'CONFIG_MODE': 'production',
                    'LOG_LEVEL': 'INFO',
                    'NETWORK_INTERFACE': 'eth0'
                },
                'timestamp': datetime.utcnow().isoformat()
            }
            
            logger.info(f"Retrieved variables for robot {robot_id}")
            return jsonify(variables), 200
            
        elif request.method == 'POST':
            data = request.get_json()
            
            if not data or 'variables' not in data:
                return jsonify({'error': 'No variables provided'}), 400
            
            # TODO: Store variables for robot
            result = {
                'robot_id': robot_id,
                'variables': data['variables'],
                'status': 'updated',
                'timestamp': datetime.utcnow().isoformat()
            }
            
            logger.info(f"Updated variables for robot {robot_id}")
            return jsonify(result), 200
            
    except Exception as e:
        logger.error(f"Failed to manage variables for robot {robot_id}: {e}")
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
