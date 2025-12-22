"""
Tests for Device ID Generator (Step 1 of Phase 2.1)

This test file follows Test-Driven Development (TDD) approach:
1. Write tests first (Red phase)
2. Implement code (Green phase)
3. Refactor (Refactor phase)

Test Coverage: 8 test cases for DeviceIDGenerator
"""

import os
import sys
import unittest
import tempfile
import shutil

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from src.edge_app.auth.device_id import DeviceIDGenerator
    DEVICE_ID_AVAILABLE = True
except ImportError as e:
    # Module doesn't exist yet (expected in TDD Red phase)
    print(f"Import failed: {e}")
    DeviceIDGenerator = None
    DEVICE_ID_AVAILABLE = False


class TestDeviceIDGenerator(unittest.TestCase):
    """Test suite for DeviceIDGenerator class"""

    def setUp(self):
        """Set up test environment before each test"""
        if not DEVICE_ID_AVAILABLE:
            self.skipTest("DeviceIDGenerator not implemented yet (TDD Red phase)")
        
        # Create temporary directory for testing
        self.test_dir = tempfile.mkdtemp()
        self.device_id_file = os.path.join(self.test_dir, '.device_id')
    
    def tearDown(self):
        """Clean up after each test"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    # Test 1: Device ID generation returns string
    def test_generate_returns_string(self):
        """Test that generate() returns a string"""
        device_id = DeviceIDGenerator.generate()
        self.assertIsInstance(device_id, str)
    
    # Test 2: Device ID has expected length (64 chars for SHA-256)
    def test_generate_returns_64_char_hex(self):
        """Test that Device ID is 64-character hexadecimal (SHA-256)"""
        device_id = DeviceIDGenerator.generate()
        self.assertEqual(len(device_id), 64)
        # Should be valid hexadecimal
        int(device_id, 16)  # Will raise ValueError if not hex
    
    # Test 3: Device ID is stable (same machine -> same ID)
    def test_generate_is_stable(self):
        """Test that multiple calls return the same Device ID"""
        device_id_1 = DeviceIDGenerator.generate()
        device_id_2 = DeviceIDGenerator.generate()
        self.assertEqual(device_id_1, device_id_2)
    
    # Test 4: get_or_create creates new ID if not exists
    def test_get_or_create_creates_new_id(self):
        """Test that get_or_create() creates new ID when file doesn't exist"""
        device_id = DeviceIDGenerator.get_or_create(storage_path=self.device_id_file)
        self.assertIsInstance(device_id, str)
        self.assertEqual(len(device_id), 64)
    
    # Test 5: get_or_create persists Device ID to file
    def test_get_or_create_persists_to_file(self):
        """Test that Device ID is saved to file"""
        DeviceIDGenerator.get_or_create(storage_path=self.device_id_file)
        self.assertTrue(os.path.exists(self.device_id_file))
    
    # Test 6: get_or_create returns same ID on subsequent calls
    def test_get_or_create_returns_cached_id(self):
        """Test that get_or_create() returns the same ID from file"""
        device_id_1 = DeviceIDGenerator.get_or_create(storage_path=self.device_id_file)
        device_id_2 = DeviceIDGenerator.get_or_create(storage_path=self.device_id_file)
        self.assertEqual(device_id_1, device_id_2)
    
    # Test 7: File permissions are restrictive (chmod 600)
    def test_device_id_file_permissions(self):
        """Test that Device ID file has restrictive permissions (600)"""
        DeviceIDGenerator.get_or_create(storage_path=self.device_id_file)
        
        # Only test on Unix-like systems
        if os.name != 'nt':  # Not Windows
            stat_info = os.stat(self.device_id_file)
            # Check file mode (600 = owner read/write only)
            permissions = stat_info.st_mode & 0o777
            self.assertEqual(permissions, 0o600)
    
    # Test 8: Corrupted file is handled gracefully
    def test_handles_corrupted_device_id_file(self):
        """Test that corrupted Device ID file is regenerated"""
        # Create corrupted file
        with open(self.device_id_file, 'w') as f:
            f.write("corrupted_data_not_64_chars")
        
        # Should regenerate valid Device ID
        device_id = DeviceIDGenerator.get_or_create(storage_path=self.device_id_file)
        self.assertEqual(len(device_id), 64)
        int(device_id, 16)  # Should be valid hex


if __name__ == '__main__':
    unittest.main()
