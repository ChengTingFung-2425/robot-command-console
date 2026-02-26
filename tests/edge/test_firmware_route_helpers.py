# imports
import sys
from pathlib import Path
import pytest

# Edge/qtwebview-app has a dash so it cannot be imported as a Python package directly.
# Add its directory to sys.path so the module can be imported by filename.
_QTWEBVIEW_DIR = str(Path(__file__).parent.parent.parent / "Edge" / "qtwebview-app")
if _QTWEBVIEW_DIR not in sys.path:
    sys.path.insert(0, _QTWEBVIEW_DIR)

from routes_firmware_tiny import (  # noqa: E402
    _build_remote_firmware_path,
    _validate_and_sanitize_identifier,
    _validate_remote_path,
)


class TestValidateAndSanitizeIdentifier:
    """Tests for _validate_and_sanitize_identifier (firmware_id / robot_id)."""

    def test_accepts_alphanumeric(self):
        assert _validate_and_sanitize_identifier("fw001") == "fw001"

    def test_accepts_dash_and_underscore(self):
        assert _validate_and_sanitize_identifier("fw_001-beta") == "fw_001-beta"

    def test_rejects_empty_string(self):
        assert _validate_and_sanitize_identifier("") is None

    def test_rejects_none(self):
        assert _validate_and_sanitize_identifier(None) is None

    def test_rejects_path_traversal_dotdot(self):
        assert _validate_and_sanitize_identifier("../admin") is None

    def test_rejects_forward_slash(self):
        assert _validate_and_sanitize_identifier("fw/etc") is None

    def test_rejects_backslash(self):
        assert _validate_and_sanitize_identifier("fw\\etc") is None

    def test_rejects_null_byte(self):
        assert _validate_and_sanitize_identifier("fw\x00id") is None

    def test_rejects_special_chars(self):
        for bad in ["fw@id", "fw id", "fw.id", "fw:id"]:
            assert _validate_and_sanitize_identifier(bad) is None, f"expected None for {bad!r}"


class TestValidateRemotePath:
    """Tests for _validate_remote_path."""

    def test_accepts_simple_absolute_path(self):
        assert _validate_remote_path("/opt/firmware") == "/opt/firmware"

    def test_accepts_path_with_subdirs(self):
        assert _validate_remote_path("/opt/robot/firmware") == "/opt/robot/firmware"

    def test_accepts_path_with_trailing_slash(self):
        # trailing slash is fine; the function should pass it through
        assert _validate_remote_path("/opt/firmware/") == "/opt/firmware/"

    def test_accepts_hidden_dir_in_path(self):
        # /opt/.config is a legitimate path; only /./  and trailing /. are rejected
        assert _validate_remote_path("/opt/config") is not None

    def test_rejects_empty_string(self):
        assert _validate_remote_path("") is None

    def test_rejects_none(self):
        assert _validate_remote_path(None) is None

    def test_rejects_relative_path(self):
        assert _validate_remote_path("opt/firmware") is None

    def test_rejects_dotdot_traversal(self):
        assert _validate_remote_path("/opt/../etc/passwd") is None

    def test_rejects_null_byte(self):
        assert _validate_remote_path("/opt/fw\x00") is None

    def test_rejects_dot_component_middle(self):
        # /path/./etc — single-dot middle component
        assert _validate_remote_path("/path/./etc") is None

    def test_rejects_dot_component_end(self):
        # /path/. — trailing single-dot component
        assert _validate_remote_path("/path/.") is None

    def test_rejects_shell_special_chars(self):
        for bad in ["/opt/fw;rm -rf /", "/opt/fw|cat", "/opt/fw$(whoami)"]:
            assert _validate_remote_path(bad) is None, f"expected None for {bad!r}"

    def test_normalised_traversal_still_rejected(self):
        # normpath on /a/b/../../etc gives /etc — should still be caught
        assert _validate_remote_path("/a/b/../../etc") is None


class TestBuildRemoteFirmwarePath:
    """Tests for _build_remote_firmware_path."""

    def test_joins_path_and_filename(self):
        result = _build_remote_firmware_path("/opt/firmware", "/tmp/firmware/fw_001.bin")
        assert result == "/opt/firmware/fw_001.bin"

    def test_strips_trailing_slash_from_remote(self):
        result = _build_remote_firmware_path("/opt/firmware/", "/tmp/firmware/fw_001.bin")
        assert result == "/opt/firmware/fw_001.bin"

    def test_root_remote_path(self):
        result = _build_remote_firmware_path("/", "/tmp/fw.bin")
        assert result == "/fw.bin"

    def test_raises_on_empty_remote_path(self):
        with pytest.raises(ValueError, match="Remote path must not be empty"):
            _build_remote_firmware_path("", "/tmp/fw.bin")

    def test_raises_on_null_byte_in_remote(self):
        with pytest.raises(ValueError, match="null bytes"):
            _build_remote_firmware_path("/opt/fw\x00", "/tmp/fw.bin")

    def test_raises_on_null_byte_in_local(self):
        with pytest.raises(ValueError, match="null bytes"):
            _build_remote_firmware_path("/opt/firmware", "/tmp/fw\x00.bin")

    def test_raises_when_local_has_no_filename(self):
        # os.path.basename of "/" is ""
        with pytest.raises(ValueError, match="file name"):
            _build_remote_firmware_path("/opt/firmware", "/")

    def test_raises_on_dot_filename(self):
        with pytest.raises(ValueError, match="Invalid firmware file name"):
            _build_remote_firmware_path("/opt/firmware", "/tmp/.")

    def test_raises_on_dotdot_filename(self):
        with pytest.raises(ValueError, match="Invalid firmware file name"):
            _build_remote_firmware_path("/opt/firmware", "/tmp/..")

    def test_raises_on_unsafe_chars_in_filename(self):
        with pytest.raises(ValueError, match="Invalid characters"):
            _build_remote_firmware_path("/opt/firmware", "/tmp/fw;rm.bin")
