#!/usr/bin/env python3
"""
Flask 背景服務 for Electron POC
Port: 5000
Auth: Bearer token from APP_TOKEN environment variable
"""

import os
import sys
from flask import Flask, jsonify, request
from functools import wraps
from datetime import datetime

app = Flask(__name__)

# 從環境變數讀取 token
APP_TOKEN = os.environ.get('APP_TOKEN')
PORT = int(os.environ.get('PORT', 5000))

if not APP_TOKEN:
    print('ERROR: APP_TOKEN environment variable not set', file=sys.stderr)
    sys.exit(1)

print(f'Flask service initializing with token: {APP_TOKEN[:8]}...')

# Token 驗證裝飾器
def require_token(f):
    """驗證 Authorization header 中的 Bearer token"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return jsonify({
                'error': 'Missing Authorization header',
                'code': 'ERR_UNAUTHORIZED'
            }), 401
        
        try:
            scheme, token = auth_header.split(' ', 1)
            if scheme.lower() != 'bearer':
                raise ValueError('Invalid scheme')
            
            if token != APP_TOKEN:
                return jsonify({
                    'error': 'Invalid token',
                    'code': 'ERR_UNAUTHORIZED'
                }), 401
        except (ValueError, AttributeError):
            return jsonify({
                'error': 'Invalid Authorization header format',
                'code': 'ERR_UNAUTHORIZED'
            }), 401
        
        return f(*args, **kwargs)
    
    return decorated_function

# 健康檢查端點（不需要認證）
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'robot-command-console-flask',
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'version': '1.0.0-poc'
    })

# API 測試端點（需要認證）
@app.route('/api/ping', methods=['GET', 'POST'])
@require_token
def api_ping():
    """測試端點：驗證 token 和往返通訊"""
    return jsonify({
        'message': 'pong',
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'method': request.method,
        'authenticated': True
    })

# 錯誤處理
@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'error': 'Endpoint not found',
        'code': 'ERR_NOT_FOUND'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'error': 'Internal server error',
        'code': 'ERR_INTERNAL'
    }), 500

if __name__ == '__main__':
    print(f'Starting Flask service on 127.0.0.1:{PORT}...')
    # 只監聽 localhost 確保安全
    app.run(host='127.0.0.1', port=PORT, debug=False)
