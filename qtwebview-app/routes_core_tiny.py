"""
Core routes for Tiny WebUI version
Includes: Home, Dashboard, Robots, Commands (basic execution)
"""

import json
import logging
import requests
from flask import Blueprint, jsonify, request, render_template, redirect, url_for, flash
from flask_login import current_user, login_required
from WebUI.app import db
from WebUI.app.models import Robot, Command

bp_core = Blueprint('core', __name__)
logger = logging.getLogger(__name__)


# ==================== Home ====================

@bp_core.route('/', methods=['GET', 'POST'])
def home():
    """首頁"""
    if request.method == 'POST':
        pass
    return render_template('home.html.j2')


# ==================== Dashboard ====================

@bp_core.route('/dashboard', methods=['GET'])
@login_required
def dashboard():
    """儀表板 - 顯示機器人狀態與快速操作"""
    robots = Robot.query.all()
    return render_template('dashboard.html.j2', robots=robots)


# ==================== Robots ====================

@bp_core.route('/robots', methods=['GET'])
@login_required
def robots():
    """機器人列表"""
    robots = Robot.query.all()
    return render_template('robots.html.j2', robots=robots)


@bp_core.route('/media_stream', methods=['GET'])
@bp_core.route('/media_stream/<int:robot_id>', methods=['GET'])
@login_required
def media_stream(robot_id=None):
    """媒體串流頁面"""
    if robot_id:
        robot = Robot.query.get_or_404(robot_id)
        return render_template('media_stream.html.j2', robot=robot)
    robots = Robot.query.all()
    return render_template('media_stream.html.j2', robots=robots)


# ==================== Commands ====================

@bp_core.route('/commands', methods=['POST'])
@login_required
def commands():
    """執行基本指令"""
    try:
        data = request.get_json()
        robot_id = data.get('robot_id')
        action = data.get('action')
        
        if not robot_id or not action:
            return jsonify({'error': '缺少必要參數'}), 400
        
        robot = Robot.query.get(robot_id)
        if not robot:
            return jsonify({'error': '機器人不存在'}), 404
        
        # 建立指令記錄
        command = Command(
            robot_id=robot_id,
            action=action,
            parameters=json.dumps(data.get('parameters', {})),
            user_id=current_user.id
        )
        db.session.add(command)
        db.session.commit()
        
        # 發送指令到 Robot-Console
        try:
            response = requests.post(
                f'{robot.endpoint}/execute',
                json={'action': action, 'parameters': data.get('parameters', {})},
                timeout=5
            )
            command.status = 'success' if response.ok else 'failed'
            command.result = response.text
        except Exception as e:
            command.status = 'failed'
            command.result = str(e)
            logger.error(f'Failed to send command to robot {robot_id}: {e}')
        
        db.session.commit()
        
        return jsonify({
            'command_id': command.id,
            'status': command.status,
            'result': command.result
        })
    
    except Exception as e:
        # Log detailed error information on the server, but return a generic message to the client
        logger.error(f'Command execution error: {e}', exc_info=True)
        return jsonify({'error': '指令執行發生內部錯誤'}), 500


@bp_core.route('/commands/<int:cmd_id>', methods=['GET'])
@login_required
def get_command(cmd_id):
    """查詢指令狀態"""
    command = Command.query.get_or_404(cmd_id)
    
    # 檢查權限
    if command.user_id != current_user.id and not current_user.is_admin():
        return jsonify({'error': '無權限查看此指令'}), 403
    
    return jsonify({
        'id': command.id,
        'robot_id': command.robot_id,
        'action': command.action,
        'parameters': json.loads(command.parameters) if command.parameters else {},
        'status': command.status,
        'result': command.result,
        'timestamp': command.timestamp.isoformat() if command.timestamp else None
    })


# ==================== Health Check ====================

@bp_core.route('/health', methods=['GET'])
def health():
    """健康檢查端點"""
    return jsonify({'status': 'healthy', 'service': 'webui-tiny-core'}), 200
