"""
Admin routes for Tiny WebUI version
Includes: Audit logs, Robot registration
"""

import logging
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request, render_template, redirect, url_for, flash, make_response
from flask_login import current_user, login_required
from WebUI.app import db
from WebUI.app.models import Robot, AuditLog
from WebUI.app.forms import RegisterRobotForm

bp_admin = Blueprint('admin', __name__, url_prefix='/admin')
logger = logging.getLogger(__name__)


def admin_required(f):
    """管理員權限裝飾器"""
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('需要管理員權限', 'error')
            return redirect(url_for('core.home'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return login_required(decorated_function)


# ==================== Robot Registration ====================

@bp_admin.route('/register_robot', methods=['GET', 'POST'])
@admin_required
def register_robot():
    """註冊新機器人"""
    form = RegisterRobotForm()
    if form.validate_on_submit():
        try:
            robot = Robot(
                name=form.name.data,
                type=form.type.data,
                endpoint=form.endpoint.data,
                status='idle'
            )
            db.session.add(robot)
            db.session.commit()
            
            flash(f'機器人 {robot.name} 註冊成功！', 'success')
            return redirect(url_for('core.robots'))
        
        except Exception as e:
            db.session.rollback()
            logger.error(f'Robot registration failed: {e}')
            flash('機器人註冊失敗，請稍後再試。', 'error')
    
    return render_template('register_robot.html.j2', form=form)


# ==================== Audit Logs ====================

@bp_admin.route('/audit_logs')
@admin_required
def audit_logs():
    """審計日誌頁面"""
    page = request.args.get('page', 1, type=int)
    per_page = 50
    
    # 過濾條件
    event_type = request.args.get('event_type', type=str)
    username = request.args.get('username', type=str)
    start_date = request.args.get('start_date', type=str)
    end_date = request.args.get('end_date', type=str)
    
    query = AuditLog.query
    
    if event_type:
        query = query.filter_by(event_type=event_type)
    if username:
        query = query.filter(AuditLog.username.contains(username))
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date)
            query = query.filter(AuditLog.timestamp >= start_dt)
        except ValueError:
            pass
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date)
            query = query.filter(AuditLog.timestamp <= end_dt)
        except ValueError:
            pass
    
    pagination = query.order_by(AuditLog.timestamp.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template(
        'audit_logs.html.j2',
        logs=pagination.items,
        pagination=pagination
    )


@bp_admin.route('/audit_logs/<int:log_id>')
@admin_required
def audit_log_detail(log_id):
    """審計日誌詳細資訊"""
    log = AuditLog.query.get_or_404(log_id)
    return render_template('audit_log_detail.html.j2', log=log)


@bp_admin.route('/audit_logs/export')
@admin_required
def export_audit_logs():
    """匯出審計日誌 (CSV)"""
    # 套用相同的過濾條件
    event_type = request.args.get('event_type', type=str)
    username = request.args.get('username', type=str)
    start_date = request.args.get('start_date', type=str)
    end_date = request.args.get('end_date', type=str)
    
    query = AuditLog.query
    
    if event_type:
        query = query.filter_by(event_type=event_type)
    if username:
        query = query.filter(AuditLog.username.contains(username))
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date)
            query = query.filter(AuditLog.timestamp >= start_dt)
        except ValueError:
            pass
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date)
            query = query.filter(AuditLog.timestamp <= end_dt)
        except ValueError:
            pass
    
    logs = query.order_by(AuditLog.timestamp.desc()).limit(10000).all()
    
    # 生成 CSV
    csv_data = 'ID,Timestamp,Event Type,Username,User ID,IP Address,Details\n'
    for log in logs:
        csv_data += f'{log.id},{log.timestamp},{log.event_type},{log.username or "N/A"},{log.user_id or "N/A"},{log.ip_address or "N/A"},"{log.details or ""}"\n'
    
    response = make_response(csv_data)
    response.headers['Content-Disposition'] = f'attachment; filename=audit_logs_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    response.headers['Content-Type'] = 'text/csv'
    
    return response
