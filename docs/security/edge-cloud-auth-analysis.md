# Edge-Cloud 認證架構分析與建議

> **建立日期**：2025-12-17  
> **狀態**：📋 分析與建議  
> **相關**：威脅模型 v2.0、零信任前端原則

## 執行摘要

基於威脅模型 v2.0 的零信任前端原則，本文件分析將登入移至雲端並同步至 Edge 的認證架構，提供實作建議與優缺點分析。

## 需求分析

### 當前架構問題

1. **Edge 環境認證風險**：
   - Edge 設備物理安全較弱
   - 本地認證資料可能被篡改
   - 離線期間無法驗證憑證有效性

2. **分散式認證管理複雜**：
   - Edge 和 Server 各自維護使用者資料
   - 權限變更無法即時同步
   - 審計追蹤分散

### 目標架構

**Cloud-First Authentication with Edge Token Sync**
- 🔐 **登入在雲端執行**：所有認證在 Server 端驗證
- 🔄 **Token 同步至 Edge**：Edge 快取有效 token 供離線使用
- ⏱️ **短期 token**：減少被盜用風險
- 🔁 **自動更新**：重連時自動更新 token

---

## 方案比較

### 方案 A：完全雲端認證（Online-Only）

**架構**：
```
使用者 → Edge UI → Server API → 認證 → 返回 JWT
              ↓
         每次請求都驗證 Server
```

**優點**：
- ✅ 最高安全性：所有驗證在 Server
- ✅ 即時權限撤銷
- ✅ 集中審計日誌
- ✅ 無本地憑證儲存風險

**缺點**：
- ❌ **無法離線運作**（致命缺陷）
- ❌ 網路延遲影響體驗
- ❌ 網路中斷時系統無法使用
- ❌ 不符合 Edge 低延遲要求 (<100ms)

**適用場景**：純 Server 環境，不適合 Edge 部署

**風險等級**：🔴 高（不符合離線要求）

---

### 方案 B：Token 快取同步（推薦）

**架構**：
```
# 線上登入
使用者 → Edge UI → Server API → 認證 → JWT + Refresh Token
              ↓
         Edge 快取 Token（加密儲存）

# 離線使用（使用快取 Token）
使用者 → Edge UI → 本地驗證 JWT → 允許操作（受限）

# 重連同步
Edge → Server：驗證 Refresh Token → 更新 JWT
       ↓
    同步權限變更
```

**優點**：
- ✅ **支援離線運作**
- ✅ 低延遲：本地驗證快取 token
- ✅ 安全性高：登入在 Server 驗證
- ✅ 靈活：可設定離線期間限制
- ✅ 可審計：重連後同步審計日誌

**缺點**：
- ⚠️ Token 被盜風險（緩解：短期 token + 加密儲存）
- ⚠️ 離線期間權限變更無法即時生效
- ⚠️ 需要複雜的同步邏輯

**適用場景**：Edge 環境標準方案

**風險等級**：🟡 中（可接受，有緩解措施）

**安全緩解措施**：
1. **短期 Access Token**：15 分鐘過期
2. **Refresh Token**：7 天過期，僅用於更新
3. **加密儲存**：使用 OS keychain 或加密檔案
4. **離線操作限制**：敏感操作（新增使用者、權限變更）需線上
5. **重連驗證**：自動更新 token 並同步權限
6. **Token 指紋**：綁定設備 ID，防止跨設備使用

---

### 方案 C：混合認證（Fallback）

**架構**：
```
# 優先雲端
使用者 → Edge UI → 嘗試 Server API
              ↓
         成功：使用 Server JWT
              ↓
         失敗：降級至本地認證（僅基本操作）
```

**優點**：
- ✅ 高可用性：網路故障時仍可用
- ✅ 漸進式降級

**缺點**：
- ❌ 複雜度高：維護兩套認證系統
- ❌ 安全風險：本地認證可能被繞過
- ❌ 審計困難：需要合併兩邊日誌

**適用場景**：高可用性要求但安全性次要的場景

**風險等級**：🟠 中高（複雜度與安全風險）

---

## 推薦方案：方案 B（Token 快取同步）

### 實作策略

#### 1. 認證流程

**初始登入**：
```python
# Server 端 (WebUI/app/routes.py)
@app.route('/auth/login', methods=['POST'])
def login():
    # 1. 驗證使用者名稱與密碼
    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        log_login_attempt(username, success=False)
        return jsonify({'error': 'Invalid credentials'}), 401
    
    # 2. 生成 Access Token (15 分鐘)
    access_token = create_access_token(
        user_id=user.id,
        role=user.role,
        expires_in=900  # 15 minutes
    )
    
    # 3. 生成 Refresh Token (7 天)
    refresh_token = create_refresh_token(
        user_id=user.id,
        device_id=request.headers.get('X-Device-ID'),
        expires_in=604800  # 7 days
    )
    
    # 4. 記錄審計日誌
    log_login_attempt(username, success=True, user_id=user.id)
    
    return jsonify({
        'access_token': access_token,
        'refresh_token': refresh_token,
        'user': user.to_dict(),
        'expires_in': 900
    })
```

**Token 更新**：
```python
@app.route('/auth/refresh', methods=['POST'])
def refresh_token():
    refresh_token = request.json.get('refresh_token')
    
    # 1. 驗證 Refresh Token
    payload = verify_refresh_token(refresh_token)
    if not payload:
        return jsonify({'error': 'Invalid token'}), 401
    
    # 2. 檢查 token 是否被撤銷
    if is_token_revoked(refresh_token):
        return jsonify({'error': 'Token revoked'}), 401
    
    # 3. 獲取最新使用者資料（權限可能已變更）
    user = User.query.get(payload['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # 4. 生成新的 Access Token
    access_token = create_access_token(
        user_id=user.id,
        role=user.role,  # 使用最新角色
        expires_in=900
    )
    
    return jsonify({
        'access_token': access_token,
        'user': user.to_dict()
    })
```

#### 2. Edge 端實作

**Token 管理器**：
```python
# src/robot_service/auth_cache.py

import json
import time
from pathlib import Path
from cryptography.fernet import Fernet
from src.common.config import EdgeConfig

class EdgeAuthCache:
    """Edge 端認證快取管理器"""
    
    def __init__(self):
        self.config = EdgeConfig.from_env()
        self.cache_file = Path(self.config.data_dir) / 'auth_cache.encrypted'
        self.cipher = self._init_cipher()
    
    def _init_cipher(self):
        """初始化加密器（使用設備唯一金鑰）"""
        # 使用設備 ID 生成金鑰
        key = self._get_device_key()
        return Fernet(key)
    
    def save_tokens(self, access_token: str, refresh_token: str, user_data: dict):
        """儲存 token（加密）"""
        data = {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': user_data,
            'cached_at': time.time()
        }
        
        # 加密並儲存
        encrypted = self.cipher.encrypt(json.dumps(data).encode())
        self.cache_file.write_bytes(encrypted)
    
    def load_tokens(self) -> dict:
        """載入 token（解密）"""
        if not self.cache_file.exists():
            return None
        
        try:
            encrypted = self.cache_file.read_bytes()
            decrypted = self.cipher.decrypt(encrypted)
            return json.loads(decrypted.decode())
        except Exception as e:
            # Token 損壞或過期，刪除快取
            self.cache_file.unlink(missing_ok=True)
            return None
    
    def get_valid_access_token(self) -> str:
        """獲取有效的 Access Token"""
        tokens = self.load_tokens()
        if not tokens:
            return None
        
        # 檢查是否過期（提前 1 分鐘更新）
        if not self._is_token_valid(tokens['access_token'], buffer=60):
            # 嘗試使用 Refresh Token 更新
            return self._refresh_access_token(tokens['refresh_token'])
        
        return tokens['access_token']
    
    def _refresh_access_token(self, refresh_token: str) -> str:
        """使用 Refresh Token 更新 Access Token"""
        try:
            response = self._call_server_api('/auth/refresh', {
                'refresh_token': refresh_token
            })
            
            if response['success']:
                # 更新快取
                self.save_tokens(
                    response['access_token'],
                    refresh_token,  # Refresh token 不變
                    response['user']
                )
                return response['access_token']
        except Exception as e:
            # 網路錯誤，返回 None（將使用離線模式）
            return None
    
    def clear(self):
        """清除快取（登出）"""
        self.cache_file.unlink(missing_ok=True)
```

**離線驗證**：
```python
# src/robot_service/offline_auth.py

from flask import request, jsonify
from functools import wraps

class OfflineAuthManager:
    """離線模式認證管理器"""
    
    def __init__(self, cache: EdgeAuthCache):
        self.cache = cache
        self.offline_mode = False
    
    def require_auth(self, allow_offline=True, offline_restricted=False):
        """認證裝飾器"""
        def decorator(f):
            @wraps(f)
            def wrapper(*args, **kwargs):
                # 1. 嘗試線上驗證
                online_user = self._verify_online()
                if online_user:
                    request.current_user = online_user
                    self.offline_mode = False
                    return f(*args, **kwargs)
                
                # 2. 線上驗證失敗，嘗試離線模式
                if allow_offline:
                    offline_user = self._verify_offline()
                    if offline_user:
                        request.current_user = offline_user
                        self.offline_mode = True
                        
                        # 檢查是否為受限操作
                        if offline_restricted:
                            return jsonify({
                                'error': 'This operation requires online connection'
                            }), 403
                        
                        return f(*args, **kwargs)
                
                # 3. 無法驗證
                return jsonify({'error': 'Unauthorized'}), 401
            
            return wrapper
        return decorator
    
    def _verify_online(self):
        """線上驗證（呼叫 Server API）"""
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return None
        
        try:
            # 呼叫 Server 驗證 API
            response = self._call_server('/auth/verify', {'token': token})
            return response['user'] if response['valid'] else None
        except:
            return None
    
    def _verify_offline(self):
        """離線驗證（使用快取）"""
        cached = self.cache.load_tokens()
        if not cached:
            return None
        
        # 驗證 Access Token（本地驗證簽名）
        if self._verify_jwt_signature(cached['access_token']):
            return cached['user']
        
        return None
```

#### 3. 離線操作限制

**操作權限矩陣**：

| 操作類型 | 線上模式 | 離線模式 |
|---------|---------|---------|
| 查看機器人狀態 | ✅ | ✅ |
| 執行基本指令 | ✅ | ✅ |
| 查看指令歷史 | ✅ | ✅（本地快取）|
| 執行進階指令 | ✅ | ✅（需預先下載）|
| 新增/修改使用者 | ✅ | ❌ |
| 變更權限 | ✅ | ❌ |
| 查看審計日誌 | ✅ | ✅（本地副本）|
| 匯出審計日誌 | ✅ | ❌ |
| 固件更新 | ✅ | ⚠️（僅快取檔案）|

**實作範例**：
```python
# Edge API 端點
@app.route('/api/users', methods=['POST'])
@auth.require_auth(offline_restricted=True)
def create_user():
    """建立使用者（需要線上連線）"""
    if auth.offline_mode:
        # 雖然有 offline_restricted=True，但加倍保險
        return jsonify({'error': 'Cannot create users offline'}), 403
    
    # 執行建立邏輯
    ...
```

#### 4. 同步機制

**重連後同步**：
```python
# src/robot_service/sync_manager.py

class EdgeServerSyncManager:
    """Edge-Server 同步管理器"""
    
    def on_reconnect(self):
        """重連時執行同步"""
        # 1. 驗證時間同步（防止 replay attack）
        self._sync_time()
        
        # 2. 更新 Token
        self._refresh_tokens()
        
        # 3. 同步權限與配置
        self._sync_user_permissions()
        
        # 4. 上傳審計日誌
        self._upload_audit_logs()
        
        # 5. 下載進階指令更新
        self._sync_advanced_commands()
    
    def _refresh_tokens(self):
        """更新 Token"""
        cache = EdgeAuthCache()
        tokens = cache.load_tokens()
        
        if tokens and tokens['refresh_token']:
            # 使用 Refresh Token 更新
            new_token = cache._refresh_access_token(tokens['refresh_token'])
            if new_token:
                print("✅ Token refreshed successfully")
            else:
                print("⚠️ Token refresh failed, re-authentication required")
    
    def _upload_audit_logs(self):
        """上傳本地審計日誌到 Server"""
        local_logs = self._get_pending_audit_logs()
        
        for log in local_logs:
            try:
                # Server 端會重新驗證
                response = self._call_server('/audit_logs/sync', {
                    'log': log,
                    'signature': self._sign_log(log)
                })
                
                if response['accepted']:
                    self._mark_log_synced(log['id'])
            except Exception as e:
                # 同步失敗，稍後重試
                continue
```

---

## 安全考量

### Token 安全

1. **短期 Access Token**：
   - 過期時間：15 分鐘
   - 減少被盜用窗口

2. **Refresh Token 保護**：
   - 過期時間：7 天
   - 加密儲存（OS keychain 或 Fernet）
   - 設備綁定（Device ID）
   - 單次使用（rotation）

3. **Token 撤銷**：
   - Server 端維護撤銷清單
   - 重連時檢查是否被撤銷
   - 支援強制登出所有設備

### 離線期間限制

1. **敏感操作禁止**：
   - 新增/刪除使用者
   - 權限變更
   - 系統配置修改

2. **審計日誌累積**：
   - 本地記錄所有操作
   - 重連後上傳到 Server
   - Server 端驗證日誌完整性

3. **時間窗口限制**：
   - 最長離線時間：7 天（Refresh Token 過期）
   - 超過後需重新登入

---

## 實作階段

### Phase 1：Server 端認證 API（1 週）
- [ ] 實作 `/auth/login` 端點
- [ ] 實作 `/auth/refresh` 端點
- [ ] 實作 `/auth/verify` 端點
- [ ] 實作 Token 撤銷機制
- [ ] 單元測試

### Phase 2：Edge 端 Token 快取（1 週）
- [ ] 實作 `EdgeAuthCache` 類別
- [ ] 加密儲存機制
- [ ] Token 自動更新邏輯
- [ ] 單元測試

### Phase 3：離線模式支援（1 週）
- [ ] 實作 `OfflineAuthManager`
- [ ] 離線操作限制
- [ ] 本地 JWT 驗證
- [ ] 整合測試

### Phase 4：同步機制（1 週）
- [ ] 實作 `EdgeServerSyncManager`
- [ ] 審計日誌上傳
- [ ] 權限同步
- [ ] 進階指令下載
- [ ] E2E 測試

### Phase 5：安全加固（1 週）
- [ ] Token rotation
- [ ] 設備指紋
- [ ] 異常偵測
- [ ] 滲透測試

---

## 優缺點總結

### 優點

1. ✅ **安全性**：登入在 Server，集中管理
2. ✅ **離線支援**：Edge 可獨立運作
3. ✅ **低延遲**：本地驗證快取 token
4. ✅ **可審計**：所有操作可追溯
5. ✅ **靈活性**：支援離線期間限制

### 缺點與緩解

1. ⚠️ **Token 被盜風險**
   - 緩解：短期 token + 加密儲存 + 設備綁定
   
2. ⚠️ **離線權限變更延遲**
   - 緩解：重連後強制更新 + 敏感操作需線上
   
3. ⚠️ **實作複雜度**
   - 緩解：分階段實作 + 完整測試

---

## 建議

**推薦實作方案 B（Token 快取同步）**，理由：

1. 符合 Edge 環境需求（低延遲、離線）
2. 安全性可接受（有多層緩解措施）
3. 實作可行性高
4. 符合零信任前端原則

**下一步**：
1. 審查本分析文件
2. 確認實作方案
3. 開始 Phase 1 實作
4. 持續更新威脅模型

---

**參考文件**：
- [threat-model.md](threat-model.md) - 威脅模型 v2.0
- [security-checklist.md](security-checklist.md) - 安全檢查清單
- [architecture.md](../architecture.md) - Edge-Server 架構
