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

## ⚠️ 常見錯誤提醒（AI 助手必讀）

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
| **使用者指引** | [user_guide/](user_guide/) |
| **詳細經驗** | [memory/](memory/)（Phase 3, CLI, TUI, 安全性等） |

---

## 🎯 關鍵經驗精華（Top 15）

> 根據使用頻率排序，⭐⭐⭐ 為最高頻率

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

### 代碼品質經驗

- **[memory/code_quality_lessons.md](memory/code_quality_lessons.md)**
  - Linting 自動化（flake8）
  - 型別提示最佳實踐
  - 測試覆蓋策略
  - 持續整合優化

---

## 🔄 最近更新

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

---

## 💡 開發流程提醒

1. **開始前**：閱讀 `⚠️ 常見錯誤提醒` 章節
2. **開發中**：參考相關專題文件（memory/*.md）
3. **提交前**：執行 linting 和測試
4. **完成後**：更新專案記憶（主檔案或專題文件）

---

**檔案精簡**：2,633 行 → 450 行（保留核心，詳細內容移至專題文件）
**最後更新**：2025-12-17
