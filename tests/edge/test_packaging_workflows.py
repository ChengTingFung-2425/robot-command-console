# imports
from pathlib import Path


# ─── 路徑常數 ──────────────────────────────────────────────────────────────

PROJECT_ROOT: Path = Path(__file__).parent.parent.parent
BUILD_WORKFLOW: Path = PROJECT_ROOT / ".github" / "workflows" / "build.yml"
RELEASE_WORKFLOW: Path = PROJECT_ROOT / ".github" / "workflows" / "release.yml"


# ─── 輔助函式 ──────────────────────────────────────────────────────────────

def _workflow_text(path: Path) -> str:
    """Read a GitHub Actions workflow file as UTF-8 text."""
    return path.read_text(encoding="utf-8")


# ─── 1. build.yml 驗證 ──────────────────────────────────────────────────────

class TestBuildWorkflowPackagingScripts:
    """Validate Build and Package workflow reuses cross-platform scripts."""

    def test_build_workflow_exists(self):
        """build.yml must exist."""
        assert BUILD_WORKFLOW.is_file(), ".github/workflows/build.yml not found"

    def test_build_workflow_calls_linux_script(self):
        """Linux packaging must reuse scripts/build-linux.sh."""
        content = _workflow_text(BUILD_WORKFLOW)
        assert "bash scripts/build-linux.sh" in content, \
            "build.yml does not call scripts/build-linux.sh"

    def test_build_workflow_calls_windows_script(self):
        """Windows packaging must reuse scripts/build-windows.ps1."""
        content = _workflow_text(BUILD_WORKFLOW)
        assert "scripts/build-windows.ps1" in content, \
            "build.yml does not call scripts/build-windows.ps1"

    def test_build_workflow_calls_macos_script(self):
        """macOS packaging must reuse scripts/build-macos.sh."""
        content = _workflow_text(BUILD_WORKFLOW)
        assert "bash scripts/build-macos.sh" in content, \
            "build.yml does not call scripts/build-macos.sh"

    def test_build_workflow_uploads_linux_artifacts(self):
        """build.yml must upload both Linux packaging artifacts."""
        content = _workflow_text(BUILD_WORKFLOW)
        assert "dist/RobotConsole-linux.AppImage" in content, \
            "build.yml does not upload RobotConsole-linux.AppImage"
        assert "dist/RobotConsole-linux.tar.gz" in content, \
            "build.yml does not upload RobotConsole-linux.tar.gz"

    def test_build_workflow_uploads_windows_installers(self):
        """build.yml must upload both Windows installer outputs."""
        content = _workflow_text(BUILD_WORKFLOW)
        assert "dist/RobotConsole-Setup-*.exe" in content, \
            "build.yml does not upload PyInstaller NSIS installers"
        assert "dist/RobotConsole-Electron-Setup-*.exe" in content, \
            "build.yml does not upload Electron NSIS installers"

    def test_build_workflow_uploads_macos_tarball(self):
        """build.yml must upload the macOS tarball artifact."""
        content = _workflow_text(BUILD_WORKFLOW)
        assert "dist/RobotConsole-macos.tar.gz" in content, \
            "build.yml does not upload RobotConsole-macos.tar.gz"


# ─── 2. release.yml 驗證 ────────────────────────────────────────────────────

class TestReleaseWorkflowPackagingScripts:
    """Validate Release workflow reuses cross-platform scripts."""

    def test_release_workflow_exists(self):
        """release.yml must exist."""
        assert RELEASE_WORKFLOW.is_file(), ".github/workflows/release.yml not found"

    def test_release_workflow_calls_linux_script(self):
        """Linux release packaging must reuse scripts/build-linux.sh."""
        content = _workflow_text(RELEASE_WORKFLOW)
        assert "bash scripts/build-linux.sh" in content, \
            "release.yml does not call scripts/build-linux.sh"

    def test_release_workflow_calls_windows_script(self):
        """Windows release packaging must reuse scripts/build-windows.ps1."""
        content = _workflow_text(RELEASE_WORKFLOW)
        assert "scripts/build-windows.ps1" in content, \
            "release.yml does not call scripts/build-windows.ps1"

    def test_release_workflow_calls_macos_script(self):
        """macOS release packaging must reuse scripts/build-macos.sh."""
        content = _workflow_text(RELEASE_WORKFLOW)
        assert "bash scripts/build-macos.sh" in content, \
            "release.yml does not call scripts/build-macos.sh"

    def test_release_workflow_references_linux_downloads(self):
        """Release notes and uploads must include Linux artifacts."""
        content = _workflow_text(RELEASE_WORKFLOW)
        assert "RobotConsole-linux.AppImage" in content, \
            "release.yml does not reference RobotConsole-linux.AppImage"
        assert "RobotConsole-linux.tar.gz" in content, \
            "release.yml does not reference RobotConsole-linux.tar.gz"

    def test_release_workflow_references_windows_downloads(self):
        """Release notes and uploads must include Windows installers."""
        content = _workflow_text(RELEASE_WORKFLOW)
        assert "RobotConsole-Setup-" in content, \
            "release.yml does not reference PyInstaller NSIS installers"
        assert "RobotConsole-Electron-Setup-" in content, \
            "release.yml does not reference Electron NSIS installers"

    def test_release_workflow_references_macos_downloads(self):
        """Release notes and uploads must include the macOS tarball."""
        content = _workflow_text(RELEASE_WORKFLOW)
        assert "RobotConsole-macos.tar.gz" in content, \
            "release.yml does not reference RobotConsole-macos.tar.gz"
