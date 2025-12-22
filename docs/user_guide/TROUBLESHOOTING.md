# 疑難排解指南

> **最後更新**：2025-12-22  
> **適用版本**：v1.0.0+

本指南幫助您診斷和解決使用 Robot Command Console 時遇到的問題。

---

## 📑 目錄

- [診斷工具](#診斷工具)
- [安裝問題](#安裝問題)
- [啟動問題](#啟動問題)
- [連線問題](#連線問題)
- [執行問題](#執行問題)
- [效能問題](#效能問題)
- [日誌分析](#日誌分析)

---

## 診斷工具

### 健康檢查

快速檢查系統狀態：

```bash
# 檢查所有服務健康狀態
curl http://localhost:5000/health
curl http://localhost:8000/health

# 查看詳細指標
curl http://localhost:5000/metrics
```

預期輸出：
```json
{
  "status": "healthy",
  "services": {
    "database": "ok",
    "queue": "ok",
    "robot_connection": "ok"
  },
  "uptime": 3600
}
```

---

### 日誌收集

收集完整的診斷資訊：

```bash
# 建立診斷報告
./scripts/collect_diagnostics.sh

# 或手動收集
mkdir -p /tmp/diagnostics
cp logs/*.log /tmp/diagnostics/
curl http://localhost:5000/health > /tmp/diagnostics/health.json
curl http://localhost:5000/metrics > /tmp/diagnostics/metrics.txt
```

---

## 安裝問題

### 問題：Python 版本不相容

**症狀**：
```
ERROR: This package requires Python 3.10 or later
```

**診斷**：
```bash
python3 --version
```

**解決方案**：
1. 安裝 Python 3.10 或更新版本
2. 使用 pyenv 管理多版本 Python：
```bash
# 安裝 pyenv
curl https://pyenv.run | bash

# 安裝 Python 3.11
pyenv install 3.11.0
pyenv global 3.11.0
```

---

### 問題：依賴套件安裝失敗

**症狀**：
```
ERROR: Could not build wheels for <package>
```

**診斷**：
```bash
# 檢查 pip 版本
pip --version

# 檢查系統套件
dpkg -l | grep python3-dev  # Debian/Ubuntu
rpm -qa | grep python3-devel  # Fedora/RHEL
```

**解決方案**：

**Ubuntu/Debian**：
```bash
sudo apt-get update
sudo apt-get install python3-dev python3-pip build-essential
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

**macOS**：
```bash
brew install python@3.11
pip3 install --upgrade pip
pip3 install -r requirements.txt
```

**Windows**：
```powershell
# 安裝 Microsoft C++ Build Tools
# https://visualstudio.microsoft.com/visual-cpp-build-tools/

# 升級 pip
python -m pip install --upgrade pip
pip install -r requirements.txt
```

---

### 問題：npm 套件安裝失敗

**症狀**：
```
npm ERR! code EACCES
npm ERR! permission denied
```

**解決方案**：

```bash
# 不要使用 sudo npm install！

# 方法 1：修正 npm 權限
mkdir ~/.npm-global
npm config set prefix '~/.npm-global'
echo 'export PATH=~/.npm-global/bin:$PATH' >> ~/.bashrc
source ~/.bashrc

# 方法 2：使用 nvm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
nvm install 18
nvm use 18
npm install
```

---

## 啟動問題

### 問題：埠號被佔用

**症狀**：
```
Error: listen EADDRINUSE: address already in use :::5000
```

**診斷**：
```bash
# Linux/macOS
lsof -i :5000
netstat -tuln | grep 5000

# Windows
netstat -ano | findstr :5000
```

**解決方案**：

**方法 1：停止佔用埠號的程式**
```bash
# Linux/macOS
lsof -ti :5000 | xargs kill -9

# Windows
netstat -ano | findstr :5000
# 記下 PID
taskkill /PID <PID> /F
```

**方法 2：使用不同埠號**
```bash
# 設定環境變數
export FLASK_PORT=5001
export MCP_PORT=8001
export WEBUI_PORT=8081

python3 start_all_services.py
```

---

### 問題：服務啟動但無回應

**症狀**：
- 啟動訊息顯示成功
- 但無法存取 URL

**診斷**：
```bash
# 檢查程序是否運行
ps aux | grep "flask_service\|start.py"

# 檢查埠號監聽
netstat -tuln | grep -E '5000|8000|8080'

# 測試連線
curl -v http://localhost:5000/health
```

**解決方案**：

1. **檢查防火牆**：
```bash
# Linux - 允許埠號
sudo ufw allow 5000
sudo ufw allow 8000
sudo ufw allow 8080

# 查看狀態
sudo ufw status
```

2. **檢查綁定地址**：
```python
# flask_service.py 應該綁定到 0.0.0.0
app.run(host='0.0.0.0', port=5000)  # ✅ 正確
app.run(host='127.0.0.1', port=5000)  # ❌ 僅本機
```

3. **查看詳細日誌**：
```bash
tail -f logs/flask.log
tail -f logs/mcp.log
```

---

### 問題：資料庫初始化失敗

**症狀**：
```
sqlite3.OperationalError: unable to open database file
```

**診斷**：
```bash
# 檢查資料庫目錄權限
ls -la data/
ls -la data/app.db

# 檢查磁碟空間
df -h
```

**解決方案**：

```bash
# 建立資料目錄
mkdir -p data

# 修正權限
chmod 755 data
chmod 644 data/app.db  # 如果檔案存在

# 重新初始化
rm -f data/app.db
python3 -c "from WebUI.app import db; db.create_all()"
```

---

## 連線問題

### 問題：無法連接機器人

**症狀**：
```
ConnectionError: Unable to connect to robot at 192.168.1.100:8080
```

**診斷流程**：

**1. 網路連線測試**：
```bash
# Ping 測試
ping 192.168.1.100

# 埠號測試
telnet 192.168.1.100 8080
# 或
nc -zv 192.168.1.100 8080
```

**2. 路由追蹤**：
```bash
traceroute 192.168.1.100
# Windows
tracert 192.168.1.100
```

**3. DNS 解析**（如果使用主機名稱）：
```bash
nslookup robot-hostname
dig robot-hostname
```

**解決方案**：

**網路隔離問題**：
```bash
# 檢查是否在同一子網路
ip addr show  # Linux
ipconfig /all  # Windows

# 測試跨子網路路由
ping -c 4 192.168.1.1  # 閘道
```

**防火牆問題**：
```bash
# 檢查機器人防火牆
# 在機器人上執行：
sudo ufw status
sudo iptables -L -n

# 檢查本機防火牆
sudo ufw allow from 192.168.1.100
```

---

### 問題：MQTT 連線失敗

**症狀**：
```
paho.mqtt.client.MQTTException: Connection refused
```

**診斷**：
```bash
# 測試 MQTT broker
mosquitto_sub -h localhost -t test -v

# 或使用 MQTT Explorer（GUI 工具）
```

**解決方案**：

**1. 確認 broker 運行**：
```bash
# 啟動 Mosquitto
sudo systemctl start mosquitto
sudo systemctl status mosquitto

# 或使用 Docker
docker run -it -p 1883:1883 eclipse-mosquitto
```

**2. 檢查認證**：
```python
# config.py
MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_USERNAME = "your-username"  # 如果需要
MQTT_PASSWORD = "your-password"  # 如果需要
```

---

### 問題：WebSocket 連線中斷

**症狀**：
```
WebSocket connection closed: 1006
```

**診斷**：
```bash
# 使用 wscat 測試
npm install -g wscat
wscat -c ws://localhost:8080/ws

# 或使用 Python
python3 -c "
import websocket
ws = websocket.create_connection('ws://localhost:8080/ws')
print(ws.recv())
ws.close()
"
```

**解決方案**：

**1. 代理伺服器問題**：
```nginx
# Nginx 配置
location /ws {
    proxy_pass http://localhost:8080;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_read_timeout 86400;
}
```

**2. 逾時設定**：
```python
# 增加 WebSocket 逾時
WEBSOCKET_PING_INTERVAL = 20
WEBSOCKET_PING_TIMEOUT = 10
```

---

## 執行問題

### 問題：指令執行超時

**症狀**：
```
TimeoutError: Command execution timed out after 30s
```

**診斷**：
```bash
# 檢查網路延遲
ping -c 10 192.168.1.100 | tail -1

# 檢查機器人負載
# 在機器人上執行
top
htop
```

**解決方案**：

**1. 增加 timeout**：
```python
# 在指令請求中設定
{
    "action": "complex_action",
    "timeout_ms": 60000  # 60 秒
}
```

**2. 優化網路**：
```bash
# 使用有線連線而非 WiFi
# 減少網路跳數
# 確保機器人與控制端在同一交換機
```

**3. 分解複雜指令**：
```json
// ❌ 單一複雜指令
{"action": "complex_sequence"}

// ✅ 拆分為多個簡單指令
[
  {"action": "step1"},
  {"action": "step2"},
  {"action": "step3"}
]
```

---

### 問題：指令執行失敗但無錯誤訊息

**症狀**：
- 指令標記為失敗
- 但 error 欄位為空

**診斷**：
```bash
# 查看詳細日誌
tail -f logs/robot_service.log | grep ERROR

# 查看機器人端日誌（如果可存取）
ssh robot@192.168.1.100
tail -f /var/log/robot_api.log
```

**解決方案**：

**1. 啟用詳細日誌**：
```bash
export LOG_LEVEL=DEBUG
python3 start_all_services.py
```

**2. 檢查機器人狀態**：
```bash
# 查詢機器人狀態
curl http://192.168.1.100:8080/status
```

**3. 驗證指令格式**：
```python
# 確保指令符合 JSON Schema
from jsonschema import validate

command = {
    "action": "go_forward",
    "target": "robot-001"
}

validate(command, command_schema)
```

---

### 問題：批次指令部分失敗

**症狀**：
```
Batch execution completed with errors: 3/10 commands failed
```

**診斷**：
```bash
# 查看批次執行日誌
cat logs/batch_execution_*.log

# 檢查失敗的指令
grep "FAILED" logs/batch_execution_*.log
```

**解決方案**：

**1. 啟用容錯模式**：
```python
{
    "commands": [...],
    "options": {
        "continue_on_error": true,  # 繼續執行後續指令
        "retry_failed": true,        # 重試失敗指令
        "max_retries": 3
    }
}
```

**2. 增加指令間延遲**：
```python
{
    "commands": [
        {"action": "step1"},
        {"action": "step2", "delay_ms": 1000},  # 延遲 1 秒
        {"action": "step3"}
    ]
}
```

---

## 效能問題

### 問題：系統回應緩慢

**診斷**：

**1. 檢查 CPU 使用率**：
```bash
# Linux
top
htop

# 查看特定程序
ps aux | grep python | sort -nrk 3 | head -5
```

**2. 檢查記憶體使用**：
```bash
free -h
vmstat 1 5

# Python 記憶體分析
python3 -m memory_profiler flask_service.py
```

**3. 檢查磁碟 I/O**：
```bash
iostat -x 1 5
iotop
```

**4. 檢查資料庫效能**：
```bash
# SQLite 分析
sqlite3 data/app.db "ANALYZE;"
sqlite3 data/app.db ".schema"

# 查看慢查詢
export SQLALCHEMY_ECHO=True
```

**解決方案**：

**1. 增加 Worker 數量**：
```bash
python3 run_service_cli.py --workers 10
```

**2. 啟用快取**：
```python
# config.py
CACHE_TYPE = "simple"
CACHE_DEFAULT_TIMEOUT = 300
```

**3. 資料庫優化**：
```sql
-- 建立索引
CREATE INDEX idx_commands_timestamp ON commands(timestamp);
CREATE INDEX idx_commands_status ON commands(status);

-- 清理舊資料
DELETE FROM commands WHERE timestamp < datetime('now', '-30 days');
VACUUM;
```

**4. 限制日誌大小**：
```python
# logging_config.py
LOGGING = {
    'handlers': {
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/app.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5
        }
    }
}
```

---

### 問題：記憶體洩漏

**症狀**：
- 記憶體使用持續增長
- 最終導致系統無回應

**診斷**：
```bash
# 監控記憶體使用
watch -n 1 'ps aux | grep python'

# 使用 memory_profiler
pip install memory_profiler
python3 -m memory_profiler flask_service.py
```

**解決方案**：

**1. 定期重啟服務**：
```bash
# 使用 systemd timer 或 cron
# /etc/systemd/system/robot-console-restart.timer
[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
```

**2. 限制快取大小**：
```python
from cachetools import LRUCache

cache = LRUCache(maxsize=1000)
```

**3. 清理閒置連線**：
```python
# 使用連線池
SQLALCHEMY_POOL_SIZE = 10
SQLALCHEMY_POOL_RECYCLE = 3600
SQLALCHEMY_POOL_PRE_PING = True
```

---

## 日誌分析

### 日誌位置

```
logs/
├── flask.log           # Flask API 日誌
├── mcp.log            # MCP 服務日誌
├── queue.log          # Queue 服務日誌
├── robot_service.log  # Robot Service 日誌
├── tui.log            # TUI 介面日誌
└── error.log          # 錯誤匯總
```

---

### 常見錯誤模式

**1. 連線錯誤**：
```
ERROR: ConnectionRefusedError: [Errno 111] Connection refused
```
→ 檢查目標服務是否運行、防火牆設定

**2. 認證失敗**：
```
ERROR: 401 Unauthorized: Invalid or expired token
```
→ 檢查 token 是否正確、是否已過期

**3. 資源不足**：
```
ERROR: OSError: [Errno 24] Too many open files
```
→ 增加檔案描述符限制：`ulimit -n 4096`

**4. 資料庫鎖定**：
```
ERROR: sqlite3.OperationalError: database is locked
```
→ 使用 WAL 模式或切換到 PostgreSQL

---

### 日誌分析工具

**grep 快速搜尋**：
```bash
# 查找所有錯誤
grep -r "ERROR" logs/

# 查找特定機器人的日誌
grep "robot-001" logs/*.log

# 查找最近 1 小時的錯誤
find logs/ -name "*.log" -mmin -60 -exec grep "ERROR" {} +

# 統計錯誤類型
grep "ERROR" logs/*.log | cut -d: -f2 | sort | uniq -c | sort -nr
```

**結構化日誌查詢**：
```bash
# 安裝 jq
sudo apt-get install jq

# 查詢 JSON 日誌
cat logs/flask.log | jq 'select(.level == "ERROR")'
cat logs/flask.log | jq 'select(.timestamp > "2025-12-22T00:00:00")'
```

**日誌聚合（進階）**：
```bash
# 使用 lnav（log navigator）
sudo apt-get install lnav
lnav logs/*.log

# 使用 GoAccess（Web UI）
goaccess logs/access.log -o report.html --log-format=COMBINED
```

---

## 取得進階支援

如果以上方法都無法解決問題：

### 1. 收集診斷資訊

```bash
# 建立完整診斷報告
./scripts/collect_diagnostics.sh

# 包含：
# - 所有日誌檔案
# - 系統資訊
# - 服務狀態
# - 配置檔案（已脫敏）
```

### 2. 回報問題

前往 [GitHub Issues](https://github.com/ChengTingFung-2425/robot-command-console/issues/new) 並提供：

- **問題描述**：詳細說明問題
- **重現步驟**：如何觸發問題
- **預期行為**：應該如何運作
- **實際行為**：實際發生什麼
- **環境資訊**：
  - 作業系統與版本
  - Python 版本
  - 應用程式版本
- **日誌與截圖**：附上相關日誌片段

### 3. 社群支援

- [GitHub Discussions](https://github.com/ChengTingFung-2425/robot-command-console/discussions) - 提問與討論
- 查看已關閉的 Issues - 可能有類似問題的解決方案

---

**回到索引**：[用戶指南索引](USER_GUIDE_INDEX.md)

**最後更新**：2025-12-22
