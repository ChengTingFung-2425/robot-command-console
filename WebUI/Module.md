# WebUI 模組設計說明

本文件定義 WebUI 模組在本專案中的職責、互動流程、事件與即時性要求、介入操作、安全與可觀測性，對齊 `Project.prompt.md` 與 `MCP/Module.md`。

## 1. 職責與邊界
- WebUI 僅與 MCP 交互，永不直接連線機器人或協定適配器。
- 提供人機互動能力：登入/審批中心/指令下達/狀態面板/日誌查詢/告警訂閱。
- 提供人類介入控制：pause/resume/cancel/override，並完整產生日誌與審計事件。

## 2. 互動流程（對齊 MCP 契約）
1) 使用者登入（AuthN），獲取 Token；授權（AuthZ）決定可用功能。
2) **機器人管理**：
   - 查詢可用機器人：GET `/api/robots` 取得機器人清單（id/type/status/capabilities）
   - 選擇目標機器人：UI 提供下拉選單或卡片式選擇器
   - 查看機器人狀態：即時顯示 online/offline/busy 與電量、位置等資訊
3) **下達指令**：
   - 選擇機器人後，UI 動態載入該機器人的可用動作清單
  - 注意：機器人可用動作的權威來源為 MCP（例如：GET /api/robots/{robot_id}/capabilities 或 GET /api/tools）。WebUI 應以 MCP 回傳為準，不直接讀取 Robot-Console 的本地映射檔。
   - 組裝 CommandRequest（含 trace_id/actor/source/target/params/labels）
   - POST 到 MCP `/api/command`
   - 顯示指令已接受並取得 command_id
4) 監控執行：
   - 查詢：輪詢 `/api/status?command_id=...` 或
   - 訂閱：透過 WebSocket/SSE `/api/events` 接收事件（accepted/running/...）
   - 進度條與狀態指示器即時更新
5) 人類介入：於執行中狀態觸發 pause/resume/cancel/override；所有操作與審批紀錄寫入 Event（category=audit）。
6) 結果歸檔：將最終狀態、摘要與關鍵上下文關聯 trace_id 以供追溯與報表。

## 3. 即時性與事件
- 渲染來源：事件優先（WS/SSE），失連時回退輪詢。
- UI 狀態機：顯示 accepted → running → succeeded/failed/cancelled 流轉與進度。
- 告警：對錯誤與高風險事件彈出提醒與指引（排查建議/回滾操作）。

事件格式（參考 MCP）：
{
	"trace_id": "...",
	"timestamp": "...",
	"severity": "INFO|WARN|ERROR",
	"category": "command|auth|protocol|robot|audit",
	"message": "...",
	"context": { "command_id": "cmd-...", "user_id": "..." }
}

## 4. 介入操作與審批
- 高風險指令需先審批；審批結論、審批人與依據須記錄於審計事件。
- 支援操作：pause/resume/cancel/override；若覆寫需提供原因與風險提示。
- UI 應提供保護：二次確認、角色限制、節流與速率限制。

## 5. 安全與權限
- 身份驗證：JWT/OAuth2/Session 皆可，建議短期 Token + 刷新。
- 授權：RBAC（viewer/operator/admin/auditor）；頁面與操作基於權限控制顯示。
- 敏感資訊：前端不儲存明文秘鑰；錯誤訊息脫敏；避免在 URL 曝露敏感參數。

## 6. 可觀測性
- 使用者行為與關鍵操作產生 Event（category=audit）。
- UI 健康指標：事件延遲、斷線率、重連成功率。
- 與 MCP 之 trace_id 對齊，確保端到端追蹤。

## 7. 目錄結構對照
- `WebUI/app/*.py`：後端路由、錯誤處理、資料模型、郵件、表單。
- `WebUI/app/templates/*.j2`：頁面模板（狀態面板、日誌、審批、登入）。
- `WebUI/migrations/*`：資料庫遷移。
- `Test/Web/*`：對應測試檔，驗證路由、權限、日誌與 UI 結構。

### 7.1 核心頁面與功能
- **機器人儀表板（Dashboard）**：
  - 顯示所有註冊機器人的卡片（狀態、類型、能力）
  - 即時狀態更新（WebSocket）
  - 快速操作按鈕（選擇、查看詳情）
  
- **指令控制中心（Command Center）**：
  - 機器人選擇器（下拉或搜尋）
  - 動作選擇器（根據機器人類型動態載入）
  - 參數輸入表單（JSON 編輯器或結構化表單）
  - 執行按鈕與確認對話框
  
- **進階指令建立器（Advanced Command Builder）**：
  - **程式積木介面（Blockly Integration）**：
    - 視覺化拖放式積木編輯器，降低使用門檻
    - 37 種機器人動作積木（movement, gesture, dance, combat, exercise）
    - 控制流程積木（sequence, loop, conditional, wait）
    - 即時 JSON 預覽與驗證
    - 匯入/匯出積木工作區（儲存與分享）
  - 積木類別：
    - **移動積木**：go_forward, back_fast, turn_left, turn_right, left_move_fast, right_move_fast
    - **姿態積木**：stand, bow, squat, stand_up_front, stand_up_back
    - **戰鬥積木**：left_kick, right_kick, kung_fu, wing_chun, left_uppercut, right_uppercut, left_shot_fast, right_shot_fast
    - **舞蹈積木**：dance_two ~ dance_ten（9 種舞蹈動作）
    - **運動積木**：push_ups, sit_ups, chest, weightlifting, squat_up
    - **控制積木**：loop（重複執行）, wait（延遲）, stop（停止）
  - 積木編輯器特性：
    - 自動計算總執行時間（基於 sleep_time）
    - 語法錯誤即時提示（如未連接的積木）
    - 工作區縮放與拖曳
    - 垃圾桶拖放刪除
    - 程式碼產生器：積木 → JSON 指令序列
  
- **執行監控面板（Execution Monitor）**：
  - 進行中指令列表（狀態、進度條）
  - 歷史指令查詢（篩選、排序、搜尋）
  - 詳細執行記錄（時間軸、事件流）
  - 介入操作按鈕（pause/resume/cancel）
  
- **審批中心（Approval Center）**：
  - 待審批指令佇列
  - 審批表單（同意/拒絕/附註）
  - 審批歷史與稽核記錄
  
- **日誌與告警（Logs & Alerts）**：
  - 即時事件流（可篩選 severity/category）
  - 錯誤告警與通知
  - 匯出與下載功能

## 8. 完成定義（DoD）
- 頁面與 API 對齊 MCP 契約；指令/事件流在本地可驗證。
- 測試涵蓋：登入/授權、下達指令、事件訂閱、介入操作、日誌產生。
- 安全檢查：權限控制、敏感資訊處理、錯誤脫敏。
- 可觀測性：事件與 trace_id 貫通，關鍵指標可查。

## 9. 下一步
- 定義介入操作的 API 與前端交互細節（確認對話、風險提示）。
- 建立告警訂閱與通知機制（Email/Webhook）。
- 強化 E2E 測試：模擬連線中斷、超時與重試。

## 10. 模組狀態更新 — Docker 啟動範例

- 已在本模組下新增 `WebUI/docker/` 目錄，包含可用於開發與測試的容器化範例檔：
  - `WebUI/docker/Dockerfile`：建立以 Python 3.11-slim 為基礎的映像，預設以 Gunicorn 啟動 `WebUI.app:app`。
  - `WebUI/docker/docker-entrypoint.sh`：簡單 entrypoint，支援在有 `DATABASE_URL` 時等候資料庫啟動。
  - `WebUI/docker/.dockerignore`：列出不應打包到映像中的檔案/資料夾。
  - `WebUI/docker/docker-compose.yml`：示範性 Compose 檔案，可在本地啟動服務（映射 5000 埠、掛載程式碼以方便開發）。

- 使用建議：
  1. 若要在本機建構映像，請從專案根目錄執行：

     ```bash
     docker build -f WebUI/docker/Dockerfile -t robot-webui:latest .
     ```

  2. 或使用 compose（在 `WebUI/docker` 目錄）：

     ```bash
     cd WebUI/docker
     docker-compose up --build
     ```

- 注意：
  - 映像預設不在容器內終止 TLS，而是將 HTTP（5000）暴露出來；生產環境建議放置反向代理（nginx）處理 TLS 與靜態檔。 
  - 若希望我把現有根目錄中的 Docker 文件（若仍存在複製）移除或同步到 `WebUI/docker/`，或加入 `nginx` + TLS 範例，請回覆我想要的選項，我將清理與補齊必要的 CI 與文件。

## 11. API 端點說明

### 11.1 進階指令執行

#### POST `/advanced_commands/<cmd_id>/execute`

執行已批准的進階指令：展開為基礎動作序列並發送到指定機器人的 Robot-Console 執行佇列。

**需要認證**：是（需要登入）

**請求參數**：
- Path 參數：
  - `cmd_id` (integer): 進階指令的 ID

- Body（JSON）：
```json
{
  "robot_id": 1  // 目標機器人 ID（必填）
}
```

**權限要求**：
- 用戶必須是機器人的擁有者，或
- 用戶必須具有 admin/auditor 角色

**處理流程**：
1. 驗證進階指令狀態（必須為 `approved`）
2. 驗證用戶權限（必須擁有該機器人）
3. 展開進階指令：
   - 從資料庫載入 `base_commands` JSON
   - 解析為動作序列：`[{"command": "go_forward"}, ...] → ["go_forward", ...]`
   - 驗證所有動作都是有效的基礎動作（參照 Robot-Console/action_executor.py）
4. 構建符合 Robot-Console 期望的格式：`{"actions": ["go_forward", "turn_left", ...]}`
5. 發送到機器人（目前記錄到日誌，實際傳輸機制待整合）
6. 建立 Command 記錄到資料庫

**成功回應**（200 OK）：
```json
{
  "success": true,
  "message": "已發送 3 個動作到機器人 test_robot",
  "command_id": 123,
  "details": {
    "robot_id": 1,
    "robot_name": "test_robot",
    "actions_count": 3,
    "actions": ["go_forward", "turn_left", "stand"]
  }
}
```

**錯誤回應**：
- 400 Bad Request：缺少 robot_id 或進階指令格式錯誤
```json
{
  "success": false,
  "message": "缺少必要參數：robot_id"
}
```

- 403 Forbidden：未批准的指令或無權限控制該機器人
```json
{
  "success": false,
  "message": "只能執行已批准的進階指令（當前狀態：pending）"
}
```

- 404 Not Found：進階指令或機器人不存在

- 500 Internal Server Error：執行失敗
```json
{
  "success": false,
  "message": "執行失敗：..."
}
```

**相關函式**：
- `expand_advanced_command(advanced_cmd)`: 展開進階指令為動作列表
- `send_actions_to_robot(robot, actions)`: 發送動作到機器人

**測試覆蓋**：參見 `Test/test_advanced_command_execution.py`

