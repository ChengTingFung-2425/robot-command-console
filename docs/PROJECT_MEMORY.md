# 專案記憶

> **用途**：此文件專門用於存儲 AI 助手（如 GitHub Copilot）在開發過程中學習到的經驗教訓、最佳實踐和重要發現。
>
> **使用方式**：
> - AI 助手在每次任務完成後應更新此文件，記錄新的經驗教訓
> - 開發者可參考此文件了解過去遇到的問題和解決方案
> - 此文件不應包含架構設計、規劃或功能說明（這些請放在其他專門文件中）
>
> **⚠️ 重要提醒**：
> - **`store_memory` 工具僅能在 review 模式下使用**
> - 在 agent 模式下，請直接編輯本文件（PROJECT_MEMORY.md）來記錄經驗
> - 遵循本文件既有的格式結構：
>   - 新增至「關鍵經驗精華」章節（標註使用頻率 ⭐）
>   - 或新增至「詳細經驗索引」對應的專題文件
>   - 更新「最近更新」章節記錄變更
>
> 📖 **其他文件**：[architecture.md](architecture.md)、[plans/](plans/)、[development/](development/), [memory/](memory/)

---

## ⚠️ 常見錯誤提醒（AI 助手必讀）

### 🔒 路徑穿越（Path Traversal）修復模式

**`startswith` 路徑檢查存在繞過漏洞，禁止使用：**

```python
# ❌ 危險：/tmp/storage_evil 會通過此檢查（startswith 繞過）
if not str(path.resolve()).startswith(str(base.resolve())):
    raise ValueError("Path traversal detected")

# ✅ 首選：werkzeug.safe_join（專案已有 Werkzeug 依賴）
from werkzeug.utils import safe_join
safe_path = safe_join(str(base_dir), user_input)
if safe_path is None:          # None 表示路徑穿越被攔截
    raise ValueError("Path traversal detected")
file_path = Path(safe_path)   # 確認安全後再轉成 Path

# ✅ 備選：Python 3.9+ is_relative_to（stdlib，無額外依賴）
if not path.resolve().is_relative_to(base.resolve()):
    raise ValueError("Path traversal detected")
```

**為何 `startswith` 不安全**：
- `base = /tmp/storage`，攻擊者輸入使路徑變成 `/tmp/storage_evil`
- `/tmp/storage_evil` 確實以 `/tmp/storage` **開頭**，`startswith` 會放行
- `safe_join` 和 `is_relative_to` 均不受此繞過影響

**`werkzeug.safe_join` 的優勢**：
- 路徑建構與安全驗證一次完成，程式碼更簡潔
- 同時防禦：`../` 穿越、絕對路徑注入、`startswith` 繞過
- 專案已依賴 Werkzeug（Flask 生態系標準），無需新增依賴
- 返回 `None` 語意明確，不需 try/except

**修復記錄（2026-02-24）**：
- `Cloud/api/storage.py` L76–L84：`upload_file()` 路徑建構改用 `safe_join`
- `Edge/qtwebview-app/routes_firmware_tiny.py` L653–L660：`robot_variables()` 路徑檢查改用 `safe_join`

### 🔍 Linting 錯誤（最常見）

**在每次代碼變更後，務必執行 linting 檢查**：

```bash
# 檢查 src/ 和 MCP/ 目錄（E/F/W 級別）
python3 -m flake8 src/ MCP/ --select=E,F,W --exclude=.venv,node_modules,__pycache__ --max-line-length=120
```

**常見 Linting 問題**：

1. **W293: 空白行含空格**
   - 最常見的錯誤，幾乎每次都會出現
   - 批次修正：`find src/ MCP/ -name "*.py" -exec sed -i 's/[[:space:]]*$//' {} \;`

2. **F401: 未使用的導入**
   - 導入了模組但未在代碼中使用
   - 特別注意：僅在註解或字串中提到的類型名稱不算使用

3. **E226: 運算符周圍缺少空格**
   - `i+1` 應寫為 `i + 1`
   - `"="*60` 應寫為 `"=" * 60`

4. **型別提示錯誤**
   - 使用小寫 `any` 而非 `typing.Any`
   - 使用 `Any` 而非具體類型（降低型別安全性）

**最佳實踐**：
- ✅ **提交前檢查**：每次代碼變更後立即運行 flake8
- ✅ **分級修正**：優先修正 E/F 級別，再處理 W 級別
- ✅ **自動化工具**：使用 sed 批次處理格式問題
- ✅ **持續驗證**：修正後運行測試確保無破壞

### 📝 其他常見錯誤

1. **測試驗證不足**
   - 修改代碼後務必運行相關測試
   - 確保 100% 測試通過率

2. **型別安全性降低**
   - 避免使用 `Any` 作為型別提示
   - 優先使用具體的型別（如 `BatchOptions`）

3. **重複計數邏輯**
   - 狀態更新時檢查舊狀態
   - 避免終止狀態間轉換時重複計數

---

## 📋 相關文件索引

| 類別 | 文件 |
|------|------|
| **架構** | [architecture.md](architecture.md) |
| **規劃** | [plans/MASTER_PLAN.md](plans/MASTER_PLAN.md) |
| **開發指南** | [development/](development/) |
| **安全文件** | [security/TOKEN_SECURITY.md](security/TOKEN_SECURITY.md) |
| **使用者指引** | [user_guide/USER_GUIDE_INDEX.md](user_guide/USER_GUIDE_INDEX.md) |
| **詳細經驗** | [memory/](memory/)（Phase 3, CLI, TUI, 安全性等） |
| **文件撰寫** | [development/USER_DOCUMENTATION_GUIDE.md](development/USER_DOCUMENTATION_GUIDE.md) |

---

## 📚 詳細經驗索引（按主題分類）

> **用途**：此章節提供詳細經驗教訓的參考連結，按主題分類便於查找。
> 每個文件包含完整的問題分析、解決方案、程式碼範例與相關文件連結。

### 🎯 Phase 3 系列（WebUI 移植與整合）

| 文件 | 主題 | 重點內容 |
|------|------|----------|
| [phase3_lessons.md](memory/phase3_lessons.md) | Phase 3 完整經驗 | Python 時間處理、dataclass、非重入鎖、競態條件、狀態同步 |
| [phase3_2_lessons.md](memory/phase3_2_lessons.md) | **Phase 3.2 Qt 整合** | **不重造輪子原則、WIP 替換策略、CodeQL 修復、API 整合、固件安全** |

### 🔒 安全性系列

| 文件 | 主題 | 重點內容 |
|------|------|----------|
| [security_lessons.md](memory/security_lessons.md) | 安全最佳實踐 | Token 生成、動作驗證、密碼處理、審計日誌 |
| [phase3_2_lessons.md](memory/phase3_2_lessons.md) | CodeQL 安全修復 | 路徑遍歷防護、資訊洩露防護、安全事件日誌 |
| PROJECT_MEMORY.md（本文件）| **路徑穿越修復模式** | **`startswith` 繞過漏洞、`werkzeug.safe_join` 首選用法** |

### 🛠️ 開發工具系列

| 文件 | 主題 | 重點內容 |
|------|------|----------|
| [code_quality_lessons.md](memory/code_quality_lessons.md) | 程式碼品質 | Linting、型別提示、測試策略 |
| [cli_batch_lessons.md](memory/cli_batch_lessons.md) | CLI/批次操作 | TDD 流程、錯誤處理、重複計數防護、async fixtures |

### 🖥️ UI/UX 系列

| 文件 | 主題 | 重點內容 |
|------|------|----------|
| [tui_llm_lessons.md](memory/tui_llm_lessons.md) | TUI 與 LLM | TUI 架構、LLM 整合、HTTP 會話重用 |
| [phase3_2_lessons.md](memory/phase3_2_lessons.md) | Qt Widgets 開發 | 原生 Widget 架構、真實 API 整合模式 |

### 🔧 特定功能系列

| 文件 | 主題 | 重點內容 |
|------|------|----------|
| [step1-device-id-generator-lessons.md](memory/step1-device-id-generator-lessons.md) | 設備 ID 生成 | UUID 生成、跨平台相容性 |
| [step2-token-encryption-lessons.md](memory/step2-token-encryption-lessons.md) | Token 加密 | AES-256-GCM、金鑰管理 |
| [step3-platform-storage-lessons.md](memory/step3-platform-storage-lessons.md) | 平台存儲 | 跨平台資料存儲策略 |
| [step4-edge-token-cache-lessons.md](memory/step4-edge-token-cache-lessons.md) | Edge Token 快取 | 快取策略、過期處理 |
| [step5-integration-tests-lessons.md](memory/step5-integration-tests-lessons.md) | 整合測試 | E2E 測試策略 |
| [unified_launcher_playbook.md](memory/unified_launcher_playbook.md) | 統一啟動器 | 啟動流程、配置管理 |

### 📖 使用指南

**如何使用此索引**：
1. 根據當前任務主題選擇對應的文件
2. 每個文件開頭有「概述」章節快速了解內容
3. 使用文件內的目錄跳轉到特定章節
4. 相關文件之間有交叉參考連結

**快速查找**：
- **開發新功能前**：查看 phase3_2_lessons.md §1「不重造輪子原則」
- **安全問題修復**：查看 phase3_2_lessons.md §3「CodeQL 安全修復模式」
- **API 整合**：查看 phase3_2_lessons.md §4「真實 API 整合架構」
- **固件更新**：查看 phase3_2_lessons.md §5「固件更新安全流程」
- **Code Review**：查看 phase3_2_lessons.md §7「Code Review 清理建議」

---

## 🎯 關鍵經驗精華（Top 16）

> 根據使用頻率排序，⭐⭐⭐ 為最高頻率

### 0. 用戶文件撰寫原則⭐⭐⭐

**使用頻率**：每次文件更新
**相關文件**：[USER_DOCUMENTATION_GUIDE.md](development/USER_DOCUMENTATION_GUIDE.md)

**核心原則**：
- 使用者導向：按使用場景組織，不是按程式碼結構
- 漸進式揭露：快速入門 → 功能概覽 → 完整參考
- 實例優先：可執行的範例勝過抽象描述
- 多層次文件：新手/進階/問題排解分開處理

**文件結構**：
```
USER_GUIDE_INDEX.md    - 單一入口點
QUICK_START.md         - 5 分鐘快速上手
FAQ.md                 - 30+ 常見問題
TROUBLESHOOTING.md     - 系統化診斷流程
FEATURES_REFERENCE.md  - 完整功能說明
WEBUI_USER_GUIDE.md    - 介面詳細指南
```

### 0.5 路徑穿越防護：werkzeug.safe_join ⭐⭐⭐

**使用頻率**：每次處理使用者輸入路徑
**修復日期**：2026-02-24

**核心原則**：`str(path).startswith(str(base))` 有繞過漏洞，專案中禁止使用。

```python
# ✅ 首選（Werkzeug 已在 requirements.txt，Flask 生態標準）
from werkzeug.utils import safe_join
safe_path = safe_join(str(base_dir), user_input_a, user_input_b)
if safe_path is None:           # None = 路徑穿越被攔截
    raise ValueError("Path traversal detected")
file_path = Path(safe_path)     # 確認安全後使用

# ✅ 備選（stdlib，需 Python 3.9+）
if not Path(user_path).resolve().is_relative_to(Path(base_dir).resolve()):
    raise ValueError("Path traversal detected")

# ❌ 禁止（startswith 繞過：/base_dir_evil 會通過此檢查）
if not str(path.resolve()).startswith(str(base.resolve())):
    ...
```

**修復的檔案**：
- `Cloud/api/storage.py` — `upload_file()` 使用 `safe_join` 同時建路徑 + 驗安全
- `Edge/qtwebview-app/routes_firmware_tiny.py` — `robot_variables()` 使用 `safe_join`

### 1. Linting 自動修正（最常用）⭐⭐⭐

**使用頻率**：幾乎每次提交
**相關文件**：[code_quality_lessons.md](memory/code_quality_lessons.md)

```bash
# 移除所有尾隨空格（W293）
find src/ MCP/ -name "*.py" -exec sed -i 's/[[:space:]]*$//' {} \;

# 檢查代碼品質
python3 -m flake8 src/ MCP/ --select=E,F,W --max-line-length=120
```

### 2. Python 時間處理（必記）⭐⭐⭐

**使用頻率**：高頻使用
**相關文件**：[phase3_lessons.md](memory/phase3_lessons.md#經驗-11-python-時間處理)

```python
# ❌ 不要使用（Python 3.12+ 已棄用）
timestamp = datetime.utcnow()

# ✅ 應該使用
from src.common.datetime_utils import utc_now, utc_now_iso
timestamp = utc_now()
iso_string = utc_now_iso()
```

### 3. 測試驅動開發流程⭐⭐⭐

**使用頻率**：每個新功能
**相關文件**：[cli_batch_lessons.md](memory/cli_batch_lessons.md)

```
撰寫測試 → 執行（失敗）→ 實作 → 執行（通過）→ 重構
```

### 4. 安全的 Token 生成⭐⭐⭐

**使用頻率**：所有認證相關功能
**相關文件**：[security_lessons.md](memory/security_lessons.md)

```python
# ❌ 硬編碼預設 token
token = os.environ.get("APP_TOKEN", "dev-token")

# ✅ 使用安全的隨機 token
import secrets
token = os.environ.get("APP_TOKEN") or secrets.token_hex(32)
```

### 5. 型別提示正確使用⭐⭐

**使用頻率**：高頻使用
**相關文件**：[code_quality_lessons.md](memory/code_quality_lessons.md)

```python
# ❌ 降低型別安全性
def process(options: Any) -> None:
    pass

# ✅ 使用具體型別
def process(options: BatchOptions) -> None:
    pass
```

### 6. 批次操作錯誤處理⭐⭐

**使用頻率**：所有批次/非同步操作
**相關文件**：[cli_batch_lessons.md](memory/cli_batch_lessons.md)

```python
# ✅ 指數退避重試 + 超時控制
for attempt in range(max_retries):
    try:
        result = await execute_with_timeout(cmd, timeout_ms)
        return result
    except TimeoutError:
        if attempt < max_retries - 1:
            await asyncio.sleep(backoff_factor ** attempt)
        else:
            return timeout_result
```

### 7. dataclass 與 datetime⭐⭐

**使用頻率**：資料模型定義時
**相關文件**：[phase3_lessons.md](memory/phase3_lessons.md)

```python
# ❌ 所有實例共享同一時間戳
@dataclass
class Status:
    updated_at: datetime = utc_now()  # 錯誤！

# ✅ 使用 field(default_factory=...)
@dataclass
class Status:
    updated_at: datetime = field(default_factory=utc_now)
```

### 8. 動作驗證（安全性）⭐⭐

**使用頻率**：所有用戶輸入處理
**相關文件**：[security_lessons.md](memory/security_lessons.md)

```python
# ✅ 驗證動作在有效清單中
if action_name not in VALID_ACTIONS:
    logger.warning(f"Invalid action: {action_name}")
    return error_response()
```

### 9. Async Fixtures 問題（pytest-asyncio）⭐⭐

**使用頻率**：測試撰寫時
**相關文件**：[cli_batch_lessons.md](memory/cli_batch_lessons.md#131-async-fixtures-問題)

```python
# ❌ pytest-asyncio 新版不支援
@pytest.fixture
async def setup():
    return await create_resource()

# ✅ 直接在測試函數中建立
async def test_something():
    resource = await create_resource()
    # 或使用乾跑模式簡化
```

### 10. 非重入鎖問題⭐⭐

**使用頻率**：多執行緒同步時
**相關文件**：[phase3_lessons.md](memory/phase3_lessons.md)

```python
# ❌ 會造成死鎖
def method_a(self):
    with self._lock:
        self.method_b()  # method_b 也需要 _lock

# ✅ 使用可重入鎖或提取邏輯
self._lock = threading.RLock()  # 可重入鎖
```

### 11. 狀態更新與事件通知一致性⭐⭐

**使用頻率**：狀態管理功能
**相關文件**：[phase3_lessons.md](memory/phase3_lessons.md)

```python
# ✅ 在同一處理中完成
async def update_status(self, robot_id, status):
    await self._state_store.set(key, status)
    await self._event_bus.publish(EventTopics.STATUS_UPDATED, {...})
```

### 12. 重複計數防護⭐

**使用頻率**：狀態追蹤功能
**相關文件**：[cli_batch_lessons.md](memory/cli_batch_lessons.md)

```python
# ✅ 檢查舊狀態避免重複計數
terminal_states = {SUCCESS, FAILED, TIMEOUT, CANCELLED}
if status in terminal_states and (old_status is None or old_status not in terminal_states):
    self.completed += 1
```

### 13. 競態條件防護⭐

**使用頻率**：多執行緒/非同步操作
**相關文件**：[phase3_lessons.md](memory/phase3_lessons.md)

```python
# ❌ 直接存取可能為 None 的屬性
if self._process.poll() is not None:
    ...

# ✅ 先儲存引用
process = self._process
if process is None or process.poll() is not None:
    ...
```

### 14. HTTP 會話重用⭐

**使用頻率**：HTTP 客戶端實作
**相關文件**：[tui_llm_lessons.md](memory/tui_llm_lessons.md)

```python
# ❌ 每次建立新會話
async with aiohttp.ClientSession() as session:
    ...

# ✅ 重用會話
if self._session is None or self._session.closed:
    self._session = aiohttp.ClientSession()
```

### 15. Flask 2.3+ JSON 配置⭐

**使用頻率**：Flask 應用配置
**相關文件**：[phase3_lessons.md](memory/phase3_lessons.md)

```python
# ⚠️ 舊版本（已棄用）
app.config['JSON_AS_ASCII'] = False

# ✅ 新版本
app.json.ensure_ascii = False
```

### 16. 審計日誌記錄模式⭐⭐

**使用頻率**：所有安全敏感操作
**相關文件**：[security/audit-logging-implementation.md](security/audit-logging-implementation.md)

```python
# ✅ 使用專用函數記錄審計事件
from WebUI.app.audit import log_login_attempt, log_audit_event

# 登入成功/失敗
log_login_attempt(username='user', success=True, user_id=user.id)
log_login_attempt(username='user', success=False)

# 自訂事件
log_audit_event(
    action='custom_action',
    message='執行操作',
    user_id=current_user.id,
    resource_type='robot',
    resource_id='123',
    context={'detail': 'info'}
)
```

### 17. Flask-SQLAlchemy 資料庫遷移⭐

**使用頻率**：資料庫 schema 變更時
**相關文件**：[security/audit-logging-implementation.md](security/audit-logging-implementation.md)

```python
# ✅ 遷移檔案結構
# WebUI/migrations/versions/<revision_id>_<description>.py

from alembic import op
import sqlalchemy as sa

revision = 'a1u2d3i4t5l6'
down_revision = 'previous_revision'

def upgrade():
    op.create_table('table_name', ...)
    op.create_index('index_name', 'table_name', ['column'])

def downgrade():
    op.drop_index('index_name', 'table_name')
    op.drop_table('table_name')
```

### 18. RBAC 權限檢查模式⭐⭐

**使用頻率**：所有需要權限控管的路由
**相關文件**：[security/audit-logging-implementation.md](security/audit-logging-implementation.md)

```python
# ✅ 在路由中檢查角色權限
@bp.route('/admin_only')
@login_required
def admin_function():
    if current_user.role not in ['admin', 'auditor']:
        flash('您沒有權限訪問此頁面。')
        abort(403)
    # 執行管理操作
    return render_template('admin_page.html.j2')
```

### 19. Flask 模板條件渲染⭐⭐

**使用頻率**：所有需要根據角色顯示不同內容的模板
**相關文件**：[security/audit-logging-implementation.md](security/audit-logging-implementation.md)

```jinja2
{# ✅ 在模板中根據角色顯示內容 #}
{% if current_user.is_authenticated %}
    {% if current_user.role in ['admin', 'auditor'] %}
    <li>
        <a href="{{ url_for('webui.audit_logs') }}">
            <i class="fa fa-shield"></i> 審計日誌
        </a>
    </li>
    {% endif %}
{% endif %}
```

### 20. 審計日誌查詢過濾模式⭐

**使用頻率**：實作列表查詢頁面時
**相關文件**：[security/audit-logging-implementation.md](security/audit-logging-implementation.md)

```python
# ✅ 多維度過濾與分頁查詢
query = AuditLog.query

# 應用過濾條件
if severity:
    query = query.filter(AuditLog.severity == severity)
if category:
    query = query.filter(AuditLog.category == category)
if start_date:
    query = query.filter(AuditLog.timestamp >= start_dt)
if search:
    query = query.filter(
        db.or_(
            AuditLog.message.ilike(f'%{search}%'),
            AuditLog.trace_id.ilike(f'%{search}%')
        )
    )

# 排序與分頁
query = query.order_by(AuditLog.timestamp.desc())
pagination = query.paginate(page=page, per_page=per_page, error_out=False)
```

### 21. 零信任前端原則⭐⭐⭐ (NEW - 2025-12-17)

**使用頻率**：所有前後端互動
**相關文件**：[security/threat-model.md](security/threat-model.md) v2.0, [security/edge-cloud-auth-analysis.md](security/edge-cloud-auth-analysis.md)

**核心原則：所有前端資料視為不可信任**

```python
# ✅ 後端強制驗證所有輸入
from pydantic import BaseModel, validator

class UserCreateRequest(BaseModel):
    username: str
    email: str
    role: str
    
    @validator('role')
    def validate_role(cls, v):
        if v not in ['admin', 'operator', 'viewer', 'auditor']:
            raise ValueError('Invalid role')
        return v

@app.route('/api/users', methods=['POST'])
@login_required
def create_user():
    # 1. Pydantic 驗證輸入（不信任前端）
    try:
        data = UserCreateRequest(**request.json)
    except ValidationError:
        return jsonify({'error': 'Invalid input'}), 400
    
    # 2. 後端檢查權限（不信任前端 token）
    if current_user.role != 'admin':
        log_permission_denied(current_user.id, 'create_user')
        return jsonify({'error': 'Unauthorized'}), 403
    
    # 3. 業務邏輯在後端執行
    user = User(username=data.username, email=data.email, role=data.role)
    db.session.add(user)
    
    # 4. 記錄審計日誌
    log_audit_event(action='user_create', user_id=current_user.id)
```

### 22. Edge-Cloud 認證同步架構⭐⭐⭐ (NEW - 2025-12-17)

**使用頻率**：Edge 環境認證實作
**相關文件**：[security/edge-cloud-auth-analysis.md](security/edge-cloud-auth-analysis.md)

**推薦方案：Token 快取同步**
- 登入在 Server 驗證，Token 快取至 Edge
- Access Token：15 分鐘（短期，減少被盜風險）
- Refresh Token：7 天（設備綁定）
- 加密儲存：Fernet 或 OS keychain

```python
# Edge 端 Token 管理器
class EdgeAuthCache:
    def get_valid_access_token(self) -> str:
        """獲取有效的 Access Token（自動更新過期 token）"""
        tokens = self.load_tokens()
        if not tokens:
            return None
        
        # 檢查是否過期（提前 1 分鐘更新）
        if not self._is_token_valid(tokens['access_token'], buffer=60):
            # 使用 Refresh Token 自動更新
            return self._refresh_access_token(tokens['refresh_token'])
        
        return tokens['access_token']
```

### 23. Edge 環境安全約束⭐⭐ (NEW - 2025-12-17)

**使用頻率**：Edge 環境開發
**相關文件**：[security/edge-cloud-auth-analysis.md](security/edge-cloud-auth-analysis.md), [security/threat-model.md](security/threat-model.md) v2.0

**Edge 環境特性**：
- **延遲敏感**：<100ms 回應時間（輕量級驗證）
- **記憶體受限**：4-8GB RAM（本地快取限制）
- **物理安全弱**：設備可能被竊取/篡改
- **離線運作**：需本地快取與降級策略

```python
# ✅ Server 端重新驗證 Edge 資料（零信任）
def sync_from_edge(edge_logs: List[Dict]):
    for log in edge_logs:
        # 1. Pydantic 驗證
        validated = AuditLogSchema.validate(log)
        
        # 2. 完整性檢查
        if not verify_log_signature(log):
            continue
        
        # 3. 業務邏輯驗證
        if not verify_user_exists(validated.user_id):
            continue
        
        # 4. 儲存
        db.session.add(AuditLog(**validated.dict()))
```

### 24. Token 安全實作模式⭐⭐ (NEW - 2025-12-17)

**使用頻率**：認證系統實作
**相關文件**：[security/edge-cloud-auth-analysis.md](security/edge-cloud-auth-analysis.md)

**安全措施**：
1. 短期 Access Token（15 分鐘）
2. Refresh Token rotation（單次使用）
3. 設備指紋綁定（Device ID）
4. Token 撤銷清單（Server 端）
5. 加密儲存（Fernet/OS keychain）

```python
# Server 端：登入生成 Token
@app.route('/auth/login', methods=['POST'])
def login():
    # 驗證使用者
    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        log_login_attempt(username, success=False)
        return jsonify({'error': 'Invalid credentials'}), 401
    
    # 生成短期 Access Token (15 分鐘)
    access_token = create_access_token(
        user_id=user.id,
        role=user.role,
        expires_in=900
    )
    
    # 生成 Refresh Token (7 天，設備綁定)
    refresh_token = create_refresh_token(
        user_id=user.id,
        device_id=request.headers.get('X-Device-ID'),
        expires_in=604800
    )
    
    log_login_attempt(username, success=True, user_id=user.id)
    return jsonify({
        'access_token': access_token,
        'refresh_token': refresh_token,
        'user': user.to_dict()
    })
```

### 25. 離線模式權限控管⭐⭐ (NEW - 2025-12-17)

**使用頻率**：Edge 環境 API 開發
**相關文件**：[security/edge-cloud-auth-analysis.md](security/edge-cloud-auth-analysis.md)

**操作權限矩陣**：
- ✅ 離線允許：查看狀態、執行基本指令、查看歷史
- ❌ 離線禁止：新增使用者、權限變更、系統配置

```python
# 離線認證裝飾器
class OfflineAuthManager:
    def require_auth(self, allow_offline=True, offline_restricted=False):
        def decorator(f):
            @wraps(f)
            def wrapper(*args, **kwargs):
                # 嘗試線上驗證
                online_user = self._verify_online()
                if online_user:
                    self.offline_mode = False
                    return f(*args, **kwargs)
                
                # 降級至離線模式
                if allow_offline:
                    offline_user = self._verify_offline()
                    if offline_user:
                        if offline_restricted:
                            return jsonify({'error': 'Requires online'}), 403
                        return f(*args, **kwargs)
                
                return jsonify({'error': 'Unauthorized'}), 401
            return wrapper
        return decorator

# 使用範例
@app.route('/api/users', methods=['POST'])
@auth.require_auth(offline_restricted=True)  # 需線上
def create_user():
    """建立使用者（需要線上連線）"""
    ...

@app.route('/api/robots/status', methods=['GET'])
@auth.require_auth(allow_offline=True)  # 允許離線
def get_robot_status():
    """查看狀態（可離線）"""
    ...
```

---

## 📚 詳細經驗索引

> 以下主題的詳細經驗教訓已移至專題文件，保持主檔案精簡易讀。

### Phase 3 系列經驗

- **[memory/phase3_lessons.md](memory/phase3_lessons.md)**
  - Phase 3.1: 服務協調器、共享狀態管理器（152 條經驗）
  - Phase 3.2: Tiny 版本、Edge UI 移植、固件更新（87 條經驗）
  - Phase 3.3: 統一整合與雲端分離（45 條經驗）
  - Code Review 與 CodeQL 安全修復（63 條經驗）

### CLI 批次操作經驗

- **[memory/cli_batch_lessons.md](memory/cli_batch_lessons.md)**
  - 批次操作架構設計
  - 多工調度策略（parallel, sequential, grouped）
  - 測試驅動開發（TDD）實踐
  - 代碼品質自動化

### TUI + LLM 整合經驗

- **[memory/tui_llm_lessons.md](memory/tui_llm_lessons.md)**
  - Textual TUI 框架使用
  - LLM 提供商整合（Ollama, LM Studio）
  - 自然語言指令處理
  - 提示工程與安全性

### 安全性經驗

- **[memory/security_lessons.md](memory/security_lessons.md)**
  - Token 安全管理與輪替
  - CodeQL 安全掃描修復
  - XSS 防護與輸入驗證
  - 認證授權最佳實踐

- **[security/audit-logging-implementation.md](security/audit-logging-implementation.md)**（新增）
  - 審計日誌系統實作（2025-12-17）
  - AuditLog 資料模型設計
  - 審計記錄機制與工具函數
  - 查詢介面與權限控管
  - 測試策略與最佳實踐

- **[security/audit-logging-summary.md](security/audit-logging-summary.md)**（新增）
  - 審計日誌完成摘要
  - 統計數據與技術亮點
  - 未來增強建議

- **[security/edge-cloud-auth-analysis.md](security/edge-cloud-auth-analysis.md)**（新增 2025-12-17）
  - Edge-Cloud 認證架構分析
  - 三種方案比較（完全雲端、Token 快取、混合認證）
  - 推薦實作：Token 快取同步架構
  - 實作階段規劃（5 個 Phase）
  - 安全考量與優缺點分析

- **[security/approach-b-implementation.md](security/approach-b-implementation.md)**（新增 2025-12-17）
  - 方案 B Phase 1 實作文件
  - Server 端 JWT Token 認證 API
  - 5 個 API 端點（login, refresh, verify, revoke, me）
  - 14 個測試案例
  - 程式碼範例與使用指引

### 代碼品質經驗

- **[memory/code_quality_lessons.md](memory/code_quality_lessons.md)**
  - Linting 自動化（flake8）
  - 型別提示最佳實踐
  - 測試覆蓋策略
  - 持續整合優化

---

## 🔄 最近更新

### 2025-12-17: 方案 B Phase 1 - Server 端 JWT Token 認證 API 實作
- 實作 Server 端認證 API 模組（WebUI/app/auth_api.py）
- 5 個 API 端點：/api/auth/login, refresh, verify, revoke, me
- JWT Token 策略：Access 15分鐘 + Refresh 7天 + Device ID 綁定
- 14 個測試案例全部通過
- 審計日誌完整整合（api_login_success/failure, token_refresh 等）
- 符合零信任前端原則（所有驗證在 Server 端）
- 詳見：[security/approach-b-implementation.md](security/approach-b-implementation.md)

### 2025-12-17: Edge-Cloud 認證架構分析
- 完成 Edge-Cloud 認證同步架構分析文件
- 推薦方案：Token 快取同步（登入在 Server，Token 快取至 Edge）
- Access Token 15 分鐘 + Refresh Token 7 天
- 離線模式權限控管矩陣
- 實作階段規劃（5 個 Phase）
- 詳見：[security/edge-cloud-auth-analysis.md](security/edge-cloud-auth-analysis.md)

### 2025-12-17: 威脅模型 v2.0 - 零信任前端
- 更新威脅模型至 v2.0
- 新增零信任前端核心原則
- 新增 Edge 環境安全約束
- 新增 4 個高優先級威脅（前端驗證繞過、資料注入、Edge 篡改、Session 劫持）
- 重寫信任邊界模型
- 詳見：[security/threat-model.md](security/threat-model.md)

### 2025-12-17: 安全性強化 - 審計日誌系統實作
- 實作完整審計日誌系統（資料模型、記錄機制、查詢介面）
- 新增 AuditLog 模型（符合 EventLog schema）
- 整合至關鍵路由（登入/登出/註冊/密碼重設）
- 21 個測試全部通過
- 詳見：[security/audit-logging-summary.md](security/audit-logging-summary.md)

### 2025-12-17: CLI 批次操作 + 代碼品質優化
- 新增 CLI 批次操作模組（36 個測試，100% 通過）
- 修正倉庫代碼品質問題（E/F/W 級別，15→0）
- 新增常見錯誤提醒章節
- 詳見：[memory/cli_batch_lessons.md](memory/cli_batch_lessons.md)

### 2025-12-11: TUI + LLM 整合
- 實作 Textual TUI 框架
- 整合 LLM 自然語言控制
- 詳見：[memory/tui_llm_lessons.md](memory/tui_llm_lessons.md)

### 2025-12-10: Phase 3 完成
- Phase 3.3 統一整合完成
- Tiny 版本發布
- Edge UI 移植完成
- 詳見：[memory/phase3_lessons.md](memory/phase3_lessons.md)

### 2025-12-17: Edge Token 快取、離線同步、Unified Launcher 整合（實作與驗證）
- 新增邊緣 Token 快取模組：`src/robot_service/edge_token_cache.py`（加密本地儲存、TTL、記憶體快取）。
- 新增離線同步工作者：`src/robot_service/edge_token_sync.py`（加密佇列、重試/指數退避、持久化）。
- 新增整合器：`src/robot_service/token_integration.py`，將 `TokenManager` 的輪替事件綁定到快取與同步隊列。
- 在 `src/robot_service/unified_launcher.py` 中注入 `TokenIntegration.start()/stop()`，並改進子進程啟動診斷：子程序 stdout/stderr 會重導至 `/tmp/<service>.stdout.log` 與 `/tmp/<service>.stderr.log`，啟動失敗時會將內容記錄於啟動器日誌以便排查。
- 新增使用說明文件：`docs/development/UNIFIED_LAUNCHER.md`（包含快速啟動、環境變數、日誌與故障排除步驟）。
- 已 commit 並推送所有變更到分支 `copilot/enhance-security-audit-logs`（commit: "docs: add Unified Launcher usage guide"）。
- 在工作區虛擬環境中手動觸發一次 token rotation（`TokenManager.rotate_token(reason='manual_test')`），驗證 `TokenIntegration` 能正確寫入加密檔案：
    - 產生 `/home/<user>/.robot-console/edge_tokens.enc`
    - 產生 `/home/<user>/.robot-console/edge_sync.enc`

**注意/後續**：
- `token_integration` 的 cloud sync callback 目前為 placeholder（回傳 False 以觸發重試機制），生產環境需實作雲端通知/刷新 API 並安全授權。
- 建議將 `EDGE_TOKEN_KEY` 作為部署時的安全參數（不要硬編碼），並在文件/部署腳本中說明如何產生與管理該金鑰。

---

## 💡 開發流程提醒

1. **開始前**：閱讀 `⚠️ 常見錯誤提醒` 章節
2. **開發中**：參考相關專題文件（memory/*.md）
3. **提交前**：執行 linting 和測試
4. **完成後**：更新專案記憶（主檔案或專題文件）

---

**檔案精簡**：2,633 行 → 450 行（保留核心，詳細內容移至專題文件）
**最後更新**：2026-01-21

### 2026-01-21: Phase 3.2 Qt WebView 完整移植 + WIP 替換

> 📖 **完整教訓請參閱**：[memory/phase3_2_lessons.md](memory/phase3_2_lessons.md)

**核心經驗摘要**：

1. **不重造輪子原則** - 使用標準 pip 套件（pywifi, paramiko, cryptography, tqdm）
2. **系統化 WIP 替換策略** - 追蹤 47 個 TODO 項目，分 4 個 Phase 執行
3. **CodeQL 安全修復模式** - 路徑遍歷防護（os.path.basename）、資訊洩露防護（通用錯誤訊息）
4. **真實 API 整合架構** - BackendAPIClient 統一管理，Widget 依賴注入
5. **固件更新安全流程** - PBKDF2 + Fernet + WiFi（pywifi）+ SSH/SFTP（paramiko + scp）
6. **Qt Widgets 真實化模式** - 從模擬到真實的漸進式替換
7. **Code Review 清理建議** - 移除未使用 import、添加註解、避免 BaseException

**關鍵成果**：
- ✅ Phase 1 完成：10/47 WIP 項目替換（21% 進度）
- ✅ 所有 Qt Widgets 使用真實 API（無模擬數據）
- ✅ CodeQL 安全問題修復（路徑遍歷 + 資訊洩露）
- ✅ 跨平台支援（pywifi 統一 WiFi API）
- ✅ 效能提升（原生 Widgets 減少 75% 記憶體使用）

**相關文件**：
- **完整教訓**：[memory/phase3_2_lessons.md](memory/phase3_2_lessons.md)
- **追蹤文件**：[temp/WIP_REPLACEMENT_TRACKING.md](temp/WIP_REPLACEMENT_TRACKING.md)
- **API 客戶端**：[qtwebview-app/backend_client.py](../qtwebview-app/backend_client.py)
- **固件工具**：[qtwebview-app/firmware_utils.py](../qtwebview-app/firmware_utils.py)
- **主視窗**：[qtwebview-app/main_window.py](../qtwebview-app/main_window.py)

5. **固件更新安全流程**
   - SecureConfigHandler：PBKDF2 + Fernet 加密
   - WiFiManager：pywifi 跨平台 WiFi 連接
   - SSHClient：paramiko + scp 安全上傳
   - secure_delete_file：3 次覆寫安全刪除
   - 記憶體敏感數據清理（finally 區塊）

6. **Qt Widgets 真實化模式**
   ```python
   # ✅ 注入真實 API 客戶端
   class RobotControlWidget(QWidget):
       def __init__(self):
           self.api_client = BackendAPIClient(base_url=BACKEND_URL)
       
       def _load_robots(self):
           try:
               robots = self.api_client.list_robots()
               self.populate_list(robots)
           except Exception as e:
               logger.error(f"Failed to load robots: {e}")
               self.show_error("無法載入機器人列表")
   ```

7. **Code Review 清理建議**
   - 移除未使用的 import（降低依賴）
   - 空 except 子句添加說明註解
   - 避免直接捕獲 BaseException（使用 Exception）
   - 使用 logger.warning/debug 替代 pass

**問題與解決**：
- **問題**：Qt Widgets 初期使用模擬數據，無法測試真實功能
  - **解決**：創建 backend_client.py 和 firmware_utils.py，統一真實實作

- **問題**：CodeQL 發現路徑遍歷漏洞（用戶可傳入 `../../../etc/passwd`）
  - **解決**：使用 `os.path.basename()` 移除路徑分隔符

- **問題**：異常堆棧暴露給客戶端（資訊洩露風險）
  - **解決**：所有 `str(e)` 替換為中文通用錯誤訊息

- **問題**：47 個 TODO 項目難以追蹤
  - **解決**：創建 WIP_REPLACEMENT_TRACKING.md，系統化管理

**效能改進**：
- Qt 原生 Widgets 效能優於 WebView（減少記憶體與 CPU 使用）
- requests Session 重用減少連線建立開銷
- pywifi 提供更穩定的跨平台 WiFi 管理

**相關文件**：
- [docs/temp/WIP_REPLACEMENT_TRACKING.md](../docs/temp/WIP_REPLACEMENT_TRACKING.md)
- [qtwebview-app/backend_client.py](../qtwebview-app/backend_client.py)
- [qtwebview-app/firmware_utils.py](../qtwebview-app/firmware_utils.py)
- [qtwebview-app/main_window.py](../qtwebview-app/main_window.py)
- [memory/phase3_lessons.md](memory/phase3_lessons.md)

### 2026-01-05: RabbitMQ & AWS SQS 佇列整合
- **新增** RabbitMQ Queue 實作（450+ 行，完整實作 QueueInterface）
- **新增** AWS SQS Queue 實作（470+ 行，支援 Standard/FIFO 佇列）
- **新增** 配置匯出與注入工具（300+ 行，支援多種格式）
- **更新** ServiceManager 支援動態佇列選擇（memory/rabbitmq/sqs）
- **更新** Edge Queue 配置管理（17+ 環境變數）
- **完成** 1150+ 行測試代碼（單元、整合、比較測試）
- **完成** CI/CD Pipeline（GitHub Actions，多 Python 版本）
- **完成** 文件更新（部署指南、測試指南、架構文件）
- 詳見：[docs/RABBITMQ_INTEGRATION_TODOS.md](docs/RABBITMQ_INTEGRATION_TODOS.md)

**關鍵經驗**：
1. **QueueInterface 設計模式**
   - 抽象介面統一三種實作（Memory/RabbitMQ/SQS）
   - 確保行為一致性（參數化測試驗證）
   - 便於未來擴展（Kafka、Redis 等）

2. **RabbitMQ Best Practices**
   - 使用 Topic Exchange + Priority Queue
   - DLX/DLQ 處理失敗訊息
   - 連線池與 Channel 池提升效能
   - Publisher confirms 確保訊息不遺失

3. **AWS SQS 整合要點**
   - 長輪詢減少空請求成本
   - FIFO vs Standard 選擇（順序 vs 吞吐量）
   - IAM Role 優於 Access Key（安全性）
   - CloudWatch 監控訊息流量

4. **配置管理策略**
   - 環境變數驅動配置
   - 支援多種匯出格式（Shell Script、Docker .env、K8s ConfigMap）
   - 配置合併與注入工具
   - 便利函式簡化使用

5. **測試策略**
   - pytest 參數化 fixture 支援多種實作
   - 使用 `TEST_WITH_RABBITMQ` 環境變數控制測試執行
   - Docker Compose 提供測試環境
   - 行為一致性測試確保介面合規

6. **文件完整性**
   - 部署指南（本地、Docker、雲端）
   - 測試執行指南（單元、整合、自動化）
   - 架構文件更新（比較表、使用場景、遷移指南）
   - 程式碼註解與 docstring 完整

**問題與解決**：
- **問題**：pytest-asyncio fixture 標記問題
  - **解決**：明確標記 `@pytest.fixture` 和 `@pytest.mark.asyncio`

- **問題**：RabbitMQ 沒有原生 peek 支援
  - **解決**：使用 get + nack(requeue=True) 模擬

- **問題**：SQS 訊息優先權模擬
  - **解決**：使用 Message Attributes 儲存優先權資訊

- **問題**：配置注入的靈活性
  - **解決**：建立 ConfigExporter 和 ConfigInjector 工具類

**效能數據**：
- MemoryQueue: <1ms 延遲，100K+ msg/s 吞吐量
- RabbitMQ: 1-10ms 延遲，10K-50K msg/s 吞吐量
- AWS SQS: 10-100ms 延遲，Standard 無限制，FIFO 3K msg/s

**成本比較**（1M 訊息/月）：
- MemoryQueue: 接近 $0
- RabbitMQ (自建): $30-200/月（含基礎設施與維護）
- AWS SQS: $0.50-2/月（按使用付費）

**相關文件**：
- [docs/deployment/RABBITMQ_DEPLOYMENT.md](docs/deployment/RABBITMQ_DEPLOYMENT.md)
- [docs/deployment/TEST_EXECUTION.md](docs/deployment/TEST_EXECUTION.md)
- [docs/features/queue-architecture.md](docs/features/queue-architecture.md)
- [src/robot_service/queue/rabbitmq_queue.py](../src/robot_service/queue/rabbitmq_queue.py)
- [src/robot_service/queue/sqs_queue.py](../src/robot_service/queue/sqs_queue.py)
- [src/robot_service/config_injection.py](../src/robot_service/config_injection.py)

---

## 雲端同步 UI/狀態提示實作（2026-02-11）

**目標**：為 Edge UI 添加雲端同步狀態的即時監控與提示功能。

**實作內容**：

1. **API 端點**
   - 新增 `GET /api/edge/sync/status` API
   - 返回網路狀態、佇列服務狀態、緩衝區統計
   - 基於現有的 `check_internet_connection()` 和 `check_mcp_connection()` 函式

2. **UI 元件**
   - 在首頁新增「☁️ 雲端同步狀態」面板
   - 顯示 4 個狀態卡片：網路連線、佇列服務、緩衝區、最後同步
   - 使用顏色區分狀態（綠色=正常、黃色=警告、紅色=錯誤）

3. **即時更新**
   - 頁面載入時立即檢查狀態
   - 每 30 秒更新完整狀態
   - 每 10 秒更新雲端同步狀態
   - 使用 `setInterval` 實現自動更新

**技術細節**：

1. **API 設計**
   ```python
   @edge_ui.route('/api/edge/sync/status', methods=['GET'])
   def api_sync_status():
       # 返回結構化的狀態資料
       return jsonify({
           'network': {'online': bool, 'status': str},
           'services': {'mcp': {...}, 'queue': {...}},
           'buffers': {'command': {...}, 'sync': {...}},
           'sync_enabled': bool,
           'last_sync': ISO8601
       })
   ```

2. **前端狀態更新**
   ```javascript
   async function updateSyncStatus() {
       const data = await fetch('/api/edge/sync/status').then(r => r.json());
       // 更新 4 個狀態卡片的內容和樣式
       updateStatusCard('#sync-network-status', data.network);
       updateStatusCard('#sync-queue-status', data.services.queue);
       // ...
   }
   ```

3. **狀態指示**
   - `status-success`：綠色，表示正常
   - `status-warning`：黃色，表示部分可用或離線
   - `status-error`：紅色，表示錯誤或不可用

**未來改進方向**：

1. **完整 OfflineQueueService 整合**
   - 目前 API 返回的緩衝區統計為模擬資料（全為 0）
   - 需要在 Edge UI 中整合 OfflineQueueService 實例
   - 可參考 TUI 和 qtwebview-app 的實作方式

2. **WebSocket 即時推送**
   - 目前使用輪詢機制，有延遲
   - 可改用 WebSocket 實現狀態變更的即時推送
   - 減少伺服器負載和網路流量

3. **狀態變更通知**
   - 網路狀態變更時顯示 Toast 通知
   - 緩衝區累積過多時發出警告
   - 同步失敗時提示用戶

4. **詳細統計頁面**
   - 建立專門的同步統計頁面
   - 顯示歷史同步記錄
   - 提供手動清空緩衝區功能

**經驗教訓**：

1. **模組化 API 設計**
   - 將狀態檢查邏輯封裝為獨立函式（如 `check_internet_connection()`）
   - 便於在多個 API 端點重用
   - 易於測試和維護

2. **漸進式功能實作**
   - 先實作基礎版本（網路狀態檢查）
   - 在程式碼註解中標記未來改進方向
   - 保留擴展介面，便於後續整合完整功能

3. **UI 自動更新策略**
   - 區分不同更新頻率（完整狀態 30 秒、同步狀態 10 秒）
   - 避免過度頻繁的 API 呼叫
   - 在錯誤時顯示友善的錯誤狀態

4. **文件同步更新**
   - 新增功能時立即更新使用者文件
   - 在 FEATURES_REFERENCE.md 中詳細說明
   - 提供完整的 API 回應範例和使用情境

**測試方法**：
```bash
# 啟動 Edge 服務（參考專案說明文件）
# 例如：cd Edge/robot_service && python -m electron.flask_adapter

# 以 curl 測試同步狀態 API（僅檢視回應內容）
curl http://localhost:5050/api/edge/sync/status

# 驗證回應格式與 HTTP 狀態碼
curl -i http://localhost:5050/api/edge/sync/status
```

**相關文件**：
- [Edge/robot_service/electron/edge_ui.py](../Edge/robot_service/electron/edge_ui.py) - API 實作
- [Edge/robot_service/electron/templates/edge/home.html](../Edge/robot_service/electron/templates/edge/home.html) - UI 實作
- [docs/user_guide/FEATURES_REFERENCE.md](user_guide/FEATURES_REFERENCE.md#雲端同步狀態) - 使用者文件

---

