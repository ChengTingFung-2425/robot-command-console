# Electron/背景服務間權杖與安全通信

> **文件版本**: 1.0  
> **建立日期**: 2025-12-03  
> **狀態**: 已實作

## 概述

本文件說明 Electron 應用程式與 Python 背景服務（Flask）之間的權杖（Token）管理與安全通信機制。

## 架構

```
┌─────────────────────────────────────────────────────────────────┐
│                    Electron Main Process                         │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                   TokenManager (JS)                        │  │
│  │  • 生成加密安全 Token                                       │  │
│  │  • Token 輪替管理                                           │  │
│  │  • 過期監控                                                 │  │
│  └───────────────────────────────────────────────────────────┘  │
│                            │                                      │
│                    環境變數 (APP_TOKEN)                          │
│                            │                                      │
│                            ▼                                      │
└─────────────────────────────────────────────────────────────────┘
                             │
                    spawn + env vars
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Flask Service (Python)                        │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                  TokenValidator (Python)                   │  │
│  │  • 時間安全的 Token 比較                                    │  │
│  │  • 支援多 Token 驗證（輪替寬限期）                          │  │
│  │  • 請求認證                                                 │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                             │
                    IPC (preload.js)
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Electron Renderer Process                      │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    electronAPI                             │  │
│  │  • getToken() / getTokenInfo()                             │  │
│  │  • rotateToken()                                            │  │
│  │  • onTokenRotated() 事件監聽                                │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## 核心元件

### 1. TokenManager (JavaScript - Electron)

位於: `electron-app/token-manager.js`

提供 Token 生命週期管理：

```javascript
const { getTokenManager } = require('./token-manager');

const manager = getTokenManager();

// 生成新 Token
const { token, info } = manager.generateToken();

// Token 輪替（不中斷服務）
const { token: newToken, info: newInfo } = manager.rotateToken('scheduled');

// 驗證 Token
const isValid = manager.verifyToken(someToken);

// 取得 Token 狀態
const status = manager.getStatus();
```

**特性**:
- 加密安全的 Token 生成 (`crypto.randomBytes`)
- Token 輪替與寬限期支援
- 時間安全的 Token 比較 (`crypto.timingSafeEqual`)
- 輪替事件訂閱

### 2. TokenManager (Python - 共用模組)

位於: `src/common/token_manager.py`

Python 端的 Token 管理器，提供相同的功能：

```python
from src.common.token_manager import get_edge_token_manager

manager = get_edge_token_manager()

# 生成新 Token
token, info = manager.generate_token()

# Token 輪替
new_token, new_info = manager.rotate_token(reason='scheduled')

# 驗證 Token
is_valid = manager.verify_token(some_token)

# 訂閱輪替事件
def on_rotation(new_token, info):
    print(f"Token rotated: {info.token_id}")

manager.on_token_rotated(on_rotation)
```

### 3. TokenValidator (Python - Flask)

位於: `src/robot_service/electron/flask_adapter.py`

用於 Flask 請求認證：

```python
from src.robot_service.electron import TokenValidator

# 建立驗證器
validator = TokenValidator(primary_token="xxx")

# 添加額外有效 Token（用於輪替期間）
validator.add_token("old_token")

# 驗證請求中的 Token
if validator.validate(request_token):
    # 認證成功
    pass
```

## IPC API

### Renderer 可用的 API

透過 `window.electronAPI` 存取：

| 方法 | 說明 |
|------|------|
| `getToken()` | 取得當前 Token |
| `getTokenInfo()` | 取得 Token 詳細資訊 |
| `rotateToken(reason)` | 輪替 Token |
| `getTokenStatus()` | 取得 Token 管理器狀態 |
| `getTokenRotationHistory()` | 取得輪替歷史 |
| `isTokenRotationNeeded(hours)` | 檢查是否需要輪替 |
| `invalidateToken()` | 使 Token 失效 |
| `onTokenRotated(callback)` | 監聽輪替事件 |

### 使用範例

```javascript
// 取得 Token 資訊
const tokenInfo = await window.electronAPI.getTokenInfo();
console.log(`Token ID: ${tokenInfo.tokenId}`);
console.log(`Expires: ${tokenInfo.expiresAt}`);

// 手動輪替 Token
const result = await window.electronAPI.rotateToken('security_update');
if (result.success) {
    console.log('Token rotated successfully');
}

// 監聽輪替事件
window.electronAPI.onTokenRotated((data) => {
    console.log(`Token rotated: ${data.tokenId}`);
});
```

## 安全機制

### 1. Token 生成

- 使用 `crypto.randomBytes(32)` 生成 256 位元加密安全 Token
- Token 長度: 64 個十六進位字元

### 2. Token 驗證

- 使用時間安全的比較 (`hmac.compare_digest` / `crypto.timingSafeEqual`)
- 防止時序攻擊 (Timing Attack)

### 3. Token 輪替

- 支援無中斷服務的 Token 輪替
- 舊 Token 在寬限期內（預設 2 分鐘）仍然有效
- 寬限期結束後，舊 Token 自動失效

### 4. Token 過期

- 預設 Token 有效期: 24 小時
- 自動檢查並在剩餘 2 小時時進行輪替
- 可配置過期時間

### 5. Token 儲存

- Token 不以明文形式儲存於舊 Token 列表
- 使用 SHA-256 雜湊儲存舊 Token 的識別資訊

## 配置

### Electron 端配置

```javascript
// electron-app/main.js
const TOKEN_CONFIG = {
  rotationCheckIntervalMs: 3600000,  // 每小時檢查一次
  rotationThresholdHours: 2,         // 剩餘 2 小時時輪替
};
```

### TokenManager 配置

```javascript
const manager = new TokenManager({
  tokenLength: 32,           // Token 長度（bytes）
  tokenExpiryHours: 24,      // 過期時間（小時）
  gracePeriodSeconds: 120,   // 寬限期（秒）
  maxRotationHistory: 10,    // 保留的輪替歷史數
});
```

## 最佳實踐

1. **不要在渲染進程中儲存 Token**
   - 每次需要時透過 IPC 取得
   - 避免 XSS 攻擊風險

2. **定期輪替 Token**
   - 使用自動輪替機制
   - 在敏感操作後手動輪替

3. **監控 Token 狀態**
   - 定期檢查 Token 過期時間
   - 處理 Token 輪替事件

4. **安全事件處理**
   - 發現異常時立即 `invalidateToken()`
   - 停止所有服務並重新認證

## 相關文件

- [architecture.md](architecture.md) - 系統架構
- [PHASE3_EDGE_ALL_IN_ONE.md](plans/PHASE3_EDGE_ALL_IN_ONE.md) - Phase 3 規劃

---

**最後更新**: 2025-12-03
