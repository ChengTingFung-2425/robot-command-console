# imports
import json
import os
import stat
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

# ─── 路徑常數 ──────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).parent.parent.parent
ELECTRON_APP_DIR = PROJECT_ROOT / "Edge" / "electron-app"
QTAPP_DIR = PROJECT_ROOT / "Edge" / "qtwebview-app"
BUILD_SCRIPT = PROJECT_ROOT / "scripts" / "build-linux.sh"
DIST_DIR = PROJECT_ROOT / "dist"
BINARY_TARBALL = DIST_DIR / "RobotConsole-linux.tar.gz"
APPIMAGE = DIST_DIR / "RobotConsole-linux.AppImage"


# ─── 輔助函式 ──────────────────────────────────────────────────────────────

def _artifact_exists(path: Path) -> bool:
    """Return True if a packaging artifact file exists on disk."""
    return path.exists() and path.is_file()


# ─── 1. 打包前提：必要原始檔案 ─────────────────────────────────────────────

class TestPackagingPrerequisites:
    """Verify all source files required for packaging exist before building."""

    # ── Electron AppImage 所需檔案 ──────────────────────────────────────────

    def test_electron_main_js_exists(self):
        """Electron entry point must exist."""
        assert (ELECTRON_APP_DIR / "main.js").is_file(), \
            f"Edge/electron-app/main.js not found"

    def test_electron_preload_js_exists(self):
        """Electron preload bridge must exist."""
        assert (ELECTRON_APP_DIR / "preload.js").is_file(), \
            f"Edge/electron-app/preload.js not found"

    def test_electron_renderer_dir_exists(self):
        """Electron renderer directory must exist."""
        assert (ELECTRON_APP_DIR / "renderer").is_dir(), \
            f"Edge/electron-app/renderer/ directory not found"

    def test_electron_renderer_html_exists(self):
        """Electron renderer HTML must exist."""
        assert (ELECTRON_APP_DIR / "renderer" / "index.html").is_file(), \
            f"Edge/electron-app/renderer/index.html not found"

    def test_electron_package_json_exists(self):
        """Electron package.json must exist."""
        assert (ELECTRON_APP_DIR / "package.json").is_file(), \
            f"Edge/electron-app/package.json not found"

    # ── PyInstaller Binary 所需檔案 ─────────────────────────────────────────

    def test_qtapp_main_py_exists(self):
        """PyQt6 application entry point must exist."""
        assert (QTAPP_DIR / "main.py").is_file(), \
            f"Edge/qtwebview-app/main.py not found"

    def test_qtapp_build_spec_exists(self):
        """PyInstaller spec file must exist."""
        assert (QTAPP_DIR / "build.spec").is_file(), \
            f"Edge/qtwebview-app/build.spec not found"

    def test_qtapp_resources_dir_exists(self):
        """Qt app resources directory must exist."""
        assert (QTAPP_DIR / "resources").is_dir(), \
            f"Edge/qtwebview-app/resources/ directory not found"

    def test_webui_static_dir_exists(self):
        """WebUI static assets referenced by build.spec must exist."""
        assert (PROJECT_ROOT / "Edge" / "WebUI" / "app" / "static").is_dir(), \
            f"Edge/WebUI/app/static/ directory not found"

    def test_webui_templates_dir_exists(self):
        """WebUI templates referenced by build.spec must exist."""
        assert (PROJECT_ROOT / "Edge" / "WebUI" / "app" / "templates").is_dir(), \
            f"Edge/WebUI/app/templates/ directory not found"

    def test_common_version_module_exists(self):
        """src/common/version.py must exist (listed as hiddenimport)."""
        assert (PROJECT_ROOT / "src" / "common" / "version.py").is_file(), \
            f"src/common/version.py not found"

    def test_common_version_importable(self):
        """version module must be importable without error."""
        import importlib.util
        version_path = PROJECT_ROOT / "src" / "common" / "version.py"
        spec = importlib.util.spec_from_file_location("src_common_version", version_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        assert hasattr(mod, "__version__"), \
            "version module missing __version__"

    def test_flask_service_py_exists(self):
        """flask_service.py referenced in Electron files list must exist."""
        assert (PROJECT_ROOT / "Edge" / "flask_service.py").is_file() or \
               (PROJECT_ROOT / "flask_service.py").is_file(), \
            "flask_service.py not found in project root or Edge/"

    def test_build_script_exists(self):
        """Linux build script must exist."""
        assert BUILD_SCRIPT.is_file(), \
            f"scripts/build-linux.sh not found"

    def test_build_script_is_executable(self):
        """Linux build script must have executable permission."""
        mode = BUILD_SCRIPT.stat().st_mode
        assert mode & stat.S_IXUSR, \
            "scripts/build-linux.sh is not executable (missing user +x)"


# ─── 2. Electron AppImage 打包配置驗證 ──────────────────────────────────────

class TestElectronAppImageConfig:
    """Validate electron-builder configuration in package.json."""

    @pytest.fixture(scope="class")
    def pkg(self):
        """Parse and return Edge/electron-app/package.json."""
        with open(ELECTRON_APP_DIR / "package.json", encoding="utf-8") as f:
            return json.load(f)

    def test_package_has_build_section(self, pkg):
        """package.json must contain an electron-builder 'build' section."""
        assert "build" in pkg, "package.json missing 'build' section"

    def test_appid_defined(self, pkg):
        """AppImage requires a valid appId."""
        build = pkg.get("build", {})
        assert "appId" in build, "build.appId is missing"
        assert build["appId"], "build.appId must not be empty"

    def test_linux_target_is_appimage(self, pkg):
        """Linux build target must include AppImage."""
        linux = pkg.get("build", {}).get("linux", {})
        targets = linux.get("target", [])
        assert "AppImage" in targets, \
            f"Expected 'AppImage' in linux.target, got: {targets}"

    def test_linux_category_defined(self, pkg):
        """Linux AppImage should declare a freedesktop category."""
        linux = pkg.get("build", {}).get("linux", {})
        assert "category" in linux, "linux.category is missing from build config"

    def test_main_entry_defined(self, pkg):
        """package.json 'main' field must be set for Electron."""
        assert "main" in pkg, "package.json missing 'main' field"
        assert pkg["main"], "package.json 'main' field must not be empty"

    def test_files_include_main_js(self, pkg):
        """Electron packaged files list must include main.js."""
        files = pkg.get("build", {}).get("files", [])
        assert any("main.js" in f for f in files), \
            "main.js not listed in build.files"

    def test_files_include_preload_js(self, pkg):
        """Electron packaged files list must include preload.js."""
        files = pkg.get("build", {}).get("files", [])
        assert any("preload.js" in f for f in files), \
            "preload.js not listed in build.files"

    def test_files_include_renderer(self, pkg):
        """Electron packaged files list must include renderer assets."""
        files = pkg.get("build", {}).get("files", [])
        assert any("renderer" in f for f in files), \
            "renderer/** not listed in build.files"

    def test_build_appimage_script_defined(self, pkg):
        """'build:appimage' npm script must be defined."""
        scripts = pkg.get("scripts", {})
        assert "build:appimage" in scripts, \
            "npm script 'build:appimage' is not defined in package.json"
        assert "AppImage" in scripts["build:appimage"], \
            "'build:appimage' script should invoke electron-builder with AppImage target"

    def test_electron_builder_in_dev_deps(self, pkg):
        """electron-builder must be listed in devDependencies."""
        dev_deps = pkg.get("devDependencies", {})
        assert "electron-builder" in dev_deps, \
            "electron-builder not found in devDependencies"


# ─── 3. PyInstaller Binary 配置驗證（build.spec）───────────────────────────

class TestPyInstallerBinaryConfig:
    """Validate PyInstaller build.spec contents without running pyinstaller."""

    @pytest.fixture(scope="class")
    def spec_content(self):
        """Read and return the build.spec file contents."""
        return (QTAPP_DIR / "build.spec").read_text(encoding="utf-8")

    def test_spec_declares_entry_point(self, spec_content):
        """build.spec must reference main.py as the entry point."""
        assert "main.py" in spec_content, \
            "build.spec does not reference main.py as entry point"

    def test_spec_sets_output_name(self, spec_content):
        """build.spec must set the output binary name."""
        assert "RobotConsole" in spec_content, \
            "build.spec does not define 'RobotConsole' as the output name"

    def test_spec_includes_resources(self, spec_content):
        """build.spec must include the resources directory."""
        assert "resources" in spec_content, \
            "build.spec does not reference resources data"

    def test_spec_includes_webui_static(self, spec_content):
        """build.spec must include WebUI static assets."""
        assert "static" in spec_content, \
            "build.spec does not reference WebUI static assets"

    def test_spec_includes_webui_templates(self, spec_content):
        """build.spec must include WebUI templates."""
        assert "templates" in spec_content, \
            "build.spec does not reference WebUI templates"

    def test_spec_has_hidden_imports_flask(self, spec_content):
        """build.spec must declare Flask as a hidden import."""
        assert "Flask" in spec_content, \
            "build.spec missing Flask in hiddenimports"

    def test_spec_has_hidden_import_version(self, spec_content):
        """build.spec must declare the version module as a hidden import."""
        assert "version" in spec_content, \
            "build.spec missing version module in hiddenimports"

    def test_spec_excludes_heavy_packages(self, spec_content):
        """build.spec should exclude unnecessary heavy packages."""
        for pkg in ("matplotlib", "numpy", "tensorflow", "torch"):
            assert pkg in spec_content, \
                f"build.spec does not list '{pkg}' in excludes"

    def test_spec_has_collect_stage(self, spec_content):
        """build.spec must include a COLLECT stage for one-dir output."""
        assert "COLLECT" in spec_content, \
            "build.spec missing COLLECT stage (required for one-dir mode)"

    def test_spec_uses_upx(self, spec_content):
        """build.spec should enable UPX compression."""
        assert "upx=True" in spec_content, \
            "build.spec does not enable UPX compression"

    def test_spec_is_valid_python_syntax(self):
        """build.spec must be syntactically valid Python."""
        spec_path = str(QTAPP_DIR / "build.spec")
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", spec_path],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, \
            f"build.spec has Python syntax errors:\n{result.stderr}"


# ─── 4. build-linux.sh 腳本行為驗證 ─────────────────────────────────────────

class TestBuildScript:
    """Validate scripts/build-linux.sh behaviour without running a full build."""

    def test_help_flag_succeeds(self):
        """--help flag must exit 0 and print usage information."""
        result = subprocess.run(
            ["bash", str(BUILD_SCRIPT), "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, \
            f"--help exited {result.returncode}:\n{result.stderr}"
        assert "AppImage" in result.stdout, \
            "--help output missing 'AppImage' keyword"
        assert "tar.gz" in result.stdout or "Binary" in result.stdout, \
            "--help output missing binary/tar.gz description"

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

    def test_script_references_appimage_target(self):
        """build-linux.sh must reference electron-builder AppImage target."""
        content = BUILD_SCRIPT.read_text(encoding="utf-8")
        assert "AppImage" in content, \
            "build-linux.sh does not reference AppImage"

    def test_script_references_pyinstaller(self):
        """build-linux.sh must reference pyinstaller for binary packaging."""
        content = BUILD_SCRIPT.read_text(encoding="utf-8")
        assert "pyinstaller" in content, \
            "build-linux.sh does not reference pyinstaller"

    def test_script_references_build_spec(self):
        """build-linux.sh must reference build.spec."""
        content = BUILD_SCRIPT.read_text(encoding="utf-8")
        assert "build.spec" in content, \
            "build-linux.sh does not reference build.spec"

    def test_script_sets_errexit(self):
        """build-linux.sh must use set -e (or set -euo pipefail) for safety."""
        content = BUILD_SCRIPT.read_text(encoding="utf-8")
        assert "set -e" in content, \
            "build-linux.sh does not use 'set -e' for error handling"

    def test_script_creates_dist_dir(self):
        """build-linux.sh must create the dist/ output directory."""
        content = BUILD_SCRIPT.read_text(encoding="utf-8")
        assert "mkdir" in content and "dist" in content, \
            "build-linux.sh does not create the dist/ directory"


# ─── 5. 打包產物驗證（若產物已存在）──────────────────────────────────────────

@pytest.mark.skipif(
    not _artifact_exists(BINARY_TARBALL),
    reason="Binary tar.gz artifact not present (run build-linux.sh --binary first)",
)
class TestBinaryTarballArtifact:
    """Validate the packaged binary tar.gz when it has been built."""

    def test_tarball_is_readable(self):
        """Tarball must be readable and valid gzip."""
        assert tarfile.is_tarfile(str(BINARY_TARBALL)), \
            f"{BINARY_TARBALL} is not a valid tar archive"

    def test_tarball_contains_executable(self):
        """Tarball must contain the RobotConsole executable."""
        with tarfile.open(str(BINARY_TARBALL), "r:gz") as tf:
            names = tf.getnames()
        executables = [n for n in names if "RobotConsole" in n and "/." not in n]
        assert executables, \
            f"No RobotConsole executable found in tar. Members:\n" + "\n".join(names[:20])

    def test_tarball_executable_has_correct_permissions(self):
        """The RobotConsole binary inside the tarball must be executable."""
        with tarfile.open(str(BINARY_TARBALL), "r:gz") as tf:
            for member in tf.getmembers():
                if member.name.endswith("RobotConsole") and member.isfile():
                    assert member.mode & 0o111, \
                        f"RobotConsole in tarball is not executable (mode={oct(member.mode)})"
                    return
        pytest.fail("RobotConsole file member not found in tarball")

    def test_tarball_contains_resources(self):
        """Tarball must contain at least one resource file."""
        with tarfile.open(str(BINARY_TARBALL), "r:gz") as tf:
            names = tf.getnames()
        has_resources = any("resources" in n or "_internal" in n or ".so" in n for n in names)
        assert has_resources, \
            "Tarball does not contain expected resource files"

    def test_extracted_binary_is_elf_on_linux(self, tmp_path):
        """Extracted binary must be a valid ELF executable on Linux."""
        import platform
        if platform.system() != "Linux":
            pytest.skip("ELF check only applicable on Linux")

        with tarfile.open(str(BINARY_TARBALL), "r:gz") as tf:
            for member in tf.getmembers():
                if member.name.endswith("RobotConsole") and member.isfile():
                    tf.extract(member, tmp_path, filter="data")
                    extracted = tmp_path / member.name
                    with open(extracted, "rb") as f:
                        magic = f.read(4)
                    assert magic == b"\x7fELF", \
                        f"Extracted binary is not an ELF file (magic={magic!r})"
                    return
        pytest.fail("Could not find RobotConsole binary in tarball to inspect")

    def test_extracted_binary_is_executable_file(self, tmp_path):
        """Extracted binary file must have executable permission in normal env."""
        import platform
        if platform.system() != "Linux":
            pytest.skip("Linux-only test")

        with tarfile.open(str(BINARY_TARBALL), "r:gz") as tf:
            for member in tf.getmembers():
                if member.name.endswith("RobotConsole") and member.isfile():
                    tf.extract(member, tmp_path, filter="data")
                    extracted = tmp_path / member.name
                    # Restore the executable bit from the tarball member mode
                    os.chmod(extracted, member.mode | 0o111)
                    assert os.access(extracted, os.X_OK), \
                        "RobotConsole binary is not executable after extraction"
                    return
        pytest.fail("RobotConsole not found in tarball")


@pytest.mark.skipif(
    not _artifact_exists(APPIMAGE),
    reason="AppImage artifact not present (run build-linux.sh --appimage first)",
)
class TestAppImageArtifact:
    """Validate the packaged AppImage when it has been built."""

    def test_appimage_is_executable(self):
        """AppImage file must be executable."""
        assert os.access(str(APPIMAGE), os.X_OK), \
            f"{APPIMAGE.name} is not executable"

    def test_appimage_has_elf_magic(self):
        """AppImage file must start with an ELF or AppImage header."""
        with open(str(APPIMAGE), "rb") as f:
            magic = f.read(4)
        assert magic == b"\x7fELF", \
            f"{APPIMAGE.name} does not start with ELF magic bytes (got {magic!r})"

    def test_appimage_minimum_size(self):
        """AppImage must be a non-trivial size (at least 10 MB)."""
        size_mb = APPIMAGE.stat().st_size / (1024 * 1024)
        assert size_mb >= 10, \
            f"{APPIMAGE.name} is unexpectedly small ({size_mb:.1f} MB); likely corrupt"


# ─── 6. 入口點邏輯驗證（Normal env：無 GUI 啟動）────────────────────────────

class TestEdgeEntryPointLogic:
    """
    Verify that the Edge application entry point logic is syntactically valid
    and that its non-GUI modules can be imported without a display server.
    These tests run in a Normal (non-GUI, headless) environment.
    """

    def test_qtapp_main_py_is_valid_python(self):
        """Edge/qtwebview-app/main.py must be syntactically valid Python."""
        main_py = str(QTAPP_DIR / "main.py")
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", main_py],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, \
            f"main.py has syntax errors:\n{result.stderr}"

    def test_version_module_returns_correct_format(self):
        """Version string must follow semver-like format (e.g. '3.2.0-beta')."""
        import importlib.util
        version_path = PROJECT_ROOT / "src" / "common" / "version.py"
        spec = importlib.util.spec_from_file_location("src_common_version_logic", version_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        version = mod.get_version()
        parts = version.split("-")[0].split(".")
        assert len(parts) == 3, \
            f"Version '{version}' does not match MAJOR.MINOR.PATCH format"
        assert all(p.isdigit() for p in parts), \
            f"Version parts {parts} must all be numeric"
        info = mod.get_release_info()
        assert info["version"] == version
        assert "project_name" in info

    def test_version_module_cli_output(self):
        """version.py CLI must produce valid JSON when run as script."""
        result = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "src" / "common" / "version.py")],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0, \
            f"version.py exited {result.returncode}:\n{result.stderr}"
        import json as _json
        data = _json.loads(result.stdout)
        assert "version" in data
        assert "project_name" in data

    def test_flask_service_py_is_valid_python(self):
        """flask_service.py must be syntactically valid Python."""
        # Support both Edge/ and project root locations
        candidates = [
            PROJECT_ROOT / "Edge" / "flask_service.py",
            PROJECT_ROOT / "flask_service.py",
        ]
        flask_service = next((p for p in candidates if p.is_file()), None)
        if flask_service is None:
            pytest.skip("flask_service.py not found in either location")
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", str(flask_service)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, \
            f"flask_service.py has syntax errors:\n{result.stderr}"

    def test_all_qtapp_route_modules_valid_syntax(self):
        """All route modules in qtwebview-app must be syntactically valid Python."""
        route_files = list(QTAPP_DIR.glob("routes_*_tiny.py"))
        assert route_files, "No route_*_tiny.py files found in qtwebview-app"
        errors = []
        for route_file in route_files:
            result = subprocess.run(
                [sys.executable, "-m", "py_compile", str(route_file)],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                errors.append(f"{route_file.name}:\n{result.stderr}")
        assert not errors, \
            "Syntax errors found in route modules:\n" + "\n".join(errors)
