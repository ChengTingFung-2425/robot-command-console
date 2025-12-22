"""
Device ID Generator for Edge Token Cache

This module provides stable device identification for token binding.
Device ID is generated from machine characteristics and persisted.
"""

import os
import hashlib
import platform
import socket
from typing import Optional
import uuid


class DeviceIDGenerator:
    """
    Generate and manage stable Device IDs for Edge devices.
    
    Device ID is a SHA-256 hash of machine characteristics:
    - MAC address
    - Hostname
    - Platform information
    - CPU information
    
    The ID is stable across reboots and persisted to local storage.
    """
    
    DEFAULT_STORAGE_PATH = os.path.expanduser("~/.robot-edge/.device_id")
    
    @staticmethod
    def generate() -> str:
        """
        Generate a stable Device ID based on machine characteristics.
        
        Returns:
            str: 64-character hexadecimal Device ID (SHA-256 hash)
        """
        # Collect machine characteristics
        characteristics = []
        
        # 1. MAC address (most stable identifier)
        try:
            mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff)
                           for elements in range(0, 2*6, 2)][::-1])
            characteristics.append(mac)
        except Exception:
            characteristics.append("no-mac")
        
        # 2. Hostname
        try:
            hostname = socket.gethostname()
            characteristics.append(hostname)
        except Exception:
            characteristics.append("no-hostname")
        
        # 3. Platform information
        try:
            platform_info = f"{platform.system()}-{platform.machine()}"
            characteristics.append(platform_info)
        except Exception:
            characteristics.append("no-platform")
        
        # 4. CPU information (if available)
        try:
            # Try to get CPU info
            if hasattr(platform, 'processor'):
                cpu_info = platform.processor()
                if cpu_info:
                    characteristics.append(cpu_info)
        except Exception:
            # Ignore CPU info retrieval errors (not critical for device ID)
            pass
        
        # Combine all characteristics
        combined = "|".join(characteristics)
        
        # Generate SHA-256 hash
        device_id = hashlib.sha256(combined.encode('utf-8')).hexdigest()
        
        return device_id
    
    @staticmethod
    def get_or_create(storage_path: Optional[str] = None) -> str:
        """
        Get existing Device ID from file or create new one.
        
        Args:
            storage_path: Path to store Device ID file.
                         Defaults to ~/.robot-edge/.device_id
        
        Returns:
            str: 64-character hexadecimal Device ID
        """
        if storage_path is None:
            storage_path = DeviceIDGenerator.DEFAULT_STORAGE_PATH
        
        # Try to read existing Device ID
        if os.path.exists(storage_path):
            try:
                with open(storage_path, 'r') as f:
                    device_id = f.read().strip()
                
                # Validate Device ID format
                if len(device_id) == 64:
                    # Check if it's valid hexadecimal
                    try:
                        int(device_id, 16)
                        return device_id
                    except ValueError:
                        pass  # Invalid hex, will regenerate
            except Exception:
                pass  # File read error, will regenerate
        
        # Generate new Device ID
        device_id = DeviceIDGenerator.generate()
        
        # Ensure directory exists
        storage_dir = os.path.dirname(storage_path)
        if storage_dir and not os.path.exists(storage_dir):
            os.makedirs(storage_dir, mode=0o700, exist_ok=True)
        
        # Write Device ID to file
        with open(storage_path, 'w') as f:
            f.write(device_id)
        
        # Set restrictive permissions (chmod 600) on Unix-like systems
        if os.name != 'nt':  # Not Windows
            os.chmod(storage_path, 0o600)
        
        return device_id
