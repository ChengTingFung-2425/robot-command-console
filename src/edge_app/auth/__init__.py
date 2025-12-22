"""
Edge App Authentication Module

This module provides authentication and token management for the Edge application.
Supports Linux and Windows platforms with OS-native keychain integration.
"""

from .token_cache import EdgeTokenCache

__all__ = ['EdgeTokenCache']
