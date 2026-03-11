# imports
import stat
import subprocess
from pathlib import Path

import pytest

# ─── 路徑常數 ──────────────────────────────────────────────────────────────

PROJECT_ROOT: Path = Path(__file__).parent.parent.parent
QTAPP_DIR: Path = PROJECT_ROOT / "Edge" / "qtwebview-app"
BUILD_SCRIPT: Path = PROJECT_ROOT / "scripts" / "build-macos.sh"


# ─── 1. 打包前提：必要原始檔案 ─────────────────────────────────────────────

class TestMacOSPackagingPrerequisites:
    """Verify all source files required for macOS packaging exist."""

    def test_qtapp_main_py_exists(self):
        """PyQt6 application entry point must exist."""
        assert (QTAPP_DIR / "main.py").is_file(), \
            "Edge/qtwebview-app/main.py not found"

    def test_qtapp_build_spec_exists(self):
        """PyInstaller spec file must exist."""
        assert (QTAPP_DIR / "build.spec").is_file(), \
            "Edge/qtwebview-app/build.spec not found"

    def test_qtapp_resources_dir_exists(self):
        """Qt app resources directory must exist."""
        assert (QTAPP_DIR / "resources").is_dir(), \
            "Edge/qtwebview-app/resources/ directory not found"

    def test_build_script_exists(self):
        """macOS build script must exist."""
        assert BUILD_SCRIPT.is_file(), \
            "scripts/build-macos.sh not found"

    def test_build_script_is_executable(self):
        """macOS build script must have executable permission."""
        mode = BUILD_SCRIPT.stat().st_mode
        assert mode & stat.S_IXUSR, \
            "scripts/build-macos.sh is not executable (missing user +x)"


# ─── 2. build-macos.sh 腳本行為驗證 ───────────────────────────────────────

class TestMacOSBuildScript:
    """Validate scripts/build-macos.sh behaviour without running a full build."""

    def test_help_flag_succeeds(self):
        """--help flag must exit 0 and print usage information."""
        result = subprocess.run(
            ["bash", str(BUILD_SCRIPT), "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, \
            f"--help exited {result.returncode}:\n{result.stderr}"
        assert "macOS" in result.stdout, \
            "--help output missing 'macOS' keyword"
        assert "tar.gz" in result.stdout, \
            "--help output missing tar.gz description"

    def test_help_flag_short_form(self):
        """-h flag must also work."""
        result = subprocess.run(
            ["bash", str(BUILD_SCRIPT), "-h"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"-h exited {result.returncode}"

    def test_unknown_flag_exits_nonzero(self):
        """An unrecognised flag must exit with a non-zero status."""
        result = subprocess.run(
            ["bash", str(BUILD_SCRIPT), "--not-a-real-option"],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0, \
            "Expected non-zero exit for unknown flag, got 0"

    def test_script_has_shebang(self):
        """Build script must have a valid bash shebang."""
        first_line = BUILD_SCRIPT.read_text(encoding="utf-8").splitlines()[0]
        assert first_line.startswith("#!/"), \
            f"Missing shebang line; got: {first_line!r}"
        assert "bash" in first_line, \
            f"Shebang must reference bash; got: {first_line!r}"

    def test_script_passes_shellcheck_syntax(self):
        """Shell script must have no syntax errors (bash -n)."""
        result = subprocess.run(
            ["bash", "-n", str(BUILD_SCRIPT)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, \
            f"bash -n reported syntax errors:\n{result.stderr}"

    def test_script_references_pyinstaller(self):
        """build-macos.sh must reference pyinstaller for macOS packaging."""
        content = BUILD_SCRIPT.read_text(encoding="utf-8")
        assert "pyinstaller" in content.lower(), \
            "build-macos.sh does not reference pyinstaller"

    def test_script_references_build_spec(self):
        """build-macos.sh must reference build.spec."""
        content = BUILD_SCRIPT.read_text(encoding="utf-8")
        assert "build.spec" in content, \
            "build-macos.sh does not reference build.spec"

    def test_script_references_macos_tarball(self):
        """build-macos.sh must create the expected macOS tar.gz artifact."""
        content = BUILD_SCRIPT.read_text(encoding="utf-8")
        assert "RobotConsole-macos.tar.gz" in content, \
            "build-macos.sh does not reference RobotConsole-macos.tar.gz"

    def test_script_references_macos_bundle(self):
        """build-macos.sh must archive RobotConsole.app when present."""
        content = BUILD_SCRIPT.read_text(encoding="utf-8")
        assert "RobotConsole.app" in content, \
            "build-macos.sh does not reference RobotConsole.app"

    def test_script_sets_errexit(self):
        """build-macos.sh must use set -e (or set -euo pipefail) for safety."""
        content = BUILD_SCRIPT.read_text(encoding="utf-8")
        assert "set -e" in content, \
            "build-macos.sh does not use 'set -e' for error handling"

    def test_script_creates_dist_dir(self):
        """build-macos.sh must create the dist/ output directory."""
        content = BUILD_SCRIPT.read_text(encoding="utf-8")
        assert "mkdir" in content and "dist" in content, \
            "build-macos.sh does not create the dist/ directory"
