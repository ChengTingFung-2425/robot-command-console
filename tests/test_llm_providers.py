"""
測試 LLM 提供商插件系統
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from MCP.llm_provider_base import (
    LLMModel,
    LLMProviderBase,
    ModelCapability,
    ProviderConfig,
    ProviderHealth,
    ProviderStatus,
)
from MCP.providers import OllamaProvider, LMStudioProvider
from MCP.llm_provider_manager import LLMProviderManager


class TestProviderBase:
    """測試提供商基底類別"""
    
    def test_provider_config_creation(self):
        """測試提供商配置建立"""
        config = ProviderConfig(
            name="test",
            host="localhost",
            port=8080
        )
        
        assert config.name == "test"
        assert config.host == "localhost"
        assert config.port == 8080
        assert config.timeout == 30  # 預設值
    
    def test_llm_model_creation(self):
        """測試 LLM 模型資訊建立"""
        capabilities = ModelCapability(
            supports_streaming=True,
            context_length=4096
        )
        
        model = LLMModel(
            id="test-model",
            name="Test Model",
            size="7B",
            capabilities=capabilities
        )
        
        assert model.id == "test-model"
        assert model.name == "Test Model"
        assert model.size == "7B"
        assert model.capabilities.supports_streaming is True
        assert model.capabilities.context_length == 4096
    
    def test_provider_health_status(self):
        """測試提供商健康狀態"""
        health = ProviderHealth(
            status=ProviderStatus.AVAILABLE,
            version="1.0.0",
            available_models=["model1", "model2"],
            response_time_ms=123.45
        )
        
        assert health.status == ProviderStatus.AVAILABLE
        assert health.version == "1.0.0"
        assert len(health.available_models) == 2
        assert health.response_time_ms == 123.45


class TestOllamaProvider:
    """測試 Ollama 提供商"""
    
    def test_provider_name(self):
        """測試提供商名稱"""
        config = ProviderConfig(name="ollama", port=11434)
        provider = OllamaProvider(config)
        
        assert provider.provider_name == "ollama"
        assert provider.default_port == 11434
    
    def test_api_endpoint(self):
        """測試 API 端點生成"""
        config = ProviderConfig(
            name="ollama",
            host="localhost",
            port=11434
        )
        provider = OllamaProvider(config)
        
        assert provider.get_api_endpoint() == "http://localhost:11434"
        assert provider.get_api_endpoint("api/tags") == "http://localhost:11434/api/tags"
    
    @pytest.mark.asyncio
    async def test_check_health_unavailable(self):
        """測試健康檢查 - 服務不可用"""
        config = ProviderConfig(
            name="ollama",
            host="localhost",
            port=11434,
            timeout=1
        )
        provider = OllamaProvider(config)
        
        health = await provider.check_health()
        
        # 由於實際服務可能不在運行，應該回傳 UNAVAILABLE 或 ERROR
        assert health.status in [ProviderStatus.UNAVAILABLE, ProviderStatus.ERROR]
    
    @pytest.mark.asyncio
    async def test_list_models_no_service(self):
        """測試列出模型 - 無服務運行"""
        config = ProviderConfig(
            name="ollama",
            host="localhost",
            port=11434,
            timeout=1
        )
        provider = OllamaProvider(config)
        
        models = await provider.list_models()
        
        # 無服務時應回傳空列表
        assert isinstance(models, list)


class TestLMStudioProvider:
    """測試 LM Studio 提供商"""
    
    def test_provider_name(self):
        """測試提供商名稱"""
        config = ProviderConfig(name="lmstudio", port=1234)
        provider = LMStudioProvider(config)
        
        assert provider.provider_name == "lmstudio"
        assert provider.default_port == 1234
    
    def test_api_endpoint(self):
        """測試 API 端點生成"""
        config = ProviderConfig(
            name="lmstudio",
            host="localhost",
            port=1234
        )
        provider = LMStudioProvider(config)
        
        assert provider.get_api_endpoint() == "http://localhost:1234"
        assert provider.get_api_endpoint("v1/models") == "http://localhost:1234/v1/models"
    
    @pytest.mark.asyncio
    async def test_check_health_unavailable(self):
        """測試健康檢查 - 服務不可用"""
        config = ProviderConfig(
            name="lmstudio",
            host="localhost",
            port=1234,
            timeout=1
        )
        provider = LMStudioProvider(config)
        
        health = await provider.check_health()
        
        # 由於實際服務可能不在運行，應該回傳 UNAVAILABLE 或 ERROR
        assert health.status in [ProviderStatus.UNAVAILABLE, ProviderStatus.ERROR]


class TestLLMProviderManager:
    """測試 LLM 提供商管理器"""
    
    def test_manager_initialization(self):
        """測試管理器初始化"""
        manager = LLMProviderManager()
        
        assert len(manager.provider_classes) >= 2  # 至少有 Ollama 和 LM Studio
        assert manager.get_selected_provider_name() is None
    
    def test_list_providers_empty(self):
        """測試列出提供商 - 空列表"""
        manager = LLMProviderManager()
        
        providers = manager.list_providers()
        assert isinstance(providers, list)
        assert len(providers) == 0  # 初始時沒有註冊的提供商
    
    def test_register_provider(self):
        """測試手動註冊提供商"""
        manager = LLMProviderManager()
        
        config = ProviderConfig(name="test", port=8080)
        provider = OllamaProvider(config)
        
        manager.register_provider(provider, set_as_default=True)
        
        assert "ollama" in manager.list_providers()
        assert manager.get_selected_provider_name() == "ollama"
    
    def test_select_provider(self):
        """測試選擇提供商"""
        manager = LLMProviderManager()
        
        # 註冊兩個提供商
        config1 = ProviderConfig(name="ollama", port=11434)
        provider1 = OllamaProvider(config1)
        manager.register_provider(provider1)
        
        config2 = ProviderConfig(name="lmstudio", port=1234)
        provider2 = LMStudioProvider(config2)
        manager.register_provider(provider2)
        
        # 選擇提供商
        success = manager.select_provider("lmstudio")
        assert success is True
        assert manager.get_selected_provider_name() == "lmstudio"
        
        # 選擇不存在的提供商
        success = manager.select_provider("nonexistent")
        assert success is False
    
    def test_get_provider(self):
        """測試取得提供商實例"""
        manager = LLMProviderManager()
        
        config = ProviderConfig(name="ollama", port=11434)
        provider = OllamaProvider(config)
        manager.register_provider(provider, set_as_default=True)
        
        # 取得預設提供商
        retrieved = manager.get_provider()
        assert retrieved is not None
        assert retrieved.provider_name == "ollama"
        
        # 取得指定提供商
        retrieved = manager.get_provider("ollama")
        assert retrieved is not None
        assert retrieved.provider_name == "ollama"
        
        # 取得不存在的提供商
        retrieved = manager.get_provider("nonexistent")
        assert retrieved is None
    
    @pytest.mark.asyncio
    async def test_discover_providers(self):
        """測試自動偵測提供商"""
        manager = LLMProviderManager()
        
        # 執行偵測（實際服務可能不在運行）
        health_results = await manager.discover_providers(timeout=1)
        
        # 應該至少嘗試掃描預設的提供商
        assert isinstance(health_results, dict)
        assert len(health_results) >= 2  # Ollama 和 LM Studio
        
        # 檢查返回的健康狀態物件
        for name, health in health_results.items():
            assert isinstance(health, ProviderHealth)
            assert health.status in [
                ProviderStatus.AVAILABLE,
                ProviderStatus.UNAVAILABLE,
                ProviderStatus.ERROR
            ]
    
    @pytest.mark.asyncio
    async def test_get_all_provider_health(self):
        """測試取得所有提供商健康狀態"""
        manager = LLMProviderManager()
        
        # 註冊提供商
        config = ProviderConfig(name="ollama", port=11434, timeout=1)
        provider = OllamaProvider(config)
        manager.register_provider(provider)
        
        # 取得健康狀態
        health_results = await manager.get_all_provider_health()
        
        assert isinstance(health_results, dict)
        assert "ollama" in health_results
        assert isinstance(health_results["ollama"], ProviderHealth)


class TestLLMProcessorIntegration:
    """測試 LLM 處理器與提供商整合"""
    
    @pytest.mark.asyncio
    async def test_llm_processor_with_manager(self):
        """測試 LLM 處理器使用提供商管理器"""
        from MCP.llm_processor import LLMProcessor
        
        manager = LLMProviderManager()
        processor = LLMProcessor(provider_manager=manager)
        
        assert processor.provider_manager is manager
    
    @pytest.mark.asyncio
    async def test_parse_command_without_provider(self):
        """測試在沒有可用提供商時的指令解析（回退到規則式）"""
        from MCP.llm_processor import LLMProcessor
        
        manager = LLMProviderManager()
        processor = LLMProcessor(provider_manager=manager)
        
        # 解析簡單指令
        command = await processor.parse_command(
            transcription="向前移動三秒",
            robot_id="robot-001"
        )
        
        assert command is not None
        assert command.type == "robot.action"
        assert command.target.robot_id == "robot-001"
        assert command.params["action_name"] == "go_forward"
        assert command.params["duration_ms"] == 3000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
