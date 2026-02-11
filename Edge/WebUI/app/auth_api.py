# imports
import os
import secrets
from datetime import datetime, timedelta
from functools import wraps
from typing import Optional

import jwt
from flask import Blueprint, jsonify, request

from WebUI.app.models import User
from WebUI.app.audit import log_audit_event

# Blueprint
auth_api_bp = Blueprint('auth_api', __name__, url_prefix='/api/auth')


# Constants
ACCESS_TOKEN_EXPIRES_MINUTES = 15
REFRESH_TOKEN_EXPIRES_DAYS = 7


# Helper functions
def generate_device_id() -> str:
    """生成設備 ID（用於綁定 token）"""
    return secrets.token_urlsafe(32)


def get_device_fingerprint(request_obj) -> str:
    """從請求中提取設備指紋"""
    # 組合多個因素生成唯一指紋
    user_agent = request_obj.headers.get('User-Agent', '')
    # 簡化版：實際應該包含更多因素（如 IP 範圍、瀏覽器特徵等）
    return user_agent[:100]  # 截斷避免過長


def create_access_token(user_id: int, role: str) -> str:
    """建立 Access Token（短期，15 分鐘）"""
    payload = {
        'user_id': user_id,
        'role': role,
        'type': 'access',
        'exp': datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRES_MINUTES),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, os.environ.get('SECRET_KEY', 'dev-secret-key'), algorithm='HS256')


def create_refresh_token(user_id: int, device_id: str) -> str:
    """建立 Refresh Token（長期，7 天，設備綁定）"""
    payload = {
        'user_id': user_id,
        'device_id': device_id,
        'type': 'refresh',
        'exp': datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRES_DAYS),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, os.environ.get('SECRET_KEY', 'dev-secret-key'), algorithm='HS256')


def verify_token(token: str, token_type: str = 'access') -> Optional[dict]:
    """驗證 token 並返回 payload"""
    try:
        payload = jwt.decode(token, os.environ.get('SECRET_KEY', 'dev-secret-key'), algorithms=['HS256'])
        
        # 檢查 token 類型
        if payload.get('type') != token_type:
            return None
        
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def token_required(allow_offline: bool = False):
    """Token 驗證裝飾器"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            auth_header = request.headers.get('Authorization', '')
            if not auth_header.startswith('Bearer '):
                return jsonify({'error': 'Missing or invalid Authorization header'}), 401
            
            token = auth_header.replace('Bearer ', '')
            payload = verify_token(token, 'access')
            
            if not payload:
                return jsonify({'error': 'Invalid or expired token'}), 401
            
            # 查詢使用者
            user = User.query.get(payload['user_id'])
            if not user:
                return jsonify({'error': 'User not found'}), 401
            
            # 將使用者注入到 request context
            request.current_user = user
            request.token_payload = payload
            
            return f(*args, **kwargs)
        
        return wrapper
    return decorator


# Routes
@auth_api_bp.route('/login', methods=['POST'])
def login():
    """
    登入端點（Cloud-First 認證）
    
    請求：
    {
        "username": "string",
        "password": "string",
        "device_id": "string (optional)"
    }
    
    回應：
    {
        "success": true,
        "access_token": "string (15分鐘)",
        "refresh_token": "string (7天)",
        "user": {
            "id": int,
            "username": "string",
            "email": "string",
            "role": "string"
        },
        "device_id": "string"
    }
    """
    data = request.get_json() or {}
    
    # 驗證輸入
    username = data.get('username', '').strip()
    password = data.get('password', '')
    device_id = data.get('device_id')
    
    if not username or not password:
        log_audit_event(
            action='login_failure',
            message='登入失敗：缺少使用者名稱或密碼',
            severity='warning',
            category='authentication'
        )
        return jsonify({'error': 'Username and password are required'}), 400
    
    # 查詢使用者
    user = User.query.filter_by(username=username).first()
    
    if not user or not user.check_password(password):
        log_audit_event(
            action='login_failure',
            message=f'登入失敗：無效的使用者名稱或密碼 (username={username})',
            severity='warning',
            category='authentication'
        )
        return jsonify({'error': 'Invalid username or password'}), 401
    
    # 生成或使用設備 ID
    if not device_id:
        device_id = generate_device_id()
    
    # 建立 tokens
    access_token = create_access_token(user.id, user.role)
    refresh_token = create_refresh_token(user.id, device_id)
    
    # 記錄審計日誌
    log_audit_event(
        action='api_login_success',
        message=f'使用者透過 API 成功登入 (device_id={device_id[:8]}...)',
        user_id=user.id,
        severity='info',
        category='authentication',
        context={'device_id': device_id, 'login_method': 'api'}
    )
    
    return jsonify({
        'success': True,
        'access_token': access_token,
        'refresh_token': refresh_token,
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role
        },
        'device_id': device_id,
        'expires_in': ACCESS_TOKEN_EXPIRES_MINUTES * 60  # 秒數
    }), 200


@auth_api_bp.route('/refresh', methods=['POST'])
def refresh():
    """
    Token 更新端點
    
    請求：
    {
        "refresh_token": "string"
    }
    
    回應：
    {
        "success": true,
        "access_token": "string (新的15分鐘token)",
        "user": {...}
    }
    """
    data = request.get_json() or {}
    refresh_token = data.get('refresh_token', '').strip()
    
    if not refresh_token:
        return jsonify({'error': 'Refresh token is required'}), 400
    
    # 驗證 Refresh Token
    payload = verify_token(refresh_token, 'refresh')
    if not payload:
        log_audit_event(
            action='token_refresh_failure',
            message='Token 更新失敗：無效或過期的 refresh token',
            severity='warning',
            category='authentication'
        )
        return jsonify({'error': 'Invalid or expired refresh token'}), 401
    
    # 查詢使用者
    user = User.query.get(payload['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 401
    
    # 建立新的 Access Token（使用最新角色）
    new_access_token = create_access_token(user.id, user.role)
    
    # 記錄審計日誌
    log_audit_event(
        action='token_refresh_success',
        message='使用者成功更新 access token',
        user_id=user.id,
        severity='info',
        category='authentication',
        context={'device_id': payload.get('device_id', 'unknown')}
    )
    
    return jsonify({
        'success': True,
        'access_token': new_access_token,
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role
        },
        'expires_in': ACCESS_TOKEN_EXPIRES_MINUTES * 60
    }), 200


@auth_api_bp.route('/verify', methods=['POST'])
@token_required()
def verify():
    """
    驗證 Token 有效性
    
    Headers:
        Authorization: Bearer <access_token>
    
    回應：
    {
        "valid": true,
        "user": {...}
    }
    """
    user = request.current_user
    
    return jsonify({
        'valid': True,
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role
        }
    }), 200


@auth_api_bp.route('/revoke', methods=['POST'])
@token_required()
def revoke():
    """
    撤銷 Token（登出）
    
    Headers:
        Authorization: Bearer <access_token>
    
    回應：
    {
        "success": true,
        "message": "Token revoked successfully"
    }
    """
    user = request.current_user
    
    # 記錄審計日誌
    log_audit_event(
        action='api_logout',
        message='使用者透過 API 登出',
        user_id=user.id,
        severity='info',
        category='authentication'
    )
    
    # 注意：JWT token 無法真正撤銷（無狀態設計）
    # 實際應用中需要：
    # 1. 黑名單機制（Redis）
    # 2. 或使用短期 token + 頻繁更新
    # 這裡僅記錄登出事件
    
    return jsonify({
        'success': True,
        'message': 'Logged out successfully. Token will expire naturally.'
    }), 200


@auth_api_bp.route('/me', methods=['GET'])
@token_required()
def get_current_user():
    """
    取得當前使用者資訊
    
    Headers:
        Authorization: Bearer <access_token>
    
    回應：
    {
        "user": {...}
    }
    """
    user = request.current_user
    
    return jsonify({
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role,
            'ui_preferences': {
                'duration_unit': user.ui_duration_unit,
                'verify_collapsed': user.ui_verify_collapsed
            }
        }
    }), 200
