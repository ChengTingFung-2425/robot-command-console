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
**最後更新**：2025-12-17
