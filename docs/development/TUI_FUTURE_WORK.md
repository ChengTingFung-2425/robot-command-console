# TUI 後續實作待辦事項

## 已完成 ✅

1. **PR Review 修正** (commit 0ecfdff)
   - 導入路徑一致性
   - 型別提示相容性
   - TODO 註解詳細化
   - 服務詳情功能實作
   - 錯誤處理測試
   - 文件改進

2. **核心 TUI 功能**
   - 服務狀態監控
   - 系統管理指令 (list/show/healthcheck)
   - 服務管理指令 (start/stop/restart/healthcheck)
   - 指令解析與歷史記錄

## 待實作功能

### 1. 機器人指令發送邏輯 🔨

**目標：** 完整實作機器人指令的實際發送與執行

**需要整合的元件：**
- `CommandProcessor` - 指令處理器
- `QueueService` - 佇列服務
- `SharedStateManager` - 狀態管理

**實作步驟：**

#### 1.1 建立 CommandSender 類別
```python
class CommandSender:
    """TUI 指令發送器"""
    
    def __init__(self, queue_service, state_manager):
        self.queue_service = queue_service
        self.state_manager = state_manager
    
    async def send_command(self, robot_id: str, action: str, params: Dict = None):
        """發送指令到指定機器人"""
        # 建立 CommandRequest
        # 加入佇列
        # 返回指令 ID
    
    async def broadcast_command(self, action: str, params: Dict = None):
        """廣播指令到所有機器人"""
        # 取得所有機器人清單
        # 對每個機器人發送指令
```

#### 1.2 整合到 TUI
```python
# 在 RobotConsoleTUI.__init__ 加入
self.command_sender = CommandSender(queue_service, state_manager)

# 在 on_input_submitted 實作實際發送
async def on_input_submitted(self, event):
    # ...
    if robot_id == "all":
        command_id = await self.command_sender.broadcast_command(action)
        history.add_command(timestamp, "all robots", action, "sending")
    else:
        command_id = await self.command_sender.send_command(robot_id, action)
        history.add_command(timestamp, robot_id, action, "sending")
```

#### 1.3 監聽指令執行結果
```python
async def _on_command_completed(self, event_data):
    """更新指令歷史狀態"""
    command_id = event_data["command_id"]
    status = event_data["status"]
    # 更新 CommandHistoryWidget 顯示
```

### 2. LLM 提供商 IPC 整合 🔨

**目標：** 使用 IPC 協定設定 LLM 提供商，並以現有邏輯作為後備

**參考文件：**
- `docs/implementation/LLM_IPC_README.md`
- `docs/implementation/llm_ipc_protocol.md`

**實作步驟：**

#### 2.1 檢查 IPC 可用性
```python
async def _handle_llm_provider(self, provider_name: str) -> None:
    """設定 LLM 提供商（優先使用 IPC）"""
    
    # 1. 嘗試 IPC 方式（Electron 環境）
    if await self._try_ipc_llm_config(provider_name):
        self.notify(f"LLM provider set via IPC: {provider_name}", severity="information")
        return
    
    # 2. 後備：直接整合 LLMProviderManager
    if await self._try_direct_llm_config(provider_name):
        self.notify(f"LLM provider set: {provider_name}", severity="information")
        return
    
    # 3. 失敗處理
    self.notify(f"Failed to set LLM provider: {provider_name}", severity="error")
```

#### 2.2 IPC 通訊實作
```python
async def _try_ipc_llm_config(self, provider_name: str) -> bool:
    """透過 IPC 設定 LLM 提供商"""
    try:
        # 檢查是否在 Electron 環境
        if not self._is_electron_env():
            return False
        
        # 發送 IPC 訊息
        response = await self._send_ipc_message({
            "type": "llm:set_provider",
            "provider": provider_name
        })
        
        return response.get("success", False)
    except Exception as e:
        logger.warning(f"IPC LLM config failed: {e}")
        return False
```

#### 2.3 直接整合後備
```python
async def _try_direct_llm_config(self, provider_name: str) -> bool:
    """直接整合 LLMProviderManager"""
    try:
        from MCP.llm_provider_manager import LLMProviderManager
        
        # 取得或建立 manager 實例
        if not hasattr(self, '_llm_manager'):
            self._llm_manager = LLMProviderManager()
        
        # 設定提供商
        success = await self._llm_manager.select_provider(provider_name)
        return success
    except Exception as e:
        logger.error(f"Direct LLM config failed: {e}")
        return False
```

### 3. 雲端路由控制實作 🔨

**目標：** 整合 OfflineQueueService 的雲端路由控制

**實作步驟：**

#### 3.1 取得 OfflineQueueService 實例
```python
async def _handle_queue_cloud(self, action: str) -> None:
    """處理佇列雲端路由控制"""
    if action not in ["on", "off"]:
        raise ValueError(f"Invalid cloud action: {action}")
    
    enabled = (action == "on")
    
    # 取得佇列服務
    queue_service = self._get_queue_service()
    if not queue_service:
        self.notify("Queue service not available", severity="error")
        return
    
    # 設定雲端路由
    if hasattr(queue_service, 'set_cloud_routing'):
        await queue_service.set_cloud_routing(enabled)
        status = "enabled" if enabled else "disabled"
        self.notify(f"Cloud routing {status}", severity="information")
    else:
        self.notify("Cloud routing not supported by queue service", severity="warning")
```

#### 3.2 服務查找
```python
def _get_queue_service(self):
    """取得佇列服務實例"""
    if not self.coordinator:
        return None
    
    # 從協調器取得佇列服務
    services = self.coordinator.get_all_services()
    for service in services.values():
        if isinstance(service, (QueueService, OfflineQueueService)):
            return service
    
    return None
```

### 4. 機器人狀態即時更新 🔨

**目標：** 從 SharedStateManager 取得實際機器人狀態

**實作步驟：**

#### 4.1 訂閱狀態事件
```python
async def on_mount(self) -> None:
    """應用啟動時"""
    # 訂閱機器人狀態更新事件
    if self.state_manager:
        await self.state_manager.subscribe(
            EventTopics.ROBOT_STATUS_UPDATED,
            self._on_robot_status_updated
        )
```

#### 4.2 更新處理
```python
async def _on_robot_status_updated(self, event_data):
    """處理機器人狀態更新事件"""
    robot_id = event_data.get("robot_id")
    status = event_data.get("status")
    
    robot_widget = self.query_one("#robots", RobotStatusWidget)
    robot_widget.update_robot_status(robot_id, status)
```

#### 4.3 初始載入
```python
async def _refresh_robots(self) -> None:
    """刷新機器人狀態"""
    if not self.state_manager:
        return
    
    robot_widget = self.query_one("#robots", RobotStatusWidget)
    
    # 從 StateManager 取得所有機器人
    robot_ids = await self.state_manager.get_robot_list()
    
    for robot_id in robot_ids:
        status = await self.state_manager.get_robot_status(robot_id)
        if status:
            robot_widget.update_robot_status(robot_id, status)
```

## 實作優先順序

1. **高優先級：** 機器人指令發送邏輯（核心功能）
2. **中優先級：** 機器人狀態即時更新（用戶體驗）
3. **中優先級：** LLM 提供商 IPC 整合（進階功能）
4. **低優先級：** 雲端路由控制（特殊場景）

## 測試計畫

### 1. 指令發送測試
- 單一機器人指令發送
- 廣播指令發送
- 指令佇列處理
- 執行結果更新

### 2. LLM 提供商測試
- IPC 通訊測試
- 後備邏輯測試
- 錯誤處理測試

### 3. 狀態更新測試
- 事件訂閱測試
- 狀態同步測試
- UI 更新測試

## 相關文件

- `docs/proposal.md` - 系統架構
- `docs/implementation/LLM_IPC_README.md` - LLM IPC 協定
- `MCP/llm_provider_manager.py` - LLM 管理器
- `src/robot_service/queue/` - 佇列服務
- `src/common/shared_state.py` - 狀態管理

## 備註

這些功能需要深入了解現有系統架構和整合點。建議：

1. 先完成單元測試框架
2. 逐步整合每個功能
3. 保持向後相容性
4. 充分測試後再啟用

最後更新：2025-12-11
