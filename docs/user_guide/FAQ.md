# 常見問題與解答（FAQ）

> **最後更新**：2025-12-22  
> **適用版本**：v1.0.0+

本文件收錄使用 Robot Command Console 時最常遇到的問題與解答。

---

## 📑 目錄

- [安裝與啟動](#安裝與啟動)
- [機器人連接](#機器人連接)
- [指令執行](#指令執行)
- [LLM 功能](#llm-功能)
- [服務管理](#服務管理)
- [效能與資源](#效能與資源)
- [安全性](#安全性)
- [更新與升級](#更新與升級)

---

## 安裝與啟動

### Q1: 我應該選擇 Heavy 還是 Tiny 版本？

**A:** 依據您的使用場景選擇：

| 選擇 Heavy | 選擇 Tiny |
|-----------|----------|
| 開發者或進階使用者 | 生產環境部署 |
| 需要完整 UI 互動 | 資源受限設備 |
| RAM ≥ 4GB | RAM < 4GB |
| 需要 DevTools 調試 | 只需核心功能 |

📖 詳細對比：[版本選擇指引](TINY_VS_HEAVY.md)

---

### Q2: 啟動時顯示「埠號被佔用」怎麼辦？

**A:** 預設使用以下埠號：
- Flask API: `5000`
- MCP Service: `8000`
- WebUI: `8080`

**解決方法**：

**方法 1**：停止佔用埠號的程式
```bash
# Linux/macOS - 查找佔用埠號的程式
lsof -i :5000
lsof -i :8000

# Windows - 查找並結束
netstat -ano | findstr :5000
taskkill /PID <PID> /F
```

**方法 2**：使用環境變數指定其他埠號
```bash
# 設定環境變數
export FLASK_PORT=5001
export MCP_PORT=8001
export WEBUI_PORT=8081

# 啟動應用
python3 start_all_services.py
```

---

### Q3: macOS 提示「無法打開，因為來自未識別的開發者」

**A:** 這是 macOS Gatekeeper 的安全機制。

**解決步驟**：
1. 按住 `Control` 鍵點擊應用程式
2. 選擇「打開」
3. 在彈出視窗點擊「打開」確認

**或使用終端機**：
```bash
sudo xattr -rd com.apple.quarantine /Applications/TinyEdgeApp.app
```

---

### Q4: Windows Defender 阻止應用程式執行

**A:** 這是正常的 SmartScreen 保護。

**解決步驟**：
1. 點擊「更多資訊」
2. 點擊「仍要執行」

如果您擔心安全性，可以：
- 查看 [GitHub Actions](https://github.com/ChengTingFung-2425/robot-command-console/actions) 的建置日誌
- 從原始碼自行建置：`python qtwebview-app/main.py`

---

### Q5: Linux 啟動時缺少依賴庫

**A:** 需要安裝 Qt WebEngine 相關系統套件。

**Ubuntu/Debian**：
```bash
sudo apt-get update
sudo apt-get install libxcb-xinerama0 libxcb-cursor0 \
  libqt5webengine5 libqt5webenginewidgets5
```

**Fedora/RHEL**：
```bash
sudo dnf install xcb-util-cursor qt5-qtwebengine
```

**Arch Linux**：
```bash
sudo pacman -S qt5-webengine
```

---

## 機器人連接

### Q6: 如何連接我的機器人？

**A:** 連接步驟：

1. 確認機器人與電腦在同一網路
2. 在 WebUI 進入「機器人」頁面
3. 點擊「新增機器人」
4. 填寫資訊：
   - **名稱**：自訂識別名稱（例如：`robot-001`）
   - **IP 地址**：機器人的 IP（例如：`192.168.1.100`）
   - **埠號**：通訊埠（預設 `8080`）
   - **協定**：選擇 HTTP、MQTT 或 WebSocket
5. 點擊「測試連線」
6. 連線成功後點擊「儲存」

---

### Q7: 機器人連線失敗怎麼辦？

**A:** 依序檢查：

**1. 網路連線**：
```bash
# 測試能否 ping 到機器人
ping 192.168.1.100

# 測試埠號是否開放
telnet 192.168.1.100 8080
# 或使用 nc
nc -zv 192.168.1.100 8080
```

**2. 防火牆設定**：
- 確認防火牆允許對應埠號
- Windows：檢查 Windows Defender 防火牆
- Linux：檢查 `iptables` 或 `firewalld`
- 路由器：檢查是否有網路隔離

**3. 機器人狀態**：
- 確認機器人電源已開啟
- 檢查機器人的 API 服務是否正常運行
- 查看機器人日誌是否有錯誤

**4. 協定設定**：
- HTTP：確認 URL 格式正確（例如：`http://192.168.1.100:8080`）
- MQTT：檢查 broker 地址和認證
- WebSocket：檢查 WS/WSS 協定

---

### Q8: 支援哪些機器人協定？

**A:** 目前支援：

| 協定 | 適用場景 | 配置難度 |
|------|----------|----------|
| **HTTP** | 簡單的 REST API | ⭐ 簡單 |
| **MQTT** | 分散式環境、IoT | ⭐⭐ 中等 |
| **WebSocket** | 即時雙向通訊 | ⭐⭐ 中等 |
| **Serial** | 直連硬體（開發中） | ⭐⭐⭐ 進階 |
| **ROS** | ROS 生態系統（規劃中） | ⭐⭐⭐ 進階 |

---

### Q9: 可以同時控制多個機器人嗎？

**A:** 可以！Robot Command Console 支援多機器人管理。

**單一指令**：
- WebUI：選擇目標機器人後執行指令
- TUI：使用 `robot-002:go_forward` 格式指定機器人

**廣播指令**（所有機器人同時執行）：
- TUI：使用 `all:stand` 格式
- WebUI：選擇「所有機器人」選項

**批次指令**：
```json
{
  "commands": [
    {"target": "robot-001", "action": "go_forward"},
    {"target": "robot-002", "action": "turn_left"},
    {"target": "robot-003", "action": "wave_hand"}
  ]
}
```

---

## 指令執行

### Q10: 為什麼指令執行失敗？

**A:** 常見原因與解決方法：

| 錯誤訊息 | 原因 | 解決方法 |
|----------|------|----------|
| `Timeout` | 機器人回應超時 | 檢查網路連線、增加 timeout 值 |
| `Invalid action` | 指令不存在 | 檢查拼寫、查看支援的指令列表 |
| `Permission denied` | 權限不足 | 確認使用者角色與權限 |
| `Robot busy` | 機器人正在執行其他任務 | 等待完成或取消現有任務 |
| `Connection refused` | 無法連接機器人 | 檢查機器人狀態與網路 |

---

### Q11: 支援哪些基本指令？

**A:** 常用基本指令：

**移動類**：
- `go_forward` - 向前移動
- `go_backward` - 向後移動
- `turn_left` - 左轉
- `turn_right` - 右轉
- `stop` - 停止

**姿勢類**：
- `stand` - 站立
- `sit` - 坐下
- `wave_hand` - 揮手
- `nod_head` - 點頭
- `shake_head` - 搖頭

**系統類**：
- `get_status` - 獲取狀態
- `get_battery` - 查詢電量
- `reset` - 重置

> 💡 具體支援的指令取決於您的機器人型號。

---

### Q12: 如何撤銷或取消正在執行的指令？

**A:** 取消方法：

**WebUI / Heavy / Tiny**：
1. 前往「指令歷史」頁面
2. 找到正在執行的指令
3. 點擊「取消」按鈕

**TUI**：
```
system:cancel <command_id>
```

**緊急停止（所有機器人）**：
```
all:stop
```

---

### Q13: 可以排程指令嗎？

**A:** 可以！使用批次指令功能：

**方法 1：時間延遲**
```json
{
  "commands": [
    {"action": "stand", "delay_ms": 0},
    {"action": "wave_hand", "delay_ms": 2000},
    {"action": "go_forward", "delay_ms": 5000}
  ]
}
```

**方法 2：定時執行**（規劃中）
- 使用系統排程工具（cron、Task Scheduler）
- 透過 API 在指定時間觸發指令

---

## LLM 功能

### Q14: 如何啟用 AI 功能？

**A:** 配置步驟：

1. 前往「設定」→「LLM 設定」
2. 選擇提供商：

**本地方案（免費）**：
- **Ollama**：
  1. 安裝 Ollama：https://ollama.ai
  2. 執行 `ollama pull llama2`
  3. 在應用中設定：`http://localhost:11434`

- **LM Studio**：
  1. 下載 LM Studio：https://lmstudio.ai
  2. 載入模型並啟動伺服器
  3. 在應用中設定：`http://localhost:1234`

**雲端方案（需 API 金鑰）**：
- **OpenAI**：在 https://platform.openai.com 獲取 API 金鑰
- **Anthropic**：在 https://console.anthropic.com 獲取 API 金鑰

---

### Q15: LLM 功能有什麼用？

**A:** 主要功能：

1. **自然語言指令**：
   - 輸入：「讓機器人向前走然後揮手」
   - LLM 解析為：`go_forward` → `wave_hand`

2. **指令建議**：
   - 根據上下文建議下一步動作
   - 智慧完成指令序列

3. **錯誤診斷**：
   - 分析執行失敗原因
   - 提供解決建議

4. **進階指令生成**：
   - 將複雜任務拆解為基本指令序列

---

### Q16: LLM 回應很慢怎麼辦？

**A:** 優化建議：

**本地 LLM**：
1. 使用較小的模型（例如 `llama2:7b` 而非 `llama2:70b`）
2. 確認硬體支援（建議 16GB+ RAM）
3. 使用 GPU 加速（如果支援）

**雲端 LLM**：
1. 檢查網路連線品質
2. 選擇地理位置較近的服務區域
3. 考慮升級 API 方案

**通用方法**：
- 縮短提示詞長度
- 降低輸出 token 數量限制
- 增加 timeout 設定

---

## 服務管理

### Q17: 如何檢查服務狀態？

**A:** 檢查方法：

**WebUI / Heavy / Tiny**：
- 前往「系統狀態」頁面
- 查看各服務狀態指示燈

**TUI**：
- 左上角 "Services" 區塊
- ● 綠色 = 運行中
- ○ 灰色 = 已停止
- ✗ 紅色 = 錯誤

**CLI**：
```bash
# 檢查所有服務
curl http://localhost:5000/health
curl http://localhost:8000/health

# 查看詳細指標
curl http://localhost:5000/metrics
```

---

### Q18: 某個服務無法啟動怎麼辦？

**A:** 診斷步驟：

**1. 查看日誌**：
```bash
# Flask API 日誌
cat logs/flask.log

# MCP 服務日誌
cat logs/mcp.log

# Queue 服務日誌
cat logs/queue.log
```

**2. 檢查埠號衝突**：
```bash
# 確認埠號未被佔用
netstat -tuln | grep -E '5000|8000|8080'
```

**3. 檢查依賴**：
```bash
# 確認 Python 套件已安裝
pip list | grep -E 'flask|fastapi|pydantic'

# 重新安裝依賴
pip install -r requirements.txt
```

**4. 重啟服務**：
```bash
# 停止所有服務
pkill -f "python.*flask_service.py"
pkill -f "python.*start.py"

# 重新啟動
python3 start_all_services.py
```

---

### Q19: 如何手動啟動個別服務？

**A:** 手動啟動方法：

```bash
# 啟動 Flask API
export APP_TOKEN="your-secure-token"
export PORT=5000
python3 flask_service.py

# 啟動 MCP 服務
cd MCP
export MCP_JWT_SECRET="your-jwt-secret"
python3 start.py

# 啟動 WebUI
cd WebUI
export FLASK_APP=microblog.py
flask run --port 8080

# 啟動 Queue Service
python3 run_service_cli.py --queue-size 1000 --workers 5
```

---

## 效能與資源

### Q20: 應用程式佔用太多記憶體怎麼辦？

**A:** 優化建議：

**使用 Tiny 版本**：
- 記憶體佔用降低 50%
- 從 Heavy (~300MB) 切換到 Tiny (~150MB)

**調整 Queue 設定**：
```bash
# 減少佇列大小和工作執行緒
python3 run_service_cli.py --queue-size 500 --workers 3
```

**關閉不需要的功能**：
- 停用 LLM 功能（如果不使用）
- 停用雲端同步
- 減少日誌記錄等級

**定期清理**：
- 清除舊的指令歷史
- 清除過期的日誌檔案

---

### Q21: 如何提升指令執行效能？

**A:** 效能調校：

**1. 增加 Worker 數量**：
```bash
python3 run_service_cli.py --workers 10
```

**2. 使用本地佇列**（而非網路佇列）：
```python
# config.py
USE_REDIS_QUEUE = False  # 使用記憶體佇列
```

**3. 啟用快取**：
```bash
export ENABLE_CACHE=true
```

**4. 批次處理指令**：
- 使用批次 API 減少網路往返
- 一次發送多個指令

---

## 安全性

### Q22: 如何設定安全的密碼？

**A:** 密碼建議：

**強密碼要求**：
- 至少 12 個字元
- 包含大小寫字母
- 包含數字
- 包含特殊符號
- 不使用字典單字

**範例**：
- ❌ 弱密碼：`password123`
- ✅ 強密碼：`R0b0t!C0ns0le#2025`

**密碼管理**：
- 使用密碼管理器（1Password、Bitwarden）
- 定期更換密碼（建議每 90 天）
- 不同服務使用不同密碼

---

### Q23: API Token 如何管理？

**A:** Token 安全實踐：

**生成安全 Token**：
```bash
# 使用 Python 生成
python3 -c "import secrets; print(secrets.token_hex(32))"

# 使用 OpenSSL 生成
openssl rand -hex 32
```

**環境變數設定**：
```bash
# .env 檔案（不要提交到 Git）
APP_TOKEN=your-secure-token-here
MCP_JWT_SECRET=your-jwt-secret-here

# 載入環境變數
source .env
```

**定期輪替**：
```bash
# 使用 API 輪替 token
curl -X POST http://localhost:8000/v1/auth/rotate \
  -H "Authorization: Bearer $OLD_TOKEN" \
  -d '{"new_token": "$NEW_TOKEN"}'
```

📖 詳細說明：[API 安全指南](../security/api-security-guide.md)

---

### Q24: 如何限制使用者權限？

**A:** 角色權限管理：

**三種內建角色**：

| 角色 | 權限 | 適用對象 |
|------|------|----------|
| **admin** | 完整存取、使用者管理 | 系統管理員 |
| **operator** | 執行指令、查看狀態 | 操作員 |
| **viewer** | 僅查看、無法執行 | 訪客、監控人員 |

**建立使用者**：
```bash
curl -X POST http://localhost:8000/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "operator1",
    "password": "secure-pass",
    "role": "operator"
  }'
```

---

## 更新與升級

### Q25: 如何更新到最新版本？

**A:** 更新步驟：

**Tiny 版本（安裝包）**：
1. 下載最新版本安裝包
2. 關閉舊版本應用程式
3. 執行新版本安裝程式
4. 資料庫與設定自動保留

**Heavy 版本（原始碼）**：
```bash
# 1. 備份資料
cp -r data/ data.backup/

# 2. 拉取最新程式碼
git pull origin main

# 3. 更新依賴
npm install
pip install -r requirements.txt

# 4. 執行資料庫遷移（如有需要）
python3 migrate_db.py

# 5. 重新啟動
npm start
```

**TUI 版本**：
```bash
git pull origin main
pip install -r requirements.txt --upgrade
```

---

### Q26: 更新後無法啟動怎麼辦？

**A:** 回復步驟：

**1. 檢查版本相容性**：
```bash
# 查看發布說明
https://github.com/ChengTingFung-2425/robot-command-console/releases

# 確認是否有重大變更（Breaking Changes）
```

**2. 恢復備份**：
```bash
# 恢復資料
rm -rf data/
mv data.backup/ data/

# 回退到舊版本
git checkout v1.0.0
npm install
pip install -r requirements.txt
```

**3. 清除快取**：
```bash
# 清除 Python 快取
find . -type d -name __pycache__ -exec rm -rf {} +

# 清除 npm 快取
npm cache clean --force
rm -rf node_modules package-lock.json
npm install
```

---

### Q27: 版本更新會影響資料嗎？

**A:** 資料保護機制：

**自動備份**：
- 每次更新前自動備份資料庫
- 備份位置：`data/backups/db_YYYYMMDD_HHMMSS.sqlite`

**資料遷移**：
- 自動執行資料庫遷移腳本
- 向後相容舊版本資料格式

**手動備份建議**：
```bash
# 重要更新前手動備份
tar -czf backup_$(date +%Y%m%d).tar.gz data/ config/ logs/
```

---

## 其他問題

### Q28: 支援哪些作業系統？

**A:** 支援平台：

| 作業系統 | Heavy (Electron) | Tiny (PyQt) | TUI |
|----------|-----------------|-------------|-----|
| **Windows** | ✅ 10/11 | ✅ 10/11 | ✅ |
| **macOS** | ✅ 12+ | ✅ 12+ | ✅ |
| **Linux** | ✅ Ubuntu 20.04+ | ✅ Ubuntu 20.04+ | ✅ |
| **Debian** | ✅ 11+ | ✅ 11+ | ✅ |
| **Fedora** | ✅ 35+ | ✅ 35+ | ✅ |

**架構支援**：
- x64 (Intel/AMD) ✅
- ARM64 (Apple Silicon, Raspberry Pi) ✅

---

### Q29: 可以在 Docker 中運行嗎？

**A:** 可以！Docker 支援（規劃中）：

**當前方案**：
```bash
# 使用 Python 環境
docker run -it --rm \
  -v $(pwd):/app \
  -p 5000:5000 -p 8000:8000 -p 8080:8080 \
  python:3.11 \
  /bin/bash -c "cd /app && pip install -r requirements.txt && python3 start_all_services.py"
```

**官方 Docker 映像**（規劃中）：
```bash
docker pull ghcr.io/chengtingfung-2425/robot-command-console:latest
docker run -p 5000:5000 -p 8000:8000 robot-command-console
```

---

### Q30: 我還有其他問題

**A:** 獲取更多幫助：

📖 **查閱文件**：
- [疑難排解指南](TROUBLESHOOTING.md) - 詳細問題診斷
- [用戶指南索引](USER_GUIDE_INDEX.md) - 完整文件列表
- [API 文件](../../openapi.yaml) - API 規範

💬 **社群支援**：
- [GitHub Issues](https://github.com/ChengTingFung-2425/robot-command-console/issues) - 回報 Bug
- [GitHub Discussions](https://github.com/ChengTingFung-2425/robot-command-console/discussions) - 提問討論

🔧 **貢獻改進**：
- 提交 Pull Request 改進文件
- 分享您的使用經驗

---

**回到索引**：[用戶指南索引](USER_GUIDE_INDEX.md)

**最後更新**：2025-12-22
