# 雲端同步 UI/狀態提示實作經驗（2026-02-11）

## 概述

為 Edge UI 添加雲端同步狀態的即時監控與提示功能，使用者可在首頁即時看到網路、佇列、緩衝區的健康狀態。

**相關檔案**：
- [`Edge/robot_service/electron/edge_ui.py`](../../Edge/robot_service/electron/edge_ui.py) — API 實作
- [`Edge/robot_service/electron/templates/edge/home.html`](../../Edge/robot_service/electron/templates/edge/home.html) — UI 實作
- [`docs/user_guide/FEATURES_REFERENCE.md`](../user_guide/FEATURES_REFERENCE.md#雲端同步狀態) — 使用者文件

---

## 實作內容

### 1. API 端點

```python
@edge_ui.route('/api/edge/sync/status', methods=['GET'])
def api_sync_status():
    return jsonify({
        'network': {'online': bool, 'status': str},
        'services': {'mcp': {...}, 'queue': {...}},
        'buffers': {'command': {...}, 'sync': {...}},
        'sync_enabled': bool,
        'last_sync': ISO8601
    })
```

- 基於既有 `check_internet_connection()` 和 `check_mcp_connection()`
- 返回結構化狀態資料（網路、服務、緩衝區、時間戳）

### 2. UI 元件

首頁新增「☁️ 雲端同步狀態」面板，4 個狀態卡片：
- **網路連線**：是否能到達公網
- **佇列服務**：MCP/Queue 服務健康
- **緩衝區**：待發送訊息數量
- **最後同步**：上次成功同步時間戳

狀態色彩：`status-success`（綠）、`status-warning`（黃）、`status-error`（紅）

### 3. 即時更新

```javascript
async function updateSyncStatus() {
    const data = await fetch('/api/edge/sync/status').then(r => r.json());
    updateStatusCard('#sync-network-status', data.network);
    updateStatusCard('#sync-queue-status', data.services.queue);
    // ...
}

setInterval(updateFullStatus, 30_000);   // 完整狀態每 30 秒
setInterval(updateSyncStatus, 10_000);  // 同步狀態每 10 秒
```

---

## 經驗教訓

### ✅ 模組化 API 設計

將狀態檢查邏輯封裝為獨立函式（`check_internet_connection()`），便於在多個 API 端點重用，也易於測試。

### ✅ 漸進式功能實作

先實作基礎版（網路狀態），在程式碼中標記 TODO 標記未來方向，保留擴展介面待後續整合。

### ✅ 雙頻率更新策略

區分兩種更新頻率，避免過度 API 呼叫：
- 完整頁面狀態（30 秒）— 包含服務健康、UI 刷新
- 同步特定狀態（10 秒）— 輕量 API，只更新同步卡片

---

## 待改進方向

1. **完整 OfflineQueueService 整合**：目前緩衝區統計為模擬資料（全 0），需整合 `OfflineQueueService` 實例（參考 TUI/qtwebview-app 實作）
2. **WebSocket 即時推送**：以 WebSocket 取代輪詢，減少延遲與伺服器負載
3. **狀態變更通知**：網路變更時 Toast 通知、緩衝區過多時警告
4. **詳細統計頁面**：同步歷史記錄、手動清空緩衝區功能
