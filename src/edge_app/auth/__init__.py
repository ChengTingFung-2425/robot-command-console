"""
Edge App Authentication Module

This module provides authentication and token management for the Edge application.
Supports Linux and Windows platforms with OS-native keychain integration.
"""

from .device_id import DeviceIDGenerator  # noqa: F401

__all__ = ['DeviceIDGenerator']
