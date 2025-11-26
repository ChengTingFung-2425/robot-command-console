# 威脅模型 (Threat Model)

## 概述

本文件描述 Robot Command Console 系統的威脅模型，識別潛在的安全威脅並提出相應的緩解措施。

## 系統架構概覽

Robot Command Console 由以下主要元件組成：
- **MCP Service (FastAPI)**: 提供 REST API 和 WebSocket 端點
- **Flask Service**: 提供 Electron 整合和獨立 CLI 模式
- **WebUI**: 使用者介面和進階指令處理
- **Robot-Console**: 機器人執行層
- **Electron App**: 桌面應用程式封裝

## 威脅分類

我們使用 STRIDE 模型來分類威脅：
- **S**poofing (欺騙)
- **T**ampering (篡改)
- **R**epudiation (否認)
- **I**nformation Disclosure (資訊洩露)
- **D**enial of Service (拒絕服務)
- **E**levation of Privilege (權限提升)

## 識別的威脅

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

**風險等級**: 中

**緩解措施**:
- ✅ 使用 bcrypt 進行密碼雜湊（包含隨機鹽值）
- ✅ 強制密碼最小長度（8 字元）
- ⚠️ 建議實施登入速率限制（未來增強）
- ⚠️ 建議實施帳號鎖定機制（未來增強）
- ⚠️ 建議記錄失敗的登入嘗試（部分實施）

#### 1.3 權限提升 (Elevation of Privilege)

**威脅描述**: 低權限使用者嘗試執行需要更高權限的操作。

**風險等級**: 高

**緩解措施**:
- ✅ 實施基於角色的存取控制 (RBAC)
- ✅ 三種角色：admin、operator、viewer
- ✅ 在每個操作前檢查權限
- ✅ 記錄權限拒絕事件到審計日誌
- ✅ 最小權限原則（預設為 viewer 角色）

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

### 外部信任邊界
1. **網際網路 ↔ API 閘道**: 所有外部請求必須通過認證
2. **WebUI ↔ MCP Service**: 需要有效的 JWT token
3. **Electron App ↔ Flask Service**: 需要 APP_TOKEN

### 內部信任邊界
1. **MCP Service ↔ Robot-Console**: 內部通訊，但仍需驗證
2. **佇列系統 ↔ 工作者**: 信任邊界內，但需要合約驗證

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

### 立即需要 (已實施)
- ✅ JWT token 驗證和過期檢查
- ✅ 基於角色的存取控制
- ✅ 密碼雜湊 (bcrypt)
- ✅ 輸入驗證 (Pydantic/JSON Schema)
- ✅ 審計日誌
- ✅ 指令超時機制

### 短期改進 (建議實施)
- ⚠️ 速率限制
- ⚠️ 登入失敗鎖定
- ⚠️ Refresh token 機制
- ⚠️ 生產環境 HTTPS 強制
- ⚠️ 集中式日誌管理

### 長期改進 (未來增強)
- ⚠️ Token 黑名單
- ⚠️ 外部秘密管理服務整合
- ⚠️ 日誌完整性檢查
- ⚠️ 憑證釘扎
- ⚠️ 進階 DoS 防護

## 假設和依賴

### 假設
1. 生產環境使用 HTTPS
2. 網路環境受到基本保護（防火牆等）
3. 作業系統和依賴套件保持更新
4. 秘密（JWT_SECRET、APP_TOKEN）安全管理

### 外部依賴
1. **Python 套件**: Flask, FastAPI, Pydantic, PyJWT, passlib
   - 風險：供應鏈攻擊、已知漏洞
   - 緩解：定期更新、漏洞掃描
2. **作業系統**: 檔案系統權限、程序隔離
   - 風險：OS 漏洞
   - 緩解：系統更新、最小權限運行

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
1. 每季度審查一次
2. 在重大架構變更後更新
3. 在發現新威脅後更新
4. 在安全事件後更新

## 參考資源

- [OWASP Threat Modeling](https://owasp.org/www-community/Threat_Modeling)
- [Microsoft STRIDE](https://docs.microsoft.com/en-us/azure/security/develop/threat-modeling-tool-threats)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
