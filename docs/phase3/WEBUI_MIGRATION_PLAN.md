# WebUI 本地版移植計畫 (Week 2-3)

> **建立日期**: 2026-01-05  
> **狀態**: 📋 規劃階段  
> **預計時程**: 2-3 週  
> **優先級**: 🔴 最高

---

## 🎯 目標

將現有 WebUI（4,778 行 Python 程式碼，24 個模板）拆分、隔離並本地化，整合至 PyQt Tiny 版本，實現完全離線運作。

---

## 📊 現況分析

### WebUI 程式碼統計

| 類別 | 數量 | 行數 | 備註 |
|------|------|------|------|
| Python 檔案 | 26 | 4,778 | 包含路由、模型、表單等 |
| 模板檔案 | 24 | - | Jinja2 模板 |
| 路由端點 | 48 | - | 在 routes.py 定義 |
| 核心路由檔 | routes.py | 1,913 | 主要路由邏輯 |
| 資料模型 | models.py | 559 | SQLAlchemy 模型 |
| 表單定義 | forms.py | 107 | WTForms |

### 外部依賴分析

**Flask 擴展**:
- Flask-SQLAlchemy (資料庫)
- Flask-Login (認證)
- Flask-Bootstrap (UI 框架)
- Flask-Mail (郵件)
- Flask-Moment (時間格式化)
- Flask-Babel (國際化)
- Flask-Migrate (資料庫遷移)
- Flask-WTF (表單)

**CDN 依賴**（需本地化）:
- Blockly (https://unpkg.com/blockly/blockly.min.js) - 進階指令編輯器
- Bootstrap CSS/JS (通過 Flask-Bootstrap)
- jQuery (通過 Bootstrap)
- Font Awesome (圖示字體)

**問題識別**:
1. ✅ 使用 Flask-Bootstrap 的 `bootstrap/base.html` 模板
2. ⚠️ Blockly 需要 CDN 下載並本地化
3. ✅ 大部分模板繼承自 base.html.j2
4. ⚠️ 路由檔案過大（1,913 行），需拆分

---

## 📋 實作階段

### Stage 1: 研究與規劃（完成）✅

**已完成**:
- ✅ WebUI 結構分析
- ✅ 依賴項目識別
- ✅ CDN 資源列表
- ✅ 路由端點統計
- ✅ 本文件建立

---

### Stage 2: 路由拆分與隔離 (3-4 天) 🔴

**目標**: 將 routes.py (1,913 行) 拆分為模組化 Blueprint

#### 2.1 路由分類

根據功能將 48 個路由分為以下類別：

| 類別 | 路由數 | 優先級 | 檔案名稱 |
|------|--------|--------|----------|
| **核心功能** | 15 | 🔴 高 | `routes_core.py` |
| - 首頁、儀表板 | 2 | | |
| - 機器人管理 | 4 | | |
| - 指令執行 | 3 | | |
| - 媒體串流 | 2 | | |
| - 設定 | 4 | | |
| **使用者認證** | 8 | 🔴 高 | `routes_auth.py` |
| - 登入/登出 | 2 | | |
| - 註冊 | 1 | | |
| - 密碼重設 | 2 | | |
| - 用戶檔案 | 3 | | |
| **進階功能** | 12 | 🟠 中 | `routes_advanced.py` |
| - 進階指令 (Blockly) | 5 | | |
| - LLM 設定 | 3 | | |
| - 排行榜/成就 | 2 | | |
| - 編輯檔案 | 2 | | |
| **管理功能** | 8 | 🟡 低 | `routes_admin.py` |
| - 審計日誌 | 4 | | |
| - 固件更新 | 2 | | |
| - 系統監控 | 2 | | |
| **API 端點** | 5 | 🟠 中 | `routes_api.py` |
| - JWT 認證 API | 5 | | |

#### 2.2 Tiny 版本路由選擇

**Phase 1 實作（核心功能）**:
- ✅ 首頁、儀表板
- ✅ 機器人管理（列表、註冊、詳情）
- ✅ 基本指令執行
- ✅ 使用者認證（登入/登出/註冊）
- ✅ 設定（UI 偏好）

**Phase 2 實作（進階功能）**:
- ⏳ 進階指令（Blockly，需本地化）
- ⏳ LLM 設定
- ⏳ 審計日誌查看

**暫不實作**:
- ❌ 排行榜/成就系統
- ❌ 密碼重設（需郵件服務）
- ❌ 固件更新 UI（延後至整合測試）
- ❌ 複雜的管理功能

#### 2.3 實作步驟

**Step 1: 建立 routes_tiny.py 基礎架構** (0.5 天)

```python
# WebUI/app/routes_tiny.py
"""
Tiny 版本路由 - 簡化版 WebUI，用於 PyQt 整合
僅包含核心功能，移除複雜依賴
"""

from flask import Blueprint

# 建立 Blueprint，統一使用 /ui 前綴
bp_tiny = Blueprint('ui', __name__, url_prefix='/ui')

# 匯入分模組路由
from . import routes_core_tiny
from . import routes_auth_tiny

# 註冊子模組路由
bp_tiny.register_blueprint(routes_core_tiny.bp, url_prefix='/core')
bp_tiny.register_blueprint(routes_auth_tiny.bp, url_prefix='/auth')
```

**Step 2: 實作核心路由模組** (1 天)

```python
# WebUI/app/routes_core_tiny.py
"""核心功能路由：首頁、儀表板、機器人管理、指令執行"""

from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from WebUI.app import db
from WebUI.app.models import Robot, Command

bp = Blueprint('core', __name__)

@bp.route('/')
@bp.route('/home')
def home():
    """首頁（簡化版）"""
    return render_template('tiny/home.html.j2')

@bp.route('/dashboard')
@login_required
def dashboard():
    """儀表板（顯示機器人狀態）"""
    robots = Robot.query.filter_by(owner_id=current_user.id).all()
    return render_template('tiny/dashboard.html.j2', robots=robots)

@bp.route('/robots')
@login_required
def robots():
    """機器人列表（JSON API）"""
    robots = Robot.query.filter_by(owner_id=current_user.id).all()
    return jsonify([r.to_dict() for r in robots])

@bp.route('/commands', methods=['POST'])
@login_required
def send_command():
    """發送指令給機器人"""
    data = request.json
    # ... 指令處理邏輯
    return jsonify({"status": "success"})
```

**Step 3: 實作認證路由模組** (1 天)

```python
# WebUI/app/routes_auth_tiny.py
"""認證路由：登入、登出、註冊（簡化版）"""

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user
from WebUI.app import db
from WebUI.app.models import User
from WebUI.app.forms import LoginForm, RegisterForm

bp = Blueprint('auth', __name__)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    """登入（簡化版，移除審計日誌）"""
    if current_user.is_authenticated:
        return redirect(url_for('ui.core.dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect(url_for('ui.core.dashboard'))
        flash('用戶名稱或密碼錯誤')
    
    return render_template('tiny/login.html.j2', form=form)

@bp.route('/logout')
def logout():
    """登出"""
    logout_user()
    return redirect(url_for('ui.auth.login'))
```

**Step 4: 更新 app/__init__.py 註冊 Tiny Blueprint** (0.5 天)

```python
# WebUI/app/__init__.py (新增)

def create_app(config_name='default'):
    # ... 現有程式碼 ...
    
    # 註冊原始 Blueprint（用於 Heavy 版本）
    from WebUI.app import routes
    flask_app.register_blueprint(routes.bp, url_prefix='/')
    
    # 註冊 Tiny Blueprint（用於 PyQt 版本）
    from WebUI.app import routes_tiny
    flask_app.register_blueprint(routes_tiny.bp_tiny)
    
    return flask_app
```

**驗收標準**:
- [ ] routes_tiny.py 基礎架構建立
- [ ] 核心路由模組實作（home, dashboard, robots, commands）
- [ ] 認證路由模組實作（login, logout, register）
- [ ] Blueprint 正確註冊，路由可訪問
- [ ] 單元測試通過（新增 test_routes_tiny.py）

---

### Stage 3: 模板簡化與本地化 (3-4 天) 🔴

**目標**: 建立簡化版模板，移除 CDN 依賴

#### 3.1 模板結構

**建立 templates_tiny/ 目錄**:
```
WebUI/app/templates_tiny/
├── base.html.j2           # 基礎模板（簡化版）
├── home.html.j2           # 首頁
├── login.html.j2          # 登入
├── register.html.j2       # 註冊
├── dashboard.html.j2      # 儀表板
├── robots.html.j2         # 機器人列表
└── partials/              # 可重用組件
    ├── navbar.html.j2
    ├── flash.html.j2
    └── footer.html.j2
```

#### 3.2 Base 模板簡化

**原始 base.html.j2 問題**:
- ❌ 繼承 `bootstrap/base.html`（Flask-Bootstrap）
- ❌ 依賴 CDN 載入 CSS/JS
- ❌ 複雜的導航列與樣式

**Tiny 版本 base.html.j2** (簡化策略):

```html
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Robot Console{% endblock %}</title>
    
    <!-- 本地 Bootstrap CSS -->
    <link rel="stylesheet" href="{{ url_for('static', filename='vendor/bootstrap-5.3.0/css/bootstrap.min.css') }}">
    
    <!-- 本地 Font Awesome -->
    <link rel="stylesheet" href="{{ url_for('static', filename='vendor/fontawesome-6.4.0/css/all.min.css') }}">
    
    <!-- 自訂樣式 -->
    <link rel="stylesheet" href="{{ url_for('static', filename='css/tiny.css') }}">
    
    {% block head %}{% endblock %}
</head>
<body>
    <!-- 導航列 -->
    {% include 'tiny/partials/navbar.html.j2' %}
    
    <!-- Flash 訊息 -->
    {% include 'tiny/partials/flash.html.j2' %}
    
    <!-- 主要內容 -->
    <main class="container mt-4">
        {% block content %}{% endblock %}
    </main>
    
    <!-- 頁尾 -->
    {% include 'tiny/partials/footer.html.j2' %}
    
    <!-- 本地 jQuery -->
    <script src="{{ url_for('static', filename='vendor/jquery-3.7.0/jquery.min.js') }}"></script>
    
    <!-- 本地 Bootstrap JS -->
    <script src="{{ url_for('static', filename='vendor/bootstrap-5.3.0/js/bootstrap.bundle.min.js') }}"></script>
    
    {% block scripts %}{% endblock %}
</body>
</html>
```

**優勢**:
- ✅ 完全本地化，無 CDN 依賴
- ✅ 簡化結構，易於維護
- ✅ 保留基本 Bootstrap 功能
- ✅ 支援響應式設計

#### 3.3 模板實作步驟

**Step 1: 建立 base.html.j2** (0.5 天)
- 定義基礎 HTML 結構
- 配置本地靜態資源路徑
- 建立 block 供子模板使用

**Step 2: 建立可重用 partials** (0.5 天)
- navbar.html.j2 - 簡化導航列
- flash.html.j2 - Flash 訊息顯示
- footer.html.j2 - 頁尾資訊

**Step 3: 實作功能頁面模板** (2 天)
- home.html.j2 - 首頁（歡迎訊息、功能簡介）
- login.html.j2 - 登入表單
- register.html.j2 - 註冊表單
- dashboard.html.j2 - 機器人狀態儀表板
- robots.html.j2 - 機器人列表與操作

**Step 4: 自訂樣式 tiny.css** (1 天)
```css
/* WebUI/app/static/css/tiny.css */

/* 全域變數 */
:root {
    --primary-color: #007bff;
    --secondary-color: #6c757d;
    --success-color: #28a745;
    --danger-color: #dc3545;
    --warning-color: #ffc107;
}

/* 導航列樣式 */
.navbar-tiny {
    background-color: var(--primary-color);
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

/* 儀表板卡片 */
.robot-card {
    border: 1px solid #dee2e6;
    border-radius: 8px;
    padding: 20px;
    margin-bottom: 15px;
    transition: box-shadow 0.3s;
}

.robot-card:hover {
    box-shadow: 0 4px 8px rgba(0,0,0,0.15);
}

/* 狀態指示器 */
.status-online {
    color: var(--success-color);
}

.status-offline {
    color: var(--danger-color);
}

/* 按鈕樣式 */
.btn-tiny {
    padding: 8px 16px;
    border-radius: 4px;
    font-size: 14px;
}

/* 響應式調整 */
@media (max-width: 768px) {
    .robot-card {
        padding: 15px;
    }
}
```

**驗收標準**:
- [ ] base.html.j2 無 CDN 依賴
- [ ] 所有模板繼承自 base.html.j2
- [ ] partials 可重用
- [ ] 功能頁面模板完成
- [ ] 自訂樣式正確載入
- [ ] 響應式設計正常

---

### Stage 4: 靜態資源本地化 (2-3 天) 🟠

**目標**: 下載並配置所有外部依賴至本地

#### 4.1 資源下載清單

**Bootstrap 5.3.0**:
- URL: https://github.com/twbs/bootstrap/releases/download/v5.3.0/bootstrap-5.3.0-dist.zip
- 大小: ~2MB
- 檔案: css/bootstrap.min.css, js/bootstrap.bundle.min.js

**jQuery 3.7.0**:
- URL: https://code.jquery.com/jquery-3.7.0.min.js
- 大小: ~90KB
- 檔案: jquery.min.js

**Font Awesome 6.4.0**:
- URL: https://use.fontawesome.com/releases/v6.4.0/fontawesome-free-6.4.0-web.zip
- 大小: ~5MB
- 檔案: css/all.min.css, webfonts/*

**Blockly (進階指令編輯器)**:
- URL: https://unpkg.com/blockly@latest/blockly.min.js
- 大小: ~500KB
- 檔案: blockly.min.js, msg/zh-hant.js

#### 4.2 目錄結構

```
WebUI/app/static/
├── vendor/                      # 第三方庫
│   ├── bootstrap-5.3.0/
│   │   ├── css/
│   │   │   ├── bootstrap.min.css
│   │   │   └── bootstrap.min.css.map
│   │   └── js/
│   │       ├── bootstrap.bundle.min.js
│   │       └── bootstrap.bundle.min.js.map
│   ├── jquery-3.7.0/
│   │   └── jquery.min.js
│   ├── fontawesome-6.4.0/
│   │   ├── css/
│   │   │   └── all.min.css
│   │   └── webfonts/
│   │       ├── fa-solid-900.woff2
│   │       ├── fa-regular-400.woff2
│   │       └── fa-brands-400.woff2
│   └── blockly/
│       ├── blockly.min.js
│       └── msg/
│           └── zh-hant.js
├── css/
│   └── tiny.css              # 自訂樣式
└── js/
    └── tiny.js               # 自訂 JavaScript
```

#### 4.3 實作步驟

**Step 1: 建立下載腳本** (0.5 天)

```python
# scripts/download_static_assets.py
"""下載並配置靜態資源腳本"""

import os
import requests
import zipfile
from pathlib import Path

STATIC_DIR = Path("WebUI/app/static/vendor")
ASSETS = {
    "bootstrap": {
        "url": "https://github.com/twbs/bootstrap/releases/download/v5.3.0/bootstrap-5.3.0-dist.zip",
        "extract": True
    },
    "jquery": {
        "url": "https://code.jquery.com/jquery-3.7.0.min.js",
        "extract": False
    },
    "fontawesome": {
        "url": "https://use.fontawesome.com/releases/v6.4.0/fontawesome-free-6.4.0-web.zip",
        "extract": True
    },
    "blockly": {
        "url": "https://unpkg.com/blockly@latest/blockly.min.js",
        "extract": False
    }
}

def download_asset(name, config):
    """下載單一資源"""
    print(f"Downloading {name}...")
    response = requests.get(config["url"], stream=True)
    
    if config["extract"]:
        # 下載並解壓縮
        zip_path = STATIC_DIR / f"{name}.zip"
        with open(zip_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(STATIC_DIR / name)
        
        os.remove(zip_path)
    else:
        # 直接下載檔案
        file_path = STATIC_DIR / name / Path(config["url"]).name
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'wb') as f:
            f.write(response.content)
    
    print(f"✓ {name} downloaded")

def main():
    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    
    for name, config in ASSETS.items():
        download_asset(name, config)
    
    print("\n✓ All static assets downloaded successfully!")

if __name__ == "__main__":
    main()
```

**Step 2: 執行下載** (自動化)

```bash
cd /path/to/project
python scripts/download_static_assets.py
```

**Step 3: 驗證資源** (0.5 天)
- 檢查所有檔案是否正確下載
- 驗證檔案完整性（大小、格式）
- 測試本地載入是否正常

**Step 4: 更新 .gitignore** (立即)

```gitignore
# WebUI/app/.gitignore

# 靜態資源（大型第三方庫）
static/vendor/bootstrap-*/
static/vendor/jquery-*/
static/vendor/fontawesome-*/
static/vendor/blockly/

# 保留下載腳本和自訂資源
!static/css/
!static/js/
```

**驗收標準**:
- [ ] 下載腳本可正常運行
- [ ] 所有資源正確下載至 vendor/
- [ ] 模板可正確載入本地資源
- [ ] .gitignore 配置正確
- [ ] 文件說明資源來源與版本

---

### Stage 5: 整合測試與調整 (2-3 天) 🟡

**目標**: 確保 Tiny WebUI 與 PyQt 應用整合無誤

#### 5.1 測試項目

**功能測試**:
- [ ] 首頁正確顯示
- [ ] 登入/登出流程正常
- [ ] 儀表板顯示機器人列表
- [ ] 指令可正常發送
- [ ] 靜態資源載入無錯誤（檢查 Console）

**整合測試**:
- [ ] PyQt 應用可啟動 Flask 服務
- [ ] QtWebEngineView 載入 WebUI 正常
- [ ] QWebChannel 橋接功能正常
- [ ] Cookie/Session 儲存正常
- [ ] 離線模式可用

**效能測試**:
- [ ] 頁面載入時間 < 2 秒
- [ ] 記憶體佔用 < 200MB
- [ ] CPU 使用率 < 5%

#### 5.2 調整與優化

**常見問題修復**:
1. **CORS 問題**: 配置 Flask CORS 允許 127.0.0.1
2. **路徑問題**: 確保靜態資源路徑正確
3. **Session 問題**: 配置 Flask Session 使用檔案儲存

**效能優化**:
1. 壓縮 CSS/JS（可選）
2. 啟用 HTTP 快取
3. 減少不必要的 AJAX 請求

**驗收標準**:
- [ ] 所有功能測試通過
- [ ] 所有整合測試通過
- [ ] 效能指標達標
- [ ] 無 Console 錯誤
- [ ] 文件更新

---

## 📈 時程規劃

### Week 2 (第 2 週)

**Day 1-2: Stage 2 路由拆分**
- Day 1 上午: 建立 routes_tiny.py 基礎架構
- Day 1 下午: 實作核心路由模組（home, dashboard）
- Day 2 上午: 實作認證路由模組（login, logout）
- Day 2 下午: 更新 app/__init__.py，單元測試

**Day 3-4: Stage 3 模板簡化**
- Day 3 上午: 建立 base.html.j2 與 partials
- Day 3 下午: 實作功能頁面模板（home, login）
- Day 4 上午: 實作儀表板與機器人模板
- Day 4 下午: 自訂樣式 tiny.css

**Day 5: Stage 4 靜態資源本地化**
- 上午: 建立下載腳本
- 下午: 執行下載與驗證

### Week 3 (第 3 週)

**Day 1-2: Stage 4 繼續 + Stage 5 整合測試**
- Day 1: 完成 Blockly 本地化，調整路徑
- Day 2 上午: 功能測試
- Day 2 下午: 整合測試（PyQt + Flask）

**Day 3-4: 調整與優化**
- Day 3: 修復測試發現的問題
- Day 4: 效能優化與文件更新

**Day 5: 最終驗收**
- 完整測試流程
- 文件完善
- 準備進入 Week 4 跨平台驗證

---

## 🎯 驗收標準

### 功能完整性
- [ ] 核心路由全部實作（首頁、儀表板、機器人、指令）
- [ ] 認證路由全部實作（登入、登出、註冊）
- [ ] 所有模板無 CDN 依賴
- [ ] 靜態資源完全本地化

### 程式碼品質
- [ ] 程式碼符合 PEP 8 規範
- [ ] 單元測試覆蓋率 > 80%
- [ ] 無 lint 錯誤

### 效能指標
- [ ] 頁面載入時間 < 2 秒
- [ ] 記憶體佔用 < 200MB
- [ ] 靜態資源總大小 < 10MB

### 文件完整性
- [ ] 本文件更新完整
- [ ] API 文件完整
- [ ] 使用者指引更新

---

## 📚 參考文件

- [Phase 3.2 規劃](PHASE3_2_QTWEBVIEW_PLAN.md)
- [Phase 3.2 實作總結](PHASE3_2_IMPLEMENTATION_SUMMARY.md)
- [Phase 3.2 狀態檢查](PHASE3_2_STATUS_CHECK.md)
- [Week 1 進度報告](WEEK1_PROGRESS.md)

---

## 🔄 變更歷史

| 日期 | 版本 | 變更內容 |
|------|------|----------|
| 2026-01-05 | v1.0 | 初始版本，完成研究與規劃 |

---

**建立者**: GitHub Copilot  
**狀態**: 📋 規劃完成，等待執行  
**下一步**: 開始 Stage 2 - 路由拆分與隔離
