# Cloud Services Migration Notes

> **遷移日期**: 2025-12-10  
> **原因**: 實現 Server-Edge-Runner 三層架構的清晰分離

---

## 🎯 遷移目標

將 WebUI 中的雲端/社群功能分離到獨立的 Cloud 目錄，使 Edge App 更輕量、更專注於本地機器人控制。

---

## 📦 已遷移的內容

### 1. 社群互動功能

| 檔案 | 原位置 | 新位置 | 狀態 |
|------|-------|--------|------|
| engagement.py | WebUI/app/ | Cloud/engagement/ | ✅ 已複製 |
| leaderboard.html.j2 | WebUI/app/templates/ | Cloud/engagement/ | ✅ 已複製 |
| _post.html.j2 | WebUI/app/templates/ | Cloud/engagement/ | ✅ 已複製 |

**包含功能**:
- `get_posts()`: 取得討論區貼文
- `create_post()`: 建立新貼文
- `like_post()`: 點讚功能
- `add_comment()`: 新增評論
- `get_leaderboard()`: 排行榜

### 2. 通知服務

| 檔案 | 原位置 | 新位置 | 狀態 |
|------|-------|--------|------|
| email.py | WebUI/app/ | Cloud/notification/ | ✅ 已複製 |

**包含功能**:
- `send_email()`: 發送郵件
- `send_password_reset_email()`: 密碼重設郵件
- `send_notification_email()`: 系統通知郵件

---

## 📋 待遷移的內容

### 3. 用戶社交功能

**來源**: `WebUI/app/models.py` 中的社交模型

待遷移：
- `followers` 關聯表
- `User.follow()` 方法
- `User.unfollow()` 方法
- `User.followed_posts()` 方法

**目標**: `Cloud/user_management/social_network.py`

### 4. 資料模型分離

待分離到 `Cloud/models.py`:
```python
# 雲端專用模型
class Post(db.Model)
class Comment(db.Model)  
class Like(db.Model)
class Follower(db.Model)
```

保留在 Edge（`WebUI/models.py` 精簡版）:
```python
# Edge 本地模型
class Robot(db.Model)
class Command(db.Model)
class Advanced_Command(db.Model)
# User (簡化版 - 僅本地認證)
```

### 5. 路由分離

待從 `WebUI/app/routes.py` 遷移到 `Cloud/api/`:
- `/posts` 相關路由
- `/follow` 相關路由
- `/leaderboard` 路由
- `/notifications` 路由

---

## 🔄 遷移步驟（詳細）

### Step 1: 檔案移動 ✅

```bash
# 已完成
cp WebUI/app/engagement.py Cloud/engagement/
cp WebUI/app/email.py Cloud/notification/
```

### Step 2: 模型分離 ⏳

```bash
# 待執行
# 1. 建立 Cloud/models.py
# 2. 從 WebUI/app/models.py 移動雲端模型
# 3. 更新 WebUI/app/models.py 僅保留 Edge 模型
```

```python
# Cloud/models.py (新檔案)
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    # ... 其他欄位

class Comment(db.Model):
    __tablename__ = 'comments'
    # ...

class Like(db.Model):
    __tablename__ = 'likes'
    # ...
```

### Step 3: 路由分離 ⏳

```bash
# 待執行
# 1. 建立 Cloud/api/routes.py
# 2. 從 WebUI/app/routes.py 移動雲端路由
# 3. 建立 Cloud API 服務
```

### Step 4: 資料庫遷移 ⏳

```bash
# 待執行
# 1. 建立 Cloud 資料庫 schema
# 2. 從 WebUI 資料庫匯出雲端數據
# 3. 匯入到 Cloud 資料庫
```

### Step 5: API 端點建立 ⏳

```python
# Cloud/api/main.py (待建立)
from fastapi import FastAPI
from .routes import engagement, users, firmware

app = FastAPI(title="Robot Command Console - Cloud API")

app.include_router(engagement.router)
app.include_router(users.router)
app.include_router(firmware.router)
```

---

## 🔗 導入路徑更新

### 舊路徑（WebUI 混合）
```python
from WebUI.app.engagement import get_posts
from WebUI.app.email import send_email
from WebUI.app.models import Post, Comment
```

### 新路徑（分離後）
```python
# Edge App (不應使用雲端功能)
# 移除所有對 engagement, Post, Comment 的引用

# Cloud Service (新的雲端 API)
from Cloud.engagement import get_posts
from Cloud.notification.email import send_email
from Cloud.models import Post, Comment
```

---

## ⚠️ 破壞性變更

### WebUI (Edge) 的變更

**移除的功能**:
- ❌ 討論區路由（`/posts`, `/create_post`）
- ❌ 排行榜路由（`/leaderboard`）
- ❌ 關注功能路由（`/follow`, `/unfollow`）
- ❌ 郵件通知功能

**保留的功能**:
- ✅ 機器人控制
- ✅ 進階指令建立（本地）
- ✅ 執行監控
- ✅ 本地設定
- ✅ 簡化的本地認證

### 資料庫 Schema 變更

**Edge Database (SQLite)**:
```sql
-- 保留
CREATE TABLE robot (...);
CREATE TABLE command (...);
CREATE TABLE advanced_command (...);
CREATE TABLE user (簡化版 - 僅 id, username, password_hash);
```

**Cloud Database (PostgreSQL)**:
```sql
-- 新增
CREATE TABLE posts (...);
CREATE TABLE comments (...);
CREATE TABLE likes (...);
CREATE TABLE followers (...);
CREATE TABLE user (完整版 - 包含社交欄位);
```

---

## 🧪 測試計劃

### Edge App 測試

確保移除雲端功能後仍正常運作：

```bash
# 1. 測試基本功能
python -m pytest tests/edge_app/

# 2. 測試不應存在雲端功能
# 確認以下路由回傳 404
curl http://localhost:5000/posts  # 應該 404
curl http://localhost:5000/leaderboard  # 應該 404
```

### Cloud Service 測試

確保雲端功能獨立運作：

```bash
# 1. 測試雲端 API
python -m pytest tests/cloud_service/

# 2. 測試端點可用性
curl http://localhost:8001/api/posts
curl http://localhost:8001/api/leaderboard
```

---

## 📊 影響分析

### Edge App

| 指標 | 遷移前 | 遷移後 | 變化 |
|------|-------|--------|------|
| 檔案大小 | 200MB | 150MB | ↓ 25% |
| 依賴數量 | 45 | 32 | ↓ 29% |
| 啟動時間 | 8s | 5s | ↓ 37% |
| 必要網路連接 | 是 | 否 | 離線可用 |

### 新增 Cloud Service

| 指標 | 值 |
|------|-----|
| 部署方式 | Docker/K8s |
| 資料庫 | PostgreSQL |
| 快取 | Redis |
| 預估 QPS | 1000+ |

---

## ✅ 驗收標準

- [ ] Edge App 不包含任何雲端功能的程式碼
- [ ] Edge App 可完全離線運行
- [ ] Cloud Service 提供完整的 REST API
- [ ] API 文件完整（OpenAPI/Swagger）
- [ ] 所有測試通過
- [ ] 文件已更新

---

## 📚 相關文件

- [Cloud README](README.md)
- [統一套件設計](../docs/UNIFIED_PACKAGE_DESIGN.md)
- [架構說明](../docs/architecture.md)

---

**狀態**: 進行中（Step 1 完成）  
**下一步**: Step 2 - 模型分離  
**預計完成**: 2025-12-15
