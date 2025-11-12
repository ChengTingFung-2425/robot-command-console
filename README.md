# Robot Command Console

本專案（robot-command-console）是一個用於機器人指令管理、路由與執行的整合式控制台與服務平台。目標是提供一套模組化、可測試且可部署的系統，用來接收、驗證、路由並執行來自各種介面（WebUI、API、排程或其他整合服務）的指令，同時保留豐富的日誌、驗證與合約（schema）檢查。

## 核心目的

- 集中管理來自多來源的機器人指令。  
- 提供可插拔的模組（MCP、Robot-Console、WebUI），方便開發、測試與部署。  
- 支援合約驅動的請求/回應格式（JSON schema），強化驗證與互通性。  
- 內建測試與監控範例，協助維持系統可靠性。

## 主要元件概覽

- MCP/: 管理核心後端服務（API、身分驗證、指令處理、上下文管理、日誌監控）。
- Robot-Console/: 機器人執行層與相關工具（action executor、decoder、pubsub）。
- WebUI/: 提供使用者介面與微服務整合的範例實作（microblog 與 Web UI routes）。
- Test/: 專案的自動化測試集合，包含單元測試與整合測試範例。

## 主要功能（摘要）

- 指令接收與路由（支援多種輸入來源）。
- 驗證與合約（JSON schema）檢查。  
- 身分驗證與權限管理（模組化 auth）。
- 執行器抽象與模擬（便於開發與測試）。
- 日誌、監控與事件記錄。

## 快速啟動（開發者）

1. 建立虛擬環境並安裝依賴（請根據不同子專案執行相應 requirements.txt）：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

1. 依需求啟動單一元件：例如啟動 WebUI 開發伺服器或 MCP 服務（詳見各子資料夾 `README.md`）：

```bash
# 例如：啟動主應用（若有 app.py）
python app.py

# 或在 WebUI 資料夾中啟動 microblog
cd WebUI
python microblog.py
```

1. 執行測試：

```bash
# 在專案根目錄
pytest -q
```

## 專案約定與延伸

- JSON schema 檔案放置於 `docs/contract/`，用於請求/回應與錯誤合約驗證。  
- 日誌檔與測試範例位於 `logs/` 與 `Test/` 資料夾。  
- 以模組化設計為主，便於替換不同的執行後端或外部整合。

## 貢獻

歡迎開發者提交 issue 與 PR。請遵守現有測試與程式碼風格，並在新增功能時補上對應的測試。

## 參考與文件

- 專案內 `docs/` 與各子模組的 `README.md` 提供更詳細的設計說明與部署指引。  

## CI: 自動將 main 同步到各分支（新增）

本倉庫新增了一個 GitHub Actions 工作流程 `./github/workflows/sync-main-to-branches.yml`，會在 `main` 有 push（例如合併 PR）時嘗試把 `origin/main` merge 回其他遠端分支，並將合併後的結果 push 回對應分支。

注意事項：

- 使用預設的 `GITHUB_TOKEN` 應可執行一般的 push，但若目標分支設定為受保護（protected）且需要額外審查或強制檢查，push 可能會被拒絕。若需要跨受保護分支自動推送，請改用有適當權限的 Personal Access Token（PAT），並將其存為 repository secret，再在 workflow 中使用該 PAT（取代預設憑證）。
- 若某分支與 `main` 的合併發生衝突，該分支會被跳過（workflow 會記錄失敗的分支）。目前實作不會自動解決衝突或建立 PR；若希望自動建立包含衝突的 PR 以便手動處理，可進一步擴充 workflow。
- 請注意避免把不應自動同步的分支（例如臨時測試分支或維護分支）放入同步列表；目前 workflow 會自動排除 `main`、`gh-pages` 與 `HEAD`，你可以根據需要再修改檔案以排除更多分支。

如果需要，我可以把 README 中這段改為更詳細的操作範例（包含如何用 PAT 推送與示範保護分支設定）。
