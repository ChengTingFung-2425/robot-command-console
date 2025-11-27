"""
Phase 2 結構驗證測試
驗證 Phase 2 重構後的目錄結構是否正確
"""
import sys
from pathlib import Path


def test_project_root_structure():
    """驗證專案根目錄結構"""
    project_root = Path(__file__).parent.parent

    # 必須存在的目錄
    required_dirs = [
        "electron-app",
        "src/robot_service",
        "src/common",           # 新增：共用模組
        "MCP",
        "Robot-Console",
        "WebUI",
        "tests",
        "config",
        "docs",
        "docs/plans",           # 已從根目錄移動到 docs/plans
        "docs/phase1",          # 新增：Phase 1 文檔
        "examples",
    ]

    for dir_path in required_dirs:
        full_path = project_root / dir_path
        assert full_path.exists(), f"目錄不存在: {dir_path}"
        assert full_path.is_dir(), f"不是目錄: {dir_path}"


def test_electron_app_structure():
    """驗證 Electron 應用目錄結構"""
    project_root = Path(__file__).parent.parent
    electron_dir = project_root / "electron-app"

    # Electron 必須的文件
    required_files = [
        "main.js",
        "preload.js",
        "package.json",
    ]

    for file_name in required_files:
        file_path = electron_dir / file_name
        assert file_path.exists(), f"文件不存在: electron-app/{file_name}"
        assert file_path.is_file(), f"不是文件: electron-app/{file_name}"

    # renderer 目錄
    renderer_dir = electron_dir / "renderer"
    assert renderer_dir.exists(), "renderer 目錄不存在"
    assert (renderer_dir / "index.html").exists(), "index.html 不存在"
    assert (renderer_dir / "renderer.js").exists(), "renderer.js 不存在"


def test_tests_directory():
    """驗證測試目錄結構"""
    project_root = Path(__file__).parent.parent
    tests_dir = project_root / "tests"

    # 確認舊的 Test 目錄不存在
    old_test_dir = project_root / "Test"
    assert not old_test_dir.exists(), "舊的 Test/ 目錄仍然存在，應該已重命名為 tests/"

    # 確認新的 tests 目錄存在且包含測試文件
    assert tests_dir.exists(), "tests/ 目錄不存在"

    test_files = list(tests_dir.glob("test_*.py"))
    assert len(test_files) > 0, "tests/ 目錄中沒有測試文件"

    # 驗證關鍵測試文件存在
    key_tests = [
        "test_auth_compliance.py",
        "test_command_handler_compliance.py",
        "test_contract_compliance.py",
        "test_queue_system.py",
    ]

    for test_file in key_tests:
        assert (tests_dir / test_file).exists(), f"測試文件不存在: {test_file}"


def test_config_directory():
    """驗證配置目錄結構"""
    project_root = Path(__file__).parent.parent
    config_dir = project_root / "config"

    assert config_dir.exists(), "config/ 目錄不存在"
    assert (config_dir / "README.md").exists(), "config/README.md 不存在"


def test_documentation_structure():
    """驗證文檔結構"""
    project_root = Path(__file__).parent.parent
    docs_dir = project_root / "docs"

    # Phase 2 關鍵文檔（已更新路徑）
    key_docs = [
        "architecture.md",
        "phase2/MIGRATION_GUIDE_PHASE2.md",
        "features/queue-architecture.md",
        "proposal.md",
    ]

    for doc_file in key_docs:
        doc_path = docs_dir / doc_file
        assert doc_path.exists(), f"文檔不存在: docs/{doc_file}"


def test_root_level_files():
    """驗證根層級關鍵文件"""
    project_root = Path(__file__).parent.parent

    root_files = [
        "README.md",
        "package.json",  # 新增的根層級 package.json
        "requirements.txt",
        "flask_service.py",
        "run_service_cli.py",
        "config.py",  # 保留向後相容
    ]

    for file_name in root_files:
        file_path = project_root / file_name
        assert file_path.exists(), f"根層級文件不存在: {file_name}"


def test_python_imports_work():
    """驗證 Python 導入路徑仍然有效"""
    project_root = Path(__file__).parent.parent

    # 確保 src 在 Python 路徑中
    src_path = str(project_root / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

    # 測試關鍵模組可以導入
    try:
        from robot_service.service_manager import ServiceManager
        assert ServiceManager is not None
    except ImportError as e:
        assert False, f"無法導入 robot_service: {e}"

    # 測試 MCP 模組
    mcp_path = str(project_root)
    if mcp_path not in sys.path:
        sys.path.insert(0, mcp_path)

    try:
        from MCP.auth_manager import AuthManager
        assert AuthManager is not None
    except ImportError as e:
        assert False, f"無法導入 MCP: {e}"


def test_common_module_imports():
    """驗證共用模組可以導入"""
    project_root = Path(__file__).parent.parent

    # 確保 src 在 Python 路徑中
    src_path = str(project_root / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

    # 測試 common 模組
    try:
        from common import utc_now, utc_now_iso, get_logger
        assert utc_now is not None
        assert utc_now_iso is not None
        assert get_logger is not None
    except ImportError as e:
        assert False, f"無法導入 common 模組: {e}"

    # 測試配置類別
    try:
        from common.config import EdgeConfig, ServerConfig, Environment
        assert EdgeConfig is not None
        assert ServerConfig is not None
        assert Environment is not None
    except ImportError as e:
        assert False, f"無法導入 common.config: {e}"


def test_no_old_references_in_root():
    """確認根目錄沒有舊的 Electron 文件"""
    project_root = Path(__file__).parent.parent

    # 這些文件應該已移到 electron-app/
    old_files = [
        "main.js",
        "preload.js",
    ]

    for file_name in old_files:
        old_path = project_root / file_name
        assert not old_path.exists(), f"舊文件仍在根目錄: {file_name}（應該移到 electron-app/）"

    # renderer 目錄應該已移動
    old_renderer = project_root / "renderer"
    assert not old_renderer.exists(), "舊的 renderer/ 目錄仍在根目錄（應該移到 electron-app/）"


if __name__ == "__main__":
    # 可以單獨運行此測試文件
    import pytest
    pytest.main([__file__, "-v"])
