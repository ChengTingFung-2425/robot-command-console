"""
Flask Adapter
將 robot_service 適配為 Flask 應用，供 Electron 使用
"""

import asyncio
import logging
import os
import sys
from functools import wraps
from typing import Optional

from flask import Flask, g, jsonify, request
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

from ..queue import MessagePriority
from ..service_manager import ServiceManager
from ..utils.datetime_utils import utc_now, utc_now_iso
from ..utils.logging_utils import CustomJsonFormatter


def create_flask_app(
    service_manager: Optional[ServiceManager] = None,
    app_token: Optional[str] = None,
) -> Flask:
    """
    建立 Flask 應用
    
    Args:
        service_manager: 服務管理器實例，若無則建立新的
        app_token: 認證 token，若無則從環境變數讀取
        
    Returns:
        Flask 應用實例
    """
    app = Flask(__name__)
    
    # 配置日誌處理器
    log_handler = logging.StreamHandler(sys.stdout)
    formatter = CustomJsonFormatter(
        '%(timestamp)s %(level)s %(event)s %(message)s',
        service_name='robot-service-flask'
    )
    log_handler.setFormatter(formatter)
    
    app.logger.handlers.clear()
    app.logger.addHandler(log_handler)
    app.logger.setLevel(logging.INFO)
    
    logging.basicConfig(level=logging.INFO, handlers=[log_handler])
    logger = logging.getLogger(__name__)
    
    # 服務管理器
    if service_manager is None:
        service_manager = ServiceManager()
    
    app.config['SERVICE_MANAGER'] = service_manager
    
    # Token 認證
    APP_TOKEN = app_token or os.environ.get('APP_TOKEN')
    if not APP_TOKEN:
        logger.error('APP_TOKEN not configured')
        sys.exit(1)
    
    # Prometheus Metrics
    REQUEST_COUNT = Counter(
        'flask_service_request_count_total',
        'Total number of requests',
        ['method', 'endpoint', 'status']
    )
    
    REQUEST_LATENCY = Histogram(
        'flask_service_request_latency_seconds',
        'Request latency in seconds',
        ['method', 'endpoint']
    )
    
    ERROR_COUNT = Counter(
        'flask_service_error_count_total',
        'Total number of errors',
        ['endpoint', 'error_type']
    )
    
    ACTIVE_CONNECTIONS = Gauge(
        'flask_service_active_connections',
        'Number of active connections'
    )
    
    QUEUE_SIZE = Gauge(
        'flask_service_queue_size',
        'Current queue size'
    )
    
    def run_async(coro):
        """在 Flask 同步上下文中執行非同步函式的輔助函式"""
        return asyncio.run(coro)
    
    # Request ID middleware
    @app.before_request
    def before_request():
        """在每個請求之前執行"""
        import uuid
        g.request_id = str(uuid.uuid4())
        g.correlation_id = request.headers.get('X-Correlation-ID', g.request_id)
        g.start_time = utc_now()
        ACTIVE_CONNECTIONS.inc()
        
        logger.info('Request started', extra={
            'method': request.method,
            'path': request.path,
            'remote_addr': request.remote_addr,
        })
    
    @app.after_request
    def after_request(response):
        """在每個請求之後執行"""
        if hasattr(g, 'start_time'):
            duration = (utc_now() - g.start_time).total_seconds()
            
            REQUEST_COUNT.labels(
                method=request.method,
                endpoint=request.endpoint or 'unknown',
                status=response.status_code
            ).inc()
            
            REQUEST_LATENCY.labels(
                method=request.method,
                endpoint=request.endpoint or 'unknown'
            ).observe(duration)
            
            logger.info('Request completed', extra={
                'method': request.method,
                'path': request.path,
                'status': response.status_code,
                'duration_seconds': duration
            })
            
            ACTIVE_CONNECTIONS.dec()
        
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
                logger.warning('Missing authorization header')
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
                    logger.warning('Invalid token')
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
                logger.warning('Invalid authorization header format', extra={'error': str(e)})
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
    
    # Prometheus Metrics 端點
    @app.route('/metrics', methods=['GET'])
    def metrics():
        """Prometheus metrics endpoint"""
        logger.info('Metrics endpoint accessed')
        
        # 更新佇列大小指標
        size = run_async(service_manager.queue.size())
        QUEUE_SIZE.set(size)
        
        return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}
    
    # 健康檢查端點
    @app.route('/health', methods=['GET'])
    def health_check():
        """Health check endpoint"""
        logger.info('Health check requested')
        
        health = run_async(service_manager.health_check())
        
        return jsonify({
            'status': 'healthy',
            'service': 'robot-command-console-flask',
            'timestamp': utc_now_iso(),
            'version': '1.0.0',
            'request_id': g.request_id if hasattr(g, 'request_id') else None,
            'service_manager': health,
        })
    
    # API 測試端點
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
            'timestamp': utc_now_iso(),
            'method': request.method,
            'authenticated': True,
            'request_id': g.request_id if hasattr(g, 'request_id') else None,
            'correlation_id': g.correlation_id if hasattr(g, 'correlation_id') else None
        })
    
    # 指令提交端點
    @app.route('/api/command', methods=['POST'])
    @require_token
    def submit_command():
        """提交指令到佇列"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({
                    'error': 'Missing request body',
                    'code': 'ERR_VALIDATION',
                    'request_id': g.request_id
                }), 400
            
            # 提取優先權
            priority_str = data.get('priority', 'NORMAL')
            try:
                priority = MessagePriority[priority_str]
            except KeyError:
                priority = MessagePriority.NORMAL
            
            # 提交到佇列
            message_id = run_async(service_manager.submit_command(
                payload=data,
                priority=priority,
                trace_id=data.get('trace_id'),
                correlation_id=g.correlation_id,
            ))
            
            if message_id:
                return jsonify({
                    'message_id': message_id,
                    'status': 'queued',
                    'request_id': g.request_id,
                }), 202
            else:
                return jsonify({
                    'error': 'Failed to queue command',
                    'code': 'ERR_QUEUE_FULL',
                    'request_id': g.request_id,
                }), 503
        
        except Exception as e:
            logger.error('Error submitting command', exc_info=True)
            return jsonify({
                'error': 'Internal server error',
                'code': 'ERR_INTERNAL',
                'request_id': g.request_id,
            }), 500
    
    # 佇列狀態端點
    @app.route('/api/queue/stats', methods=['GET'])
    @require_token
    def queue_stats():
        """取得佇列統計"""
        stats = run_async(service_manager.get_queue_stats())
        return jsonify(stats)
    
    # 錯誤處理
    @app.errorhandler(404)
    def not_found(error):
        logger.warning('Endpoint not found', extra={'path': request.path})
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
        logger.error('Internal server error', exc_info=True)
        ERROR_COUNT.labels(
            endpoint=request.endpoint or 'unknown',
            error_type='internal_error'
        ).inc()
        return jsonify({
            'error': 'Internal server error',
            'code': 'ERR_INTERNAL',
            'request_id': g.request_id if hasattr(g, 'request_id') else None
        }), 500
    
    return app
