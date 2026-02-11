# Changelog

All notable changes to Robot Command Console will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- CI/CD 工作流程（build.yml, release.yml）
- PyInstaller 打包配置（build.spec）
- 統一版本管理機制（version.py）
- 跨平台自動化構建

## [3.2.0-beta] - 2026-02-04

### Added
- **Tiny Edge App**: PyQt6 + QtWebEngine 輕量級桌面應用
- **Splash Screen**: 專業的啟動畫面（使用 PIL 繪製）
- **Toolbar Actions**: 完整的工具列功能（全螢幕、幫助、關於、設定）
- **Async Firmware Update**: 完整的非同步固件更新流程
  - 5 階段更新：下載、驗證、傳送、安裝、驗證
  - 進度追蹤（0-100%）
  - 詳細的錯誤處理
- **統一後端服務管理**: BackendServiceManagerSync
- **QWebChannel Bridge**: JS-Python 雙向通訊

### Changed
- 重構 Splash Screen 使用實際圖片而非程式碼繪製
- 優化應用程式啟動速度

### Fixed
- 修復全螢幕模式切換問題
- 修復 ESC 鍵退出全螢幕

### Documentation
- 建立 Phase 4 詳細計劃（PHASE4_PACKAGING_PLAN.md）
- 建立 Async Firmware & UI Polish 完成總結
- 更新架構文件

## [3.1.0] - 2025-12-04

### Added
- **Phase 3.1 完成**: 統一啟動器與服務協調
- **LLM 整合**: 本地 LLM 提供商管理（Ollama, LM Studio）
- **插件架構**: CommandPlugin, DevicePlugin, IntegrationPlugin
- **共享狀態管理**: SharedStateManager
- **服務協調器**: ServiceCoordinator（啟動/停止/健康檢查）

### Changed
- 重構目錄結構（Edge/Server/Runner 分離）
- 優化效能和記憶體使用

## [3.0.0] - 2025-11-01

### Added
- **Phase 2 完成**: 模組化與後端服務層調整
- Server-Edge-Runner 三層架構
- 本地佇列系統
- 進階指令職責轉移

## [2.0.0] - 2025-10-01

### Added
- **Phase 1 完成**: Electron POC
- WebUI 基礎功能
- 機器人抽象層
- 基礎認證授權

## [1.0.0] - 2025-09-01

### Added
- 初始版本
- 基礎 MCP 服務層
- Robot-Console 執行器
- WebUI 介面

---

## 版本號規則

- **Major (X.0.0)**: 重大架構變更或不相容變更
- **Minor (x.Y.0)**: 新功能或重要改進
- **Patch (x.y.Z)**: Bug 修復或小改進
- **Pre-release**: alpha, beta, rc（如 3.2.0-beta）

## 連結

- [Unreleased]: https://github.com/ChengTingFung-2425/robot-command-console/compare/v3.2.0-beta...HEAD
- [3.2.0-beta]: https://github.com/ChengTingFung-2425/robot-command-console/releases/tag/v3.2.0-beta
- [3.1.0]: https://github.com/ChengTingFung-2425/robot-command-console/releases/tag/v3.1.0
- [3.0.0]: https://github.com/ChengTingFung-2425/robot-command-console/releases/tag/v3.0.0
