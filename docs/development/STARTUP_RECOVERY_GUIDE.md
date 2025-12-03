# 服務啟動異常恢復邏輯指南

> 本文件說明子服務啟動失敗時的自動重試機制。
> 
> **建立日期**：2025-12-03
> **狀態**：✅ 已實作

---

## 目錄

1. [概述](#概述)
2. [配置選項](#配置選項)
3. [使用方式](#使用方式)
4. [運作流程](#運作流程)
5. [告警機制](#告警機制)
6. [測試](#測試)
7. [相關文件](#相關文件)

---

## 概述

當子服務（如 Flask API、MCP Service、Queue Service）啟動失敗時，系統會自動進行配置次數的重試嘗試。這個機制減少了人工介入的需求，提高了系統的容錯能力。

### 設計原則

1. **自動恢復**：啟動失敗後自動重試，減少人工介入
2. **配置靈活**：可針對不同服務設定不同的重試策略
3. **告警機制**：每次重試和最終失敗都會觸發告警
4. **狀態追蹤**：透過 `get_services_status()` 可查看重試次數

---

## 配置選項

### ServiceConfig 新增欄位

| 欄位 | 類型 | 預設值 | 說明 |
|------|------|--------|------|
| `startup_retry_enabled` | `bool` | `True` | 是否啟用啟動重試 |
| `max_startup_retry_attempts` | `int` | `3` | 最大重試次數 |
| `startup_retry_delay_seconds` | `float` | `1.0` | 重試間隔（秒） |

### ServiceState 新增欄位

| 欄位 | 類型 | 說明 |
|------|------|------|
| `startup_retry_count` | `int` | 當前啟動過程的重試次數 |

---

## 使用方式

### 基本配置

```python
from common.service_types import ServiceConfig
from robot_service.service_coordinator import ServiceCoordinator

# 建立服務配置
config = ServiceConfig(
    name="my_service",
    service_type="MyService",
    startup_retry_enabled=True,        # 啟用重試
    max_startup_retry_attempts=5,      # 最多重試 5 次
    startup_retry_delay_seconds=2.0,   # 每次重試間隔 2 秒
)

# 註冊服務
coordinator.register_service(service, config)

# 啟動服務（失敗時會自動重試）
await coordinator.start_service("my_service")
```

### 禁用重試

```python
config = ServiceConfig(
    name="critical_service",
    service_type="CriticalService",
    startup_retry_enabled=False,  # 禁用重試，啟動失敗立即報錯
)
```

### 查詢重試狀態

```python
# 取得所有服務狀態
statuses = coordinator.get_services_status()

for name, status in statuses.items():
    print(f"{name}: 重試次數 = {status['startup_retry_count']}")
```

---

## 運作流程

```
┌─────────────────────────────────────────────────────────────────────┐
│                      服務啟動流程                                    │
└─────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
                      ┌────────────────┐
                      │  start_service │
                      └───────┬────────┘
                              │
                              ▼
                      ┌────────────────┐
                      │ 重置重試計數   │
                      │ startup_retry  │
                      │ _count = 0     │
                      └───────┬────────┘
                              │
                              ▼
                      ┌────────────────┐
                      │ _do_start      │
                      │ _service()     │
                      └───────┬────────┘
                              │
              ┌───────────────┴───────────────┐
              │                               │
              ▼                               ▼
       ┌──────────┐                    ┌──────────┐
       │  成功    │                    │  失敗    │
       └────┬─────┘                    └────┬─────┘
            │                               │
            ▼                               ▼
    ┌──────────────┐               ┌────────────────────┐
    │ 返回 True    │               │ 重試已啟用?        │
    │ 狀態=RUNNING │               └─────────┬──────────┘
    └──────────────┘                         │
                                   ┌─────────┴─────────┐
                                   │                   │
                                   ▼                   ▼
                            ┌──────────┐         ┌──────────┐
                            │ 是       │         │ 否       │
                            └────┬─────┘         └────┬─────┘
                                 │                    │
                                 ▼                    ▼
                      ┌──────────────────┐     ┌──────────────┐
                      │ 重試次數 <       │     │ 返回 False   │
                      │ max_attempts?    │     │ 狀態=ERROR   │
                      └─────────┬────────┘     └──────────────┘
                                │
                    ┌───────────┴───────────┐
                    │                       │
                    ▼                       ▼
             ┌──────────┐            ┌──────────┐
             │ 是       │            │ 否       │
             └────┬─────┘            └────┬─────┘
                  │                       │
                  ▼                       ▼
          ┌──────────────┐        ┌────────────────┐
          │ retry_count++│        │ 發送最終失敗   │
          │ 發送重試告警 │        │ 告警           │
          │ 等待延遲     │        │ 返回 False     │
          │ 重新嘗試     │        └────────────────┘
          └───────┬──────┘
                  │
                  └──────► 回到 _do_start_service()
```

---

## 告警機制

### 重試告警

每次重試時會觸發告警：

```python
{
    "title": "服務啟動失敗，正在重試",
    "body": "{service_name} 啟動失敗，正在進行第 {retry_attempt}/{max_retries} 次重試",
    "context": {
        "alert_type": "startup_retry",
        "service": "service_name",
        "retry_attempt": 1,
        "last_error": "Connection refused"
    }
}
```

### 最終失敗告警

重試次數用盡後會觸發最終失敗告警：

```python
{
    "title": "服務啟動失敗，重試次數已用盡",
    "body": "{service_name} 在 {max_retries} 次重試後仍然無法啟動",
    "context": {
        "alert_type": "startup_failed",
        "service": "service_name",
        "total_attempts": 4,  # 1 初始 + 3 重試
        "last_error": "Connection refused"
    }
}
```

### 設定告警回呼

```python
async def handle_alert(title, body, context):
    # 發送到通知系統
    await send_notification(title, body)
    # 記錄到日誌
    logger.warning(f"Alert: {title} - {body}")

coordinator.set_alert_callback(handle_alert)
```

---

## 測試

### 測試檔案

`tests/test_startup_recovery.py` 包含完整的測試案例：

| 測試類別 | 說明 |
|---------|------|
| `TestServiceConfigStartupRetry` | 測試配置選項 |
| `TestStartupRecovery` | 測試重試邏輯 |
| `TestStartupRecoveryIntegration` | 整合測試 |

### 執行測試

```bash
# 執行啟動恢復相關測試
python3 -m pytest tests/test_startup_recovery.py -v

# 執行所有服務協調器測試
python3 -m pytest tests/test_service_coordinator.py tests/test_startup_recovery.py -v
```

### 模擬不穩定服務

測試中使用 `FlakeyService` 模擬不穩定的服務：

```python
class FlakeyService(ServiceBase):
    """前幾次啟動會失敗，之後成功"""
    
    def __init__(self, name: str, failures_before_success: int = 2):
        self._failures_before_success = failures_before_success
        self._start_attempts = 0
    
    async def start(self) -> bool:
        self._start_attempts += 1
        if self._start_attempts <= self._failures_before_success:
            return False
        return True
```

---

## 相關文件

| 文件 | 說明 |
|------|------|
| `src/common/service_types.py` | ServiceConfig 和 ServiceState 定義 |
| `src/robot_service/service_coordinator.py` | 服務協調器實作 |
| `tests/test_startup_recovery.py` | 測試案例 |
| `docs/PROJECT_MEMORY.md` | 專案記憶（含經驗教訓） |
| `docs/development/UNIFIED_LAUNCHER_GUIDE.md` | 統一啟動器指南 |

---

**最後更新**：2025-12-03
