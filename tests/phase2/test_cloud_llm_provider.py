"""
雲端 LLM 提供商與混合路由策略測試

驗證：
- CloudLLMProvider（通用 OpenAI 相容）
- AzureOpenAIProvider（Azure OpenAI Service）
- GCPGeminiProvider（Google Cloud Gemini API）
- AWSBedrockProvider（Amazon Bedrock）
- LLMProviderManager RoutingMode 與備援邏輯
"""

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from Edge.MCP.llm_provider_base import (  # noqa: E402
    ProviderConfig,
    ProviderHealth,
    ProviderStatus,
)
from Edge.MCP.llm_provider_manager import (  # noqa: E402
    LLMProviderManager,
    RoutingMode,
)
from Edge.MCP.providers import (  # noqa: E402
    AWSBedrockProvider,
    AzureOpenAIProvider,
    CloudLLMProvider,
    GCPGeminiProvider,
    OllamaProvider,
)


# ------------------------------------------------------------------ #
#  共用輔助函數                                                         #
# ------------------------------------------------------------------ #

def _make_cloud_config(**overrides) -> ProviderConfig:
    """建立雲端提供商設定（通用 OpenAI 相容）"""
    defaults = dict(
        name="cloud",
        host="api.openai.com",
        port=443,
        api_key="sk-test-key",
        api_base="https://api.openai.com",
        timeout=5,
    )
    defaults.update(overrides)
    return ProviderConfig(**defaults)


def _make_azure_config(**overrides) -> ProviderConfig:
    """建立 Azure OpenAI 提供商設定"""
    defaults = dict(
        name="azure_openai",
        host="my-resource.openai.azure.com",
        port=443,
        api_key="azure-key-test",
        api_base="https://my-resource.openai.azure.com",
        timeout=5,
        custom_headers={"deployment": "gpt-4o-mini", "api_version": "2024-02-01"},
    )
    defaults.update(overrides)
    return ProviderConfig(**defaults)


def _make_gcp_config(**overrides) -> ProviderConfig:
    """建立 GCP Gemini 提供商設定"""
    defaults = dict(
        name="gcp_gemini",
        host="generativelanguage.googleapis.com",
        port=443,
        api_key="gcp-key-test",
        timeout=5,
    )
    defaults.update(overrides)
    return ProviderConfig(**defaults)


def _make_aws_config(**overrides) -> ProviderConfig:
    """建立 AWS Bedrock 提供商設定"""
    defaults = dict(
        name="aws_bedrock",
        host="bedrock-runtime.us-east-1.amazonaws.com",
        port=443,
        timeout=5,
        custom_headers={
            "region": "us-east-1",
            "model_id": "anthropic.claude-3-haiku-20240307-v1:0",
            "aws_access_key_id": "AKIATEST",
            "aws_secret_access_key": "secret-test",
        },
    )
    defaults.update(overrides)
    return ProviderConfig(**defaults)


# ------------------------------------------------------------------ #
#  CloudLLMProvider 測試                                               #
# ------------------------------------------------------------------ #

class TestCloudLLMProvider:
    """測試通用雲端 LLM 提供商（OpenAI 相容）"""

    def test_provider_name(self):
        """提供商名稱應為 'cloud'"""
        provider = CloudLLMProvider(_make_cloud_config())
        assert provider.provider_name == "cloud"

    def test_default_port(self):
        """預設埠號應為 443"""
        provider = CloudLLMProvider(_make_cloud_config())
        assert provider.default_port == 443

    def test_set_default_model(self):
        """可以設定預設模型"""
        provider = CloudLLMProvider(_make_cloud_config())
        provider.set_default_model("gpt-4o-mini")
        assert provider._default_model == "gpt-4o-mini"

    @pytest.mark.asyncio
    async def test_check_health_no_api_key(self):
        """未設定 API 金鑰應回傳 UNAVAILABLE"""
        config = ProviderConfig(
            name="cloud", host="api.openai.com", port=443, timeout=1
        )
        provider = CloudLLMProvider(config)
        health = await provider.check_health()
        assert health.status == ProviderStatus.UNAVAILABLE
        assert "API 金鑰" in health.error_message

    @pytest.mark.asyncio
    async def test_check_health_connection_error(self):
        """連線失敗應回傳 UNAVAILABLE"""
        provider = CloudLLMProvider(_make_cloud_config(timeout=1))
        # api.openai.com 不會在測試環境可達，結果為 UNAVAILABLE 或 ERROR
        health = await provider.check_health()
        assert health.status in (ProviderStatus.UNAVAILABLE, ProviderStatus.ERROR)

    @pytest.mark.asyncio
    async def test_check_health_available(self):
        """模擬 200 回應，應回傳 AVAILABLE"""
        provider = CloudLLMProvider(_make_cloud_config())

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={"data": [{"id": "gpt-4o-mini"}, {"id": "gpt-4o"}]}
        )
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            health = await provider.check_health()

        assert health.status == ProviderStatus.AVAILABLE
        assert "gpt-4o-mini" in health.available_models

    @pytest.mark.asyncio
    async def test_generate_without_model_raises(self):
        """未設定模型且未指定 model 參數應拋出例外"""
        provider = CloudLLMProvider(_make_cloud_config())
        with pytest.raises(ValueError, match="未指定模型名稱"):
            await provider.generate(prompt="Hello", model="")

    @pytest.mark.asyncio
    async def test_generate_success(self):
        """模擬成功生成文字"""
        provider = CloudLLMProvider(_make_cloud_config())

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(return_value={
            "choices": [{
                "message": {"content": "向前移動"},
                "finish_reason": "stop",
            }]
        })
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            text, confidence = await provider.generate(
                prompt="請向前移動", model="gpt-4o-mini"
            )

        assert text == "向前移動"
        assert confidence == 0.92

    @pytest.mark.asyncio
    async def test_list_models_no_api_key(self):
        """未設定 API 金鑰應回傳空列表"""
        config = _make_cloud_config(api_key=None)
        provider = CloudLLMProvider(config)
        models = await provider.list_models()
        assert models == []


# ------------------------------------------------------------------ #
#  AzureOpenAIProvider 測試                                            #
# ------------------------------------------------------------------ #

class TestAzureOpenAIProvider:
    """測試 Azure OpenAI Service 提供商"""

    def test_provider_name(self):
        provider = AzureOpenAIProvider(_make_azure_config())
        assert provider.provider_name == "azure_openai"

    def test_default_port(self):
        provider = AzureOpenAIProvider(_make_azure_config())
        assert provider.default_port == 443

    def test_deployment_from_custom_headers(self):
        """部署名稱應從 custom_headers 讀取"""
        provider = AzureOpenAIProvider(_make_azure_config())
        assert provider._deployment == "gpt-4o-mini"

    def test_api_version_from_custom_headers(self):
        """API 版本應從 custom_headers 讀取"""
        provider = AzureOpenAIProvider(_make_azure_config())
        assert provider._api_version == "2024-02-01"

    def test_chat_url_format(self):
        """Chat URL 格式應符合 Azure 規範"""
        provider = AzureOpenAIProvider(_make_azure_config())
        url = provider._get_chat_url()
        assert "openai/deployments/gpt-4o-mini/chat/completions" in url
        assert "api-version=2024-02-01" in url

    @pytest.mark.asyncio
    async def test_check_health_no_config(self):
        """未設定資源 URL 或 API 金鑰應回傳 UNAVAILABLE"""
        config = _make_azure_config(api_key=None, api_base=None)
        provider = AzureOpenAIProvider(config)
        health = await provider.check_health()
        assert health.status == ProviderStatus.UNAVAILABLE

    @pytest.mark.asyncio
    async def test_check_health_available(self):
        """模擬 200 回應，應回傳 AVAILABLE"""
        provider = AzureOpenAIProvider(_make_azure_config())

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={"data": [{"id": "gpt-4o-mini"}]}
        )
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            health = await provider.check_health()

        assert health.status == ProviderStatus.AVAILABLE

    @pytest.mark.asyncio
    async def test_check_health_auth_error(self):
        """API 金鑰無效（401）應回傳 ERROR"""
        provider = AzureOpenAIProvider(_make_azure_config())

        mock_response = MagicMock()
        mock_response.status = 401
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            health = await provider.check_health()

        assert health.status == ProviderStatus.ERROR
        assert "金鑰" in health.error_message

    @pytest.mark.asyncio
    async def test_generate_success(self):
        """模擬成功生成文字"""
        provider = AzureOpenAIProvider(_make_azure_config())

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(return_value={
            "choices": [{
                "message": {"content": "已收到指令"},
                "finish_reason": "stop",
            }]
        })
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            text, confidence = await provider.generate(
                prompt="向左轉", model="gpt-4o-mini"
            )

        assert text == "已收到指令"
        assert confidence == 0.92


# ------------------------------------------------------------------ #
#  GCPGeminiProvider 測試                                              #
# ------------------------------------------------------------------ #

class TestGCPGeminiProvider:
    """測試 GCP Gemini API 提供商"""

    def test_provider_name(self):
        provider = GCPGeminiProvider(_make_gcp_config())
        assert provider.provider_name == "gcp_gemini"

    def test_default_port(self):
        provider = GCPGeminiProvider(_make_gcp_config())
        assert provider.default_port == 443

    def test_generate_url_format(self):
        """生成 URL 應包含模型名稱與 API 金鑰"""
        provider = GCPGeminiProvider(_make_gcp_config())
        url = provider._generate_url("gemini-1.5-flash")
        assert "gemini-1.5-flash" in url
        assert "gcp-key-test" in url
        assert "generateContent" in url

    @pytest.mark.asyncio
    async def test_check_health_no_api_key(self):
        """未設定 API 金鑰應回傳 UNAVAILABLE"""
        config = _make_gcp_config(api_key=None)
        provider = GCPGeminiProvider(config)
        health = await provider.check_health()
        assert health.status == ProviderStatus.UNAVAILABLE

    @pytest.mark.asyncio
    async def test_check_health_available(self):
        """模擬 200 回應，應回傳 AVAILABLE"""
        provider = GCPGeminiProvider(_make_gcp_config())

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "models": [
                {
                    "name": "models/gemini-1.5-flash",
                    "supportedGenerationMethods": ["generateContent"],
                }
            ]
        })
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            health = await provider.check_health()

        assert health.status == ProviderStatus.AVAILABLE
        assert "gemini-1.5-flash" in health.available_models

    @pytest.mark.asyncio
    async def test_generate_success(self):
        """模擬 Gemini 成功生成文字"""
        provider = GCPGeminiProvider(_make_gcp_config())

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(return_value={
            "candidates": [{
                "content": {
                    "parts": [{"text": "機器人已收到指令"}]
                },
                "finishReason": "STOP",
            }]
        })
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("aiohttp.ClientSession", return_value=mock_session):
            text, confidence = await provider.generate(
                prompt="向右轉", model="gemini-1.5-flash"
            )

        assert text == "機器人已收到指令"
        assert confidence == 0.92


# ------------------------------------------------------------------ #
#  AWSBedrockProvider 測試                                             #
# ------------------------------------------------------------------ #

class TestAWSBedrockProvider:
    """測試 Amazon Bedrock 提供商"""

    def test_provider_name(self):
        provider = AWSBedrockProvider(_make_aws_config())
        assert provider.provider_name == "aws_bedrock"

    def test_default_port(self):
        provider = AWSBedrockProvider(_make_aws_config())
        assert provider.default_port == 443

    def test_region_from_custom_headers(self):
        """AWS 區域應從 custom_headers 讀取"""
        provider = AWSBedrockProvider(_make_aws_config())
        assert provider._region == "us-east-1"

    def test_model_id_from_custom_headers(self):
        """模型 ID 應從 custom_headers 讀取"""
        provider = AWSBedrockProvider(_make_aws_config())
        assert "claude" in provider._model_id

    def test_build_request_body_anthropic(self):
        """Anthropic Claude 請求 body 應包含 anthropic_version"""
        provider = AWSBedrockProvider(_make_aws_config())
        body = provider._build_request_body(
            model_id="anthropic.claude-3-haiku-20240307-v1:0",
            prompt="Hello",
            temperature=0.5,
            max_tokens=512,
            system="You are a robot assistant.",
        )
        assert body["anthropic_version"] == "bedrock-2023-05-31"
        assert body["system"] == "You are a robot assistant."
        assert body["max_tokens"] == 512

    def test_build_request_body_titan(self):
        """Amazon Titan 請求 body 應包含 inputText"""
        provider = AWSBedrockProvider(_make_aws_config())
        body = provider._build_request_body(
            model_id="amazon.titan-text-lite-v1",
            prompt="Hello",
            temperature=0.5,
            max_tokens=512,
            system=None,
        )
        assert "inputText" in body
        assert "textGenerationConfig" in body

    def test_parse_response_anthropic(self):
        """解析 Anthropic Claude 回應格式"""
        provider = AWSBedrockProvider(_make_aws_config())
        response = {
            "content": [{"type": "text", "text": "機器人已向前移動"}],
            "stop_reason": "end_turn",
        }
        text, confidence = provider._parse_response(
            "anthropic.claude-3-haiku-20240307-v1:0", response
        )
        assert text == "機器人已向前移動"
        assert confidence == 0.92

    def test_parse_response_titan(self):
        """解析 Amazon Titan 回應格式"""
        provider = AWSBedrockProvider(_make_aws_config())
        response = {
            "results": [{"outputText": "Titan 回應", "completionReason": "FINISH"}]
        }
        text, confidence = provider._parse_response(
            "amazon.titan-text-lite-v1", response
        )
        assert text == "Titan 回應"
        assert confidence == 0.90

    @pytest.mark.asyncio
    async def test_check_health_no_aioboto3(self):
        """未安裝 aioboto3 應回傳 ERROR"""
        provider = AWSBedrockProvider(_make_aws_config())
        with patch.dict("sys.modules", {"aioboto3": None}):
            health = await provider.check_health()
        assert health.status == ProviderStatus.ERROR

    @pytest.mark.asyncio
    async def test_check_health_available(self):
        """模擬 aioboto3 正常回應，應回傳 AVAILABLE"""
        provider = AWSBedrockProvider(_make_aws_config())

        mock_client = AsyncMock()
        mock_client.list_foundation_models = AsyncMock(return_value={
            "modelSummaries": [
                {"modelId": "anthropic.claude-3-haiku-20240307-v1:0"},
                {"modelId": "amazon.titan-text-lite-v1"},
            ]
        })
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.client.return_value = mock_client

        mock_aioboto3 = MagicMock()
        mock_aioboto3.Session.return_value = mock_session

        with patch.dict("sys.modules", {"aioboto3": mock_aioboto3}):
            health = await provider.check_health()

        assert health.status == ProviderStatus.AVAILABLE
        assert len(health.available_models) >= 2


# ------------------------------------------------------------------ #
#  RoutingMode 與 LLMProviderManager 路由測試                          #
# ------------------------------------------------------------------ #

class TestRoutingMode:
    """測試 RoutingMode 列舉"""

    def test_routing_mode_values(self):
        assert RoutingMode.CLOUD_FIRST.value == "cloud_first"
        assert RoutingMode.LOCAL_FIRST.value == "local_first"
        assert RoutingMode.CLOUD_ONLY.value == "cloud_only"
        assert RoutingMode.LOCAL_ONLY.value == "local_only"


class TestLLMProviderManagerRouting:
    """測試 LLMProviderManager 路由策略"""

    def _register_providers(self, manager: LLMProviderManager):
        """向管理器註冊本地與雲端各一個提供商"""
        local_config = ProviderConfig(name="ollama", port=11434, timeout=1)
        cloud_config = _make_cloud_config()

        local_provider = OllamaProvider(local_config)
        cloud_provider = CloudLLMProvider(cloud_config)

        manager.register_provider(local_provider)
        manager.register_provider(cloud_provider)
        return local_provider, cloud_provider

    def test_default_routing_mode_is_local_first(self):
        """預設路由模式應為 LOCAL_FIRST"""
        manager = LLMProviderManager()
        assert manager.routing_mode == RoutingMode.LOCAL_FIRST

    def test_set_routing_mode(self):
        """可以設定路由模式"""
        manager = LLMProviderManager()
        manager.set_routing_mode(RoutingMode.CLOUD_FIRST)
        assert manager.get_routing_mode() == RoutingMode.CLOUD_FIRST

    def test_is_cloud_provider(self):
        """is_cloud_provider 應正確識別雲端提供商"""
        manager = LLMProviderManager()
        assert manager.is_cloud_provider("cloud") is True
        assert manager.is_cloud_provider("azure_openai") is True
        assert manager.is_cloud_provider("gcp_gemini") is True
        assert manager.is_cloud_provider("aws_bedrock") is True
        assert manager.is_cloud_provider("ollama") is False
        assert manager.is_cloud_provider("lmstudio") is False

    def test_list_cloud_and_local_providers(self):
        """list_cloud_providers / list_local_providers 應正確分類"""
        manager = LLMProviderManager()
        self._register_providers(manager)

        cloud = manager.list_cloud_providers()
        local = manager.list_local_providers()

        assert "cloud" in cloud
        assert "ollama" in local
        assert "cloud" not in local
        assert "ollama" not in cloud

    def test_get_provider_local_first(self):
        """LOCAL_FIRST 模式應優先返回本地提供商"""
        manager = LLMProviderManager(routing_mode=RoutingMode.LOCAL_FIRST)
        self._register_providers(manager)

        provider = manager.get_provider_with_routing()
        assert provider is not None
        assert not manager.is_cloud_provider(provider.provider_name)

    def test_get_provider_cloud_first(self):
        """CLOUD_FIRST 模式應優先返回雲端提供商"""
        manager = LLMProviderManager(routing_mode=RoutingMode.CLOUD_FIRST)
        self._register_providers(manager)

        provider = manager.get_provider_with_routing()
        assert provider is not None
        assert manager.is_cloud_provider(provider.provider_name)

    def test_get_provider_cloud_only_no_cloud(self):
        """CLOUD_ONLY 且無雲端提供商時應回傳 None"""
        manager = LLMProviderManager(routing_mode=RoutingMode.CLOUD_ONLY)
        # 僅註冊本地提供商
        local_config = ProviderConfig(name="ollama", port=11434, timeout=1)
        manager.register_provider(OllamaProvider(local_config))

        provider = manager.get_provider_with_routing()
        assert provider is None

    def test_get_provider_local_only_no_local(self):
        """LOCAL_ONLY 且無本地提供商時應回傳 None"""
        manager = LLMProviderManager(routing_mode=RoutingMode.LOCAL_ONLY)
        # 僅註冊雲端提供商
        manager.register_provider(CloudLLMProvider(_make_cloud_config()))

        provider = manager.get_provider_with_routing()
        assert provider is None

    @pytest.mark.asyncio
    async def test_get_provider_with_routing_and_health_cloud_first_fallback(self):
        """CLOUD_FIRST 雲端不可用時應備援到本地"""
        manager = LLMProviderManager(routing_mode=RoutingMode.CLOUD_FIRST)

        # 雲端提供商：模擬不可用
        cloud_config = _make_cloud_config(api_key="invalid-key")
        cloud_provider = CloudLLMProvider(cloud_config)
        cloud_provider.check_health = AsyncMock(
            return_value=ProviderHealth(status=ProviderStatus.UNAVAILABLE)
        )

        # 本地提供商：模擬可用
        local_config = ProviderConfig(name="ollama", port=11434, timeout=1)
        local_provider = OllamaProvider(local_config)
        local_provider.check_health = AsyncMock(
            return_value=ProviderHealth(
                status=ProviderStatus.AVAILABLE,
                available_models=["llama2"],
            )
        )

        manager.register_provider(cloud_provider)
        manager.register_provider(local_provider)

        selected = await manager.get_provider_with_routing_and_health()
        assert selected is not None
        assert selected.provider_name == "ollama"

    @pytest.mark.asyncio
    async def test_get_provider_with_routing_and_health_all_unavailable(self):
        """所有提供商不可用時應回傳 None"""
        manager = LLMProviderManager(routing_mode=RoutingMode.CLOUD_FIRST)

        for config_fn in [_make_cloud_config, _make_azure_config]:
            provider_cls = CloudLLMProvider if config_fn == _make_cloud_config else AzureOpenAIProvider
            provider = provider_cls(config_fn())
            provider.check_health = AsyncMock(
                return_value=ProviderHealth(status=ProviderStatus.UNAVAILABLE)
            )
            manager.register_provider(provider)

        selected = await manager.get_provider_with_routing_and_health()
        assert selected is None

    @pytest.mark.asyncio
    async def test_generate_with_routing_success(self):
        """generate_with_routing 應成功呼叫可用提供商並回傳結果"""
        manager = LLMProviderManager(routing_mode=RoutingMode.CLOUD_FIRST)

        cloud_provider = CloudLLMProvider(_make_cloud_config())
        cloud_provider.check_health = AsyncMock(
            return_value=ProviderHealth(
                status=ProviderStatus.AVAILABLE,
                available_models=["gpt-4o-mini"],
            )
        )
        cloud_provider.list_models = AsyncMock(return_value=[
            MagicMock(id="gpt-4o-mini")
        ])
        cloud_provider.generate = AsyncMock(return_value=("向前移動完成", 0.92))

        manager.register_provider(cloud_provider)

        text, provider_name, confidence = await manager.generate_with_routing(
            prompt="請向前移動"
        )

        assert text == "向前移動完成"
        assert provider_name == "cloud"
        assert confidence == 0.92

    @pytest.mark.asyncio
    async def test_generate_with_routing_no_provider(self):
        """無可用提供商時 generate_with_routing 應回傳 (None, None, 0.0)"""
        manager = LLMProviderManager(routing_mode=RoutingMode.LOCAL_ONLY)
        # 未註冊任何提供商

        text, provider_name, confidence = await manager.generate_with_routing(
            prompt="Hello"
        )

        assert text is None
        assert provider_name is None
        assert confidence == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
