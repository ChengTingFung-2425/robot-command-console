
# imports
from flask import Blueprint, jsonify, request, render_template, redirect, url_for, flash, session, abort
from flask_login import current_user, login_user, logout_user, login_required
from WebUI.app import db
from WebUI.app.models import Robot, Command, User, AdvancedCommand, UserProfile
from WebUI.app.forms import LoginForm, RegisterForm, RegisterRobotForm, ResetPasswordRequestForm, ResetPasswordForm, AdvancedCommandForm
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
                logging.warning(f"MQTT 發送失敗，可能是 MQTT 未啟用或連接失敗")
                
        except ImportError as e:
            logging.warning(f"無法導入 MQTT 客戶端模組: {str(e)}")
        except Exception as e:
            logging.warning(f"MQTT 發送時發生錯誤: {str(e)}")
        
        # 備用方案：如果 MQTT 不可用或失敗，只記錄到日誌
        # 這允許在沒有 MQTT 配置的環境中仍然可以測試其他功能
        logging.info(
            f"備用方案：動作列表已記錄（MQTT 不可用），等待其他傳輸機制"
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

    return render_template('advanced_commands.html.j2', 
                         commands=commands,
                         filter_status=filter_status,
                         sort_by=sort_by,
                         sort_order=sort_order,
                         author_filter=author_filter,
                         approved_adv_command_map=approved)

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
                ver = cmd.add_version(content=form.base_commands.data, status='pending', bump=True)
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
import os
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
            'error': str(e)
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
