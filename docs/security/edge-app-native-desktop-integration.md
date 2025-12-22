# Edge App Native Desktop Integration - 步驟 2 完整規劃

> **建立日期**：2025-12-22  
> **狀態**：📋 設計與規劃  
> **相關**：方案 B Phase 1、威脅模型 v2.0、零信任前端原則  
> **前置條件**：方案 B Phase 1 (Server 端認證 API) 已完成

---

## 執行摘要

本文件設計 Edge App 的 Native Desktop 整合方案，解決威脅模型 v2.0 中識別的安全問題，並整合 GUI/TUI/CLI 三種介面模式於統一的 native desktop 應用程式中。

### 核心目標

1. **Native Desktop App**：提供跨平台原生桌面應用（Windows/macOS/Linux）
2. **GUI/TUI/CLI 整合**：統一啟動器支援三種介面模式
3. **Token 認證整合**：實作 Edge Token 快取與同步（方案 B Phase 2-5）
4. **威脅緩解**：解決前端驗證繞過、資料注入、Session 劫持等問題
5. **雙版本策略**：提供 Heavy (Electron) 和 Tiny (PyQt) 兩個版本

---

## 目錄

1. [架構設計](#架構設計)
2. [雙版本策略](#雙版本策略)
3. [GUI/TUI/CLI 整合](#guituicli-整合)
4. [Token 認證整合](#token-認證整合)
5. [威脅緩解措施](#威脅緩解措施)
6. [實作階段](#實作階段)
7. [技術規格](#技術規格)
8. [安全考量](#安全考量)

---

## 架構設計

### 整體架構

```
┌─────────────────────────────────────────────────────────────────┐
│                   Native Desktop App (Edge)                       │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                  統一啟動器 (Unified Launcher)              │ │
│  │  • 模式選擇 (GUI/TUI/CLI)                                   │ │
│  │  • Token 初始化與驗證                                       │ │
│  │  • 服務協調與生命週期管理                                   │ │
│  └──────┬─────────────────────┬──────────────────┬────────────┘ │
│         │                     │                  │              │
│  ┌──────▼─────┐        ┌──────▼──────┐   ┌──────▼──────┐     │
│  │  GUI Mode  │        │  TUI Mode   │   │  CLI Mode   │     │
│  │            │        │             │   │             │     │
│  │ Electron/  │        │  Rich/      │   │  argparse   │     │
│  │ PyQt       │        │  Textual    │   │  + batch    │     │
│  └──────┬─────┘        └──────┬──────┘   └──────┬──────┘     │
│         │                     │                  │              │
│         └─────────────────────┴──────────────────┘              │
│                               │                                 │
│         ┌─────────────────────▼─────────────────────┐          │
│         │      Edge Token Cache & Sync Manager       │          │
│         │  • Token 快取（加密儲存）                   │          │
│         │  • 自動更新過期 Token                       │          │
│         │  • Device ID 管理                          │          │
│         │  • 離線模式支援                            │          │
│         └─────────────────────┬─────────────────────┘          │
│                               │                                 │
│         ┌─────────────────────▼─────────────────────┐          │
│         │         Robot Service (Local Flask)        │          │
│         │  • 本地 API 服務                            │          │
│         │  • 指令處理與佇列管理                       │          │
│         │  • LLM 整合                                 │          │
│         └─────────────────────┬─────────────────────┘          │
│                               │                                 │
└───────────────────────────────┼─────────────────────────────────┘
                                │ HTTPS + JWT Token
                                │
                    ┌───────────▼───────────┐
                    │   Cloud Server API    │
                    │  • /api/auth/login    │
                    │  • /api/auth/refresh  │
                    │  • /api/auth/verify   │
                    └───────────────────────┘
```

### 核心組件

#### 1. 統一啟動器 (Unified Launcher)

**職責**：
- 解析啟動參數決定模式（GUI/TUI/CLI）
- 初始化 Token 管理器
- 驗證或提示使用者登入
- 啟動對應介面

**實作位置**：`src/robot_service/unified_launcher.py`（已存在，需增強）

```python
# 增強的 unified_launcher.py
import argparse
import sys
from edge_token_cache import EdgeAuthCache
from token_integration import TokenIntegration

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['gui', 'tui', 'cli'], default='gui')
    parser.add_argument('--login', action='store_true', help='Force re-login')
    parser.add_argument('--offline', action='store_true', help='Offline mode')
    args = parser.parse_args()
    
    # 初始化 Token 管理
    token_cache = EdgeAuthCache()
    token_integration = TokenIntegration(token_cache)
    
    # 驗證或登入
    if args.login or not token_cache.has_valid_token():
        if not args.offline:
            # 提示登入
            login_required = True
        else:
            # 離線模式檢查
            if not token_cache.has_cached_token():
                print("錯誤：離線模式需要有效的快取 token")
                sys.exit(1)
    
    # 啟動對應模式
    if args.mode == 'gui':
        launch_gui(token_integration)
    elif args.mode == 'tui':
        launch_tui(token_integration)
    else:
        launch_cli(token_integration, args)
```

#### 2. Edge Token Cache (Phase 2)

**檔案**：`src/robot_service/edge_token_cache.py`（已存在，需完善）

**功能**：
- 加密儲存 Access Token 和 Refresh Token
- 自動檢測過期並更新
- Device ID 綁定
- 離線模式支援

**實作規格**：
```python
from cryptography.fernet import Fernet
import os
import json
from datetime import datetime, timedelta

class EdgeAuthCache:
    """
    Edge 端 Token 快取管理器
    
    安全特性：
    - Fernet 對稱加密（AES-128）
    - OS Keychain 整合（macOS/Windows）
    - Device ID 綁定
    - 自動過期檢測
    """
    
    def __init__(self, cache_dir=None):
        self.cache_dir = cache_dir or self._get_default_cache_dir()
        self.cache_file = os.path.join(self.cache_dir, 'token_cache.enc')
        self.key_file = os.path.join(self.cache_dir, '.key')
        self._ensure_cache_dir()
        self._init_encryption_key()
    
    def save_tokens(self, access_token, refresh_token, device_id, expires_in):
        """儲存 tokens（加密）"""
        data = {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'device_id': device_id,
            'expires_at': (datetime.now() + timedelta(seconds=expires_in)).isoformat(),
            'cached_at': datetime.now().isoformat()
        }
        encrypted = self.fernet.encrypt(json.dumps(data).encode())
        with open(self.cache_file, 'wb') as f:
            f.write(encrypted)
    
    def get_valid_access_token(self):
        """取得有效的 Access Token（自動更新）"""
        tokens = self._load_tokens()
        if not tokens:
            return None
        
        # 檢查是否過期
        expires_at = datetime.fromisoformat(tokens['expires_at'])
        if datetime.now() >= expires_at - timedelta(minutes=2):
            # 即將過期，嘗試更新
            return self._refresh_token(tokens['refresh_token'])
        
        return tokens['access_token']
    
    def _refresh_token(self, refresh_token):
        """使用 Refresh Token 更新 Access Token"""
        import requests
        response = requests.post(
            f"{self.server_url}/api/auth/refresh",
            json={'refresh_token': refresh_token},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            self.save_tokens(
                data['access_token'],
                data['refresh_token'],
                data['device_id'],
                data['expires_in']
            )
            return data['access_token']
        return None
    
    def clear(self):
        """清除快取的 tokens（登出）"""
        if os.path.exists(self.cache_file):
            os.remove(self.cache_file)
```

#### 3. Token Integration (已實作)

**檔案**：`src/robot_service/token_integration.py`（已存在）

**功能**：
- 整合 Token Cache 與 Robot Service
- HTTP 請求自動加入 Authorization header
- Token 過期自動處理
- 離線模式降級

---

## 雙版本策略

### Heavy Version (Electron)

**適用場景**：
- ✅ 開發與測試環境
- ✅ 進階使用者
- ✅ 需要豐富 UI 互動
- ✅ 硬體資源充足（>4GB RAM）

**技術棧**：
- Electron (主框架)
- React (前端)
- Node.js (後端服務啟動)
- Chromium (內嵌 WebView)

**安裝包大小**：150-300MB  
**記憶體佔用**：300-500MB  
**啟動時間**：2-5秒

**實作位置**：`electron-app/`

### Tiny Version (PyQt)

**適用場景**：
- ✅ 生產環境
- ✅ 資源受限設備（<4GB RAM）
- ✅ 快速啟動需求
- ✅ 只需核心功能

**技術棧**：
- PyQt6 (主框架)
- QtWebEngineView (WebView)
- Flask (本地 Web 服務)
- Jinja2 Templates (UI)

**安裝包大小**：40-60MB  
**記憶體佔用**：150-250MB  
**啟動時間**：1-3秒

**實作位置**：`qtwebview-app/` (Phase 3.2)

### 版本對照表

| 特性 | Heavy (Electron) | Tiny (PyQt) |
|------|------------------|-------------|
| 安裝包 | ~200MB | ~50MB |
| 記憶體 | ~400MB | ~200MB |
| 啟動速度 | 3秒 | 1.5秒 |
| UI 框架 | React | Flask Templates |
| WebView | Chromium (內嵌) | Qt (系統) |
| 開發工具 | ✅ DevTools | ⚠️ 有限 |
| 熱重載 | ✅ 支援 | ❌ 不支援 |
| 離線支援 | ✅ 完整 | ✅ 完整 |
| Token 認證 | ✅ 支援 | ✅ 支援 |
| 自動更新 | ✅ 支援 | ✅ 支援 |

---

## GUI/TUI/CLI 整合

### 統一啟動模式

```bash
# GUI 模式（預設）
./robot-edge-app

# TUI 模式
./robot-edge-app --mode tui

# CLI 模式
./robot-edge-app --mode cli --command "status"

# 批次模式
./robot-edge-app --mode cli --batch commands.txt

# 強制登入
./robot-edge-app --login

# 離線模式
./robot-edge-app --offline
```

### 1. GUI Mode

**實作方式**：
- Heavy: Electron + React (已實作於 `electron-app/`)
- Tiny: PyQt6 + QtWebView (規劃於 `qtwebview-app/`)

**功能**：
- ✅ 視覺化指令建立與執行
- ✅ 機器人狀態監控
- ✅ 指令歷史查看
- ✅ 系統托盤整合
- ✅ Token 管理 UI

**啟動邏輯**：
```python
def launch_gui(token_integration):
    """啟動 GUI 模式"""
    import sys
    import platform
    
    # 檢測平台與安裝的版本
    if platform.system() == 'Darwin' and has_electron():
        # macOS 優先使用 Electron
        launch_electron_gui(token_integration)
    elif has_pyqt():
        # 其他平台使用 PyQt
        launch_pyqt_gui(token_integration)
    else:
        print("錯誤：未安裝 GUI 支援")
        sys.exit(1)

def launch_electron_gui(token_integration):
    """啟動 Electron GUI"""
    from subprocess import Popen
    import os
    
    electron_path = os.path.join(os.path.dirname(__file__), '../../electron-app')
    env = os.environ.copy()
    env['TOKEN_INTEGRATION'] = token_integration.get_token()
    
    Popen(['npm', 'start'], cwd=electron_path, env=env)

def launch_pyqt_gui(token_integration):
    """啟動 PyQt GUI"""
    from PyQt6.QtWidgets import QApplication
    from qtwebview_app.main import MainWindow
    
    app = QApplication(sys.argv)
    window = MainWindow(token_integration)
    window.show()
    sys.exit(app.exec())
```

### 2. TUI Mode

**實作位置**：`src/robot_service/tui/`（已實作）

**功能**：
- ✅ 終端機介面
- ✅ 互動式指令輸入
- ✅ 即時狀態顯示
- ✅ 支援 LLM 輔助

**框架**：Rich / Textual

**啟動邏輯**：
```python
def launch_tui(token_integration):
    """啟動 TUI 模式"""
    from src.robot_service.tui.main import TUIApp
    
    app = TUIApp(token_integration)
    app.run()
```

### 3. CLI Mode

**實作位置**：`src/robot_service/cli/`（已實作）

**功能**：
- ✅ 命令列指令
- ✅ 批次處理
- ✅ 腳本整合
- ✅ CI/CD 支援

**啟動邏輯**：
```python
def launch_cli(token_integration, args):
    """啟動 CLI 模式"""
    from src.robot_service.cli.main import CLIApp
    
    cli = CLIApp(token_integration)
    
    if args.batch:
        # 批次模式
        cli.run_batch(args.batch)
    elif args.command:
        # 單一指令
        cli.run_command(args.command)
    else:
        # 互動模式
        cli.run_interactive()
```

---

## Token 認證整合

### Phase 2: Edge Token 快取

**目標**：實作本地 Token 快取與加密儲存

**實作清單**：
- [x] `EdgeAuthCache` 類別（基礎版已實作）
- [ ] Fernet 加密整合
- [ ] OS Keychain 整合（macOS/Windows）
- [ ] Device ID 管理
- [ ] Token 過期檢測

**安全要求**：
1. Token 必須加密儲存（Fernet AES-128）
2. 加密金鑰儲存於 OS Keychain（可選）
3. 檔案權限限制為僅使用者可讀
4. 支援 Device ID 綁定驗證

### Phase 3: 離線模式支援

**目標**：實作離線操作與權限限制

**離線操作矩陣**：

| 操作類型 | 線上模式 | 離線模式 | 說明 |
|---------|---------|---------|------|
| 查看機器人狀態 | ✅ | ✅ | 本地快取 |
| 執行基本指令 | ✅ | ✅ | 本地佇列 |
| 查看指令歷史 | ✅ | ✅ | 本地資料庫 |
| 新增/修改使用者 | ✅ | ❌ | 需線上驗證 |
| 變更權限 | ✅ | ❌ | 需線上驗證 |
| 系統配置變更 | ✅ | ❌ | 需線上驗證 |
| LLM 指令解析 | ✅ | ⚠️ | 降級為本地模型 |

**實作**：
```python
def require_online(func):
    """裝飾器：要求線上模式"""
    def wrapper(*args, **kwargs):
        token_integration = args[0].token_integration
        if not token_integration.is_online():
            raise OfflineError("此操作需要線上連線")
        return func(*args, **kwargs)
    return wrapper

class RobotService:
    @require_online
    def create_user(self, username, role):
        """建立使用者（需線上）"""
        pass
    
    def execute_command(self, command_id):
        """執行指令（離線可用）"""
        pass
```

### Phase 4: 同步機制

**目標**：重連後自動同步資料與權限

**同步流程**：
```
1. 偵測網路恢復
2. 驗證快取的 Refresh Token
3. 更新 Access Token
4. 同步使用者權限
5. 上傳離線期間的審計日誌
6. 同步指令執行結果
```

**實作**：
```python
class EdgeServerSyncManager:
    """Edge-Server 同步管理器"""
    
    def on_reconnect(self):
        """重連事件處理"""
        # 1. 更新 Token
        new_token = self.token_cache.refresh_token()
        
        # 2. 同步權限
        self.sync_permissions()
        
        # 3. 上傳審計日誌
        self.upload_audit_logs()
        
        # 4. 同步指令結果
        self.sync_command_results()
    
    def sync_permissions(self):
        """同步使用者權限"""
        response = requests.get(
            f"{self.server_url}/api/auth/me",
            headers={'Authorization': f'Bearer {self.token_cache.get_valid_access_token()}'}
        )
        user_data = response.json()
        self.update_local_permissions(user_data)
```

### Phase 5: 安全加固

**目標**：Token 撤銷、速率限制、異常偵測

**實作清單**：
- [ ] Token 撤銷機制
- [ ] 速率限制（防止暴力破解）
- [ ] 異常登入偵測
- [ ] Device ID 變更告警
- [ ] Token 洩漏偵測

---

## 威脅緩解措施

### 對應威脅模型 v2.0

#### 0.1 前端驗證繞過 🔴

**威脅**：攻擊者修改前端代碼繞過驗證

**緩解措施**：
1. ✅ 所有認證在 Server 端執行
2. ✅ Edge 不儲存密碼
3. ✅ 業務邏輯完全在後端
4. ✅ 前端僅為展示層

**實作**：
```python
# ✅ 正確：後端驗證
@app.route('/api/command/create', methods=['POST'])
@require_auth
def create_command():
    # Server 端完整驗證
    data = validate_schema(request.json, CommandSchema)
    if not current_user.has_permission('create_command'):
        abort(403)
    # 業務邏輯...

# ❌ 錯誤：依賴前端驗證
# if (userRole === 'admin') { // 前端檢查，可被繞過 }
```

#### 0.2 前端資料注入攻擊 🔴

**威脅**：XSS、SQL 注入、指令注入

**緩解措施**：
1. ✅ 輸入清理與驗證（Pydantic）
2. ✅ 參數化查詢（SQLAlchemy ORM）
3. ✅ 白名單驗證
4. ✅ Jinja2 自動轉義啟用

**實作**：
```python
# ✅ 正確：使用 Pydantic 驗證
from pydantic import BaseModel, validator

class CommandRequest(BaseModel):
    command: str
    robot_id: int
    
    @validator('command')
    def validate_command(cls, v):
        # 白名單驗證
        allowed_commands = ['move', 'stop', 'rotate']
        if v not in allowed_commands:
            raise ValueError(f'Invalid command: {v}')
        return v

# ✅ 正確：參數化查詢
robot = Robot.query.filter_by(id=robot_id).first()

# ❌ 錯誤：SQL 注入風險
# robot = db.execute(f"SELECT * FROM robots WHERE id = {robot_id}")
```

#### 0.3 Edge 資料篡改威脅 🟠

**威脅**：物理訪問篡改本地資料庫

**緩解措施**：
1. ✅ Server 端重新驗證所有 Edge 資料
2. ✅ Token 簽名驗證（JWT）
3. ✅ 審計日誌完整性檢查
4. ✅ 不信任 Edge 來源

**實作**：
```python
# ✅ 正確：Server 重新驗證
def sync_from_edge(edge_data):
    # 1. Schema 驗證
    validated = AuditLogSchema.validate(edge_data)
    
    # 2. Token 簽名驗證
    if not verify_jwt_signature(edge_data['token']):
        raise SecurityError("Invalid token signature")
    
    # 3. 業務邏輯驗證
    if not verify_user_exists(validated['user_id']):
        raise ValidationError("User not found")
    
    # 4. 儲存
    db.session.add(AuditLog(**validated))
```

#### 0.4 WebUI Session 劫持 🔴

**威脅**：Token/Cookie 竊取

**緩解措施**：
1. ✅ 短期 Access Token（15 分鐘）
2. ✅ Refresh Token rotation（單次使用）
3. ✅ Device ID 綁定
4. ✅ HTTPS 強制
5. ✅ HttpOnly + Secure + SameSite cookies

**實作**：
```python
# Access Token：短期
access_token_expires = timedelta(minutes=15)

# Refresh Token：設備綁定
refresh_token_payload = {
    'user_id': user.id,
    'device_id': device_id,
    'type': 'refresh'
}

# Token Rotation：單次使用
def refresh_access_token(refresh_token):
    # 驗證舊 token
    payload = verify_jwt(refresh_token)
    
    # 撤銷舊 token
    revoke_token(refresh_token)
    
    # 發放新的 token 對
    new_access = generate_access_token(payload['user_id'])
    new_refresh = generate_refresh_token(payload['user_id'], payload['device_id'])
    
    return new_access, new_refresh
```

---

## 實作階段

### Phase 2.1: Edge Token 快取（2 週）

**目標**：完成本地 Token 快取與加密儲存

**任務清單**：
- [ ] 完善 `EdgeAuthCache` 類別
  - [ ] Fernet 加密整合
  - [ ] OS Keychain 整合（macOS: keyring, Windows: DPAPI）
  - [ ] Token 過期自動檢測
  - [ ] Device ID 管理
- [ ] 整合至 `unified_launcher.py`
  - [ ] 啟動時檢查 Token
  - [ ] 過期時提示登入
  - [ ] 登入流程整合
- [ ] 測試
  - [ ] 單元測試（加密/解密）
  - [ ] 整合測試（完整登入流程）
  - [ ] 跨平台測試

**交付物**：
- 完善的 `edge_token_cache.py`
- 測試套件（`tests/test_edge_token_cache.py`）
- 使用文件

### Phase 2.2: GUI 模式整合（2 週）

**目標**：整合 Token 認證至 GUI 模式

**任務清單**：
- [ ] Electron GUI 整合
  - [ ] Token 傳遞機制（環境變數/IPC）
  - [ ] 登入 UI
  - [ ] Token 過期處理
- [ ] PyQt GUI 整合（如果已實作）
  - [ ] QWebChannel 橋接
  - [ ] Token 管理 UI
- [ ] 統一啟動邏輯
  - [ ] `launch_gui()` 函數
  - [ ] 版本偵測與選擇

**交付物**：
- 更新的 `electron-app/` 或 `qtwebview-app/`
- GUI 整合測試
- 使用者指引

### Phase 2.3: 離線模式支援（2 週）

**目標**：實作離線操作與權限限制

**任務清單**：
- [ ] 離線模式檢測
  - [ ] 網路狀態監控
  - [ ] 快取 Token 驗證
- [ ] 權限限制實作
  - [ ] `@require_online` 裝飾器
  - [ ] 操作白名單定義
  - [ ] 離線錯誤處理
- [ ] 本地資料快取
  - [ ] 機器人狀態
  - [ ] 指令歷史
  - [ ] 配置資料

**交付物**：
- 離線模式支援程式碼
- 操作權限矩陣實作
- 測試套件

### Phase 2.4: 同步機制（2 週）

**目標**：實作重連後自動同步

**任務清單**：
- [ ] `EdgeServerSyncManager` 類別
  - [ ] 網路恢復偵測
  - [ ] Token 自動更新
  - [ ] 權限同步
  - [ ] 審計日誌上傳
  - [ ] 指令結果同步
- [ ] 衝突解決策略
  - [ ] Server 優先原則
  - [ ] 時間戳比對
- [ ] 同步狀態 UI

**交付物**：
- `edge_token_sync.py` 完整實作
- 同步測試案例
- 文件

### Phase 2.5: 安全加固（1 週）

**目標**：Token 撤銷、速率限制、異常偵測

**任務清單**：
- [ ] Token 撤銷機制
  - [ ] Server 端撤銷 API
  - [ ] Edge 端撤銷檢查
- [ ] 速率限制
  - [ ] 登入嘗試限制
  - [ ] API 請求限制
- [ ] 異常偵測
  - [ ] Device ID 變更告警
  - [ ] 異地登入偵測
  - [ ] Token 洩漏偵測

**交付物**：
- 安全加固功能
- 安全測試報告
- 文件更新

---

## 技術規格

### 開發環境

**必要工具**：
- Python 3.8+
- Node.js 16+ (Electron)
- PyQt6 (Tiny 版本)
- Git

**依賴管理**：
```bash
# Python 依賴
pip install -r requirements.txt

# Electron 依賴
cd electron-app && npm install

# PyQt 依賴（Tiny 版本）
pip install PyQt6 PyQt6-WebEngine
```

### 打包與發佈

#### Electron (Heavy)

```bash
# 開發模式
cd electron-app
npm start

# 打包
npm run build:mac    # macOS
npm run build:win    # Windows
npm run build:linux  # Linux
```

#### PyQt (Tiny)

```bash
# 開發模式
python qtwebview-app/main.py

# 打包
pyinstaller --onefile --windowed qtwebview-app/main.py
```

### 跨平台支援

| 平台 | Heavy | Tiny | 說明 |
|------|-------|------|------|
| macOS | ✅ | ✅ | 完整支援 |
| Windows | ✅ | ✅ | 完整支援 |
| Linux | ✅ | ✅ | 完整支援 |
| Raspberry Pi | ❌ | ✅ | 僅 Tiny 版本 |

---

## 安全考量

### Token 儲存安全

**加密方式**：
```python
from cryptography.fernet import Fernet

# 生成金鑰（首次啟動）
key = Fernet.generate_key()

# 加密
cipher_suite = Fernet(key)
encrypted_token = cipher_suite.encrypt(token.encode())

# 解密
decrypted_token = cipher_suite.decrypt(encrypted_token).decode()
```

**金鑰儲存**：

**macOS**：
```python
import keyring
keyring.set_password("robot-edge-app", "encryption_key", key.decode())
key = keyring.get_password("robot-edge-app", "encryption_key").encode()
```

**Windows**：
```python
import win32crypt
encrypted_key = win32crypt.CryptProtectData(key)
key = win32crypt.CryptUnprotectData(encrypted_key)
```

**Linux**：
```python
# 使用檔案權限保護（chmod 600）
import os
os.chmod(key_file, 0o600)
```

### 檔案權限

```python
import os
import stat

# 限制僅使用者可讀寫
os.chmod(cache_file, stat.S_IRUSR | stat.S_IWUSR)  # 0o600
```

### Device ID 生成

```python
import uuid
import hashlib
import platform

def generate_device_id():
    """生成唯一的設備 ID"""
    # 組合多個系統資訊
    info = [
        platform.node(),           # 主機名
        platform.system(),          # 作業系統
        str(uuid.getnode()),        # MAC 地址
    ]
    
    # 生成穩定的 hash
    combined = ':'.join(info)
    device_id = hashlib.sha256(combined.encode()).hexdigest()[:32]
    
    return device_id
```

### 審計日誌

所有 Token 操作必須記錄：

```python
from WebUI.app.audit import log_audit_event

# Token 生成
log_audit_event(
    action='token_generate',
    message=f'為使用者 {user.username} 生成 Token',
    user_id=user.id,
    context={'device_id': device_id}
)

# Token 更新
log_audit_event(
    action='token_refresh',
    message=f'Token 自動更新',
    user_id=user.id
)

# Token 撤銷
log_audit_event(
    action='token_revoke',
    message=f'Token 已撤銷',
    user_id=user.id
)
```

---

## 完成定義

### Phase 2 完成標準

- [ ] Edge Token Cache 完整實作
  - [ ] 加密儲存
  - [ ] OS Keychain 整合
  - [ ] 自動過期檢測
  - [ ] Device ID 綁定
- [ ] GUI/TUI/CLI 整合
  - [ ] 統一啟動器
  - [ ] 三種模式正常運作
  - [ ] Token 認證整合
- [ ] 離線模式支援
  - [ ] 操作權限限制
  - [ ] 本地快取機制
- [ ] 同步機制
  - [ ] 自動重連
  - [ ] 資料同步
- [ ] 測試完整
  - [ ] 單元測試 >90% 覆蓋率
  - [ ] 整合測試通過
  - [ ] 跨平台測試
- [ ] 文件完整
  - [ ] 實作文件
  - [ ] 使用者指引
  - [ ] API 文件
- [ ] 安全驗證
  - [ ] 通過 CodeQL 掃描
  - [ ] 安全審查通過
  - [ ] 威脅緩解措施到位

---

## 後續步驟

### 步驟 3：RabbitMQ 最佳實作

在完成 Edge App 整合後，將套用相同模式實作 Edge-Worker 間的 RabbitMQ 通訊：

1. **安全通訊**：TLS/SSL 加密
2. **認證整合**：使用相同的 Token 機制
3. **訊息簽名**：防止訊息篡改
4. **審計追蹤**：完整的訊息日誌

詳細規劃將在步驟 2 完成後提供。

---

## 參考文件

- [方案 B Phase 1 實作文件](approach-b-implementation.md)
- [威脅模型 v2.0](threat-model.md)
- [安全檢查清單](security-checklist.md)
- [Edge-Cloud 認證分析](edge-cloud-auth-analysis.md)
- [架構文件](../architecture.md)
- [Phase 3.2 QtWebView 規劃](../phase3/PHASE3_2_QTWEBVIEW_PLAN.md)

---

**版本**：1.0  
**作者**：Copilot  
**最後更新**：2025-12-22
