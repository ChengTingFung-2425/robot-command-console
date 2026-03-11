"""
Phase 2 結構驗證測試
驗證 Phase 2 重構後的目錄結構是否正確
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
SRC_PATH = str(PROJECT_ROOT / "src")
EDGE_PATH = str(PROJECT_ROOT / "Edge")

for path in [EDGE_PATH, SRC_PATH]:
    if path not in sys.path:
        sys.path.insert(0, path)


def test_project_root_structure():
    """驗證專案根目錄結構"""
    project_root = PROJECT_ROOT

    # 必須存在的目錄
    required_dirs = [
        "Cloud",
        "Edge",
        "Executor",
        "Edge/electron-app",
        "Edge/robot_service",
        "Edge/MCP",
        "Edge/WebUI",
        "src/common",           # 新增：共用模組
        "tests",
        "docs",
        "docs/plans",           # 已從根目錄移動到 docs/plans
        "docs/phase1",          # 新增：Phase 1 文檔
    ]

    for dir_path in required_dirs:
        full_path = project_root / dir_path
        assert full_path.exists(), f"目錄不存在: {dir_path}"
        assert full_path.is_dir(), f"不是目錄: {dir_path}"


def test_electron_app_structure():
    """驗證 Electron 應用目錄結構"""
    electron_dir = PROJECT_ROOT / "Edge" / "electron-app"

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
    project_root = PROJECT_ROOT
    tests_dir = project_root / "tests"

    # 確認舊的 Test 目錄不存在
    old_test_dir = project_root / "Test"
    assert not old_test_dir.exists(), "舊的 Test/ 目錄仍然存在，應該已重命名為 tests/"

    # 確認新的 tests 目錄存在且包含測試文件
    assert tests_dir.exists(), "tests/ 目錄不存在"

    # 測試文件現在在子目錄中 (phase1/, phase2/, phase3/, core/)
    test_files = list(tests_dir.glob("**/test_*.py"))
    assert len(test_files) > 0, "tests/ 目錄中沒有測試文件"

    # 驗證關鍵測試文件存在（現在在子目錄中）
    key_tests = [
        "core/test_auth_compliance.py",
        "core/test_command_handler_compliance.py",
        "core/test_contract_compliance.py",
        "phase2/test_queue_system.py",
    ]

    for test_file in key_tests:
        assert (tests_dir / test_file).exists(), f"測試文件不存在: {test_file}"


def test_config_directory():
    """驗證配置檔與 Edge 配置結構"""
    project_root = PROJECT_ROOT
    config_file = project_root / "config.py"
    edge_config = project_root / "Edge" / "config.py"

    assert config_file.exists(), "config.py 不存在"
    assert edge_config.exists(), "Edge/config.py 不存在"


def test_documentation_structure():
    """驗證文檔結構"""
    project_root = PROJECT_ROOT
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
    project_root = PROJECT_ROOT

    root_files = [
        "README.md",
        "package.json",  # 新增的根層級 package.json
        "run_tests.py",
        "config.py",  # 保留向後相容
    ]

    for file_name in root_files:
        file_path = project_root / file_name
        assert file_path.exists(), f"根層級文件不存在: {file_name}"

    module_requirements = [
        "Cloud/requirements.txt",
        "Edge/requirements.txt",
        "Executor/requirements.txt",
    ]

    for file_name in module_requirements:
        file_path = project_root / file_name
        assert file_path.exists(), f"模組依賴文件不存在: {file_name}"


def test_python_imports_work():
    """驗證 Python 導入路徑仍然有效"""
    # 測試關鍵模組可以導入
    try:
        from robot_service.service_manager import ServiceManager
        assert ServiceManager is not None
    except ImportError as e:
        assert False, f"無法導入 robot_service: {e}"

    try:
        from Edge.config import BaseConfig
        assert BaseConfig is not None
    except ImportError as e:
        assert False, f"無法導入 Edge config: {e}"


def test_common_module_imports():
    """驗證共用模組可以導入"""
    # 測試 common 模組
    try:
        from src.common import utc_now, utc_now_iso, get_logger
        assert utc_now is not None
        assert utc_now_iso is not None
        assert get_logger is not None
    except ImportError as e:
        assert False, f"無法導入 common 模組: {e}"

    # 測試配置類別
    try:
        from src.common.config import EdgeConfig, ServerConfig, Environment
        assert EdgeConfig is not None
        assert ServerConfig is not None
        assert Environment is not None
    except ImportError as e:
        assert False, f"無法導入 common.config: {e}"


def test_no_old_references_in_root():
    """確認根目錄沒有舊的 Electron 文件"""
    project_root = PROJECT_ROOT

    # 這些文件應該已移到 Edge/electron-app/
    old_files = [
        "main.js",
        "preload.js",
    ]

    for file_name in old_files:
        old_path = project_root / file_name
        assert not old_path.exists(), f"舊文件仍在根目錄: {file_name}（應該移到 Edge/electron-app/）"

    # renderer 目錄應該已移動
    old_renderer = project_root / "renderer"
    assert not old_renderer.exists(), "舊的 renderer/ 目錄仍在根目錄（應該移到 Edge/electron-app/）"


if __name__ == "__main__":
    # 可以單獨運行此測試文件
    import pytest
    pytest.main([__file__, "-v"])
