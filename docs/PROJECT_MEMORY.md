# 專案記憶

> **用途**：此文件專門用於存儲 AI 助手（如 GitHub Copilot）在開發過程中學習到的經驗教訓、最佳實踐和重要發現。
> 
> **使用方式**：
> - AI 助手在每次任務完成後應更新此文件，記錄新的經驗教訓
> - 開發者可參考此文件了解過去遇到的問題和解決方案
> - 此文件不應包含架構設計、規劃或功能說明（這些請放在其他專門文件中）
> 
> 📖 **其他文件**：[architecture.md](architecture.md)、[plans/](plans/)、[development/](development/)

---

## 📋 相關文件索引

| 類別 | 文件 |
|------|------|
| **架構** | [architecture.md](architecture.md) |
| **規劃** | [plans/MASTER_PLAN.md](plans/MASTER_PLAN.md)、[plans/PHASE3_EDGE_ALL_IN_ONE.md](plans/PHASE3_EDGE_ALL_IN_ONE.md) |
| **開發指南** | [development/](development/) |
| **功能文件** | [features/](features/) |
| **安全文件** | [security/TOKEN_SECURITY.md](security/TOKEN_SECURITY.md) |
| **Phase 3 文件** | [phase3/PHASE3_1_STATUS_REPORT.md](phase3/PHASE3_1_STATUS_REPORT.md)、[phase3/TEST_PLAN_PHASE3_1.md](phase3/TEST_PLAN_PHASE3_1.md) |

---

## 💡 經驗教訓

### Python 時間處理

```python
# ❌ 不要使用（Python 3.12+ 已棄用）
timestamp = datetime.utcnow()

# ✅ 應該使用
timestamp = datetime.now(timezone.utc)
```

**原因**：`datetime.utcnow()` 在 Python 3.12+ 中已被棄用。

### ISO 時間格式

```python
# ❌ 不要這樣（會產生 +00:00Z 格式錯誤）
timestamp = datetime.now(timezone.utc).isoformat() + "Z"

# ✅ 直接使用 isoformat（已包含 +00:00）
timestamp = datetime.now(timezone.utc).isoformat()
```

### 共用模組使用

```python
# ❌ 不要在各模組重複定義
class CustomJsonFormatter(jsonlogger.JsonFormatter):
    ...

# ✅ 使用共用模組
from .utils import setup_json_logging
logger = setup_json_logging(__name__, service_name='mcp-api')
```

**原因**：消除代碼重複，統一日誌格式。

### Pydantic V2 遷移

```python
# ⚠️ 即將棄用
data = model.dict()

# ✅ Pydantic V2 建議
data = model.model_dump()
```

### HTTP 會話重用

```python
# ❌ 每次都建立新會話
async with aiohttp.ClientSession() as session:
    ...

# ✅ 重用會話
async def _get_http_session(self):
    if self._http_session is None or self._http_session.closed:
        self._http_session = aiohttp.ClientSession()
    return self._http_session
```

**原因**：每次建立新的 HTTP 會話有額外開銷。

### 競態條件防護

```python
# ❌ 直接存取可能為 None 的屬性
if self._process.poll() is not None:
    ...

# ✅ 先儲存引用再檢查
process = self._process
if process is None or process.poll() is not None:
    ...
```

**原因**：在非同步環境中，屬性可能被其他協程修改。

### 安全的 Token 生成

```python
# ❌ 使用硬編碼預設 token
token = os.environ.get("APP_TOKEN", "dev-token")

# ✅ 使用安全的隨機 token
import secrets
token = os.environ.get("APP_TOKEN") or secrets.token_hex(32)
```

**原因**：硬編碼的預設 token 是安全風險。

### 服務啟動異常恢復

> 📖 **詳細指南**：[development/STARTUP_RECOVERY_GUIDE.md](development/STARTUP_RECOVERY_GUIDE.md)

**經驗教訓**：
1. 啟動成功時不要重置 `startup_retry_count`，以便追蹤重試次數
2. 使用告警機制通知每次重試和最終失敗
3. 將實際啟動邏輯分離到 `_do_start_service()` 以便重試

### 指令處理器設計

```python
# ✅ 使用分派器模式解耦指令處理和執行
processor = CommandProcessor(action_dispatcher=my_dispatcher)
```

**原因**：分派器模式允許在不同環境中靈活配置執行邏輯。

### 動作驗證

```python
# ✅ 驗證動作在有效清單中
if action_name not in VALID_ACTIONS:
    logger.warning(f"Invalid action: {action_name}")
```

**原因**：防止無效動作導致執行錯誤。

### Token 安全比較

```python
# ❌ 直接使用 hmac.compare_digest（可能拋出異常）
if hmac.compare_digest(token, valid_token):
    return True

# ✅ 先檢查長度再進行比較
if len(token) == len(valid_token) and \
   hmac.compare_digest(token, valid_token):
    return True
```

**原因**：`hmac.compare_digest` 在比較不同長度的字串時可能拋出 `TypeError`。同時先檢查長度可以避免不必要的時序洩漏。

### 執行緒鎖與方法呼叫

```python
# ❌ 在持有鎖的情況下呼叫也需要獲取鎖的方法（會造成死鎖）
def rotate_token(self):
    with self._lock:
        # generate_token 也會嘗試獲取 self._lock
        new_token, new_info = self.generate_token()

# ✅ 提取內部邏輯避免重複獲取鎖
def rotate_token(self):
    with self._lock:
        self._archive_current_token()
        # 直接執行 token 生成邏輯
        token = secrets.token_hex(self._token_length)
        ...
```

**原因**：Python 的 `threading.Lock` 是非重入鎖，同一執行緒重複獲取會造成死鎖。使用 `threading.RLock`（可重入鎖）或提取內部邏輯可解決此問題。

### Token 輪替設計

> 📖 **詳細指南**：[security/TOKEN_SECURITY.md](security/TOKEN_SECURITY.md)

**經驗教訓**：
1. Token 輪替時應保留舊 Token 的寬限期，避免服務中斷
2. 使用雜湊存儲舊 Token 以避免明文儲存
3. 定期清理過期的舊 Token 以防止記憶體洩漏
4. 輪替事件應通知所有相關訂閱者

### 5.1 Flask 配置遷移（2.3+）

```python
# ⚠️ 舊版本配置方式（Flask 2.3+ 已棄用）
app.config['JSON_AS_ASCII'] = False

# ✅ Flask 2.3+ 建議使用
app.json.ensure_ascii = False
```

**原因**：Flask 2.3 更新了 JSON 配置方式，舊的配置鍵將被移除。

### 5.2 SQLAlchemy 2.0 遷移

```python
# ⚠️ SQLAlchemy 1.x 風格（將棄用）
user = User.query.get(user_id)

# ✅ SQLAlchemy 2.0 風格
user = db.session.get(User, user_id)
```

**原因**：`Query.get()` 在 SQLAlchemy 2.0 中已被標記為遺留 API。

### 5.3 datetime_utils 使用統一化

```python
# ❌ 直接使用 datetime.now(timezone.utc)
timestamp = datetime.now(timezone.utc).isoformat()

# ✅ 使用共用 datetime_utils
from src.common.datetime_utils import utc_now_iso
timestamp = utc_now_iso()
```

**原因**：統一時間處理，減少代碼重複，便於未來維護。

---

## 🚀 Phase 3.1 經驗教訓

> 📖 **詳細報告**：[phase3/PHASE3_1_STATUS_REPORT.md](phase3/PHASE3_1_STATUS_REPORT.md)

### 6.1 服務協調器設計模式

```python
# ✅ 使用抽象基礎類別定義服務介面
class ServiceBase(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass
    
    @abstractmethod
    async def start(self) -> bool:
        pass
    
    @abstractmethod
    async def stop(self, timeout: Optional[float] = None) -> bool:
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        pass
```

**經驗教訓**：
1. 使用抽象基礎類別確保所有服務實作統一的介面
2. 服務協調器負責生命週期管理，服務本身只負責自身邏輯
3. 服務狀態應由外部協調器追蹤，避免服務自己管理狀態導致不一致

### 6.2 共享狀態管理器設計

```python
# ✅ 整合狀態存儲和事件匯流排
class SharedStateManager:
    def __init__(self, db_path=None):
        self._state_store = LocalStateStore(db_path=db_path)
        self._event_bus = LocalEventBus()
    
    async def update_robot_status(self, robot_id: str, status: Dict):
        # 更新狀態
        await self._state_store.set(key, status)
        # 發布事件通知訂閱者
        await self._event_bus.publish(EventTopics.ROBOT_STATUS_UPDATED, {...})
```

**經驗教訓**：
1. 狀態更新和事件通知應在同一處理中完成，確保一致性
2. 使用預定義的狀態鍵（`StateKeys`）和事件主題（`EventTopics`）避免拼寫錯誤
3. SQLite 作為本地狀態存儲可滿足 Edge 環境需求，支援 TTL 過期
4. 事件匯流排應支援通配符訂閱以便監控所有相關事件

### 6.3 服務註冊安全檢查

```python
# ❌ 直接覆蓋已註冊的服務
def register_service(self, service: ServiceBase):
    self._services[service.name] = service  # 可能覆蓋運行中的服務

# ✅ 檢查服務狀態後再註冊
def register_service(self, service: ServiceBase):
    if service.name in self._services:
        old_service = self._services[service.name]
        if old_service.is_running:
            raise ValueError(f"Cannot replace running service: {service.name}")
```

**原因**：替換正在運行的服務可能導致資源洩漏和狀態不一致。

### 6.4 非同步狀態變更通知

```python
# ✅ 使用回呼機制通知狀態變更
def set_state_change_callback(
    self,
    callback: Callable[[str, ServiceStatus, ServiceStatus], Coroutine],
) -> None:
    self._state_change_callback = callback

async def _notify_state_change(
    self,
    service_name: str,
    old_status: ServiceStatus,
    new_status: ServiceStatus,
) -> None:
    if old_status == new_status:
        return  # 避免重複通知
    if self._state_change_callback:
        await self._state_change_callback(service_name, old_status, new_status)
```

**經驗教訓**：
1. 狀態變更通知應是非同步的，避免阻塞主流程
2. 只在狀態實際變更時通知，避免冗餘通知
3. 回呼失敗不應影響主流程，需要錯誤處理

### 6.5 健康檢查任務可取消設計

```python
# ✅ 使用 shutdown event 實現可取消的定期任務
async def _periodic_health_check(self) -> None:
    while self._running:
        try:
            await asyncio.wait_for(
                self._shutdown_event.wait(),
                timeout=self._health_check_interval,
            )
            break  # 收到關閉信號
        except asyncio.TimeoutError:
            # 正常超時，執行健康檢查
            if not self._running or self._shutdown_event.is_set():
                break
            await self.check_all_services_health()
```

**經驗教訓**：
1. 使用 `asyncio.Event` 而非簡單的 `sleep` 以支援快速關閉
2. 在執行耗時操作前檢查運行狀態
3. 正確處理 `CancelledError` 以確保優雅關閉

### 6.6 dataclass 與 datetime 結合使用

```python
# ✅ 使用 field(default_factory=...) 設定動態預設值
from dataclasses import dataclass, field
from src.common.datetime_utils import utc_now

@dataclass
class RobotStatus:
    robot_id: str
    connected: bool = False
    updated_at: datetime = field(default_factory=utc_now)  # 動態預設值
```

**原因**：直接使用 `datetime.now()` 作為預設值會導致所有實例共享同一個時間戳。

### 6.7 測試覆蓋增長策略

| 階段 | 測試數 | 增加數 | 說明 |
|------|--------|--------|------|
| Phase 3.1 初期 | 243 | - | 基礎測試 |
| Phase 3.1 完成 | 365 | +122 | 服務協調器、共享狀態等 |

**經驗教訓**：
1. 每個新模組都應有對應的測試套件
2. 測試文件命名應清晰反映測試對象（如 `test_service_coordinator.py`）
3. 使用 mock 隔離外部依賴，提高測試速度和可靠性

---

## 📝 開發流程提醒

1. **新增共用工具**：放在 `src/common/`
2. **環境區分**：使用 `ENV_TYPE=edge` 或 `ENV_TYPE=server`
3. **文檔位置**：規劃放 `docs/plans/`，技術放 `docs/`，開發指南放 `docs/development/`，安全相關放 `docs/security/`
4. **測試與文檔同步**：文檔路徑變更時需同步更新測試
5. **任務完成後**：更新 `PROJECT_MEMORY.md` 記錄經驗教訓
6. **AI 記憶存儲**：`store_memory` 工具只能在 review 模式下使用，一般開發任務請直接更新此文件記錄經驗教訓

---

## 🌐 Phase 3.2 Edge UI 移植經驗教訓

> 📖 **詳細分析**：[phase3/WEBUI_MIGRATION_ANALYSIS.md](phase3/WEBUI_MIGRATION_ANALYSIS.md)

### 7.1 Edge/Cloud 功能隔離原則

```
Edge 功能（本地）              Cloud 功能（雲端）
══════════════════            ══════════════════
✅ 機器人儀表板               ❌ 用戶註冊/密碼重設
✅ 指令控制中心               ❌ 排行榜/成就系統
✅ LLM 設定（本地提供商）     ❌ 進階指令審核/共享
✅ 用戶偏好設定               ❌ 社群功能
✅ 進階指令建立/執行          ❌ 雲端 LLM 服務
```

**經驗教訓**：
1. Edge 功能必須可離線運作，不依賴網路
2. Cloud 功能涉及多用戶數據彙整，不適合本地化
3. 混合功能（如進階指令）需明確區分本地執行與雲端共享

### 7.2 Flask Blueprint 整合模式

```python
# ✅ 使用 Blueprint 擴展現有 Flask Service
from flask import Blueprint

edge_ui = Blueprint(
    'edge_ui',
    __name__,
    template_folder='templates',
    static_folder='static',
    static_url_path='/edge/static'
)

# 在 Flask Adapter 中註冊
if enable_edge_ui:
    from .edge_ui import edge_ui
    app.register_blueprint(edge_ui)
```

**經驗教訓**：
1. Blueprint 允許模組化擴展，保持向後相容
2. `template_folder` 和 `static_folder` 需指向正確的相對路徑
3. `static_url_path` 避免與主應用靜態資源衝突

### 7.3 可配置端點設計

```python
# ❌ 硬編碼端點（不靈活）
ollama_url = 'http://127.0.0.1:11434/api/tags'

# ✅ 透過環境變數配置
OLLAMA_ENDPOINT = os.environ.get('OLLAMA_ENDPOINT', 'http://127.0.0.1:11434')
LMSTUDIO_ENDPOINT = os.environ.get('LMSTUDIO_ENDPOINT', 'http://127.0.0.1:1234')
MCP_API_URL = os.environ.get('MCP_API_URL', 'http://localhost:8000')
```

**經驗教訓**：
1. 所有外部服務端點應可透過環境變數配置
2. 提供合理的預設值以簡化開發環境設定
3. 在文檔中記錄所有可配置的環境變數

### 7.4 前端用戶體驗一致性

```javascript
// ❌ 使用 browser alert（體驗不佳）
alert('操作成功');

// ✅ 使用統一的 Toast 通知
function showToast(message, type = 'success', duration = 3000) {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), duration);
}
showToast('操作成功');
```

**經驗教訓**：
1. 避免使用 `alert()`，改用自定義 Toast 通知
2. 統一通知樣式（success/error/warning/info）
3. 在共用 JS 文件中提供 `showToast` 函式

### 7.5 移植方案選擇

| 方案 | 優點 | 缺點 | 適用場景 |
|------|------|------|----------|
| 純 Electron 前端 | 最低延遲 | 開發工作量大 | 效能優先 |
| 獨立 Flask 服務 | 可重用代碼 | 資源消耗增加 | 快速原型 |
| **混合方案（推薦）** | 最小變更 | 混合路由 | 漸進式移植 |

**經驗教訓**：
1. 優先選擇最小變更原則
2. 擴展現有服務比新建服務更易維護
3. 漸進式移植允許逐步驗證功能

### 7.6 Edge UI 路由結構

| 路由 | 類型 | 說明 |
|------|------|------|
| `/ui` | 頁面 | Edge UI 首頁 |
| `/ui/dashboard` | 頁面 | 機器人儀表板 |
| `/ui/command-center` | 頁面 | 指令控制中心 |
| `/ui/llm-settings` | 頁面 | LLM 設定 |
| `/ui/settings` | 頁面 | 用戶設定 |
| `/api/edge/robots` | API | 機器人管理 |
| `/api/edge/llm/*` | API | LLM 狀態 |
| `/api/edge/settings` | API | 用戶設定 |

**經驗教訓**：
1. UI 頁面使用 `/ui/` 前綴
2. Edge API 使用 `/api/edge/` 前綴，與現有 API 區分
3. 保持路由命名一致性（kebab-case）

### 7.7 異常處理與日誌記錄

```python
# ❌ 靜默捕獲異常（難以除錯）
try:
    detect_service()
except Exception:
    pass

# ✅ 記錄 debug 日誌以便除錯
try:
    detect_service()
except Exception as e:
    logger.debug(f'Failed to detect service at {endpoint}: {e}')
```

**經驗教訓**：
1. 即使是預期的失敗（如服務未啟動），也應記錄 debug 日誌
2. 避免使用空的 `except: pass`，至少記錄錯誤信息
3. 使用 `logger.debug()` 而非 `logger.error()` 以避免正常情況下的日誌噪音

### 7.8 網路連線檢查彈性設計

```python
# ❌ 硬編碼單一端點（某些網路環境可能失敗）
def check_internet():
    urllib.request.urlopen('https://www.google.com', timeout=3)

# ✅ 使用多個備用端點
def check_internet_connection() -> bool:
    check_urls = [
        'https://www.google.com',
        'https://www.cloudflare.com',
        'https://1.1.1.1'
    ]
    for url in check_urls:
        try:
            urllib.request.urlopen(url, timeout=3)
            return True
        except Exception:
            continue
    return False
```

**經驗教訓**：
1. 考慮不同網路環境（中國大陸、企業內網等）
2. 提供多個備用端點以提高可靠性
3. 使用快速失敗策略（短超時）避免阻塞

### 7.9 前端可訪問性（Accessibility）

```javascript
// ❌ 缺少 ARIA 屬性
const toast = document.createElement('div');
toast.textContent = message;

// ✅ 添加 ARIA 屬性提升螢幕閱讀器支援
const toast = document.createElement('div');
toast.textContent = message;
toast.setAttribute('role', 'alert');
toast.setAttribute('aria-live', 'polite');
```

```html
<!-- ❌ 缺少語意化標籤 -->
<nav class="navbar">

<!-- ✅ 添加 aria-label -->
<nav class="navbar" aria-label="主要導航">
```

**經驗教訓**：
1. Toast 通知需添加 `role="alert"` 和 `aria-live="polite"`
2. 導航元素需添加 `aria-label` 描述
3. 遵循 WCAG 可訪問性指南

### 7.10 前端預設值與後端同步

```javascript
// ❌ 前端硬編碼預設值（可能與後端不同步）
body: JSON.stringify({
    duration_unit: 's',
    theme: 'light'
})

// ✅ 從後端 API 取得預設值
const defaultsRes = await fetch('/api/edge/settings/defaults');
const defaultsData = await defaultsRes.json();
body: JSON.stringify(defaultsData.settings)
```

**經驗教訓**：
1. 預設值應由後端統一定義（單一真相來源）
2. 提供 `/api/.../defaults` 端點供前端取得預設值
3. 避免前後端預設值不同步的問題

### 7.11 Electron Token 注入機制

```javascript
// ❌ 假設 Token 存在但未實作
headers: { 
    'Authorization': 'Bearer ???',
    // Token 會由 Electron 注入
}

// ✅ 安全地嘗試取得 Token
const token = (window.electronAPI && typeof window.electronAPI.getToken === 'function') 
    ? await window.electronAPI.getToken() 
    : '';
headers: { 
    'Authorization': token ? `Bearer ${token}` : '',
}
```

**經驗教訓**：
1. 檢查 `electronAPI` 是否存在再使用
2. 提供空字串作為後備值
3. 在文檔中明確說明 Token 注入機制

### 7.12 JSDoc 註解規範

```javascript
// ❌ 簡單註解
/**
 * 通用 API 請求函式
 */

// ✅ 完整 JSDoc 註解
/**
 * 通用 API 請求函式
 * @param {string} endpoint - API 端點路徑
 * @param {Object} options - fetch 選項
 * @returns {Promise<Object>} API 回應資料
 * @throws {Error} 當請求失敗或回應不正常時拋出錯誤
 */
```

**經驗教訓**：
1. 公開 API 函式應有完整的 JSDoc 註解
2. 包含 `@param`、`@returns`、`@throws` 說明
3. 提高代碼可維護性和 IDE 自動完成支援

---

**最後更新**：2025-12-04
