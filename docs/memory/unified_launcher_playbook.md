**Unified Launcher 操作手冊（Playbook）**

目的：提供開發者與維運人員一份可執行的檢查表與操作步驟，涵蓋啟動器的啟動/停止、日誌診斷、`TokenIntegration` 驗證與常見故障處理。

關聯文件：
- 主指南（快速上手）： [docs/development/UNIFIED_LAUNCHER.md](docs/development/UNIFIED_LAUNCHER.md)
- 專案記憶： [docs/PROJECT_MEMORY.md](docs/PROJECT_MEMORY.md)

前置條件：
- 已安裝並啟用虛擬環境（工作區預設 `.venv`）。
- 在開發機上已安裝 `requirements.txt` 內所有套件。
- 有 shell 存取使用者家目錄（`$HOME`）。

環境變數與檔案位置（重要）
- `APP_TOKEN`：用於在開發環境中簡單驗證；生產請以安全方式設定。
- `EDGE_TOKEN_KEY`：Edge token 加密金鑰（Base64 urlsafe 32 bytes），部署時提供。
- `~/.robot-console/edge_tokens.enc`：Edge token 加密快取檔。
- `~/.robot-console/edge_sync.enc`：Edge 同步佇列加密檔。
- 子進程日誌：`/tmp/<service>.stdout.log`、`/tmp/<service>.stderr.log`。

快速操作範例

啟用虛擬環境：

```bash
source .venv/bin/activate
```

開發（前台）啟動（交互式，可看到日誌）：

```bash
APP_TOKEN="dev-token-$(date +%s)" python src/robot_service/unified_launcher.py --log-level=INFO
```

背景啟動（nohup）與導出日誌：

```bash
APP_TOKEN="dev-token-$(date +%s)" nohup python src/robot_service/unified_launcher.py --log-level=INFO > /tmp/unified_launcher.log 2>&1 &
```

停止：
- 若在前台按 `Ctrl+C`。
- 背景時使用 `ps` 找到 process 並 `kill`。

啟動器健康檢查與診斷

1. 檢查 UnifiedLauncher 主日誌：

```bash
tail -n 200 /tmp/unified_launcher.log
```

2. 子進程日誌（若某服務啟動失敗）：

```bash
ls -l /tmp/<service>.*
less /tmp/<service>.stderr.log
less /tmp/<service>.stdout.log
```

3. 確認 Python 環境：

```bash
# 確認正在使用的 Python
which python
python -V
# 安裝依賴
.venv/bin/python -m pip install -r requirements.txt
```

TokenIntegration 測試與驗證（手動流程）

說明：`TokenIntegration` 會在 `main_async` 中啟動，監聽 `TokenManager` 的輪替事件，並把 token 寫入 `~/.robot-console/edge_tokens.enc`，同時 enqueue 到 `edge_sync.enc`。

手動觸發 token rotation（在虛擬環境中執行）：

```bash
.venv/bin/python - <<'PY'
from src.robot_service.token_integration import TokenIntegration
from src.common.token_manager import get_edge_token_manager
import time

# 啟動 integration
ti = TokenIntegration()
ti.start()
# 觸發輪替
mgr = get_edge_token_manager()
new_token, info = mgr.rotate_token(reason='manual_test')
print('rotated token id=', info.token_id)
# 給 sync/background 一點時間
time.sleep(1)
ti.stop()
PY
```

檢查檔案是否已產生：

```bash
ls -la ~/.robot-console
hexdump -C -n 128 ~/.robot-console/edge_tokens.enc
hexdump -C -n 128 ~/.robot-console/edge_sync.enc
```

開發者測試提示（可選）
- 若要在開發模式檢查快取內部結構，可暫時在 `EdgeTokenCache` 加入一個 debug 方法輸出未加密的 payload（僅限本地測試，請勿在生產環境使用）。
- `EdgeTokenSync` 的 `sync_callback` 目前為 placeholder，實作雲端 API 時請確保：
  - 使用安全授權（OAuth2/JWT）與最小權限
  - 回傳值 `True` 表示成功，`False` 表示需重試

故障排除常見項目

- 問題：`mcp_service` 在 UnifiedLauncher 中啟動失敗但直接啟動可運行。
  - 原因常見於不同的 Python / 套件環境或 working dir 不一致。
  - 檢查：`/tmp/mcp_service.stderr.log` 的 ModuleNotFoundError 或 ImportError。
  - 解法：確保 UnifiedLauncher 使用的 Python（`sys.executable`）與你執行 `python -m MCP.start` 時相同，並在該環境安裝依賴。

- 問題：沒有看到 `~/.robot-console/*.enc` 檔案。
  - 原因：尚未發生 token rotation，或 `EDGE_TOKEN_KEY` 導致解密失敗覆蓋行為。
  - 檢查：在程式啟動時觀察 `src.common.token_manager` 的日誌，或手動觸發 rotation（如上）。

- 問題：`edge_tokens.enc` 解密失敗（InvalidToken）
  - 原因：`EDGE_TOKEN_KEY` 不同或損壞。
  - 解法：確認部署時傳入相同 `EDGE_TOKEN_KEY`，或提供遷移步驟（以安全方式備份並重新加密）。

提交與回滾

- 將本次變更推到分支 `copilot/enhance-security-audit-logs`（若尚未）：

```bash
git add -A
git commit -m "docs: add unified launcher playbook"
git push origin <branch>
```

- 若需要回滾檔案（小範圍）：使用 `git checkout -- <file>` 或重設 commit（視情況使用 `git revert` 或 `git reset --hard`）。

記錄與後續

- 已在 `docs/PROJECT_MEMORY.md` 紀錄此次實作要點。
- 建議：實作 production `sync_callback`、CI 檢查 `EDGE_TOKEN_KEY` 與建立 key rotation policy。

---
文件位置（新增）： `docs/memory/unified_launcher_playbook.md`

若你要，我可以：
- 把此檔 commit 並 push（我會立即做），或
- 在 PR 描述中加入使用步驟摘要。