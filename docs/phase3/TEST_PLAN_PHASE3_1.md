# Phase 3.1 測試計畫

> **建立日期**：2025-12-03  
> **狀態**：✅ 已完成  
> **前置條件**：Phase 2 模組化與後端服務層調整完成  
> **最終測試結果**：365 個測試全部通過

---

## 目錄

1. [測試目標](#測試目標)
2. [測試範圍](#測試範圍)
3. [測試策略](#測試策略)
4. [測試案例清單](#測試案例清單)
5. [驗收條件](#驗收條件)
6. [執行指南](#執行指南)

---

## 測試目標

根據 Phase 3.1 的核心目標，本測試計畫旨在驗證以下功能：

1. **統一啟動器原型**：驗證一鍵啟動/停止所有服務的能力
2. **服務協調器**：驗證服務的啟動、停止、健康檢查功能
3. **LLM 選擇介面**：驗證可選擇本地 LLM 提供商（Ollama/LM Studio）
4. **服務間狀態共享機制**：驗證各服務間的狀態同步與事件通訊

---

## 測試範圍

### 核心功能測試

| 功能模組 | 測試檔案 | 說明 |
|----------|----------|------|
| 統一啟動器 | `phase3/test_unified_launcher.py`, `phase3/test_unified_launcher_phase3.py` | 一鍵啟動/停止、健康檢查 |
| 服務協調器 | `phase3/test_service_coordinator.py` | 服務註冊、啟動、停止、狀態管理 |
| LLM 提供商 | `phase2/test_llm_providers.py`, `phase2/test_llm_settings.py` | LLM 提供商選擇與配置 |
| 狀態共享 | `phase3/test_shared_state.py` | LocalStateStore、LocalEventBus、SharedStateManager |
| 啟動恢復 | `phase3/test_startup_recovery.py` | 服務啟動失敗時的恢復機制 |

### 整合測試

| 測試項目 | 測試檔案 | 說明 |
|----------|----------|------|
| 指令執行流程 | `phase3/test_phase3_1_integration.py` | 端對端指令執行流程 |
| 服務協調整合 | `phase3/test_phase3_1_integration.py` | 多服務協調測試 |

---

## 測試策略

### 測試類型

1. **單元測試**
   - 各模組獨立功能測試
   - Mock 外部依賴
   - 快速執行與回饋

2. **整合測試**
   - 多模組協同工作測試
   - 驗證服務間通訊
   - 驗證端對端流程

3. **冒煙測試**
   - 核心功能快速驗證
   - CI/CD 流水線整合

### 測試框架

- **Python**：pytest、pytest-asyncio
- **覆蓋率**：pytest-cov

---

## 測試案例清單

### 1. 統一啟動器測試 (`test_unified_launcher_phase3.py`)

| 測試案例 ID | 測試案例名稱 | 說明 | 優先級 |
|-------------|--------------|------|--------|
| UL-001 | `test_one_click_start_all` | 驗證一鍵啟動所有服務 | P0 |
| UL-002 | `test_one_click_stop_all` | 驗證一鍵停止所有服務 | P0 |
| UL-003 | `test_health_check_all_services` | 驗證所有服務健康檢查 | P0 |
| UL-004 | `test_get_services_status` | 驗證取得所有服務狀態 | P0 |
| UL-005 | `test_register_default_services` | 驗證預設服務註冊 | P1 |

### 2. 服務協調器測試 (`test_service_coordinator.py`)

| 測試案例 ID | 測試案例名稱 | 說明 | 優先級 |
|-------------|--------------|------|--------|
| SC-001 | `test_register_service` | 驗證服務註冊 | P0 |
| SC-002 | `test_start_service` | 驗證單一服務啟動 | P0 |
| SC-003 | `test_stop_service` | 驗證單一服務停止 | P0 |
| SC-004 | `test_start_all_services` | 驗證啟動所有服務 | P0 |
| SC-005 | `test_stop_all_services` | 驗證停止所有服務 | P0 |
| SC-006 | `test_check_service_health` | 驗證服務健康檢查 | P0 |
| SC-007 | `test_check_all_services_health` | 驗證所有服務健康檢查 | P0 |
| SC-008 | `test_start_service_failure` | 驗證服務啟動失敗處理 | P1 |
| SC-009 | `test_auto_restart_on_failure` | 驗證失敗時自動重啟 | P1 |

### 3. LLM 提供商測試 (`test_llm_providers.py`)

| 測試案例 ID | 測試案例名稱 | 說明 | 優先級 |
|-------------|--------------|------|--------|
| LLM-001 | `test_select_provider` | 驗證選擇 LLM 提供商 | P0 |
| LLM-002 | `test_discover_providers` | 驗證自動偵測提供商 | P0 |
| LLM-003 | `test_ollama_provider` | 驗證 Ollama 提供商配置 | P1 |
| LLM-004 | `test_lmstudio_provider` | 驗證 LM Studio 提供商配置 | P1 |
| LLM-005 | `test_provider_health_check` | 驗證提供商健康檢查 | P1 |
| LLM-006 | `test_fallback_rule_based` | 驗證無 LLM 時回退規則式解析 | P1 |

### 4. 狀態共享測試 (`test_shared_state.py`)

| 測試案例 ID | 測試案例名稱 | 說明 | 優先級 |
|-------------|--------------|------|--------|
| SS-001 | `test_robot_status_update` | 驗證機器人狀態更新 | P0 |
| SS-002 | `test_queue_status_update` | 驗證佇列狀態更新 | P0 |
| SS-003 | `test_service_status_update` | 驗證服務狀態更新 | P0 |
| SS-004 | `test_llm_provider_update` | 驗證 LLM 提供商設定更新 | P0 |
| SS-005 | `test_subscribe_and_publish` | 驗證事件訂閱與發布 | P0 |
| SS-006 | `test_user_settings` | 驗證用戶設定儲存 | P1 |

### 5. 指令執行流程測試 (`test_phase3_1_integration.py`)

| 測試案例 ID | 測試案例名稱 | 說明 | 優先級 |
|-------------|--------------|------|--------|
| CE-001 | `test_basic_command_flow` | 驗證基本指令執行流程 | P0 |
| CE-002 | `test_command_with_llm_parse` | 驗證 LLM 指令解析流程 | P1 |
| CE-003 | `test_command_queue_processing` | 驗證指令佇列處理 | P1 |
| CE-004 | `test_command_status_tracking` | 驗證指令狀態追蹤 | P1 |

---

## 驗收條件

根據 Phase 3.1 規劃文件，驗收條件如下：

### P0 驗收條件（必須通過）

- [x] **AC-001**：一鍵啟動所有服務成功，無錯誤
- [x] **AC-002**：所有服務健康檢查通過
- [x] **AC-003**：可選擇本地 LLM 提供商（Ollama/LM Studio）
- [x] **AC-004**：基本指令執行流程完整
- [x] **AC-005**：服務間狀態共享機制正常運作

### P1 驗收條件（建議通過）

- [x] **AC-006**：服務啟動失敗時可自動恢復
- [x] **AC-007**：無 LLM 時可回退到規則式解析
- [x] **AC-008**：事件訂閱/發布機制正常

---

## 執行指南

### 執行所有測試

```bash
cd /path/to/robot-command-console
python3 -m pytest tests/ -v
```

### 執行 Phase 3.1 相關測試

```bash
# Phase 1 測試（基礎架構）
python3 -m pytest tests/phase1/ -v

# Phase 2 測試（模組化）
python3 -m pytest tests/phase2/ -v

# Phase 3 測試（ALL-in-One Edge App）
python3 -m pytest tests/phase3/ -v

# 核心測試（認證、安全、契約）
python3 -m pytest tests/core/ -v
```

### 執行覆蓋率報告

```bash
python3 -m pytest tests/ --cov=src --cov=MCP --cov-report=html
```

---

## 參考文件

- [PHASE3_EDGE_ALL_IN_ONE.md](../plans/PHASE3_EDGE_ALL_IN_ONE.md) - Phase 3 完整規劃
- [MASTER_PLAN.md](../plans/MASTER_PLAN.md) - 專案主計畫
- [architecture.md](../architecture.md) - 系統架構
- [PHASE3_1_STATUS_REPORT.md](PHASE3_1_STATUS_REPORT.md) - Phase 3.1 狀態報告

---

## 測試執行結果

### 最終測試結果（2025-12-03）

```
====================== 365 passed, 234 warnings in 26.25s ======================
```

### 測試分布

| 測試目錄 | 測試數 |
|----------|--------|
| `tests/core/` | 88 |
| `tests/phase1/` | 28 |
| `tests/phase2/` | 84 |
| `tests/phase3/` | 165 |

---

**文件維護者**：開發團隊  
**最後更新**：2025-12-03  
**下次審查**：Phase 3.2 開始時
