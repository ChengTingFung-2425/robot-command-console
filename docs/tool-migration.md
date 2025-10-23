# 機器人工具清單遷移說明

此文件記錄將機器人模組（Robot-Console）之工具清單移交至 MCP 的變更，以及開發／維運團隊應遵循的作業流程。

背景
- 原始工具清單位於 `Robot-Console/tools.py`（包含 `TOOL_LIST`、`TOOLS` 與每項動作的簡單描述／schema）。
- 為了集中管理、版本化以及供 WebUI / LLM 代理一致查詢，工具清單的權威來源已改為 MCP（`MCP/Module.md` 已記錄目前工具清單與使用建議）。

變更要點
- MCP 提供查詢 API（建議）：
  - GET /api/tools -> 回傳全域工具清單與 schema
  - GET /api/robots/{robot_id}/capabilities -> 回傳該 robot 可用的工具/能力清單
- Robot-Console 保持本地 `tools.py` 作為執行器映射與快速開發參考，但不應直接在此處修改權威定義。
- WebUI 與其他消費者應對 MCP 的 API 做為權威資料來源。

建議同步機制（實作選項）
1. CI 驗證與同步腳本
   - 對 MCP 上的工具庫變更啟用 CI：在工具庫變更時，自動建立 PR 到各 Robot-Console 的 `tools.py`，包含映射與版本註記。
2. 定期同步任務
   - 每日或每次發佈時，執行同步腳本以保持各端最新。
3. 讀取時版本檢查
   - Robot-Console 在啟動時可檢查 MCP 工具庫版本與本地版本，若不一致則產生警告或嘗試自動更新（視安全政策而定）。

短期開發注意事項
- 在尚未完成自動同步前段時間，開發者可能會在 `Robot-Console/tools.py` 做本地修正以進行測試，但在合併到主分支前，必須同步回 MCP 並通過審核流程。

聯絡與支援
- 若需修改工具定義或 schema，請向 MCP 團隊提出 PR 或 issue，包含變更說明與相容性影響評估。


變更紀錄
- 2025-10-23: 將 `Robot-Console/tools.py` 的工具清單移交為 MCP 的權威清單，並在 `MCP/Module.md` 中加入工具清單節與遷移建議。同時更新 `Robot-Console/module.md` 與 `WebUI/Module.md` 參照說明。

附註：進階指令擴展 API（MCP）

為支援動態將使用者下達的「進階指令」解碼成基礎指令序列，MCP 可選擇提供一個擴展端點，建議如下：

- POST /api/advanced_commands/expand
   - Input: 任意 JSON 表示之進階指令（由上層定義），例如：
      - { "type": "sequence", "steps": [ {"action": "go_forward"}, {"action": "turn_left"} ] }
      - 或其他具語意的結構（MCP 應記錄 schema 與版本）。
   - Output (200): { "actions": [ "go_forward", "turn_left", ... ], "version": "tools.v1" }
   - Error: 回傳 `error` 結構，並使用標準錯誤碼（例如 ERR_ACTION_INVALID / ERR_VALIDATION）。

Decoder 行為說明：
- Robot-Console 已加入本地的 `AdvancedDecoder`，會先嘗試呼叫上述 MCP 端點進行擴展；若呼叫失敗或回傳非預期結構，則回退至本地簡單擴展（例如解析 `type: sequence`）。
- WebUI 與其他呼叫者可以直接呼叫 MCP 的 expand 端點以驗證或預覽展開結果（例如在 UI 中顯示動作序列供使用者確認）。
