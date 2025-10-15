# WebUI 目錄說明# WebUI 目錄說明



本資料夾為「機器人指令中介層（MCP 伺服器）」的 Web 介面實作，依據專案提案（prosposal.md）設計，具備以下特點：



## 目標## 目標

WebUI 提供人類操作員與 AI 客戶端的互動入口，支援指令發送、狀態監控、日誌查詢與即時介入，確保人機協作安全與可追溯性。WebUI 提供人類操作員與 AI 客戶端的互動入口，支援指令發送、狀態監控、日誌查詢與即時介入，確保人機協作安全與可追溯性。



## 模組化架構## 模組化架構

本 WebUI 採用模組化設計，主要模組包括：

- 指令路由與處理（routes.py）- 网页路由與處理（routes.py）

- 資料模型（models.py）- 数据库模型（models.py）

- 錯誤處理（errors.py）- 錯誤處理（errors.py）

- 郵件通知（email.py）- 郵件通知（email.py）

- 表單驗證（forms.py）- 表單驗證（forms.py）

- 日誌與監控（logging_monitor.py）- 設定管理（config.py）



所有設定統一由專案根目錄 config.py 提供。各模組可獨立維護、擴充，便於未來整合新功能或新型機器人。



## 目錄結構簡介## 目标功能

- app/：WebUI 主程式與模組- 指令驗證、排隊、分派與回應

- templates/：Jinja2 前端模板- 機器人狀態與指令結果監控

- translations/：多語系翻譯檔- 完整日誌查詢與即時監督介面

- migrations/：資料庫遷移管理- 認證授權與角色權限控管

- 日誌與監控（可擴充 logging_monitor 模組）

---

如需詳細設計理念與開發步驟，請參閱專案根目錄下的 prosposal.md。## 目錄結構簡介

- app/：WebUI 主程式與模組
- templates/：Jinja2 前端模板
- translations/：多語系翻譯檔
- migrations/：資料庫遷移管理


---
如需詳細設計理念與開發步驟，請參閱專案根目錄下的 prosposal.md。
