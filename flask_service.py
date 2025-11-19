#!/usr/bin/env python3
"""
Flask 背景服務 for Electron POC
Port: 5000
Auth: Bearer token from APP_TOKEN environment variable
"""

import os
import sys
import logging
import uuid
from flask import Flask, jsonify, request, g
from functools import wraps
from datetime import datetime, timezone
from pythonjsonlogger import jsonlogger
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

app = Flask(__name__)

# 從環境變數讀取 token
APP_TOKEN = os.environ.get('APP_TOKEN')
PORT = int(os.environ.get('PORT', 5000))

if not APP_TOKEN:
    print('ERROR: APP_TOKEN environment variable not set', file=sys.stderr)
    sys.exit(1)

# 設定 JSON 結構化日誌
class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """自定義 JSON 日誌格式器"""
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        log_record['timestamp'] = datetime.now(timezone.utc).isoformat()
        log_record['level'] = record.levelname
        log_record['event'] = record.name
        log_record['service'] = 'flask-service'
        # 添加 request_id 如果在請求上下文中
        try:
            if hasattr(g, 'request_id'):
                log_record['request_id'] = g.request_id
            if hasattr(g, 'correlation_id'):
                log_record['correlation_id'] = g.correlation_id
        except RuntimeError:
            # 不在請求上下文中，略過
            pass

# 配置日誌處理器
log_handler = logging.StreamHandler(sys.stdout)
formatter = CustomJsonFormatter('%(timestamp)s %(level)s %(event)s %(message)s')
log_handler.setFormatter(formatter)

# 配置 Flask app logger
app.logger.handlers.clear()
app.logger.addHandler(log_handler)
app.logger.setLevel(logging.INFO)

# 配置根 logger
logging.basicConfig(level=logging.INFO, handlers=[log_handler])
logger = logging.getLogger(__name__)

# Prometheus Metrics
REQUEST_COUNT = Counter(
    'flask_request_count_total',
    'Total number of requests',
    ['method', 'endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    'flask_request_latency_seconds',
    'Request latency in seconds',
    ['method', 'endpoint']
)

ERROR_COUNT = Counter(
    'flask_error_count_total',
    'Total number of errors',
    ['endpoint', 'error_type']
)

QUEUE_DEPTH = Gauge(
    'flask_queue_depth',
    'Current depth of the processing queue'
)

ACTIVE_CONNECTIONS = Gauge(
    'flask_active_connections',
    'Number of active connections'
)

logger.info('Flask service initializing', extra={
    'token_prefix': APP_TOKEN[:8],
    'port': PORT
})

# Request ID middleware
@app.before_request
def before_request():
    """在每個請求之前執行，生成 request_id 和 correlation_id"""
    g.request_id = str(uuid.uuid4())
    g.correlation_id = request.headers.get('X-Correlation-ID', g.request_id)
    g.start_time = datetime.now(timezone.utc)
    
    ACTIVE_CONNECTIONS.inc()
    
    logger.info('Request started', extra={
        'method': request.method,
        'path': request.path,
        'remote_addr': request.remote_addr,
        'user_agent': request.headers.get('User-Agent', 'unknown')
    })

@app.after_request
def after_request(response):
    """在每個請求之後執行，記錄 metrics 和日誌"""
    if hasattr(g, 'start_time'):
        duration = (datetime.now(timezone.utc) - g.start_time).total_seconds()
        
        # 記錄 Prometheus metrics
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.endpoint or 'unknown',
            status=response.status_code
        ).inc()
        
        REQUEST_LATENCY.labels(
            method=request.method,
            endpoint=request.endpoint or 'unknown'
        ).observe(duration)
        
        # 記錄結構化日誌
        logger.info('Request completed', extra={
            'method': request.method,
            'path': request.path,
            'status': response.status_code,
            'duration_seconds': duration
        })
    
    if hasattr(g, 'start_time'):
        ACTIVE_CONNECTIONS.dec()
    
    # 添加 correlation ID 到 response headers
    if hasattr(g, 'correlation_id'):
        response.headers['X-Correlation-ID'] = g.correlation_id
    if hasattr(g, 'request_id'):
        response.headers['X-Request-ID'] = g.request_id
    
    return response

# Token 驗證裝飾器
def require_token(f):
    """驗證 Authorization header 中的 Bearer token"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            logger.warning('Missing authorization header', extra={
                'path': request.path,
                'remote_addr': request.remote_addr
            })
            ERROR_COUNT.labels(
                endpoint=request.endpoint or 'unknown',
                error_type='unauthorized'
            ).inc()
            return jsonify({
                'error': 'Missing Authorization header',
                'code': 'ERR_UNAUTHORIZED',
                'request_id': g.request_id if hasattr(g, 'request_id') else None
            }), 401
        
        try:
            scheme, token = auth_header.split(' ', 1)
            if scheme.lower() != 'bearer':
                raise ValueError('Invalid scheme')
            
            if token != APP_TOKEN:
                logger.warning('Invalid token', extra={
                    'path': request.path,
                    'token_prefix': token[:8] if len(token) >= 8 else token
                })
                ERROR_COUNT.labels(
                    endpoint=request.endpoint or 'unknown',
                    error_type='invalid_token'
                ).inc()
                return jsonify({
                    'error': 'Invalid token',
                    'code': 'ERR_UNAUTHORIZED',
                    'request_id': g.request_id if hasattr(g, 'request_id') else None
                }), 401
        except (ValueError, AttributeError) as e:
            logger.warning('Invalid authorization header format', extra={
                'path': request.path,
                'error': str(e)
            })
            ERROR_COUNT.labels(
                endpoint=request.endpoint or 'unknown',
                error_type='invalid_auth_format'
            ).inc()
            return jsonify({
                'error': 'Invalid Authorization header format',
                'code': 'ERR_UNAUTHORIZED',
                'request_id': g.request_id if hasattr(g, 'request_id') else None
            }), 401
        
        return f(*args, **kwargs)
    
    return decorated_function

# Prometheus Metrics 端點（不需要認證）
@app.route('/metrics', methods=['GET'])
def metrics():
    """Prometheus metrics endpoint"""
    logger.info('Metrics endpoint accessed')
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

# 健康檢查端點（不需要認證）
@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    logger.info('Health check requested')
    return jsonify({
        'status': 'healthy',
        'service': 'robot-command-console-flask',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'version': '1.0.0-poc',
        'request_id': g.request_id if hasattr(g, 'request_id') else None
    })

# API 測試端點（需要認證）
@app.route('/api/ping', methods=['GET', 'POST'])
@require_token
def api_ping():
    """測試端點：驗證 token 和往返通訊"""
    logger.info('Ping endpoint accessed', extra={
        'method': request.method,
        'authenticated': True
    })
    return jsonify({
        'message': 'pong',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'method': request.method,
        'authenticated': True,
        'request_id': g.request_id if hasattr(g, 'request_id') else None,
        'correlation_id': g.correlation_id if hasattr(g, 'correlation_id') else None
    })

# 錯誤處理
@app.errorhandler(404)
def not_found(error):
    logger.warning('Endpoint not found', extra={
        'path': request.path,
        'error': str(error)
    })
    ERROR_COUNT.labels(
        endpoint=request.endpoint or 'unknown',
        error_type='not_found'
    ).inc()
    return jsonify({
        'error': 'Endpoint not found',
        'code': 'ERR_NOT_FOUND',
        'request_id': g.request_id if hasattr(g, 'request_id') else None
    }), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error('Internal server error', extra={
        'path': request.path,
        'error': str(error)
    }, exc_info=True)
    ERROR_COUNT.labels(
        endpoint=request.endpoint or 'unknown',
        error_type='internal_error'
    ).inc()
    return jsonify({
        'error': 'Internal server error',
        'code': 'ERR_INTERNAL',
        'request_id': g.request_id if hasattr(g, 'request_id') else None
    }), 500

if __name__ == '__main__':
    logger.info('Starting Flask service', extra={
        'host': '127.0.0.1',
        'port': PORT
    })
    # 只監聽 localhost 確保安全
    app.run(host='127.0.0.1', port=PORT, debug=False)
