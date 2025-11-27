"""
LLM 提供商基底類別與插件介面
定義本地 LLM 提供商的標準 API 契約
"""

import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ProviderStatus(str, Enum):
    """提供商狀態"""
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    ERROR = "error"
    UNKNOWN = "unknown"


class ModelCapability(BaseModel):
    """模型能力描述"""
    supports_streaming: bool = False
    supports_vision: bool = False
    supports_function_calling: bool = False
    context_length: int = 2048
    max_tokens: int = 2048


class LLMModel(BaseModel):
    """LLM 模型資訊"""
    id: str = Field(..., description="模型唯一識別碼")
    name: str = Field(..., description="模型顯示名稱")
    size: Optional[str] = Field(None, description="模型大小（如 7B, 13B）")
    capabilities: ModelCapability = Field(default_factory=ModelCapability)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ProviderConfig(BaseModel):
    """提供商配置"""
    name: str = Field(..., description="提供商名稱")
    host: str = Field(default="localhost", description="主機位址")
    port: int = Field(..., description="服務埠號")
    api_base: Optional[str] = Field(None, description="API 基礎路徑")
    timeout: int = Field(default=30, description="請求逾時（秒）")
    api_key: Optional[str] = Field(None, description="API 金鑰（如需要）")
    custom_headers: Dict[str, str] = Field(default_factory=dict)


class ProviderHealth(BaseModel):
    """提供商健康狀態"""
    status: ProviderStatus
    version: Optional[str] = None
    available_models: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None
    response_time_ms: Optional[float] = None


class LLMProviderBase(ABC):
    """
    LLM 提供商基底抽象類別
    所有本地 LLM 提供商插件必須繼承此類別
    """

    def __init__(self, config: ProviderConfig):
        """
        初始化提供商
        
        Args:
            config: 提供商配置
        """
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """
        提供商名稱
        
        Returns:
            提供商唯一識別名稱
        """
        pass

    @property
    @abstractmethod
    def default_port(self) -> int:
        """
        預設服務埠號
        
        Returns:
            預設埠號
        """
        pass

    @abstractmethod
    async def check_health(self) -> ProviderHealth:
        """
        檢查提供商健康狀態
        
        Returns:
            健康狀態資訊
        """
        pass

    @abstractmethod
    async def list_models(self) -> List[LLMModel]:
        """
        列出可用的模型
        
        Returns:
            可用模型列表
        """
        pass

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Tuple[str, float]:
        """
        生成文字
        
        Args:
            prompt: 輸入提示
            model: 使用的模型 ID
            temperature: 溫度參數
            max_tokens: 最大生成 token 數
            **kwargs: 其他提供商特定參數
            
        Returns:
            (生成的文字, 信心度) 元組
        """
        pass

    async def transcribe_audio(
        self,
        audio_bytes: bytes,
        audio_format: str = "opus",
        language: str = "zh-TW"
    ) -> Tuple[str, float]:
        """
        將音訊轉換為文字（選用功能）
        
        Args:
            audio_bytes: 音訊資料
            audio_format: 音訊格式
            language: 語言代碼
            
        Returns:
            (轉錄文字, 信心度) 元組
            
        Raises:
            NotImplementedError: 如果提供商不支援語音辨識
        """
        raise NotImplementedError(
            f"{self.provider_name} 不支援語音轉文字功能"
        )

    def get_api_endpoint(self, path: str = "") -> str:
        """
        取得完整 API 端點 URL
        
        Args:
            path: API 路徑
            
        Returns:
            完整 URL
        """
        base = self.config.api_base or f"http://{self.config.host}:{self.config.port}"
        return f"{base.rstrip('/')}/{path.lstrip('/')}" if path else base

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}({self.provider_name}@{self.config.host}:{self.config.port})>"
