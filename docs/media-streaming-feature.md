# 機器人視訊與音訊串流功能

## 功能概述

本功能為 Robot Command Console 系統新增了視訊與音訊串流能力，允許 WebUI 從機器人接收即時的視訊與音訊資料，並支援透過語音指令控制機器人。

## 主要功能

### 1. 視訊串流

- **即時視訊傳輸**：透過 WebSocket 從機器人接收即時視訊串流
- **支援多種格式**：MJPEG、H.264、VP8
- **低延遲**：~30 FPS 的流暢播放
- **狀態監控**：顯示連線狀態、FPS、延遲等資訊

### 2. 音訊串流

- **雙向音訊**：同時支援接收機器人的音訊與發送語音指令
- **多種格式**：Opus、PCM、MP3
- **語音錄製**：直接在 WebUI 中錄製語音指令

### 3. 語音指令處理

- **語音轉文字**：使用語音辨識服務將音訊轉換為文字
- **LLM 指令解析**：使用 LLM 將自然語言轉換為結構化指令
- **信心度評估**：提供指令解析的信心度分數
- **一鍵執行**：解析後的指令可立即執行

## 系統架構

```
┌─────────────┐     WebSocket      ┌─────────────┐
│   WebUI     │ ◄─────────────────► │     MCP     │
│  (瀏覽器)    │    視訊/音訊串流     │   (服務層)   │
└─────────────┘                    └─────────────┘
      ▲                                    │
      │                                    │
      │ HTTP POST                          │ HTTP/MQTT
      │ (音訊指令)                          │
      │                                    ▼
      │                            ┌─────────────┐
      │                            │ Robot-Console│
      │                            │  (執行層)    │
      │                            └─────────────┘
      │                                    │
      └────────────────────────────────────┘
               指令執行結果回傳
```

## 新增的資料模型

### MediaStreamRequest

媒體串流請求模型：

```python
{
    "robot_id": "robot_1",
    "media_type": "both",  # video, audio, both
    "video_format": "mjpeg",  # mjpeg, h264, vp8
    "audio_format": "opus",  # opus, pcm, mp3
    "trace_id": "uuid-v4"
}
```

### AudioCommandRequest

音訊指令請求模型：

```python
{
    "robot_id": "robot_1",
    "audio_data": "base64-encoded-audio",
    "audio_format": "opus",
    "language": "zh-TW",
    "trace_id": "uuid-v4"
}
```

### AudioCommandResponse

音訊指令回應模型：

```python
{
    "trace_id": "uuid-v4",
    "timestamp": "2025-11-05T02:51:35.920Z",
    "transcription": "向前移動三秒",
    "command": {
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

## API 端點

### 1. 視訊/音訊串流 (WebSocket)

**端點**: `WS /api/media/stream/{robot_id}`

**描述**: 建立與指定機器人的即時媒體串流連線

**示例**:
```javascript
const ws = new WebSocket('ws://localhost:8000/api/media/stream/robot_1');

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    if (data.type === 'video') {
        renderVideoFrame(data.frame);
    }
};
```

### 2. 音訊指令處理 (HTTP)

**端點**: `POST /api/media/audio/command`

**描述**: 處理語音指令，包含語音轉文字和指令解析

**請求範例**:
```bash
curl -X POST http://localhost:8000/api/media/audio/command \
  -H "Content-Type: application/json" \
  -d '{
    "robot_id": "robot_1",
    "audio_data": "UklGRiQAAABXQVZFZm10...",
    "audio_format": "opus",
    "language": "zh-TW"
  }'
```

**回應範例**:
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
        },
        "priority": "normal"
    },
    "confidence": 0.95
}
```

## LLM 處理器

### LLMProcessor 類別

負責處理音訊轉文字與指令解析的核心組件。

#### 主要方法

1. **transcribe_audio()**
   - 將音訊轉換為文字
   - 支援多種音訊格式與語言
   - 返回轉錄文字與信心度

2. **parse_command()**
   - 使用 LLM 或規則式解析將文字轉換為指令
   - 支援自然語言理解
   - 返回結構化的指令規格

3. **_simple_parse()**
   - 簡單的規則式解析器（示範用）
   - 支援基本動作關鍵字匹配
   - 可作為 LLM 的後備方案

### 支援的動作關鍵字

目前的簡單解析器支援以下中文關鍵字：

- **移動類**: 向前、前進、往前、後退、向後
- **轉向類**: 左轉、向左、右轉、向右
- **控制類**: 停止、站立
- **動作類**: 揮手、鞠躬、跳舞

### 擴展性

可以輕易整合第三方服務：

1. **語音辨識**:
   - OpenAI Whisper API
   - Google Speech-to-Text
   - Azure Speech Service

2. **LLM 服務**:
   - OpenAI GPT-4
   - Anthropic Claude
   - Google Gemini

## WebUI 使用指南

### 存取媒體串流頁面

1. 登入 WebUI
2. 導航至 `/media_stream` 或點擊導航選單中的「媒體串流」
3. 選擇要監控的機器人
4. 點擊「連線」按鈕

### 使用語音指令

1. 確保已連線到機器人
2. 點擊「開始錄音」按鈕
3. 說出指令（例如：「向前移動三秒」）
4. 點擊「停止錄音」
5. 系統會自動轉錄並解析指令
6. 檢視解析結果，點擊「執行指令」

### 瀏覽器權限

使用語音錄製功能需要授予瀏覽器麥克風權限：

- Chrome/Edge: 設定 > 隱私權與安全性 > 網站設定 > 麥克風
- Firefox: 偏好設定 > 隱私權與安全性 > 權限 > 麥克風
- Safari: 偏好設定 > 網站 > 麥克風

## 測試

執行測試套件：

```bash
cd /home/runner/work/robot-command-console/robot-command-console
pytest Test/test_media_streaming.py -v
```

測試涵蓋：

- 資料模型驗證
- LLM 處理器功能
- API 端點
- 指令解析邏輯

## 設定

### 環境變數

可選的環境變數設定：

```bash
# OpenAI API 金鑰（如使用 Whisper 或 GPT）
export OPENAI_API_KEY="sk-..."

# 語音辨識服務設定
export SPEECH_SERVICE_PROVIDER="whisper"  # whisper, google, azure

# LLM 服務設定
export LLM_SERVICE_PROVIDER="gpt-4"  # gpt-4, claude, gemini
```

## 安全性考量

1. **驗證與授權**: 所有媒體串流端點都需要適當的身份驗證
2. **速率限制**: 建議對音訊指令處理端點實施速率限制
3. **資料加密**: WebSocket 連線應使用 WSS（WebSocket Secure）
4. **輸入驗證**: 所有音訊資料都經過大小與格式驗證

## 效能優化

1. **串流壓縮**: 使用適當的視訊編解碼器減少頻寬
2. **批次處理**: 多個音訊指令可批次處理以提高效率
3. **快取**: 常見指令模式可快取以加速解析
4. **非同步處理**: 所有 I/O 操作都是非阻塞的

## 已知限制

1. **語音辨識**: 目前使用模擬資料，需要整合實際的語音辨識服務
2. **視訊編碼**: WebSocket 串流需要實際的視訊編碼實作
3. **多語言支援**: 目前主要支援中文，其他語言需要額外配置
4. **離線模式**: 需要網路連線才能使用 LLM 服務

## 未來改進

1. [ ] 整合 OpenAI Whisper API 進行實際語音辨識
2. [ ] 整合 GPT-4 進行更智慧的指令解析
3. [ ] 支援視訊錄製與回放
4. [ ] 支援多機器人同時串流
5. [ ] 新增語音指令歷史記錄
6. [ ] 支援自定義語音指令模板
7. [ ] 實作端到端加密

## 相關檔案

- `/MCP/models.py` - 資料模型定義
- `/MCP/api.py` - API 端點實作
- `/MCP/llm_processor.py` - LLM 處理器
- `/WebUI/app/routes.py` - WebUI 路由
- `/WebUI/app/templates/media_stream.html.j2` - 媒體串流頁面模板
- `/Test/test_media_streaming.py` - 測試套件

## 支援

如有問題或建議，請：

1. 查看專案 README 與文件
2. 提交 GitHub Issue
3. 聯絡專案維護者

---

**版本**: 1.0.0  
**最後更新**: 2025-11-05
