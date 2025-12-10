"""
LLM Copilot Discovery Module

用於 Edge 環境中發現和註冊 LLM Copilot 實例及其技能。
包含防止模型解密攻擊的安全機制。
"""

from .models import (
    ProviderManifest,
    Endpoint,
    ProviderHealth,
    Skill,
    AntiDecryptionConfig,
)
from .scanner import FilesystemScanner
from .probe import EndpointProbe
from .discovery_service import DiscoveryService
from .security import PromptSanitizer, ResponseFilter

__all__ = [
    "ProviderManifest",
    "Endpoint",
    "ProviderHealth",
    "Skill",
    "AntiDecryptionConfig",
    "FilesystemScanner",
    "EndpointProbe",
    "DiscoveryService",
    "PromptSanitizer",
    "ResponseFilter",
]

__version__ = "1.0.0"
