# LLM IPC Discovery PoC - 快速開始

> **版本**：1.0.0  
> **狀態**：PoC 完成  
> **分支**：`copilot/create-llm-ipc-discovery-poc`

## 概覽

LLM IPC Discovery Protocol 是一個用於 Edge 環境的 **LLM Compatible Software（llm-cop）發現與技能註冊機制**，支援：

1. **什麼是 llm-cop？**
   - **llm-cop** = **LLM Compatible Software**（LLM 相容軟體）
   - 讓 LLM 能夠透過技能（skills）操作軟體的相容軟體

2. **雙向互動能力**：
   - **LLM → Software**：LLM 透過 OpenAI function calling 操作軟體功能
   - **Software → LLM**：軟體提供資訊給 LLM 查詢和理解

3. **防止模型解密攻擊**：
   - 不記錄 prompt
   - 不暴露模型內部狀態
   - 回應過濾與記憶體清理

4. **跨平台支援**：
   - Linux, macOS, Windows
   - HTTP, Unix socket, TCP

## 快速開始

### 1. 安裝依賴

```bash
pip install pytest jsonschema
```

### 2. 註冊 llm-cop Provider

```bash
python examples/provider.py
```

輸入 `y` 確認註冊。這會創建一個範例 llm-cop（LLM Compatible Software），包含 4 個 skills：
- `code_review` - 程式碼審查
- `refactor` - 程式碼重構
- `security_scan` - 安全掃描（支援資訊查詢）
- `system_monitor` - 系統監控（支援資訊查詢）

### 3. 發現 Provider

```bash
python examples/llm_core.py
```

這會掃描並顯示：
- 所有註冊的 llm-cop（LLM Compatible Software）
- 健康狀態檢查
- Skills 列表（LLM 可用來操作軟體的功能）
- 可提供的資訊類型

### 4. 運行測試

```bash
pytest tests/test_discovery.py -v
```

## 文件結構

```
docs/
├── implementation/
│   ├── llm_ipc_protocol.md     # 完整協定規格
│   └── LLM_IPC_README.md       # 本文件
└── contract/
    └── manifest_schema.json    # Manifest JSON Schema

src/
└── llm_discovery/
    ├── __init__.py
    ├── models.py               # 資料模型
    ├── scanner.py              # 檔案系統掃描器
    ├── probe.py                # 端點探測器
    ├── discovery_service.py    # 發現服務
    └── security.py             # 安全模組

examples/
├── provider.py                 # Provider 註冊範例
└── llm_core.py                 # Discovery 使用範例

tests/
└── test_discovery.py           # 單元測試
```

## 核心概念

### Manifest 檔案

llm-cop（LLM Compatible Software）透過 manifest 檔案註冊到系統：

**位置**：
- Linux: `~/.local/share/llm-providers/<provider-id>.json`
- macOS: `~/Library/Application Support/llm-providers/<provider-id>.json`
- Windows: `%LOCALAPPDATA%\llm-providers\<provider-id>.json`

**權限**：0600 (僅擁有者可讀寫)

### Skill 定義

每個 skill 包含兩個部分：

1. **Function Definition**（LLM 操作軟體）
   ```python
   {
       "name": "code_review",
       "description": "Review code quality",
       "parameters": {...}
   }
   ```

2. **Info Schema**（軟體提供資訊給 LLM）
   ```python
   {
       "provides": ["scan_history", "metrics"],
       "query_methods": {
           "get_stats": {...}
       }
   }
   ```

### 安全機制

1. **Prompt 保護**
   - `PromptSanitizer.sanitize_for_logging()` - 不記錄 prompt
   - `PromptSanitizer.clear_from_memory()` - 清除記憶體

2. **回應過濾**
   - `ResponseFilter.filter_prompt_echo()` - 移除 prompt 回顯
   - `ResponseFilter.remove_metadata()` - 移除敏感元資料

3. **Prompt Injection 檢測**
   - `ResponseFilter.detect_prompt_injection()` - 識別攻擊

## 使用範例

### 程式碼整合

```python
from llm_discovery import DiscoveryService

# 初始化
discovery = DiscoveryService()

# 掃描 providers
providers = await discovery.scan_providers()

# 檢查健康狀態
health = await discovery.check_health("example-llm-cop")

# 搜尋 skills
skills = await discovery.search_skills(category="security")

# 查詢資訊（軟體→LLM）
info = await discovery.query_skill_info(
    provider_id="example-llm-cop",
    skill_id="system_monitor",
    query_method="get_status"
)
```

### 與 OpenAI SDK 整合

```python
import openai

# 配置為使用本地 llm-cop
openai.api_base = "http://localhost:9001/v1"
openai.api_key = "not-needed"

# 使用 function calling
response = openai.ChatCompletion.create(
    model="code_review",
    messages=[{"role": "user", "content": "Review this code"}],
    functions=[{
        "name": "code_review",
        "description": "Review code quality",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {"type": "string"}
            }
        }
    }]
)
```

## API 介面

### DiscoveryService

| 方法 | 描述 |
|------|------|
| `scan_providers()` | 掃描所有註冊的 providers |
| `check_health(provider_id)` | 檢查 provider 健康狀態 |
| `get_available_providers()` | 獲取可用的 providers |
| `search_skills(keyword, category)` | 搜尋 skills |
| `query_skill_info(...)` | 查詢 skill 提供的資訊 |
| `register_provider(manifest)` | 註冊新 provider（需用戶同意） |
| `unregister_provider(provider_id)` | 取消註冊 |

### FilesystemScanner

| 方法 | 描述 |
|------|------|
| `get_registry_path()` | 獲取 registry 路徑 |
| `scan_manifests()` | 掃描所有 manifest 檔案 |
| `save_manifest(manifest)` | 儲存 manifest（權限 0600） |
| `delete_manifest(provider_id)` | 刪除 manifest |

### EndpointProbe

| 方法 | 描述 |
|------|------|
| `check_http_endpoint(endpoint)` | 檢查 HTTP 端點 |
| `check_unix_socket(endpoint)` | 檢查 Unix socket |
| `check_provider_health(...)` | 檢查 provider 整體健康 |

## 安全最佳實踐

### Provider 開發者

1. **啟用所有防解密措施**
   ```python
   anti_decryption=AntiDecryptionConfig(
       no_prompt_logging=True,
       no_model_exposure=True,
       prompt_sanitization=True,
       response_filtering=True,
       memory_cleanup=True
   )
   ```

2. **限制本地連接**
   - 端點僅監聽 `127.0.0.1`
   - 使用 Unix socket（Linux/macOS）

3. **不暴露敏感 API**
   - 禁止 `/model/weights` 等端點
   - 僅提供功能介面

### 使用者

1. **檢查 manifest 權限**
   ```bash
   ls -la ~/.local/share/llm-providers/
   # 應為 -rw------- (0600)
   ```

2. **審查 skills**
   - 檢查 function_definition
   - 確認 info_schema 不洩露敏感資訊

3. **監控健康狀態**
   ```python
   health = await discovery.check_health(provider_id)
   if health.consecutive_failures > 3:
       # 調查問題
   ```

## 測試結果

```bash
$ pytest tests/test_discovery.py -v
================================================= test session starts ==================================================
...
tests/test_discovery.py::TestModels::test_anti_decryption_config PASSED                                          [  4%]
tests/test_discovery.py::TestModels::test_endpoint_creation PASSED                                               [  9%]
tests/test_discovery.py::TestModels::test_skill_creation PASSED                                                  [ 14%]
tests/test_discovery.py::TestModels::test_skill_with_function_definition PASSED                                  [ 19%]
tests/test_discovery.py::TestModels::test_provider_manifest_creation PASSED                                      [ 23%]
tests/test_discovery.py::TestModels::test_provider_manifest_to_dict PASSED                                       [ 28%]
tests/test_discovery.py::TestModels::test_provider_manifest_get_openai_functions PASSED                          [ 33%]
tests/test_discovery.py::TestModels::test_provider_manifest_from_dict PASSED                                     [ 38%]
tests/test_discovery.py::TestSecurity::test_prompt_sanitizer_for_logging PASSED                                  [ 42%]
tests/test_discovery.py::TestSecurity::test_prompt_sanitizer_remove_sensitive_info PASSED                        [ 47%]
tests/test_discovery.py::TestSecurity::test_response_filter_prompt_echo PASSED                                   [ 52%]
tests/test_discovery.py::TestSecurity::test_response_filter_remove_metadata PASSED                               [ 57%]
tests/test_discovery.py::TestSecurity::test_response_filter_detect_prompt_injection PASSED                       [ 61%]
tests/test_discovery.py::TestSecurity::test_memory_guard_secure_delete PASSED                                    [ 66%]
tests/test_discovery.py::TestSecurity::test_memory_guard_secure_context PASSED                                   [ 71%]
tests/test_discovery.py::TestEndpointProbe::test_probe_http_endpoint_invalid PASSED                              [ 76%]
tests/test_discovery.py::TestEndpointProbe::test_probe_unix_socket_invalid PASSED                                [ 80%]
tests/test_discovery.py::TestEndpointProbe::test_check_provider_health PASSED                                    [ 85%]
tests/test_discovery.py::TestFilesystemScanner::test_get_registry_path PASSED                                    [ 90%]
tests/test_discovery.py::TestFilesystemScanner::test_save_and_load_manifest PASSED                               [ 95%]
tests/test_discovery.py::TestFilesystemScanner::test_scan_manifests PASSED                                       [100%]

================================================== 21 passed in 0.09s ==================================================
```

## 下一步

### Phase 3.3 擴充

- [ ] 實際 LLM Copilot 實作（運行 HTTP 服務）
- [ ] 與 MCP Service 整合
- [ ] 雲端註冊中心（可選，需用戶同意）
- [ ] mTLS 支援
- [ ] Manifest 簽名驗證

### Phase 3.4 優化

- [ ] 更多端點類型（WebSocket）
- [ ] 進階健康檢查（深度探測）
- [ ] 性能監控與遙測
- [ ] 自動更新機制

## 疑難排解

### Provider 無法發現

```bash
# 檢查 registry 路徑
python -c "from llm_discovery.scanner import FilesystemScanner; print(FilesystemScanner.get_registry_path())"

# 檢查 manifest 檔案
ls -la ~/.local/share/llm-providers/
```

### 端點無法連接

```bash
# 確保服務正在運行
curl http://localhost:9001/health

# 檢查 manifest 中的端點配置
cat ~/.local/share/llm-providers/<provider-id>.json | grep -A5 endpoints
```

### 權限問題

```bash
# 修復 manifest 權限
chmod 600 ~/.local/share/llm-providers/*.json
```

## 相關文件

- [完整協定規格](llm_ipc_protocol.md)
- [Manifest Schema](../contract/manifest_schema.json)
- [專案架構](../architecture.md)
- [Phase 3 計畫](../plans/MASTER_PLAN.md)

## 授權

本專案遵循 Robot Command Console 專案的授權條款。

## 貢獻者

- GitHub Copilot
- Robot Command Console Team

---

**最後更新**：2025-12-10
