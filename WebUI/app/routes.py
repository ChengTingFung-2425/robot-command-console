
# imports
import re
from urllib.parse import quote as url_quote

from flask import Blueprint, jsonify, request, render_template, redirect, url_for, flash, session, abort
from flask_login import current_user, login_user, logout_user, login_required
from WebUI.app import db
from WebUI.app.models import Robot, Command, User, AdvancedCommand, UserProfile
from WebUI.app.forms import (
    LoginForm, RegisterForm, RegisterRobotForm,
    ResetPasswordRequestForm, ResetPasswordForm, AdvancedCommandForm
)
from WebUI.app.email import send_email
from WebUI.app.engagement import award_on_registration, get_or_create_user_profile
import json
import requests
import logging

# blueprint
bp = Blueprint('webui', __name__)

# functions


def send_password_reset_email(user, token):
    """發送密碼重設郵件"""
    send_email(
        subject='[Robot Console] 重設您的密碼',
        sender='noreply@robot-console.com',
        recipients=[user.email],
        text_body=render_template('email/reset_password.txt.j2', user=user, token=token),
        html_body=render_template('email/reset_password.html.j2', user=user, token=token)
    )

# 首頁


@bp.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        # 處理 POST 請求
        pass
    return render_template('home.html.j2')

# 用戶註冊


@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('webui.home'))
    form = RegisterForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.flush()  # Ensure user.id is generated
        
        # Create user profile with engagement metrics
        profile = UserProfile(user_id=user.id)
        db.session.add(profile)
        db.session.commit()
        
        # Award registration points
        award_on_registration(user.id)
        
        flash('註冊成功，請登入。')
        return redirect(url_for('webui.login'))
    return render_template('register.html.j2', form=form)

# 用戶登入


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('webui.home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('用戶名稱或密碼錯誤')
            return redirect(url_for('webui.login'))
        login_user(user, remember=form.remember_me.data)
        return redirect(url_for('webui.home'))
    return render_template('login.html.j2', form=form)

# 用戶登出


@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('webui.home'))

# 用戶檔案頁面


@bp.route('/user/<username>')
def user_profile(username):
    """Display user profile with engagement metrics and achievements."""
    user = User.query.filter_by(username=username).first_or_404()
    profile = get_or_create_user_profile(user)
    
    # Get user's earned achievements
    from WebUI.app.models import UserAchievement, Achievement
    user_achievements = db.session.query(Achievement).join(
        UserAchievement
    ).filter(
        UserAchievement.user_id == user.id
    ).all()
    
    return render_template(
        'user.html.j2',
        user=user,
        profile=profile,
        user_achievements=user_achievements
    )

# 編輯用戶檔案


@bp.route('/user/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """Edit current user's profile preferences."""
    if request.method == 'POST':
        current_user.ui_duration_unit = request.form.get('ui_duration_unit', 's')
        current_user.ui_verify_collapsed = request.form.get('ui_verify_collapsed', False) == 'on'
        db.session.commit()
        flash('檔案已更新。')
        return redirect(url_for('webui.user_profile', username=current_user.username))
    
    return render_template('edit_profile.html.j2')

# 排行榜


@bp.route('/leaderboard')
def leaderboard():
    """Display leaderboard of top users."""
    from WebUI.app.engagement import get_leaderboard
    
    sort_by = request.args.get('sort', 'points')
    limit = request.args.get('limit', 50, type=int)
    
    if sort_by not in ['points', 'level', 'reputation', 'commands']:
        sort_by = 'points'
    
    if limit > 100:
        limit = 100
    
    leaderboard_data = get_leaderboard(limit=limit, sort_by=sort_by)
    
    return render_template(
        'leaderboard.html.j2',
        leaderboard=leaderboard_data,
        sort_by=sort_by
    )

# 註冊機器人


@bp.route('/register_robot', methods=['GET', 'POST'])
@login_required
def register_robot():
    from WebUI.app.engagement import award_on_robot_registration
    form = RegisterRobotForm()
    if form.validate_on_submit():
        robot = Robot(name=form.name.data, type=form.type.data, owner=current_user)
        db.session.add(robot)
        db.session.commit()
        
        # Award points for robot registration
        award_on_robot_registration(current_user.id)
        
        flash('機器人註冊成功！')
        return redirect(url_for('webui.robot_dashboard'))
    return render_template('register_robot.html.j2', form=form)

# 儀表板頁面：顯示當前用戶的機器人


@bp.route('/dashboard', methods=['GET'])
@login_required
def robot_dashboard():
    robots = Robot.query.filter_by(owner=current_user).all()
    for r in robots:
        if not hasattr(r, 'capabilities'):
            r.capabilities = ['go_forward', 'turn_left', 'turn_right']
    return render_template('robot_dashboard.html.j2', robots=robots)

# API：查詢所有機器人（JSON）


@bp.route('/robots', methods=['GET'])
def list_robots():
    """列出所有機器人 (API)"""
    robots = Robot.query.all()
    return jsonify([
        {'id': r.id, 'name': r.name, 'type': r.type, 'status': r.status,
         'capabilities': getattr(r, 'capabilities', ['go_forward', 'turn_left', 'turn_right'])}
        for r in robots
    ])


# 媒體串流頁面
@bp.route('/media_stream', methods=['GET'])
@bp.route('/media_stream/<int:robot_id>', methods=['GET'])
@login_required
def media_stream(robot_id=None):
    """媒體串流頁面"""
    robots = Robot.query.filter_by(owner=current_user).all()
    robot = None
    if robot_id:
        robot = Robot.query.get_or_404(robot_id)
        # 確保用戶有權限存取此機器人
        if robot.owner != current_user:
            abort(403)
    elif robots:
        # 預設選擇第一個機器人
        robot = robots[0]
    
    return render_template('media_stream.html.j2', robots=robots, robot=robot)


# 指令下達（支援表單與 API）
@bp.route('/commands', methods=['POST'])
def send_command():
    """發送指令給指定機器人（API 或表單）"""
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form
    robot_id = data.get('robot_id')
    command = data.get('command')
    cmd = Command(robot_id=robot_id, command=command, status='pending')
    db.session.add(cmd)
    db.session.commit()
    # 若為表單提交則導回 dashboard
    if not request.is_json:
        return redirect(url_for('webui.robot_dashboard'))
    return jsonify({'result': 'ok', 'command_id': cmd.id})


# 查詢指令執行狀態
@bp.route('/commands/<int:cmd_id>', methods=['GET'])
def get_command_status(cmd_id):
    """查詢指令執行狀態"""
    cmd = Command.query.get_or_404(cmd_id)
    return jsonify({'id': cmd.id, 'robot_id': cmd.robot_id, 'command': cmd.command, 'status': cmd.status})


def expand_advanced_command(advanced_cmd):
    """展開進階指令為基礎動作列表
    
    Args:
        advanced_cmd: AdvancedCommand 模型實例
        
    Returns:
        list: 基礎動作名稱列表，例如 ['go_forward', 'turn_left', 'stand']
        
    Raises:
        ValueError: 如果指令格式無效或包含無效的動作
    """
    # 有效的基礎動作列表（與 Robot-Console/action_executor.py 同步）
    VALID_ACTIONS = {
        "back_fast", "bow", "chest", "dance_eight", "dance_five", "dance_four",
        "dance_nine", "dance_seven", "dance_six", "dance_ten", "dance_three", "dance_two",
        "go_forward", "kung_fu", "left_kick", "left_move_fast", "left_shot_fast",
        "left_uppercut", "push_ups", "right_kick", "right_move_fast", "right_shot_fast",
        "right_uppercut", "sit_ups", "squat", "squat_up", "stand", "stand_up_back",
        "stand_up_front", "stepping", "stop", "turn_left", "turn_right", "twist",
        "wave", "weightlifting", "wing_chun"
    }
    
    try:
        # 從資料庫載入進階指令的 base_commands
        base_commands_str = advanced_cmd.current_base_commands()
        commands = json.loads(base_commands_str)
        
        # 確認是陣列
        if not isinstance(commands, list):
            raise ValueError('指令序列必須是陣列格式')
        
        # 提取動作名稱並驗證
        actions = []
        for idx, cmd in enumerate(commands):
            if not isinstance(cmd, dict):
                raise ValueError(f'第 {idx + 1} 個指令格式錯誤：必須是物件')
            
            if 'command' not in cmd:
                raise ValueError(f'第 {idx + 1} 個指令缺少 "command" 欄位')
            
            action_name = cmd['command']
            
            # 跳過特殊指令如 'wait' 和 'advanced_command'
            if action_name in ['wait', 'advanced_command']:
                logging.warning(f'跳過特殊指令: {action_name}')
                continue
            
            # 驗證是否為有效的基礎動作
            if action_name not in VALID_ACTIONS:
                raise ValueError(f'第 {idx + 1} 個指令 "{action_name}" 不是有效的基礎動作')
            
            actions.append(action_name)
        
        return actions
        
    except json.JSONDecodeError as e:
        raise ValueError(f'JSON 格式錯誤：{str(e)}')
    except Exception as e:
        raise ValueError(f'展開進階指令時發生錯誤：{str(e)}')


def send_actions_to_robot(robot, actions):
    """發送動作列表到機器人的 Robot-Console 執行佇列
    
    Args:
        robot: Robot 模型實例
        actions: 基礎動作名稱列表
        
    Returns:
        dict: 包含結果的字典 {'success': bool, 'message': str, 'details': dict}
    """
    try:
        # 構建符合 Robot-Console pubsub.py 期望的新格式
        payload = {
            "actions": actions
        }
        
        # 記錄發送資訊
        logging.info(
            f"發送動作列表到機器人 {robot.name}: {actions}"
        )
        
        # 使用 MQTT 發送到機器人（選項 1：直接 MQTT 發布）
        try:
            from WebUI.app.mqtt_client import publish_to_robot
            
            # 嘗試透過 MQTT 發送
            mqtt_success = publish_to_robot(robot.name, payload)
            
            if mqtt_success:
                return {
                    'success': True,
                    'message': f'已透過 MQTT 發送 {len(actions)} 個動作到機器人 {robot.name}',
                    'details': {
                        'robot_id': robot.id,
                        'robot_name': robot.name,
                        'actions_count': len(actions),
                        'actions': actions,
                        'transport': 'MQTT'
                    }
                }
            else:
                # MQTT 發送失敗，記錄警告
                logging.warning("MQTT 發送失敗，可能是 MQTT 未啟用或連接失敗")
                
        except ImportError as e:
            logging.warning(f"無法導入 MQTT 客戶端模組: {str(e)}")
        except Exception as e:
            logging.warning(f"MQTT 發送時發生錯誤: {str(e)}")
        
        # 備用方案：如果 MQTT 不可用或失敗，只記錄到日誌
        # 這允許在沒有 MQTT 配置的環境中仍然可以測試其他功能
        logging.info(
            "備用方案：動作列表已記錄（MQTT 不可用），等待其他傳輸機制"
        )
        
        return {
            'success': True,
            'message': f'已接受 {len(actions)} 個動作到機器人 {robot.name}（等待傳輸）',
            'details': {
                'robot_id': robot.id,
                'robot_name': robot.name,
                'actions_count': len(actions),
                'actions': actions,
                'transport': 'pending'
            }
        }
        
    except Exception as e:
        logging.error(f'發送動作到機器人時發生錯誤: {str(e)}', exc_info=True)
        return {
            'success': False,
            'message': '發送失敗',
            'details': None
        }


# 執行進階指令：解碼並發送到 Robot-Console 佇列
@bp.route('/advanced_commands/<int:cmd_id>/execute', methods=['POST'])
@login_required
def execute_advanced_command(cmd_id):
    """執行進階指令：展開並發送到指定機器人的 Robot-Console 執行佇列
    
    Request Body (JSON):
        {
            "robot_id": 1  // 目標機器人 ID
        }
        
    Response:
        {
            "success": true,
            "message": "...",
            "command_id": 123,
            "details": {...}
        }
    """
    try:
        # 取得進階指令
        advanced_cmd = AdvancedCommand.query.get_or_404(cmd_id)
        
        # 權限檢查：只有 approved 的指令可以執行
        if advanced_cmd.status != 'approved':
            return jsonify({
                'success': False,
                'message': f'只能執行已批准的進階指令（當前狀態：{advanced_cmd.status}）'
            }), 403
        
        # 取得請求資料
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form
        
        robot_id = data.get('robot_id')
        if not robot_id:
            return jsonify({
                'success': False,
                'message': '缺少必要參數：robot_id'
            }), 400
        
        # 取得機器人
        robot = Robot.query.get_or_404(robot_id)
        
        # 權限檢查：確認用戶擁有該機器人
        if robot.owner != current_user and not current_user.is_admin():
            return jsonify({
                'success': False,
                'message': '您沒有權限控制此機器人'
            }), 403
        
        # 展開進階指令為基礎動作列表
        try:
            actions = expand_advanced_command(advanced_cmd)
        except ValueError as e:
            # 記錄詳細錯誤到日誌，但只返回通用訊息給用戶
            logging.warning(f'展開進階指令失敗: {str(e)}')
            return jsonify({
                'success': False,
                'message': '展開進階指令失敗，請檢查指令格式是否正確'
            }), 400
        
        # 發送動作到機器人
        result = send_actions_to_robot(robot, actions)
        
        # 記錄到資料庫（建立 Command 記錄）
        cmd_record = Command(
            robot_id=robot.id,
            command=f'advanced:{advanced_cmd.name}',
            status='sent' if result['success'] else 'failed',
            nested_command=True
        )
        db.session.add(cmd_record)
        db.session.commit()
        
        # 返回結果
        if result['success']:
            response = {
                'success': True,
                'message': result['message'],
                'command_id': cmd_record.id,
                'details': result.get('details')
            }
            return jsonify(response), 200
        else:
            # 發送失敗時只返回通用錯誤訊息，詳細錯誤已記錄到日誌
            logging.warning(f'發送指令到機器人失敗: {result["message"]}')
            response = {
                'success': False,
                'message': '發送指令到機器人失敗，請稍後再試',
                'command_id': cmd_record.id
            }
            return jsonify(response), 500
        
    except Exception as e:
        # 記錄詳細錯誤到日誌（包含堆疊追蹤），但只返回通用訊息給用戶
        logging.error(f'執行進階指令時發生錯誤: {str(e)}', exc_info=True)
        return jsonify({
            'success': False,
            'message': '執行指令時發生內部錯誤，請聯繫管理員'
        }), 500


# 密碼重設請求
@bp.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('webui.home'))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            token = user.get_reset_password_token()
            send_password_reset_email(user, token)
            flash('密碼重設郵件已發送至您的信箱，請查收。')
        else:
            flash('該電子郵件尚未註冊。')
        return redirect(url_for('webui.login'))
    return render_template('reset_password_request.html.j2', form=form)

# 密碼重設


@bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('webui.home'))
    user = User.verify_reset_password_token(token)
    if not user:
        flash('無效或過期的重設連結。')
        return redirect(url_for('webui.login'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('您的密碼已重設成功，請登入。')
        return redirect(url_for('webui.login'))
    return render_template('reset_password.html.j2', form=form)

# 進階指令分享區


@bp.route('/advanced_commands', methods=['GET'])
def advanced_commands():
    # 獲取篩選參數（從 URL 查詢字串或 session）
    filter_status = request.args.get('status', session.get('cmd_filter_status', 'all'))
    sort_by = request.args.get('sort', session.get('cmd_sort_by', 'created_at'))
    sort_order = request.args.get('order', session.get('cmd_sort_order', 'desc'))
    author_filter = request.args.get('author', session.get('cmd_filter_author', None))

    # 儲存篩選設定到 session
    session['cmd_filter_status'] = filter_status
    session['cmd_sort_by'] = sort_by
    session['cmd_sort_order'] = sort_order
    session['cmd_filter_author'] = author_filter

    # 基礎查詢
    query = AdvancedCommand.query

    # 權限與狀態篩選
    if filter_status != 'all':
        query = query.filter_by(status=filter_status)
    if author_filter:
        try:
            af = int(author_filter)
            query = query.filter_by(author_id=af)
        except Exception:
            pass

    # 排序
    if sort_by == 'name':
        sort_column = AdvancedCommand.name
    elif sort_by == 'category':
        sort_column = AdvancedCommand.category
    elif sort_by == 'author':
        sort_column = AdvancedCommand.author_id
    elif sort_by == 'updated_at':
        sort_column = AdvancedCommand.updated_at
    else:  # created_at (預設)
        sort_column = AdvancedCommand.created_at

    if sort_order == 'asc':
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    commands = query.all()

    # Build approved map: name -> content for latest approved versions
    approved = {}
    for c in AdvancedCommand.query.filter_by(status='approved').all():
        v = c.latest_version()
        if v and v.adv_command:
            approved[c.name] = v.adv_command.content

    return render_template(
        'advanced_commands.html.j2',
        commands=commands,
        filter_status=filter_status,
        sort_by=sort_by,
        sort_order=sort_order,
        author_filter=author_filter,
        approved_adv_command_map=approved
    )

# 建立進階指令


@bp.route('/advanced_commands/create', methods=['GET', 'POST'])
@login_required
def create_advanced_command():
    form = AdvancedCommandForm()
    if form.validate_on_submit():
        # Create metadata row first
        cmd = AdvancedCommand(
            name=form.name.data,
            description=form.description.data,
            category=form.category.data,
            base_commands=form.base_commands.data,
            version=form.version.data or 1,
            author=current_user
        )
        db.session.add(cmd)
        db.session.commit()  # ensure cmd.id exists before creating version

        # Create canonical AdvCommand + AdvancedCommandVersion and sync legacy fields
        try:
            cmd.add_version(content=form.base_commands.data, status='pending', bump=False)
            db.session.commit()
            flash('進階指令已提交，等待審核。')
        except Exception:
            db.session.rollback()
            flash('建立進階指令時發生錯誤。')
        return redirect(url_for('webui.advanced_commands'))
    # Server-side initial UI preferences and verified advanced commands list
    duration_unit = session.get('duration_unit', 's')
    verify_collapsed = session.get('verify_collapsed', False)
    # Provide server-side list of approved advanced commands (names) for client-side validation
    try:
        verified_cmds = [ac.name for ac in AdvancedCommand.query.filter_by(status='approved').all()]
    except Exception:
        verified_cmds = []

    return render_template(
        'create_advanced_command.html.j2',
        form=form,
        duration_unit=duration_unit,
        verify_collapsed=verify_collapsed,
        verified_advanced_commands=verified_cmds,
        editing=False
    )


# API: 更新使用者 UI 偏好（持久化到 session 與用戶資料）
@bp.route('/settings/ui', methods=['POST'])
@login_required
def update_ui_settings():
    data = request.get_json() or request.form
    duration_unit = data.get('duration_unit')
    verify_collapsed = data.get('verify_collapsed')
    # 更新 session
    if duration_unit in ('s', 'ms'):
        session['duration_unit'] = duration_unit
        try:
            current_user.ui_duration_unit = duration_unit
        except Exception:
            pass
    if verify_collapsed is not None:
        # expect '1'/'0' or true/false
        val = str(verify_collapsed) in ('1', 'true', 'True', 'yes')
        session['verify_collapsed'] = val
        try:
            current_user.ui_verify_collapsed = val
        except Exception:
            pass
    # try to persist user changes
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
    return jsonify({'result': 'ok'})


# 編輯進階指令：允許作者或管理員編輯自己的指令
@bp.route('/advanced_commands/edit/<int:cmd_id>', methods=['GET', 'POST'])
@login_required
def edit_advanced_command(cmd_id):
    cmd = AdvancedCommand.query.get_or_404(cmd_id)
    # 權限檢查：作者本人或 admin/auditor
    if not (current_user.is_admin() or cmd.author_id == current_user.id):
        # Return 403 Forbidden for unauthorized edit attempts (tests expect non-200)
        abort(403)
    form = AdvancedCommandForm(obj=cmd)
    if form.validate_on_submit():
        # compute change summary
        changes = []
        if cmd.name != form.name.data:
            changes.append(f'名稱: "{cmd.name}" -> "{form.name.data}"')
        if cmd.description != form.description.data:
            changes.append('描述：已更新')
        if cmd.category != form.category.data:
            changes.append(f'分類: "{cmd.category}" -> "{form.category.data}"')
        if cmd.base_commands != form.base_commands.data:
            changes.append('基礎指令序列：已更新')

        # update metadata
        cmd.name = form.name.data
        cmd.description = form.description.data
        cmd.category = form.category.data

        bump = request.form.get('bumpVersionCheck')
        if bump:
            # create a new version record (adv content) and bump version number
            try:
                cmd.add_version(content=form.base_commands.data, status='pending', bump=True)
                changes.append(f'版本已增加為 {cmd.version}')
            except Exception:
                db.session.rollback()
                flash('建立新版本時發生錯誤。')
                return redirect(url_for('webui.advanced_commands'))
        else:
            # update legacy in-place fields
            cmd.base_commands = form.base_commands.data
            cmd.version = form.version.data or cmd.version or 1

        # 編輯後狀態回到 pending 需重新審核
        cmd.status = 'pending'
        db.session.commit()
        if changes:
            flash('進階指令已更新並重新送審。變更摘要：' + '; '.join(changes))
        else:
            flash('進階指令已更新並重新送審。')
        return redirect(url_for('webui.advanced_commands'))
    # Extract complex logic into variables for readability
    duration_unit = session.get(
        'duration_unit',
        getattr(current_user, 'ui_duration_unit', 's')
    )
    verify_collapsed = session.get(
        'verify_collapsed',
        getattr(current_user, 'ui_verify_collapsed', False)
    )
    verified_advanced_commands = [
        ac.name for ac in AdvancedCommand.query.filter_by(status='approved').all()
    ]
    return render_template(
        'create_advanced_command.html.j2',
        form=form,
        cmd=cmd,
        duration_unit=duration_unit,
        verify_collapsed=verify_collapsed,
        verified_advanced_commands=verified_advanced_commands,
        editing=True
    )

# 審核進階指令（僅 admin/auditor）


@bp.route('/advanced_commands/audit/<int:cmd_id>', methods=['POST'])
@login_required
def audit_advanced_command(cmd_id):
    if not current_user.is_admin():
        flash('您沒有權限執行此操作。')
        return redirect(url_for('webui.advanced_commands'))
    cmd = AdvancedCommand.query.get_or_404(cmd_id)
    action = request.form.get('action')
    if action == 'approve':
        cmd.status = 'approved'
        flash(f'進階指令「{cmd.name}」已批准。')
    elif action == 'reject':
        cmd.status = 'rejected'
        flash(f'進階指令「{cmd.name}」已拒絕。')
    db.session.commit()
    return redirect(url_for('webui.advanced_commands'))


# ===== LLM 連線狀態與警告 API =====

# MCP API 基礎 URL
import os  # noqa: E402
MCP_API_URL = os.environ.get('MCP_API_URL', 'http://localhost:8000/api')


@bp.route('/api/llm/status', methods=['GET'])
def get_llm_status():
    """
    取得 LLM 連線狀態
    用於前端顯示連線狀態指示器
    """
    try:
        response = requests.get(f'{MCP_API_URL}/llm/connection/status', timeout=5)
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({
                'internet_available': None,
                'local_llm_available': False,
                'local_llm_provider': None,
                'using_fallback': None,
                'error': '無法取得連線狀態'
            }), response.status_code
    except requests.exceptions.ConnectionError:
        logging.warning('無法連線到 MCP API 伺服器')
        return jsonify({
            'internet_available': None,
            'local_llm_available': False,
            'local_llm_provider': None,
            'using_fallback': None,
            'mcp_available': False,
            'error': '無法連線到 MCP API 伺服器'
        }), 503
    except Exception as e:
        logging.error(f'取得 LLM 狀態失敗: {str(e)}')
        return jsonify({
            'internet_available': None,
            'local_llm_available': False,
            'local_llm_provider': None,
            'using_fallback': None,
            'error': '無法取得連線狀態'
        }), 500


@bp.route('/api/llm/warnings', methods=['GET'])
def get_llm_warnings():
    """
    取得 LLM 相關警告訊息
    用於前端顯示警告通知
    """
    try:
        clear = request.args.get('clear', 'false').lower() == 'true'
        response = requests.get(f'{MCP_API_URL}/llm/warnings', params={'clear': clear}, timeout=5)
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({
                'warnings': [],
                'count': 0,
                'error': '無法取得警告訊息'
            }), response.status_code
    except requests.exceptions.ConnectionError:
        logging.warning('無法連線到 MCP API 伺服器取得警告')
        return jsonify({
            'warnings': [{
                'type': 'mcp_unavailable',
                'message': '無法連線到 MCP 伺服器',
                'timestamp': None
            }],
            'count': 1,
            'mcp_available': False
        }), 503
    except Exception as e:
        logging.error(f'取得 LLM 警告失敗: {str(e)}')
        return jsonify({
            'warnings': [],
            'error': '無法取得警告訊息'
        }), 500


@bp.route('/api/llm/warnings', methods=['DELETE'])
@login_required
def clear_llm_warnings():
    """清除 LLM 警告訊息"""
    try:
        response = requests.delete(f'{MCP_API_URL}/llm/warnings', timeout=5)
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({
                'success': False,
                'error': '無法清除警告'
            }), response.status_code
    except Exception as e:
        logging.error(f'清除 LLM 警告失敗: {str(e)}')
        return jsonify({
            'success': False,
            'error': '伺服器發生錯誤'
        }), 500


@bp.route('/api/llm/check-internet', methods=['GET'])
def check_internet():
    """檢查網路連線狀態"""
    try:
        response = requests.get(f'{MCP_API_URL}/llm/check-internet', timeout=5)
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({
                'internet_available': None,
                'error': '無法檢查網路連線'
            }), response.status_code
    except requests.exceptions.ConnectionError:
        return jsonify({
            'internet_available': False,
            'mcp_available': False,
            'error': '無法連線到 MCP API 伺服器'
        }), 503
    except Exception as e:
        logging.error(f'檢查網路連線失敗: {str(e)}')
        return jsonify({
            'internet_available': None,
            'error': '伺服器發生錯誤'
        }), 500


# ===== LLM 設定頁面與提供商管理 =====

@bp.route('/llm_settings', methods=['GET'])
@login_required
def llm_settings():
    """LLM 設定頁面 - 管理本地 LLM 提供商"""
    return render_template('llm_settings.html.j2')


@bp.route('/api/llm/providers', methods=['GET'])
def get_llm_providers():
    """取得可用的 LLM 提供商列表"""
    try:
        response = requests.get(f'{MCP_API_URL}/llm/providers', timeout=5)
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({
                'providers': [],
                'error': '無法取得提供商列表'
            }), response.status_code
    except requests.exceptions.ConnectionError:
        return jsonify({
            'providers': [],
            'mcp_available': False,
            'error': '無法連線到 MCP API 伺服器'
        }), 503
    except Exception as e:
        logging.error(f'取得 LLM 提供商失敗: {str(e)}', exc_info=True)
        return jsonify({
            'providers': [],
            'error': '伺服器發生錯誤'
        }), 500


@bp.route('/api/llm/providers/health', methods=['GET'])
def get_llm_providers_health():
    """取得所有 LLM 提供商的健康狀態"""
    try:
        response = requests.get(f'{MCP_API_URL}/llm/providers/health', timeout=10)
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({
                'providers': {},
                'error': '無法取得提供商健康狀態'
            }), response.status_code
    except requests.exceptions.ConnectionError:
        return jsonify({
            'providers': {},
            'mcp_available': False,
            'error': '無法連線到 MCP API 伺服器'
        }), 503
    except Exception as e:
        logging.error(f'取得 LLM 提供商健康狀態失敗: {str(e)}', exc_info=True)
        return jsonify({
            'providers': {},
            'error': '伺服器發生錯誤'
        }), 500


@bp.route('/api/llm/providers/select', methods=['POST'])
@login_required
def select_llm_provider():
    """選擇要使用的 LLM 提供商並保存用戶偏好"""
    try:
        # 支援 JSON body 或 query parameter
        data = request.get_json(silent=True) or {}
        provider_name = data.get('provider_name') or request.args.get('provider_name')
        model_name = data.get('model_name') or request.args.get('model_name')
        save_preference = data.get('save_preference', True)

        if not provider_name:
            return jsonify({
                'success': False,
                'error': '缺少 provider_name 參數'
            }), 400

        # provider_name 格式驗證
        if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9_-]*$', provider_name):
            return jsonify({
                'success': False,
                'error': 'provider_name 格式不正確'
            }), 400

        # model_name 長度驗證
        if model_name is not None and len(model_name) > 128:
            return jsonify({
                'success': False,
                'error': 'model_name 長度不可超過 128 字元'
            }), 400

        response = requests.post(
            f'{MCP_API_URL}/llm/providers/select',
            json={'provider_name': provider_name},
            timeout=5
        )
        if response.status_code == 200:
            result = response.json()

            # 保存用戶偏好設定
            if save_preference:
                try:
                    current_user.llm_provider = provider_name
                    if model_name:
                        current_user.llm_model = model_name
                    db.session.commit()
                    result['preference_saved'] = True
                except Exception as e:
                    db.session.rollback()
                    logging.warning(f'保存 LLM 偏好設定失敗: {str(e)}')
                    result['preference_saved'] = False

            return jsonify(result)
        else:
            return jsonify({
                'success': False,
                'error': '選擇提供商失敗'
            }), response.status_code
    except requests.exceptions.ConnectionError:
        return jsonify({
            'success': False,
            'mcp_available': False,
            'error': '無法連線到 MCP API 伺服器'
        }), 503
    except Exception as e:
        logging.error(f'選擇 LLM 提供商失敗: {str(e)}', exc_info=True)
        return jsonify({
            'success': False,
            'error': '伺服器發生錯誤'
        }), 500


@bp.route('/api/llm/preferences', methods=['GET'])
@login_required
def get_llm_preferences():
    """取得用戶的 LLM 偏好設定"""
    try:
        return jsonify({
            'provider': current_user.llm_provider,
            'model': current_user.llm_model,
            'success': True
        })
    except Exception as e:
        logging.error(f'取得 LLM 偏好設定失敗: {str(e)}', exc_info=True)
        return jsonify({
            'success': False,
            'provider': None,
            'model': None,
            'error': '取得偏好設定失敗'
        }), 500


@bp.route('/api/llm/preferences', methods=['POST'])
@login_required
def save_llm_preferences():
    """保存用戶的 LLM 偏好設定"""
    try:
        data = request.get_json(silent=True) or {}

        # 驗證並更新 provider
        if 'provider' in data:
            provider = data.get('provider')
            if provider is not None and not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9_-]*$', provider):
                return jsonify({
                    'success': False,
                    'error': '無效的提供商名稱'
                }), 400
            current_user.llm_provider = provider

        # 驗證並更新 model
        if 'model' in data:
            model = data.get('model')
            if model is not None and len(model) > 128:
                return jsonify({
                    'success': False,
                    'error': '模型名稱過長'
                }), 400
            current_user.llm_model = model

        db.session.commit()

        return jsonify({
            'success': True,
            'provider': current_user.llm_provider,
            'model': current_user.llm_model,
            'message': 'LLM 偏好設定已保存'
        })
    except Exception as e:
        db.session.rollback()
        logging.error(f'保存 LLM 偏好設定失敗: {str(e)}', exc_info=True)
        return jsonify({
            'success': False,
            'error': '保存偏好設定失敗'
        }), 500


@bp.route('/api/llm/providers/<provider_name>/models', methods=['GET'])
def get_provider_models(provider_name):
    """取得特定提供商的可用模型列表"""
    try:
        # 驗證 provider_name 僅包含允許的字元（不允許以連字號開頭）
        if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9_-]*$', provider_name):
            return jsonify({
                'models': [],
                'error': '無效的提供商名稱'
            }), 400

        safe_provider_name = url_quote(provider_name, safe='_-')
        response = requests.get(
            f'{MCP_API_URL}/llm/providers/{safe_provider_name}/models',
            timeout=10
        )
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({
                'models': [],
                'error': '取得模型列表失敗'
            }), response.status_code
    except requests.exceptions.ConnectionError:
        return jsonify({
            'models': [],
            'mcp_available': False,
            'error': '無法連線到 MCP API 伺服器'
        }), 503
    except Exception as e:
        logging.error(f'取得提供商模型列表失敗: {str(e)}', exc_info=True)
        return jsonify({
            'models': [],
            'error': '伺服器發生錯誤'
        }), 500


@bp.route('/api/llm/providers/discover', methods=['POST'])
@login_required
def discover_llm_providers():
    """觸發 LLM 提供商偵測"""
    try:
        response = requests.post(f'{MCP_API_URL}/llm/providers/discover', timeout=15)
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({
                'discovered': {},
                'available_count': 0,
                'error': '偵測提供商失敗'
            }), response.status_code
    except requests.exceptions.ConnectionError:
        return jsonify({
            'discovered': {},
            'available_count': 0,
            'mcp_available': False,
            'error': '無法連線到 MCP API 伺服器'
        }), 503
    except Exception as e:
        logging.error(f'偵測 LLM 提供商失敗: {str(e)}', exc_info=True)
        return jsonify({
            'discovered': {},
            'available_count': 0,
            'error': '伺服器發生錯誤'
        }), 500


@bp.route('/api/llm/providers/<provider_name>/refresh', methods=['POST'])
@login_required
def refresh_llm_provider(provider_name):
    """重新檢查特定 LLM 提供商的健康狀態"""
    try:
        # 驗證 provider_name 僅包含允許的字元（不允許以連字號開頭）
        if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9_-]*$', provider_name):
            return jsonify({
                'success': False,
                'error': '無效的提供商名稱'
            }), 400

        # 使用 URL 編碼確保安全（允許底線和連字號，因為已經過正則驗證）
        safe_provider_name = url_quote(provider_name, safe='_-')
        response = requests.post(
            f'{MCP_API_URL}/llm/providers/{safe_provider_name}/refresh',
            timeout=10
        )
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({
                'success': False,
                'error': '重新檢查提供商失敗'
            }), response.status_code
    except requests.exceptions.ConnectionError:
        return jsonify({
            'success': False,
            'mcp_available': False,
            'error': '無法連線到 MCP API 伺服器'
        }), 503
    except Exception as e:
        logging.error(f'重新檢查 LLM 提供商失敗: {str(e)}', exc_info=True)
        return jsonify({
            'success': False,
            'error': '伺服器發生錯誤'
        }), 500


# ===== CORS 設定 API =====

# 儲存 CORS 狀態（在實際應用中應儲存到配置文件或資料庫）
_cors_enabled = False


@bp.route('/api/llm/cors/status', methods=['GET'])
def get_cors_status():
    """取得 CORS 設定狀態"""
    return jsonify({
        'enabled': _cors_enabled,
        'message': f'CORS 目前已{"啟用" if _cors_enabled else "停用"}'
    })


@bp.route('/api/llm/cors/toggle', methods=['POST'])
@login_required
def toggle_cors():
    """切換 CORS 設定"""
    global _cors_enabled
    try:
        data = request.get_json(silent=True) or {}

        # 支援指定狀態或切換
        if 'enabled' in data:
            _cors_enabled = bool(data['enabled'])
        else:
            _cors_enabled = not _cors_enabled

        logging.info(f'CORS 設定已切換為: {_cors_enabled}')

        return jsonify({
            'success': True,
            'enabled': _cors_enabled,
            'message': 'CORS 已' + ('啟用' if _cors_enabled else '停用')
        })
    except Exception as e:
        logging.error(f'切換 CORS 設定失敗: {str(e)}', exc_info=True)
        return jsonify({
            'success': False,
            'error': '切換 CORS 設定失敗'
        }), 500


# ===== 固件更新 API =====

@bp.route('/firmware', methods=['GET'])
@login_required
def firmware_update_page():
    """固件更新管理頁面"""
    from WebUI.app.models import DEFAULT_FIRMWARE_VERSION
    robots = Robot.query.filter_by(owner=current_user).all()
    return render_template(
        'firmware_update.html.j2',
        robots=robots,
        default_firmware_version=DEFAULT_FIRMWARE_VERSION
    )


@bp.route('/api/firmware/versions', methods=['GET'])
@login_required
def get_firmware_versions():
    """取得可用的固件版本列表
    
    Query Parameters:
        robot_type: 篩選特定機器人類型的固件（可選）
        stable_only: 是否只顯示穩定版本，預設為 'true'。
                     設為 'false' 以顯示所有版本（包含測試版）
    
    Returns:
        JSON 物件包含：
        - success: 操作是否成功
        - versions: 固件版本列表
        - count: 版本數量
    """
    from WebUI.app.models import FirmwareVersion
    
    try:
        robot_type = request.args.get('robot_type')
        stable_only = request.args.get('stable_only', 'true').lower() == 'true'
        
        query = FirmwareVersion.query
        
        if robot_type:
            query = query.filter_by(robot_type=robot_type)
        
        if stable_only:
            query = query.filter_by(is_stable=True)
        
        # Order by version descending (newest first)
        versions = query.order_by(FirmwareVersion.created_at.desc()).all()
        
        return jsonify({
            'success': True,
            'versions': [v.to_dict() for v in versions],
            'count': len(versions)
        })
    except Exception as e:
        logging.error(f'取得固件版本列表失敗: {str(e)}', exc_info=True)
        return jsonify({
            'success': False,
            'versions': [],
            'error': '取得固件版本列表失敗'
        }), 500


@bp.route('/api/firmware/check/<int:robot_id>', methods=['GET'])
@login_required
def check_firmware_status(robot_id):
    """檢查機器人的固件狀態
    
    回傳機器人當前固件版本以及是否有可用的更新
    """
    from WebUI.app.models import FirmwareVersion, DEFAULT_FIRMWARE_VERSION
    
    try:
        robot = Robot.query.get_or_404(robot_id)
        
        # 權限檢查：確認用戶擁有該機器人
        if robot.owner != current_user and not current_user.is_admin():
            return jsonify({
                'success': False,
                'error': '您沒有權限查看此機器人'
            }), 403
        
        current_version = robot.firmware_version or DEFAULT_FIRMWARE_VERSION
        
        # 查找該機器人類型的最新穩定版本
        latest_version = FirmwareVersion.query.filter_by(
            robot_type=robot.type,
            is_stable=True
        ).order_by(FirmwareVersion.created_at.desc()).first()
        
        # 判斷是否有更新可用
        update_available = False
        latest_version_str = None
        if latest_version:
            latest_version_str = latest_version.version
            # 簡單版本比較（假設版本格式為 x.y.z）
            update_available = _compare_versions(
                current_version,
                latest_version.version
            ) < 0
        
        return jsonify({
            'success': True,
            'robot_id': robot.id,
            'robot_name': robot.name,
            'robot_type': robot.type,
            'current_version': current_version,
            'latest_version': latest_version_str,
            'update_available': update_available,
            'latest_firmware': latest_version.to_dict() if latest_version else None
        })
    except Exception as e:
        logging.error(f'檢查固件狀態失敗: {str(e)}', exc_info=True)
        return jsonify({
            'success': False,
            'error': '檢查固件狀態時發生錯誤'
        }), 500


def _compare_versions(v1: str, v2: str) -> int:
    """比較兩個版本號
    
    Returns:
        -1 if v1 < v2
        0 if v1 == v2
        1 if v1 > v2
    """
    try:
        parts1 = [int(x) for x in v1.split('.')]
        parts2 = [int(x) for x in v2.split('.')]
        
        # Pad shorter version with zeros
        while len(parts1) < len(parts2):
            parts1.append(0)
        while len(parts2) < len(parts1):
            parts2.append(0)
        
        for p1, p2 in zip(parts1, parts2):
            if p1 < p2:
                return -1
            elif p1 > p2:
                return 1
        return 0
    except (ValueError, AttributeError):
        # If parsing fails, return 0 (equal)
        return 0


@bp.route('/api/firmware/update', methods=['POST'])
@login_required
def initiate_firmware_update():
    """啟動固件更新
    
    Request Body (JSON):
        {
            "robot_id": 1,
            "firmware_version_id": 2
        }
    """
    from WebUI.app.models import FirmwareVersion, FirmwareUpdate
    
    try:
        data = request.get_json(silent=True) or {}
        
        robot_id = data.get('robot_id')
        firmware_version_id = data.get('firmware_version_id')
        
        if not robot_id or not firmware_version_id:
            return jsonify({
                'success': False,
                'error': '缺少必要參數：robot_id 和 firmware_version_id'
            }), 400
        
        # 取得機器人
        robot = Robot.query.get_or_404(robot_id)
        
        # 權限檢查
        if robot.owner != current_user and not current_user.is_admin():
            return jsonify({
                'success': False,
                'error': '您沒有權限更新此機器人'
            }), 403
        
        # 取得目標固件版本
        firmware = FirmwareVersion.query.get_or_404(firmware_version_id)
        
        # 驗證固件類型與機器人類型匹配
        if firmware.robot_type != robot.type:
            return jsonify({
                'success': False,
                'error': f'固件類型不匹配：固件適用於 {firmware.robot_type}，但機器人類型為 {robot.type}'
            }), 400
        
        # 檢查是否已有進行中的更新
        existing_update = FirmwareUpdate.query.filter(
            FirmwareUpdate.robot_id == robot_id,
            FirmwareUpdate.status.in_(['pending', 'downloading', 'installing'])
        ).first()
        
        if existing_update:
            return jsonify({
                'success': False,
                'error': '該機器人已有進行中的固件更新',
                'existing_update_id': existing_update.id
            }), 409
        
        # 建立固件更新記錄
        update = FirmwareUpdate(
            robot_id=robot.id,
            firmware_version_id=firmware.id,
            initiated_by=current_user.id,
            status='pending',
            progress=0,
            previous_version=robot.firmware_version
        )
        db.session.add(update)
        db.session.commit()
        
        logging.info(
            f'固件更新已啟動: robot={robot.name}, '
            f'version={firmware.version}, initiated_by={current_user.username}'
        )
        
        # 觸發固件更新過程（在實際應用中這會是非同步任務）
        # 這裡模擬啟動更新
        _start_firmware_update_task(update.id)
        
        return jsonify({
            'success': True,
            'message': f'已啟動固件更新至版本 {firmware.version}',
            'update_id': update.id,
            'update': update.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        logging.error(f'啟動固件更新失敗: {str(e)}', exc_info=True)
        return jsonify({
            'success': False,
            'error': '啟動固件更新時發生錯誤'
        }), 500


def _start_firmware_update_task(update_id: int):
    """初始化固件更新任務（模擬實作）
    
    注意：這是一個簡化的模擬實作，僅將狀態更新為 'downloading' 並設置進度為 10%。
    完整的更新流程需要透過 `/api/firmware/simulate-progress` API 手動推進。
    
    在生產環境中，這應該是一個背景任務（如 Celery 任務）來處理：
    1. 下載固件檔案
    2. 驗證校驗碼
    3. 傳送到機器人
    4. 執行安裝
    5. 驗證安裝結果
    
    TODO: 實作完整的非同步更新流程，包括進度追蹤和錯誤處理。
    """
    from WebUI.app.models import FirmwareUpdate
    
    try:
        update = FirmwareUpdate.query.get(update_id)
        if not update:
            return
        
        # 更新狀態為下載中
        update.status = 'downloading'
        update.progress = 10
        db.session.commit()
        
        # 在實際應用中，這裡會執行：
        # 1. 下載固件檔案
        # 2. 驗證校驗碼
        # 3. 傳送到機器人
        # 4. 執行安裝
        # 5. 驗證安裝結果
        
        logging.info(f'固件更新任務已啟動: update_id={update_id}')
        
    except Exception as e:
        logging.error(f'固件更新任務啟動失敗: {str(e)}', exc_info=True)


@bp.route('/api/firmware/status/<int:update_id>', methods=['GET'])
@login_required
def get_firmware_update_status(update_id):
    """查詢固件更新狀態"""
    from WebUI.app.models import FirmwareUpdate
    
    try:
        update = FirmwareUpdate.query.get_or_404(update_id)
        
        # 權限檢查
        if update.user != current_user and not current_user.is_admin():
            # 也允許機器人擁有者查看
            if update.robot.owner != current_user:
                return jsonify({
                    'success': False,
                    'error': '您沒有權限查看此更新狀態'
                }), 403
        
        return jsonify({
            'success': True,
            'update': update.to_dict()
        })
        
    except Exception as e:
        logging.error(f'查詢固件更新狀態失敗: {str(e)}', exc_info=True)
        return jsonify({
            'success': False,
            'error': '查詢更新狀態時發生錯誤'
        }), 500


@bp.route('/api/firmware/history/<int:robot_id>', methods=['GET'])
@login_required
def get_firmware_update_history(robot_id):
    """取得機器人的固件更新歷史"""
    from WebUI.app.models import FirmwareUpdate
    
    try:
        robot = Robot.query.get_or_404(robot_id)
        
        # 權限檢查
        if robot.owner != current_user and not current_user.is_admin():
            return jsonify({
                'success': False,
                'error': '您沒有權限查看此機器人'
            }), 403
        
        updates = FirmwareUpdate.query.filter_by(
            robot_id=robot_id
        ).order_by(FirmwareUpdate.started_at.desc()).limit(20).all()
        
        return jsonify({
            'success': True,
            'robot_id': robot_id,
            'robot_name': robot.name,
            'updates': [u.to_dict() for u in updates],
            'count': len(updates)
        })
        
    except Exception as e:
        logging.error(f'取得固件更新歷史失敗: {str(e)}', exc_info=True)
        return jsonify({
            'success': False,
            'error': '取得更新歷史時發生錯誤'
        }), 500


@bp.route('/api/firmware/cancel/<int:update_id>', methods=['POST'])
@login_required
def cancel_firmware_update(update_id):
    """取消進行中的固件更新"""
    from WebUI.app.models import FirmwareUpdate
    
    try:
        update = FirmwareUpdate.query.get_or_404(update_id)
        
        # 權限檢查
        if update.user != current_user and not current_user.is_admin():
            if update.robot.owner != current_user:
                return jsonify({
                    'success': False,
                    'error': '您沒有權限取消此更新'
                }), 403
        
        # 只能取消尚未完成的更新
        if update.status in ['completed', 'failed', 'cancelled']:
            return jsonify({
                'success': False,
                'error': f'無法取消已{update.status}的更新'
            }), 400
        
        update.status = 'cancelled'
        from datetime import datetime
        update.completed_at = datetime.utcnow()
        db.session.commit()
        
        logging.info(
            f'固件更新已取消: update_id={update_id}, '
            f'cancelled_by={current_user.username}'
        )
        
        return jsonify({
            'success': True,
            'message': '固件更新已取消',
            'update': update.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        logging.error(f'取消固件更新失敗: {str(e)}', exc_info=True)
        return jsonify({
            'success': False,
            'error': '取消更新時發生錯誤'
        }), 500


# 模擬固件更新進度 API（用於開發和演示）
@bp.route('/api/firmware/simulate-progress/<int:update_id>', methods=['POST'])
@login_required
def simulate_firmware_progress(update_id):
    """模擬固件更新進度（僅用於開發測試）"""
    from WebUI.app.models import FirmwareUpdate
    
    try:
        if not current_user.is_admin():
            return jsonify({
                'success': False,
                'error': '只有管理員可以使用此功能'
            }), 403
        
        update = FirmwareUpdate.query.get_or_404(update_id)
        
        data = request.get_json(silent=True) or {}
        new_status = data.get('status')
        new_progress = data.get('progress')
        
        if new_status:
            update.status = new_status
            if new_status in ['completed', 'failed', 'cancelled']:
                from datetime import datetime
                update.completed_at = datetime.utcnow()
                # 如果完成，更新機器人的固件版本
                if new_status == 'completed' and update.robot:
                    update.robot.firmware_version = update.firmware_version.version
        
        if new_progress is not None:
            update.progress = min(max(0, int(new_progress)), 100)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'update': update.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        logging.error(f'模擬固件更新進度失敗: {str(e)}', exc_info=True)
        return jsonify({
            'success': False,
            'error': '模擬進度時發生錯誤'
        }), 500
