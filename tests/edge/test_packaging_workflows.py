# imports
from pathlib import Path


# ─── 路徑常數 ──────────────────────────────────────────────────────────────

PROJECT_ROOT_PATH: Path = Path(__file__).parent.parent.parent
BUILD_WORKFLOW_PATH: Path = PROJECT_ROOT_PATH / ".github" / "workflows" / "build.yml"
RELEASE_WORKFLOW_PATH: Path = PROJECT_ROOT_PATH / ".github" / "workflows" / "release.yml"
CLOUD_REQUIREMENTS_PATH: Path = PROJECT_ROOT_PATH / "Cloud" / "requirements.txt"
EDGE_REQUIREMENTS_PATH: Path = PROJECT_ROOT_PATH / "Edge" / "requirements.txt"
EXECUTOR_REQUIREMENTS_PATH: Path = PROJECT_ROOT_PATH / "Executor" / "requirements.txt"
EXPECTED_PSYCOPG_BINARY_PIN = "psycopg2-binary==2.9.5"
LEGACY_PSYCOPG_PIN = "psycopg2==2.9.5"


# ─── 輔助函式 ──────────────────────────────────────────────────────────────

def _load_file_text(path: Path) -> str:
    """Read a project text file, such as workflow YAML or requirements.txt, as UTF-8."""
    return path.read_text(encoding="utf-8")


# ─── 1. build.yml 驗證 ──────────────────────────────────────────────────────

class TestBuildWorkflowPackagingScripts:
    """Validate Build and Package workflow reuses cross-platform scripts."""

    def test_build_workflow_exists(self):
        """build.yml must exist."""
        assert BUILD_WORKFLOW_PATH.is_file(), ".github/workflows/build.yml not found"

    def test_build_workflow_calls_linux_script(self):
        """Linux packaging must reuse scripts/build-linux.sh."""
        content = _load_file_text(BUILD_WORKFLOW_PATH)
        assert "bash scripts/build-linux.sh" in content, \
            "build.yml does not call scripts/build-linux.sh"

    def test_build_workflow_calls_windows_script(self):
        """Windows packaging must reuse scripts/build-windows.ps1."""
        content = _load_file_text(BUILD_WORKFLOW_PATH)
        assert "scripts/build-windows.ps1" in content, \
            "build.yml does not call scripts/build-windows.ps1"

    def test_build_workflow_calls_macos_script(self):
        """macOS packaging must reuse scripts/build-macos.sh."""
        content = _load_file_text(BUILD_WORKFLOW_PATH)
        assert "bash scripts/build-macos.sh" in content, \
            "build.yml does not call scripts/build-macos.sh"

    def test_build_workflow_uploads_linux_artifacts(self):
        """build.yml must upload both Linux packaging artifacts."""
        content = _load_file_text(BUILD_WORKFLOW_PATH)
        assert "dist/RobotConsole-linux.AppImage" in content, \
            "build.yml does not upload RobotConsole-linux.AppImage"
        assert "dist/RobotConsole-linux.tar.gz" in content, \
            "build.yml does not upload RobotConsole-linux.tar.gz"

    def test_build_workflow_uploads_windows_installers(self):
        """build.yml must upload both Windows installer outputs."""
        content = _load_file_text(BUILD_WORKFLOW_PATH)
        assert "dist/RobotConsole-Setup-*.exe" in content, \
            "build.yml does not upload PyInstaller NSIS installers"
        assert "dist/RobotConsole-Electron-Setup-*.exe" in content, \
            "build.yml does not upload Electron NSIS installers"

    def test_build_workflow_uploads_macos_tarball(self):
        """build.yml must upload the macOS tarball artifact."""
        content = _load_file_text(BUILD_WORKFLOW_PATH)
        assert "dist/RobotConsole-macos.tar.gz" in content, \
            "build.yml does not upload RobotConsole-macos.tar.gz"

class TestReleaseWorkflowPackagingScripts:
    """Validate Release workflow reuses cross-platform scripts."""

    def test_release_workflow_exists(self):
        """release.yml must exist."""
        assert RELEASE_WORKFLOW_PATH.is_file(), ".github/workflows/release.yml not found"

    def test_release_workflow_calls_linux_script(self):
        """Linux release packaging must reuse scripts/build-linux.sh."""
        content = _load_file_text(RELEASE_WORKFLOW_PATH)
        assert "bash scripts/build-linux.sh" in content, \
            "release.yml does not call scripts/build-linux.sh"

    def test_release_workflow_calls_windows_script(self):
        """Windows release packaging must reuse scripts/build-windows.ps1."""
        content = _load_file_text(RELEASE_WORKFLOW_PATH)
        assert "scripts/build-windows.ps1" in content, \
            "release.yml does not call scripts/build-windows.ps1"

    def test_release_workflow_calls_macos_script(self):
        """macOS release packaging must reuse scripts/build-macos.sh."""
        content = _load_file_text(RELEASE_WORKFLOW_PATH)
        assert "bash scripts/build-macos.sh" in content, \
            "release.yml does not call scripts/build-macos.sh"

    def test_release_workflow_references_linux_downloads(self):
        """Release notes and uploads must include Linux artifacts."""
        content = _load_file_text(RELEASE_WORKFLOW_PATH)
        assert "RobotConsole-linux.AppImage" in content, \
            "release.yml does not reference RobotConsole-linux.AppImage"
        assert "RobotConsole-linux.tar.gz" in content, \
            "release.yml does not reference RobotConsole-linux.tar.gz"

    def test_release_workflow_references_windows_downloads(self):
        """Release notes and uploads must include Windows installers."""
        content = _load_file_text(RELEASE_WORKFLOW_PATH)
        assert "RobotConsole-Setup-" in content, \
            "release.yml does not reference PyInstaller NSIS installers"
        assert "RobotConsole-Electron-Setup-" in content, \
            "release.yml does not reference Electron NSIS installers"

    def test_release_workflow_references_macos_downloads(self):
        """Release notes and uploads must include the macOS tarball."""
        content = _load_file_text(RELEASE_WORKFLOW_PATH)
        assert "RobotConsole-macos.tar.gz" in content, \
            "release.yml does not reference RobotConsole-macos.tar.gz"

class TestWorkflowDependencies:
    """Validate workflow dependency setup for packaging jobs."""

    def test_build_workflow_uses_mysql_client_on_macos(self):
        """build.yml macOS setup must use MySQL client instead of PostgreSQL."""
        content = _load_file_text(BUILD_WORKFLOW_PATH)
        assert "brew install mysql-client" in content, \
            "build.yml does not install mysql-client on macOS"
        assert "brew install postgresql" not in content, \
            "build.yml should not install PostgreSQL on macOS"

    def test_release_workflow_uses_mysql_client_on_macos(self):
        """release.yml macOS setup must use MySQL client instead of PostgreSQL."""
        content = _load_file_text(RELEASE_WORKFLOW_PATH)
        assert "brew install mysql-client" in content, \
            "release.yml does not install mysql-client on macOS"
        assert "brew install postgresql" not in content, \
            "release.yml should not install PostgreSQL on macOS"


class TestPackagingRequirements:
    """Validate packaging requirements avoid PostgreSQL build tools in CI."""

    def test_module_requirements_use_binary_psycopg(self):
        """Packaging requirements should use psycopg2-binary to avoid pg_config in CI."""
        for path in (
            CLOUD_REQUIREMENTS_PATH,
            EDGE_REQUIREMENTS_PATH,
            EXECUTOR_REQUIREMENTS_PATH,
        ):
            content = _load_file_text(path)
            assert EXPECTED_PSYCOPG_BINARY_PIN in content, \
                f"{path} does not pin psycopg2-binary"
            assert LEGACY_PSYCOPG_PIN not in content, \
                f"{path} should not pin source-built psycopg2"
