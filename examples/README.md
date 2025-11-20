# 視訊與音訊串流功能使用指南

## 快速開始

### 1. 啟動 MCP 服務

```bash
cd /home/runner/work/robot-command-console/robot-command-console
python3 -m MCP.api
```

服務將在 `http://localhost:8000` 啟動。

### 2. 存取 WebUI 媒體串流頁面

在瀏覽器中訪問：
```
http://localhost:5000/media_stream
```

### 3. 使用示範腳本

```bash
python3 examples/demo_media_streaming.py
```

## 主要功能

### 視訊串流

透過 WebSocket 連線接收機器人的即時視訊串流：

```javascript
const ws = new WebSocket('ws://localhost:8000/api/media/stream/robot_1');

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    if (data.type === 'video') {
        // 處理視訊幀
        renderVideoFrame(data.frame);
    }
};
```

### 音訊指令處理

發送音訊資料以進行語音辨識和指令解析：

```python
import base64
import requests

# 準備音訊資料（Base64 編碼）
with open('audio.wav', 'rb') as f:
    audio_bytes = f.read()
audio_data = base64.b64encode(audio_bytes).decode('utf-8')

# 發送請求
response = requests.post(
    'http://localhost:8000/api/media/audio/command',
    json={
        'robot_id': 'robot_1',
        'audio_data': audio_data,
        'audio_format': 'opus',
        'language': 'zh-TW'
    }
)

result = response.json()
print(f"轉錄: {result['transcription']}")
print(f"指令: {result['command']}")
```

### 支援的語音指令

目前簡單解析器支援以下中文指令：

- **移動指令**: "向前移動"、"前進"、"後退"
- **轉向指令**: "左轉"、"右轉"
- **控制指令**: "停止"、"站立"
- **動作指令**: "揮手"、"鞠躬"、"跳舞"

時間可以使用中文數字或阿拉伯數字：
- "向前移動三秒"
- "左轉5秒"
- "跳舞十秒"

## API 參考

### WebSocket: 媒體串流

**端點**: `WS /api/media/stream/{robot_id}`

**訊息格式**:
```json
{
    "type": "video|audio|status",
    "robot_id": "robot_1",
    "timestamp": "2025-11-05T02:51:35.920Z",
    "frame": "base64-encoded-data"  // 僅視訊
}
```

### HTTP POST: 音訊指令處理

**端點**: `POST /api/media/audio/command`

**請求格式**:
```json
{
    "robot_id": "robot_1",
    "audio_data": "base64-encoded-audio",
    "audio_format": "opus",
    "language": "zh-TW",
    "trace_id": "optional-trace-id"
}
```

**回應格式**:
```json
{
    "trace_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2025-11-05T02:51:35.920Z",
    "transcription": "向前移動三秒",
    "command": {
        "id": "cmd-abc123",
        "type": "robot.action",
        "target": {"robot_id": "robot_1"},
        "params": {
            "action_name": "go_forward",
            "duration_ms": 3000
        }
    },
    "confidence": 0.95
}
```

## 整合 LLM 服務

要整合實際的語音辨識和 LLM 服務，請編輯 `MCP/llm_processor.py`：

### 整合 OpenAI Whisper

```python
import openai

async def transcribe_audio(self, audio_bytes, audio_format="opus", language="zh-TW"):
    response = openai.Audio.transcribe(
        model="whisper-1",
        file=audio_bytes,
        language=language
    )
    return response.text, 0.9  # 返回轉錄與信心度
```

### 整合 GPT-4 指令解析

```python
import openai

async def parse_command(self, transcription, robot_id, context=None):
    prompt = f"""
    將以下指令轉換為機器人動作：
    使用者說：{transcription}
    
    回傳 JSON 格式：
    {{"action_name": "動作名稱", "duration_ms": 毫秒}}
    """
    
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    
    result = json.loads(response.choices[0].message.content)
    # 建立並回傳 CommandSpec...
```

## 測試

執行測試套件：

```bash
pytest tests/test_media_streaming.py -v
```

預期結果：11 個測試通過，1 個測試跳過。

## 疑難排解

### 問題：WebSocket 連線失敗

**解決方案**：
- 確認 MCP 服務正在運行
- 檢查防火牆設定
- 使用瀏覽器開發者工具檢查 WebSocket 連線

### 問題：音訊錄製無法啟動

**解決方案**：
- 檢查瀏覽器麥克風權限
- 確認使用 HTTPS（某些瀏覽器需要）
- 嘗試使用不同的瀏覽器

### 問題：語音辨識結果不準確

**解決方案**：
- 目前使用模擬資料，需要整合實際的語音辨識服務
- 改善音訊品質（降噪、提高取樣率）
- 調整語言模型設定

## 後續開發

- [ ] 整合 OpenAI Whisper API
- [ ] 整合 GPT-4 進行智慧指令解析
- [ ] 支援視訊錄製與回放
- [ ] 新增多機器人同時串流
- [ ] 實作端到端加密
- [ ] 優化視訊壓縮以降低頻寬使用

## 相關文件

- [完整功能文件](../docs/media-streaming-feature.md)
- [MCP API 文件](../MCP/README.md)
- [WebUI 使用指南](../WebUI/README.md)
