**Unified Launcher 使用說明**

- **目的**: 統一啟動、停止與監控本地服務（`flask_api`, `mcp_service`, queue 等），提供健康檢查、自動重啟與診斷日誌支援。

- **檔案**: [src/robot_service/unified_launcher.py](src/robot_service/unified_launcher.py)

**快速開始**

- 先啟用專案虛擬環境（workspace 使用 `.venv`）:

```bash
source .venv/bin/activate
```

- 使用預設參數啟動啟動器（開發機）:

```bash
APP_TOKEN="dev-token-$(date +%s)" python src/robot_service/unified_launcher.py --log-level=INFO
```

- 背景執行範例（nohup）:

```bash
APP_TOKEN="dev-token-$(date +%s)" nohup python src/robot_service/unified_launcher.py --log-level=INFO > /tmp/unified_launcher.log 2>&1 &
```

**重要環境變數**

- `APP_TOKEN`：用於服務間簡單身份驗證（開發時可自動產生，生產環境請顯式設定）。
- `EDGE_TOKEN_KEY`：若使用 `TokenIntegration`（邊緣 token 快取與離線同步），此 env 為對稱加密金鑰來源（Base64 urlsafe 32bytes）。

**行為重點**

- 啟動器會註冊並啟動下列預設服務：
  - `flask_api`（port 5000）
  - `mcp_service`（port 8000，透過 `python -m MCP.start` 啟動）
  - `queue_service`（內部工作佇列）

- 爲了可靠診斷，當啟動子進程時會把子程序的 stdout/stderr 重導到 `/tmp/<service>.stdout.log` 與 `/tmp/<service>.stderr.log`。
  - 若子進程啟動失敗，啟動器會嘗試讀取並記錄這些檔案的內容，請在診斷時檢查這些檔案。

**TokenIntegration（邊緣 Token 快取/同步）**

- TokenIntegration 會在啟動器啟動流程中啟動（在 `main_async` 中呼叫 `TokenIntegration.start()`），會將 token 寫入預設 persist 目錄（預設 `~/.robot-console/edge_tokens.enc` 與 `~/.robot-console/edge_sync.enc`）。
- 若未看到加密檔，表示尚未發生 token rotation 或快取尚未寫入；可檢查 `TokenManager` 事件或手動觸發測試旋轉。

**故障排除步驟**

1. 檢查 UnifiedLauncher log:

```bash
tail -n 200 /tmp/unified_launcher.log
```

2. 檢查子進程日誌（若 `mcp_service` 無法啟動）:

```bash
ls -l /tmp/mcp_service.* /tmp/flask_api.*
less /tmp/mcp_service.stderr.log
less /tmp/mcp_service.stdout.log
```

3. 確認使用的 Python 解譯器與環境套件：啟動器會使用當前 Python (`sys.executable`) 啟動子進程，確保已在 `.venv` 或適當環境中安裝依賴：

```bash
.venv/bin/python -m pip install -r requirements.txt
```

4. 若出現 ModuleNotFoundError（例如 `pydantic`），請在虛擬環境中安裝相依套件，或使用相同 Python 來手動啟動該子服務測試。

**開發者提示**

- 在修改子進程啟動命令或 working dir 時，請注意 `ProcessServiceConfig` 的 `command`、`working_dir` 與 `env`。
- `ServiceCoordinator` 會對服務做重啟策略（`max_restart_attempts`、`restart_delay`），可在 `UnifiedLauncher` 建構時調整參數。

**範例：本機測試啟動與停機**

```bash
# 啟動
APP_TOKEN="dev-token" python src/robot_service/unified_launcher.py --log-level=DEBUG
# Ctrl+C 停止 (或使用該 CLI 的 signal handling)
```

**如何貢獻改進文檔**

- 若你增加了新服務或改變子進程啟動行為，請同步更新本文件並在 PR 描述中說明變更。

---
文件位置: [docs/development/UNIFIED_LAUNCHER.md](docs/development/UNIFIED_LAUNCHER.md)

若要我做：我可以把檔案 commit 並 push 到 `copilot/enhance-security-audit-logs`。