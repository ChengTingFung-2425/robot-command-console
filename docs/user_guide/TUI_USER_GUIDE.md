# TUI 使用指南

## 概述

Robot Console TUI（Terminal User Interface）提供了一個終端機互動式介面，適用於無頭（headless）伺服器或容器環境。TUI 使用 [Textual](https://github.com/Textualize/textual) 框架建立，提供豐富的互動體驗。

## 功能特性

### 主要功能

1. **服務狀態監控**
   - 即時顯示所有服務狀態（MCP、Flask、Queue 等）
   - 顏色編碼狀態指示（綠色=運行中、紅色=錯誤、黃色=啟動中）
   - 服務健康檢查結果

2. **機器人狀態顯示**
   - 顯示所有連接的機器人
   - 即時電量百分比
   - 當前運行模式
   - 連接狀態指示

3. **指令歷史記錄**
   - 顯示最近 20 條執行的指令
   - 包含時間戳、目標機器人、動作名稱和執行狀態
   - 支援滾動查看

4. **指令輸入**
   - 直接在終端輸入指令
   - 即時發送到機器人執行
   - 自動更新執行結果

### 鍵盤快捷鍵

| 快捷鍵 | 功能 | 說明 |
|--------|------|------|
| `q` | 退出 | 關閉 TUI 並停止所有服務 |
| `r` | 刷新 | 手動刷新所有狀態資訊 |
| `s` | 服務詳情 | 顯示服務詳細資訊（計劃中） |
| `Ctrl+C` | 退出 | 快速退出程式 |

## 安裝

### 依賴安裝

TUI 依賴 `textual` 函式庫，請確保已安裝：

```bash
pip install -r requirements.txt
```

或單獨安裝：

```bash
pip install textual>=0.47.0
```

## 使用方式

### 基本啟動

```bash
# 使用預設設定啟動 TUI
python3 run_tui.py
```

### 自訂參數

```bash
# 指定佇列大小和工作執行緒數
python3 run_tui.py --queue-size 2000 --workers 10

# 調整健康檢查間隔
python3 run_tui.py --health-check-interval 60

# 設定日誌等級（日誌會輸出到檔案避免干擾 TUI）
python3 run_tui.py --log-level INFO

# 指定指令歷史資料庫路徑
python3 run_tui.py --history-db /path/to/history.db
```

### 完整參數說明

```
python3 run_tui.py --help

選項：
  --queue-size SIZE         佇列最大容量（預設：1000）
  --workers NUM             工作執行緒數量（預設：5）
  --poll-interval SECONDS   佇列輪詢間隔（預設：0.1 秒）
  --health-check-interval SECONDS
                           健康檢查間隔（預設：30 秒）
  --log-level LEVEL        日誌等級（DEBUG/INFO/WARNING/ERROR/CRITICAL，預設：WARNING）
  --history-db PATH        指令歷史資料庫路徑（預設：data/command_history.db）
  -h, --help               顯示幫助訊息
```

## TUI 畫面說明

```
┌─────────────────────────────────────────────────────────────────────┐
│  Robot Console Edge - Terminal UI                    [q: quit]       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Services                          │ Robot Status                    │
│  ─────────────────────────────    │ ─────────────────────────────  │
│  ● MCP Service     [running]      │ 🤖 robot-001  [connected]      │
│  ● Flask API       [running]      │    Battery: 85%                │
│  ● Queue Service   [running]      │    Mode: Standby               │
│  ○ LLM Provider    [not running]  │                                 │
│                                    │ 🤖 robot-002  [disconnected]  │
│                                    │                                 │
├────────────────────────────────────┴────────────────────────────────┤
│  Command History                                                     │
│  ─────────────────────────────────────────────────────────────────  │
│  [10:23:45] robot-001: go_forward (success)                         │
│  [10:23:48] robot-001: turn_left (success)                          │
│  [10:24:01] robot-001: stand (success)                              │
│                                                                      │
├─────────────────────────────────────────────────────────────────────┤
│  > Enter command: _                                                  │
└─────────────────────────────────────────────────────────────────────┘
```

### 區域說明

1. **標題列**（Header）
   - 顯示應用名稱和當前時間
   - 提示可用的快捷鍵

2. **左上區域：服務狀態**
   - 列出所有已註冊的服務
   - 狀態指示符：
     - `●` 綠色：運行中
     - `○` 灰色：已停止
     - `◐` 黃色：啟動中
     - `◑` 黃色：停止中
     - `✗` 紅色：錯誤

3. **右上區域：機器人狀態**
   - 顯示所有機器人的連接狀態
   - 包含電量、模式等詳細資訊
   - 圖示：
     - `🤖` 已連接
     - `⚠️` 未連接

4. **中間區域：指令歷史**
   - 滾動顯示最近 20 條指令
   - 格式：`[時間] 機器人ID: 動作 (狀態)`
   - 顏色編碼：
     - 綠色：成功
     - 紅色：失敗

5. **底部區域：指令輸入**
   - 輸入欄位，按 `Enter` 發送指令
   - 自動清空輸入內容

6. **底部列**（Footer）
   - 顯示所有可用的鍵盤快捷鍵

## 發送指令

### 基本指令

在指令輸入欄位中輸入動作名稱，按 `Enter` 發送：

```
go_forward
turn_left
stand
wave_hand
```

### 指定機器人

預設指令會發送到 `robot-001`。如需指定其他機器人，請使用以下格式：

```
robot-002:go_forward
robot-003:turn_left
```

### 廣播指令到所有機器人

使用 `all:` 前綴可同時對所有連接的機器人執行相同動作：

```
all:stand
all:wave_hand
all:go_forward
```

這在需要同步控制多個機器人時非常有用，例如：
- 集體表演或展示
- 緊急停止所有機器人
- 統一初始化動作

**注意**：廣播指令會並行發送到所有機器人，執行時間取決於最慢的機器人。

### 指令格式總結

| 格式 | 範例 | 說明 |
|------|------|------|
| `action` | `go_forward` | 發送到預設機器人 (robot-001) |
| `robot-id:action` | `robot-002:turn_left` | 發送到指定機器人 |
| `all:action` | `all:stand` | 廣播到所有機器人 |

### 進階功能（計劃中）

- 指令自動完成
- 歷史指令搜尋
- 批次指令執行
- 條件執行（僅對特定狀態的機器人執行）

## 日誌輸出

TUI 模式下，為避免日誌輸出干擾畫面顯示，所有日誌會輸出到檔案：

```
logs/tui.log
```

可使用其他終端視窗即時查看日誌：

```bash
tail -f logs/tui.log
```

## 疑難排解

### TUI 無法啟動

1. **檢查依賴安裝**
   ```bash
   python3 -c "import textual; print(textual.__version__)"
   ```

2. **檢查終端機支援**
   - TUI 需要支援 ANSI 顏色碼的終端機
   - 建議使用：xterm、iTerm2、Windows Terminal

### 服務無法啟動

1. **檢查埠號衝突**
   - 確保 5000（Flask）和 8000（MCP）埠未被佔用

2. **查看日誌**
   ```bash
   cat logs/tui.log
   ```

### 機器人未顯示

1. **檢查機器人連接**
   - 確保機器人服務已啟動並配置正確

2. **手動刷新**
   - 按 `r` 鍵強制刷新狀態

## 與其他模式比較

| 功能 | TUI | CLI | GUI (Electron) | WebUI |
|------|-----|-----|----------------|-------|
| 視覺化介面 | ✓ | ✗ | ✓ | ✓ |
| 即時狀態更新 | ✓ | 部分 | ✓ | ✓ |
| 互動式指令輸入 | ✓ | ✓ | ✓ | ✓ |
| 資源使用 | 低 | 極低 | 中 | 低 |
| 適用環境 | 終端機 | 無頭伺服器 | 桌面 | 瀏覽器 |
| 遠端存取 | SSH 支援 | SSH 支援 | ✗ | ✓ |

## 未來規劃

- [ ] 指令自動完成功能
- [ ] 歷史指令搜尋與過濾
- [ ] 服務詳細資訊彈窗
- [ ] 機器人詳細資訊檢視
- [ ] 主題與配色方案自訂
- [ ] 多語言支援

## 相關文件

- [architecture.md](../architecture.md) - 系統架構說明
- [PHASE3_EDGE_ALL_IN_ONE.md](../plans/PHASE3_EDGE_ALL_IN_ONE.md) - Phase 3 規劃
- [Textual 官方文檔](https://textual.textualize.io/)

## 授權

與專案主體相同授權。
