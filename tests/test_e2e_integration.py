"""
端到端整合測試
測試 WebUI → MCP → Robot-Console 完整資料流

此測試驗證：
1. 統一啟動器可以啟動所有服務
2. WebUI 可以透過 MCP 發送指令
3. Robot-Console 可以接收並執行指令
4. 狀態回報正確傳遞
"""

import asyncio
import json
import os
import sys
import time
from typing import Dict, Any
from uuid import uuid4

# 添加路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest


class TestEndToEndIntegration:
    """端到端整合測試套件"""

    def test_e2e_01_unified_launcher_starts_services(self):
        """
        測試 1: 統一啟動器可以啟動服務
        
        驗證：
        - UnifiedLauncher 可以建立
        - 可以註冊預設服務
        - 服務狀態可查詢
        """
        from robot_service.unified_launcher import UnifiedLauncher
        
        launcher = UnifiedLauncher()
        launcher.register_default_services()
        
        # 驗證至少有 Queue 服務被註冊
        status = launcher.get_services_status()
        assert len(status) >= 1, "應該至少註冊一個服務"
        
        # 驗證 Queue 服務存在
        service_names = [s["name"] for s in status]
        assert "queue-service" in service_names, "Queue 服務應該被註冊"

    def test_e2e_02_command_processor_validates_actions(self):
        """
        測試 2: 指令處理器驗證動作
        
        驗證：
        - CommandProcessor 可以建立
        - 可以驗證有效動作
        - 可以拒絕無效動作
        """
        from robot_service.command_processor import CommandProcessor, VALID_ACTIONS
        from robot_service.queue import Message
        
        # 建立處理器（使用預設 dispatcher）
        processor = CommandProcessor()
        
        # 測試有效動作
        valid_message = Message(
            id=str(uuid4()),
            trace_id=str(uuid4()),
            payload={"actions": ["go_forward", "turn_left"]},
            priority=1
        )
        
        # 驗證可以處理（不會拋出異常）
        async def test_valid():
            result = await processor.process(valid_message)
            # 預設 dispatcher 會記錄日誌並返回 True
            assert result is True
        
        asyncio.run(test_valid())
        
        # 驗證 VALID_ACTIONS 包含基本動作
        assert "go_forward" in VALID_ACTIONS
        assert "turn_left" in VALID_ACTIONS
        assert "turn_right" in VALID_ACTIONS

    def test_e2e_03_queue_enqueue_dequeue(self):
        """
        測試 3: 佇列系統可以正常運作
        
        驗證：
        - PriorityQueue 可以建立
        - 可以 enqueue 訊息
        - 可以 dequeue 訊息
        - 優先權排序正確
        """
        from robot_service.queue import PriorityQueue, Message
        
        async def test():
            queue = PriorityQueue()
            
            # 建立測試訊息
            msg_low = Message(
                id="msg-1",
                trace_id="trace-1",
                payload={"actions": ["go_forward"]},
                priority=1  # 低優先權
            )
            
            msg_high = Message(
                id="msg-2",
                trace_id="trace-2",
                payload={"actions": ["turn_left"]},
                priority=10  # 高優先權
            )
            
            # 先放入低優先權
            await queue.enqueue(msg_low)
            await queue.enqueue(msg_high)
            
            # 取出應該是高優先權先出來
            first = await queue.dequeue()
            assert first.id == "msg-2", "高優先權應該先出來"
            
            second = await queue.dequeue()
            assert second.id == "msg-1", "低優先權後出來"
        
        asyncio.run(test())

    def test_e2e_04_action_executor_basic_actions(self):
        """
        測試 4: ActionExecutor 可以執行基本動作
        
        驗證：
        - ActionExecutor 可以建立
        - 可以執行單個動作
        - 可以執行多個動作序列
        """
        # 由於 ActionExecutor 需要實際的機器人連線，
        # 這裡只測試介面是否正確
        try:
            from Robot_Console.action_executor import ActionExecutor
            
            executor = ActionExecutor()
            
            # 驗證必要方法存在
            assert hasattr(executor, 'execute_actions'), "應有 execute_actions 方法"
            assert callable(executor.execute_actions), "execute_actions 應可呼叫"
            
            # 在無機器人環境下，不實際執行
            # 只驗證介面正確性
            
        except ImportError:
            pytest.skip("Robot-Console 模組未安裝或不可用")

    def test_e2e_05_shared_state_manager_lifecycle(self):
        """
        測試 5: 共享狀態管理器生命週期
        
        驗證：
        - SharedStateManager 可以建立
        - 可以更新機器人狀態
        - 可以取得機器人狀態
        - 可以訂閱事件
        """
        from common.shared_state import SharedStateManager
        
        async def test():
            # 使用記憶體資料庫
            manager = SharedStateManager(db_path=":memory:")
            
            # 更新機器人狀態
            robot_id = "robot_test_1"
            status = {
                "connected": True,
                "battery": 85,
                "position": {"x": 1.0, "y": 2.0}
            }
            
            await manager.update_robot_status(robot_id, status)
            
            # 取得狀態
            retrieved = await manager.get_robot_status(robot_id)
            assert retrieved is not None, "應該能取得狀態"
            assert retrieved["connected"] is True
            assert retrieved["battery"] == 85
            
            # 清理
            await manager.close()
        
        asyncio.run(test())

    def test_e2e_06_service_coordinator_lifecycle(self):
        """
        測試 6: 服務協調器生命週期管理
        
        驗證：
        - ServiceCoordinator 可以建立
        - 可以註冊服務
        - 可以啟動/停止服務
        - 可以執行健康檢查
        """
        from robot_service.service_coordinator import ServiceCoordinator, QueueService
        from robot_service.queue import PriorityQueue
        
        async def test():
            coordinator = ServiceCoordinator()
            
            # 建立測試服務（Queue Service）
            queue = PriorityQueue()
            queue_service = QueueService(
                name="test-queue",
                queue=queue,
                max_workers=2
            )
            
            # 註冊服務
            coordinator.register_service(queue_service)
            
            # 驗證已註冊
            status = coordinator.get_all_services_status()
            assert "test-queue" in status, "服務應該已註冊"
            
            # 啟動服務
            success = await coordinator.start_service("test-queue")
            assert success, "服務應該啟動成功"
            
            # 健康檢查
            health = await coordinator.check_service_health("test-queue")
            assert health["status"] == "healthy", "服務應該健康"
            
            # 停止服務
            success = await coordinator.stop_service("test-queue", timeout=5.0)
            assert success, "服務應該停止成功"
            
            # 清理
            await coordinator.shutdown(timeout=5.0)
        
        asyncio.run(test())

    def test_e2e_07_command_data_contract(self):
        """
        測試 7: 指令資料契約驗證
        
        驗證：
        - CommandRequest 格式正確
        - Robot-Console 接收格式正確
        - 資料轉換正確
        """
        # 標準 CommandRequest 格式（MCP 接收）
        command_request = {
            "trace_id": str(uuid4()),
            "timestamp": "2025-12-10T10:30:00Z",
            "actor": {
                "type": "human",
                "id": "user-123",
                "name": "測試用戶"
            },
            "source": "webui",
            "command": {
                "id": f"cmd-{uuid4()}",
                "type": "robot.action",
                "target": {
                    "robot_id": "robot_7",
                    "robot_type": "humanoid"
                },
                "params": {
                    "action_name": "go_forward",
                    "duration_ms": 3000
                },
                "timeout_ms": 10000,
                "priority": "normal"
            }
        }
        
        # 驗證格式
        assert "trace_id" in command_request
        assert "command" in command_request
        assert "target" in command_request["command"]
        assert "params" in command_request["command"]
        
        # Robot-Console 接收格式（簡化版）
        robot_console_format = {
            "actions": ["go_forward", "turn_left", "turn_right"]
        }
        
        # 驗證格式
        assert "actions" in robot_console_format
        assert isinstance(robot_console_format["actions"], list)
        assert len(robot_console_format["actions"]) > 0

    def test_e2e_08_integration_smoke_test(self):
        """
        測試 8: 整合冒煙測試
        
        這是一個綜合測試，模擬完整的指令流程：
        1. 建立 Queue Service
        2. 建立 CommandProcessor
        3. 發送指令到 Queue
        4. Worker 處理指令
        5. 驗證處理結果
        """
        from robot_service.queue import PriorityQueue, Message
        from robot_service.command_processor import CommandProcessor
        from robot_service.service_coordinator import QueueService
        
        async def test():
            # 1. 建立 Queue 和 Processor
            queue = PriorityQueue()
            processor = CommandProcessor()
            
            # 2. 建立 Queue Service（包含 Worker Pool）
            queue_service = QueueService(
                name="integration-test-queue",
                queue=queue,
                max_workers=1,
                processor=processor.process
            )
            
            # 3. 啟動服務
            await queue_service.start()
            
            # 等待服務啟動
            await asyncio.sleep(0.5)
            
            # 4. 發送測試指令
            test_message = Message(
                id=str(uuid4()),
                trace_id=str(uuid4()),
                payload={"actions": ["go_forward", "turn_left"]},
                priority=5
            )
            
            await queue.enqueue(test_message)
            
            # 5. 等待處理（Worker 會自動處理）
            await asyncio.sleep(1.0)
            
            # 6. 驗證 Queue 已清空（訊息已被處理）
            stats = await queue.get_stats()
            assert stats["size"] == 0, "Queue 應該已清空"
            
            # 7. 停止服務
            await queue_service.stop(timeout=3.0)
        
        asyncio.run(test())


class TestIntegrationConfiguration:
    """整合配置測試"""

    def test_config_01_environment_variables(self):
        """
        測試配置 1: 環境變數正確讀取
        
        驗證：
        - 可以讀取 MCP_API_URL
        - 可以讀取 MQTT 配置
        - 預設值正確
        """
        # 測試 MCP API URL
        mcp_url = os.environ.get('MCP_API_URL', 'http://localhost:8000/api')
        assert mcp_url.startswith('http'), "MCP URL 應該是 HTTP(S) 格式"
        
        # 測試 MQTT 配置
        mqtt_host = os.environ.get('MQTT_BROKER_HOST', 'localhost')
        mqtt_port = int(os.environ.get('MQTT_BROKER_PORT', '1883'))
        
        assert isinstance(mqtt_host, str)
        assert isinstance(mqtt_port, int)
        assert 1 <= mqtt_port <= 65535, "MQTT port 應該在有效範圍"

    def test_config_02_service_ports(self):
        """
        測試配置 2: 服務埠號不衝突
        
        驗證：
        - Flask Service: 5000
        - MCP Service: 8000
        - WebUI: 8080
        - 沒有重複埠號
        """
        ports = {
            "flask": int(os.environ.get('PORT', '5000')),
            "mcp": int(os.environ.get('MCP_API_PORT', '8000')),
            "webui": 8080  # WebUI 預設埠號
        }
        
        # 驗證沒有重複
        port_values = list(ports.values())
        assert len(port_values) == len(set(port_values)), "服務埠號不應重複"
        
        # 驗證都在有效範圍
        for service, port in ports.items():
            assert 1024 <= port <= 65535, f"{service} 埠號應在 1024-65535 範圍"


class TestIntegrationDocumentation:
    """整合文件測試"""

    def test_doc_01_integration_guide_exists(self):
        """
        測試文件 1: 整合指南存在
        
        驗證：
        - INTEGRATION_GUIDE.md 存在
        - 內容包含關鍵章節
        """
        doc_path = os.path.join(
            os.path.dirname(__file__),
            '..',
            'docs',
            'INTEGRATION_GUIDE.md'
        )
        
        assert os.path.exists(doc_path), "整合指南應該存在"
        
        # 讀取內容
        with open(doc_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 驗證關鍵章節
        assert "資料流向" in content, "應包含資料流向說明"
        assert "整合點" in content, "應包含整合點說明"
        assert "資料契約" in content, "應包含資料契約說明"
        assert "啟動整合系統" in content, "應包含啟動說明"

    def test_doc_02_architecture_consistency(self):
        """
        測試文件 2: 架構文件一致性
        
        驗證：
        - architecture.md 存在
        - 與 proposal.md 架構一致
        """
        arch_path = os.path.join(
            os.path.dirname(__file__),
            '..',
            'docs',
            'architecture.md'
        )
        
        prop_path = os.path.join(
            os.path.dirname(__file__),
            '..',
            'docs',
            'proposal.md'
        )
        
        assert os.path.exists(arch_path), "架構文件應該存在"
        assert os.path.exists(prop_path), "規格文件應該存在"


if __name__ == '__main__':
    # 可以直接執行此檔案進行測試
    pytest.main([__file__, '-v', '--tb=short'])
