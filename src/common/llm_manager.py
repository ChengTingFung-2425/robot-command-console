"""
Unified LLM Manager

This module consolidates shared functionality between MCP and llm_discovery.
"""

import logging
from typing import Dict, List, Optional, Type
from pathlib import Path
import platform

# Shared models
from Edge.llm_discovery.models import ProviderManifest, ProviderHealth, Skill
from Edge.MCP.llm_provider_base import LLMProviderBase

logger = logging.getLogger(__name__)

class LLMManager:
    """
    Unified LLM Manager for handling provider discovery, health checks, and skill management.
    """

    DEFAULT_PROVIDERS: List[Type[LLMProviderBase]] = []

    def __init__(self):
        self.providers: Dict[str, ProviderManifest] = {}
        self.health_cache: Dict[str, ProviderHealth] = {}

    @staticmethod
    def get_registry_path() -> Path:
        """
        Get the standardized registry path based on the current platform.
        """
        system = platform.system()
        if system == "Linux":
            base_path = Path.home() / ".local" / "share"
        elif system == "Darwin":
            base_path = Path.home() / "Library" / "Application Support"
        elif system == "Windows":
            base_path = Path(os.getenv("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        else:
            base_path = Path.home() / ".local" / "share"

        registry_path = base_path / "llm-providers"
        registry_path.mkdir(parents=True, exist_ok=True)
        return registry_path

    def register_provider(self, provider: ProviderManifest):
        """
        Register a new LLM provider.
        """
        self.providers[provider.name] = provider
        logger.info(f"Registered provider: {provider.name}")

    def check_health(self, provider_name: str) -> Optional[ProviderHealth]:
        """
        Perform a health check for a specific provider.
        """
        provider = self.providers.get(provider_name)
        if not provider:
            logger.warning(f"Provider {provider_name} not found.")
            return None

        # Simulate health check logic
        health = ProviderHealth(status="healthy", details={})
        self.health_cache[provider_name] = health
        return health

    def discover_providers(self) -> List[ProviderManifest]:
        """
        Discover and return all registered providers.
        """
        registry_path = self.get_registry_path()
        # Simulate discovery logic
        logger.info(f"Scanning registry path: {registry_path}")
        return list(self.providers.values())

    def list_skills(self, provider_name: str) -> Optional[List[Skill]]:
        """
        List all skills for a specific provider.
        """
        provider = self.providers.get(provider_name)
        if not provider:
            logger.warning(f"Provider {provider_name} not found.")
            return None

        # Simulate skill listing logic
        return provider.skills