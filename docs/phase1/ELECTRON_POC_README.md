# Electron POC - Phase 1

## 概述

這是 Robot Command Console 的 Phase 1 Electron POC，實現了 Electron 桌面應用與本地 Flask 背景服務的整合。

## 技術規格

- **平台**: Linux (主要目標)
- **Node.js**: v20.x
- **Python**: 3.x (系統安裝)
- **Electron**: v39.x
- **Flask**: 3.x
- **API 端口**: 5000
- **認證**: Bearer Token（應用生命週期內有效）

## 架構

```
┌─────────────────────────────────────┐
│     Electron Desktop App             │
│  ┌───────────────────────────────┐  │
│  │  Renderer (renderer/*)        │  │
│  │  - UI (index.html)            │  │
│  │  - API Client (renderer.js)   │  │
│  └──────────────┬────────────────┘  │
│                 │ IPC                │
│  ┌──────────────▼────────────────┐  │
│  │  Main Process (main.js)       │  │
│  │  - Token 生成                  │  │
│  │  - Python 服務管理             │  │
│  │  - 健康檢查                    │  │
│  └──────────────┬────────────────┘  │
└─────────────────┼────────────────────┘
                  │ HTTP (localhost:5000)
                  │ Authorization: Bearer <token>
┌─────────────────▼────────────────────┐
│  Flask Service (flask_service.py)    │
│  - /health (無需認證)                 │
│  - /api/ping (需要認證)               │
└──────────────────────────────────────┘
```

## 功能特性

### ✅ 已實現

1. **Token 認證**
   - Electron 主進程生成 32 字節隨機 token
   - 透過環境變數 `APP_TOKEN` 傳遞給 Python
   - Renderer 透過 IPC 從主進程獲取 token
   - Flask 驗證 `Authorization: Bearer <token>` header

2. **健康檢查**
   - `/health` 端點（不需認證）
   - 啟動時自動檢查（最多重試 10 次）
   - UI 顯示服務狀態

3. **API 往返測試**
   - `/api/ping` 端點（需要認證）
   - POST 請求測試 token 驗證
   - 顯示完整回應

4. **Python 服務管理**
   - 主進程自動啟動 Flask 服務
   - 監聽 stdout/stderr 輸出
   - 應用關閉時自動終止服務

5. **UI**
   - 簡潔的 Web UI
   - 即時狀態顯示
   - 互動式測試按鈕

## 安裝與運行

### 前置需求

```bash
# 確認 Node.js 和 Python 版本
node --version  # 應為 v20.x
python3 --version  # 應為 3.x
```

### 安裝依賴

```bash
# 安裝 Node.js 依賴
npm install

# 安裝 Python 依賴
pip install flask
```

### 開發模式運行

```bash
# 啟動 Electron（自動啟動 Flask）
npm start

# 或開發模式（開啟 DevTools）
npm run start:dev
```

### 建置 AppImage（Linux）

```bash
# 建置 Linux AppImage
npm run build:appimage

# 產出位置
ls dist/*.AppImage
```

## 測試流程

1. **啟動應用**
   ```bash
   npm start
   ```

2. **檢查系統狀態**
   - 應顯示 "✅ 服務運行正常"
   - Token 應顯示前 8 個字元

3. **測試健康檢查**
   - 點擊 "重新檢查 /health" 按鈕
   - 應看到 JSON 回應顯示 `status: "healthy"`

4. **測試 API Ping**
   - 點擊 "測試 /api/ping" 按鈕
   - 應看到 `✅ 成功！` 和 `authenticated: true`

5. **驗證 Token 認證**
   - 如果 token 不正確，應返回 401 錯誤
   - 檢查 Flask 日誌確認認證流程

## 檔案結構

```
.
├── main.js                 # Electron 主進程
├── preload.js             # Preload script (Context Bridge)
├── flask_service.py       # Flask 背景服務
├── renderer/
│   ├── index.html         # UI 頁面
│   └── renderer.js        # Renderer 進程邏輯
├── package.json           # Node.js 配置
└── ELECTRON_POC_README.md # 本文件
```

## API 端點

### GET /health

健康檢查端點（不需認證）

**回應範例:**
```json
{
  "status": "healthy",
  "service": "robot-command-console-flask",
  "timestamp": "2025-11-19T03:00:00.000Z",
  "version": "1.0.0-poc"
}
```

### POST /api/ping

Ping 測試端點（需要認證）

**請求 Headers:**
```
Authorization: Bearer <token>
Content-Type: application/json
```

**回應範例:**
```json
{
  "message": "pong",
  "timestamp": "2025-11-19T03:00:00.000Z",
  "method": "POST",
  "authenticated": true
}
```

**錯誤回應 (401):**
```json
{
  "error": "Invalid token",
  "code": "ERR_UNAUTHORIZED"
}
```

## 安全考量

1. **本地綁定**: Flask 服務只監聽 `127.0.0.1`，不暴露給外部網路
2. **Token 隔離**: Token 透過環境變數傳遞，不寫入檔案
3. **Context Isolation**: Renderer 進程啟用 context isolation
4. **No Node Integration**: Renderer 不直接存取 Node.js API
5. **Preload Script**: 透過安全的 IPC 通道傳遞 token

## 疑難排解

### Flask 服務無法啟動

**症狀**: 健康檢查失敗，顯示連接錯誤

**解決方案**:
1. 檢查 Python 是否安裝 Flask: `pip list | grep -i flask`
2. 檢查 port 5000 是否被占用: `lsof -i :5000`
3. 查看 Electron 控制台的 Python 輸出
4. 手動測試 Flask: `python3 flask_service.py` (需設定 APP_TOKEN)

### Token 認證失敗

**症狀**: /api/ping 返回 401 錯誤

**解決方案**:
1. 確認 token 已正確顯示在 UI
2. 檢查請求 header 格式: `Authorization: Bearer <token>`
3. 查看 Flask 控制台輸出
4. 重啟應用重新生成 token

### UI 無法載入

**症狀**: Electron 視窗空白

**解決方案**:
1. 檢查 `renderer/index.html` 是否存在
2. 開啟 DevTools: `npm run start:dev`
3. 查看控制台錯誤訊息

## 已知限制（Phase 1 範圍）

Phase 1 POC 專注於基本整合驗證，以下為有意的限制，將在後續階段改進：

1. **單一 Token**: 目前每次啟動生成一個固定 token，無刷新機制（Phase 2）
2. **無持久化**: Token 不保存，每次重啟都會變更（Phase 2）
3. **基礎錯誤處理**: 錯誤處理較簡單，未涵蓋所有情況（Phase 2）
4. **無 CI**: 此 POC 不包含 CI 配置（依問題說明，CI 不在此 PR 範圍）
5. **Linux Only**: 主要測試 Linux，其他平台未完整測試（Phase 2）

## Phase 2 計劃功能

- [ ] CI/CD 配置
- [ ] Token 過期與刷新機制
- [ ] Flask 錯誤自動恢復
- [ ] 更多 API 端點
- [ ] 整合完整的 MCP 後端
- [ ] WebSocket 即時通訊
- [ ] macOS 和 Windows 完整支援
- [ ] 生產級 WSGI 伺服器（gunicorn/uwsgi）

## 參考文件

- [Electron 整合計畫](./plans/webui-to-app/electron-python-integration.md)
- [Electron 開發設定](./plans/webui-to-app/electron-dev-setup.md)
- [Electron 打包](./plans/webui-to-app/electron-packaging.md)

## 版本資訊

- **版本**: 1.0.0-poc
- **日期**: 2025-11-19
- **狀態**: ✅ Phase 1 完成
