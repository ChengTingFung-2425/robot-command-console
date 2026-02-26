"""
Edge Device Binding Client

This module provides functionality to bind Edge devices to cloud user accounts.
It integrates with DeviceIDGenerator and communicates with the cloud authentication API.
"""

import platform
import socket
import requests
from typing import Optional, Dict

from src.edge_app.auth.device_id import DeviceIDGenerator


class DeviceBindingClient:
    """
    Client for binding Edge devices to cloud user accounts.

    Handles device registration, verification, and management through the cloud API.
    """

    def __init__(self, cloud_api_url: str = "http://localhost:5000"):
        """
        Initialize DeviceBindingClient.

        Args:
            cloud_api_url: Base URL of the cloud API server
        """
        self.cloud_api_url = cloud_api_url.rstrip('/')
        self.device_id_generator = DeviceIDGenerator()

    def get_device_id(self) -> str:
        """
        Get or generate device ID.

        Returns:
            str: 64-character hexadecimal device ID
        """
        return self.device_id_generator.get_or_create()

    def get_device_metadata(self) -> Dict[str, str]:
        """
        Collect device metadata for registration.

        Returns:
            dict: Device metadata including platform, hostname, etc.
        """
        metadata = {
            'platform': platform.system(),
            'hostname': socket.gethostname(),
            'device_type': self._detect_device_type(),
        }
        return metadata

    def _detect_device_type(self) -> str:
        """
        Detect device type based on platform and characteristics.

        Returns:
            str: Device type (desktop/laptop/edge_device)
        """
        system = platform.system()

        # Simple heuristics for device type detection
        if system in ['Linux', 'Windows', 'Darwin']:
            # Check if it's a likely embedded/edge device
            machine = platform.machine().lower()
            if any(arch in machine for arch in ['arm', 'aarch', 'riscv']):
                return 'edge_device'
            return 'desktop'  # Default for x86/x64

        return 'unknown'

    def register_device(self, access_token: str, device_name: Optional[str] = None) -> Dict:
        """
        Register and bind device to user account.

        Args:
            access_token: JWT access token for authentication
            device_name: Optional custom name for the device

        Returns:
            dict: Registration response from API

        Raises:
            requests.RequestException: If API request fails
        """
        device_id = self.get_device_id()
        metadata = self.get_device_metadata()

        # Prepare registration payload
        payload = {
            'device_id': device_id,
            'device_type': metadata['device_type'],
            'platform': metadata['platform'],
            'hostname': metadata['hostname'],
        }

        if device_name:
            payload['device_name'] = device_name

        # Make API request
        url = f"{self.cloud_api_url}/api/auth/device/register"
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }

        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()

        return response.json()

    def list_devices(self, access_token: str, active_only: bool = False) -> Dict:
        """
        List all devices bound to the user account.

        Args:
            access_token: JWT access token for authentication
            active_only: Only return active devices

        Returns:
            dict: API response with devices list

        Raises:
            requests.RequestException: If API request fails
        """
        url = f"{self.cloud_api_url}/api/auth/devices"
        headers = {'Authorization': f'Bearer {access_token}'}
        params = {'active_only': str(active_only).lower()}

        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()

        return response.json()

    def get_device(self, access_token: str, device_id: int) -> Dict:
        """
        Get details of a specific device.

        Args:
            access_token: JWT access token for authentication
            device_id: Device database ID (not device_id hash)

        Returns:
            dict: Device details

        Raises:
            requests.RequestException: If API request fails
        """
        url = f"{self.cloud_api_url}/api/auth/device/{device_id}"
        headers = {'Authorization': f'Bearer {access_token}'}

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        return response.json()

    def update_device(self, access_token: str, device_id: int,
                      device_name: Optional[str] = None,
                      is_trusted: Optional[bool] = None) -> Dict:
        """
        Update device information.

        Args:
            access_token: JWT access token for authentication
            device_id: Device database ID
            device_name: New device name (optional)
            is_trusted: Mark device as trusted (optional)

        Returns:
            dict: Updated device information

        Raises:
            requests.RequestException: If API request fails
        """
        url = f"{self.cloud_api_url}/api/auth/device/{device_id}"
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }

        payload = {}
        if device_name is not None:
            payload['device_name'] = device_name
        if is_trusted is not None:
            payload['is_trusted'] = is_trusted

        response = requests.put(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()

        return response.json()

    def unbind_device(self, access_token: str, device_id: int) -> Dict:
        """
        Unbind (deactivate) a device.

        Args:
            access_token: JWT access token for authentication
            device_id: Device database ID

        Returns:
            dict: API response

        Raises:
            requests.RequestException: If API request fails
        """
        url = f"{self.cloud_api_url}/api/auth/device/{device_id}/unbind"
        headers = {'Authorization': f'Bearer {access_token}'}

        response = requests.post(url, headers=headers, timeout=10)
        response.raise_for_status()

        return response.json()

    def verify_device_bound(self, access_token: str) -> bool:
        """
        Check if current device is bound to the authenticated user.

        Args:
            access_token: JWT access token for authentication

        Returns:
            bool: True if device is bound and active

        Raises:
            requests.RequestException: If API request fails
        """
        current_device_id = self.get_device_id()

        # List all active devices
        response = self.list_devices(access_token, active_only=True)
        devices = response.get('devices', [])

        # Check if current device_id exists in the list
        for device in devices:
            if device.get('device_id') == current_device_id:
                return True

        return False

    def auto_register_if_needed(self, access_token: str,
                                device_name: Optional[str] = None) -> Dict:
        """
        Automatically register device if not already bound.

        Args:
            access_token: JWT access token for authentication
            device_name: Optional custom name for the device

        Returns:
            dict: Registration result or existing device info
        """
        try:
            # Check if already bound
            if self.verify_device_bound(access_token):
                current_device_id = self.get_device_id()
                return {
                    'success': True,
                    'already_bound': True,
                    'device_id': current_device_id,
                    'message': 'Device already bound'
                }
        except requests.RequestException:
            # If verification fails, try to register
            pass

        # Register device
        result = self.register_device(access_token, device_name)
        result.setdefault('already_bound', False)
        return result
