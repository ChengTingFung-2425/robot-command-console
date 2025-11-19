# Testing Guide for Electron POC

## 自動化測試

### 整合測試
運行完整的整合測試腳本：

```bash
node test_integration.js
```

這會測試：
- Token 生成
- Flask 服務啟動
- 健康檢查端點
- Token 認證
- 無效 token 拒絕

預期輸出：
```
🎉 All tests passed! Integration working correctly.

✅ Electron POC Phase 1 verification complete:
   - Token generation: ✅
   - Flask service startup: ✅
   - Health check endpoint: ✅
   - Token authentication: ✅
   - Invalid token rejection: ✅
```

## 手動測試 Flask 服務

### 1. 啟動 Flask 服務

```bash
APP_TOKEN="test_token_123" PORT=5000 python3 flask_service.py
```

### 2. 測試健康檢查（無需認證）

```bash
curl http://127.0.0.1:5000/health | python3 -m json.tool
```

預期輸出：
```json
{
    "status": "healthy",
    "service": "robot-command-console-flask",
    "timestamp": "2025-11-19T03:00:00.000000+00:00",
    "version": "1.0.0-poc"
}
```

### 3. 測試 ping 端點（有效 token）

```bash
curl -X POST http://127.0.0.1:5000/api/ping \
  -H "Authorization: Bearer test_token_123" \
  -H "Content-Type: application/json" | python3 -m json.tool
```

預期輸出：
```json
{
    "authenticated": true,
    "message": "pong",
    "method": "POST",
    "timestamp": "2025-11-19T03:00:00.000000+00:00"
}
```

### 4. 測試 ping 端點（無效 token）

```bash
curl -X POST http://127.0.0.1:5000/api/ping \
  -H "Authorization: Bearer wrong_token" \
  -H "Content-Type: application/json" | python3 -m json.tool
```

預期輸出（401 錯誤）：
```json
{
    "code": "ERR_UNAUTHORIZED",
    "error": "Invalid token"
}
```

### 5. 測試 ping 端點（缺少 Authorization header）

```bash
curl -X POST http://127.0.0.1:5000/api/ping \
  -H "Content-Type: application/json" | python3 -m json.tool
```

預期輸出（401 錯誤）：
```json
{
    "code": "ERR_UNAUTHORIZED",
    "error": "Missing Authorization header"
}
```

## 手動測試 Electron 應用

### 1. 安裝依賴

```bash
# Node.js 依賴
npm install

# Python 依賴
pip install flask
```

### 2. 啟動 Electron（開發模式）

```bash
npm run start:dev
```

這會：
1. 生成隨機 token
2. 啟動 Flask 服務（port 5000）
3. 執行健康檢查
4. 開啟 Electron 視窗（含 DevTools）

### 3. 在 UI 中測試

**系統狀態卡片：**
- ✅ 應顯示 "✅ 服務運行正常"
- ✅ 應顯示 token 前 8 字元
- ✅ 應顯示 API 端點為 http://127.0.0.1:5000

**健康檢查：**
1. 點擊 "重新檢查 /health" 按鈕
2. ✅ 應顯示成功的 JSON 回應
3. ✅ 回應應包含 `status: "healthy"`

**API 測試：**
1. 點擊 "測試 /api/ping" 按鈕
2. ✅ 應顯示 "✅ 成功！"
3. ✅ 回應應包含 `authenticated: true`
4. ✅ 回應應包含 `message: "pong"`

### 4. 檢查控制台輸出

在 DevTools 控制台中：
- ✅ 應看到 "Renderer initializing..."
- ✅ 應看到 "Token received: xxxxxxxx..."
- ✅ 無 JavaScript 錯誤

在啟動 Electron 的終端中：
- ✅ 應看到 "[Python] Flask service initializing..."
- ✅ 應看到 "[Python] Running on http://127.0.0.1:5000"
- ✅ 應看到 "Health check passed"

### 5. 測試關閉流程

1. 關閉 Electron 視窗
2. ✅ Flask 服務應自動終止
3. ✅ 終端應顯示 "Shutting down Python service..."

## 建置測試（Linux）

### 建置 AppImage

```bash
npm run build:appimage
```

### 檢查產出

```bash
ls -lh dist/*.AppImage
```

應看到類似：
```
-rwxr-xr-x 1 user user 150M Nov 19 03:00 robot-command-console-1.0.0.AppImage
```

### 測試 AppImage（如果在 Linux 上）

```bash
chmod +x dist/robot-command-console-*.AppImage
./dist/robot-command-console-*.AppImage
```

## 疑難排解

### Flask 無法啟動

**檢查點：**
1. Python 3 已安裝：`python3 --version`
2. Flask 已安裝：`pip list | grep -i flask`
3. Port 5000 未被占用：`lsof -i :5000`

### Electron 視窗空白

**檢查點：**
1. 檢查 DevTools 控制台錯誤
2. 確認 `renderer/index.html` 存在
3. 確認 preload.js 正確載入

### Token 認證失敗

**檢查點：**
1. 確認 token 在 UI 中正確顯示
2. 檢查 Network 面板的請求 header
3. 查看 Flask 控制台輸出
4. 重啟應用重新生成 token

## 測試清單

- [ ] 整合測試腳本通過（test_integration.js）
- [ ] Flask 健康檢查成功
- [ ] Flask token 認證成功
- [ ] Flask 拒絕無效 token
- [ ] Electron 應用啟動成功
- [ ] UI 顯示正確
- [ ] 健康檢查按鈕工作
- [ ] Ping 測試按鈕工作
- [ ] Token 正確傳遞
- [ ] 關閉時 Flask 正確終止
- [ ] AppImage 建置成功（如在 Linux 上）

## 效能基準

- Flask 啟動時間：< 5 秒
- 健康檢查回應：< 100ms
- API ping 回應：< 100ms
- Electron 視窗開啟：< 10 秒
- 記憶體使用：< 200MB（含 Python）

## 已知限制（Phase 2 改進項目）

以下項目在 Phase 1 POC 中屬於已知限制，將在 Phase 2 中改進：

1. **開發模式警告**: Flask 顯示 "This is a development server" 警告 - 這是正常的，生產環境應使用 gunicorn 或 uwsgi（Phase 2）
2. **無 Token 刷新**: Token 在應用生命週期內固定，無自動刷新機制（Phase 2）
3. **無錯誤恢復**: Flask 崩潰後 Electron 不會自動重啟服務（Phase 2）
