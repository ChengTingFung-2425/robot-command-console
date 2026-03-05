# imports
import json
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

import pytest

# ─── 路徑常數 ──────────────────────────────────────────────────────────────

PROJECT_ROOT: Path = Path(__file__).parent.parent.parent
ELECTRON_APP_DIR: Path = PROJECT_ROOT / "Edge" / "electron-app"
QTAPP_DIR: Path = PROJECT_ROOT / "Edge" / "qtwebview-app"
NSIS_SCRIPT: Path = QTAPP_DIR / "installer.nsi"
BUILD_SCRIPT: Path = PROJECT_ROOT / "scripts" / "build-windows.ps1"
DIST_DIR: Path = PROJECT_ROOT / "dist"

# NSIS インストーラー出力ファイルのパターン
NSIS_INSTALLER_PATTERN = "RobotConsole-Setup-*.exe"
ELECTRON_INSTALLER_PATTERN = "RobotConsole-Electron-Setup-*.exe"

# タイムアウト定数
INSTALL_TIMEOUT_SECONDS = 120
UNINSTALL_TIMEOUT_SECONDS = 60


# ─── 輔助函式 ──────────────────────────────────────────────────────────────

def _is_windows() -> bool:
    """Return True if running on Windows."""
    return platform.system() == "Windows"


def _makensis_available() -> bool:
    """Return True if makensis is available in PATH or common install locations."""
    return _get_makensis_path() is not None


def _powershell_available() -> bool:
    """Return True if PowerShell (pwsh or powershell) is available."""
    return bool(shutil.which("pwsh") or shutil.which("powershell"))


def _find_installer_exe(pattern: str) -> Optional[Path]:
    """Find an installer .exe matching pattern in dist/. Returns None if absent."""
    matches = list(DIST_DIR.glob(pattern))
    return matches[0] if matches else None


def _get_makensis_path() -> Optional[str]:
    """Return the path to makensis, or None if not found."""
    found = shutil.which("makensis")
    if found:
        return found
    common_paths = [
        r"C:\Program Files (x86)\NSIS\makensis.exe",
        r"C:\Program Files\NSIS\makensis.exe",
    ]
    for p in common_paths:
        if Path(p).is_file():
            return p
    return None


# ─── 1. 必要原始檔案前提驗證 ─────────────────────────────────────────────────

class TestWindowsInstallerPrerequisites:
    """Verify all source files required for Windows NSIS packaging exist."""

    def test_nsis_script_exists(self):
        """NSIS installer script must exist."""
        assert NSIS_SCRIPT.is_file(), \
            f"Edge/qtwebview-app/installer.nsi not found"

    def test_build_windows_script_exists(self):
        """Windows PowerShell build script must exist."""
        assert BUILD_SCRIPT.is_file(), \
            f"scripts/build-windows.ps1 not found"

    def test_qtapp_build_spec_exists(self):
        """PyInstaller spec file must exist (prerequisite for NSIS packaging)."""
        assert (QTAPP_DIR / "build.spec").is_file(), \
            "Edge/qtwebview-app/build.spec not found"

    def test_qtapp_main_py_exists(self):
        """PyQt6 entry point main.py must exist."""
        assert (QTAPP_DIR / "main.py").is_file(), \
            "Edge/qtwebview-app/main.py not found"

    def test_electron_package_json_exists(self):
        """Electron package.json must exist (for electron-builder NSIS)."""
        assert (ELECTRON_APP_DIR / "package.json").is_file(), \
            "Edge/electron-app/package.json not found"


# ─── 2. NSIS 腳本靜態內容驗證 ───────────────────────────────────────────────

class TestNsisScriptContent:
    """Validate installer.nsi content without running makensis."""

    @pytest.fixture(scope="class")
    def nsi_content(self):
        """Read and return installer.nsi content."""
        return NSIS_SCRIPT.read_text(encoding="utf-8")

    def test_defines_app_name(self, nsi_content):
        """installer.nsi must define APP_NAME."""
        assert "APP_NAME" in nsi_content, \
            "installer.nsi does not define APP_NAME"

    def test_defines_app_version(self, nsi_content):
        """installer.nsi must define APP_VERSION."""
        assert "APP_VERSION" in nsi_content, \
            "installer.nsi does not define APP_VERSION"

    def test_defines_app_exe(self, nsi_content):
        """installer.nsi must reference the main executable name."""
        assert "RobotConsole.exe" in nsi_content, \
            "installer.nsi does not reference RobotConsole.exe"

    def test_outfile_targets_dist(self, nsi_content):
        """OutFile must point to the dist/ directory."""
        assert "dist" in nsi_content and "OutFile" in nsi_content, \
            "installer.nsi OutFile directive does not reference dist/"

    def test_outfile_produces_exe(self, nsi_content):
        """OutFile name must end with .exe."""
        match = re.search(r'OutFile\s+"([^"]+)"', nsi_content)
        assert match, "Cannot find OutFile directive in installer.nsi"
        assert match.group(1).lower().endswith(".exe"), \
            f"OutFile target is not an .exe: {match.group(1)}"

    def test_uses_mui2(self, nsi_content):
        """installer.nsi must use MUI2 for a professional UI."""
        assert "MUI2.nsh" in nsi_content, \
            "installer.nsi does not include MUI2.nsh"

    def test_requests_admin_privileges(self, nsi_content):
        """installer.nsi must request administrator execution level."""
        assert "RequestExecutionLevel admin" in nsi_content, \
            "installer.nsi does not request admin execution level"

    def test_installs_to_program_files(self, nsi_content):
        """installer.nsi should target the 64-bit Program Files directory."""
        assert "PROGRAMFILES64" in nsi_content, \
            "installer.nsi does not install to PROGRAMFILES64"

    def test_writes_uninstall_registry_key(self, nsi_content):
        """installer.nsi must register in Windows Add/Remove Programs."""
        assert "UninstallString" in nsi_content, \
            "installer.nsi does not write UninstallString registry key"

    def test_creates_start_menu_shortcut(self, nsi_content):
        """installer.nsi must create a Start Menu shortcut."""
        assert "SMPROGRAMS" in nsi_content, \
            "installer.nsi does not create a Start Menu shortcut"

    def test_creates_desktop_shortcut(self, nsi_content):
        """installer.nsi must create a Desktop shortcut."""
        assert "DESKTOP" in nsi_content and "CreateShortcut" in nsi_content, \
            "installer.nsi does not create a Desktop shortcut"

    def test_has_uninstall_section(self, nsi_content):
        """installer.nsi must include an Uninstall section."""
        assert 'Section "Uninstall"' in nsi_content, \
            "installer.nsi missing Uninstall section"

    def test_uninstall_removes_shortcuts(self, nsi_content):
        """Uninstall section must remove Start Menu and Desktop shortcuts."""
        assert "Delete" in nsi_content and "SMPROGRAMS" in nsi_content, \
            "Uninstall section does not remove shortcuts"

    def test_uninstall_removes_directory(self, nsi_content):
        """Uninstall section must remove the installation directory."""
        assert "RMDir /r" in nsi_content, \
            "Uninstall section does not use 'RMDir /r' to remove install dir"

    def test_uninstall_removes_registry_key(self, nsi_content):
        """Uninstall section must delete the registry key."""
        assert "DeleteRegKey" in nsi_content, \
            "Uninstall section does not delete registry key"

    def test_includes_english_language(self, nsi_content):
        """installer.nsi must include at least English language."""
        assert 'MUI_LANGUAGE "English"' in nsi_content, \
            "installer.nsi does not include English language"

    def test_copies_dist_robotconsole_directory(self, nsi_content):
        """installer.nsi must copy files from the dist/RobotConsole directory."""
        assert "RobotConsole" in nsi_content and 'File /r' in nsi_content, \
            "installer.nsi does not use 'File /r' to copy RobotConsole build output"

    def test_version_string_format(self, nsi_content):
        """APP_VERSION in installer.nsi must match MAJOR.MINOR.PATCH format."""
        match = re.search(r'!define\s+APP_VERSION\s+"([^"]+)"', nsi_content)
        assert match, "Cannot find APP_VERSION definition in installer.nsi"
        version = match.group(1)
        parts = version.split(".")
        assert len(parts) == 3, \
            f"APP_VERSION '{version}' does not match MAJOR.MINOR.PATCH format"
        assert all(p.isdigit() for p in parts), \
            f"APP_VERSION parts {parts} must all be numeric"

    def test_vi_product_version_defined(self, nsi_content):
        """installer.nsi must set VIProductVersion for EXE metadata."""
        assert "VIProductVersion" in nsi_content, \
            "installer.nsi does not set VIProductVersion"

    def test_quiet_uninstall_string_defined(self, nsi_content):
        """QuietUninstallString must be defined for silent uninstall support."""
        assert "QuietUninstallString" in nsi_content, \
            "installer.nsi does not define QuietUninstallString"


# ─── 3. Electron Windows NSIS 配置驗證 ─────────────────────────────────────

class TestElectronWindowsNsisConfig:
    """Validate electron-builder Windows/NSIS configuration in package.json."""

    @pytest.fixture(scope="class")
    def pkg(self):
        """Parse and return Edge/electron-app/package.json."""
        with open(ELECTRON_APP_DIR / "package.json", encoding="utf-8") as f:
            return json.load(f)

    def test_win_target_defined(self, pkg):
        """package.json must define a 'win' build target."""
        build = pkg.get("build", {})
        assert "win" in build, \
            "package.json build section missing 'win' target configuration"

    def test_win_target_includes_nsis(self, pkg):
        """Windows build target must include NSIS installer."""
        win = pkg.get("build", {}).get("win", {})
        targets = win.get("target", [])
        target_names = [
            t["target"] if isinstance(t, dict) else t
            for t in targets
        ]
        assert "nsis" in target_names, \
            f"Windows targets do not include 'nsis': {target_names}"

    def test_nsis_section_defined(self, pkg):
        """package.json must have a 'nsis' configuration section."""
        build = pkg.get("build", {})
        assert "nsis" in build, \
            "package.json build section missing 'nsis' configuration"

    def test_nsis_one_click_disabled(self, pkg):
        """NSIS should not be one-click (to allow directory selection)."""
        nsis = pkg.get("build", {}).get("nsis", {})
        assert nsis.get("oneClick") is False, \
            "NSIS oneClick should be False to allow user to choose install dir"

    def test_nsis_allows_directory_change(self, pkg):
        """NSIS should allow users to change the installation directory."""
        nsis = pkg.get("build", {}).get("nsis", {})
        assert nsis.get("allowToChangeInstallationDirectory") is True, \
            "NSIS should allow installation directory change"

    def test_nsis_creates_desktop_shortcut(self, pkg):
        """NSIS should create a Desktop shortcut."""
        nsis = pkg.get("build", {}).get("nsis", {})
        assert nsis.get("createDesktopShortcut") is True, \
            "NSIS should create a Desktop shortcut"

    def test_nsis_creates_start_menu_shortcut(self, pkg):
        """NSIS should create a Start Menu shortcut."""
        nsis = pkg.get("build", {}).get("nsis", {})
        assert nsis.get("createStartMenuShortcut") is True, \
            "NSIS should create a Start Menu shortcut"

    def test_nsis_artifact_name_includes_exe(self, pkg):
        """NSIS artifactName must produce a .exe file."""
        nsis = pkg.get("build", {}).get("nsis", {})
        artifact = nsis.get("artifactName", "")
        assert artifact.lower().endswith(".exe"), \
            f"NSIS artifactName should end with .exe, got: {artifact!r}"

    def test_build_win_script_defined(self, pkg):
        """'build:win' npm script must be defined."""
        scripts = pkg.get("scripts", {})
        assert "build:win" in scripts, \
            "npm script 'build:win' is not defined in package.json"

    def test_build_win_nsis_script_defined(self, pkg):
        """'build:win:nsis' npm script must be defined."""
        scripts = pkg.get("scripts", {})
        assert "build:win:nsis" in scripts, \
            "npm script 'build:win:nsis' is not defined in package.json"
        assert "nsis" in scripts["build:win:nsis"], \
            "'build:win:nsis' script must reference nsis target"


# ─── 4. build-windows.ps1 腳本內容驗證 ──────────────────────────────────────

class TestBuildWindowsScriptContent:
    """Validate scripts/build-windows.ps1 content without executing it."""

    @pytest.fixture(scope="class")
    def ps1_content(self):
        """Read and return build-windows.ps1 content."""
        return BUILD_SCRIPT.read_text(encoding="utf-8")

    def test_script_declares_param_block(self, ps1_content):
        """PowerShell script must declare a param() block."""
        assert "param(" in ps1_content, \
            "build-windows.ps1 missing param() block"

    def test_script_has_target_parameter(self, ps1_content):
        """Script must accept a -Target parameter."""
        assert "-Target" in ps1_content or "Target" in ps1_content, \
            "build-windows.ps1 does not define a Target parameter"

    def test_script_has_help_parameter(self, ps1_content):
        """Script must accept a -Help switch."""
        assert "[switch]$Help" in ps1_content, \
            "build-windows.ps1 does not define a -Help switch parameter"

    def test_script_validates_nsis_availability(self, ps1_content):
        """Script must check for NSIS (makensis) before attempting to use it."""
        assert "makensis" in ps1_content, \
            "build-windows.ps1 does not reference makensis"

    def test_script_validates_python_environment(self, ps1_content):
        """Script must verify Python availability."""
        assert "python" in ps1_content.lower(), \
            "build-windows.ps1 does not check for Python"

    def test_script_validates_node_environment(self, ps1_content):
        """Script must verify Node.js availability."""
        assert "node" in ps1_content.lower(), \
            "build-windows.ps1 does not check for Node.js"

    def test_script_references_pyinstaller(self, ps1_content):
        """Script must invoke PyInstaller for the NSIS binary build."""
        assert "PyInstaller" in ps1_content or "pyinstaller" in ps1_content, \
            "build-windows.ps1 does not reference PyInstaller"

    def test_script_references_nsi_file(self, ps1_content):
        """Script must reference installer.nsi."""
        assert "installer.nsi" in ps1_content, \
            "build-windows.ps1 does not reference installer.nsi"

    def test_script_references_electron_builder(self, ps1_content):
        """Script must invoke electron-builder for the Electron NSIS build."""
        assert "electron-builder" in ps1_content, \
            "build-windows.ps1 does not reference electron-builder"

    def test_script_references_dist_directory(self, ps1_content):
        """Script must reference the dist/ output directory."""
        assert "dist" in ps1_content.lower(), \
            "build-windows.ps1 does not reference a dist/ output directory"

    def test_script_has_error_handling(self, ps1_content):
        """Script must set ErrorActionPreference for fail-fast behaviour."""
        assert "ErrorActionPreference" in ps1_content, \
            "build-windows.ps1 does not set ErrorActionPreference"

    def test_script_has_summary_output(self, ps1_content):
        """Script must print a build summary at the end."""
        assert "Summary" in ps1_content or "摘要" in ps1_content, \
            "build-windows.ps1 does not print a build summary"

    def test_build_windows_script_powershell_syntax(self):
        """
        PowerShell syntax check — skipped when PowerShell is not installed.

        On Windows CI PowerShell is always available; on Linux/macOS the check
        is skipped so the test suite can still run in those environments.
        """
        if not _powershell_available():
            pytest.skip("PowerShell (pwsh/powershell) not available — syntax check impossible")

        ps_exe = shutil.which("pwsh") or shutil.which("powershell")
        # Variables must be declared before passing as [ref]
        # Escape single quotes in path (PowerShell single-quote escape: '' )
        safe_path = str(BUILD_SCRIPT).replace("'", "''")
        ps_command = (
            "$t = $null; $e = $null; "
            f"$null = [System.Management.Automation.Language.Parser]::ParseFile("
            f"'{safe_path}', [ref]$t, [ref]$e); "
            "if ($e.Count -gt 0) { $e | ForEach-Object { Write-Error $_.Message }; exit 1 }"
        )
        result = subprocess.run(
            [ps_exe, "-Command", ps_command],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, \
            f"build-windows.ps1 has PowerShell syntax errors:\n{result.stderr}"


# ─── 5. 實際 .exe 安裝程式驗證（產物存在時才執行）────────────────────────────

_NSIS_EXE = _find_installer_exe(NSIS_INSTALLER_PATTERN)
_ELECTRON_EXE = _find_installer_exe(ELECTRON_INSTALLER_PATTERN)


@pytest.mark.skipif(
    _NSIS_EXE is None,
    reason=(
        "PyInstaller NSIS installer .exe not found in dist/ "
        "(build first: makensis Edge/qtwebview-app/installer.nsi) — impossible to test"
    ),
)
class TestNsisInstallerExeArtifact:
    """Validate the built NSIS .exe installer when it is present."""

    def test_installer_exe_is_regular_file(self):
        """NSIS installer .exe must be a regular file."""
        assert _NSIS_EXE.is_file(), \
            f"{_NSIS_EXE} is not a regular file"

    def test_installer_exe_minimum_size(self):
        """NSIS installer .exe must be larger than 1 MB (sanity check)."""
        size_mb = _NSIS_EXE.stat().st_size / (1024 * 1024)
        assert size_mb >= 1, \
            f"{_NSIS_EXE.name} is unexpectedly small ({size_mb:.2f} MB)"

    def test_installer_exe_has_mz_magic(self):
        """NSIS .exe must start with the Windows PE/MZ magic bytes (b'MZ')."""
        with open(_NSIS_EXE, "rb") as f:
            magic = f.read(2)
        assert magic == b"MZ", \
            f"{_NSIS_EXE.name} does not start with MZ magic bytes (got {magic!r}); not a valid Windows executable"

    def test_installer_exe_name_contains_version(self):
        """NSIS installer filename must embed the version number."""
        assert re.search(r"\d+\.\d+\.\d+", _NSIS_EXE.name), \
            f"Installer filename '{_NSIS_EXE.name}' does not contain a version number"

    @pytest.mark.skipif(
        not _is_windows(),
        reason="Silent install/uninstall can only run on Windows — impossible on this platform",
    )
    def test_installer_silent_install_and_uninstall(self, tmp_path):
        """
        Perform a silent installation and then a silent uninstallation.

        This test only runs on Windows and requires administrator privileges.
        """
        install_dir = tmp_path / "RobotConsoleTest"
        # Silent install to a temporary directory
        result = subprocess.run(
            [str(_NSIS_EXE), "/S", f"/D={install_dir}"],
            capture_output=True,
            text=True,
            timeout=INSTALL_TIMEOUT_SECONDS,
        )
        assert result.returncode == 0, \
            f"Silent install failed (exit {result.returncode}):\n{result.stderr}"

        # Verify the main executable was installed
        installed_exe = install_dir / "RobotConsole.exe"
        assert installed_exe.is_file(), \
            f"RobotConsole.exe not found at {installed_exe} after silent install"

        # Silent uninstall
        uninstaller = install_dir / "Uninstall.exe"
        assert uninstaller.is_file(), \
            "Uninstall.exe not found after installation"
        result_un = subprocess.run(
            [str(uninstaller), "/S"],
            capture_output=True,
            text=True,
            timeout=UNINSTALL_TIMEOUT_SECONDS,
        )
        assert result_un.returncode == 0, \
            f"Silent uninstall failed (exit {result_un.returncode}):\n{result_un.stderr}"


@pytest.mark.skipif(
    _ELECTRON_EXE is None,
    reason=(
        "Electron NSIS installer .exe not found in dist/ "
        "(build first: npm run build:win:nsis in Edge/electron-app/) — impossible to test"
    ),
)
class TestElectronNsisInstallerExeArtifact:
    """Validate the built Electron NSIS .exe installer when it is present."""

    def test_electron_installer_is_regular_file(self):
        """Electron NSIS installer .exe must be a regular file."""
        assert _ELECTRON_EXE.is_file(), \
            f"{_ELECTRON_EXE} is not a regular file"

    def test_electron_installer_minimum_size(self):
        """Electron NSIS installer must be at least 10 MB (Electron baseline)."""
        size_mb = _ELECTRON_EXE.stat().st_size / (1024 * 1024)
        assert size_mb >= 10, \
            f"{_ELECTRON_EXE.name} is unexpectedly small ({size_mb:.1f} MB); likely corrupt"

    def test_electron_installer_has_mz_magic(self):
        """Electron NSIS .exe must start with the Windows PE/MZ magic bytes."""
        with open(_ELECTRON_EXE, "rb") as f:
            magic = f.read(2)
        assert magic == b"MZ", \
            f"{_ELECTRON_EXE.name} does not start with MZ magic bytes (got {magic!r})"

    def test_electron_installer_name_matches_config(self):
        """Electron installer filename must match the artifactName pattern in package.json."""
        with open(ELECTRON_APP_DIR / "package.json", encoding="utf-8") as f:
            pkg = json.load(f)
        artifact_template = pkg.get("build", {}).get("nsis", {}).get("artifactName", "")
        # artifactName may use ${version} placeholder — check prefix and suffix
        assert "RobotConsole" in _ELECTRON_EXE.name, \
            f"Electron installer filename '{_ELECTRON_EXE.name}' does not contain 'RobotConsole'"
        assert _ELECTRON_EXE.name.endswith(".exe"), \
            f"Electron installer filename '{_ELECTRON_EXE.name}' does not end with .exe"


# ─── 6. NSIS 工具可用性探測（不是建置，僅報告環境資訊）────────────────────────

class TestNsisEnvironmentProbe:
    """
    Probe for NSIS tooling availability and report the result.

    These tests never fail — they skip when the tool is absent so that the
    overall test suite passes in environments where building is impossible
    (e.g. Linux CI, macOS).  On Windows CI with NSIS installed they run and
    confirm the tool is functional.
    """

    @pytest.mark.skipif(
        not _makensis_available(),
        reason="makensis not available — NSIS compilation impossible on this platform",
    )
    def test_makensis_version_reported(self):
        """makensis must exit 0 and report its version when available."""
        makensis = _get_makensis_path()
        result = subprocess.run(
            [makensis, "/VERSION"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0, \
            f"makensis /VERSION exited {result.returncode}"
        assert result.stdout.strip(), \
            "makensis /VERSION produced no output"

    @pytest.mark.skipif(
        not (_makensis_available() and _is_windows()),
        reason="NSIS syntax check requires makensis on Windows — impossible on this platform",
    )
    def test_nsis_script_compiles_dry_run(self):
        """
        makensis /NOCONFIG /V0 performs a syntax/include check on the .nsi file.

        Note: this will fail if dist/RobotConsole/ does not exist, because
        installer.nsi references those files.  The test is intentionally
        Windows-only and is skipped otherwise.
        """
        makensis = _get_makensis_path()
        result = subprocess.run(
            [makensis, "/V0", str(NSIS_SCRIPT)],
            capture_output=True,
            text=True,
            timeout=INSTALL_TIMEOUT_SECONDS,
            cwd=str(QTAPP_DIR),
        )
        assert result.returncode == 0, \
            f"makensis reported errors on installer.nsi:\n{result.stdout}\n{result.stderr}"
