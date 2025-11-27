"""
MCP FastAPI 服務
提供 HTTP API 介面
"""

import asyncio
import base64
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

from .auth_manager import AuthManager
from .command_handler import CommandHandler
from .config import MCPConfig
from .context_manager import ContextManager
from .llm_processor import LLMProcessor
from .llm_provider_manager import LLMProviderManager
from .logging_monitor import LoggingMonitor
from .mcp_tool_interface import MCPToolInterface
from .models import (
    AudioCommandRequest,
    AudioCommandResponse,
    CommandRequest,
    CommandResponse,
    Event,
    Heartbeat,
    RobotRegistration,
    RobotStatus,
)
from .plugin_base import PluginConfig
from .plugin_manager import PluginManager
from .plugins.commands import AdvancedCommandPlugin, WebUICommandPlugin
from .plugins.devices import CameraPlugin, SensorPlugin
from .robot_router import RobotRouter
from .utils import setup_json_logging

# 配置 logger（使用共用模組）
logger = setup_json_logging(__name__, service_name='mcp-api', level=MCPConfig.LOG_LEVEL)

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
    if (request.url.path in public_paths or
            request.url.path.startswith('/docs') or
            request.url.path.startswith('/openapi')):
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

command_handler = CommandHandler(
    robot_router=robot_router,
    context_manager=context_manager,
    auth_manager=auth_manager,
    logging_monitor=logging_monitor
)

# 初始化 MCP 工具介面
mcp_tool_interface = MCPToolInterface(command_handler=command_handler)

# 初始化 LLM 提供商管理器和處理器（注入 MCP 工具介面）
llm_provider_manager = LLMProviderManager(mcp_tool_interface=mcp_tool_interface)
llm_processor = LLMProcessor(provider_manager=llm_provider_manager)

# 初始化插件管理器
plugin_manager = PluginManager()

# 註冊插件
plugin_manager.register_plugin(AdvancedCommandPlugin, PluginConfig(enabled=True, priority=10))
plugin_manager.register_plugin(WebUICommandPlugin, PluginConfig(enabled=True, priority=20))
plugin_manager.register_plugin(CameraPlugin, PluginConfig(enabled=True, priority=30))
plugin_manager.register_plugin(SensorPlugin, PluginConfig(enabled=True, priority=40))


@app.on_event("startup")
async def startup_event():
    """啟動事件"""
    logger.info("MCP service starting", extra={
        'host': MCPConfig.API_HOST,
        'port': MCPConfig.API_PORT,
        'log_level': MCPConfig.LOG_LEVEL
    })
    robot_router.start()

    # 初始化插件
    try:
        logger.info("開始初始化插件...")
        plugin_results = await plugin_manager.initialize_all()
        success_count = sum(1 for success in plugin_results.values() if success)
        logger.info(f"插件初始化完成: {success_count}/{len(plugin_results)} 成功")
    except Exception as e:
        logger.error(f"插件初始化失敗: {e}", exc_info=True)

    # 自動偵測本地 LLM 提供商
    try:
        logger.info("開始偵測本地 LLM 提供商...")
        health_results = await llm_provider_manager.discover_providers()
        available_count = len([h for h in health_results.values() if h.status.value == "available"])
        logger.info(f"LLM 提供商偵測完成: 發現 {available_count} 個可用提供商")
    except Exception as e:
        logger.error(f"LLM 提供商偵測失敗: {e}", exc_info=True)

    logger.info("MCP service started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """關閉事件"""
    logger.info("MCP service shutting down")

    # 關閉插件
    try:
        logger.info("開始關閉插件...")
        await plugin_manager.shutdown_all()
        logger.info("插件關閉完成")
    except Exception as e:
        logger.error(f"插件關閉失敗: {e}", exc_info=True)

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
        trace_id = str(datetime.now(timezone.utc).timestamp())

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
            except Exception:
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


# ===== LLM 提供商管理 API =====

@v1_router.post("/llm/invoke")
@app.post("/api/llm/invoke")
async def invoke_llm_with_tools(
    prompt: str,
    robot_id: str,
    model: Optional[str] = None,
    provider: Optional[str] = None,
    use_tools: bool = True,
    trace_id: Optional[str] = None
):
    """
    使用 LLM 處理指令，並啟用 MCP 工具呼叫
    
    Args:
        prompt: 使用者輸入
        robot_id: 目標機器人 ID
        model: 使用的模型（選用）
        provider: 使用的提供商（選用，預設使用當前選擇的）
        use_tools: 是否啟用工具呼叫（預設 True）
        trace_id: 追蹤 ID（選用）
    """
    try:
        trace_id = trace_id or str(uuid.uuid4())

        # 取得提供商
        llm_provider = llm_provider_manager.get_provider(provider)

        if not llm_provider:
            raise HTTPException(
                status_code=404,
                detail=f"提供商不存在或未選擇: {provider or '未指定'}"
            )

        # 如果未指定模型，使用第一個可用模型
        if not model:
            models = await llm_provider.list_models()
            if not models:
                raise HTTPException(
                    status_code=400,
                    detail="沒有可用的模型"
                )
            model = models[0].id
            logger.info(f"自動選擇模型: {model}")

        # 加入機器人上下文到提示
        enhanced_prompt = f"使用者對機器人 {robot_id} 說: {prompt}"

        # 呼叫 LLM
        logger.info(f"呼叫 LLM: provider={llm_provider.provider_name}, model={model}, use_tools={use_tools}")

        response_text, confidence = await llm_provider.generate(
            prompt=enhanced_prompt,
            model=model,
            temperature=0.3,
            max_tokens=500,
            use_tools=use_tools,
            trace_id=trace_id
        )

        return {
            "trace_id": trace_id,
            "robot_id": robot_id,
            "provider": llm_provider.provider_name,
            "model": model,
            "prompt": prompt,
            "response": response_text,
            "confidence": confidence,
            "tools_used": use_tools,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"LLM 呼叫失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@v1_router.get("/llm/tools")
@app.get("/api/llm/tools")
async def get_mcp_tools():
    """取得可用的 MCP 工具定義"""
    try:
        tools = mcp_tool_interface.get_tool_definitions()

        return {
            "tools": tools,
            "count": len(tools),
            "formats": {
                "openai": "標準 OpenAI function calling 格式",
                "ollama": "Ollama 工具格式"
            }
        }
    except Exception as e:
        logger.error(f"取得工具定義失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@v1_router.get("/llm/providers")
@app.get("/api/llm/providers")
async def list_llm_providers():
    """列出所有已註冊的 LLM 提供商"""
    try:
        providers = llm_provider_manager.list_providers()
        selected = llm_provider_manager.get_selected_provider_name()

        return {
            "providers": providers,
            "selected": selected,
            "count": len(providers)
        }
    except Exception as e:
        logger.error(f"列出 LLM 提供商失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@v1_router.get("/llm/providers/health")
@app.get("/api/llm/providers/health")
async def get_providers_health():
    """取得所有提供商的健康狀態"""
    try:
        health_results = await llm_provider_manager.get_all_provider_health()

        # 將 ProviderHealth 物件轉換為字典
        health_dict = {
            name: {
                "status": health.status.value,
                "version": health.version,
                "available_models": health.available_models,
                "error_message": health.error_message,
                "response_time_ms": health.response_time_ms
            }
            for name, health in health_results.items()
        }

        return {
            "providers": health_dict,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"取得提供商健康狀態失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@v1_router.post("/llm/providers/discover")
@app.post("/api/llm/providers/discover")
async def discover_llm_providers(host: str = "localhost", timeout: int = 5):
    """手動觸發提供商偵測"""
    try:
        logger.info(f"手動觸發 LLM 提供商偵測 (host={host}, timeout={timeout})")

        health_results = await llm_provider_manager.discover_providers(host, timeout)

        # 轉換為字典格式
        health_dict = {
            name: {
                "status": health.status.value,
                "version": health.version,
                "available_models": health.available_models,
                "error_message": health.error_message,
                "response_time_ms": health.response_time_ms
            }
            for name, health in health_results.items()
        }

        available_count = len([h for h in health_results.values() if h.status.value == "available"])

        return {
            "discovered": health_dict,
            "available_count": available_count,
            "total_count": len(health_results),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"偵測 LLM 提供商失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@v1_router.post("/llm/providers/select")
@app.post("/api/llm/providers/select")
async def select_llm_provider(provider_name: str):
    """選擇要使用的 LLM 提供商"""
    try:
        success = llm_provider_manager.select_provider(provider_name)

        if not success:
            raise HTTPException(status_code=404, detail=f"提供商 '{provider_name}' 不存在")

        logger.info(f"已切換到 LLM 提供商: {provider_name}")

        return {
            "message": "提供商切換成功",
            "provider": provider_name
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"選擇 LLM 提供商失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@v1_router.get("/llm/providers/{provider_name}/models")
@app.get("/api/llm/providers/{provider_name}/models")
async def list_provider_models(provider_name: str):
    """列出特定提供商的可用模型"""
    try:
        provider = llm_provider_manager.get_provider(provider_name)

        if not provider:
            raise HTTPException(status_code=404, detail=f"提供商 '{provider_name}' 不存在")

        models = await provider.list_models()

        # 轉換為字典格式
        models_dict = [
            {
                "id": model.id,
                "name": model.name,
                "size": model.size,
                "capabilities": {
                    "supports_streaming": model.capabilities.supports_streaming,
                    "supports_vision": model.capabilities.supports_vision,
                    "supports_function_calling": model.capabilities.supports_function_calling,
                    "context_length": model.capabilities.context_length,
                    "max_tokens": model.capabilities.max_tokens
                },
                "metadata": model.metadata
            }
            for model in models
        ]

        return {
            "provider": provider_name,
            "models": models_dict,
            "count": len(models_dict)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"列出提供商模型失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@v1_router.post("/llm/providers/{provider_name}/refresh")
@app.post("/api/llm/providers/{provider_name}/refresh")
async def refresh_provider_health(provider_name: str):
    """重新檢查特定提供商的健康狀態"""
    try:
        health = await llm_provider_manager.refresh_provider(provider_name)

        if not health:
            raise HTTPException(status_code=404, detail=f"提供商 '{provider_name}' 不存在")

        return {
            "provider": provider_name,
            "status": health.status.value,
            "version": health.version,
            "available_models": health.available_models,
            "error_message": health.error_message,
            "response_time_ms": health.response_time_ms,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"重新檢查提供商健康狀態失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ===== 連線狀態與警告 API =====

@v1_router.get("/llm/connection/status")
@app.get("/api/llm/connection/status")
async def get_connection_status():
    """
    取得 LLM 連線狀態
    
    Returns:
        包含網路狀態、本地 LLM 狀態和回退狀態的資訊
    """
    try:
        # 檢查網路連線
        internet_available = await llm_processor.check_internet_connection_async()

        # 取得連線狀態摘要
        status = llm_processor.get_connection_status()

        return {
            "internet_available": internet_available,
            "local_llm_available": status["local_llm_available"],
            "local_llm_provider": status["local_llm_provider"],
            "using_fallback": status["using_fallback"],
            "warnings_count": status["warnings_count"],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"取得連線狀態失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="取得連線狀態時發生內部錯誤")


@v1_router.get("/llm/warnings")
@app.get("/api/llm/warnings")
async def get_llm_warnings(clear: bool = False):
    """
    取得 LLM 相關警告訊息
    
    Args:
        clear: 是否在取得後清除警告
        
    Returns:
        警告列表
    """
    try:
        warnings = llm_processor.get_warnings(clear=clear)

        return {
            "warnings": warnings,
            "count": len(warnings),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"取得警告訊息失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="取得警告訊息時發生內部錯誤")


@v1_router.delete("/llm/warnings")
@app.delete("/api/llm/warnings")
async def clear_llm_warnings():
    """清除所有 LLM 相關警告"""
    try:
        llm_processor.clear_warnings()

        return {
            "message": "警告已清除",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"清除警告失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="清除警告時發生內部錯誤")


@v1_router.get("/llm/check-internet")
@app.get("/api/llm/check-internet")
async def check_internet_connection():
    """
    檢查網路連線狀態
    
    Returns:
        網路連線狀態
    """
    try:
        is_available = await llm_processor.check_internet_connection_async()

        return {
            "internet_available": is_available,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"檢查網路連線失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="檢查網路連線時發生內部錯誤")


# ===== 插件管理 API =====

@v1_router.get("/plugins")
@app.get("/api/plugins")
async def list_plugins(
    plugin_type: Optional[str] = None,
    status: Optional[str] = None
):
    """列出所有插件"""
    try:
        from .plugin_base import PluginType, PluginStatus

        # 轉換參數
        ptype = PluginType(plugin_type) if plugin_type else None
        pstatus = PluginStatus(status) if status else None

        plugins = plugin_manager.list_plugins(ptype, pstatus)

        # 取得詳細資訊
        plugin_details = []
        for name in plugins:
            plugin = plugin_manager.get_plugin(name)
            if plugin:
                plugin_details.append({
                    "name": plugin.metadata.name,
                    "version": plugin.metadata.version,
                    "type": plugin.metadata.plugin_type.value,
                    "status": plugin.status.value,
                    "description": plugin.metadata.description,
                    "enabled": plugin.config.enabled,
                    "priority": plugin.config.priority
                })

        return {
            "plugins": plugin_details,
            "count": len(plugin_details)
        }

    except Exception as e:
        logger.error(f"列出插件失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@v1_router.get("/plugins/health")
@app.get("/api/plugins/health")
async def get_plugins_health():
    """取得所有插件的健康狀態"""
    try:
        health_results = await plugin_manager.get_all_plugin_health()

        return {
            "plugins": health_results,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"取得插件健康狀態失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@v1_router.get("/plugins/{plugin_name}/commands")
@app.get("/api/plugins/{plugin_name}/commands")
async def get_plugin_commands(plugin_name: str):
    """取得插件支援的指令列表"""
    try:
        commands = plugin_manager.get_supported_commands(plugin_name)

        if commands is None:
            raise HTTPException(status_code=404, detail=f"插件不存在: {plugin_name}")

        # 取得每個指令的 schema
        command_details = []
        for cmd in commands:
            schema = plugin_manager.get_command_schema(plugin_name, cmd)
            command_details.append({
                "name": cmd,
                "schema": schema
            })

        return {
            "plugin": plugin_name,
            "commands": command_details,
            "count": len(commands)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"取得插件指令失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@v1_router.post("/plugins/{plugin_name}/execute")
@app.post("/api/plugins/{plugin_name}/execute")
async def execute_plugin_command(
    plugin_name: str,
    command_name: str,
    parameters: Dict[str, Any],
    trace_id: Optional[str] = None
):
    """透過插件執行指令"""
    try:
        trace_id = trace_id or str(uuid.uuid4())

        context = {
            "trace_id": trace_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        result = await plugin_manager.execute_command(
            plugin_name=plugin_name,
            command_name=command_name,
            parameters=parameters,
            context=context
        )

        return {
            "trace_id": trace_id,
            "plugin": plugin_name,
            "command": command_name,
            "result": result,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"執行插件指令失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@v1_router.get("/devices/{device_name}/info")
@app.get("/api/devices/{device_name}/info")
async def get_device_info(device_name: str):
    """取得裝置資訊"""
    try:
        device = plugin_manager.get_device_plugin(device_name)

        if not device:
            raise HTTPException(status_code=404, detail=f"裝置不存在: {device_name}")

        info = await device.get_device_info()

        return {
            "device": device_name,
            "info": info,
            "status": device.status.value
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"取得裝置資訊失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@v1_router.post("/devices/{device_name}/read")
@app.post("/api/devices/{device_name}/read")
async def read_device_data(
    device_name: str,
    parameters: Optional[Dict[str, Any]] = None
):
    """讀取裝置資料"""
    try:
        parameters = parameters or {}

        data = await plugin_manager.read_device_data(
            plugin_name=device_name,
            **parameters
        )

        return {
            "device": device_name,
            "data": data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"讀取裝置資料失敗: {e}", exc_info=True)
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
