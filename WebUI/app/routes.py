

# imports
from flask import Blueprint, jsonify, request
from WebUI.app import db
from WebUI.app.models import Robot, Command

# blueprint
bp = Blueprint('webui', __name__)

# functions
@bp.route('/robots', methods=['GET'])
def list_robots():
    """列出所有機器人"""
    robots = Robot.query.all()
    return jsonify([{'id': r.id, 'name': r.name, 'type': r.type, 'status': r.status} for r in robots])

@bp.route('/commands', methods=['POST'])
def send_command():
    """發送指令給指定機器人"""
    data = request.get_json()
    robot_id = data.get('robot_id')
    command = data.get('command')
    cmd = Command(robot_id=robot_id, command=command, status='pending')
    db.session.add(cmd)
    db.session.commit()
    return jsonify({'result': 'ok', 'command_id': cmd.id})

@bp.route('/commands/<int:cmd_id>', methods=['GET'])
def get_command_status(cmd_id):
    """查詢指令執行狀態"""
    cmd = Command.query.get_or_404(cmd_id)
    return jsonify({'id': cmd.id, 'robot_id': cmd.robot_id, 'command': cmd.command, 'status': cmd.status})
