"""
MCP FastAPI 服務
提供 HTTP API 介面
"""

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .auth_manager import AuthManager
from .command_handler import CommandHandler
from .config import MCPConfig
from .context_manager import ContextManager
from .logging_monitor import LoggingMonitor
from .models import (
    CommandRequest,
    CommandResponse,
    Event,
    Heartbeat,
    RobotRegistration,
    RobotStatus,
    StatusResponse,
)
from .robot_router import RobotRouter


# 設定日誌
logging.basicConfig(
    level=MCPConfig.LOG_LEVEL,
    format=MCPConfig.LOG_FORMAT
)
logger = logging.getLogger(__name__)


# 建立應用
app = FastAPI(
    title="MCP 服務",
    description="Model Context Protocol 服務 API",
    version="1.0.0"
)


# CORS 設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=MCPConfig.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 初始化模組
context_manager = ContextManager()
auth_manager = AuthManager()
logging_monitor = LoggingMonitor()
robot_router = RobotRouter()
command_handler = CommandHandler(
    robot_router=robot_router,
    context_manager=context_manager,
    auth_manager=auth_manager,
    logging_monitor=logging_monitor
)


@app.on_event("startup")
async def startup_event():
    """啟動事件"""
    logger.info("MCP 服務啟動中...")
    robot_router.start()
    logger.info("MCP 服務已啟動")


@app.on_event("shutdown")
async def shutdown_event():
    """關閉事件"""
    logger.info("MCP 服務關閉中...")
    await robot_router.stop()
    logger.info("MCP 服務已關閉")


# ===== 健康檢查 =====

@app.get("/health")
async def health_check():
    """健康檢查"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


# ===== 指令 API =====

@app.post("/api/command", response_model=CommandResponse)
async def create_command(request: CommandRequest):
    """建立指令"""
    try:
        response = await command_handler.process_command(request)
        return response
    except Exception as e:
        logger.error(f"處理指令失敗: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/command/{command_id}")
async def get_command_status(command_id: str):
    """查詢指令狀態"""
    status = await command_handler.get_command_status(command_id)
    if not status:
        raise HTTPException(status_code=404, detail="指令不存在")
    return status


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

@app.post("/api/robots/register")
async def register_robot(registration: RobotRegistration):
    """註冊機器人"""
    success = await robot_router.register_robot(registration)
    if not success:
        raise HTTPException(status_code=500, detail="註冊失敗")
    
    return {"message": "註冊成功", "robot_id": registration.robot_id}


@app.delete("/api/robots/{robot_id}")
async def unregister_robot(robot_id: str):
    """取消註冊機器人"""
    success = await robot_router.unregister_robot(robot_id)
    if not success:
        raise HTTPException(status_code=404, detail="機器人不存在")
    
    return {"message": "取消註冊成功", "robot_id": robot_id}


@app.post("/api/robots/heartbeat")
async def update_heartbeat(heartbeat: Heartbeat):
    """更新心跳"""
    success = await robot_router.update_heartbeat(heartbeat)
    if not success:
        raise HTTPException(status_code=404, detail="機器人未註冊")
    
    return {"message": "心跳已更新"}


@app.get("/api/robots/{robot_id}")
async def get_robot(robot_id: str):
    """取得機器人資訊"""
    robot = await robot_router.get_robot(robot_id)
    if not robot:
        raise HTTPException(status_code=404, detail="機器人不存在")
    
    return robot


@app.get("/api/robots")
async def list_robots(
    robot_type: Optional[str] = None,
    status: Optional[RobotStatus] = None
):
    """列出機器人"""
    robots = await robot_router.list_robots(robot_type=robot_type, status=status)
    return {"robots": robots, "count": len(robots)}


# ===== 事件 API =====

@app.get("/api/events")
async def get_events(
    trace_id: Optional[str] = None,
    limit: int = 100
):
    """查詢事件"""
    events = await logging_monitor.get_events(trace_id=trace_id, limit=limit)
    return {"events": events, "count": len(events)}


@app.websocket("/api/events/subscribe")
async def subscribe_events(websocket: WebSocket):
    """訂閱事件（WebSocket）"""
    await websocket.accept()
    
    async def send_event(event: Event):
        try:
            await websocket.send_json(event.dict())
        except Exception as e:
            logger.error(f"發送事件失敗: {e}")
    
    await logging_monitor.subscribe_events(send_event)
    
    try:
        while True:
            # 保持連線
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info("WebSocket 已中斷")
    finally:
        await logging_monitor.unsubscribe_events(send_event)


# ===== 指標 API =====

@app.get("/api/metrics")
async def get_metrics():
    """取得指標"""
    metrics = await logging_monitor.get_metrics()
    return metrics


# ===== 認證 API =====

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
    
    return {"token": token, "user_id": user_id, "role": role}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api:app",
        host=MCPConfig.API_HOST,
        port=MCPConfig.API_PORT,
        reload=True
    )
