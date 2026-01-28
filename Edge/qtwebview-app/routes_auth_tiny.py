"""
Authentication routes for Tiny WebUI version
Includes: Login, Logout, Register (simplified, no password reset)
"""

import logging
from flask import Blueprint, request, render_template, redirect, url_for, flash
from flask_login import current_user, login_user, logout_user
from urllib.parse import urlparse
from WebUI.app import db
from WebUI.app.models import User, UserProfile
from WebUI.app.forms import LoginForm, RegisterForm
from WebUI.app.audit import log_login_attempt, log_logout, log_registration
from WebUI.app.engagement import award_on_registration
from flask import current_app

bp_auth = Blueprint('auth', __name__, url_prefix='/auth')
logger = logging.getLogger(__name__)


# ==================== Register ====================

@bp_auth.route('/register', methods=['GET', 'POST'])
def register():
    """用戶註冊 (簡化版)"""
    if current_user.is_authenticated:
        return redirect(url_for('core.home'))
    
    form = RegisterForm()
    if form.validate_on_submit():
        try:
            user = User(username=form.username.data, email=form.email.data)
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.flush()
            
            # 建立用戶 profile
            profile = UserProfile(user_id=user.id)
            db.session.add(profile)
            db.session.commit()
            
            # 獎勵積分
            award_on_registration(user.id)
            
            # 記錄日誌
            log_registration(
                username=user.username,
                email=user.email,
                user_id=user.id
            )
            
            flash('註冊成功，請登入。', 'success')
            return redirect(url_for('auth.login'))
        
        except Exception as e:
            db.session.rollback()
            logger.error(f'Registration failed: {e}')
            flash('註冊失敗，請稍後再試。', 'error')
    
    return render_template('register.html.j2', form=form)


# ==================== Login ====================

@bp_auth.route('/login', methods=['GET', 'POST'])
def login():
    """用戶登入"""
    if current_user.is_authenticated:
        return redirect(url_for('core.dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        
        if user is None or not user.check_password(form.password.data):
            log_login_attempt(username=form.username.data, success=False)
            flash('用戶名稱或密碼錯誤', 'error')
            return redirect(url_for('auth.login'))
        
        log_login_attempt(username=user.username, success=True, user_id=user.id)
        login_user(user, remember=form.remember_me.data if hasattr(form, 'remember_me') else False)
        
        # 重定向到原本要訪問的頁面（只允許站內相對路徑）
        raw_next = request.args.get('next', '')
        next_page = None
        if raw_next:
            # Normalize and parse the user-provided next parameter
            candidate = raw_next.replace('\\', '').strip()
            parsed = urlparse(candidate)
            # Accept only relative paths without scheme/netloc and starting with '/'
            if not parsed.scheme and not parsed.netloc and candidate.startswith('/'):
                next_page = candidate
            # Verify if the route exists in the Flask application
            if next_page and next_page in [rule.rule for rule in current_app.url_map.iter_rules()]:
                next_page = candidate
        else:
            next_page = url_for('core.dashboard')
        
        flash(f'歡迎回來，{user.username}！', 'success')
        return redirect(next_page or url_for('core.dashboard'))
    
    return render_template('login.html.j2', form=form)


# ==================== Logout ====================

@bp_auth.route('/logout')
def logout():
    """用戶登出"""
    if current_user.is_authenticated:
        log_logout(username=current_user.username, user_id=current_user.id)
        logout_user()
        flash('您已成功登出。', 'info')
    
    return redirect(url_for('core.home'))


# ==================== User Profile (Simplified) ====================

@bp_auth.route('/user/<username>')
def user_profile(username):
    """用戶資料頁面 (簡化版，僅顯示基本資訊)"""
    user = User.query.filter_by(username=username).first_or_404()
    return render_template('user.html.j2', user=user)
