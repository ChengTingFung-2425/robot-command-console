# Phase 3 Lessons

此文件包含 Phase 3 系列開發的詳細經驗教訓。

包含：Phase 3.1, 3.2, 3.3 的服務協調、Edge UI、固件更新、本地指令歷史、統一整合、安全修復等經驗。

## 📚 相關文件

- **[← 返回主記憶](../PROJECT_MEMORY.md)** - Top 15 關鍵經驗
- **[CLI 批次操作](cli_batch_lessons.md)** - 批次執行經驗
- **[TUI + LLM](tui_llm_lessons.md)** - 互動介面經驗
- **[安全性](security_lessons.md)** - Token 輪替、認證
- **[代碼品質](code_quality_lessons.md)** - Code Review 經驗

---

## 🚀 Phase 3.2: Tiny 版本開發經驗（2025-12-10）

### 雙版本策略實作

**決策**：建立 PyQt+QtWebView 輕量版本（Tiny）與 Electron 版本（Heavy）並行發布

**實作重點**：
- ✅ 使用 PyQt6 + QtWebEngine 建立輕量桌面應用
- ✅ Flask 服務管理器：自動尋找可用埠、健康檢查、自動重啟
- ✅ QWebChannel 橋接：JS-Python 通訊，提供原生功能
- ✅ 跨平台打包：PyInstaller 配置（Windows/macOS/Linux）

**技術選型**：
```python
# 選擇 PyQt6 而非 PySide6
# 原因：更成熟的社群、更完整的文檔、GPL 授權可接受

# 選擇 QtWebEngineView 而非 QWebView
# 原因：Qt6 官方推薦、支援現代 Web 標準

# 選擇 PyInstaller 而非 Nuitka/cx_Freeze
# 原因：跨平台支援完整、社群活躍
```

**目錄結構設計**：
```
qtwebview-app/
├── main.py              # 主程式入口
├── flask_manager.py     # Flask 服務管理（含健康檢查）
├── webview_window.py    # WebView 視窗
├── bridge.py            # JS-Python 橋接
├── system_tray.py       # 系統托盤
└── build/               # 打包配置（3 個平台）
```

**健康檢查機制**：
```python
# 每 5 秒檢查一次 Flask 服務
# 失敗時自動重啟（最多 3 次）
# 使用獨立執行緒避免阻塞 UI
```

**重要經驗**：
1. **埠號管理**：動態尋找可用埠而非固定埠號
2. **進程管理**：使用 `subprocess.Popen` 管理 Flask，確保正確終止
3. **.gitignore 衝突**：build/ 目錄預設被忽略，需使用 `-f` 強制加入配置檔案
4. **Import 錯誤**：模組名稱不能包含連字號（`qtwebview-app`），需特殊處理

**文件結構**：
- 規劃文件：18KB 詳細實作指引（`PHASE3_2_QTWEBVIEW_PLAN.md`）
- 使用者指引：版本選擇、安裝指引
- 架構文件：加入 Tiny 版本說明

**下一步**：
- Flask Blueprint 調整（靜態資源本地化）
- 實際測試與驗證
- 完善打包腳本

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

### 7.13 共用函式統一化

```javascript
// ❌ 在每個頁面重複定義相同函式
// dashboard.html
function showToast(message, type) { ... }

// llm_settings.html
function showToast(message, type) { ... }

// ✅ 統一使用共用模組
// 使用 edge-common.js 中定義的 window.EdgeUI.showToast
window.EdgeUI.showToast('操作成功', 'success');
```

**經驗教訓**：
1. 通用函式應定義在共用 JS 檔案（如 `edge-common.js`）
2. 透過 `window.EdgeUI.showToast()` 等命名空間存取
3. 避免在多個頁面重複定義相同函式
4. 保持程式碼 DRY（Don't Repeat Yourself）原則

---

## 🔧 Phase 3.2 固件更新功能經驗教訓

### 8.1 模型常數定義

```python
# ✅ 將預設值定義為模組常數
DEFAULT_FIRMWARE_VERSION = '1.0.0'

class Robot(db.Model):
    firmware_version = db.Column(
        db.String(32),
        default=DEFAULT_FIRMWARE_VERSION
    )
```

**經驗教訓**：
1. 預設值應定義為常數，避免硬編碼在多處
2. 常數放在模組頂部方便引用
3. 模板也應使用傳入的常數而非硬編碼

### 8.2 固件版本比較函式

```python
def _compare_versions(v1: str, v2: str) -> int:
    """比較兩個版本號（x.y.z 格式）"""
    try:
        parts1 = [int(x) for x in v1.split('.')]
        parts2 = [int(x) for x in v2.split('.')]
        # 補齊長度不足的版本
        while len(parts1) < len(parts2):
            parts1.append(0)
        # ...
    except (ValueError, AttributeError):
        return 0  # 解析失敗返回相等
```

**經驗教訓**：
1. 版本比較需處理不同長度的版本號（如 1.0 vs 1.0.0）
2. 需要優雅處理無效格式，避免拋出異常
3. 返回 -1/0/1 符合標準比較函式慣例

### 8.3 固件更新路由設計

| 路由 | 類型 | 說明 |
|------|------|------|
| `/firmware` | 頁面 | 固件更新管理頁面 |
| `/api/firmware/versions` | API | 查詢可用固件版本 |
| `/api/firmware/check/<robot_id>` | API | 檢查機器人固件狀態 |
| `/api/firmware/update` | API | 啟動固件更新 |
| `/api/firmware/status/<update_id>` | API | 查詢更新狀態 |
| `/api/firmware/history/<robot_id>` | API | 查詢更新歷史 |
| `/api/firmware/cancel/<update_id>` | API | 取消更新 |

**經驗教訓**：
1. 頁面路由使用簡潔路徑（`/firmware`）
2. API 路由使用 `/api/` 前綴統一管理
3. 資源 ID 放在路徑中（如 `<robot_id>`），篩選參數用 query string

### 8.4 固件更新狀態機

```
pending → downloading → installing → completed
    ↓          ↓            ↓
cancelled   failed       failed
```

**經驗教訓**：
1. 定義明確的狀態轉換規則
2. 終態（completed/failed/cancelled）不可再變更
3. 只有進行中的更新可以取消

---

## 🗄️ Phase 3.2: 本地指令歷史與快取實作（2025-12-10）

### 功能實作總結

**目標**：為 Edge 環境實作本地指令歷史記錄與快取功能，支援離線使用與效能優化。

**實作模組**：
1. **CommandHistoryStore** (`src/common/command_history.py`)
2. **CommandCache** (`src/common/command_cache.py`)
3. **CommandResultCache** (`src/common/command_cache.py`)
4. **CommandHistoryManager** (`src/robot_service/command_history_manager.py`)
5. **History API** (`src/robot_service/history_api.py`)

**測試覆蓋**：57 個測試，100% 通過率

---

### 9.1 SQLite 索引設計

```python
# ✅ 為常用查詢欄位建立索引
CREATE INDEX IF NOT EXISTS idx_command_history_trace_id ON command_history(trace_id)
CREATE INDEX IF NOT EXISTS idx_command_history_robot_id ON command_history(robot_id)
CREATE INDEX IF NOT EXISTS idx_command_history_status ON command_history(status)
CREATE INDEX IF NOT EXISTS idx_command_history_created_at ON command_history(created_at)
CREATE INDEX IF NOT EXISTS idx_command_history_command_id ON command_history(command_id)
```

**經驗教訓**：
1. **主鍵索引**：command_id 作為主鍵自動建立索引
2. **外鍵索引**：trace_id 雖非外鍵但查詢頻繁，需建立索引
3. **查詢優化**：為所有 WHERE 子句中常用的欄位建立索引
4. **時間範圍查詢**：created_at 索引支援時間範圍篩選

---

### 9.2 查詢方法設計模式

```python
# ❌ 效率低下的查詢方式
def get_by_trace_id(trace_id):
    records = query_records(limit=1)  # 只查 1 筆
    for r in records:
        if r.trace_id == trace_id:
            return r
    return None

# ✅ 正確的查詢方式
def get_by_trace_id(self, trace_id: str) -> Optional[CommandRecord]:
    cursor.execute('''
        SELECT * FROM command_history WHERE trace_id = ? LIMIT 1
    ''', (trace_id,))
    return cursor.fetchone()
```

**經驗教訓**：
1. 直接使用 SQL WHERE 子句篩選，而非先查詢再在 Python 中過濾
2. 為常用查詢模式建立專門方法（如 `get_by_trace_id`）
3. 使用 `LIMIT 1` 優化單筆查詢

---

### 9.3 LRU 快取實作

```python
# ✅ 使用 OrderedDict 實作 LRU
from collections import OrderedDict

class CommandCache:
    def __init__(self, max_size: int):
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.max_size = max_size
    
    def get(self, key: str):
        if key in self._cache:
            # 移到最後（標記為最近使用）
            self._cache.move_to_end(key)
            return self._cache[key].value
    
    def set(self, key: str, value: Any):
        if len(self._cache) >= self.max_size:
            # 移除最舊的項目（第一個）
            self._cache.popitem(last=False)
        self._cache[key] = CacheEntry(key, value)
```

**經驗教訓**：
1. **OrderedDict**：Python 內建的有序字典非常適合實作 LRU
2. **move_to_end()**：更新存取順序的高效方法
3. **popitem(last=False)**：移除最舊項目（FIFO 方式）
4. **執行緒安全**：使用 `threading.RLock()` 保護操作

---

### 9.4 TTL 過期機制設計

```python
@dataclass
class CacheEntry:
    key: str
    value: Any
    created_at: datetime = field(default_factory=utc_now)
    expires_at: Optional[datetime] = None
    
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return utc_now() >= self.expires_at

# 設定 TTL
def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None):
    if ttl_seconds is None:
        ttl_seconds = self.default_ttl_seconds
    
    expires_at = None
    if ttl_seconds > 0:
        expires_at = utc_now() + timedelta(seconds=ttl_seconds)
    
    entry = CacheEntry(key=key, value=value, expires_at=expires_at)
    self._cache[key] = entry
```

**經驗教訓**：
1. **可選過期**：`expires_at=None` 表示永不過期
2. **TTL=0**：特殊值表示永不過期，與預設 TTL 區分
3. **惰性清理**：在 get() 時檢查過期，而非主動定期掃描
4. **主動清理**：提供 `cleanup_expired()` 方法供定期呼叫

---

### 9.5 統一管理介面設計

```python
# ✅ 整合歷史與快取的統一介面
class CommandHistoryManager:
    def __init__(self, history_db_path, cache_max_size, cache_ttl):
        self.history_store = CommandHistoryStore(db_path=history_db_path)
        self.result_cache = CommandResultCache(
            max_size=cache_max_size,
            default_ttl_seconds=cache_ttl
        )
    
    def get_command_result(self, command_id, use_cache=True):
        # 優先從快取取得
        if use_cache:
            cached = self.result_cache.get(command_id)
            if cached is not None:
                return cached
        
        # 快取未命中，從歷史取得
        record = self.history_store.get_record(command_id)
        if record and record.result:
            # 自動加入快取
            if use_cache:
                self.cache_command_result(command_id, record.trace_id, record.result)
            return record.result
        
        return None
```

**經驗教訓**：
1. **統一介面**：隱藏底層實作細節，提供簡潔 API
2. **智能快取**：從資料庫查詢時自動加入快取
3. **可選快取**：提供 `use_cache` 參數允許繞過快取
4. **自動同步**：更新狀態時自動更新快取

---

### 9.6 Flask Blueprint 設計模式

```python
# ✅ 使用工廠函式建立 Blueprint
def create_history_api_blueprint(
    history_manager: CommandHistoryManager,
    url_prefix: str = '/api/commands'
) -> Blueprint:
    bp = Blueprint('command_history_api', __name__, url_prefix=url_prefix)
    
    @bp.route('/history', methods=['GET'])
    def get_command_history():
        # 使用閉包存取 history_manager
        records = history_manager.get_command_history(...)
        return jsonify({'status': 'success', 'data': records})
    
    return bp

# 使用
app = Flask(__name__)
manager = CommandHistoryManager()
history_bp = create_history_api_blueprint(manager)
app.register_blueprint(history_bp)
```

**經驗教訓**：
1. **工廠模式**：使用工廠函式而非直接建立 Blueprint
2. **依賴注入**：透過參數傳入依賴（如 history_manager）
3. **閉包**：Blueprint 內的路由函式可存取外層變數
4. **靈活配置**：url_prefix 可自訂，方便整合

---

### 9.7 分頁查詢最佳實踐

```python
# ✅ 完整的分頁查詢回應
@bp.route('/history', methods=['GET'])
def get_command_history():
    limit = request.args.get('limit', 100, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    # 查詢資料
    records = history_manager.get_command_history(
        limit=min(limit, 1000),  # 限制最大值
        offset=max(offset, 0)     # 防止負數
    )
    
    # 統計總數
    total = history_manager.count_commands()
    
    return jsonify({
        'status': 'success',
        'data': {
            'records': [r.to_dict() for r in records],
            'pagination': {
                'total': total,
                'limit': limit,
                'offset': offset,
                'has_more': (offset + len(records)) < total
            }
        }
    })
```

**經驗教訓**：
1. **limit 上限**：防止過大的 limit 值影響效能
2. **offset 下限**：防止負數 offset
3. **分頁資訊**：提供 total、has_more 等資訊方便前端
4. **獨立計數**：使用專門的 count 查詢，避免查詢所有資料

---

### 9.8 測試資料清理策略

```python
# ✅ 使用 fixture 管理測試資源
@pytest.fixture
def temp_db():
    """建立臨時資料庫"""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    yield path
    # 測試結束後自動清理
    if os.path.exists(path):
        os.unlink(path)

@pytest.fixture
def manager(temp_db):
    """建立測試用的 Manager"""
    return CommandHistoryManager(history_db_path=temp_db)
```

**經驗教訓**：
1. **臨時檔案**：使用 `tempfile.mkstemp()` 建立臨時資料庫
2. **自動清理**：使用 `yield` 確保測試後清理資源
3. **fixture 鏈**：manager fixture 依賴 temp_db fixture
4. **隔離性**：每個測試使用獨立的資料庫，避免相互影響

---

### 9.9 dataclass 與 JSON 序列化

```python
@dataclass
class CommandRecord:
    command_id: str
    created_at: datetime
    command_params: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        data = asdict(self)
        # 手動處理 datetime 序列化
        if isinstance(data.get('created_at'), datetime):
            data['created_at'] = data['created_at'].isoformat()
        # 手動處理巢狀字典（已是 dict 不需處理）
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CommandRecord':
        """從字典建立實例"""
        # 手動處理 datetime 反序列化
        if isinstance(data.get('created_at'), str):
            data['created_at'] = parse_iso_datetime(data['created_at'])
        return cls(**data)
```

**經驗教訓**：
1. **asdict() 限制**：無法自動處理 datetime、自訂類型
2. **手動序列化**：需要明確轉換 datetime 為 ISO 字串
3. **類型檢查**：使用 isinstance() 判斷是否需要轉換
4. **對稱處理**：to_dict 和 from_dict 應對稱處理所有欄位

---

### 9.10 Code Review 回饋整合

**問題 1**：查詢效率低下

```python
# ❌ Code Review 前
def get_command_by_id(command_id):
    records = get_command_history(limit=1)  # 只查最新一筆
    for r in records:
        if r.command_id == command_id:
            return r

# ✅ Code Review 後
def get_command_by_id(command_id):
    return history_store.get_record(command_id)  # 直接查詢
```

**問題 2**：缺少索引

```python
# ✅ 為 trace_id 加入索引
CREATE INDEX IF NOT EXISTS idx_command_history_trace_id 
ON command_history(trace_id)
```

**問題 3**：查詢方法不足

```python
# ✅ 新增專門的查詢方法
def get_by_trace_id(self, trace_id: str) -> Optional[CommandRecord]:
    cursor.execute('''
        SELECT * FROM command_history WHERE trace_id = ? LIMIT 1
    ''', (trace_id,))
    return self._row_to_record(cursor.fetchone())
```

**經驗教訓**：
1. **即時修復**：Code Review 發現問題應立即修復
2. **根本解決**：不只修復表面問題，還要優化底層設計
3. **完善測試**：修復後運行測試確保功能正常
4. **文件更新**：重要變更應更新功能文件
## 🌐 Phase 3.3 統一整合與雲端分離經驗教訓（2025-12-10）

### 9.1 XSS 防護：模板自動跳脫

```jinja2
{# ❌ 直接輸出用戶內容（XSS 漏洞） #}
{{ post.body }}
{{ user.username }}

{# ✅ 使用 |e 過濾器自動跳脫 HTML #}
{{ post.body|e }}
{{ user.username|e }}
```

**經驗教訓**：
1. 所有用戶可控的內容必須經過 HTML 跳脫
2. `.html.j2` 模板預設不啟用自動跳脫，需手動加上 `|e`
3. 特別注意：username、post body、comments 等都可能含有惡意 HTML/JS
4. 使用 `bleach` 套件清理允許的 HTML 標籤更安全

### 9.2 Cloud 服務架構分離模式

```python
# ❌ Cloud 服務直接依賴 WebUI
from WebUI.app import db
from WebUI.app.models import User

# ✅ Cloud 服務獨立實作
# Cloud/models.py - 獨立資料模型
# Cloud/database.py - 獨立資料庫連接
# 函式設計為接受參數而非直接導入
def send_email(app, mail, subject, recipients, body):
    with app.app_context():
        mail.send(...)
```

**經驗教訓**：
1. 分離的服務必須完全獨立，不能依賴原始服務的內部實作
2. 過渡期可標記函式為 `NotImplementedError`，避免誤用
3. 移動到 Cloud 的模板需更新路由（如 `url_for('cloud.user_profile')`）
4. 完整分離需要：獨立模型、獨立資料庫、獨立 API

### 9.3 非同步健康檢查避免阻塞

```python
# ❌ 在 async 函式中使用同步 IO（阻塞事件循環）
async def health_check(url):
    response = urllib.request.urlopen(url, timeout=3)
    return response.status == 200

# ✅ 使用 asyncio.to_thread 包裝同步 IO
async def health_check(url):
    response = await asyncio.to_thread(
        urllib.request.urlopen, url, timeout=3
    )
    return response.status == 200
```

**經驗教訓**：
1. 避免在 `async` 函式中直接使用同步 IO
2. 使用 `asyncio.to_thread()` 將同步呼叫移到執行緒池
3. 或使用 `aiohttp` 等真正的非同步 HTTP 函式庫
4. 阻塞的健康檢查會影響整個服務效能

### 9.4 Subprocess Pipe Buffer 管理

```python
# ❌ PIPE 未讀取導致子進程阻塞
process = subprocess.Popen(
    cmd,
    stdout=subprocess.PIPE,  # Buffer 會填滿
    stderr=subprocess.PIPE
)

# ✅ 使用 DEVNULL 或持續讀取
process = subprocess.Popen(
    cmd,
    stdout=subprocess.DEVNULL,  # 不需要輸出時使用
    stderr=subprocess.DEVNULL
)
```

**經驗教訓**：
1. `subprocess.PIPE` 有固定大小的緩衝區
2. 長時間運行的進程若不讀取輸出，緩衝區會填滿導致阻塞
3. 選擇 1: 使用 `subprocess.DEVNULL` 丟棄輸出
4. 選擇 2: 實作背景執行緒持續讀取並記錄
5. 選擇 3: 將輸出重定向到檔案

### 9.5 Electron 後端服務偵測

```javascript
// ❌ 依賴中文字串匹配（不可靠）
if (data.includes('所有後端服務已就緒')) {
    // 編碼問題、格式變更都會破壞此機制
}

// ✅ 使用 HTTP 健康檢查
async function waitForBackend() {
    for (let i = 0; i < 30; i++) {
        try {
            const response = await fetch('http://127.0.0.1:5000/health');
            if (response.ok) return true;
        } catch (e) {
            await sleep(1000);
        }
    }
    return false;
}
```

**經驗教訓**：
1. 不要依賴日誌訊息的字串匹配來判斷服務狀態
2. 使用專門的健康檢查端點更可靠
3. 實作重試機制（如最多 30 秒）
4. HTTP 健康檢查與語言、編碼無關

### 9.6 NotImplementedError 標記待重構程式碼

```python
# ✅ 明確標記待重構的函式
def award_points(user_id: int, reason: str, amount: Optional[int] = None):
    """
    Award points to a user for a specific action.
    
    ⚠️ 尚未重構，待 Cloud 服務資料模型與資料庫完成後實作。
    """
    raise NotImplementedError("待 Cloud 服務重構完成")
```

**經驗教訓**：
1. 移動到新模組但尚未完成的程式碼應拋出 `NotImplementedError`
2. 在 docstring 中說明為何尚未實作及何時會完成
3. 避免保留無法運作的程式碼誤導使用者
4. 過渡期的明確錯誤訊息比靜默失敗好

### 9.7 統一套件設計模式

```
unified-edge-app/
├── core/
│   ├── launcher.py      # 統一啟動器
│   ├── config.py        # 配置管理（YAML + 環境變數）
│   └── service_manager.py  # 服務協調
├── README.md
├── requirements.txt
└── config.example.yaml
```

**經驗教訓**：
1. 將多個服務整合為單一套件，簡化部署
2. 提供統一的配置檔案格式（YAML）
3. 支援環境變數覆寫以適應不同環境
4. 一鍵啟動腳本降低使用門檻
5. 完整的 README 說明安裝、配置、使用

### 9.8 Edge/Cloud 職責分離原則

| 層級 | 職責 | 特性 |
|------|------|------|
| **Edge** | 本地機器人控制 | 離線可用、低延遲、隱私保護 |
| **Cloud** | 社群功能、資料分析 | 需網路、多用戶、集中管理 |

**經驗教訓**：
1. Edge 功能必須完全離線可用
2. Cloud 功能移除後，Edge App 體積減小 25%
3. 清晰的職責分離使系統更易維護
4. 用戶可選擇性啟用 Cloud 服務

### 9.9 程式碼審查流程自動化

**PR 審查檢查清單**：
- ✅ 移除未使用的導入
- ✅ 修正非同步阻塞問題
- ✅ 處理 subprocess pipe buffer
- ✅ XSS 防護（模板跳脫）
- ✅ 依賴隔離檢查
- ✅ 錯誤處理完整性

**經驗教訓**：
1. 使用自動化工具檢查常見問題（如 flake8）
2. PR 審查機器人可及早發現問題
3. 建立檢查清單確保品質一致
4. 及時修正審查意見避免技術債累積

### 9.10 模板路由更新模式

```jinja2
{# ❌ 舊路由（移動前） #}
{{ url_for('user', username=...) }}
{{ url_for('webui.leaderboard', ...) }}

{# ✅ 新路由（移動後） #}
{{ url_for('cloud.user_profile', username=...) }}
{{ url_for('cloud.leaderboard', ...) }}
```

**經驗教訓**：
1. 模板移動到新模組時，所有 `url_for` 都需更新
2. 使用全域搜尋確保沒有遺漏的路由
3. 測試所有頁面連結確保無 404 錯誤
4. 考慮提供重定向以保持向後相容（過渡期）

---

## 🔍 Phase 3.2: Code Review 與 CodeQL 安全修復（2025-12-10）

### PR Review 回饋處理經驗

**背景**：本地指令歷史與快取功能實作完成後，收到自動化 Code Review 的 16 個建議，並發現 CodeQL 的資訊暴露安全問題。

### 11.1 冗餘索引識別

```python
# ❌ 不必要的索引（PRIMARY KEY 已自動建立）
cursor.execute('''
    CREATE INDEX IF NOT EXISTS idx_command_history_command_id 
    ON command_history(command_id)
''')

# ✅ 移除冗餘索引
# PRIMARY KEY 自動建立 B-tree 索引，無需額外索引
```

**經驗教訓**：
1. SQLite 為 PRIMARY KEY 自動建立索引
2. 冗餘索引不會造成錯誤（IF NOT EXISTS），但增加維護成本
3. 定期審查索引設計，移除不必要的索引

---

### 11.2 快取執行緒安全問題

```python
# ❌ 執行緒不安全（兩次鎖定間隔可能導致不一致）
def get_by_trace_id(self, trace_id: str):
    with self._lock:
        command_id = self._trace_to_command.get(trace_id)
        if command_id is None:
            return None
        return self.get(command_id)  # 離開鎖定後再次取得鎖

# ✅ 在鎖定區域內處理快取失效
def get_by_trace_id(self, trace_id: str):
    with self._lock:
        command_id = self._trace_to_command.get(trace_id)
        if command_id is None:
            return None
        result = self.get(command_id)
        if result is None:
            # 快取已過期或被淘汰，清理 trace_id 映射
            del self._trace_to_command[trace_id]
        return result
```

**經驗教訓**：
1. 多次鎖定/解鎖之間存在競態條件窗口
2. 相關操作應在同一鎖定區域內完成
3. 快取失效時需同步清理所有相關映射

---

### 11.3 快取淘汰時的映射同步

```python
# ❌ 子類未覆寫父類方法，導致映射不同步
class CommandResultCache(CommandCache):
    def __init__(self):
        self._trace_to_command: Dict[str, str] = {}
    # 缺少 _remove_entry() 覆寫

# ✅ 覆寫 _remove_entry() 確保映射同步
class CommandResultCache(CommandCache):
    def _remove_entry(self, key: str):
        """移除快取項目時，同步清理 trace_id 對應"""
        # 找出所有 trace_id 對應此 command_id
        to_remove = [tid for tid, cid in self._trace_to_command.items() if cid == key]
        for tid in to_remove:
            del self._trace_to_command[tid]
        super()._remove_entry(key)
```

**經驗教訓**：
1. 子類維護額外狀態時，必須覆寫所有相關方法
2. LRU 淘汰、過期清理、手動刪除都會呼叫 `_remove_entry()`
3. 映射不同步會導致記憶體洩漏和邏輯錯誤

---

### 11.4 OrderedDict 與 LRU 語義

```python
# ❌ 直接覆寫會破壞 LRU 順序
def set(self, key, value):
    self._cache[key] = entry  # OrderedDict 保持原位置

# ✅ 先刪除再新增以移到最後
def set(self, key, value):
    # 如果鍵已存在，先移除以確保新增時會移到最後（維持 LRU 語義）
    # 不能直接覆寫，因為 OrderedDict 會保持原有位置
    if key in self._cache:
        del self._cache[key]
    # 新增會自動加到最後
    self._cache[key] = entry
```

**經驗教訓**：
1. OrderedDict 的 `[]` 賦值不會改變項目位置
2. 必須先刪除再新增才能移到最後
3. 註解應說明這個非顯而易見的行為

---

### 11.5 API 參數驗證

```python
# ❌ 靜默失敗（無效參數被忽略）
start_time_str = request.args.get('start_time')
if start_time_str:
    start_time = parse_iso_datetime(start_time_str)  # 可能返回 None

# ✅ 明確驗證並回傳錯誤
start_time_str = request.args.get('start_time')
if start_time_str:
    start_time = parse_iso_datetime(start_time_str)
    if start_time is None:
        return jsonify({
            'status': 'error',
            'error': {
                'code': 'INVALID_PARAMETER',
                'message': 'Invalid start_time format'
            }
        }), 400
```

**經驗教訓**：
1. API 應明確驗證所有輸入參數
2. 無效參數應回傳 4xx 錯誤，而非靜默忽略
3. 錯誤訊息應清楚指出哪個參數有問題

---

### 11.6 CodeQL 資訊暴露修復

```python
# ❌ 直接暴露異常訊息（可能包含敏感資訊）
except Exception as e:
    return jsonify({
        'status': 'error',
        'error': {
            'code': 'QUERY_ERROR',
            'message': str(e)  # 可能暴露檔案路徑、SQL 語句等
        }
    }), 500

# ✅ 使用通用錯誤訊息，詳細資訊僅記錄
except Exception as e:
    logger.error(f"Error getting command history: {e}", exc_info=True)
    return jsonify({
        'status': 'error',
        'error': {
            'code': 'QUERY_ERROR',
            'message': 'An internal error has occurred.'
        }
    }), 500
```

**經驗教訓**：
1. **永遠不要**在 API 回應中包含 `str(e)` 或異常詳情
2. 異常可能包含：檔案路徑、SQL 語句、資料庫結構、內部邏輯
3. 使用通用錯誤訊息，詳細資訊僅記錄到 logger
4. CodeQL 會檢測這類資訊暴露問題（Medium 級別）

**修復範圍**：
- `history_api.py`：6 處 `str(e)` 替換為通用訊息
- 所有 API 端點統一錯誤處理模式
- 確保 logger 有 `exc_info=True` 以記錄完整堆疊

---

### 11.7 迴圈變數作用域陷阱

```python
# ❌ 使用外層迴圈變數（變數作用域錯誤）
for i in range(5):
    record = create_record(f'cmd-{i}')
    offline_commands.append(record)

for record in offline_commands:  # 沒有定義新的 i
    update_status(record.id, execution_time=1000 + i * 100)  # 使用最後的 i=4

# ✅ 在內層迴圈中定義新的迴圈變數
for i, record in enumerate(offline_commands):
    update_status(record.id, execution_time=1000 + i * 100)
```

**經驗教訓**：
1. Python 的迴圈變數會洩漏到外層作用域
2. 巢狀迴圈時要特別注意變數名稱
3. 使用 `enumerate()` 明確綁定索引與元素

---

### 11.8 測試中的未使用變數

```python
# ❌ 變數賦值後未使用
def test_init_db(self, temp_db):
    store = CommandHistoryStore(db_path=temp_db)  # 未使用
    assert os.path.exists(temp_db)

# ✅ 使用底線表示故意不使用
def test_init_db(self, temp_db):
    _ = CommandHistoryStore(db_path=temp_db)
    assert os.path.exists(temp_db)

# ✅ 或直接移除賦值
def test_count_commands(self, manager):
    for i in range(10):
        manager.record_command(command_id=f'cmd-{i}')  # 不需要接收回傳值
```

**經驗教訓**：
1. Linter 會標記未使用的變數
2. 使用 `_` 表示故意不使用的回傳值
3. 測試中如果只是觸發副作用，可不接收回傳值

---

### 11.9 Import 清理

```python
# ❌ 匯入但未使用
from datetime import datetime, timedelta, timezone

# ✅ 只匯入需要的
from datetime import datetime, timedelta
```

**經驗教訓**：
1. 定期清理未使用的 import
2. IDE/編輯器通常會灰色標示未使用的 import
3. Flake8 的 F401 會檢測未使用的 import

---

### 11.10 分頁查詢一致性

```python
# ❌ 查詢與計數的篩選條件不一致
records = get_command_history(
    robot_id=robot_id,
    status=status,
    actor_type=actor_type,  # 有此條件
    source=source            # 有此條件
)
total = count_commands(
    robot_id=robot_id,
    status=status
    # 缺少 actor_type 和 source
)

# ✅ 保持篩選條件一致
total = count_commands(
    robot_id=robot_id,
    status=status,
    actor_type=actor_type,
    source=source
)
```

**經驗教訓**：
1. 分頁查詢的 `total` 必須使用相同篩選條件
2. 不一致會導致 `has_more` 判斷錯誤
3. Code Review 可發現這類邏輯錯誤

---

### 11.11 自動化 Code Review 價值

**本次 PR Review 發現的問題類型**：

| 類型 | 數量 | 嚴重性 |
|------|------|--------|
| 執行緒安全 | 2 | High |
| 記憶體洩漏 | 1 | High |
| 邏輯錯誤 | 2 | Medium |
| 參數驗證 | 1 | Medium |
| 程式碼清理 | 10 | Low |

**經驗教訓**：
1. 自動化 Review 能發現人工容易忽略的問題
2. 即使測試通過，仍可能有邏輯或效能問題
3. 執行緒安全和記憶體管理是容易遺漏的重點
4. 應在開發階段就考慮這些問題，而非等 Review

---

### 11.12 完整的錯誤處理模式

**API 錯誤處理最佳實踐**：

```python
@bp.route('/api/resource', methods=['POST'])
def api_endpoint():
    try:
        # 1. 參數驗證
        param = request.args.get('param')
        if param and not validate(param):
            return jsonify({
                'status': 'error',
                'error': {
                    'code': 'INVALID_PARAMETER',
                    'message': 'Invalid param format'
                }
            }), 400
        
        # 2. 業務邏輯
        result = process(param)
        
        # 3. 成功回應
        return jsonify({
            'status': 'success',
            'data': result
        })
    
    except Exception as e:
        # 4. 記錄詳細錯誤（含堆疊）
        logger.error(f"Error in api_endpoint: {e}", exc_info=True)
        
        # 5. 回傳通用錯誤訊息
        return jsonify({
            'status': 'error',
            'error': {
                'code': 'INTERNAL_ERROR',
                'message': 'An internal error has occurred.'
            }
        }), 500
```

**關鍵原則**：
- ✅ 驗證在前，業務邏輯在後
- ✅ 4xx 用於客戶端錯誤（參數問題）
- ✅ 5xx 用於伺服器錯誤（內部問題）
- ✅ 詳細錯誤僅記錄到 logger
- ✅ 回應使用通用錯誤訊息
- ✅ 統一的錯誤格式

---

---

