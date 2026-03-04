#!/usr/bin/env python3
"""
Executor Batch CLI

對 Executor (Robot-Console) 層的批次動作執行 CLI 入口。
讀取 JSON 批次檔案，以 JSON-RPC POST 到本地機器人控制器
（`http://localhost:9030/`），與 ActionExecutor._send_request 採用
相同的請求格式（jsonrpc 2.0）與連線逾時設定。

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

import requests

# 將 Executor 目錄加入路徑
sys.path.insert(0, str(Path(__file__).parent))

from action_executor import actions as ACTION_MAP  # noqa: E402
from config import ExecutorConfig  # noqa: E402

logger = logging.getLogger(__name__)

# 本地控制器端點（與 ActionExecutor._send_request 一致）
_CONTROLLER_URL = "http://localhost:9030/"
_CONTROLLER_HEADERS = {"deviceid": "1732853986186"}


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


def _send_action(name: str) -> bool:
    """以 JSON-RPC 2.0 格式呼叫本地機器人控制器

    採用與 ActionExecutor._send_request 相同的端點、header 和請求格式。

    Args:
        name: 動作名稱（必須存在於 ACTION_MAP 中）

    Returns:
        True 表示成功，False 表示失敗
    """
    if name not in ACTION_MAP:
        logger.error("Unknown action '%s' — not found in ACTION_MAP", name)
        return False

    action_cfg = ACTION_MAP[name]
    method, count = action_cfg["action"][0], action_cfg["action"][1]

    payload = {
        "id": "1732853986186",
        "jsonrpc": "2.0",
        "method": method,
        "params": [count],
    }

    try:
        resp = requests.post(
            _CONTROLLER_URL,
            headers=_CONTROLLER_HEADERS,
            json=payload,
            timeout=ExecutorConfig.EXECUTION_TIMEOUT,
        )
        resp.raise_for_status()
        logger.debug("Controller response: %s", resp.json())
        return True
    except requests.exceptions.HTTPError as exc:
        logger.error("HTTP error for action '%s': %s", name, exc)
    except requests.exceptions.ConnectionError as exc:
        logger.error("Connection error for action '%s': %s", name, exc)
    except requests.exceptions.Timeout:
        logger.error("Timeout after %ss for action '%s'", ExecutorConfig.EXECUTION_TIMEOUT, name)
    except requests.exceptions.RequestException as exc:
        logger.error("Request failed for action '%s': %s", name, exc)
    return False


def run_batch(action_list: list, dry_run: bool = False) -> int:
    """執行批次動作

    Args:
        action_list: 動作清單
        dry_run: 若為 True，僅列印動作而不實際執行

    Returns:
        失敗動作數量（0 表示全部成功）
    """
    failed = 0
    total = len(action_list)
    logger.info("Starting batch: %d action(s), dry_run=%s", total, dry_run)

    for idx, action in enumerate(action_list, 1):
        name = action if isinstance(action, str) else action.get('action', str(action))
        if dry_run:
            logger.info("[%d/%d] DRY-RUN: %s", idx, total, name)
            continue

        logger.info("[%d/%d] Executing: %s", idx, total, name)
        if _send_action(name):
            logger.info("[%d/%d] OK: %s", idx, total, name)
        else:
            logger.error("[%d/%d] FAILED: %s", idx, total, name)
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

    action_list = load_batch(args.file)
    failed = run_batch(action_list, dry_run=args.dry_run)
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()

