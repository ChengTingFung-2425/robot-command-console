# Cloud

This folder contains modules and components related to cloud-based operations, such as user management, notifications, and firmware repositories.

---

## Recent Updates

### 2026-01-28
- **MCP Isolation**: MCP services have been moved to the Edge folder to align with edge-related responsibilities.
- **Integration Completed**: Notification and firmware repository services remain in the Cloud folder and have been fully integrated.

---

## 📋 概述

本目錄包含從 WebUI 分離出來的雲端/社群功能，這些功能屬於 Cloud/Server Layer，不應包含在 Edge App 中。

### 為什麼分離？

根據 Server-Edge-Runner 三層架構：
- **Edge Layer**: 本地功能，離線可用（機器人控制、本地設定）
- **Cloud Layer**: 雲端功能，需要網路連接（社群、共享、分析）

分離的好處：
1. **減小 Edge App 體積**: 移除不必要的依賴
2. **清晰的職責分離**: Edge 專注本地控制，Cloud 專注社群與共享
3. **獨立部署**: Cloud 服務可以獨立擴展與更新
4. **離線可用**: Edge App 不依賴雲端服務即可運行

---

## 📁 目錄結構

```
Cloud/
├── README.md                    # 本文件
├── engagement/                  # 社群互動功能
├── user_management/            # 用戶管理（雲端）
├── firmware_repository/        # 固件倉庫
├── notification/               # 通知服務
├── shared_commands/            # 進階指令共享（✅ 已實作）
└── analytics/                  # 數據分析（未來）
```

---

## 🔄 已移動的功能

### 1. 社群互動（Engagement）

**來源**: `WebUI/app/engagement.py`  
**目標**: `Cloud/engagement/`

包含功能：
- 討論區（Posts）
- 評論系統（Comments）
- 點讚功能（Likes）
- 排行榜（Leaderboard）

### 2. 通知服務（Notification）

**來源**: `WebUI/app/email.py`  
**目標**: `Cloud/notification/`

包含功能：
- 郵件通知
- 密碼重設郵件
- 系統通知

### 3. 用戶管理（User Management）

**待移動功能**：
- 用戶註冊系統
- 社交網路（Follow/Followers）
- 用戶個人頁面
- 信譽與評級系統

### 4. 固件倉庫（Firmware Repository）

**待移動功能**：
- 固件上傳/下載
- 版本管理
- 更新推送

### 5. 進階指令共享（Advanced Command Sharing）✅

**狀態**: ✅ 已實作完成

**來源**: 新功能  
**目標**: `Cloud/shared_commands/`

包含功能：
- 指令上傳與存儲
- 搜尋與篩選
- 下載與同步
- 評分系統
- 留言討論
- 精選與熱門指令
- 同步日誌

**相關文件**：
- [shared_commands/README.md](shared_commands/README.md) - API 文件
- [docs/features/advanced-command-sharing.md](../docs/features/advanced-command-sharing.md) - 功能說明
- [Edge/cloud_sync/README.md](../Edge/cloud_sync/README.md) - Edge 同步模組

---

## 🏗️ 雲端服務架構

### 部署模式

```
┌─────────────────────────────────────────────────────────┐
│                   Cloud Services                         │
│  ┌────────────────────────────────────────────────────┐ │
│  │           FastAPI / Flask REST API                  │ │
│  │  • /api/engagement/* - 社群功能                     │ │
│  │  • /api/users/* - 用戶管理                          │ │
│  │  • /api/firmware/* - 固件倉庫                       │ │
│  │  • /api/notifications/* - 通知服務                  │ │
│  └────────────────────────────────────────────────────┘ │
│                          │                               │
│                          │ HTTPS                         │
│  ┌────────────────────────────────────────────────────┐ │
│  │              Database (PostgreSQL)                  │ │
│  │  • Users, Posts, Comments, Likes                    │ │
│  │  • Firmware Metadata                                │ │
│  │  • Analytics Data                                   │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │         Object Storage (S3/MinIO)                   │ │
│  │  • Firmware Files                                   │ │
│  │  • User Avatars                                     │ │
│  │  • Attachments                                      │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
                          │
                    HTTPS/WSS
                          │
┌─────────────────────────────────────────────────────────┐
│                   Edge Applications                      │
│  • Unified Edge App                                     │
│  • Electron App (Heavy)                                 │
│  • PyQt App (Tiny)                                      │
│                                                          │
│  可選連接到雲端服務以獲取：                               │
│  - 進階指令共享與下載                                     │
│  - 固件更新                                              │
│  - 社群互動                                              │
└─────────────────────────────────────────────────────────┘
```

---

## 🚀 使用方式

### 作為獨立雲端服務部署

```bash
# 安裝依賴
cd Cloud
pip install -r requirements.txt

# 啟動雲端服務
python -m cloud_service.main

# 或使用 Docker
docker-compose up -d
```

### 使用 Terraform 建立多雲端儲存資源

```bash
cd Cloud/terraform
cp terraform.tfvars.example terraform.tfvars

# 依實際環境填入 gcp_project / azure_subscription_id 等值後再執行
terraform init
terraform plan
```

目前 Terraform 組態會：

- 在 AWS 建立一個 S3 bucket
- 在 GCP 建立一個 Cloud Storage bucket
- 在 Azure 建立一個 Resource Group 與 Storage Account

如需調整名稱前綴或區域，可修改 `terraform.tfvars` 內對應變數。

### Edge App 連接到雲端（可選）

```yaml
# unified-edge-app/config.yaml
cloud:
  enabled: true
  api_url: "https://cloud.example.com/api"
  api_key: "your-api-key"
  
  features:
    sync_commands: true      # 同步進階指令
    firmware_updates: true   # 固件自動更新
    analytics: false         # 使用情況分析
```

---

## 📊 功能對照表

| 功能 | Edge App | Cloud Service | 說明 |
|------|----------|---------------|------|
| 機器人控制 | ✅ | ❌ | 本地即時控制 |
| 進階指令建立 | ✅ | ✅ | Edge 建立，可選上傳雲端共享 |
| 進階指令共享 | ❌ | ✅ | 雲端共享與評分 |
| 執行監控 | ✅ | ❌ | 本地監控 |
| 討論區 | ❌ | ✅ | 雲端社群功能 |
| 排行榜 | ❌ | ✅ | 雲端統計 |
| 用戶註冊 | 簡化版 | ✅ | Edge 使用本地認證 |
| 固件更新 | ✅ | ✅ | Edge 本地管理，可從雲端下載 |
| 郵件通知 | ❌ | ✅ | 雲端服務 |

---

## 🔐 安全考量

### 認證與授權

- **Edge App**: 本地認證（簡化或無認證）
- **Cloud Service**: OAuth2/JWT 認證，完整 RBAC

### 數據隱私

- **Edge 數據**: 完全本地，不上傳
- **Cloud 數據**: 用戶同意後才上傳共享內容
- **可選同步**: 用戶控制哪些數據同步到雲端

---

## 📝 遷移指南

### 從 WebUI 遷移功能到 Cloud

1. **識別雲端功能**:
   ```bash
   # 檢查 WebUI 中的社群功能
   grep -r "Post\|Comment\|Follower\|Like" WebUI/app/
   ```

2. **移動檔案**:
   ```bash
   # 移動 Python 模組
   mv WebUI/app/engagement.py Cloud/engagement/
   
   # 移動模板
   mv WebUI/app/templates/*post* Cloud/engagement/templates/
   ```

3. **更新導入路徑**:
   ```python
   # 舊路徑
   from WebUI.app.engagement import get_posts
   
   # 新路徑
   from Cloud.engagement import get_posts
   ```

4. **更新資料模型**:
   ```python
   # 分離雲端模型到 Cloud/models.py
   class Post(db.Model):
       # 雲端專用模型
       pass
   ```

---

## 🔄 待辦事項

- [ ] **Phase 1: 基礎分離**
  - [x] 移動 engagement.py
  - [x] 移動 email.py
  - [x] 移動相關模板
  - [ ] 移動用戶社交功能（Follow/Followers）
  - [ ] 分離資料模型（User, Post, Comment, Like）

- [ ] **Phase 2: Cloud API 建立**
  - [ ] 建立 REST API 端點
  - [ ] 實作認證機制（OAuth2）
  - [ ] 建立 API 文件（OpenAPI）

- [ ] **Phase 3: Edge ↔ Cloud 整合**
  - [ ] 實作可選的雲端連接
  - [ ] 進階指令同步功能
  - [ ] 固件更新服務

- [ ] **Phase 4: 部署與測試**
  - [ ] Docker 容器化
  - [ ] Kubernetes 部署配置
  - [ ] 負載測試與優化

---

## 📚 相關文件

- [架構說明](../docs/architecture.md)
- [權威規格](../docs/proposal.md)
- [統一套件設計](../docs/UNIFIED_PACKAGE_DESIGN.md)
- [WebUI 模組說明](../WebUI/Module.md)

---

## 🤝 貢獻

如需新增雲端功能或改進現有功能，請：

1. 在 `Cloud/` 目錄下新增對應模組
2. 確保與 Edge App 保持清晰分離
3. 提供 API 文件與範例
4. 撰寫單元測試

---

**建立日期**: 2025-12-10  
**狀態**: 初始版本  
**維護者**: Robot Command Console Team
