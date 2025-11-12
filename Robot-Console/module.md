# Robot-Console 模組設計說明

本文件說明 `Robot-Console` 模組（機器人抽象層）的職責、檔案結構、介面契約、核心流程與擴充指引，對齊專案的 MCP 架構與契約檔（見 `docs/contract/*.schema.json`）。

## ⚠️ 重要變更：進階指令解碼職責轉移

**從此版本開始，進階指令的展開和解碼已移至 WebUI/上游服務處理。**

- **Robot-Console** 現在只接收預先解碼的基礎動作列表（如 `{"actions": ["go_forward", "turn_left", ...]}`）
- **WebUI/前端** 負責所有進階指令的展開、使用者互動和命令巨集的 UX
- **`advanced_decoder.py`** 已標記為棄用，僅保留用於向後相容
- 向後相容：仍支援舊的 `toolName` 格式和舊式進階指令（需在設定中啟用）

詳細說明請參閱第 13 節「進階指令處理（職責變更）」。

---

## 1. 模組定位與邊界

- 提供「統一的機器人指令抽象」，屏蔽底層通訊差異（MQTT、HTTP、WebSocket⋯⋯）。
- 接收 MCP 的標準化指令，轉為機器人可執行的動作並下發；回傳標準化狀態與結果。
- 僅供服務層（MCP）呼叫，不直接暴露給 WebUI 或外部客戶端。

注意：為了安全，系統必須支援「緊急停止（Emergency Stop）」指令可由 WebUI 觸發並立即到達本模組（經 MCP 授權與風控後轉發，或在受控條件下的直通通道）。

---

## 2. 資料夾與檔案說明

- `action_executor.py`：動作執行引擎（佇列、排程、超時、停止、並行下發本地/遠端）。
- `pubsub.py`：AWS IoT MQTT 發佈/訂閱用戶端（mTLS 與 WebSocket 雙模式、自動切換、重連）。現在優先處理 `actions` 陣列格式。
- `advanced_decoder.py`：⚠️ **已棄用** - 僅用於向後相容。新實作應在 WebUI 進行指令展開。
- `tools.py`：本地執行器使用的工具映射（`TOOL_LIST`、`TOOLS` 與各動作的 JSON Schema）。注意：MCP 為工具清單的權威來源，請勿直接在此檔案中變更正式工具定義——變更應先在 MCP 更新，然後透過同步機制或 CI 下放到本模組。
- `settings.yaml`：機器人與 AWS IoT 相關設定。可選設定 `enable_legacy_decoder: true` 以啟用舊式解碼器。
- `requirements.txt`：此模組的依賴套件清單。
- `create_virtual_env.sh`：建立虛擬環境與安裝依賴。
- `create_deploy_package.sh`：建立部署套件（排除 venv/cache）。
- `AmazonRootCA1.pem`：AWS 根 CA 憑證（TLS 連線使用）。
- `module.md`：本文件。

---

## 3. 核心能力與機器人動作

支援 38+ 預定義動作，依類別舉例如下（完整清單請參閱 `tools.py` 的 `TOOL_LIST`）：

- 移動類：`go_forward`、`back_fast`、`left_move_fast`、`right_move_fast`、`turn_left`、`turn_right`
- 控制類：`stop`、`stand_up_front`、`stand_up_back`
  - 其中包含「緊急停止」語意，必須可由 WebUI 觸發，並在本模組以最高優先權執行（可中斷當前動作佇列）。
- 手勢類：`bow`、`wave`、`stand`、`twist`
- 運動類：`push_ups`、`sit_ups`、`squat`、`chest`、`weightlifting`
- 格鬥類：`kung_fu`、`wing_chun`、`left_kick`、`right_kick`、`left_uppercut`、`right_uppercut`
- 舞蹈類：`dance_two` ~ `dance_ten`

目前主要針對人形機器人（Humanoid），結構可擴充至 AGV/AMR、機械臂、無人機等類型。

---

## 4. 標準化契約（與 MCP 對齊）

契約的正式定義請參閱：
- 請求：`docs/contract/command_request.schema.json`
- 回應：`docs/contract/command_response.schema.json`
- 錯誤：`docs/contract/error.schema.json`
- 事件：`docs/contract/event_log.schema.json`
- 狀態查詢：`docs/contract/status_response.schema.json`

以下提供精簡範例（欄位依實際 Schema 為準）：

### 4.1 指令請求（Request）

```json
{
  "trace_id": "uuid-v4",
  "command": {
    "id": "cmd-xxx",
    "type": "robot.action",
    "target": {
      "robot_id": "robot_7",
      "robot_type": "humanoid"
    },
    "params": {
      "action_name": "go_forward",
      "duration_ms": 3000,
      "speed": "normal"
    },
    "timeout_ms": 10000
  }
}
```

### 4.2 指令回應（Response）

```json
{
  "trace_id": "uuid-v4",
  "command": {
    "id": "cmd-xxx",
    "status": "succeeded"
  },
  "result": {
    "data": {
      "execution_time_ms": 2850,
      "final_position": { "x": 1.2, "y": 0.5 }
    },
    "summary": "動作執行完成"
  },
  "error": null
}
```

發生錯誤時（例如：機器人離線）：

```json
{
  "trace_id": "uuid-v4",
  "command": { "id": "cmd-xxx", "status": "failed" },
  "result": null,
  "error": {
    "code": "ERR_ROBOT_OFFLINE",
    "message": "機器人連線中斷",
    "details": { "last_ping": "2025-10-16T10:30:00Z" }
  }
}
```

---

## 5. 系統架構與流程

```
MCP（服務層）
    │  發送標準化指令（MQTT/HTTP/...）
    ▼
Robot-Console（本模組）
    ├─ pubsub.py（MQTT 訂閱/發布、mTLS/WS、自動切換）
    ├─ action_executor.py（佇列排程、超時、立即停止）
  └─ tools.py（本地執行器映射與 Schema；MCP 為權威工具庫）
    │
    ├─ 向本地控制器（localhost:9030）下發
    └─ 向遠端模擬器（雲端）下發

回傳：標準化回應 / 事件日誌（trace_id 貫穿）
```

---

## 6. 核心組件說明

### 6.1 `action_executor.py`

- 基於執行緒佇列的非同步引擎，支援排隊、優先權、超時控制。
- 可並行呼叫：
  - 本地機器人控制器（`http://localhost:9030/...`）
  - 遠端模擬器（雲端端點）
- 提供「立即停止」與動作中斷機制；追蹤狀態並回報進度。
  - 緊急停止（E-Stop）須具備最高優先權：
    - 立即清空接續佇列、嘗試中止目前動作、並下發停止指令至所有控制端。
    - 回報結束狀態與必要錯誤碼（若停止失敗，需回報原因）。

### 6.2 `pubsub.py`

- AWS IoT Core MQTT 用戶端：優先使用 mTLS，失敗時自動改用 WebSocket。
- 自動重連與容錯；訂閱主題（例如：`{robot_name}/topic`）。
- 驗證與解析訊息後，轉交 `ActionExecutor` 排程執行。
- 憑證來源：環境變數、設定檔或 AWS CLI 憑證。

### 6.3 `tools.py`

- 提供 AI/LLM 代理可用的工具清單（`TOOL_LIST`）。
- 定義每個動作的 JSON Schema（`TOOLS`），用於參數驗證與語義對齊。
- 與 `action_executor.py` 的動作定義一致，避免落差。

### 6.4 `settings.yaml`

示例（實際欄位請以檔案為準）：

```yaml
robot_name: robot_7
aws_iot:
  endpoint: xxxxx-ats.iot.region.amazonaws.com
  cert: /path/to/certificate.pem.crt
  private_key: /path/to/private.pem.key
  root_ca: ./AmazonRootCA1.pem
simulator:
  url: https://your-simulator.app
  session_key: your-session-key
```

---

## 7. 可靠性與可觀測性

- 重試機制：指數退避 + 隨機抖動。
- 超時控制：每筆指令可設定 `timeout_ms`。
- 冪等性：依 `command.id` 去重（由 MCP/上游協調）。
- 事件與日誌：包含 `trace_id`，方便端到端追蹤。

狀態機（簡化）：

```
idle → accepted → running → {succeeded | failed | cancelled}
                     ↓
                  paused → resumed → running
```

---

## 8. 錯誤處理

- `ERR_ROBOT_OFFLINE`：機器人離線或無回應。
- `ERR_ROBOT_BUSY`：執行中不可接受新指令。
- `ERR_ACTION_INVALID`：動作不支援或參數錯誤。
- `ERR_PARAM_INVALID`：參數驗證失敗（依 `TOOLS` 之 schema）。
- `ERR_HARDWARE_FAULT`：硬體故障（馬達、感測器）。
- `ERR_SAFETY_VIOLATION`：安全限制觸發（碰撞、超速）。
- `ERR_ESTOP_FAILED`：緊急停止失敗或未能在時限內生效。

錯誤格式請對齊 `docs/contract/error.schema.json`。

---

## 9. 測試與驗證（概述）

- 單元測試：動作定義、參數驗證、狀態轉換。
- 整合測試：指令流與錯誤處理、MQTT 連線流程。
- 模擬器測試：雲端模擬端對端驗證。
- 硬體測試：於實體機器人上驗證時間序與安全性。

---

## 10. 安全性

- 參數與動作白名單：所有動作需通過 Schema 驗證。
- 速度/角度/範圍限制：避免危險操作。
- 憑證與密鑰管理：優先使用環境變數或密管服務；設定檔不得明文提交。
- 授權與驗證：由 MCP 層完成，本模組僅接受經授權的指令來源。

---

## 11. 完成定義（DoD）

- 至少完成一種機器人類型的抽象與執行流程。
- 至少兩種通訊協定（例如：MQTT + HTTP）。
- 契約對齊：請求/回應/錯誤格式符合 `docs/contract/*.schema.json`。
- 測試涵蓋成功、錯誤、超時、重連；事件含 `trace_id` 並可查詢。
- 文件完整（能力清單、協定適配、擴充範例）。
  - 包含緊急停止（E-Stop）從 WebUI 觸發到本模組執行與回報的端到端流程與測試。

---

## 12. 擴充指南

### 12.1 新增機器人類型
1. 定義該類型支援的動作與參數 schema。
2. 在 `tools.py` 增加工具與 schema。
3. 在執行器中對應轉換與下發邏輯。
4. 撰寫測試並驗證（模擬器/硬體）。

### 12.2 新增通訊協定
1. 建立協定適配器（connect/send/receive/close）。
2. 處理重試、超時與錯誤映射。
3. 註冊到協定管理器並撰寫協定測試。

---

## 13. 進階指令處理（職責變更）

⚠️ **重要變更**：從此版本開始，進階指令的展開與解碼由 **WebUI/上游服務** 負責。
Robot-Console 模組現在只接收預先解碼的基礎動作列表。

### 13.1 新的資料格式

Robot-Console 現在預期接收已展開的動作列表：

```json
{
  "actions": ["go_forward", "turn_left", "go_forward", "stand"]
}
```

每個動作名稱必須是 `action_executor.py` 中定義的有效基礎動作。

### 13.2 向後相容性

為保持向後相容，仍支援以下格式（不建議新實作使用）：

1. 單一動作格式：
```json
{ "toolName": "go_forward" }
```

2. 舊式進階指令（需要在 `settings.yaml` 中設定 `enable_legacy_decoder: true`）：
```json
{ "type": "sequence", "steps": [{"action": "go_forward"}, {"action": "turn_left"}] }
```

### 13.3 新的職責劃分

1. **WebUI/前端**：
   - 負責進階指令的建立、編輯、儲存
   - 負責將進階指令展開為基礎動作序列
   - 負責使用者互動和命令巨集的 UX
   - 發送預先解碼的動作列表到 Robot-Console

2. **Robot-Console（本模組）**：
   - 只接收並執行基礎動作列表
   - 不再負責進階指令的解碼或展開
   - `advanced_decoder.py` 已標記為棄用，僅用於向後相容

3. **權限與審核**（在 WebUI 層處理）：
   - 提交：登入用戶建立進階指令，初始狀態 `pending`
   - 審核：Admin/Auditor 可將狀態改為 `approved` 或 `rejected`
   - 公開：通過審核者可被其他用戶引用

### 13.4 優點

- 更簡單的後端邏輯，易於維護
- 更靈活的前端 UX，便於建立命令序列和巨集
- 更清晰的職責劃分
- 減少 Robot-Console 的複雜度

---

## 14. 與其他模組的關係

```
MCP 服務層
    ↓（發送標準化指令）
Robot-Console（本模組）
    ↓（轉換為機器人特定格式）
協定適配器（HTTP/MQTT/WS/gRPC/ROS）
    ↓（實際通訊）
機器人硬體／模擬器
```

關鍵原則：
- MCP 不需要了解機器人底層細節。
- WebUI 不直接呼叫本模組。
- 本模組專注於抽象與協定轉換，確保安全與一致性。
