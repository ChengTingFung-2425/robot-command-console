#!/usr/bin/env python3
"""
媒體串流功能示範腳本

此腳本展示如何使用新增的媒體串流與音訊指令處理功能。
"""

import sys
import os
# 將專案根目錄加入 Python 路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import base64
import json
from datetime import datetime


async def demo_audio_command_processing():
    """示範音訊指令處理功能"""
    print("=" * 60)
    print("媒體串流與音訊指令處理功能示範")
    print("=" * 60)
    print()
    
    # 1. 測試 LLM 處理器
    print("1. 測試 LLM 處理器")
    print("-" * 60)
    
    from MCP.llm_processor import LLMProcessor
    
    processor = LLMProcessor()
    
    # 測試語音轉錄
    print("  測試語音轉錄...")
    fake_audio = b"fake audio data"
    transcription, confidence = await processor.transcribe_audio(
        audio_bytes=fake_audio,
        audio_format="opus",
        language="zh-TW"
    )
    print(f"  轉錄結果: {transcription}")
    print(f"  信心度: {confidence * 100:.1f}%")
    print()
    
    # 測試指令解析 - 各種情況
    test_cases = [
        ("向前移動三秒", "robot_1"),
        ("左轉五秒", "robot_2"),
        ("揮手", "robot_3"),
        ("跳舞十秒", "robot_4"),
        ("後退", "robot_5"),
        ("這是一個無效的指令", "robot_6"),
    ]
    
    print("  測試指令解析...")
    for text, robot_id in test_cases:
        command = await processor.parse_command(
            transcription=text,
            robot_id=robot_id
        )
        
        if command:
            print(f"  ✓ '{text}' → {command.params['action_name']} "
                  f"({command.params['duration_ms']}ms)")
        else:
            print(f"  ✗ '{text}' → 無法解析")
    
    print()
    
    # 2. 測試資料模型
    print("2. 測試資料模型")
    print("-" * 60)
    
    from MCP.models import (
        MediaStreamRequest, AudioCommandRequest, AudioCommandResponse,
        MediaType, StreamFormat, CommandSpec, CommandTarget, Priority
    )
    
    # 建立媒體串流請求
    stream_request = MediaStreamRequest(
        robot_id="robot_1",
        media_type=MediaType.BOTH,
        video_format=StreamFormat.MJPEG,
        audio_format=StreamFormat.OPUS
    )
    print(f"  媒體串流請求: {stream_request.robot_id}")
    print(f"    媒體類型: {stream_request.media_type}")
    print(f"    視訊格式: {stream_request.video_format}")
    print(f"    音訊格式: {stream_request.audio_format}")
    print()
    
    # 建立音訊指令請求
    audio_data = base64.b64encode(b"sample audio").decode('utf-8')
    audio_request = AudioCommandRequest(
        robot_id="robot_1",
        audio_data=audio_data,
        audio_format=StreamFormat.OPUS,
        language="zh-TW"
    )
    print(f"  音訊指令請求: {audio_request.robot_id}")
    print(f"    語言: {audio_request.language}")
    print(f"    音訊格式: {audio_request.audio_format}")
    print()
    
    # 建立音訊指令回應
    command_spec = CommandSpec(
        type="robot.action",
        target=CommandTarget(robot_id="robot_1"),
        params={"action_name": "go_forward", "duration_ms": 3000},
        priority=Priority.NORMAL
    )
    
    audio_response = AudioCommandResponse(
        trace_id="demo-trace-123",
        transcription="向前移動三秒",
        command=command_spec,
        confidence=0.95
    )
    
    print(f"  音訊指令回應:")
    print(f"    轉錄: {audio_response.transcription}")
    print(f"    指令: {audio_response.command.params['action_name']}")
    print(f"    信心度: {audio_response.confidence * 100:.1f}%")
    print()
    
    # 3. JSON 序列化測試
    print("3. JSON 序列化測試")
    print("-" * 60)
    
    response_dict = audio_response.model_dump()
    response_json = json.dumps(response_dict, indent=2, ensure_ascii=False, default=str)
    print(f"  JSON 輸出:")
    print("  " + "\n  ".join(response_json.split("\n")))
    print()
    
    # 4. 總結
    print("=" * 60)
    print("功能測試完成！")
    print()
    print("可用的 API 端點：")
    print("  - WS /api/media/stream/{robot_id}  (媒體串流)")
    print("  - POST /api/media/audio/command    (音訊指令處理)")
    print()
    print("可用的 WebUI 頁面：")
    print("  - GET /media_stream                (媒體串流介面)")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(demo_audio_command_processing())
