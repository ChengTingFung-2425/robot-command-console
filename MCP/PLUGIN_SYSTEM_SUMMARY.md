# MCP 插件系統實作總結

## 概覽

本文件總結 MCP (Model Context Protocol) 服務的插件系統實作，包括本地 LLM 提供商自動偵測、MCP 工具注入、以及通用插件架構。

## 實作的三大系統

### 1. 本地 LLM 提供商系統

**目的**：自動偵測並整合本地 LLM 服務（Ollama, LM Studio 等）

**核心檔案**：
- `llm_provider_base.py` - 提供商基底類別與介面定義
- `llm_provider_manager.py` - 提供商管理器
- `providers/ollama_provider.py` - Ollama 提供商實作
- `providers/lmstudio_provider.py` - LM Studio 提供商實作

**功能**：
- ✅ 自動偵測本地 LLM 服務（掃描預設埠）
- ✅ 健康檢查與狀態監控
- ✅ 動態模型列表與選擇
- ✅ 提供商切換與回退機制
- ✅ 文字生成與參數調整

**API 端點**：
```
GET  /api/llm/providers           # 列出提供商
GET  /api/llm/providers/health    # 健康狀態
POST /api/llm/providers/discover  # 手動偵測
POST /api/llm/providers/select    # 選擇提供商
GET  /api/llm/providers/{name}/models  # 列出模型
POST /api/llm/providers/{name}/refresh # 重新檢查
```

### 2. MCP 工具介面系統 (Function Calling)

**目的**：將 MCP 指令暴露為 LLM 可呼叫的工具

**核心檔案**：
- `mcp_tool_interface.py` - 工具介面與執行邏輯

**功能**：
- ✅ 定義 MCP 指令為工具（OpenAI 格式）
- ✅ 支援 6 種機器人控制工具：
  - `robot_move_forward` - 向前移動
  - `robot_turn` - 轉向
  - `robot_stop` - 停止
  - `robot_gesture` - 手勢動作
  - `robot_get_status` - 查詢狀態
  - `robot_execute_sequence` - 執行動作序列
- ✅ 注入到 Ollama 和 LM Studio 提供商
- ✅ 工具呼叫執行與結果回傳

**工作流程**：
```
使用者輸入 -> LLM (with tools) -> 決定呼叫工具 -> 
執行 MCP 指令 -> 回傳結果 -> LLM 格式化回應 -> 使用者
```

**API 端點**：
```
POST /api/llm/invoke  # 使用 LLM 處理指令（啟用工具）
GET  /api/llm/tools   # 取得可用工具定義
```

### 3. 通用插件架構系統

**目的**：提供模組化的指令與裝置插件架構

**核心檔案**：
- `plugin_base.py` - 插件基底類別
- `plugin_manager.py` - 插件管理器
- `plugins/commands/` - 指令插件目錄
- `plugins/devices/` - 裝置插件目錄

**插件類型**：

#### 指令插件 (CommandPlugin)
處理複雜指令序列

**已實作插件**：
1. **AdvancedCommandPlugin** - 進階指令
   - `patrol` - 巡邏動作
   - `dance` - 跳舞動作（simple/complex/freestyle）
   - `greet` - 打招呼（wave/bow/nod）
   - `complex_navigation` - 複雜導航
   - `inspection` - 檢查動作
   - `presentation` - 展示動作

2. **WebUICommandPlugin** - WebUI 整合
   - `emergency_stop` - 緊急停止
   - `video_stream_control` - 視訊串流控制
   - `ui_feedback` - UI 回饋
   - `robot_selection` - 機器人選擇
   - `batch_command` - 批次指令

#### 裝置插件 (DevicePlugin)
整合物理模組

**已實作插件**：
1. **CameraPlugin** - 攝影機模組
   - 拍照功能（JPEG/PNG）
   - 視訊串流啟動/停止
   - 解析度與參數調整
   - 裝置資訊查詢

2. **SensorPlugin** - 感測器模組
   - 超音波距離感測器（5-400cm）
   - IMU 慣性測量（加速度、陀螺儀、方向）
   - 溫度感測器
   - 電池監控（電壓、電流、百分比）
   - 資料串流模式
   - 感測器校準

**API 端點**：
```
GET  /api/plugins                      # 列出插件
GET  /api/plugins/health               # 插件健康狀態
GET  /api/plugins/{name}/commands      # 插件支援的指令
POST /api/plugins/{name}/execute       # 執行插件指令
GET  /api/devices/{name}/info          # 裝置資訊
POST /api/devices/{name}/read          # 讀取裝置資料
```

## 整合架構

```
┌─────────────────────────────────────────────────────────┐
│                     MCP API 服務                         │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────────┐  ┌──────────────────┐           │
│  │ LLM 提供商管理器  │  │  插件管理器       │           │
│  ├──────────────────┤  ├──────────────────┤           │
│  │ • Ollama         │  │ 指令插件:         │           │
│  │ • LM Studio      │  │ • 進階指令        │           │
│  │ • 自動偵測        │  │ • WebUI 指令      │           │
│  │ • 健康監控        │  │                  │           │
│  └────────┬─────────┘  │ 裝置插件:         │           │
│           │            │ • 攝影機          │           │
│           │            │ • 感測器          │           │
│           │            └──────────────────┘           │
│           │                                             │
│           ▼                                             │
│  ┌──────────────────┐                                  │
│  │ MCP 工具介面     │  ◄──────┐                        │
│  ├──────────────────┤         │                        │
│  │ • 工具定義        │         │ 注入                   │
│  │ • 工具執行        │         │                        │
│  │ • 指令處理器      │         │                        │
│  └──────────────────┘         │                        │
│           │                    │                        │
│           ▼                    │                        │
│  ┌──────────────────┐         │                        │
│  │  指令處理器       │◄────────┘                        │
│  └──────────────────┘                                  │
│           │                                             │
└───────────┼─────────────────────────────────────────────┘
            │
            ▼
   ┌────────────────┐
   │  機器人路由器   │
   └────────────────┘
```

## 使用範例

### 1. 自動偵測 LLM 提供商

```bash
# MCP 啟動時自動執行
# 或手動觸發
curl -X POST http://localhost:8000/api/llm/providers/discover
```

### 2. 使用 LLM 控制機器人（with tools）

```bash
curl -X POST http://localhost:8000/api/llm/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "讓機器人向前移動 5 秒然後右轉",
    "robot_id": "robot-001",
    "use_tools": true
  }'

# LLM 會：
# 1. 理解指令
# 2. 呼叫 robot_move_forward(robot_id="robot-001", duration_ms=5000)
# 3. 呼叫 robot_turn(robot_id="robot-001", direction="right", duration_ms=1000)
# 4. 返回執行結果
```

### 3. 執行進階指令

```bash
curl -X POST http://localhost:8000/api/plugins/advanced_command/execute \
  -H "Content-Type: application/json" \
  -d '{
    "command_name": "patrol",
    "parameters": {
      "waypoints": [
        {"x": 10, "y": 20},
        {"x": 30, "y": 40}
      ],
      "speed": "normal"
    }
  }'

# 返回展開的動作序列
```

### 4. 讀取攝影機資料

```bash
curl -X POST http://localhost:8000/api/devices/camera/read \
  -H "Content-Type: application/json" \
  -d '{
    "format": "jpeg",
    "quality": 85
  }'
```

### 5. 讀取感測器資料

```bash
curl -X POST http://localhost:8000/api/devices/sensor/read \
  -H "Content-Type: application/json" \
  -d '{
    "sensor_type": "battery"
  }'
```

## 測試覆蓋

### LLM 提供商測試 (19 個測試)
- 提供商配置與初始化
- 健康檢查（可用/不可用）
- 模型列表
- 提供商管理器功能
- LLM 處理器整合

### 整體測試統計
- **總測試數**：114
- **通過率**：100%
- **新增測試**：19

## 設計原則

1. **模組化**：每個功能獨立封裝為插件
2. **可擴充**：輕鬆新增新的提供商或插件
3. **非同步**：所有 I/O 操作使用 async/await
4. **錯誤處理**：完整的例外處理與回退機制
5. **可觀測性**：詳細的日誌與 trace_id 追蹤
6. **標準化**：統一的介面與資料格式

## 效能特性

- **並行偵測**：多個提供商同時偵測
- **逾時控制**：每個操作都有逾時設定
- **健康監控**：定期檢查提供商狀態
- **自動回退**：提供商失敗時自動切換

## 安全性

- ✅ 通過 CodeQL 安全掃描
- ✅ 無安全警告
- ✅ 適當的錯誤處理
- ✅ 資源洩漏防護

## 文件

1. **LLM 提供商指南** - `docs/MCP_LLM_PROVIDERS.md`
   - 提供商安裝與配置
   - API 端點說明
   - 使用範例
   - 疑難排解

2. **插件架構指南** - `docs/MCP_PLUGIN_ARCHITECTURE.md`
   - 插件開發教學
   - 範例程式碼
   - 最佳實踐
   - 測試指南

## 未來擴充建議

### 短期（1-2 週）
- [ ] 新增更多 LLM 提供商（Claude, OpenAI API）
- [ ] 實作配置檔案持久化
- [ ] 新增插件熱載入功能
- [ ] UI 管理介面

### 中期（1-2 月）
- [ ] 插件市集與自動更新
- [ ] 更多裝置驅動（GPS、音訊等）
- [ ] 插件依賴管理系統
- [ ] 效能監控與優化

### 長期（3-6 月）
- [ ] 分散式插件執行
- [ ] 插件沙箱隔離
- [ ] A/B 測試支援
- [ ] 機器學習模型整合

## 總結

本次實作成功建立了一個完整的插件化架構，包含：

1. **本地 LLM 整合**：自動偵測並整合 Ollama 和 LM Studio
2. **MCP 工具注入**：LLM 可直接呼叫 MCP 指令控制機器人
3. **通用插件系統**：模組化的指令和裝置插件架構
4. **完整測試**：114 個測試全部通過
5. **詳細文件**：使用指南、開發指南、API 參考

系統具有良好的可擴充性、可維護性和可靠性，為未來的功能擴充奠定了堅實的基礎。
