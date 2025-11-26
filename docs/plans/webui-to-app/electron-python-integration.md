# Electron 與 Python 背景服務整合

目的：定義在 Electron 應用內啟動、監控與與 Python 背景服務通訊的實作建議與範例，並說明升級與安全考量。

啟動策略（開發 vs 發佈）
- 開發模式：開發者手動在虛擬環境啟動 Python 服務（方便快速迭代）。
- 發佈模式（POC 建議）：Electron 主進程檢查是否已存在本地服務；若無，spawn 子進程啟動內嵌 Python 可執行或系統安裝的 Python。

Spawn 範例（Node 主進程，簡化示例）
```js
const { spawn } = require('child_process');
const py = spawn('python', ['path/to/app.py'], { stdio: 'inherit' });
py.on('exit', (code) => console.log('python exit', code));

// 在 app quit 時關閉
app.on('before-quit', () => {
  py.kill();
});
```

通訊建議
- 使用 HTTP on localhost（例如 `http://127.0.0.1:5000`）搭配短期 token（POC）或使用 unix socket（較安全）作為進階選項。
- 在每次啟動時產生短期 token，並在 Renderer 發出的請求加上 Authorization header。

健康檢查與重啟策略
- 在主進程啟動時發送 health-check，若服務未就緒則等待並重試若干次。
- 若子進程崩潰，可紀錄錯誤，依錯誤類型選擇自動重啟（有限次數）或提示使用者。

升級與版本管理
- 若 Python 背景服務是內嵌（隨 App 發佈），需在打包時確認 Python 二進位版本與相依性。
- 若 Python 為系統安裝，文件需說明支援的 Python 版本範圍與安裝指引。

安全建議
- 監聽回環位址，避免綁定 0.0.0.0。
- 使用短期 token 與 CSP，並把敏感資料儲存在 OS 的安全抽象（Keychain/DPAPI/Secret Service）。

驗收標準
- 主進程能成功啟動並監控 Python 背景服務，Renderer 能用 token 成功呼叫 API 並取得回應。
