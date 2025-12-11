# Robot Service TUI Module

終端機使用者介面（Terminal User Interface）模組

## 概述

TUI 模組提供終端機互動式介面，適用於：
- 無頭（headless）伺服器環境
- 容器部署環境
- SSH 遠端存取
- 偏好終端機操作的使用者

## 架構

```
src/robot_service/tui/
├── __init__.py          # 模組初始化
├── app.py               # TUI 應用主程式
└── runner.py            # TUI 執行器
```

### 核心元件

#### 1. ServiceStatusWidget

顯示服務狀態的元件。

**功能：**
- 即時更新服務狀態
- 顏色編碼狀態指示
- 支援多種服務狀態（STOPPED、STARTING、RUNNING、ERROR 等）

**使用範例：**
```python
from src.robot_service.tui.app import ServiceStatusWidget
from common.service_types import ServiceStatus

widget = ServiceStatusWidget()
widget.update_service_status("mcp_service", ServiceStatus.RUNNING)
```

#### 2. RobotStatusWidget

顯示機器人狀態的元件。

**功能：**
- 顯示機器人連接狀態
- 顯示電量百分比
- 顯示當前運行模式

**使用範例：**
```python
from src.robot_service.tui.app import RobotStatusWidget

widget = RobotStatusWidget()
widget.update_robot_status("robot-001", {
    "connected": True,
    "battery_level": 85,
    "mode": "Standby"
})
```

#### 3. CommandHistoryWidget

顯示指令執行歷史的元件。

**功能：**
- 滾動顯示最近 20 條指令
- 包含時間戳、機器人 ID、動作名稱和狀態
- 自動更新

**使用範例：**
```python
from src.robot_service.tui.app import CommandHistoryWidget

widget = CommandHistoryWidget()
widget.add_command("10:30:00", "robot-001", "go_forward", "success")
```

#### 4. RobotConsoleTUI

主 TUI 應用程式。

**功能：**
- 整合所有元件
- 處理鍵盤事件
- 與服務協調器和狀態管理器整合
- 定期更新顯示

**使用範例：**
```python
from src.robot_service.tui.app import RobotConsoleTUI

app = RobotConsoleTUI(
    coordinator=my_coordinator,
    state_manager=my_state_manager,
    history_manager=my_history_manager
)
await app.run_async()
```

**指令格式：**

TUI 支援以下指令格式：

1. **基本指令**：`action_name`
   - 發送到預設機器人 (robot-001)
   - 範例：`go_forward`

2. **指定機器人**：`robot-id:action_name`
   - 發送到特定機器人
   - 範例：`robot-002:turn_left`

3. **廣播指令**：`all:action_name`
   - 同時發送到所有連接的機器人
   - 範例：`all:stand`

指令解析由 `_parse_command()` 方法處理，返回 `(robot_id, action)` 元組。

#### 5. TUIRunner

TUI 執行器，負責初始化和啟動 TUI。

**功能：**
- 解析命令列參數
- 設定服務（協調器、狀態管理器、歷史管理器）
- 啟動和管理 TUI 生命週期

## 技術選型

### Textual 框架

使用 [Textual](https://github.com/Textualize/textual) 作為 TUI 框架：

**優點：**
- 現代化的 Python TUI 框架
- 支援 CSS-like 布局語法
- 完整的異步支援
- 豐富的內建元件
- 跨平台相容性

**版本需求：**
- `textual >= 0.47.0`

### 布局設計

使用 Grid 布局：

```
┌─────────────────────────────┐
│         Header              │
├──────────────┬──────────────┤
│   Services   │   Robots     │
│  (col 1,     │  (col 2,     │
│   row 1-2)   │   row 1-2)   │
├──────────────┴──────────────┤
│      Command History        │
│      (col 1-2, row 3)       │
├─────────────────────────────┤
│      Command Input          │
│      (col 1-2, row 4)       │
├─────────────────────────────┤
│         Footer              │
└─────────────────────────────┘
```

## 事件處理

### 鍵盤事件

| 事件 | 處理方法 | 說明 |
|------|----------|------|
| `q` | `action_quit()` | 退出應用 |
| `r` | `action_refresh()` | 刷新所有狀態 |
| `s` | `action_services()` | 顯示服務詳情 |
| `Ctrl+C` | `action_quit()` | 強制退出 |
| `Enter` (in Input) | `on_input_submitted()` | 發送指令 |

### 狀態事件

透過 SharedStateManager 訂閱：

| 事件主題 | 處理方法 | 說明 |
|---------|----------|------|
| `ROBOT_STATUS_UPDATED` | `_on_robot_status_updated()` | 機器人狀態變更 |
| `COMMAND_COMPLETED` | `_on_command_completed()` | 指令執行完成 |

## 整合

### 與 ServiceCoordinator 整合

```python
# TUI 從 ServiceCoordinator 取得服務狀態
services_info = coordinator.get_all_services_info()
for service_name, info in services_info.items():
    widget.update_service_status(service_name, info.status)
```

### 與 SharedStateManager 整合

```python
# 訂閱機器人狀態更新
await state_manager.subscribe(
    EventTopics.ROBOT_STATUS_UPDATED,
    on_robot_status_updated
)

# 取得機器人狀態
robot_status = await state_manager.get(StateKeys.ROBOT_STATUS.format(robot_id="robot-001"))
```

### 與 CommandHistoryManager 整合

```python
# 查詢歷史記錄
history = history_manager.get_command_history(
    limit=20,
    sort_by="created_at",
    sort_order="desc"
)

# 顯示在 TUI 中
for record in history:
    widget.add_command(
        timestamp=record.created_at.strftime("%H:%M:%S"),
        robot_id=record.target_robot_id,
        action=record.command_params.get("action_name", "unknown"),
        status=record.status
    )
```

## 測試

### 單元測試

```bash
# 執行 TUI 模組測試
python3 -m pytest tests/test_tui.py -v
```

### 測試覆蓋範圍

- ✓ ServiceStatusWidget 初始化和狀態更新
- ✓ RobotStatusWidget 初始化和狀態更新
- ✓ CommandHistoryWidget 初始化和指令新增
- ✓ RobotConsoleTUI 初始化和依賴注入
- ✓ 服務狀態刷新

### 整合測試（計劃中）

- [ ] TUI 與 ServiceCoordinator 整合
- [ ] TUI 與 SharedStateManager 整合
- [ ] 鍵盤事件處理
- [ ] 定期更新機制

## 效能考量

### 記憶體使用

- 指令歷史限制為最近 20 筆
- 定期清理過期的快取資料

### 更新頻率

- 服務狀態：每 5 秒自動更新
- 機器人狀態：即時更新（事件驅動）
- 指令歷史：即時更新（事件驅動）

### 日誌處理

- 日誌輸出到檔案（`logs/tui.log`）避免干擾畫面
- 預設日誌等級：WARNING（可調整）

## 已知限制

1. **終端機相容性**
   - 需要支援 ANSI 顏色碼的終端機
   - 部分舊版終端機可能顯示異常

2. **指令發送**
   - 目前僅支援基本指令輸入
   - 尚未實作指令自動完成

3. **服務詳情**
   - 服務詳情彈窗功能尚未實作

## 未來改進

- [ ] 實作指令自動完成
- [ ] 新增歷史指令搜尋功能
- [ ] 實作服務詳細資訊彈窗
- [ ] 支援主題切換
- [ ] 新增更多鍵盤快捷鍵
- [ ] 實作分頁顯示（支援更多機器人）
- [ ] 新增設定檔案支援

## 相關文件

- [TUI_USER_GUIDE.md](../../docs/user_guide/TUI_USER_GUIDE.md) - 使用者指南
- [architecture.md](../../docs/architecture.md) - 系統架構
- [PHASE3_EDGE_ALL_IN_ONE.md](../../docs/plans/PHASE3_EDGE_ALL_IN_ONE.md) - Phase 3 規劃

## 貢獻指南

### 新增元件

1. 繼承 `textual.widgets.Static` 或其他基礎元件
2. 實作 `render()` 方法
3. 使用 `reactive` 屬性管理狀態
4. 新增對應的單元測試

### 新增鍵盤快捷鍵

1. 在 `RobotConsoleTUI.BINDINGS` 中定義綁定
2. 實作 `action_*()` 方法
3. 更新 Footer 顯示
4. 更新使用者文件

## 授權

與專案主體相同授權。
