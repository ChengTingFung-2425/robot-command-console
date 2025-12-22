# 威脅模型 (Threat Model)

## 概述

本文件描述 Robot Command Console 系統的威脅模型，識別潛在的安全威脅並提出相應的緩解措施。

> **最後更新**：2025-12-22  
> **架構版本**：Phase 3 (Server-Edge-Runner 三層架構) + Phase 2.1 (Edge Token Cache)  
> **狀態**：✅ 包含審計日誌系統、Edge Token Cache 與 Edge 部署安全考量

## 系統架構概覽

Robot Command Console 採用 **Server-Edge-Runner 三層架構**，元件分布如下：

### Server 環境（雲端/伺服器）
- **MCP Service (FastAPI)**: 提供 REST API 和 WebSocket 端點
- **WebUI (Flask)**: Web 管理介面、進階指令共享、用戶討論區
- **集中式資料庫**: 使用者資料、審計日誌、進階指令庫
- **特點**: 高可用性、集中管理、強大運算資源

### Edge 環境（本地/邊緣節點）
- **Electron App / QtWebView App**: 桌面應用程式封裝
- **Flask Service**: 本地 API 服務與 WebUI
- **Robot Service**: 本地佇列系統、指令處理器
- **LLM Provider Manager**: 本地 LLM 整合（Ollama, LM Studio）
- **本地資料庫**: 離線快取、審計日誌本地副本
- **特點**: 
  - **低延遲處理**：直接與機器人通訊，減少網路往返
  - **離線支援**：網路中斷時仍可運作
  - **資源受限**：記憶體與運算能力有限
  - **安全隔離**：Edge 資料不應無條件信任

### Runner 環境（機器人執行層）
- **Robot-Console**: 動作執行器、協定適配器
- **特點**: 最小權限、沙箱執行、安全機制

## 核心安全原則

### 1. 前端不可信任原則 (Zero Trust Frontend)

**原則**: **所有來自前端（包括 Edge WebUI 和 Electron App）的輸入都不可信任，必須在後端進行完整驗證。**

**適用範圍**:
- ✅ 所有 API 請求參數
- ✅ WebSocket 訊息
- ✅ 檔案上傳
- ✅ 使用者輸入的指令與配置

**實施措施**:
- ✅ 後端強制執行 JSON Schema 驗證（使用 Pydantic）
- ✅ 不依賴前端的任何驗證或清理
- ✅ 假設前端可能被竄改或繞過
- ✅ 所有業務邏輯在後端執行
- ✅ 前端僅作為展示層，不執行安全關鍵邏輯

**範例威脅場景**:
- 攻擊者修改 Electron App 前端代碼繞過 UI 限制
- 瀏覽器開發者工具修改請求參數
- 中間人攻擊修改傳輸中的資料

### 2. Edge-Server 信任邊界

**Edge 環境特性**:
- **延遲敏感**: 機器人控制需要即時回應（<100ms）
- **記憶體受限**: Edge 設備可能僅有 4-8GB RAM
- **離線優先**: 必須在無網路時運作
- **物理安全較弱**: Edge 設備可能暴露於物理攻擊

**安全影響**:
- ⚠️ Edge 環境的資料和請求不應自動信任
- ⚠️ Edge→Server 同步需要完整驗證
- ⚠️ Server→Edge 推送需要驗證與授權
- ⚠️ 審計日誌需要雙向同步與完整性檢查

## 威脅分類

我們使用 STRIDE 模型來分類威脅：
- **S**poofing (欺騙)
- **T**ampering (篡改)
- **R**epudiation (否認)
- **I**nformation Disclosure (資訊洩露)
- **D**enial of Service (拒絕服務)
- **E**levation of Privilege (權限提升)

## 識別的威脅

### 0. 前端資料信任威脅 (NEW - 最高優先級)

#### 0.1 前端驗證繞過 (Tampering, Elevation of Privilege)

**威脅描述**: 攻擊者修改前端代碼或使用開發者工具繞過前端驗證，直接發送惡意請求到後端。

**風險等級**: 🔴 極高

**影響範圍**: 
- Edge WebUI (Electron/QtWebView)
- Server WebUI (瀏覽器)
- API 客戶端

**攻擊場景**:
- 修改 Electron App 的 JavaScript 代碼移除驗證邏輯
- 使用瀏覽器開發者工具修改表單輸入限制
- 直接使用 curl/Postman 發送未驗證的 API 請求
- 修改前端 token 或權限檢查邏輯

**緩解措施**:
- ✅ **後端強制驗證所有輸入**（Pydantic models）
- ✅ **不依賴前端驗證**（視為 UX 功能，非安全功能）
- ✅ **JSON Schema 嚴格驗證**所有請求
- ✅ **業務邏輯完全在後端執行**
- ✅ **權限檢查在後端每個端點執行**
- ✅ **審計日誌記錄所有後端驗證失敗**
- ⚠️ 建議：實施請求簽名防止參數篡改（未來增強）

**實施狀態**: ✅ 已實施
- AuthManager 在每個請求驗證 JWT
- Pydantic models 驗證所有 API 輸入
- JSON Schema 驗證指令結構
- RBAC 權限在後端檢查

#### 0.2 前端資料注入攻擊 (Tampering, Information Disclosure)

**威脅描述**: 攻擊者通過前端注入惡意資料（XSS、SQL 注入、指令注入）。

**風險等級**: 🔴 高

**攻擊場景**:
- 在機器人名稱中注入 `<script>` 標籤進行 XSS
- 在指令參數中注入 SQL 或系統指令
- 上傳包含惡意代碼的檔案（固件、進階指令）

**緩解措施**:
- ✅ **輸入清理**: 使用 `html.escape()` 清理所有顯示內容
- ✅ **參數化查詢**: SQLAlchemy ORM 防止 SQL 注入
- ✅ **白名單驗證**: 僅允許預定義的動作和參數
- ✅ **檔案類型驗證**: 嚴格檢查上傳檔案
- ✅ **長度限制**: 所有輸入欄位有最大長度
- ✅ **正則表達式驗證**: 格式驗證（email, username等）

#### 0.3 Edge 資料篡改威脅 (Tampering)

**威脅描述**: 攻擊者獲得 Edge 設備物理訪問，篡改本地資料庫、配置或日誌。

**風險等級**: 🟠 中高

**Edge 環境特有風險**:
- Edge 設備可能在無監控環境（工廠、倉庫）
- 物理安全較弱，可能被竊取或篡改
- 本地資料庫可直接訪問（SQLite）
- 配置檔案可能被修改

**緩解措施**:
- ✅ **資料完整性檢查**: 審計日誌包含 hash/signature
- ✅ **Server 驗證**: Edge 資料同步到 Server 時重新驗證
- ✅ **不信任 Edge 來源**: 即使來自 Edge，仍需完整驗證
- ⚠️ 建議：本地資料庫加密（未來增強）
- ⚠️ 建議：配置檔案簽名驗證（未來增強）
- ⚠️ 建議：TPM 模組整合（硬體安全，未來增強）

#### 0.4 WebUI Session 劫持 (Spoofing, Elevation of Privilege)

**威脅描述**: 攻擊者竊取或偽造 WebUI 的 session cookie 或 JWT token。

**風險等級**: 🔴 高

**攻擊場景**:
- XSS 攻擊竊取存儲在 JavaScript 的 token
- 網路嗅探獲取 cookie（HTTP）
- 本地存儲（localStorage）被惡意腳本讀取

**緩解措施**:
- ✅ **HttpOnly cookies**: 防止 JavaScript 訪問
- ✅ **Secure flag**: HTTPS only（生產環境）
- ✅ **SameSite attribute**: 防止 CSRF
- ✅ **短期 token**: 24 小時過期
- ✅ **Token rotation**: 提供更新機制
- ⚠️ 建議：HTTPS 強制（生產環境必需）
- ⚠️ 建議：Refresh token 機制（未來增強）

### 1. 認證和授權威脅

#### 1.1 JWT Token 竊取 (Spoofing, Information Disclosure)

**威脅描述**: 攻擊者可能通過中間人攻擊或惡意軟體竊取 JWT token。

**風險等級**: 高

**緩解措施**:
- ✅ 使用 HTTPS 加密所有通訊（生產環境）
- ✅ 實施短期 token（預設 24 小時）
- ✅ 提供 token rotation 機制
- ✅ 在 token 中包含過期時間
- ⚠️ 建議實施 refresh token 機制（未來增強）
- ⚠️ 建議實施 token 黑名單（未來增強）

#### 1.2 密碼暴力破解 (Spoofing)

**威脅描述**: 攻擊者嘗試通過暴力破解猜測使用者密碼。

**風險等級**: 🟠 中

**緩解措施**:
- ✅ 使用 bcrypt 進行密碼雜湊（包含隨機鹽值）
- ✅ 強制密碼最小長度（8 字元）
- ✅ **審計日誌記錄所有登入失敗**（新增）
- ⚠️ 建議實施登入速率限制（未來增強）
- ⚠️ 建議實施帳號鎖定機制（未來增強）

#### 1.3 權限提升 (Elevation of Privilege)

**威脅描述**: 低權限使用者嘗試執行需要更高權限的操作。

**風險等級**: 🔴 高

**Edge 環境額外風險**: Edge WebUI 可能被修改以隱藏或繞過權限檢查

**緩解措施**:
- ✅ 實施基於角色的存取控制 (RBAC)
- ✅ 四種角色：admin、auditor、operator、viewer
- ✅ **在後端每個操作前檢查權限**（不信任前端）
- ✅ 記錄權限拒絕事件到審計日誌
- ✅ 最小權限原則（預設為 viewer 角色）
- ✅ **審計日誌查詢僅限 admin/auditor**（新增）

#### 1.4 Token 過期未檢查 (Spoofing)

**威脅描述**: 系統接受已過期的 token，允許未授權存取。

**風險等級**: 高

**緩解措施**:
- ✅ 在 AuthManager 中實施 token 過期檢查
- ✅ 記錄過期 token 使用嘗試到審計日誌
- ✅ 返回明確的錯誤訊息

### 2. 資料安全威脅

#### 2.1 敏感資料洩露 (Information Disclosure)

**威脅描述**: 敏感資料（密碼、token、秘密）可能在日誌、錯誤訊息或儲存中洩露。

**風險等級**: 高

**緩解措施**:
- ✅ 密碼使用 bcrypt 雜湊，從不記錄明文密碼
- ✅ 使用結構化 JSON 日誌，避免意外記錄敏感欄位
- ✅ 錯誤訊息不洩露內部實作細節
- ✅ 實施秘密儲存抽象層
- ⚠️ 建議在生產環境使用外部秘密管理服務（未來增強）

#### 2.2 資料庫注入 (Tampering)

**威脅描述**: 攻擊者通過構造特殊輸入來操作資料庫查詢。

**風險等級**: 中

**緩解措施**:
- ✅ 使用 SQLAlchemy ORM 防止 SQL 注入
- ✅ 使用 Pydantic 進行輸入驗證
- ✅ 參數化查詢

#### 2.3 指令注入 (Tampering)

**威脅描述**: 惡意指令可能被注入到機器人執行層。

**風險等級**: 高

**緩解措施**:
- ✅ 使用 JSON Schema 驗證所有指令請求
- ✅ 白名單允許的動作和參數
- ✅ 在執行前驗證機器人能力
- ✅ 實施指令超時機制

### 3. 可用性威脅

#### 3.1 拒絕服務攻擊 (Denial of Service)

**威脅描述**: 攻擊者通過大量請求使服務不可用。

**風險等級**: 中

**緩解措施**:
- ✅ 實施請求追蹤和監控
- ✅ 佇列大小限制（預設 1000）
- ✅ 指令超時機制
- ✅ Prometheus metrics 監控請求量和錯誤率
- ⚠️ 建議實施速率限制（未來增強）
- ⚠️ 建議使用反向代理進行 DDoS 防護（部署建議）

#### 3.2 資源耗盡 (Denial of Service)

**威脅描述**: 惡意或錯誤的請求消耗過多系統資源。

**風險等級**: 中

**緩解措施**:
- ✅ 實施佇列最大大小限制
- ✅ 工作者數量限制
- ✅ 指令超時機制（預設 10 秒）
- ✅ WebSocket 連線數監控
- ⚠️ 建議實施記憶體和 CPU 使用限制（未來增強）

### 4. 通訊安全威脅

#### 4.1 中間人攻擊 (Spoofing, Information Disclosure)

**威脅描述**: 攻擊者攔截和修改客戶端與伺服器之間的通訊。

**風險等級**: 高

**緩解措施**:
- ⚠️ 開發環境使用 HTTP（已知風險）
- ✅ 生產環境強制使用 HTTPS
- ✅ CORS 設定限制允許的來源
- ⚠️ 建議實施憑證釘扎 (Certificate Pinning)（未來增強）

#### 4.2 WebSocket 攻擊 (Tampering, Denial of Service)

**威脅描述**: 攻擊者利用 WebSocket 連線進行攻擊。

**風險等級**: 中

**緩解措施**:
- ✅ WebSocket 連線需要認證（除了特定端點）
- ✅ 監控活動 WebSocket 連線數
- ✅ 實施連線超時和心跳機制
- ✅ 記錄 WebSocket 事件

### 5. 審計和追蹤威脅

#### 5.1 日誌篡改 (Repudiation, Tampering)

**威脅描述**: 攻擊者可能修改或刪除日誌以隱藏活動。

**風險等級**: 中

**緩解措施**:
- ✅ 使用結構化 JSON 日誌格式
- ✅ 包含 correlation ID 和 trace ID
- ⚠️ 建議將日誌發送到集中式日誌系統（部署建議）
- ⚠️ 建議實施日誌完整性檢查（未來增強）

#### 5.2 不可否認性 (Repudiation)

**威脅描述**: 使用者否認執行了某些操作。

**風險等級**: 低

**緩解措施**:
- ✅ 所有敏感操作記錄到審計日誌
- ✅ 審計事件包含 user_id、action、timestamp
- ✅ Token 驗證失敗記錄到審計日誌
- ✅ 權限檢查失敗記錄到審計日誌

## 信任邊界

### 核心原則：零信任前端 (Zero Trust Frontend)

**所有前端資料（包括 Edge 和 Server WebUI）視為不可信任**

```
┌─────────────────────────────────────────────────────────┐
│  不可信任區域 (Untrusted Zone)                            │
│  • 前端 JavaScript/UI                                    │
│  • 瀏覽器/Electron 環境                                   │
│  • 使用者輸入                                             │
│  • Edge 本地資料庫                                        │
└────────────────┬────────────────────────────────────────┘
                 │ HTTPS + JWT
                 │ 完整後端驗證
┌────────────────▼────────────────────────────────────────┐
│  信任邊界 (Trust Boundary)                               │
│  • 後端 API 驗證層                                       │
│  • AuthManager (JWT + RBAC)                            │
│  • Pydantic/JSON Schema 驗證                            │
└────────────────┬────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────┐
│  半信任區域 (Semi-Trusted Zone)                          │
│  • 後端業務邏輯                                          │
│  • 經驗證的指令                                          │
│  • 審計日誌系統                                          │
└─────────────────────────────────────────────────────────┘
```

### 信任邊界定義

#### 1. 外部信任邊界（不可信任）
1. **前端 ↔ 後端 API**
   - ⚠️ **零信任**: 所有前端資料必須完整驗證
   - 保護: JWT 認證 + Pydantic 驗證 + RBAC
   - 通訊: HTTPS（生產環境）
   
2. **Edge 環境 ↔ Server 環境**
   - ⚠️ **零信任**: Edge 資料可能被篡改
   - 保護: 雙向認證 + 資料完整性檢查 + 重新驗證
   - 同步: 審計日誌、配置、進階指令
   
3. **網際網路 ↔ API 閘道**
   - ⚠️ 不可信任: 所有外部請求
   - 保護: 認證 + 速率限制（建議） + DDoS 防護（建議）

#### 2. 內部信任邊界（條件信任）
1. **經驗證的後端 ↔ 資料庫**
   - ✅ 條件信任: 僅經過驗證的資料
   - 保護: ORM (SQLAlchemy) + 參數化查詢
   
2. **MCP Service ↔ Robot Service**
   - ✅ 條件信任: 內部通訊
   - 保護: 仍需 JSON Schema 驗證
   
3. **佇列系統 ↔ 工作者**
   - ✅ 條件信任: 信任邊界內
   - 保護: 契約驗證 + 超時機制

### Edge-Server 信任模型

#### Edge 環境風險特徵
- 🔴 **物理訪問風險**: 設備可能被竊取或篡改
- 🔴 **記憶體受限**: 4-8GB RAM，複雜驗證受限
- 🟠 **延遲敏感**: 需要快速回應（<100ms），安全檢查要輕量
- 🟠 **離線運作**: 無法即時驗證 Server 端資料
- 🟡 **本地儲存**: SQLite 資料庫可直接訪問

#### Edge → Server 同步安全
```python
# Edge 發送審計日誌到 Server
# Server 必須重新驗證，不信任 Edge 資料

def sync_audit_logs_from_edge(edge_logs: List[Dict]):
    for log in edge_logs:
        # ❌ 錯誤: 直接信任 Edge 資料
        # db.session.add(AuditLog(**log))
        
        # ✅ 正確: 重新驗證
        validated_log = AuditLogSchema.validate(log)  # Pydantic 驗證
        if verify_log_signature(log):  # 完整性檢查
            if verify_user_exists(validated_log.user_id):  # 業務邏輯驗證
                db.session.add(AuditLog(**validated_log))
```

#### Server → Edge 推送安全
- ✅ Edge 必須驗證 Server 推送的資料
- ✅ 使用簽名驗證資料來源
- ⚠️ Edge 應定期與 Server 同步配置並驗證一致性

### 資料流安全分類

#### 🔴 絕對不可信任（Always Validate）
- 所有前端輸入（表單、API 請求、WebSocket 訊息）
- Edge 本地資料庫內容
- 檔案上傳
- URL 參數與 Query String
- Cookie 與 Session（需驗證 signature）

#### 🟠 條件信任（Verify Then Trust）
- 後端間通訊（MCP ↔ Robot Service）
- 已驗證的 JWT token
- Server 資料庫資料（需檢查完整性）

#### 🟢 可信任（Internal Only）
- 環境變數（JWT_SECRET, APP_TOKEN）
- 後端內部函數調用
- 系統配置（非使用者可修改）

## 資料流安全

### 高價值資料流
1. **使用者認證資訊**: username, password → AuthManager → Token
   - 保護：bcrypt 雜湊、HTTPS
2. **JWT Token**: Client ↔ Server
   - 保護：短期有效、rotation、HTTPS
3. **機器人指令**: Client → MCP → Robot
   - 保護：認證、授權、驗證、審計

### 敏感資料儲存
1. **密碼雜湊**: 記憶體（AuthManager.users）
   - 保護：bcrypt、不持久化（目前）
2. **JWT Secret**: 環境變數 (MCP_JWT_SECRET)
   - 保護：秘密儲存抽象、環境隔離
3. **APP_TOKEN**: 環境變數
   - 保護：秘密儲存抽象、環境隔離

## 攻擊面分析

### 暴露的端點
1. **公開端點（無需認證）**:
   - `/health`
   - `/metrics`
   - `/auth/login`
   - 風險：有限，但需防止濫用

2. **認證端點（需要認證）**:
   - 所有其他 API 端點
   - 風險：取決於認證機制強度

3. **WebSocket 端點**:
   - `/api/events/subscribe`
   - `/api/media/stream/{robot_id}`
   - 風險：資源消耗、DoS

### 暴露的資料
1. **錯誤訊息**: 可能洩露系統資訊
2. **API 回應**: 可能包含敏感資訊
3. **日誌**: 可能包含除錯資訊

## 緩解優先級

### 🔴 關鍵安全原則（必須遵守）
- ✅ **零信任前端**: 所有前端資料必須後端驗證
- ✅ **Edge 資料不可信**: Edge → Server 同步需完整驗證
- ✅ JWT token 驗證和過期檢查
- ✅ 基於角色的存取控制 (RBAC)
- ✅ 密碼雜湊 (bcrypt)
- ✅ 輸入驗證 (Pydantic/JSON Schema)
- ✅ **審計日誌系統**（新增，包含登入/登出/權限拒絕）
- ✅ 指令超時機制

### 🟠 短期改進（建議盡快實施）
- ⚠️ **HTTPS 強制**（生產環境必需）
- ⚠️ 速率限制（防止暴力破解與 DoS）
- ⚠️ 登入失敗鎖定
- ⚠️ Refresh token 機制
- ⚠️ **Edge 資料加密**（本地資料庫）
- ⚠️ **審計日誌完整性檢查**（hash/signature）
- ⚠️ 集中式日誌管理

### 🟡 長期改進（未來增強）
- ⚠️ Token 黑名單
- ⚠️ 外部秘密管理服務整合
- ⚠️ 日誌完整性鏈（blockchain-style）
- ⚠️ 憑證釘扎 (Certificate Pinning)
- ⚠️ 進階 DoS 防護
- ⚠️ TPM 模組整合（硬體安全）
- ⚠️ Edge 設備證明 (Device Attestation)

## Edge 環境特殊考量

### 記憶體與效能限制

**約束條件**:
- 可用記憶體: 4-8GB（扣除 OS 與其他服務）
- 目標回應時間: <100ms（機器人控制）
- 離線運作: 需要本地快取與佇列

**安全影響**:
- ✅ 輕量級驗證: 使用快速的 Pydantic 驗證而非複雜規則引擎
- ✅ 本地快取限制: 最多快取 1000 筆指令歷史
- ✅ 日誌輪轉: 自動壓縮與清理舊日誌
- ⚠️ 資源監控: 監控記憶體使用，防止 OOM
- ⚠️ 降級策略: 記憶體不足時停用非關鍵功能

### 延遲敏感性

**需求**:
- 機器人控制: <100ms
- UI 回應: <200ms
- 批次操作: <5s

**安全權衡**:
- ✅ JWT 驗證快取（短期，5 分鐘）
- ✅ 本地 RBAC 快取（避免每次查詢資料庫）
- ⚠️ 異步審計: 日誌寫入異步執行，不阻塞主流程
- ⚠️ 背景同步: Edge → Server 同步在背景執行

### 離線安全策略

**離線期間行為**:
- ✅ 使用本地快取的權限與配置
- ✅ 本地審計日誌累積，重連後同步
- ✅ 本地指令佇列繼續運作
- ⚠️ 限制離線期間的敏感操作（如新增使用者）
- ⚠️ 重連後強制重新驗證 JWT token

**重連安全檢查**:
```python
def on_server_reconnect():
    # 1. 驗證本地配置未被篡改
    verify_local_config_integrity()
    
    # 2. 同步時鐘（防止 replay attack）
    sync_system_time()
    
    # 3. 重新驗證 JWT token
    refresh_jwt_token()
    
    # 4. 同步審計日誌（Server 驗證）
    sync_audit_logs_to_server()
    
    # 5. 拉取最新配置與權限
    pull_latest_config()
```

## 假設和依賴

### 安全假設
1. **前端不可信任**: 所有前端（Web、Electron）可能被篡改
2. **Edge 環境部分可信**: Edge 資料需Server端重新驗證
3. **生產環境使用 HTTPS**: 所有 Server 通訊加密
4. **網路環境基本保護**: 防火牆、網路隔離
5. **作業系統和依賴套件保持更新**: 及時修補已知漏洞
6. **秘密安全管理**: JWT_SECRET、APP_TOKEN 通過環境變數或秘密管理服務

### 環境假設

#### Server 環境
- 高可用性（99.9% uptime）
- 充足運算資源（16GB+ RAM, 4+ CPU cores）
- 穩定網路連線
- 專業運維團隊
- 完整備份與災難恢復

#### Edge 環境
- 🟠 **記憶體受限**: 4-8GB RAM
- 🟠 **延遲敏感**: 需要 <100ms 回應
- 🟠 **間歇性網路**: 可能離線運作數小時至數天
- 🟠 **物理安全較弱**: 設備可能暴露於未受保護環境
- 🟠 **有限運維**: 可能無專業人員現場維護

### 外部依賴
1. **Python 套件**: Flask, FastAPI, Pydantic, PyJWT, passlib, SQLAlchemy
   - 風險: 供應鏈攻擊、已知漏洞
   - 緩解: 定期更新、依賴掃描、SBOM 管理
   
2. **JavaScript 依賴**: Electron, Node.js
   - 風險: npm 套件漏洞、惡意套件
   - 緩解: npm audit、lock 檔案、最小化依賴
   
3. **作業系統**: 檔案系統權限、程序隔離
   - 風險: OS 漏洞、kernel 漏洞
   - 緩解: 系統更新、最小權限運行、容器化

4. **資料庫**: PostgreSQL (Server)、SQLite (Edge)
   - 風險: 資料庫漏洞、權限設定錯誤
   - 緩解: 定期更新、最小權限、加密（建議）

## 合規性考量

### 資料保護
- 密碼使用業界標準雜湊 (bcrypt)
- 審計日誌記錄敏感操作
- 最小權限原則

### 安全標準
- OWASP Top 10 主要威脅已考慮
- 適用於 IoT 和機器人控制系統的安全最佳實踐

## 定期審查

此威脅模型應該：
1. **每季度審查一次**
2. **在重大架構變更後更新**（如 Phase 3 Edge 架構）
3. **在發現新威脅後更新**
4. **在安全事件後更新**
5. **在新增 Edge 部署場景後評估**

### 審查清單
- [ ] 檢查所有「⚠️ 建議」項目的實施進度
- [ ] 評估新增的 API 端點安全性
- [ ] 審查審計日誌覆蓋範圍
- [ ] 驗證 Edge 與 Server 同步安全性
- [ ] 測試前端驗證繞過場景
- [ ] 檢查依賴套件漏洞（npm audit, pip-audit）

## 版本歷史

| 日期 | 版本 | 變更說明 |
|------|------|----------|
| 2025-11-20 | 1.0 | 初始版本 |
| 2025-12-17 | 2.0 | **重大更新**：<br>• 新增零信任前端原則<br>• 新增 Edge-Server 架構安全考量<br>• 新增審計日誌系統威脅分析<br>• 新增 Edge 環境特殊限制（延遲、記憶體）<br>• 強調前端資料不可信任原則<br>• 更新信任邊界模型 |

## 參考資源

- [OWASP Threat Modeling](https://owasp.org/www-community/Threat_Modeling)
- [Microsoft STRIDE](https://docs.microsoft.com/en-us/azure/security/develop/threat-modeling-tool-threats)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [OWASP Top 10 2021](https://owasp.org/www-project-top-ten/)
- [CWE Top 25](https://cwe.mitre.org/top25/)
- [IoT Security Guidance (NIST)](https://www.nist.gov/itl/applied-cybersecurity/nist-cybersecurity-iot-program)
