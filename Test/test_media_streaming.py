"""
測試媒體串流與音訊指令處理功能
"""

import base64
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestMediaStreamingModels:
    """測試媒體串流相關資料模型"""
    
    def test_media_stream_request_model(self):
        """測試媒體串流請求模型"""
        from MCP.models import MediaStreamRequest, MediaType, StreamFormat
        
        request = MediaStreamRequest(
            robot_id="robot_1",
            media_type=MediaType.BOTH,
            video_format=StreamFormat.MJPEG,
            audio_format=StreamFormat.OPUS
        )
        
        assert request.robot_id == "robot_1"
        assert request.media_type == MediaType.BOTH
        assert request.video_format == StreamFormat.MJPEG
        assert request.audio_format == StreamFormat.OPUS
        assert request.trace_id  # 應該自動生成
    
    def test_audio_command_request_model(self):
        """測試音訊指令請求模型"""
        from MCP.models import AudioCommandRequest, StreamFormat
        
        # 模擬 Base64 編碼的音訊資料
        audio_data = base64.b64encode(b"fake audio data").decode('utf-8')
        
        request = AudioCommandRequest(
            robot_id="robot_1",
            audio_data=audio_data,
            audio_format=StreamFormat.OPUS,
            language="zh-TW"
        )
        
        assert request.robot_id == "robot_1"
        assert request.audio_data == audio_data
        assert request.audio_format == StreamFormat.OPUS
        assert request.language == "zh-TW"
        assert request.trace_id
    
    def test_audio_command_response_model(self):
        """測試音訊指令回應模型"""
        from MCP.models import AudioCommandResponse, CommandSpec, CommandTarget, Priority
        from datetime import datetime
        
        command = CommandSpec(
            type="robot.action",
            target=CommandTarget(robot_id="robot_1"),
            params={"action_name": "go_forward", "duration_ms": 3000},
            priority=Priority.NORMAL
        )
        
        response = AudioCommandResponse(
            trace_id="test-trace-123",
            transcription="向前移動三秒",
            command=command,
            confidence=0.95
        )
        
        assert response.trace_id == "test-trace-123"
        assert response.transcription == "向前移動三秒"
        assert response.command.params["action_name"] == "go_forward"
        assert response.confidence == 0.95
        assert isinstance(response.timestamp, datetime)


class TestLLMProcessor:
    """測試 LLM 處理器"""
    
    @pytest.mark.asyncio
    async def test_transcribe_audio(self):
        """測試音訊轉錄功能"""
        from MCP.llm_processor import LLMProcessor
        
        processor = LLMProcessor()
        audio_bytes = b"fake audio data"
        
        transcription, confidence = await processor.transcribe_audio(
            audio_bytes=audio_bytes,
            audio_format="opus",
            language="zh-TW"
        )
        
        # 應該返回模擬的轉錄結果
        assert isinstance(transcription, str)
        assert len(transcription) > 0
        assert 0.0 <= confidence <= 1.0
    
    @pytest.mark.asyncio
    async def test_parse_command_forward(self):
        """測試解析向前移動指令"""
        from MCP.llm_processor import LLMProcessor
        
        processor = LLMProcessor()
        
        command = await processor.parse_command(
            transcription="向前移動三秒",
            robot_id="robot_1"
        )
        
        assert command is not None
        assert command.params["action_name"] == "go_forward"
        assert command.params["duration_ms"] == 3000
        assert command.target.robot_id == "robot_1"
    
    @pytest.mark.asyncio
    async def test_parse_command_turn_left(self):
        """測試解析左轉指令"""
        from MCP.llm_processor import LLMProcessor
        
        processor = LLMProcessor()
        
        command = await processor.parse_command(
            transcription="左轉五秒",
            robot_id="robot_2"
        )
        
        assert command is not None
        assert command.params["action_name"] == "turn_left"
        assert command.params["duration_ms"] == 5000
    
    @pytest.mark.asyncio
    async def test_parse_command_wave(self):
        """測試解析揮手指令"""
        from MCP.llm_processor import LLMProcessor
        
        processor = LLMProcessor()
        
        command = await processor.parse_command(
            transcription="揮手",
            robot_id="robot_3"
        )
        
        assert command is not None
        assert command.params["action_name"] == "wave"
    
    @pytest.mark.asyncio
    async def test_parse_command_unknown(self):
        """測試解析未知指令"""
        from MCP.llm_processor import LLMProcessor
        
        processor = LLMProcessor()
        
        command = await processor.parse_command(
            transcription="這是一個無效的指令",
            robot_id="robot_1"
        )
        
        # 無法解析的指令應該返回 None
        assert command is None
    
    def test_simple_parse_actions(self):
        """測試簡單解析器的各種動作"""
        from MCP.llm_processor import LLMProcessor
        
        processor = LLMProcessor()
        
        test_cases = [
            ("向前移動", "go_forward"),
            ("前進", "go_forward"),
            ("後退", "back_fast"),
            ("向右轉", "turn_right"),
            ("停止", "stop"),
            ("鞠躬", "bow"),
            ("跳舞", "dance_two"),
        ]
        
        for text, expected_action in test_cases:
            result = processor._simple_parse(text)
            assert result is not None, f"無法解析: {text}"
            assert result["action_name"] == expected_action, \
                f"預期動作 {expected_action}，但得到 {result['action_name']}"


class TestMediaStreamAPI:
    """測試媒體串流 API 端點"""
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="需要 FastAPI 依賴，在 CI 環境中可能不可用")
    async def test_process_audio_command_endpoint(self):
        """測試音訊指令處理端點"""
        from fastapi.testclient import TestClient
        from MCP.api import app
        
        client = TestClient(app)
        
        # 模擬音訊資料
        audio_data = base64.b64encode(b"fake audio data").decode('utf-8')
        
        response = client.post(
            "/api/media/audio/command",
            json={
                "robot_id": "robot_1",
                "audio_data": audio_data,
                "audio_format": "opus",
                "language": "zh-TW"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "trace_id" in data
        assert "transcription" in data
        assert "confidence" in data
        assert isinstance(data["transcription"], str)
        assert 0.0 <= data["confidence"] <= 1.0


def test_media_type_enum():
    """測試媒體類型枚舉"""
    from MCP.models import MediaType
    
    assert MediaType.VIDEO == "video"
    assert MediaType.AUDIO == "audio"
    assert MediaType.BOTH == "both"


def test_stream_format_enum():
    """測試串流格式枚舉"""
    from MCP.models import StreamFormat
    
    assert StreamFormat.MJPEG == "mjpeg"
    assert StreamFormat.H264 == "h264"
    assert StreamFormat.OPUS == "opus"
    assert StreamFormat.PCM == "pcm"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
