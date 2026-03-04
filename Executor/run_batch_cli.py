#!/usr/bin/env python3
"""
Executor Batch CLI

對 Executor (Robot-Console) 層的批次動作執行 CLI 入口。
讀取 JSON 批次檔案，透過 ActionExecutor 依序執行每個機器人動作。

使用方式：
    python3 Executor/run_batch_cli.py --file batch.json
    python3 Executor/run_batch_cli.py --file batch.json --dry-run
    python3 Executor/run_batch_cli.py --help
"""

import argparse
import json
import logging
import sys
from pathlib import Path

# 將 Executor 目錄加入路徑
sys.path.insert(0, str(Path(__file__).parent))

from config import ExecutorConfig  # noqa: E402

logger = logging.getLogger(__name__)


def setup_logging(level: str = 'INFO') -> None:
    """設定日誌"""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format='%(asctime)s %(levelname)s %(name)s: %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def load_batch(file_path: str) -> list:
    """從 JSON 檔案載入批次動作清單

    Args:
        file_path: JSON 批次檔案路徑

    Returns:
        動作清單 (list of dicts)

    Raises:
        SystemExit: 檔案不存在或格式錯誤
    """
    path = Path(file_path)
    if not path.is_file():
        logger.error("Batch file not found: %s", file_path)
        sys.exit(1)

    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as exc:
        logger.error("Invalid JSON in batch file: %s", exc)
        sys.exit(1)

    if isinstance(data, list):
        return data
    if isinstance(data, dict) and 'actions' in data:
        return data['actions']

    logger.error("Batch file must be a JSON array or an object with an 'actions' key")
    sys.exit(1)


def run_batch(actions: list, dry_run: bool = False) -> int:
    """執行批次動作

    Args:
        actions: 動作清單
        dry_run: 若為 True，僅列印動作而不實際執行

    Returns:
        失敗動作數量（0 表示全部成功）
    """
    failed = 0
    total = len(actions)
    logger.info("Starting batch: %d action(s), dry_run=%s", total, dry_run)

    for idx, action in enumerate(actions, 1):
        name = action if isinstance(action, str) else action.get('action', str(action))
        if dry_run:
            logger.info("[%d/%d] DRY-RUN: %s", idx, total, name)
            continue

        try:
            logger.info("[%d/%d] Executing: %s", idx, total, name)
            # 呼叫本地機器人控制器
            import urllib.request
            import urllib.error
            url = f"http://localhost:9030/action?name={name}"
            req = urllib.request.Request(url, method='POST')
            try:
                with urllib.request.urlopen(req, timeout=ExecutorConfig.EXECUTION_TIMEOUT) as resp:
                    status = resp.status
                if status == 200:
                    logger.info("[%d/%d] OK: %s", idx, total, name)
                else:
                    logger.warning("[%d/%d] Unexpected status %d for: %s", idx, total, status, name)
                    failed += 1
            except urllib.error.HTTPError as http_err:
                logger.error("[%d/%d] HTTP %d for: %s — %s", idx, total, http_err.code, name, http_err.reason)
                failed += 1
            except urllib.error.URLError as url_err:
                logger.error("[%d/%d] Network error for: %s — %s", idx, total, name, url_err.reason)
                failed += 1
        except Exception as exc:
            logger.error("[%d/%d] FAILED: %s — %s", idx, total, name, exc)
            failed += 1

    logger.info("Batch complete: %d/%d succeeded", total - failed, total)
    return failed


def parse_args() -> argparse.Namespace:
    """解析命令列參數"""
    parser = argparse.ArgumentParser(
        description='Executor Batch CLI — run a JSON batch of robot actions',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 Executor/run_batch_cli.py --file batch.json
  python3 Executor/run_batch_cli.py --file batch.json --dry-run
  python3 Executor/run_batch_cli.py --file batch.json --log-level DEBUG
        """,
    )
    parser.add_argument('--file', required=True, help='JSON batch file path')
    parser.add_argument(
        '--dry-run', action='store_true',
        help='Print actions without executing them',
    )
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level (default: INFO)',
    )
    return parser.parse_args()


def main() -> None:
    """CLI 入口點"""
    args = parse_args()
    setup_logging(args.log_level)

    actions = load_batch(args.file)
    failed = run_batch(actions, dry_run=args.dry_run)
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
