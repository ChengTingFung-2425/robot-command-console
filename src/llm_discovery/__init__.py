"""
LLM Compatible Software (llm-cop) Discovery Module

用於 Edge 環境中發現和註冊 LLM Compatible Software 及其 skills。
包含防止模型解密攻擊的安全機制。
提供 LLM IPC Bridge 連接 LLM 和專案。
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
from .bridge import LLMIPCBridge
from .mcp_adapter import MCPAdapter, MCPErrorCode
from .skill_translator import SkillTranslator

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
    "LLMIPCBridge",
    "MCPAdapter",
    "MCPErrorCode",
    "SkillTranslator",
]

__version__ = "1.0.0"
