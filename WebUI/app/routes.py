
# imports
from flask import Blueprint, jsonify, request, render_template, redirect, url_for, flash, session, abort
from flask_login import current_user, login_user, logout_user, login_required
from WebUI.app import db
from WebUI.app.models import Robot, Command, User, AdvancedCommand, UserProfile
from WebUI.app.forms import LoginForm, RegisterForm, RegisterRobotForm, ResetPasswordRequestForm, ResetPasswordForm, AdvancedCommandForm
from WebUI.app.email import send_email
from WebUI.app.engagement import award_on_registration, get_or_create_user_profile

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
