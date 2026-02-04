# 進階指令解碼遷移指南

本指南說明如何從舊的 Robot-Console 進階指令解碼方式遷移到新的 WebUI 主導方式。

## 變更概要

**之前**：Robot-Console 負責解碼進階指令
**現在**：WebUI/上游服務負責展開進階指令，Robot-Console 只執行基礎動作列表

## 新的負載格式

### 推薦格式：預先解碼的動作列表

```json
{
  "actions": ["go_forward", "turn_left", "go_forward", "stand"]
}
```

每個動作名稱必須是 `action_executor.py` 中定義的有效基礎動作。

### 向後相容格式

#### 1. 單一動作（仍然支援）

```json
{
  "toolName": "go_forward"
}
```

#### 2. 舊式進階指令（需要啟用舊解碼器）

在 `settings.yaml` 中設定：
```yaml
enable_legacy_decoder: true
```

然後可以發送：
```json
{
  "type": "sequence",
  "steps": [
    {"action": "go_forward"},
    {"action": "turn_left"}
  ]
}
```

## WebUI 實作指南

### 1. 在 WebUI 中展開進階指令

當使用者選擇執行一個進階指令時，WebUI 應：

1. 從資料庫載入進階指令定義
2. 展開為基礎動作序列
3. 驗證每個動作都是有效的基礎動作
4. 發送格式化的負載到 Robot-Console

範例程式碼（Python/Flask）：

```python
def expand_advanced_command(command_id):
    """展開進階指令為基礎動作列表"""
    advanced_cmd = AdvancedCommand.query.get(command_id)
    
    # 假設 advanced_cmd.base_commands 包含動作序列
    actions = []
    for step in advanced_cmd.base_commands:
        if isinstance(step, dict) and 'action' in step:
            actions.append(step['action'])
    
    return actions

def send_to_robot(robot_id, command_id):
    """發送展開的指令到機器人"""
    actions = expand_advanced_command(command_id)
    
    payload = {
        "actions": actions
    }
    
    # 透過 MQTT 或其他協定發送到 Robot-Console
    publish_to_robot(robot_id, payload)
```

### 2. 驗證動作名稱

確保所有動作名稱都在允許的清單中：

```python
# 範例動作，完整清單請參考 Robot-Console/action_executor.py 中的 actions 字典
VALID_ACTIONS = [
    "go_forward", "turn_left", "stand", "stop"
    # ... 其餘動作請見 action_executor.py
]

def validate_actions(actions):
    """驗證動作列表"""
    for action in actions:
        if action not in VALID_ACTIONS:
            raise ValueError(f"無效的動作: {action}")
    return True
```

## 測試新格式

### 使用 MQTT 測試工具

```bash
# 發送新格式的指令
mosquitto_pub -h your-iot-endpoint \
  -p 8883 \
  --cert path/to/cert.pem.crt \
  --key path/to/private.pem.key \
  --cafile path/to/AmazonRootCA1.pem \
  -t "robot_7/topic" \
  -m '{"actions": ["bow", "wave", "stand"]}'
```

### 預期行為

Robot-Console 應該：
1. 接收包含 `actions` 的負載
2. 記錄：`"Processing pre-decoded actions list: ['bow', 'wave', 'stand']"`
3. 按順序執行每個動作
4. 不呼叫 AdvancedDecoder

## 故障排除

### 問題：Robot-Console 沒有執行動作

**檢查清單**：
1. 確認負載格式正確：`{"actions": ["action1", "action2"]}`
2. 確認所有動作名稱都是有效的基礎動作
3. 檢查 Robot-Console 日誌是否有錯誤訊息
4. 驗證 MQTT 連線正常

### 問題：仍然想使用舊的解碼器

如果需要暫時使用舊解碼器：

1. 在 `settings.yaml` 中設定：
```yaml
enable_legacy_decoder: true
```

2. 重新啟動 Robot-Console

3. 注意：這僅用於向後相容，不建議長期使用

## 優點

遷移到新架構的好處：

1. **更簡單的後端**：Robot-Console 邏輯更清晰，易於維護
2. **更靈活的前端**：WebUI 可以提供更好的 UX 來建立和管理命令序列
3. **更好的職責劃分**：每個模組職責明確
4. **更容易擴充**：在 WebUI 中添加新的進階指令功能更容易
5. **更好的效能**：減少 Robot-Console 的處理負擔

## 支援

如有問題，請參考：
- [module.md](module.md) - 完整模組設計說明
- [Robot-Console README](README.md) - 模組概述
- GitHub Issues - 報告問題或尋求協助
