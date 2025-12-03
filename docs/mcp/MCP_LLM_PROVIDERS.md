# MCP 本地 LLM 提供商整合指南

本文件說明如何使用 MCP (Model Context Protocol) 服務的本地 LLM 提供商自動偵測與插件架構。

## 概覽

MCP 現在支援自動偵測和整合本地 LLM 提供商（如 Ollama、LM Studio 等），讓您可以：

- **自動偵測**：MCP 在啟動時會自動掃描並偵測本地運行的 LLM 服務
- **插件式架構**：輕鬆新增新的 LLM 提供商而無需修改 MCP 核心程式碼
- **動態切換**：透過 API 動態選擇和切換不同的 LLM 提供商
- **健康監控**：即時監控提供商的健康狀態與可用性
- **模型管理**：列出和選擇可用的 LLM 模型

## 支援的提供商

### Ollama
- **預設埠號**：11434
- **協定**：HTTP REST API
- **功能**：文字生成、模型管理
- **安裝**：[https://ollama.ai](https://ollama.ai)

### LM Studio
- **預設埠號**：1234
- **協定**：OpenAI 相容 API
- **功能**：文字生成、對話
- **安裝**：[https://lmstudio.ai](https://lmstudio.ai)

## 快速開始

### 1. 安裝本地 LLM 服務

#### Ollama
```bash
# macOS/Linux
curl -fsSL https://ollama.ai/install.sh | sh

# 啟動服務
ollama serve

# 下載模型
ollama pull llama2
ollama pull mistral
```

#### LM Studio
1. 從官網下載並安裝 LM Studio
2. 在 LM Studio 中下載模型
3. 啟動本地伺服器（預設埠 1234）

### 2. 啟動 MCP 服務

```bash
cd MCP
python3 start.py
```

MCP 會在啟動時自動偵測運行中的本地 LLM 提供商。

### 3. 驗證提供商狀態

```bash
# 查看所有提供商
curl http://localhost:8000/api/llm/providers

# 查看提供商健康狀態
curl http://localhost:8000/api/llm/providers/health
```

## API 端點

### 列出提供商
```http
GET /api/llm/providers
```

回應：
```json
{
  "providers": ["ollama", "lmstudio"],
  "selected": "ollama",
  "count": 2
}
```

### 查看提供商健康狀態
```http
GET /api/llm/providers/health
```

回應：
```json
{
  "providers": {
    "ollama": {
      "status": "available",
      "version": "0.1.17",
      "available_models": ["llama2", "mistral"],
      "error_message": null,
      "response_time_ms": 45.2
    },
    "lmstudio": {
      "status": "unavailable",
      "version": null,
      "available_models": [],
      "error_message": "連線錯誤: Connection refused",
      "response_time_ms": null
    }
  },
  "timestamp": "2025-11-20T04:00:00.000Z"
}
```

### 手動觸發偵測
```http
POST /api/llm/providers/discover
Content-Type: application/json

{
  "host": "localhost",
  "timeout": 5
}
```

### 選擇提供商
```http
POST /api/llm/providers/select
Content-Type: application/json

{
  "provider_name": "ollama",           // 必填，提供商名稱
  "model_name": "llama2:latest",       // 選填，指定要使用的模型
  "save_preference": true              // 選填，預設為 true，是否保存為用戶偏好
}
```

回應：
```json
{
  "message": "提供商切換成功",
  "provider": "ollama",
  "preference_saved": true
}
```

### 取得用戶 LLM 偏好設定
```http
GET /api/llm/preferences
```

回應：
```json
{
  "provider": "ollama",
  "model": "llama2:latest",
  "success": true
}
```

### 保存用戶 LLM 偏好設定
```http
POST /api/llm/preferences
Content-Type: application/json

{
  "provider": "ollama",    // 選填參數
  "model": "llama2:latest" // 選填參數
}
```

> **說明：**
> - `provider` 與 `model` 皆為選填參數，可僅提供其中之一或皆不提供。
> - 若未提供某欄位，則該欄位不會被更新。
> - 若提供 `null` 值，則可用於清除偏好設定。

回應：
```json
{
  "success": true,
  "provider": "ollama",
  "model": "llama2:latest",
  "message": "LLM 偏好設定已保存"
}
```

### 列出提供商的模型
```http
GET /api/llm/providers/ollama/models
```

回應：
```json
{
  "provider": "ollama",
  "models": [
    {
      "id": "llama2:latest",
      "name": "llama2:latest",
      "size": "7B",
      "capabilities": {
        "supports_streaming": true,
        "supports_vision": false,
        "supports_function_calling": false,
        "context_length": 4096,
        "max_tokens": 2048
      },
      "metadata": {
        "size_bytes": 3826793677,
        "modified_at": "2024-11-20T03:00:00Z"
      }
    }
  ],
  "count": 1
}
```

### 重新檢查提供商健康狀態
```http
POST /api/llm/providers/ollama/refresh
```

## 使用 LLM 進行指令解析

MCP 的 LLMProcessor 現在會自動使用可用的本地 LLM 提供商進行指令解析。

### 工作流程

1. **音訊輸入**：使用者透過音訊命令介面輸入指令
2. **語音轉文字**：音訊轉換為文字（目前使用模擬）
3. **LLM 解析**：
   - 優先使用本地 LLM 提供商解析自然語言指令
   - 如果 LLM 不可用或解析失敗，回退到規則式解析
4. **指令執行**：解析後的指令發送給機器人執行

### 範例

```python
from MCP.llm_processor import LLMProcessor
from MCP.llm_provider_manager import LLMProviderManager

# 初始化
manager = LLMProviderManager()
await manager.discover_providers()

processor = LLMProcessor(provider_manager=manager)

# 解析指令
command = await processor.parse_command(
    transcription="請機器人向前移動五秒",
    robot_id="robot-001",
    model="llama2:latest"  # 可選，自動選擇如果未指定
)

print(command.params)  # {"action_name": "go_forward", "duration_ms": 5000}
```

## 開發新的提供商插件

### 1. 建立提供商類別

```python
from MCP.llm_provider_base import LLMProviderBase, ProviderConfig, ProviderHealth

class MyLLMProvider(LLMProviderBase):
    @property
    def provider_name(self) -> str:
        return "myllm"
    
    @property
    def default_port(self) -> int:
        return 8888
    
    async def check_health(self) -> ProviderHealth:
        # 實作健康檢查
        pass
    
    async def list_models(self) -> List[LLMModel]:
        # 實作模型列表
        pass
    
    async def generate(self, prompt: str, model: str, **kwargs) -> Tuple[str, float]:
        # 實作文字生成
        pass
```

### 2. 註冊提供商

```python
from MCP.llm_provider_manager import LLMProviderManager
from my_provider import MyLLMProvider

manager = LLMProviderManager(custom_providers=[MyLLMProvider])
```

### 3. 測試提供商

```python
config = ProviderConfig(name="myllm", host="localhost", port=8888)
provider = MyLLMProvider(config)

health = await provider.check_health()
print(health.status)

models = await provider.list_models()
print([m.id for m in models])
```

## 插件介面規範

### 必須實作的方法

- `provider_name`: 提供商唯一識別名稱
- `default_port`: 預設服務埠號
- `check_health()`: 檢查服務健康狀態
- `list_models()`: 列出可用模型
- `generate()`: 文字生成

### 選用方法

- `transcribe_audio()`: 語音轉文字（若提供商支援）

### 資料結構

#### ProviderConfig
提供商配置資訊，包括主機、埠號、逾時設定等。

#### ProviderHealth
健康狀態資訊，包括可用性、版本、模型列表、錯誤訊息等。

#### LLMModel
模型資訊，包括 ID、名稱、大小、能力等。

#### ModelCapability
模型能力描述，包括串流支援、視覺支援、功能呼叫支援等。

## 自動偵測機制

MCP 使用以下策略偵測本地 LLM 提供商：

1. **埠掃描**：掃描預設埠號（Ollama: 11434, LM Studio: 1234）
2. **健康檢查**：對每個潛在提供商執行健康檢查 API 呼叫
3. **並行偵測**：所有提供商同時進行偵測以加快速度
4. **逾時控制**：每個提供商有獨立的逾時設定（預設 5 秒）
5. **自動註冊**：偵測到可用的提供商自動註冊到管理器

## 錯誤處理與回退

### 提供商不可用
- MCP 繼續運行，使用規則式解析作為回退
- 定期重新檢查提供商可用性
- 記錄錯誤但不中斷服務

### 模型載入失敗
- 回退到其他可用模型
- 如果沒有可用模型，使用規則式解析

### 生成錯誤
- 記錄錯誤詳情
- 回退到規則式解析
- 提供使用者友善的錯誤訊息

## 監控與日誌

### 日誌事件
- 提供商偵測開始/完成
- 提供商註冊/切換
- 健康狀態變化
- API 呼叫錯誤

### Metrics
MCP 的 Prometheus metrics 端點包含 LLM 提供商相關指標：
- 提供商可用性狀態
- API 呼叫回應時間
- 錯誤率

### 範例日誌
```json
{
  "timestamp": "2025-11-20T04:00:00.000Z",
  "level": "INFO",
  "event": "llm_provider_manager",
  "message": "發現可用提供商: ollama (模型數: 2, 回應時間: 45.2ms)",
  "service": "mcp-api"
}
```

## 最佳實踐

### 部署建議

1. **本機開發**：使用 Ollama 進行快速測試
2. **生產環境**：確保 LLM 服務穩定且有足夠資源
3. **多提供商**：配置多個提供商作為備援
4. **監控**：定期檢查提供商健康狀態

### 效能優化

1. **模型選擇**：根據需求選擇適當大小的模型
2. **並行處理**：使用非同步 API 避免阻塞
3. **快取**：考慮快取常見查詢結果
4. **逾時設定**：合理設定逾時避免長時間等待

### 安全性

1. **本地執行**：提供商應在受信任的本地環境執行
2. **網路隔離**：考慮使用防火牆限制存取
3. **認證**：如果提供商支援，啟用 API 認證
4. **日誌敏感資訊**：避免記錄敏感的提示內容

## 疑難排解

### 提供商偵測失敗

**問題**：MCP 無法偵測到正在運行的提供商

**解決方案**：
1. 確認提供商服務正在運行
2. 檢查防火牆設定
3. 驗證埠號是否正確
4. 查看 MCP 日誌獲取詳細錯誤資訊

### 模型列表為空

**問題**：提供商可用但沒有模型

**解決方案**：
1. 確認已下載至少一個模型
2. 重新啟動提供商服務
3. 使用提供商的 CLI 工具驗證模型

### 生成逾時

**問題**：LLM 生成請求逾時

**解決方案**：
1. 增加逾時設定
2. 使用更小的模型
3. 減少 max_tokens 參數
4. 檢查系統資源使用情況

## 參考資源

- [Ollama 文件](https://github.com/ollama/ollama/tree/main/docs)
- [LM Studio 文件](https://lmstudio.ai/docs)
- [MCP 模組設計](../MCP/Module.md)
- [API 參考](../MCP/README.md)

## 貢獻

歡迎貢獻新的提供商插件！請遵循以下步驟：

1. Fork 專案
2. 建立提供商類別（繼承 `LLMProviderBase`）
3. 實作所有必要方法
4. 新增測試
5. 更新文件
6. 提交 Pull Request

## 授權

MIT License
