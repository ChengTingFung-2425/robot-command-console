#!/usr/bin/env python3
"""
整合驗證腳本
驗證 WebUI、MCP 和 Robot-Console 是否正確整合

此腳本會：
1. 檢查所有必要的檔案和模組
2. 驗證配置是否正確
3. 測試基本的整合功能
4. 生成驗證報告

使用方式：
    python3 verify_integration.py           # 完整驗證
    python3 verify_integration.py --quick   # 快速驗證（不啟動服務）
"""

import argparse
import asyncio
import importlib.util
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)-8s %(message)s'
)
logger = logging.getLogger(__name__)


class IntegrationVerifier:
    """整合驗證器"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.results: List[Tuple[str, bool, str]] = []
        self.errors: List[str] = []

    def verify_file_exists(self, rel_path: str, description: str) -> bool:
        """驗證檔案是否存在"""
        full_path = self.project_root / rel_path
        exists = full_path.exists()

        if exists:
            self._add_result(f"✅ {description}", True, f"找到: {rel_path}")
        else:
            self._add_result(f"❌ {description}", False, f"找不到: {rel_path}")
            self.errors.append(f"缺少檔案: {rel_path}")

        return exists

    def verify_module_imports(self, module_name: str, description: str) -> bool:
        """驗證模組是否可匯入"""
        try:
            spec = importlib.util.find_spec(module_name)
            can_import = spec is not None

            if can_import:
                self._add_result(f"✅ {description}", True, f"模組可用: {module_name}")
            else:
                self._add_result(f"❌ {description}", False, f"模組不可用: {module_name}")
                self.errors.append(f"無法匯入模組: {module_name}")

            return can_import
        except Exception as e:
            self._add_result(f"❌ {description}", False, f"檢查失敗: {e}")
            self.errors.append(f"模組檢查失敗: {module_name} - {e}")
            return False

    def verify_directory_structure(self) -> bool:
        """驗證目錄結構"""
        logger.info("\n📂 驗證目錄結構...")

        required_dirs = {
            "docs": "文件目錄",
            "MCP": "MCP 服務",
            "WebUI": "WebUI 服務",
            "Robot-Console": "Robot-Console",
            "src/common": "共用模組",
            "src/robot_service": "機器人服務",
            "tests": "測試目錄",
            "electron-app": "Electron 應用（Heavy 版本）",
            "qtwebview-app": "PyQt 應用（Tiny 版本）"
        }

        all_ok = True
        for dir_path, description in required_dirs.items():
            exists = self.verify_file_exists(dir_path, f"{description}目錄")
            all_ok = all_ok and exists

        return all_ok

    def verify_key_files(self) -> bool:
        """驗證關鍵檔案"""
        logger.info("\n📄 驗證關鍵檔案...")

        key_files = {
            "docs/INTEGRATION_GUIDE.md": "整合指南",
            "docs/architecture.md": "架構文件",
            "docs/proposal.md": "權威規格",
            "start_all_services.py": "整合啟動腳本",
            "unified_launcher_cli.py": "統一啟動器",
            "flask_service.py": "Flask 服務",
            "MCP/api.py": "MCP API",
            "MCP/start.py": "MCP 啟動腳本",
            "WebUI/microblog.py": "WebUI 應用",
            "Robot-Console/action_executor.py": "動作執行器",
            "Robot-Console/pubsub.py": "PubSub 客戶端",
            "tests/test_e2e_integration.py": "端到端測試",
            "src/common/shared_state.py": "共享狀態管理器",
            "src/robot_service/service_coordinator.py": "服務協調器",
            "src/robot_service/unified_launcher.py": "統一啟動器實作"
        }

        all_ok = True
        for file_path, description in key_files.items():
            exists = self.verify_file_exists(file_path, description)
            all_ok = all_ok and exists

        return all_ok

    def verify_python_dependencies(self) -> bool:
        """驗證 Python 依賴"""
        logger.info("\n📦 驗證 Python 依賴...")

        required_modules = {
            "flask": "Flask 框架",
            "aiohttp": "異步 HTTP 客戶端",
            "pytest": "測試框架（開發依賴）",
        }

        all_ok = True
        for module_name, description in required_modules.items():
            can_import = self.verify_module_imports(module_name, description)
            all_ok = all_ok and can_import

        return all_ok

    def verify_project_modules(self) -> bool:
        """驗證專案內部模組"""
        logger.info("\n🔧 驗證專案模組...")

        # 添加專案路徑
        sys.path.insert(0, str(self.project_root / "src"))
        sys.path.insert(0, str(self.project_root))

        project_modules = {
            "common.shared_state": "共享狀態管理器",
            "common.datetime_utils": "時間工具",
            "common.logging_utils": "日誌工具",
            "robot_service.service_coordinator": "服務協調器",
            "robot_service.unified_launcher": "統一啟動器",
            "robot_service.queue": "佇列系統",
            "robot_service.command_processor": "指令處理器"
        }

        all_ok = True
        for module_name, description in project_modules.items():
            can_import = self.verify_module_imports(module_name, description)
            all_ok = all_ok and can_import

        return all_ok

    def verify_configuration(self) -> bool:
        """驗證配置"""
        logger.info("\n⚙️  驗證配置...")

        all_ok = True

        # 檢查環境變數（提供預設值）
        env_vars = {
            "MCP_API_URL": ("MCP API 端點", "http://localhost:8000/api"),
            "PORT": ("Flask Service 埠號", "5000"),
            "MCP_API_PORT": ("MCP Service 埠號", "8000")
        }

        for var_name, (description, default) in env_vars.items():
            value = os.environ.get(var_name, default)
            self._add_result(
                f"✅ 環境變數 {var_name}",
                True,
                f"{description}: {value}"
            )

        return all_ok

    def verify_integration_docs(self) -> bool:
        """驗證整合文件內容"""
        logger.info("\n📚 驗證整合文件...")

        integration_guide = self.project_root / "docs" / "INTEGRATION_GUIDE.md"

        if not integration_guide.exists():
            self._add_result("❌ 整合指南", False, "檔案不存在")
            return False

        try:
            with open(integration_guide, 'r', encoding='utf-8') as f:
                content = f.read()

            required_sections = [
                "資料流向",
                "整合點",
                "資料契約",
                "啟動整合系統",
                "WebUI ↔ MCP",
                "MCP ↔ Robot-Console"
            ]

            all_ok = True
            for section in required_sections:
                if section in content:
                    self._add_result(f"✅ 整合指南包含「{section}」章節", True, "")
                else:
                    self._add_result(f"❌ 整合指南缺少「{section}」章節", False, "")
                    all_ok = False

            return all_ok

        except Exception as e:
            self._add_result("❌ 讀取整合指南", False, str(e))
            return False

    def _add_result(self, test_name: str, passed: bool, details: str):
        """記錄測試結果"""
        self.results.append((test_name, passed, details))
        if passed and details:
            logger.info(f"{test_name}")
        elif not passed:
            logger.error(f"{test_name}")
            if details:
                logger.error(f"  詳情: {details}")

    def generate_report(self) -> Dict:
        """生成驗證報告"""
        passed = sum(1 for _, p, _ in self.results if p)
        total = len(self.results)
        success_rate = (passed / total * 100) if total > 0 else 0

        report = {
            "summary": {
                "total_checks": total,
                "passed": passed,
                "failed": total - passed,
                "success_rate": f"{success_rate:.1f}%"
            },
            "details": [
                {
                    "test": name,
                    "passed": passed,
                    "details": details
                }
                for name, passed, details in self.results
            ],
            "errors": self.errors
        }

        return report

    def print_report(self):
        """輸出驗證報告"""
        report = self.generate_report()

        logger.info("\n" + "=" * 60)
        logger.info("📊 驗證報告")
        logger.info("=" * 60)
        logger.info(f"總檢查數: {report['summary']['total_checks']}")
        logger.info(f"通過: {report['summary']['passed']}")
        logger.info(f"失敗: {report['summary']['failed']}")
        logger.info(f"成功率: {report['summary']['success_rate']}")

        if self.errors:
            logger.info("\n" + "=" * 60)
            logger.info("⚠️  發現的問題")
            logger.info("=" * 60)
            for error in self.errors:
                logger.error(f"  • {error}")

        logger.info("\n" + "=" * 60)

        return report['summary']['failed'] == 0

    async def run_full_verification(self) -> bool:
        """執行完整驗證"""
        logger.info("🔍 開始完整整合驗證...\n")

        all_ok = True

        # 1. 目錄結構
        all_ok = self.verify_directory_structure() and all_ok

        # 2. 關鍵檔案
        all_ok = self.verify_key_files() and all_ok

        # 3. Python 依賴
        all_ok = self.verify_python_dependencies() and all_ok

        # 4. 專案模組
        all_ok = self.verify_project_modules() and all_ok

        # 5. 配置
        all_ok = self.verify_configuration() and all_ok

        # 6. 整合文件
        all_ok = self.verify_integration_docs() and all_ok

        # 生成報告
        success = self.print_report()

        return success

    async def run_quick_verification(self) -> bool:
        """執行快速驗證（不啟動服務）"""
        logger.info("🚀 開始快速整合驗證...\n")

        all_ok = True

        # 只檢查檔案和目錄
        all_ok = self.verify_directory_structure() and all_ok
        all_ok = self.verify_key_files() and all_ok
        all_ok = self.verify_integration_docs() and all_ok

        success = self.print_report()

        return success


def main():
    """主程式入口"""
    parser = argparse.ArgumentParser(
        description="驗證 WebUI/MCP/Robot-Console 整合狀態",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--quick',
        action='store_true',
        help='快速驗證（不檢查依賴和模組）'
    )

    parser.add_argument(
        '--output',
        type=str,
        help='輸出報告到 JSON 檔案'
    )

    args = parser.parse_args()

    # 取得專案根目錄
    project_root = Path(__file__).parent.absolute()

    # 建立驗證器
    verifier = IntegrationVerifier(project_root)

    # 執行驗證
    try:
        if args.quick:
            success = asyncio.run(verifier.run_quick_verification())
        else:
            success = asyncio.run(verifier.run_full_verification())

        # 輸出報告
        if args.output:
            report = verifier.generate_report()
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            logger.info(f"\n報告已儲存至: {args.output}")

        # 返回退出碼
        sys.exit(0 if success else 1)

    except Exception as e:
        logger.error(f"\n驗證過程發生錯誤: {e}", exc_info=True)
        sys.exit(2)


if __name__ == '__main__':
    main()
