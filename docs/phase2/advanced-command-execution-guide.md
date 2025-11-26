# 進階指令執行功能使用指南

本指南說明如何使用 WebUI 的進階指令執行功能，將進階指令展開並發送到機器人執行。

## 功能概述

進階指令執行功能允許用戶：
1. 選擇已批准的進階指令
2. 指定目標機器人
3. 系統自動展開為基礎動作序列
4. 透過 MQTT 發送到 Robot-Console 執行佇列

## 使用流程

### 1. 建立進階指令

首先需要建立並獲得批准的進階指令：

```json
{
  "name": "patrol_routine",
  "description": "巡邏例行程序",
  "category": "patrol",
  "base_commands": [
    {"command": "go_forward"},
    {"command": "turn_left"},
    {"command": "go_forward"},
    {"command": "turn_right"},
    {"command": "stand"}
  ]
}
```

### 2. 執行進階指令

使用 API 端點執行：

```bash
curl -X POST http://localhost:5000/advanced_commands/1/execute \
  -H "Content-Type: application/json" \
  -H "Cookie: session=YOUR_SESSION_COOKIE" \
  -d '{
    "robot_id": 1
  }'
```

**成功回應**：
```json
{
  "success": true,
  "message": "已透過 MQTT 發送 5 個動作到機器人 robot_7",
  "command_id": 123,
  "details": {
    "robot_id": 1,
    "robot_name": "robot_7",
    "actions_count": 5,
    "actions": ["go_forward", "turn_left", "go_forward", "turn_right", "stand"],
    "transport": "MQTT"
  }
}
```

## MQTT 配置

### 生產環境配置

1. **設定環境變數**：

```bash
export MQTT_ENABLED=true
export MQTT_BROKER=a1qlex7vqi1791-ats.iot.us-east-1.amazonaws.com
export MQTT_PORT=8883
export MQTT_CERT_PATH=/app/certificates
export MQTT_CA_CERT=AmazonRootCA1.pem
```

2. **準備憑證檔案**：

確保憑證結構如下：
```
certificates/
├── AmazonRootCA1.pem
└── {robot_name}/
    ├── {robot_name}.cert.pem
    └── {robot_name}.private.key
```

### 測試環境配置

測試環境可以不啟用 MQTT（預設），系統會使用備用方案：

```bash
# MQTT_ENABLED 預設為 false
# 系統會記錄動作到日誌但不實際發送
```

## 訊息流程

```
1. WebUI 接收執行請求
   POST /advanced_commands/1/execute
   
2. 驗證與展開
   - 檢查用戶權限
   - 檢查指令狀態（must be 'approved'）
   - 展開進階指令為動作列表
   
3. MQTT 發送
   - 連接到 AWS IoT MQTT broker
   - 構建訊息：{"actions": ["go_forward", ...]}
   - 發布到主題：{robot_name}/topic
   - QoS: AT_LEAST_ONCE
   
4. Robot-Console 接收
   - pubsub.py 訂閱主題
   - 解析 actions 陣列
   - 加入執行佇列
   
5. ActionExecutor 執行
   - 依序執行每個動作
   - 回報執行狀態
```

## 權限要求

執行進階指令需要：
- ✅ 用戶已登入
- ✅ 進階指令狀態為 `approved`
- ✅ 用戶擁有目標機器人，或
- ✅ 用戶具有 admin/auditor 角色

## 錯誤處理

### 常見錯誤

**403 Forbidden - 未批准的指令**：
```json
{
  "success": false,
  "message": "只能執行已批准的進階指令（當前狀態：pending）"
}
```

**403 Forbidden - 無權限**：
```json
{
  "success": false,
  "message": "您沒有權限控制此機器人"
}
```

**400 Bad Request - 缺少參數**：
```json
{
  "success": false,
  "message": "缺少必要參數：robot_id"
}
```

**400 Bad Request - 格式錯誤**：
```json
{
  "success": false,
  "message": "展開進階指令失敗，請檢查指令格式是否正確"
}
```

**500 Internal Server Error - 發送失敗**：
```json
{
  "success": false,
  "message": "發送指令到機器人失敗，請稍後再試"
}
```

## 監控與日誌

### 查看執行日誌

伺服器日誌會記錄：
- 進階指令展開過程
- MQTT 連接狀態
- 訊息發送結果
- 詳細錯誤資訊（包含堆疊追蹤）

### 查詢執行歷史

每次執行都會在資料庫中建立 Command 記錄：

```sql
SELECT * FROM command 
WHERE nested_command = true 
ORDER BY timestamp DESC;
```

## 故障排除

### MQTT 連接失敗

**症狀**：訊息顯示 "transport": "pending"

**可能原因**：
1. MQTT_ENABLED 未設定為 true
2. 憑證檔案路徑錯誤
3. 憑證檔案權限不足
4. AWS IoT Core 防火牆規則

**解決方法**：
```bash
# 檢查環境變數
echo $MQTT_ENABLED

# 檢查憑證檔案
ls -la $MQTT_CERT_PATH/{robot_name}/

# 檢查日誌
tail -f logs/microblog.log | grep MQTT
```

### 進階指令格式錯誤

**症狀**：400 錯誤，展開失敗

**可能原因**：
1. base_commands 不是有效的 JSON
2. 指令陣列格式錯誤
3. 包含無效的動作名稱

**解決方法**：
確保 base_commands 格式正確：
```json
[
  {"command": "go_forward"},
  {"command": "turn_left"}
]
```

## 測試

執行測試套件：

```bash
# 執行所有進階指令測試
python -m pytest tests/test_advanced_command_execution.py -v

# 執行特定測試
python -m pytest tests/test_advanced_command_execution.py::TestAdvancedCommandExecution::test_execute_advanced_command_success -v
```

## 安全性

本功能包含以下安全措施：

✅ **權限驗證**：確保用戶有權控制目標機器人  
✅ **狀態檢查**：只執行已批准的進階指令  
✅ **錯誤脫敏**：敏感錯誤資訊不暴露給用戶  
✅ **動作驗證**：只允許有效的基礎動作  
✅ **日誌審計**：所有操作都記錄到日誌  

## 參考資料

- [WebUI Module 文檔](../WebUI/Module.md)
- [進階指令職責變更說明](ADVANCED_COMMAND_RESPONSIBILITY_CHANGE.md)
- [Robot-Console 遷移指南](../Robot-Console/MIGRATION_GUIDE.md)
- [API 測試](../tests/test_advanced_command_execution.py)
