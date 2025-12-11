# LLM IPC Bridge 架構文件

## 概覽

LLM IPC Bridge 是連接 LLM 和專案之間的橋樑，使用 MCP (Model Context Protocol) 作為通訊協定，提供真實的 HTTP/IPC 呼叫實作。

## 架構圖

```
┌─────────────┐         ┌──────────────────┐         ┌──────────────┐
│             │         │  LLM IPC         │         │              │
│  LLM        │◄────────│  Bridge          │────────►│  Project     │
│  (Claude,   │  MCP    │                  │  HTTP   │  (Robot      │
│   GPT, etc) │ Protocol│  - Discovery     │  /IPC   │   Console)   │
│             │         │  - Translation   │         │              │
│             │         │  - HTTP Client   │         │              │
└─────────────┘         └──────────────────┘         └──────────────┘
     ▲                          ▲                           ▲
     │                          │                           │
     │                          │                           │
  OpenAI              MCP JSON-RPC 2.0            Skills Implementation
  Function                                        (robot_command, etc.)
  Calling
```

## 核心元件

### 1. LLMIPCBridge

主要橋樑類別，負責：
- 接收 LLM function calls
- 發現可用的 llm-cop providers
- 透過 HTTP 呼叫 skills
- 返回結果給 LLM

**功能：**
- `call_from_llm()` - 從 LLM 呼叫專案功能
- `expose_to_llm()` - 將專案 skills 暴露給 LLM
- `health_check()` - 檢查 provider 健康狀態
- `list_available_skills()` - 列出所有可用 skills

**HTTP 實作特色：**
- 使用 `aiohttp` 進行非同步 HTTP 請求
- 支援超時控制（預設 30 秒）
- 自動重試機制（最多 3 次）
- 指數退避策略
- 連接池管理

### 2. MCPAdapter

MCP 協定適配器，負責：
- JSON-RPC 2.0 請求編碼
- JSON-RPC 2.0 回應解碼
- 請求/回應驗證
- 錯誤處理

**JSON-RPC 2.0 格式：**

請求：
```json
{
  "jsonrpc": "2.0",
  "id": "req-1234567890.123",
  "method": "invoke",
  "params": {
    "robot_id": "robot-001",
    "action": "go_forward"
  }
}
```

回應（成功）：
```json
{
  "jsonrpc": "2.0",
  "id": "req-1234567890.123",
  "result": {
    "status": "success",
    "command_id": "cmd-abc123"
  }
}
```

回應（錯誤）：
```json
{
  "jsonrpc": "2.0",
  "id": "req-1234567890.123",
  "error": {
    "code": -32001,
    "message": "Skill not found"
  }
}
```

### 3. SkillTranslator

Skills 格式轉換器，負責：
- Project Skill → OpenAI Function Definition
- OpenAI Function Call → Project Skill Invocation
- Skill Result → OpenAI Function Response
- 參數驗證和標準化

## 使用範例

### 基本使用

```python
from llm_discovery import LLMIPCBridge

# 建立橋樑
async with LLMIPCBridge(project_endpoint="http://localhost:9001") as bridge:
    # 從 LLM 呼叫專案功能
    result = await bridge.call_from_llm({
        "name": "robot_command",
        "arguments": {
            "robot_id": "robot-001",
            "action": "go_forward",
            "params": {"duration_ms": 3000}
        }
    })
    
    print(result)
    # {
    #   "success": True,
    #   "result": {"status": "success", "command_id": "cmd-123"},
    #   "error": None
    # }
```

### 暴露 Skills 給 LLM

```python
# 取得所有可用的 skills（OpenAI function calling 格式）
functions = await bridge.expose_to_llm()

# 使用 functions 與 LLM
response = openai.ChatCompletion.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "讓機器人向前移動"}],
    functions=functions
)

# 執行 LLM 返回的 function call
if response.choices[0].message.get("function_call"):
    function_call = response.choices[0].message["function_call"]
    result = await bridge.call_from_llm(function_call)
```

### 健康檢查

```python
# 檢查特定 provider 的健康狀態
health = await bridge.health_check("mcp-robot-service")

print(health)
# {
#   "healthy": True,
#   "status": "healthy",
#   "response_time_ms": 15.3,
#   "last_check": "2025-01-01T00:00:00",
#   "consecutive_failures": 0
# }
```

### 列出可用 Skills

```python
# 列出所有 provider 的 skills
skills = await bridge.list_available_skills()

print(skills)
# {
#   "mcp-robot-service": [
#     "robot_command",
#     "robot_status",
#     "service_control",
#     "system_health"
#   ]
# }
```

## HTTP/IPC 通訊流程

### 1. Skill 調用流程

```
LLM Function Call
    ↓
Bridge.call_from_llm()
    ↓
Discovery.scan_providers() ────► 找到 provider
    ↓
SkillTranslator.normalize() ────► 標準化參數
    ↓
MCPAdapter.encode_request() ────► 編碼為 JSON-RPC 2.0
    ↓
HTTP POST /invoke/{skill_id} ───► 發送 HTTP 請求
    ↓
[等待回應，支援超時和重試]
    ↓
HTTP Response ──────────────────► 接收回應
    ↓
MCPAdapter.decode_response() ───► 解碼 JSON-RPC 2.0
    ↓
SkillTranslator.to_openai() ────► 轉換為 OpenAI 格式
    ↓
Return to LLM
```

### 2. 錯誤處理

```python
try:
    result = await bridge.call_from_llm(function_call)
    
    if result["success"]:
        # 成功
        print(result["result"])
    else:
        # 業務邏輯錯誤
        print(f"Error: {result['error']}")
        
except asyncio.TimeoutError:
    # HTTP 請求超時
    print("Request timeout")
    
except aiohttp.ClientError as e:
    # 網路錯誤
    print(f"Network error: {e}")
```

### 3. 重試策略

Bridge 自動處理以下情況的重試：
- HTTP 5xx 錯誤（伺服器錯誤）
- 網路連接錯誤
- 超時錯誤

重試配置：
- 最大重試次數：3 次
- 退避策略：指數退避（2^retry_count 秒）
- 可重試的狀態碼：500, 502, 503, 504

## 進階配置

### 自訂超時和重試

```python
bridge = LLMIPCBridge(
    project_endpoint="http://localhost:9001",
    timeout=60,  # 60 秒超時
    max_retries=5  # 最多重試 5 次
)
```

### 使用 Context Manager

```python
# 自動管理 HTTP session
async with LLMIPCBridge() as bridge:
    result = await bridge.call_from_llm(function_call)
# session 自動關閉
```

### 手動管理 Session

```python
bridge = LLMIPCBridge()

try:
    result = await bridge.call_from_llm(function_call)
finally:
    await bridge.close()  # 手動關閉 session
```

## 安全考量

### 1. 參數驗證

所有 skill 參數都會根據 JSON Schema 進行驗證：

```python
# 在 skill definition 中定義 schema
skill = {
    "id": "robot_command",
    "parameters": {
        "type": "object",
        "properties": {
            "robot_id": {"type": "string"},
            "action": {"type": "string"}
        },
        "required": ["robot_id", "action"]
    }
}

# Bridge 自動驗證
result = await bridge.call_from_llm({
    "name": "robot_command",
    "arguments": {"robot_id": "robot-001"}  # 缺少 action
})
# 返回：{"success": False, "error": "Parameter validation failed"}
```

### 2. 超時保護

所有 HTTP 請求都有超時限制，防止長時間等待：

```python
# 預設 30 秒超時
bridge = LLMIPCBridge(timeout=30)
```

### 3. 錯誤隔離

Bridge 捕獲並處理所有異常，不會影響主程式：

```python
result = await bridge.call_from_llm(function_call)
# 永遠返回標準格式，不會拋出異常
# {"success": bool, "result": Any, "error": Optional[str]}
```

## 效能優化

### 1. 連接池

Bridge 使用 `aiohttp.ClientSession` 管理 HTTP 連接池：
- 自動重用連接
- 支援 HTTP Keep-Alive
- 減少連接建立開銷

### 2. 非同步處理

所有操作都是非同步的，支援高並發：

```python
# 並行呼叫多個 skills
results = await asyncio.gather(
    bridge.call_from_llm(function_call_1),
    bridge.call_from_llm(function_call_2),
    bridge.call_from_llm(function_call_3)
)
```

### 3. 快取機制

Discovery Service 快取 provider manifests：
- 減少檔案系統掃描
- 快取健康狀態檢查結果

## 測試

### 單元測試

```python
import pytest
from llm_discovery import LLMIPCBridge

@pytest.mark.asyncio
async def test_call_from_llm():
    async with LLMIPCBridge() as bridge:
        result = await bridge.call_from_llm({
            "name": "robot_command",
            "arguments": {"robot_id": "robot-001", "action": "go_forward"}
        })
        
        assert result["success"] is True
        assert result["error"] is None
```

### 整合測試

```python
@pytest.mark.asyncio
async def test_end_to_end():
    async with LLMIPCBridge() as bridge:
        # 1. 列出 skills
        skills = await bridge.list_available_skills()
        assert "mcp-robot-service" in skills
        
        # 2. 檢查健康狀態
        health = await bridge.health_check("mcp-robot-service")
        assert health["healthy"] is True
        
        # 3. 呼叫 skill
        result = await bridge.call_from_llm({
            "name": "robot_command",
            "arguments": {"robot_id": "robot-001", "action": "go_forward"}
        })
        assert result["success"] is True
```

## 故障排除

### 問題：連接被拒絕

```
Error: Connection refused
```

**解決方案：**
1. 確認專案服務正在運行
2. 檢查端點 URL 是否正確
3. 檢查防火牆設定

### 問題：請求超時

```
Error: Request timeout
```

**解決方案：**
1. 增加超時時間：`LLMIPCBridge(timeout=60)`
2. 檢查網路連線
3. 檢查專案服務是否響應緩慢

### 問題：Skill 未找到

```
Error: Skill 'xxx' not found
```

**解決方案：**
1. 確認 provider manifest 已註冊
2. 執行 `scan_providers()` 重新掃描
3. 檢查 skill ID 是否正確

## 相關資源

- [MCP Protocol Specification](../implementation/llm_ipc_protocol.md)
- [LLM IPC Quick Start](../implementation/LLM_IPC_README.md)
- [Skills Implementation Guide](../../MCP/skills/README.md)

## 貢獻

歡迎貢獻改進！請：
1. Fork 專案
2. 建立 feature branch
3. 提交 Pull Request

## 授權

MIT License
