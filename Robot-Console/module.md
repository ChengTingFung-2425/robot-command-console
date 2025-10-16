# Robot-Console 模組設計說明# Robot-Console 資料夾說明



本文件定義 Robot-Console 模組（機器人抽象層）在本專案中的職責、介面設計、通訊協定與完成定義，對齊 `prosposal.md` 與 MCP 中介層架構。**`Robot-Console`** 資料夾包含一個基於 Python 的機器人控制系統，專為透過 AWS IoT MQTT 訊息傳遞來控制人形機器人而設計。以下是完整的說明：



## 1. 職責與邊界## 📁 **核心組件**

- **機器人抽象層**：為不同類型的機器人提供統一的指令介面，隔離底層通訊協定差異。

- **指令執行器**：接收來自 MCP 的標準化指令，轉換為機器人特定格式並執行。### **1. `action_executor.py`** (311 行)

- **狀態回報**：將機器人執行狀態、結果與錯誤回報給 MCP。管理機器人動作和指令的主要動作執行引擎。

- **協定適配**：支援多種通訊協定（HTTP、MQTT、WebSocket、gRPC、ROS 等）。

- **永不直接對外**：僅由 MCP 調用，不直接接受 WebUI 或外部客戶端請求。**主要功能：**

- **動作字典**：包含 38+ 個預定義的機器人動作，包括：

## 2. 機器人類型與能力定義  - **移動**：`go_forward`（前進）、`back_fast`（快速後退）、`left_move_fast`（快速左移）、`right_move_fast`（快速右移）、`turn_left`（左轉）、`turn_right`（右轉）

  - **格鬥**：`kung_fu`（功夫）、`wing_chun`（詠春）、`left_kick`（左踢）、`right_kick`（右踢）、`left_uppercut`（左上勾拳）、`right_uppercut`（右上勾拳）

### 2.1 人形機器人（Humanoid）  - **運動**：`push_ups`（伏地挺身）、`sit_ups`（仰臥起坐）、`squat`（深蹲）、`chest`（擴胸）、`weightlifting`（舉重）

**支援的動作類別**（38+ 個預定義動作）：  - **舞蹈**：`dance_two` 到 `dance_ten`（多個編排的舞蹈動作）

- **移動類**：`go_forward`、`back_fast`、`left_move_fast`、`right_move_fast`、`turn_left`、`turn_right`  - **手勢**：`bow`（鞠躬）、`wave`（揮手）、`stand`（站立）、`twist`（扭轉）

- **格鬥類**：`kung_fu`、`wing_chun`、`left_kick`、`right_kick`、`left_uppercut`、`right_uppercut`  - **控制**：`stop`（停止）、`stand_up_front`（從前方站起）、`stand_up_back`（從後方站起）

- **運動類**：`push_ups`、`sit_ups`、`squat`、`chest`、`weightlifting`

- **舞蹈類**：`dance_two` ~ `dance_ten`（多個編排動作）- **ActionExecutor 類別**：

- **手勢類**：`bow`、`wave`、`stand`、`twist`  - 基於執行緒佇列的動作執行系統

- **控制類**：`stop`、`stand_up_front`、`stand_up_back`  - 同時發送指令到本地機器人控制器（localhost:9030）和遠端模擬器

  - 管理動作時序和順序執行

### 2.2 可擴充機器人類型  - 支援立即停止功能

- **移動機器人**（AGV/AMR）：導航、路徑規劃、避障  - 處理動作中斷和佇列管理

- **機械臂**：抓取、放置、組裝

- **無人機**：起飛、降落、巡航### **2. `pubsub.py`** (263 行)

- **未來類型**：透過繼承基礎抽象類別新增AWS IoT Core MQTT 發布-訂閱客戶端，用於接收遠端指令。



## 3. 標準化指令介面（對齊 MCP 契約）**主要功能：**

- **PubSubClient 類別**：管理 MQTT 連線生命週期

### 3.1 接收指令格式- **雙重連線模式**：支援 mTLS（雙向 TLS）和 WebSocket 連線

```json- **自動容錯**：優先嘗試 mTLS，失敗時自動切換到 WebSocket

{- **訊息處理器**：接收帶有 `toolName` 欄位的 JSON 資料並將動作加入佇列

  "trace_id": "uuid-v4",- **AWS 憑證管理**：從環境變數、設定檔或 AWS CLI 憑證載入

  "command": {- **主題訂閱**：監聽 `{robot_name}/topic` 模式

    "id": "cmd-xxx",

    "type": "robot.action",### **3. `tools.py`** (201 行)

    "target": {外部整合的工具和動作定義（可能用於 LLM/AI 代理）。

      "robot_id": "robot_7",

      "robot_type": "humanoid"**主要功能：**

    },- 複製 `action_executor.py` 中的動作定義

    "params": {- **TOOL_LIST**：所有 38 個機器人動作的人類可讀描述

      "action_name": "go_forward",- **TOOLS**：帶有 JSON schema 的格式化工具規格，用於 AI/LLM 整合

      "duration_ms": 3000,- 實現自然語言指令解譯

      "speed": "normal"

    },### **4. `settings.yaml`**

    "timeout_ms": 10000機器人和 AWS IoT 設定的設定檔。

  }

}**設定內容：**

```- `robot_name`："robot_7"（可設定的機器人識別碼）

- AWS IoT 端點和憑證

### 3.2 回應格式- mTLS 認證的憑證路徑

```json- 模擬器認證的 session key

{- 模擬器端點 URL（AWS App Runner 託管）

  "trace_id": "uuid-v4",

  "command": {### **5. `requirements.txt`**

    "id": "cmd-xxx",Python 依賴套件：

    "status": "succeeded|failed|running"- `awsiotsdk`：AWS IoT SDK，用於 MQTT 連線

  },- `pyyaml`：YAML 設定檔解析

  "result": {- `requests`：向模擬器和機器人控制器發送 HTTP 請求

    "data": {- 已註解：audio、AWS Bedrock、boto3（未來功能？）

      "execution_time_ms": 2850,

      "final_position": {"x": 1.2, "y": 0.5}## 🛠️ **工具腳本**

    },

    "summary": "動作執行完成"### **6. `create_virtual_env.sh`**

  },Bash 腳本，用於設定 Python 虛擬環境並安裝依賴套件。

  "error": {

    "code": "ERR_ROBOT_OFFLINE",### **7. `create_deploy_package.sh`**

    "message": "機器人連線中斷",建立部署套件（`deploy_package.zip`），排除虛擬環境和快取檔案。

    "details": {"last_ping": "2025-10-16T10:30:00Z"}

  }### **8. `AmazonRootCA1.pem`**

}Amazon 根 CA 憑證，用於安全的 AWS IoT TLS 連線。

```

---

## 4. 核心組件說明

## 🔄 **系統架構**

### 4.1 `action_executor.py`

**ActionExecutor 類別**（動作執行引擎）：```

- 基於執行緒佇列的非同步執行系統AWS IoT Core (MQTT)

- 支援動作排隊、優先級管理、超時控制        ↓ (發布動作指令)

- 並行發送指令到：   pubsub.py (訂閱者)

  - 本地機器人控制器（localhost:9030）        ↓ (將動作加入佇列)

  - 遠端模擬器（用於測試與驗證）  ActionExecutor

- 立即停止與動作中斷機制        ↓ (並行發送指令)

- 狀態追蹤與進度回報        ├→ 本地機器人控制器 (localhost:9030)

        └→ 遠端模擬器 (AWS App Runner)

### 4.2 `pubsub.py`（協定適配範例）```

**MQTT 協定適配器**：

- 接收來自 MCP 的 MQTT 訊息## 🎯 **使用情境**

- 支援 mTLS 與 WebSocket 雙模式連線1. **遠端機器人控制**：透過雲端訊息傳遞控制實體人形機器人

- 自動容錯與重連機制2. **模擬器整合**：在部署到硬體之前，在網頁模擬器中測試動作

- 訊息解析與驗證3. **AI/LLM 整合**：tools.py 實現透過 AI 代理進行自然語言控制

- 將指令轉發至 ActionExecutor4. **多機器人支援**：基於設定的機器人識別，用於機群管理



**可擴充協定**：這是一個生產就緒的 IoT 機器人控制系統，具備強大的錯誤處理、雙模式連線和 AI 驅動控制的整合點！

- HTTP/REST API 適配器
- WebSocket 適配器
- gRPC 適配器
- ROS/ROS2 適配器

### 4.3 `tools.py`
**AI/LLM 整合定義**：
- 提供給 MCP 的工具清單（TOOL_LIST）
- 每個動作的 JSON Schema 定義
- 自然語言到動作指令的映射
- 用於 AI 代理理解與調用機器人能力

### 4.4 `settings.yaml`
**機器人設定檔**：
- `robot_id`：機器人唯一識別碼
- `robot_type`：機器人類型（humanoid/agv/arm/drone）
- 通訊端點與憑證設定
- 能力清單與限制參數

## 5. 通訊協定與可靠性

### 5.1 支援的協定
- **HTTP/REST**：同步指令與查詢
- **MQTT**：非同步訊息、IoT 場景
- **WebSocket**：即時雙向通訊
- **gRPC**：高效能 RPC
- **ROS/ROS2**：機器人作業系統標準

### 5.2 可靠性保證
- **重試機制**：指數退避 + 隨機抖動
- **超時控制**：每個指令設定明確超時
- **冪等性**：基於 command.id 去重
- **狀態持久化**：關鍵狀態落地存儲
- **斷線重連**：自動恢復與狀態同步

## 6. 錯誤處理與狀態碼

### 6.1 機器人特定錯誤
- `ERR_ROBOT_OFFLINE`：機器人離線或無回應
- `ERR_ROBOT_BUSY`：機器人執行中，無法接受新指令
- `ERR_ACTION_INVALID`：動作類型不支援
- `ERR_PARAM_INVALID`：參數驗證失敗
- `ERR_HARDWARE_FAULT`：硬體故障（馬達、感測器）
- `ERR_SAFETY_VIOLATION`：安全限制觸發（碰撞、超速）

### 6.2 狀態機
```
idle → accepted → running → {succeeded | failed | cancelled}
                     ↓
                  paused → resumed → running
```

## 7. 整合測試與驗證

### 7.1 測試範圍
- **單元測試**：動作定義、參數驗證、狀態轉換
- **整合測試**：與 MCP 的指令流、錯誤處理
- **協定測試**：各協定適配器的連線與訊息傳遞
- **模擬器測試**：使用模擬器驗證動作邏輯
- **硬體測試**：實體機器人執行驗證

### 7.2 可觀測性
- 所有指令執行產生事件（含 trace_id）
- 關鍵指標：成功率、平均執行時間、錯誤分佈
- 機器人健康檢查：心跳、電量、感測器狀態

## 8. 安全性

- **指令驗證**：嚴格的參數範圍與類型檢查
- **安全限制**：速度上限、可達範圍、碰撞偵測
- **權限控管**：由 MCP 層處理，本模組信任已授權指令
- **敏感資訊**：憑證與金鑰由環境變數或密管服務提供

## 9. 完成定義（DoD）
- 定義並實作至少一種機器人類型的抽象介面
- 支援至少兩種通訊協定（HTTP + MQTT）
- 與 MCP 契約對齊，指令與回應格式標準化
- 測試涵蓋：成功執行、參數錯誤、超時、斷線重連
- 事件與 trace_id 貫通，可在 WebUI 查詢
- 文件包含：機器人能力清單、協定適配指南、擴充範例

## 10. 擴充指南

### 10.1 新增機器人類型
1. 繼承 `BaseRobot` 抽象類別
2. 實作 `execute_action()` 方法
3. 定義該類型的動作清單與參數 schema
4. 更新 `tools.py` 提供給 AI 代理
5. 撰寫整合測試

### 10.2 新增通訊協定
1. 實作協定適配器（connect/send/receive/close）
2. 處理重試、超時與錯誤映射
3. 註冊到協定管理器
4. 撰寫協定測試

## 11. 與其他模組的關係

```
MCP 服務層
    ↓ (發送標準化指令)
Robot-Console (本模組)
    ↓ (轉換為機器人特定格式)
協定適配器 (HTTP/MQTT/WS/gRPC/ROS)
    ↓ (實際通訊)
機器人硬體/模擬器
```

**關鍵原則**：
- MCP 不需要了解機器人底層細節
- WebUI 永不直接調用本模組
- 本模組專注於機器人抽象與協定轉換
