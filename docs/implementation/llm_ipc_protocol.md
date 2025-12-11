# LLM IPC Discovery Protocol (Phase 3.2)

> **版本**：1.0.0  
> **狀態**：PoC 階段  
> **最後更新**：2025-12-10

## 概覽

LLM IPC Discovery Protocol 是一個跨平台的 LLM 發現與技能註冊機制，專為 Edge 環境設計。它允許本地運行的 **LLM Compatible Software（llm-cop）** 實例自動註冊其技能集（skills），並被 MCP/Robot Service 發現和安全使用。

**llm-cop（LLM Compatible Software）** 是指能夠讓 LLM 透過技能（skills）來操作軟體的相容軟體。它完全相容標準 LLM API（如 OpenAI API），使得 LLM 能夠透過 function calling 等機制來操作軟體功能，同時軟體也能提供資訊給 LLM 查詢和理解。

### 核心目標

1. **LLM Compatible Software 發現**：自動偵測本地運行的 llm-cop（LLM Compatible Software）實例
2. **技能註冊**：llm-cop 可註冊和共享其可執行的技能清單，讓 LLM 能夠操作軟體
3. **LLM 相容性**：提供標準 OpenAI-compatible API 介面，支援 function calling
4. **隱私保護**：防止 LLM 模型洩密攻擊，確保敏感資料不外洩
5. **Edge 隔離**：所有通訊限於本地 Edge 環境，不對外暴露

### 設計原則

1. **本地優先**：所有發現機制限於本地主機（127.0.0.1），保護用戶隱私
2. **跨平台**：支援 Windows (TCP)、Linux/macOS (Unix socket + TCP)
3. **輕量級**：最小化資源開銷，快速探測
4. **技能隔離**：每個 Copilot 實例獨立註冊其技能，互不干擾
5. **防洩密**：技能描述不包含敏感資訊，僅提供功能介面
6. **用戶同意**：技能註冊需明確用戶授權

## 架構

```
┌─────────────────────────────────────────────────────────────────────┐
│                   LLM Compatible Software Discovery Core             │
│  (MCP/Robot Service - Edge Layer - 負責發現與管理 llm-cop)           │
├─────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────┐    ┌──────────────────────────────┐          │
│  │ Filesystem       │    │ Endpoint Liveness Probe      │          │
│  │ Registry Scanner │    │ (TCP/Unix socket)            │          │
│  └────────┬─────────┘    └──────────┬───────────────────┘          │
│           │                          │                              │
│           └──────────┬───────────────┘                              │
│                      │                                               │
│             ┌────────▼───────────┐                                  │
│             │  Software Manager  │                                  │
│             │  • Discovery       │                                  │
│             │  • Skill Registry  │                                  │
│             │  • Privacy Guard   │                                  │
│             └────────────────────┘                                  │
└─────────────────────────────────────────────────────────────────────┘
                       │
                       │ IPC (localhost only - HTTP/Unix Socket)
                       │
┌─────────────────────▼─────────────────────────────────────────────┐
│              LLM Compatible Software Instances (llm-cop)           │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐│
│  │  llm-cop-1       │  │  llm-cop-2       │  │  llm-cop-N       ││
│  │  Skills:         │  │  Skills:         │  │  Skills:         ││
│  │  • code_review   │  │  • test_gen      │  │  • doc_gen       ││
│  │  • refactor      │  │  • bug_fix       │  │  • translate     ││
│  │  • security_scan │  │  • optimize      │  │  • summarize     ││
│  │  (localhost:9001)│  │  (localhost:9002)│  │  (localhost:9003)││
│  └──────────────────┘  └──────────────────┘  └──────────────────┘│
└───────────────────────────────────────────────────────────────────┘
```

### 防止模型解密攻擊（Anti-Decryption）

```
┌─────────────────────────────────────────────────────────────┐
│   LLM Compatible Software (llm-cop) - 多層安全防護           │
│   (讓 LLM 透過 skills 操作軟體)                              │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Layer 1: Prompt Sanitization                          │ │
│  │  • 用戶 prompt 不存儲於 manifest                        │ │
│  │  │  • 不記錄歷史 prompt                                 │ │
│  │  • 不在日誌中輸出 prompt 內容                           │ │
│  │  • Prompt 僅存在於記憶體中，用後即銷毀                  │ │
│  └────────────────────────────────────────────────────────┘ │
│              ▼                                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Layer 2: Model State Protection                       │ │
│  │  • 不暴露模型權重、參數                                 │ │
│  │  • 不提供模型內部狀態查詢 API                           │ │
│  │  • 不返回模型 logits、embeddings                        │ │
│  │  • 僅返回最終生成結果                                   │ │
│  └────────────────────────────────────────────────────────┘ │
│              ▼                                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Layer 3: Response Filtering                           │ │
│  │  • 過濾可能洩露 prompt 的回應                           │ │
│  │  • 檢測並阻止 prompt injection 攻擊                     │ │
│  │  • 移除回應中的元資料                                   │ │
│  └────────────────────────────────────────────────────────┘ │
│              ▼                                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Skill Manifest (僅功能介面，無敏感資訊)                │ │
│  │  {                                                      │ │
│  │    "skill_id": "code_review",                          │ │
│  │    "description": "Review code quality",               │ │
│  │    "input_schema": {"type": "object", ...},            │ │
│  │    "output_schema": {"type": "object", ...},           │ │
│  │    "no_prompt_logging": true,                          │ │
│  │    "no_model_exposure": true                           │ │
│  │  }                                                      │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 模型解密攻擊防禦策略

#### 攻擊向量與防禦措施

| 攻擊類型 | 描述 | 防禦措施 |
|---------|------|---------|
| **Prompt Extraction** | 試圖從回應中提取原始 prompt | • 不在回應中回顯 prompt<br>• 過濾包含 prompt 片段的輸出<br>• 使用 prompt template 而非直接暴露 |
| **Model Probing** | 探測模型內部狀態、權重 | • 禁用模型檢查 API<br>• 不返回 logits/probabilities<br>• 限制 API 功能僅到文字生成 |
| **History Replay** | 重放對話歷史以推斷 prompt | • 不持久化用戶 prompt<br>• 會話結束後清除記憶體<br>• 不提供歷史查詢 API |
| **Timing Attack** | 通過響應時間推斷 prompt 長度 | • 固定回應延遲<br>• 添加隨機 jitter<br>• 批次處理請求 |
| **Side Channel** | 通過資源使用推斷輸入 | • 限制資源監控 API<br>• 統一資源分配<br>• 隔離執行環境 |

## 註冊機制

### 1. Filesystem Registry

LLM 提供商在標準化路徑註冊其 manifest 檔案。

#### 註冊路徑

| 平台 | 路徑 |
|------|------|
| Linux | `~/.local/share/llm-providers/` |
| macOS | `~/Library/Application Support/llm-providers/` |
| Windows | `%LOCALAPPDATA%\llm-providers\` |

#### Manifest 檔案格式

檔名：`<provider-id>.json`

範例：`llm-cop-example.json`

```json
{
  "manifest_version": "1.0.0",
  "provider_id": "llm-cop-example",
  "provider_name": "LLM Copilot Example",
  "provider_version": "1.0.0",
  "description": "LLM-compatible Copilot with specialized skills",
  "vendor": "Robot Command Console",
  "homepage": "https://github.com/example/llm-cop",
  
  "endpoints": [
    {
      "type": "http",
      "address": "http://localhost:9001",
      "protocol": "openai-compatible",
      "health_check_path": "/health",
      "api_base": "/v1"
    },
    {
      "type": "unix-socket",
      "address": "/tmp/llm-cop.sock",
      "protocol": "openai-compatible",
      "health_check_path": "/health",
      "api_base": "/v1"
    }
  ],
  
  "llm_compatibility": {
    "api_version": "openai-v1",
    "supported_endpoints": [
      "/v1/chat/completions",
      "/v1/completions",
      "/v1/embeddings"
    ],
    "streaming_support": true,
    "function_calling": true
  },
  
  "capabilities": [
    "text-generation",
    "chat-completion",
    "code-analysis",
    "security-scan"
  ],
  
  "skills": [
    {
      "skill_id": "code_review",
      "name": "Code Review",
      "description": "Review code for quality and security",
      "category": "code_analysis",
      "tags": ["review", "quality", "security"],
      "input_schema": {
        "type": "object",
        "properties": {
          "code": {"type": "string"},
          "language": {"type": "string"}
        }
      },
      "output_schema": {
        "type": "object",
        "properties": {
          "issues": {"type": "array"}
        }
      },
      "llm_accessible": true,
      "function_definition": {
        "name": "code_review",
        "description": "Review code for quality and security issues",
        "parameters": {
          "type": "object",
          "properties": {
            "code": {
              "type": "string",
              "description": "The code to review"
            },
            "language": {
              "type": "string",
              "description": "Programming language (python, javascript, etc.)"
            }
          },
          "required": ["code"]
        }
      }
    }
  ],
  
  "security": {
    "require_auth": false,
    "local_only": true,
    "signature": null
  },
  
  "metadata": {
    "registered_at": "2025-12-10T01:55:00Z",
    "last_seen": "2025-12-10T01:55:00Z",
    "user_approved": true
  }
}
```

### 2. Endpoint Liveness Probe

定期檢查註冊的端點是否存活。

#### 探測機制

1. **HTTP Endpoint**
   - 發送 GET 請求至 `health_check_path`
   - 超時時間：5 秒
   - 成功條件：HTTP 200-299 狀態碼

2. **Unix Socket Endpoint**
   - 嘗試連接 socket
   - 超時時間：3 秒
   - 成功條件：連接成功

#### 健康狀態

```python
class ProviderHealth:
    status: Literal["available", "unavailable", "degraded"]
    last_check: datetime
    response_time_ms: float
    error_message: Optional[str]
    consecutive_failures: int
```

### 3. Discovery Flow

```
1. Scanner 掃描 filesystem registry 路徑
   ↓
2. 讀取所有 manifest.json 檔案
   ↓
3. 驗證 manifest schema
   ↓
4. 對每個 endpoint 執行 liveness probe
   ↓
5. 更新 Provider Manager 狀態
   ↓
6. 提供統一的 API 給上層服務
```

## API 設計

### Discovery Service API

```python
class DiscoveryService:
    """LLM 提供商發現服務"""
    
    async def scan_providers(self) -> List[ProviderManifest]:
        """掃描並返回所有註冊的提供商"""
        
    async def check_health(self, provider_id: str) -> ProviderHealth:
        """檢查特定提供商的健康狀態"""
        
    async def get_available_providers(self) -> List[str]:
        """返回所有可用的提供商 ID"""
        
    async def register_provider(
        self, 
        manifest: ProviderManifest, 
        user_approved: bool = False
    ) -> bool:
        """註冊新的提供商（需用戶同意）"""
        
    async def unregister_provider(self, provider_id: str) -> bool:
        """取消註冊提供商"""
```

## 安全考量

### 當前階段（PoC）- 必須實作

#### 1. 防止模型解密攻擊（核心安全）

```python
# 實作要點
class PromptSanitizer:
    """確保 prompt 不被記錄或洩露"""
    
    @staticmethod
    def sanitize_for_logging(text: str) -> str:
        """移除可能的敏感資訊"""
        return "[PROMPT_REDACTED]"
    
    @staticmethod
    def clear_from_memory(prompt: str):
        """從記憶體中清除 prompt"""
        # 覆寫記憶體
        prompt = None
        gc.collect()

class ResponseFilter:
    """過濾可能洩露 prompt 的回應"""
    
    @staticmethod
    def filter_prompt_echo(response: str, prompt: str) -> str:
        """移除回應中的 prompt 回顯"""
        # 檢測並移除 prompt 片段
        pass
    
    @staticmethod
    def remove_metadata(response: dict) -> dict:
        """移除可能洩露資訊的元資料"""
        safe_keys = ["result", "status"]
        return {k: v for k, v in response.items() if k in safe_keys}
```

#### 2. 本地隔離與存取控制

- ✅ 限制本地主機通訊（127.0.0.1 only）
- ✅ Unix socket 權限設定（chmod 600）
- ✅ 用戶同意機制
- ✅ Manifest schema 驗證
- ✅ 檔案系統權限檢查（0600 for manifests）

#### 3. API 安全限制

```python
# 禁止的 API（不應在 Copilot 中暴露）
FORBIDDEN_APIS = [
    "/model/weights",      # 禁止存取模型權重
    "/model/state",        # 禁止存取模型狀態
    "/model/embeddings",   # 禁止存取 embeddings
    "/prompt/history",     # 禁止查詢 prompt 歷史
    "/debug/logits",       # 禁止存取 logits
    "/debug/attention",    # 禁止存取 attention weights
]

# 允許的 API（僅功能介面）
ALLOWED_APIS = [
    "/skill/execute",      # 執行技能
    "/skill/list",         # 列出技能
    "/health",            # 健康檢查
]
```

### 未來擴充點

#### 1. mTLS 支援（Phase 3.3+）

```json
{
  "security": {
    "tls": {
      "enabled": true,
      "cert_path": "/path/to/cert.pem",
      "key_path": "/path/to/key.pem",
      "ca_path": "/path/to/ca.pem"
    }
  }
}
```

#### 2. Manifest 簽名驗證（Phase 3.3+）

```json
{
  "security": {
    "signature": {
      "algorithm": "RSA-SHA256",
      "public_key": "-----BEGIN PUBLIC KEY-----\n...",
      "signature": "base64-encoded-signature"
    }
  }
}
```

#### 3. Sandbox 隔離（Phase 3.4+）

```json
{
  "security": {
    "sandbox": {
      "enabled": true,
      "allowed_paths": ["/tmp", "~/.local/share"],
      "network_policy": "localhost-only",
      "memory_limit_mb": 512,
      "cpu_limit_percent": 50
    }
  }
}
```

#### 4. 進階反解密措施（Phase 4+）

```json
{
  "security": {
    "anti_decryption": {
      "prompt_encryption": true,        // 加密 prompt 在記憶體中
      "timing_obfuscation": true,       // 混淆回應時間
      "response_sanitization": true,    // 深度清理回應
      "watermarking": true              // 輸出加入浮水印
    }
  }
}
```

## 錯誤處理

### 錯誤碼

| 碼 | 名稱 | 描述 |
|----|------|------|
| `MANIFEST_NOT_FOUND` | Manifest 不存在 | 指定路徑無 manifest 檔案 |
| `MANIFEST_INVALID` | Manifest 無效 | Schema 驗證失敗 |
| `ENDPOINT_UNREACHABLE` | 端點無法連接 | 所有端點都無法連接 |
| `PERMISSION_DENIED` | 權限拒絕 | 用戶未授權註冊 |
| `ALREADY_REGISTERED` | 已註冊 | Provider ID 已存在 |

### 錯誤響應格式

```json
{
  "error": {
    "code": "MANIFEST_INVALID",
    "message": "Manifest schema validation failed",
    "details": {
      "field": "endpoints[0].type",
      "reason": "Invalid endpoint type: 'ws'"
    }
  }
}
```

## 性能指標

### 目標

- 單次掃描時間：< 500ms（10 個提供商）
- 健康檢查時間：< 100ms per endpoint
- 記憶體佔用：< 50MB
- CPU 使用：< 5%（閒置時）

### 最佳化策略

1. **並行掃描**：同時檢查多個提供商
2. **快取機制**：快取 manifest 與健康狀態
3. **增量更新**：僅檢查變更的檔案
4. **連接池**：重用 HTTP 連接

## 測試策略

### 單元測試

- Manifest schema 驗證
- Filesystem scanner 功能
- Endpoint probe 邏輯
- 錯誤處理

### 整合測試

- 完整發現流程
- 多提供商並行
- 錯誤恢復
- 跨平台相容性

### 效能測試

- 大量提供商掃描
- 高頻健康檢查
- 記憶體洩漏檢測

## LLM Compatible Software（llm-cop）定義

### 什麼是 llm-cop？

**llm-cop（LLM Compatible Software）** 是指能夠讓 LLM 透過技能（skills）來操作的相容軟體。它支援雙向互動：

1. **LLM → Software (操作)**：LLM 可以透過 skills (function calling) 來操作軟體功能
2. **Software → LLM (資訊)**：軟體可以透過標準 API 提供資訊給 LLM，供其理解和處理

這使得 LLM 不僅能理解軟體的資訊，還能實際操作軟體執行任務。

### API 介面標準

llm-cop 必須實作標準的 OpenAI API v1 介面，確保與現有 LLM 客戶端相容。

#### 必須實作的端點

```
# LLM 請求資訊
POST /v1/chat/completions      # LLM 對話，可包含 function calling
POST /v1/completions           # LLM 文字生成
GET  /v1/models                # 列出可用的 skills (作為 models)

# Skills 執行（LLM 透過 function calling 呼叫）
POST /v1/skills/execute        # 執行特定 skill
GET  /v1/skills/list           # 列出所有 skills
GET  /v1/skills/{skill_id}     # 獲取 skill 詳細資訊

# 軟體狀態查詢（供 LLM 獲取資訊）
GET  /v1/system/status         # 系統狀態
GET  /v1/data/query            # 查詢軟體資料
POST /v1/context/provide       # 提供上下文資訊給 LLM
```

#### Chat Completions 範例

**請求：**
```bash
curl http://localhost:9001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "code_review",
    "messages": [
      {
        "role": "system",
        "content": "You are a code review assistant"
      },
      {
        "role": "user",
        "content": "Review this code: def foo(): pass"
      }
    ],
    "functions": [
      {
        "name": "code_review",
        "description": "Perform code review",
        "parameters": {
          "type": "object",
          "properties": {
            "code": {"type": "string"},
            "language": {"type": "string"}
          }
        }
      }
    ]
  }'
```

**回應：**
```json
{
  "id": "chatcmpl-123",
  "object": "chat.completion",
  "created": 1677652288,
  "model": "code_review",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": null,
        "function_call": {
          "name": "code_review",
          "arguments": "{\"code\": \"def foo(): pass\", \"language\": \"python\"}"
        }
      },
      "finish_reason": "function_call"
    }
  ],
  "usage": {
    "prompt_tokens": 20,
    "completion_tokens": 15,
    "total_tokens": 35
  }
}
```

### LLM 操作軟體：Skills 作為 Functions

llm-cop 的每個 skill 都可以作為 OpenAI Function Calling 中的 function 使用，讓 LLM 能夠操作軟體功能。

#### 完整互動流程

```
┌─────────┐                  ┌──────────────┐                  ┌──────────┐
│   LLM   │                  │  llm-cop     │                  │ Software │
│         │                  │  (Skills)    │                  │  Backend │
└────┬────┘                  └──────┬───────┘                  └────┬─────┘
     │                              │                               │
     │ 1. Request info              │                               │
     │ "What's the system status?"  │                               │
     │─────────────────────────────>│                               │
     │                              │                               │
     │                              │ 2. Query backend              │
     │                              │──────────────────────────────>│
     │                              │                               │
     │                              │ 3. Return status              │
     │                              │<──────────────────────────────│
     │                              │                               │
     │ 4. Provide info to LLM       │                               │
     │<─────────────────────────────│                               │
     │                              │                               │
     │ 5. LLM decides to call skill │                               │
     │ function_call: "restart_service" │                          │
     │─────────────────────────────>│                               │
     │                              │                               │
     │                              │ 6. Execute skill              │
     │                              │──────────────────────────────>│
     │                              │                               │
     │                              │ 7. Execution result           │
     │                              │<──────────────────────────────│
     │                              │                               │
     │ 8. Return result to LLM      │                               │
     │<─────────────────────────────│                               │
     └──────────────────────────────┴───────────────────────────────┘
```

#### Skill 定義範例

```python
# Skill 定義（雙向互動）
skill = {
    "skill_id": "system_control",
    "name": "System Control",
    
    # LLM 可以呼叫的操作
    "function_definition": {
        "name": "system_control",
        "description": "Control system services (start, stop, restart)",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["start", "stop", "restart", "status"]
                },
                "service_name": {"type": "string"}
            },
            "required": ["action", "service_name"]
        }
    },
    
    # LLM 可以查詢的資訊
    "info_schema": {
        "provides": [
            "service_status",
            "service_list",
            "system_metrics"
        ],
        "query_methods": {
            "get_status": {
                "description": "Get service status",
                "parameters": {
                    "service_name": {"type": "string"}
                }
            },
            "list_services": {
                "description": "List all services"
            }
        }
    }
}

# LLM 使用範例
# 步驟 1: LLM 查詢資訊
response = openai.ChatCompletion.create(
    model="llm-cop-system",
    messages=[
        {"role": "user", "content": "What services are running?"}
    ],
    functions=[skill["function_definition"]]
)

# LLM 決定呼叫 function
if response.choices[0].message.get("function_call"):
    function_call = response.choices[0].message["function_call"]
    # 步驟 2: 執行 skill 操作
    result = execute_skill(function_call)
    
    # 步驟 3: 將結果返回給 LLM
    follow_up = openai.ChatCompletion.create(
        model="llm-cop-system",
        messages=[
            {"role": "user", "content": "What services are running?"},
            {"role": "assistant", "content": None, "function_call": function_call},
            {"role": "function", "name": function_call["name"], "content": result}
        ]
    )
```

### 與現有 LLM 客戶端整合

llm-cop 可以被任何支援 OpenAI API 的客戶端使用：

```python
# 使用 OpenAI Python SDK
import openai

# 配置為使用本地 llm-cop
openai.api_base = "http://localhost:9001/v1"
openai.api_key = "not-needed"  # llm-cop 不需要 API key（本地）

# 呼叫 chat completions
response = openai.ChatCompletion.create(
    model="code_review",
    messages=[
        {"role": "user", "content": "Review this Python code: ..."}
    ]
)

# 使用 LangChain
from langchain.llms import OpenAI
from langchain.chat_models import ChatOpenAI

llm = ChatOpenAI(
    openai_api_base="http://localhost:9001/v1",
    openai_api_key="not-needed",
    model_name="code_review"
)

# 使用 LlamaIndex
from llama_index.llms import OpenAI

llm = OpenAI(
    api_base="http://localhost:9001/v1",
    api_key="not-needed",
    model="code_review"
)
```

## 使用範例

### Provider 註冊

```python
# examples/provider.py
from llm_discovery import ProviderManifest, Endpoint, Skill

# 定義與 OpenAI API 相容的 skill
skill = Skill(
    skill_id="code_review",
    name="Code Review",
    description="Review code quality",
    input_schema={...},
    output_schema={...},
    llm_accessible=True,  # 可透過 LLM API 存取
    function_definition={  # OpenAI function calling 格式
        "name": "code_review",
        "description": "Review code for quality and security",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {"type": "string"},
                "language": {"type": "string"}
            }
        }
    }
)

manifest = ProviderManifest(
    provider_id="my-llm-cop",
    provider_name="My LLM Copilot",
    provider_version="1.0.0",
    endpoints=[
        Endpoint(
            type="http",
            address="http://localhost:9001",
            protocol="openai-compatible",
            health_check_path="/health",
            api_base="/v1"  # OpenAI API base path
        )
    ],
    skills=[skill],
    llm_compatibility={
        "api_version": "openai-v1",
        "streaming_support": True,
        "function_calling": True
    }
)

# 註冊到 filesystem registry
from llm_discovery.scanner import FilesystemScanner
scanner = FilesystemScanner()
scanner.save_manifest(manifest)
```

### Discovery Core

```python
# examples/llm_core.py
from llm_discovery import DiscoveryService

# 初始化發現服務
discovery = DiscoveryService()

# 掃描所有提供商
providers = await discovery.scan_providers()

# 檢查健康狀態
for provider in providers:
    health = await discovery.check_health(provider.provider_id)
    print(f"{provider.provider_name}: {health.status}")

# 獲取可用提供商
available = await discovery.get_available_providers()
print(f"Available providers: {available}")
```

## 相關文件

- [MCP LLM Providers](../mcp/MCP_LLM_PROVIDERS.md)
- [Architecture](../architecture.md)
- [Phase 3 Plans](../plans/MASTER_PLAN.md)

## 未來工作

### Phase 3.3+

1. 雲端註冊中心整合
2. Provider 版本管理
3. 自動更新機制
4. 進階監控與遙測
5. Provider marketplace

---

**貢獻者**: GitHub Copilot  
**審閱者**: TBD
