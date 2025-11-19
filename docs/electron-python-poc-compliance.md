# Electron-Python POC 合規性指南

## 概述

本文件說明 Phase 1 POC (Electron + Python API) 如何符合專案規範，並提供整合指南。

## 架構概覽

```
┌─────────────────────────────────────────────────┐
│           Electron Desktop App                   │
│  ┌──────────────────────────────────────────┐   │
│  │  Renderer Process (WebUI)                 │   │
│  │  - User Interface                         │   │
│  │  - API Client                             │   │
│  │  - Token Management                       │   │
│  └──────────────┬───────────────────────────┘   │
│                 │                                │
│  ┌──────────────▼───────────────────────────┐   │
│  │  Main Process                             │   │
│  │  - Python Service Spawner                 │   │
│  │  - Health Check                           │   │
│  │  - Lifecycle Management                   │   │
│  └──────────────┬───────────────────────────┘   │
└─────────────────┼───────────────────────────────┘
                  │ HTTP/localhost
                  │ (with JWT Token)
┌─────────────────▼───────────────────────────────┐
│           Python MCP Service                     │
│  ┌──────────────────────────────────────────┐   │
│  │  FastAPI Application                      │   │
│  │  - Schema Validator ✅ NEW                │   │
│  │  - Auth Manager (JWT) ✅ ENHANCED         │   │
│  │  - Command Handler ✅ ENHANCED            │   │
│  │  - Logging Monitor ✅ ENHANCED            │   │
│  └──────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

## Electron 整合要求

### 1. 啟動 Python 服務

Electron 主進程需要在啟動時啟動 Python 服務：

```javascript
// main.js
const { spawn } = require('child_process');
const path = require('path');

let pythonProcess = null;
let pythonServiceUrl = 'http://127.0.0.1:8000';

function startPythonService() {
  const pythonPath = path.join(__dirname, 'MCP', 'start.py');
  
  pythonProcess = spawn('python', [pythonPath], {
    stdio: 'pipe',
    cwd: path.join(__dirname, 'MCP')
  });
  
  pythonProcess.stdout.on('data', (data) => {
    console.log(`Python: ${data}`);
  });
  
  pythonProcess.stderr.on('data', (data) => {
    console.error(`Python Error: ${data}`);
  });
  
  pythonProcess.on('exit', (code) => {
    console.log(`Python service exited with code ${code}`);
  });
  
  // 等待服務就緒
  return waitForServiceReady();
}

async function waitForServiceReady(maxRetries = 10) {
  for (let i = 0; i < maxRetries; i++) {
    try {
      const response = await fetch(`${pythonServiceUrl}/health`);
      if (response.ok) {
        console.log('Python service is ready');
        return true;
      }
    } catch (err) {
      console.log(`Waiting for Python service... (${i + 1}/${maxRetries})`);
      await new Promise(resolve => setTimeout(resolve, 1000));
    }
  }
  throw new Error('Python service failed to start');
}

// App lifecycle
app.on('ready', async () => {
  await startPythonService();
  createWindow();
});

app.on('before-quit', () => {
  if (pythonProcess) {
    pythonProcess.kill();
  }
});
```

### 2. Renderer Process API 客戶端

Renderer 進程需要實作符合契約的 API 客戶端：

```javascript
// renderer/api-client.js
class MCPApiClient {
  constructor(baseUrl = 'http://127.0.0.1:8000') {
    this.baseUrl = baseUrl;
    this.token = null;
  }
  
  // 登入並取得 token
  async login(username, password) {
    const response = await fetch(`${this.baseUrl}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });
    
    if (!response.ok) {
      throw new Error('Login failed');
    }
    
    const data = await response.json();
    this.token = data.token;
    return data;
  }
  
  // 下達指令（符合契約）
  async sendCommand(commandSpec) {
    const traceId = this.generateTraceId();
    
    const request = {
      trace_id: traceId,
      timestamp: new Date().toISOString(),
      actor: {
        type: 'human',
        id: this.getUserId(),  // 從 session 取得
        name: this.getUsername()
      },
      source: 'webui',
      command: {
        id: `cmd-${Date.now()}`,
        type: commandSpec.type,
        target: commandSpec.target,
        params: commandSpec.params || {},
        timeout_ms: commandSpec.timeout_ms || 10000,
        priority: commandSpec.priority || 'normal'
      },
      auth: {
        token: this.token
      },
      labels: commandSpec.labels || {}
    };
    
    const response = await fetch(`${this.baseUrl}/api/command`, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.token}`
      },
      body: JSON.stringify(request)
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error?.message || 'Command failed');
    }
    
    const result = await response.json();
    
    // 驗證回應包含 trace_id
    if (result.trace_id !== traceId) {
      console.warn('trace_id mismatch!');
    }
    
    return result;
  }
  
  // 查詢事件（追蹤 trace_id）
  async getEvents(traceId) {
    const response = await fetch(
      `${this.baseUrl}/api/events?trace_id=${traceId}`,
      {
        headers: { 'Authorization': `Bearer ${this.token}` }
      }
    );
    
    if (!response.ok) {
      throw new Error('Failed to fetch events');
    }
    
    return await response.json();
  }
  
  // WebSocket 事件訂閱
  subscribeEvents(onEvent) {
    const ws = new WebSocket(`ws://127.0.0.1:8000/api/events/subscribe`);
    
    ws.onmessage = (event) => {
      const eventData = JSON.parse(event.data);
      onEvent(eventData);
    };
    
    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
    
    return ws;
  }
  
  // 工具函數
  generateTraceId() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
      const r = Math.random() * 16 | 0;
      const v = c === 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
  }
  
  getUserId() {
    return localStorage.getItem('user_id') || 'unknown';
  }
  
  getUsername() {
    return localStorage.getItem('username') || 'Unknown User';
  }
}

// 使用範例
const client = new MCPApiClient();

// 登入
await client.login('operator1', 'password123');

// 下達指令
const result = await client.sendCommand({
  type: 'robot.move',
  target: { robot_id: 'robot_1' },
  params: { action: 'go_forward', duration_ms: 3000 },
  timeout_ms: 10000,
  priority: 'normal'
});

console.log('Command result:', result);
console.log('Trace ID:', result.trace_id);

// 查詢事件
const events = await client.getEvents(result.trace_id);
console.log('Events:', events);

// 訂閱即時事件
const ws = client.subscribeEvents((event) => {
  console.log('New event:', event);
  if (event.trace_id === result.trace_id) {
    console.log('Event for our command!');
  }
});
```

## 契約合規性檢查清單

在整合時，確保以下項目：

### Electron 端

- [ ] 主進程正確啟動和管理 Python 服務
- [ ] 實作健康檢查，確保服務就緒
- [ ] 正確處理服務崩潰和重啟
- [ ] 在應用退出時正確關閉 Python 服務

### API 客戶端

- [ ] 所有請求包含必要欄位：trace_id, timestamp, actor, source
- [ ] 正確處理 JWT Token（儲存、傳遞、更新）
- [ ] 驗證回應的 trace_id 與請求一致
- [ ] 處理所有錯誤代碼（ERR_VALIDATION, ERR_UNAUTHORIZED 等）
- [ ] 實作 EventLog 訂閱以獲取即時更新

### 用戶體驗

- [ ] 顯示 trace_id 以便追蹤
- [ ] 顯示指令狀態（accepted, running, succeeded, failed）
- [ ] 顯示錯誤訊息（從 error.message）
- [ ] 提供事件歷史查詢
- [ ] 實作 token 過期處理（重新登入）

## 錯誤處理

### 處理驗證錯誤

```javascript
try {
  const result = await client.sendCommand(commandSpec);
} catch (error) {
  if (error.message.includes('Schema')) {
    // ERR_VALIDATION - 請求不符合 schema
    console.error('Invalid request format:', error);
    showError('請求格式不正確，請檢查輸入');
  }
}
```

### 處理認證錯誤

```javascript
try {
  const result = await client.sendCommand(commandSpec);
} catch (error) {
  if (error.message.includes('unauthorized')) {
    // ERR_UNAUTHORIZED - token 無效或過期
    console.error('Authentication failed:', error);
    // 重新登入
    await client.login(username, password);
    // 重試
    return await client.sendCommand(commandSpec);
  }
}
```

### 處理超時錯誤

```javascript
try {
  const result = await client.sendCommand({
    ...commandSpec,
    timeout_ms: 5000  // 5 秒超時
  });
} catch (error) {
  if (error.message.includes('timeout')) {
    // ERR_TIMEOUT - 指令執行超時
    console.error('Command timeout:', error);
    showError('指令執行超時，請重試');
  }
}
```

## 安全考量

### Token 管理

1. **儲存**: 使用 Electron 的 safe-storage API
   ```javascript
   const { safeStorage } = require('electron');
   
   // 儲存 token
   const encryptedToken = safeStorage.encryptString(token);
   localStorage.setItem('token', encryptedToken.toString('base64'));
   
   // 讀取 token
   const buffer = Buffer.from(localStorage.getItem('token'), 'base64');
   const token = safeStorage.decryptString(buffer);
   ```

2. **自動刷新**: 在 token 即將過期時自動刷新
   ```javascript
   setInterval(async () => {
     if (isTokenExpiringSoon()) {
       await refreshToken();
     }
   }, 60000);  // 每分鐘檢查
   ```

3. **安全通訊**: 僅監聽 localhost
   ```python
   # MCP/config.py
   API_HOST = "127.0.0.1"  # 不使用 0.0.0.0
   ```

## 測試

### 單元測試

測試 API 客戶端：

```javascript
// test/api-client.test.js
const assert = require('assert');
const MCPApiClient = require('../renderer/api-client');

describe('MCPApiClient', () => {
  it('should generate valid trace_id', () => {
    const client = new MCPApiClient();
    const traceId = client.generateTraceId();
    
    // UUID v4 格式
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
    assert(uuidRegex.test(traceId));
  });
  
  it('should include all required fields in command request', async () => {
    const client = new MCPApiClient();
    client.token = 'test-token';
    
    const commandSpec = {
      type: 'robot.move',
      target: { robot_id: 'robot_1' },
      params: { action: 'go_forward' }
    };
    
    // Mock fetch
    global.fetch = async (url, options) => {
      const body = JSON.parse(options.body);
      
      // 驗證必要欄位
      assert(body.trace_id);
      assert(body.timestamp);
      assert(body.actor);
      assert(body.source === 'webui');
      assert(body.command);
      assert(body.auth);
      
      return {
        ok: true,
        json: async () => ({ 
          trace_id: body.trace_id,
          command: { id: body.command.id, status: 'accepted' }
        })
      };
    };
    
    await client.sendCommand(commandSpec);
  });
});
```

### 整合測試

測試 Electron + Python 整合：

```javascript
// test/integration.test.js
const { Application } = require('spectron');

describe('Electron-Python Integration', () => {
  let app;
  
  beforeEach(async () => {
    app = new Application({
      path: './node_modules/.bin/electron',
      args: ['./main.js']
    });
    await app.start();
    
    // 等待 Python 服務就緒
    await app.client.waitUntil(async () => {
      const ready = await app.client.execute(() => {
        return window.pythonServiceReady;
      });
      return ready.value;
    }, 10000);
  });
  
  afterEach(async () => {
    if (app && app.isRunning()) {
      await app.stop();
    }
  });
  
  it('should start Python service and connect', async () => {
    // 檢查健康端點
    const response = await fetch('http://127.0.0.1:8000/health');
    assert(response.ok);
    
    const data = await response.json();
    assert.equal(data.status, 'healthy');
  });
  
  it('should send command with valid contract', async () => {
    // 登入
    await app.client.click('#login-btn');
    await app.client.setValue('#username', 'testuser');
    await app.client.setValue('#password', 'testpass');
    await app.client.click('#submit-login');
    
    // 等待登入完成
    await app.client.waitForVisible('#command-panel');
    
    // 下達指令
    await app.client.click('#send-command-btn');
    
    // 驗證回應
    const result = await app.client.getText('#command-result');
    assert(result.includes('trace_id'));
    assert(result.includes('accepted'));
  });
});
```

## 部署檢查清單

發布 Electron 應用前：

- [ ] Python 服務可執行檔已包含在應用包中
- [ ] 依賴已正確打包（requirements.txt）
- [ ] 配置檔案已包含（但不含敏感資訊）
- [ ] JWT Secret 透過環境變數或配置檔案設定
- [ ] 健康檢查與錯誤恢復機制已測試
- [ ] 所有 API 呼叫已符合契約
- [ ] 已測試 token 過期和刷新流程
- [ ] 已測試網路錯誤處理
- [ ] 日誌檔案位置已配置（避免權限問題）

## 疑難排解

### Python 服務無法啟動

**症狀**: Electron 啟動但無法連接到 Python 服務

**解決方案**:
1. 檢查 Python 路徑是否正確
2. 檢查端口 8000 是否被占用
3. 查看 Python 進程的 stderr 輸出
4. 確認依賴已安裝（requirements.txt）

### Token 驗證失敗

**症狀**: 所有 API 請求返回 ERR_UNAUTHORIZED

**解決方案**:
1. 檢查 token 是否正確儲存和傳遞
2. 檢查 token 是否過期
3. 驗證 JWT_SECRET 在 Electron 和 Python 間一致
4. 重新登入取得新 token

### trace_id 不一致

**症狀**: 回應的 trace_id 與請求不同

**解決方案**:
1. 檢查請求格式是否正確
2. 確認 trace_id 生成演算法符合 UUID v4 格式
3. 檢查是否有中間件修改了 trace_id

## 參考資源

- **專案規範**: `.github/prompts/Project.prompt.md`
- **提案文件**: `proposal.md`
- **合規性文件**: `docs/phase1-compliance.md`
- **Electron 整合**: `plans/webui-to-app/electron-python-integration.md`
- **MCP 模組**: `MCP/Module.md`

---

**版本**: v1.0  
**日期**: 2025-11-19  
**狀態**: ✅ Phase 1 合規性已完成
