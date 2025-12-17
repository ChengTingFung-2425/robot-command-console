# TUI + LLM Integration Lessons

此文件包含 TUI 與 LLM 自然語言控制整合的詳細經驗教訓。

包含：Textual 框架、LLM 整合、自然語言處理等經驗。

## 📚 相關文件

- **[← 返回主記憶](../PROJECT_MEMORY.md)** - Top 15 關鍵經驗
- **[Phase 3 經驗](phase3_lessons.md)** - 服務整合
- **[安全性](security_lessons.md)** - 提示注入防護、輸入驗證
- **[代碼品質](code_quality_lessons.md)** - 測試策略

---

## 🎨 TUI + LLM 自然語言控制整合（2025-12-11）

> 📖 **詳細指南**：[development/TUI_LLM_INTEGRATION_GUIDE.md](development/TUI_LLM_INTEGRATION_GUIDE.md)

### 功能實作總結

**目標**：建立完整的 TUI 與 LLM 自然語言控制系統，實現「人類自然語言 → LLM 理解 → 真實機器人執行」的完整流程。

**實作模組**：
1. **TUI 核心**（`src/robot_service/tui/`）- Textual 終端介面
2. **LLM IPC Bridge**（`src/llm_discovery/bridge.py`）- 真實 HTTP 橋樑
3. **LLM Command Processor**（`src/robot_service/llm_command_processor.py`）- 自然語言處理
4. **Robot Action Consumer**（`src/robot_service/robot_action_consumer.py`）- 真實機器人整合
5. **LLM Trace Manager**（`src/robot_service/llm_trace_manager.py`）- 完整追蹤系統
6. **WebUI GUI**（`WebUI/templates/llm_*.html`）- 圖形化介面

**測試覆蓋**：37 個 TUI 測試，100% 通過

---

### 12.1 真實 HTTP/IPC 呼叫實作

```python
# ✅ 使用 aiohttp 實作真實 HTTP 請求
async with aiohttp.ClientSession() as session:
    response = await session.post(
        f"{endpoint}/invoke/{skill_id}",
        json={"jsonrpc": "2.0", "method": "invoke", "params": parameters},
        timeout=aiohttp.ClientTimeout(total=30)
    )
    result = await response.json()
```

**經驗教訓**：
1. **連接池管理**：重用 HTTP 會話以提升效能
2. **超時控制**：所有請求都應設定超時（預設 30 秒）
3. **自動重試**：5xx 錯誤自動重試（指數退避，最多 3 次）
4. **錯誤隔離**：HTTP 錯誤不應影響主程式

---

### 12.2 LLM 自然語言處理流程

```python
# ✅ 完整的 LLM 處理流程
async def process_text_command(self, text: str) -> Dict:
    # 1. 建立追蹤
    trace_id = self.trace_manager.start_trace()
    
    # 2. 記錄輸入
    self.trace_manager.log_event(trace_id, INPUT_RECEIVED, {"text": text})
    
    # 3. 呼叫 LLM
    response = await self.llm_provider.chat_completion(
        messages=self.conversation_history + [{"role": "user", "content": text}],
        functions=self.available_functions
    )
    
    # 4. 執行 function call
    if response.get("function_call"):
        result = await self.bridge.call_from_llm(response["function_call"])
    
    # 5. 更新對話歷史
    self.conversation_history.append(...)
    
    return {"trace_id": trace_id, "result": result}
```

**經驗教訓**：
1. **對話歷史**：維護最近 10 條對話以提供上下文
2. **追蹤貫穿**：每個步驟都記錄追蹤事件
3. **錯誤處理**：LLM API 失敗應有友善提示
4. **超時保護**：LLM 請求可能很慢，需設定合理超時

---

### 12.3 追蹤系統設計模式

```python
# ✅ 10 種追蹤事件涵蓋完整流程
INPUT_RECEIVED    → 收到輸入
LLM_REQUEST       → LLM 請求
LLM_RESPONSE      → LLM 回應
FUNCTION_CALL     → Function call
BRIDGE_CALL       → Bridge HTTP 呼叫
FUNCTION_EXECUTED → Function 執行完成
QUEUE_ENQUEUED    → 加入佇列
ROBOT_EXECUTED    → 機器人執行
ERROR             → 錯誤
COMPLETED         → 完成
```

**經驗教訓**：
1. **完整性**：追蹤每個關鍵步驟
2. **時間戳**：記錄每個事件的時間
3. **持續時間**：計算每個階段的耗時
4. **訂閱機制**：支援即時事件訂閱

---

### 12.4 真實機器人整合架構

```python
# ✅ 從佇列消費動作並發送給真實機器人
class RobotActionConsumer:
    async def start(self):
        while self._running:
            # 1. 從佇列讀取
            action = await self.service_manager.dequeue()
            
            # 2. 轉換格式
            robot_command = self.translate_action(action)
            
            # 3. 發送給真實機器人
            result = await self.robot_connector.send_command(
                robot_id=action["robot_id"],
                command=robot_command
            )
            
            # 4. 回報結果
            await self.report_result(action["trace_id"], result)
```

**經驗教訓**：
1. **解耦合**：佇列作為緩衝，解耦 LLM 和機器人
2. **格式轉換**：統一的內部格式 → 機器人特定格式
3. **錯誤恢復**：機器人連接失敗應重試或通知
4. **結果回報**：執行結果應回傳給追蹤系統

---

### 12.5 WebUI GUI 設計模式

```javascript
// ✅ WebSocket 即時更新
const ws = new WebSocket('ws://localhost:5000/ws/llm');

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    if (data.type === 'trace_event') {
        updateTraceView(data.event);
    }
    
    if (data.type === 'llm_response') {
        appendMessage(data.message);
    }
};
```

**經驗教訓**：
1. **即時性**：使用 WebSocket 而非輪詢
2. **響應式**：支援桌面和行動裝置
3. **錯誤處理**：網路斷線應有明確提示
4. **使用者體驗**：Loading 狀態、Toast 通知

---

### 12.6 JSON-RPC 2.0 協定標準化

```python
# ✅ 標準 JSON-RPC 2.0 格式
request = {
    "jsonrpc": "2.0",
    "method": "invoke",
    "params": {
        "robot_id": "robot-001",
        "action": "go_forward"
    },
    "id": "req-123"
}

response = {
    "jsonrpc": "2.0",
    "result": {"status": "success", "data": ...},
    "id": "req-123"
}

# 錯誤回應
error_response = {
    "jsonrpc": "2.0",
    "error": {
        "code": -32600,
        "message": "Invalid Request"
    },
    "id": "req-123"
}
```

**經驗教訓**：
1. **標準化**：使用 JSON-RPC 2.0 提升相容性
2. **錯誤代碼**：標準錯誤代碼（-32xxx）
3. **請求 ID**：支援請求-回應對應
4. **批次請求**：可擴展支援批次操作

---

### 12.7 OpenAI Function Calling 整合

```python
# ✅ 定義 functions 供 LLM 使用
functions = [
    {
        "name": "robot_command",
        "description": "Send command to robot",
        "parameters": {
            "type": "object",
            "properties": {
                "robot_id": {"type": "string", "description": "Robot ID"},
                "action": {"type": "string", "description": "Action name"},
                "params": {"type": "object", "description": "Action parameters"}
            },
            "required": ["robot_id", "action"]
        }
    }
]

# LLM 會返回 function_call
function_call = {
    "name": "robot_command",
    "arguments": '{"robot_id": "robot-001", "action": "go_forward", "params": {"duration_ms": 3000}}'
}
```

**經驗教訓**：
1. **描述清晰**：function 和參數的描述要清楚
2. **JSON Schema**：使用標準 schema 驗證參數
3. **錯誤處理**：參數解析失敗應有友善提示
4. **多 LLM 支援**：OpenAI/Claude/Local 格式略有不同

---

### 12.8 TUI 非同步事件處理

```python
# ✅ Textual 非同步事件處理
class RobotConsoleTUI(App):
    async def on_mount(self):
        # 啟動背景任務
        self.update_task = asyncio.create_task(self._update_status())
    
    async def _update_status(self):
        while True:
            try:
                await asyncio.sleep(1)
                # 更新服務狀態
                await self.refresh_services()
            except asyncio.CancelledError:
                # 任務取消時屬預期行為，安全忽略
                break
    
    async def on_unmount(self):
        # 清理任務
        if self.update_task:
            self.update_task.cancel()
            try:
                await self.update_task
            except asyncio.CancelledError:
                pass
```

**經驗教訓**：
1. **生命週期**：正確處理 mount/unmount
2. **任務取消**：優雅處理 CancelledError
3. **異常隔離**：背景任務錯誤不應崩潰 UI
4. **資源清理**：確保所有任務正確關閉

---

### 12.9 指令解析模式設計

```python
# ✅ 清晰的指令解析邏輯
def parse_command(command: str) -> Tuple[str, str]:
    """
    解析指令類型和參數
    
    支援格式：
    - "action" → ("robot", "action")
    - "robot-id:action" → ("robot", "action")
    - "all:action" → ("broadcast", "action")
    - "system:action" → ("system", "action")
    - "service:name.action" → ("service", "name.action")
    - "llm:on/off" → ("llm", "on/off")
    - "trace:id" → ("trace", "id")
    """
    if ':' not in command:
        return ("robot", command)
    
    prefix, suffix = command.split(':', 1)
    
    if prefix in ["system", "service", "llm", "trace"]:
        return (prefix, suffix)
    elif prefix == "all":
        return ("broadcast", suffix)
    else:
        return ("robot", f"{prefix}:{suffix}")
```

**經驗教訓**：
1. **統一格式**：所有指令遵循相同格式
2. **向後相容**：無前綴指令預設為機器人指令
3. **清晰文件**：docstring 說明所有支援格式
4. **錯誤處理**：無效格式應有友善提示

---

### 12.10 多 LLM 提供商抽象

```python
# ✅ 提供商抽象介面
class LLMProviderBase(ABC):
    @abstractmethod
    async def chat_completion(
        self,
        messages: List[Dict],
        functions: Optional[List[Dict]] = None
    ) -> Dict:
        pass

# OpenAI 實作
class OpenAIProvider(LLMProviderBase):
    async def chat_completion(self, messages, functions=None):
        response = await openai.ChatCompletion.acreate(
            model="gpt-4",
            messages=messages,
            functions=functions
        )
        return response

# Claude 實作（待實作）
class ClaudeProvider(LLMProviderBase):
    async def chat_completion(self, messages, functions=None):
        # 轉換為 Claude 格式
        # 呼叫 Anthropic API
        pass

# 本地 LLM 實作（待實作）
class LocalLLMProvider(LLMProviderBase):
    async def chat_completion(self, messages, functions=None):
        # 呼叫 Ollama/LM Studio
        pass
```

**經驗教訓**：
1. **抽象介面**：定義統一的介面
2. **格式轉換**：每個提供商負責格式轉換
3. **錯誤統一**：將不同錯誤轉換為統一格式
4. **易擴展**：新增提供商只需實作介面

---

### 12.11 記憶體管理與清理

```python
# ✅ LRU 快取防止記憶體洩漏
class LLMTraceManager:
    def __init__(self, max_traces: int = 1000):
        self._traces: OrderedDict[str, List[TraceEvent]] = OrderedDict()
        self.max_traces = max_traces
    
    def add_event(self, trace_id: str, event: TraceEvent):
        # 超過限制時移除最舊的追蹤
        if len(self._traces) >= self.max_traces:
            self._traces.popitem(last=False)
        
        if trace_id not in self._traces:
            self._traces[trace_id] = []
        
        self._traces[trace_id].append(event)
```

**經驗教訓**：
1. **大小限制**：設定最大追蹤數量
2. **LRU 策略**：自動移除最舊的記錄
3. **定期清理**：提供手動清理方法
4. **監控**：記錄當前使用量

---

### 12.12 API 錯誤處理最佳實踐

```python
# ✅ 統一的 API 錯誤處理
@bp.route('/api/llm/chat', methods=['POST'])
async def chat():
    try:
        # 1. 參數驗證
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({
                'status': 'error',
                'error': {
                    'code': 'INVALID_PARAMETER',
                    'message': 'Missing required field: message'
                }
            }), 400
        
        # 2. 業務邏輯
        result = await process_message(data['message'])
        
        # 3. 成功回應
        return jsonify({
            'status': 'success',
            'data': result
        })
    
    except Exception as e:
        # 4. 記錄詳細錯誤
        logger.error(f"Error in chat API: {e}", exc_info=True)
        
        # 5. 回傳通用錯誤（不暴露內部資訊）
        return jsonify({
            'status': 'error',
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'An internal error has occurred.'
            }
        }), 500
```

**經驗教訓**：
1. **參數驗證在前**：先驗證再處理
2. **4xx vs 5xx**：客戶端錯誤 vs 伺服器錯誤
3. **詳細日誌**：使用 `exc_info=True` 記錄堆疊
4. **通用錯誤訊息**：不暴露內部實作細節
5. **統一格式**：所有 API 使用相同的錯誤格式

---

### 12.13 WebSocket 生命週期管理

```python
# ✅ WebSocket 連接管理
class LLMWebSocketHandler:
    def __init__(self):
        self.connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.connections.add(websocket)
    
    async def disconnect(self, websocket: WebSocket):
        self.connections.discard(websocket)
    
    async def broadcast(self, message: Dict):
        # 移除已斷線的連接
        dead_connections = set()
        
        for connection in self.connections:
            try:
                await connection.send_json(message)
            except Exception:
                dead_connections.add(connection)
        
        # 清理斷線連接
        self.connections -= dead_connections
```

**經驗教訓**：
1. **連接追蹤**：維護活躍連接集合
2. **斷線處理**：broadcast 時檢測並清理斷線
3. **優雅關閉**：disconnect 時正確移除
4. **錯誤隔離**：單一連接錯誤不影響其他

---

### 12.14 環境變數配置管理

```python
# ✅ 使用環境變數配置
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
OLLAMA_ENDPOINT = os.environ.get("OLLAMA_ENDPOINT", "http://127.0.0.1:11434")
MCP_ENDPOINT = os.environ.get("MCP_ENDPOINT", "http://127.0.0.1:9001")

# ✅ 配置驗證
if not OPENAI_API_KEY:
    logger.warning("OPENAI_API_KEY not set, OpenAI provider will not be available")
```

**經驗教訓**：
1. **環境變數**：敏感資訊不寫入程式碼
2. **合理預設值**：本地開發常用值作為預設
3. **配置驗證**：啟動時檢查必要配置
4. **文件記錄**：在 README 列出所有環境變數

---

### 12.15 程式碼審查自動化回饋

**本次 PR 實作規模**：
- **新增檔案**：11 個（~4500 行）
- **修改檔案**：3 個（~150 行）
- **測試**：37 個（100% 通過）
- **文件**：5 個（~2000 行）

**Code Review 發現**：
- 無重大問題
- 建議加強錯誤處理測試（已完成）
- 建議完善文件（已完成）

**經驗教訓**：
1. **早期 Review**：在實作過程中持續 review
2. **自動化工具**：flake8、mypy 自動檢查
3. **文件同步**：程式碼與文件同步更新
4. **測試覆蓋**：TDD 方式確保測試完整

---

