# Electron 開發上手（dev-setup）

目標：讓開發者能在本機快速建立開發環境並啟動 Electron + Python POC。

先決條件
- 安裝 Node.js（建議 LTS）與 npm 或 yarn。
- 安裝 Python 3.x 並建立虛擬環境（venv 或其他）。

建置步驟（示例）
1. 取得專案
   - git clone <repo>
   - cd robot-command-console
2. 建立 Python venv 並安裝相依
   - python3 -m venv .venv
   - source .venv/bin/activate
   - pip install -r requirements.txt
3. 建立 Electron 子專案（或在 repo 下新增 `electron` 目錄）
   - cd WebUI 或在 repo 根目錄新增 `electron-app`
   - 初始化 npm: `npm init -y`
   - 安裝開發依賴（示例使用 electron-forge）:
     - `npm install --save-dev @electron-forge/cli`
     - `npx electron-forge import` （或依 forge 指引建立專案結構）
4. 開發流程（範例）
   - 啟動 Python 背景服務（local API）:
     - 在專案根目錄：`source .venv/bin/activate && python app.py`
   - 在 electron-app 目錄啟動 Renderer/主進程:
     - `npm start`

注意（Python 與 Electron 整合）
- 開發期可用 `localhost:PORT` 通訊，記得在 POC 中使用短期 token 並只綁定 loopback。
- 建議在 Electron 主進程實作檢查：是否已有背景服務在執行，若無則 spawn 子進程，並在 app 關閉時終止子進程。

Debug 小技巧
- 在 Renderer 使用 devtools，主進程可加入 `--inspect` 供 VSCode attach。
- 將 Python 日誌輸出到檔或 console，方便追蹤 spawn 問題。
