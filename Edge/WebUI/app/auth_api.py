# imports
import os
import secrets
from datetime import datetime, timedelta
from functools import wraps
from typing import Optional

import jwt
from flask import Blueprint, jsonify, request

from WebUI.app.models import User, Device
from WebUI.app import db
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


# Device Management Routes
@auth_api_bp.route('/device/register', methods=['POST'])
@token_required()
def register_device():
    """
    註冊新裝置並綁定到當前使用者
    
    Headers:
        Authorization: Bearer <access_token>
    
    請求：
    {
        "device_id": "string (64 chars SHA-256)",
        "device_name": "string (optional)",
        "device_type": "string (desktop/laptop/mobile/edge_device)",
        "platform": "string (Windows/Linux/macOS)",
        "hostname": "string (optional)",
        "ip_address": "string (optional)"
    }
    
    回應：
    {
        "success": true,
        "device": {...},
        "message": "Device registered and bound successfully"
    }
    """
    user = request.current_user
    data = request.get_json() or {}
    
    device_id = data.get('device_id', '').strip()
    device_name = data.get('device_name', '').strip()
    device_type = data.get('device_type', 'unknown').strip()
    platform = data.get('platform', '').strip()
    hostname = data.get('hostname', '').strip()
    ip_address = data.get('ip_address', '').strip()
    
    # Validation
    if not device_id or len(device_id) != 64:
        return jsonify({'error': 'Invalid device_id format (must be 64 chars SHA-256)'}), 400
    
    # Validate device_id is hexadecimal
    try:
        int(device_id, 16)
    except ValueError:
        return jsonify({'error': 'Invalid device_id format (must be hexadecimal)'}), 400
    
    # Check if device already exists
    existing_device = Device.query.filter_by(device_id=device_id).first()
    if existing_device:
        # Device already bound to this user
        if existing_device.user_id == user.id:
            reactivated = False
            # If previously unbound/inactive, reactivate and refresh binding info
            if existing_device.is_active is False:
                existing_device.is_active = True
                existing_device.bound_at = db.func.now()
                # Refresh basic metadata on re-bind
                existing_device.device_type = device_type
                existing_device.platform = platform
                existing_device.hostname = hostname
                existing_device.ip_address = ip_address or request.remote_addr
                reactivated = True

            # Update last_seen
            existing_device.last_seen_at = db.func.now()
            db.session.commit()
            
            log_audit_event(
                action='device_register_existing',
                message=(
                    f'裝置已存在，{"重新啟用並" if reactivated else ""}更新最後連線時間 '
                    f'(device_id={device_id[:8]}...)'
                ),
                user_id=user.id,
                severity='info',
                category='device',
                context={
                    'device_id': device_id,
                    'reactivated': reactivated,
                }
            )
            
            return jsonify({
                'success': True,
                'device': existing_device.to_dict(),
                'message': 'Device already registered to this user'
            }), 200
        else:
            # Device bound to different user
            log_audit_event(
                action='device_register_conflict',
                message=f'裝置已綁定到其他使用者 (device_id={device_id[:8]}...)',
                user_id=user.id,
                severity='warning',
                category='device',
                context={'device_id': device_id, 'existing_user_id': existing_device.user_id}
            )
            return jsonify({'error': 'Device already registered to another user'}), 409
    
    # Check device limit (max 10 devices per user)
    device_count = Device.query.filter_by(user_id=user.id, is_active=True).count()
    if device_count >= 10:
        log_audit_event(
            action='device_register_limit_exceeded',
            message=f'使用者裝置數量已達上限 (current={device_count})',
            user_id=user.id,
            severity='warning',
            category='device'
        )
        return jsonify({'error': 'Device limit exceeded (max 10 devices per user)'}), 429
    
    # Create new device
    new_device = Device(
        device_id=device_id,
        device_name=device_name or f'{platform} Device',
        device_type=device_type,
        user_id=user.id,
        platform=platform,
        hostname=hostname,
        ip_address=ip_address or request.remote_addr,
        user_agent=request.headers.get('User-Agent', '')[:512],
        is_active=True,
        is_trusted=False
    )
    
    db.session.add(new_device)
    db.session.commit()
    
    # Log audit event
    log_audit_event(
        action='device_register_success',
        message=f'新裝置註冊成功 (device_id={device_id[:8]}...)',
        user_id=user.id,
        severity='info',
        category='device',
        context={
            'device_id': device_id,
            'device_name': device_name,
            'platform': platform
        }
    )
    
    return jsonify({
        'success': True,
        'device': new_device.to_dict(),
        'message': 'Device registered and bound successfully'
    }), 201


@auth_api_bp.route('/devices', methods=['GET'])
@token_required()
def list_devices():
    """
    列出當前使用者的所有裝置
    
    Headers:
        Authorization: Bearer <access_token>
    
    Query Parameters:
        active_only: boolean (default: false) - 僅顯示活躍裝置
    
    回應：
    {
        "devices": [...],
        "total": int
    }
    """
    user = request.current_user
    active_only = request.args.get('active_only', 'false').lower() == 'true'
    
    query = Device.query.filter_by(user_id=user.id)
    if active_only:
        query = query.filter_by(is_active=True)
    
    devices = query.order_by(Device.last_seen_at.desc()).all()
    
    return jsonify({
        'devices': [device.to_dict() for device in devices],
        'total': len(devices)
    }), 200


@auth_api_bp.route('/device/<int:device_id>', methods=['GET'])
@token_required()
def get_device(device_id):
    """
    取得特定裝置資訊
    
    Headers:
        Authorization: Bearer <access_token>
    
    回應：
    {
        "device": {...}
    }
    """
    user = request.current_user
    device = Device.query.filter_by(id=device_id, user_id=user.id).first()
    
    if not device:
        return jsonify({'error': 'Device not found'}), 404
    
    return jsonify({
        'device': device.to_dict()
    }), 200


@auth_api_bp.route('/device/<int:device_id>', methods=['PUT'])
@token_required()
def update_device(device_id):
    """
    更新裝置資訊
    
    Headers:
        Authorization: Bearer <access_token>
    
    請求：
    {
        "device_name": "string (optional)",
        "is_trusted": boolean (optional)
    }
    
    回應：
    {
        "success": true,
        "device": {...}
    }
    """
    user = request.current_user
    device = Device.query.filter_by(id=device_id, user_id=user.id).first()
    
    if not device:
        return jsonify({'error': 'Device not found'}), 404
    
    data = request.get_json() or {}
    
    if 'device_name' in data:
        device_name_stripped = data['device_name'].strip()
        if not device_name_stripped:
            return jsonify({'error': 'device_name cannot be empty'}), 400
        device.device_name = device_name_stripped
    
    if 'is_trusted' in data:
        raw_is_trusted = data['is_trusted']

        if isinstance(raw_is_trusted, bool):
            parsed_is_trusted = raw_is_trusted
        elif isinstance(raw_is_trusted, str):
            value = raw_is_trusted.strip().lower()
            if value in ('true', '1'):
                parsed_is_trusted = True
            elif value in ('false', '0'):
                parsed_is_trusted = False
            else:
                return jsonify({
                    'error': 'Invalid value for is_trusted; must be boolean'
                }), 400
        else:
            return jsonify({
                'error': 'Invalid type for is_trusted; must be boolean'
            }), 400

        device.is_trusted = parsed_is_trusted
        log_audit_event(
            action='device_trust_changed',
            message=f'裝置信任狀態變更: {device.is_trusted}',
            user_id=user.id,
            severity='info',
            category='device',
            context={'device_id': device.device_id, 'is_trusted': device.is_trusted}
        )
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'device': device.to_dict()
    }), 200


@auth_api_bp.route('/device/<int:device_id>/unbind', methods=['POST'])
@token_required()
def unbind_device(device_id):
    """
    解除裝置綁定（停用裝置）
    
    Headers:
        Authorization: Bearer <access_token>
    
    回應：
    {
        "success": true,
        "message": "Device unbound successfully"
    }
    """
    user = request.current_user
    device = Device.query.filter_by(id=device_id, user_id=user.id).first()
    
    if not device:
        return jsonify({'error': 'Device not found'}), 404
    
    # Deactivate device instead of deleting
    device.is_active = False
    db.session.commit()
    
    # Log audit event
    log_audit_event(
        action='device_unbind',
        message=f'裝置解除綁定 (device_id={device.device_id[:8]}...)',
        user_id=user.id,
        severity='info',
        category='device',
        context={'device_id': device.device_id}
    )
    
    return jsonify({
        'success': True,
        'message': 'Device unbound successfully'
    }), 200


@auth_api_bp.route('/device/<int:device_id>', methods=['DELETE'])
@token_required()
def delete_device(device_id):
    """
    刪除裝置（僅 Admin）
    
    Headers:
        Authorization: Bearer <access_token>
    
    回應：
    {
        "success": true,
        "message": "Device deleted successfully"
    }
    """
    user = request.current_user
    
    # Only admin can delete devices
    if user.role != 'admin':
        return jsonify({'error': 'Admin permission required'}), 403
    
    device = Device.query.filter_by(id=device_id).first()
    
    if not device:
        return jsonify({'error': 'Device not found'}), 404
    
    db.session.delete(device)
    db.session.commit()
    
    # Log audit event
    log_audit_event(
        action='device_delete',
        message=f'裝置刪除 (device_id={device.device_id[:8]}...)',
        user_id=user.id,
        severity='warning',
        category='device',
        context={'device_id': device.device_id, 'target_user_id': device.user_id}
    )
    
    return jsonify({
        'success': True,
        'message': 'Device deleted successfully'
    }), 200
