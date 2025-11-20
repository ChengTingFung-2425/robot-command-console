"""
MCP FastAPI 服務
提供 HTTP API 介面
"""

import asyncio
import base64
import logging
import sys
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from pythonjsonlogger import jsonlogger

from .auth_manager import AuthManager
from .command_handler import CommandHandler
from .config import MCPConfig
from .context_manager import ContextManager
from .llm_processor import LLMProcessor
from .logging_monitor import LoggingMonitor
from .models import (
    AudioCommandRequest,
    AudioCommandResponse,
    CommandRequest,
    CommandResponse,
    Event,
    Heartbeat,
    MediaStreamRequest,
    RobotRegistration,
    RobotStatus,
    StatusResponse,
)
from .robot_router import RobotRouter


# 設定 JSON 結構化日誌
class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """自定義 JSON 日誌格式器"""
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        log_record['timestamp'] = datetime.now(timezone.utc).isoformat()
        log_record['level'] = record.levelname
        log_record['event'] = record.name
        log_record['service'] = 'mcp-api'

# 配置日誌處理器
log_handler = logging.StreamHandler(sys.stdout)
formatter = CustomJsonFormatter('%(timestamp)s %(level)s %(event)s %(message)s')
log_handler.setFormatter(formatter)

# 配置 logger
logging.basicConfig(level=MCPConfig.LOG_LEVEL, handlers=[log_handler])
logger = logging.getLogger(__name__)
logger.handlers.clear()
logger.addHandler(log_handler)
logger.setLevel(MCPConfig.LOG_LEVEL)

# Prometheus Metrics
REQUEST_COUNT = Counter(
    'mcp_request_count_total',
    'Total number of requests',
    ['method', 'endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    'mcp_request_latency_seconds',
    'Request latency in seconds',
    ['method', 'endpoint']
)

COMMAND_COUNT = Counter(
    'mcp_command_count_total',
    'Total number of commands processed',
    ['status']
)

ROBOT_COUNT = Gauge(
    'mcp_robot_count',
    'Number of registered robots',
    ['status']
)

ERROR_COUNT = Counter(
    'mcp_error_count_total',
    'Total number of errors',
    ['endpoint', 'error_type']
)

ACTIVE_WEBSOCKETS = Gauge(
    'mcp_active_websockets',
    'Number of active WebSocket connections'
)


# 建立應用
app = FastAPI(
    title="MCP 服務",
    description="Model Context Protocol 服務 API",
    version="1.0.0"
)

# 建立 v1 API router
from fastapi import APIRouter
v1_router = APIRouter(prefix="/v1")


# CORS 設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=MCPConfig.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Auth middleware
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """
    認證中介軟體
    除了 /health、/metrics 和 /v1/auth/login 外，所有端點都需要認證
    """
    # 不需要認證的端點
    public_paths = ['/health', '/metrics', '/v1/auth/login', '/api/auth/login']
    
    # 檢查是否是公開端點
    if request.url.path in public_paths or request.url.path.startswith('/docs') or request.url.path.startswith('/openapi'):
        return await call_next(request)
    
    # 檢查 Authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return Response(
            status_code=401,
            content='{"error": "UNAUTHORIZED", "message": "Missing or invalid Authorization header"}',
            media_type="application/json"
        )
    
    # 提取 token
    token = auth_header.split(" ")[1]
    
    # 驗證 token
    trace_id = request.headers.get('X-Trace-ID', str(uuid.uuid4()))
    if not await auth_manager.verify_token(token, trace_id=trace_id):
        return Response(
            status_code=401,
            content='{"error": "UNAUTHORIZED", "message": "Invalid or expired token"}',
            media_type="application/json"
        )
    
    # Token 有效，繼續處理請求
    return await call_next(request)


# Request tracking middleware
@app.middleware("http")
async def track_requests(request: Request, call_next):
    """追蹤所有 HTTP 請求"""
    request_id = str(uuid.uuid4())
    correlation_id = request.headers.get('X-Correlation-ID', request_id)
    start_time = datetime.now(timezone.utc)
    
    # 記錄請求開始
    logger.info("Request started", extra={
        'request_id': request_id,
        'correlation_id': correlation_id,
        'method': request.method,
        'path': request.url.path,
        'client': request.client.host if request.client else 'unknown'
    })
    
    # 處理請求
    try:
        response = await call_next(request)
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        # 記錄 metrics
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).inc()
        
        REQUEST_LATENCY.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(duration)
        
        # 記錄請求完成
        logger.info("Request completed", extra={
            'request_id': request_id,
            'correlation_id': correlation_id,
            'method': request.method,
            'path': request.url.path,
            'status': response.status_code,
            'duration_seconds': duration
        })
        
        # 添加 headers
        response.headers['X-Request-ID'] = request_id
        response.headers['X-Correlation-ID'] = correlation_id
        
        return response
        
    except Exception as e:
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        logger.error("Request failed", extra={
            'request_id': request_id,
            'correlation_id': correlation_id,
            'method': request.method,
            'path': request.url.path,
            'error': str(e),
            'duration_seconds': duration
        }, exc_info=True)
        
        ERROR_COUNT.labels(
            endpoint=request.url.path,
            error_type=type(e).__name__
        ).inc()
        
        # 在異常時也記錄 REQUEST_COUNT 和 REQUEST_LATENCY
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status=500
        ).inc()
        REQUEST_LATENCY.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(duration)
        
        raise


# 初始化模組
context_manager = ContextManager()
logging_monitor = LoggingMonitor()
auth_manager = AuthManager(logging_monitor=logging_monitor)
robot_router = RobotRouter()
llm_processor = LLMProcessor()
command_handler = CommandHandler(
    robot_router=robot_router,
    context_manager=context_manager,
    auth_manager=auth_manager,
    logging_monitor=logging_monitor
)


@app.on_event("startup")
async def startup_event():
    """啟動事件"""
    logger.info("MCP service starting", extra={
        'host': MCPConfig.API_HOST,
        'port': MCPConfig.API_PORT,
        'log_level': MCPConfig.LOG_LEVEL
    })
    robot_router.start()
    logger.info("MCP service started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """關閉事件"""
    logger.info("MCP service shutting down")
    await robot_router.stop()
    logger.info("MCP service shutdown complete")


# ===== Prometheus Metrics =====

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    logger.debug("Metrics endpoint accessed")
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


# ===== 健康檢查 =====

@app.get("/health")
async def health_check():
    """健康檢查"""
    logger.debug("Health check requested")
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "mcp-api",
        "version": "1.0.0"
    }


# ===== 指令 API =====

@v1_router.post("/command", response_model=CommandResponse)
@app.post("/api/command", response_model=CommandResponse)
async def create_command(request: CommandRequest):
    """建立指令"""
    try:
        logger.info("Command received", extra={
            'trace_id': request.trace_id,
            'robot_id': request.robot_id,
            'action': request.action
        })
        
        response = await command_handler.process_command(request)
        
        COMMAND_COUNT.labels(status='success').inc()
        
        logger.info("Command processed successfully", extra={
            'trace_id': request.trace_id,
            'command_id': response.command_id if hasattr(response, 'command_id') else None
        })
        
        return response
    except Exception as e:
        COMMAND_COUNT.labels(status='error').inc()
        ERROR_COUNT.labels(
            endpoint='/api/command',
            error_type=type(e).__name__
        ).inc()
        
        logger.error("Command processing failed", extra={
            'trace_id': request.trace_id if hasattr(request, 'trace_id') else None,
            'error': str(e)
        }, exc_info=True)
        
        raise HTTPException(status_code=500, detail=str(e))


@v1_router.get("/command/{command_id}")
@app.get("/api/command/{command_id}")
async def get_command_status(command_id: str):
    """查詢指令狀態"""
    status = await command_handler.get_command_status(command_id)
    if not status:
        raise HTTPException(status_code=404, detail="指令不存在")
    return status


@v1_router.delete("/command/{command_id}")
@app.delete("/api/command/{command_id}")
async def cancel_command(command_id: str, trace_id: Optional[str] = None):
    """取消指令"""
    if not trace_id:
        trace_id = str(datetime.utcnow().timestamp())
    
    success = await command_handler.cancel_command(command_id, trace_id)
    if not success:
        raise HTTPException(status_code=404, detail="指令不存在或無法取消")
    
    return {"message": "指令已取消", "command_id": command_id}


# ===== 機器人 API =====

@v1_router.post("/robots/register")
@app.post("/api/robots/register")
async def register_robot(registration: RobotRegistration):
    """註冊機器人"""
    logger.info("Robot registration request", extra={
        'robot_id': registration.robot_id,
        'robot_type': registration.robot_type if hasattr(registration, 'robot_type') else None
    })
    
    success = await robot_router.register_robot(registration)
    if not success:
        logger.error("Robot registration failed", extra={
            'robot_id': registration.robot_id
        })
        raise HTTPException(status_code=500, detail="註冊失敗")
    
    ROBOT_COUNT.labels(status='active').inc()
    
    logger.info("Robot registered successfully", extra={
        'robot_id': registration.robot_id
    })
    
    return {"message": "註冊成功", "robot_id": registration.robot_id}


@v1_router.delete("/robots/{robot_id}")
@app.delete("/api/robots/{robot_id}")
async def unregister_robot(robot_id: str):
    """取消註冊機器人"""
    logger.info("Robot unregistration request", extra={
        'robot_id': robot_id
    })
    
    success = await robot_router.unregister_robot(robot_id)
    if not success:
        logger.warning("Robot not found for unregistration", extra={
            'robot_id': robot_id
        })
        raise HTTPException(status_code=404, detail="機器人不存在")
    
    ROBOT_COUNT.labels(status='active').dec()
    
    logger.info("Robot unregistered successfully", extra={
        'robot_id': robot_id
    })
    
    return {"message": "取消註冊成功", "robot_id": robot_id}


@v1_router.post("/robots/heartbeat")
@app.post("/api/robots/heartbeat")
async def update_heartbeat(heartbeat: Heartbeat):
    """更新心跳"""
    success = await robot_router.update_heartbeat(heartbeat)
    if not success:
        raise HTTPException(status_code=404, detail="機器人未註冊")
    
    return {"message": "心跳已更新"}


@v1_router.get("/robots/{robot_id}")
@app.get("/api/robots/{robot_id}")
async def get_robot(robot_id: str):
    """取得機器人資訊"""
    robot = await robot_router.get_robot(robot_id)
    if not robot:
        raise HTTPException(status_code=404, detail="機器人不存在")
    
    return robot


@v1_router.get("/robots")
@app.get("/api/robots")
async def list_robots(
    robot_type: Optional[str] = None,
    status: Optional[RobotStatus] = None
):
    """列出機器人"""
    robots = await robot_router.list_robots(robot_type=robot_type, status=status)
    return {"robots": robots, "count": len(robots)}


# ===== 事件 API =====

@v1_router.get("/events")
@app.get("/api/events")
async def get_events(
    trace_id: Optional[str] = None,
    limit: int = 100
):
    """查詢事件"""
    events = await logging_monitor.get_events(trace_id=trace_id, limit=limit)
    return {"events": events, "count": len(events)}


@v1_router.websocket("/events/subscribe")
@app.websocket("/api/events/subscribe")
async def subscribe_events(websocket: WebSocket):
    """訂閱事件（WebSocket）"""
    await websocket.accept()
    ACTIVE_WEBSOCKETS.inc()
    
    logger.info("WebSocket connection established", extra={
        'client': websocket.client.host if websocket.client else 'unknown',
        'endpoint': '/api/events/subscribe'
    })
    
    async def send_event(event: Event):
        try:
            await websocket.send_json(event.dict())
        except Exception as e:
            logger.error("Failed to send event", extra={
                'error': str(e),
                'trace_id': event.trace_id
            })
    
    await logging_monitor.subscribe_events(send_event)
    
    try:
        while True:
            # 保持連線
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected", extra={
            'endpoint': '/api/events/subscribe'
        })
    finally:
        await logging_monitor.unsubscribe_events(send_event)
        ACTIVE_WEBSOCKETS.dec()


# ===== 指標 API =====

@v1_router.get("/metrics")
@app.get("/api/metrics")
async def get_metrics():
    """取得指標"""
    metrics = await logging_monitor.get_metrics()
    return metrics


# ===== 認證 API =====

@v1_router.post("/auth/register")
@app.post("/api/auth/register")
async def register_user(
    user_id: str,
    username: str,
    password: str,
    role: str = "viewer"
):
    """註冊使用者"""
    success = await auth_manager.register_user(user_id, username, password, role)
    if not success:
        raise HTTPException(status_code=400, detail="使用者已存在")
    
    return {"message": "註冊成功", "user_id": user_id}


@v1_router.post("/auth/login")
@app.post("/api/auth/login")
async def login(username: str, password: str):
    """登入"""
    user_id = await auth_manager.authenticate_user(username, password)
    if not user_id:
        raise HTTPException(status_code=401, detail="帳號或密碼錯誤")
    
    # 取得使用者角色
    user = auth_manager.users.get(user_id)
    role = user.get("role", "viewer") if user else "viewer"
    
    # 建立 Token
    token = await auth_manager.create_token(user_id, role)
    
    # 計算過期時間
    from datetime import timedelta
    expires_at = datetime.now(timezone.utc) + timedelta(hours=MCPConfig.JWT_EXPIRATION_HOURS)
    
    return {
        "token": token,
        "user_id": user_id,
        "role": role,
        "expires_at": expires_at.isoformat()
    }


@v1_router.post("/auth/rotate")
@app.post("/api/auth/rotate")
async def rotate_token(request: Request):
    """Token 輪替"""
    # 從 Authorization header 獲取當前 token
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="缺少或無效的 Authorization header")
    
    current_token = auth_header.split(" ")[1]
    
    # 驗證當前 token
    if not await auth_manager.verify_token(current_token):
        raise HTTPException(status_code=401, detail="Token 無效或已過期")
    
    # 解碼 token 以獲取使用者資訊
    payload = await auth_manager.decode_token(current_token)
    if not payload:
        raise HTTPException(status_code=401, detail="無法解碼 token")
    
    user_id = payload.get("user_id")
    role = payload.get("role", "viewer")
    
    # 建立新 token
    new_token = await auth_manager.create_token(user_id, role)
    
    # 計算過期時間
    from datetime import timedelta
    expires_at = datetime.now(timezone.utc) + timedelta(hours=MCPConfig.JWT_EXPIRATION_HOURS)
    
    logger.info("Token rotated successfully", extra={
        'user_id': user_id,
        'role': role
    })
    
    return {
        "token": new_token,
        "expires_at": expires_at.isoformat()
    }


# ===== 媒體串流 API =====

@v1_router.websocket("/media/stream/{robot_id}")
@app.websocket("/api/media/stream/{robot_id}")
async def stream_media(websocket: WebSocket, robot_id: str):
    """媒體串流（WebSocket）"""
    await websocket.accept()
    
    # 檢查機器人是否存在（在增加計數前檢查）
    robot = await robot_router.get_robot(robot_id)
    if not robot:
        logger.warning("Media stream request for non-existent robot", extra={
            'robot_id': robot_id
        })
        await websocket.close(code=1008, reason="機器人不存在")
        return
    
    ACTIVE_WEBSOCKETS.inc()
    
    logger.info("Media stream connection established", extra={
        'robot_id': robot_id,
        'client': websocket.client.host if websocket.client else 'unknown'
    })
    
    try:
        
        # 持續推送媒體資料
        while True:
            # 接收來自 WebUI 的控制訊息（如切換格式等）
            try:
                data = await websocket.receive_json()
                logger.debug("Received media stream control message", extra={
                    'robot_id': robot_id,
                    'data': data
                })
            except:
                # 如果沒有訊息，繼續
                pass
            
            # 這裡應該從機器人端獲取實際的視訊/音訊資料
            # 目前作為示範，發送狀態訊息
            await websocket.send_json({
                "type": "status",
                "robot_id": robot_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
            # 避免過度發送
            await asyncio.sleep(0.033)  # ~30 FPS
            
    except WebSocketDisconnect:
        logger.info("Media stream disconnected", extra={
            'robot_id': robot_id
        })
    except Exception as e:
        logger.error("Media stream error", extra={
            'robot_id': robot_id,
            'error': str(e)
        }, exc_info=True)
        await websocket.close(code=1011, reason=f"串流錯誤: {str(e)}")
    finally:
        ACTIVE_WEBSOCKETS.dec()


@v1_router.post("/media/audio/command", response_model=AudioCommandResponse)
@app.post("/api/media/audio/command", response_model=AudioCommandResponse)
async def process_audio_command(request: AudioCommandRequest):
    """處理音訊指令"""
    try:
        # 解碼 Base64 音訊資料
        audio_bytes = base64.b64decode(request.audio_data)
        
        # 使用 LLM 處理器進行語音辨識
        transcription, confidence = await llm_processor.transcribe_audio(
            audio_bytes=audio_bytes,
            audio_format=request.audio_format,
            language=request.language
        )
        
        # 使用 LLM 解析指令
        command = await llm_processor.parse_command(
            transcription=transcription,
            robot_id=request.robot_id
        )
        
        response = AudioCommandResponse(
            trace_id=request.trace_id,
            transcription=transcription,
            command=command,
            confidence=confidence
        )
        
        # 記錄事件
        await logging_monitor.log_event(
            trace_id=request.trace_id,
            severity="INFO",
            category="command",
            message=f"音訊指令處理完成: {transcription}",
            context={
                "robot_id": request.robot_id,
                "transcription": transcription,
                "confidence": confidence,
                "command": command.dict() if command else None
            }
        )
        
        return response
        
    except Exception as e:
        logger.error(f"處理音訊指令失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# 註冊 v1 router
app.include_router(v1_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api:app",
        host=MCPConfig.API_HOST,
        port=MCPConfig.API_PORT,
        reload=True
    )
