# Phase 1 POC 合規性文件

## 概述

本文件記錄 Phase 1 POC (Electron + Python API) 的合規性實作，確保系統符合 `.github/prompts/Project.prompt.md` 和 `proposal.md` 中定義的標準。

## 合規性要求與實作狀態

### 1. 強制執行標準 JSON 契約 ✅

#### 要求
- 所有 API 請求/回應必須包含標準欄位：`trace_id`, `timestamp`, `actor`, `source`
- CommandRequest/CommandResponse/EventLog 必須符合定義的 schema
- 實作 schema 驗證以確保契約合規性

#### 實作
- **檔案**: `MCP/schema_validator.py`
- **功能**:
  - JSON Schema 驗證器，使用 Draft 7 標準
  - CommandRequest schema 驗證
  - CommandResponse schema 驗證
  - EventLog schema 驗證
  - Pydantic 模型驗證整合
  
#### Schema 定義

**CommandRequest 必要欄位**:
```json
{
  "trace_id": "uuid-v4",
  "timestamp": "2025-11-19T10:30:00Z",
  "actor": {
    "type": "human|ai|system",
    "id": "user-123"
  },
  "source": "webui|api|cli|scheduler",
  "command": {
    "id": "cmd-xxx",
    "type": "robot.action",
    "target": {
      "robot_id": "robot_1"
    },
    "timeout_ms": 10000,
    "priority": "low|normal|high"
  },
  "auth": {
    "token": "<jwt-token>"
  }
}
```

**CommandResponse 必要欄位**:
```json
{
  "trace_id": "uuid-v4",
  "timestamp": "2025-11-19T10:30:05Z",
  "command": {
    "id": "cmd-xxx",
    "status": "accepted|running|succeeded|failed|cancelled"
  },
  "result": {
    "data": {},
    "summary": "執行結果"
  },
  "error": {
    "code": "ERR_*",
    "message": "錯誤訊息",
    "details": {}
  }
}
```

**EventLog 必要欄位**:
```json
{
  "trace_id": "uuid-v4",
  "timestamp": "2025-11-19T10:30:03Z",
  "severity": "DEBUG|INFO|WARN|ERROR",
  "category": "command|auth|protocol|robot|audit",
  "message": "事件訊息",
  "context": {
    "command_id": "cmd-xxx"
  }
}
```

#### 驗證流程
1. 請求到達 API 端點
2. Pydantic 進行基本類型驗證
3. SchemaValidator 進行完整 JSON Schema 驗證
4. 驗證失敗時返回 `ERR_VALIDATION` 錯誤
5. 記錄驗證失敗事件到 EventLog

### 2. EventLog 發送與 trace_id 傳播 ✅

#### 要求
- 所有指令/API 呼叫必須發送 EventLog
- trace_id 必須在整個請求鏈中傳播並返回
- 關鍵事件必須記錄（auth 失敗、驗證失敗、超時等）

#### 實作
- **檔案**: `MCP/command_handler.py`, `MCP/logging_monitor.py`
- **功能**:
  - 指令接受時發送 EventLog
  - 驗證失敗時發送 EventLog
  - Auth 失敗時發送 EventLog
  - 指令執行時發送 EventLog (running, succeeded, failed)
  - 所有 EventLog 包含相同的 trace_id

#### EventLog 發送點
1. **Schema 驗證失敗** → `EventSeverity.WARN`, `EventCategory.COMMAND`
2. **身份驗證失敗** → `EventSeverity.WARN`, `EventCategory.AUTH`
3. **授權失敗** → `EventSeverity.WARN`, `EventCategory.AUTH`
4. **指令接受** → `EventSeverity.INFO`, `EventCategory.COMMAND`
5. **指令執行中** → `EventSeverity.INFO`, `EventCategory.COMMAND`
6. **指令成功** → `EventSeverity.INFO`, `EventCategory.COMMAND`
7. **指令失敗** → `EventSeverity.ERROR`, `EventCategory.COMMAND`
8. **指令超時** → `EventSeverity.ERROR`, `EventCategory.COMMAND`

#### trace_id 傳播路徑
```
CommandRequest.trace_id
  ↓ (驗證)
  → EventLog.trace_id (驗證事件)
  ↓ (認證/授權)
  → EventLog.trace_id (auth 事件)
  ↓ (執行)
  → EventLog.trace_id (執行事件)
  ↓ (完成)
  → CommandResponse.trace_id
```

### 3. 最小化 AuthN/AuthZ 實作 ✅

#### 要求
- 實作基本 JWT/Token 檢查
- Auth 失敗時返回標準錯誤
- 記錄所有 auth 事件到審計日誌

#### 實作
- **檔案**: `MCP/auth_manager.py`
- **功能**:
  - JWT Token 生成與驗證
  - 密碼雜湊（bcrypt）
  - RBAC 權限檢查（admin, operator, viewer）
  - 審計日誌記錄

#### 角色與權限

**Admin**:
- 權限: `*` (所有)
- 描述: 完整系統控制

**Operator**:
- 權限: `robot.move`, `robot.stop`, `robot.status`, `command.view`, `command.create`
- 描述: 可操作機器人和下達指令

**Viewer**:
- 權限: `robot.status`, `command.view`
- 描述: 僅可查看狀態

#### Auth 流程
1. 用戶註冊 → 密碼雜湊 → 儲存用戶資訊
2. 用戶登入 → 驗證密碼 → 生成 JWT Token
3. API 請求 → 驗證 Token → 檢查權限 → 處理請求
4. 所有 auth 操作 → 記錄審計事件

#### 標準錯誤響應
```json
{
  "trace_id": "uuid-v4",
  "timestamp": "2025-11-19T10:30:00Z",
  "command": {
    "id": "cmd-xxx",
    "status": "failed"
  },
  "result": null,
  "error": {
    "code": "ERR_UNAUTHORIZED",
    "message": "身份驗證失敗" | "權限不足",
    "details": {
      "reason": "invalid_token" | "insufficient_permission"
    }
  }
}
```

### 4. TDD 測試覆蓋 ✅

#### 測試檔案

**1. test_contract_compliance.py** (15 個測試)
- 有效 CommandRequest 驗證
- 缺少必要欄位測試
- 無效 actor type 測試
- 無效 timeout 範圍測試
- 有效 CommandResponse 測試（成功/錯誤）
- 無效錯誤代碼測試
- 有效 EventLog 測試
- 缺少訊息的 EventLog 測試
- Pydantic 模型驗證測試
- trace_id 傳播測試
- 錯誤契約合規性測試

**2. test_auth_compliance.py** (14 個測試)
- 用戶註冊測試
- 重複註冊測試
- 用戶認證測試（成功/失敗）
- Token 生成測試
- 有效 Token 驗證測試
- 過期 Token 測試
- 無效 Token 測試
- Admin 權限檢查測試
- Operator 權限檢查測試
- Viewer 權限檢查測試
- 不存在用戶權限檢查測試
- Auth 失敗審計日誌測試
- 完整 auth 流程測試
- Auth 失敗流程測試

**3. test_command_handler_compliance.py** (8 個測試)
- 成功指令處理（有效契約）
- 驗證失敗處理
- Auth 失敗（缺少 token）
- Auth 失敗（無效 token）
- 授權失敗（權限不足）
- trace_id 在整個流程中傳播
- 多個 EventLog 發送
- 錯誤回應包含所有必要欄位

#### 測試執行結果
```
契約合規性測試: 15/15 通過 ✅
認證授權測試: 14/14 通過 ✅
指令處理整合測試: 8/8 通過 ✅
總計: 37/37 通過 ✅
```

#### 測試覆蓋範圍
- ✅ 成功路徑（有效請求/回應）
- ✅ 驗證失敗（無效 schema）
- ✅ Auth 失敗（無效/缺失 token）
- ✅ 授權失敗（權限不足）
- ✅ 超時處理（錯誤響應）
- ✅ 錯誤回應（所有錯誤代碼）
- ✅ 契約驅動測試（schema 合規性）

### 5. 文件更新 ✅

#### 已更新檔案
1. **MCP/Module.md**
   - 新增 Phase 1 合規性檢查清單
   - 新增測試覆蓋統計
   - 新增技術實作詳情
   - 參考 proposal.md/Project.prompt.md

2. **docs/phase1-compliance.md** (本檔案)
   - 完整合規性文件
   - 實作詳情
   - 測試覆蓋
   - 使用範例

3. **MCP/requirements.txt**
   - 新增 jsonschema>=4.20.0

## 整合與使用

### 啟動 MCP 服務
```bash
cd MCP
pip install -r requirements.txt
python start.py
```

### 執行測試
```bash
# 執行所有合規性測試
python -m unittest discover Test -v

# 執行特定測試
python -m unittest Test.test_contract_compliance -v
python -m unittest Test.test_auth_compliance -v
python -m unittest Test.test_command_handler_compliance -v
```

### API 使用範例

#### 1. 註冊用戶
```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user-001",
    "username": "operator1",
    "password": "securepass123",
    "role": "operator"
  }'
```

#### 2. 登入取得 Token
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "operator1",
    "password": "securepass123"
  }'
```

回應:
```json
{
  "token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user_id": "user-001",
  "role": "operator"
}
```

#### 3. 下達指令
```bash
curl -X POST http://localhost:8000/api/command \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..." \
  -d '{
    "trace_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2025-11-19T10:30:00Z",
    "actor": {
      "type": "human",
      "id": "user-001"
    },
    "source": "api",
    "command": {
      "id": "cmd-001",
      "type": "robot.move",
      "target": {
        "robot_id": "robot_1"
      },
      "params": {
        "action": "go_forward",
        "duration_ms": 3000
      },
      "timeout_ms": 10000,
      "priority": "normal"
    },
    "auth": {
      "token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
    }
  }'
```

回應:
```json
{
  "trace_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2025-11-19T10:30:01Z",
  "command": {
    "id": "cmd-001",
    "status": "accepted"
  },
  "result": null,
  "error": null
}
```

#### 4. 查詢事件
```bash
curl -X GET "http://localhost:8000/api/events?trace_id=550e8400-e29b-41d4-a716-446655440000"
```

## 安全考量

### JWT 配置
- **Secret Key**: 透過環境變數 `MCP_JWT_SECRET` 設定（不得硬編碼）
- **演算法**: HS256
- **過期時間**: 24 小時（可透過環境變數調整）

### 密碼安全
- 使用 bcrypt 雜湊演算法
- 自動產生隨機鹽值
- 不儲存明文密碼

### 審計追蹤
- 所有 auth 操作記錄審計事件
- 包含 trace_id 以進行全鏈路追蹤
- 記錄失敗原因以供分析

## 錯誤代碼參考

| 代碼 | 說明 | HTTP Status |
|------|------|-------------|
| ERR_VALIDATION | Schema 驗證失敗 | 400 |
| ERR_UNAUTHORIZED | 身份驗證或授權失敗 | 401 |
| ERR_ROUTING | 路由錯誤 | 404 |
| ERR_ROBOT_NOT_FOUND | 機器人不存在 | 404 |
| ERR_ROBOT_OFFLINE | 機器人離線 | 503 |
| ERR_ROBOT_BUSY | 機器人忙碌中 | 409 |
| ERR_ACTION_INVALID | 無效動作 | 400 |
| ERR_PROTOCOL | 協定錯誤 | 500 |
| ERR_TIMEOUT | 執行超時 | 504 |
| ERR_INTERNAL | 內部錯誤 | 500 |

## 參考文件

- **專案規範**: `.github/prompts/Project.prompt.md`
- **提案文件**: `proposal.md`
- **MCP 模組文件**: `MCP/Module.md`
- **Electron 整合**: `plans/webui-to-app/electron-python-integration.md`

## 下一步

Phase 1 合規性已完成，後續工作：

1. **整合測試**: 與 Electron 前端整合測試
2. **壓力測試**: 測試高並發場景
3. **效能優化**: 優化 schema 驗證效能
4. **文件完善**: 新增 API 文件與使用範例
5. **監控**: 整合監控系統（Prometheus/Grafana）

## 版本資訊

- **版本**: Phase 1 Compliance v1.0
- **日期**: 2025-11-19
- **狀態**: ✅ 已完成並通過所有測試
