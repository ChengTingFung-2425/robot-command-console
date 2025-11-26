# Electron 打包與發佈（packaging）

概述
- 這份文件指引如何使用 `electron-builder` 建立平台安裝包、簽章與常見注意事項。

基本工具
- `electron-builder`（或使用 `electron-forge` 搭配 builder）
- 平台簽章工具：macOS 使用 Apple Developer ID 與 `codesign`；Windows 使用簽章工具及 EV code signing（若需要）。

範例：安裝 `electron-builder`
```
npm install --save-dev electron-builder
```

快速打包（範例）
- 在 `package.json` 加入 build 配置（示例）：

```
"build": {
  "appId": "com.example.robotconsole",
  "files": ["dist/**", "py-service/**"],
  "mac": {"target": ["dmg"]},
  "win": {"target": ["nsis"]},
  "linux": {"target": ["AppImage"]}
}
```

- 打包指令：
```
npx electron-builder --mac
npx electron-builder --win
npx electron-builder --linux
```

包含 Python 背景服務時的打包考量
- 內嵌 Python：將 Python 可執行檔與相依打包進應用，需處理跨平台二進位（較複雜）。
- 外部安裝：在安裝器中檢查是否已安裝 Python 或提供安裝指引；啟動時檢查版本並提示使用者。

簽章與發佈
- macOS：需 Apple Developer 帳號，`codesign` 與 `notarize`。
- Windows：建議使用代碼簽章憑證（EV 或一般）以減少 SmartScreen 警示。

CI/CD 範例（概要）
- 在 CI 中安裝 Node、搭配 runner（例如 macOS runner 做 mac build），設定簽章憑證（secret 管理），執行 `npm ci && npm run build && npx electron-builder`。

驗收標準
- 至少在一平台完成 end-to-end 打包與安裝測試（包含 Python 服務的啟動驗證）。
