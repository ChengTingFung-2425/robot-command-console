"""
自動化測試腳本
支援不同測試模式與環境配置
"""

import argparse
import os
import subprocess
import sys
from typing import List, Optional


class TestRunner:
    """測試執行器"""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    def run_command(self, cmd: List[str], env: Optional[dict] = None) -> int:
        """執行命令並返回退出碼"""
        if self.verbose:
            print(f"Running: {' '.join(cmd)}")

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env={**os.environ, **(env or {})}
        )

        for line in iter(process.stdout.readline, b''):
            print(line.decode(), end='')

        process.wait()
        return process.returncode

    def run_unit_tests(self, with_coverage: bool = False) -> int:
        """執行單元測試"""
        print("\n" + "=" * 60)
        print("Running Unit Tests (without RabbitMQ)")
        print("=" * 60 + "\n")

        cmd = [
            "python3", "-m", "pytest",
            "tests/",
            "-v",
            "-m", "not integration",
            "--tb=short"
        ]

        if with_coverage:
            cmd.extend([
                "--cov=src",
                "--cov-report=term-missing",
                "--cov-report=html:htmlcov"
            ])

        return self.run_command(cmd)

    def run_integration_tests(self, with_rabbitmq: bool = False) -> int:
        """執行整合測試"""
        print("\n" + "=" * 60)
        print(f"Running Integration Tests (RabbitMQ: {with_rabbitmq})")
        print("=" * 60 + "\n")

        cmd = [
            "python3", "-m", "pytest",
            "tests/test_rabbitmq_queue.py",
            "tests/test_queue_comparison.py",
            "-v",
            "--tb=short"
        ]

        env = {}
        if with_rabbitmq:
            env["TEST_WITH_RABBITMQ"] = "1"
            env["RABBITMQ_URL"] = os.getenv(
                "RABBITMQ_URL",
                "amqp://guest:guest@localhost:5672/"
            )

        return self.run_command(cmd, env=env)

    def run_all_tests(self, with_rabbitmq: bool = False, with_coverage: bool = False) -> int:
        """執行所有測試"""
        print("\n" + "=" * 60)
        print("Running All Tests")
        print("=" * 60 + "\n")

        cmd = [
            "python3", "-m", "pytest",
            "tests/",
            "-v",
            "--tb=short"
        ]

        env = {}
        if with_rabbitmq:
            env["TEST_WITH_RABBITMQ"] = "1"
            env["RABBITMQ_URL"] = os.getenv(
                "RABBITMQ_URL",
                "amqp://guest:guest@localhost:5672/"
            )

        if with_coverage:
            cmd.extend([
                "--cov=src",
                "--cov-report=term-missing",
                "--cov-report=html:htmlcov",
                "--cov-report=xml:coverage.xml"
            ])

        return self.run_command(cmd, env=env)

    def run_specific_tests(self, test_path: str, with_rabbitmq: bool = False) -> int:
        """執行特定測試"""
        print(f"\n{'=' * 60}")
        print(f"Running Specific Tests: {test_path}")
        print("=" * 60 + "\n")

        cmd = [
            "python3", "-m", "pytest",
            test_path,
            "-v",
            "--tb=short"
        ]

        env = {}
        if with_rabbitmq:
            env["TEST_WITH_RABBITMQ"] = "1"

        return self.run_command(cmd, env=env)

    def check_rabbitmq_availability(self) -> bool:
        """檢查 RabbitMQ 是否可用"""
        try:
            import aio_pika
            import asyncio

            async def check():
                url = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
                try:
                    connection = await aio_pika.connect_robust(url, timeout=5)
                    await connection.close()
                    return True
                except Exception:
                    return False

            return asyncio.run(check())
        except ImportError:
            print("Warning: aio-pika not installed, skipping RabbitMQ check")
            return False

    def lint_code(self) -> int:
        """執行代碼檢查"""
        print("\n" + "=" * 60)
        print("Running Code Linting")
        print("=" * 60 + "\n")

        cmd = [
            "python3", "-m", "flake8",
            "src/robot_service/queue/",
            "tests/test_rabbitmq_queue.py",
            "tests/test_queue_comparison.py",
            "--select=E,F,W",
            "--max-line-length=120",
            "--exclude=.venv,node_modules,__pycache__"
        ]

        return self.run_command(cmd)


def main():
    parser = argparse.ArgumentParser(description="Robot Service 自動化測試腳本")

    parser.add_argument(
        "mode",
        choices=["unit", "integration", "all", "specific", "lint"],
        help="測試模式"
    )

    parser.add_argument(
        "--with-rabbitmq",
        action="store_true",
        help="啟用 RabbitMQ 整合測試"
    )

    parser.add_argument(
        "--coverage",
        action="store_true",
        help="生成代碼覆蓋率報告"
    )

    parser.add_argument(
        "--test-path",
        type=str,
        help="特定測試路徑（僅用於 specific 模式）"
    )

    parser.add_argument(
        "--check-rabbitmq",
        action="store_true",
        help="檢查 RabbitMQ 可用性"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="詳細輸出"
    )

    args = parser.parse_args()

    runner = TestRunner(verbose=args.verbose)

    # 檢查 RabbitMQ（如果需要）
    if args.check_rabbitmq:
        print("Checking RabbitMQ availability...")
        if runner.check_rabbitmq_availability():
            print("✓ RabbitMQ is available")
        else:
            print("✗ RabbitMQ is not available")
            if args.with_rabbitmq:
                print("Warning: RabbitMQ tests will be skipped")
        print()

    # 執行測試
    exit_code = 0

    if args.mode == "unit":
        exit_code = runner.run_unit_tests(with_coverage=args.coverage)

    elif args.mode == "integration":
        exit_code = runner.run_integration_tests(with_rabbitmq=args.with_rabbitmq)

    elif args.mode == "all":
        exit_code = runner.run_all_tests(
            with_rabbitmq=args.with_rabbitmq,
            with_coverage=args.coverage
        )

    elif args.mode == "specific":
        if not args.test_path:
            print("Error: --test-path required for specific mode")
            sys.exit(1)
        exit_code = runner.run_specific_tests(
            args.test_path,
            with_rabbitmq=args.with_rabbitmq
        )

    elif args.mode == "lint":
        exit_code = runner.lint_code()

    # 摘要
    print("\n" + "=" * 60)
    if exit_code == 0:
        print("✓ All tests passed!")
    else:
        print(f"✗ Tests failed with exit code {exit_code}")
    print("=" * 60)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
