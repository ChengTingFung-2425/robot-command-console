"""
Result Exporter

輸出批次執行結果到不同格式（JSON/CSV/文字）。
"""

import csv
import json
import logging
from pathlib import Path
from typing import Optional

from .models import BatchResult

logger = logging.getLogger(__name__)


class ResultExporter:
    """
    結果輸出器

    支援的格式：
    - JSON (.json)
    - CSV (.csv)
    - Text (.txt)
    """

    def __init__(self):
        """初始化結果輸出器"""
        pass

    def export(
        self,
        result: BatchResult,
        output_path: str,
        format: Optional[str] = None
    ):
        """
        根據檔案副檔名自動選擇輸出格式

        Args:
            result: 批次執行結果
            output_path: 輸出檔案路徑
            format: 強制指定格式（可選），若不指定則根據副檔名判斷
        """
        path = Path(output_path)

        # 確保目錄存在
        path.parent.mkdir(parents=True, exist_ok=True)

        # 決定格式
        if format:
            fmt = format.lower()
        else:
            suffix = path.suffix.lower()
            fmt = suffix[1:] if suffix else "json"

        # 輸出
        if fmt == "json":
            self.export_json(result, output_path)
        elif fmt == "csv":
            self.export_csv(result, output_path)
        elif fmt in ["txt", "text"]:
            self.export_text(result, output_path)
        else:
            raise ValueError(f"Unsupported format: {fmt}")

    def export_json(self, result: BatchResult, output_path: str):
        """
        輸出為 JSON 格式

        Args:
            result: 批次執行結果
            output_path: 輸出檔案路徑
        """
        logger.info(f"Exporting JSON result to: {output_path}")

        data = result.to_dict()

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info("JSON result exported successfully")

    def export_csv(self, result: BatchResult, output_path: str):
        """
        輸出為 CSV 格式（僅包含指令結果）

        Args:
            result: 批次執行結果
            output_path: 輸出檔案路徑
        """
        logger.info(f"Exporting CSV result to: {output_path}")

        fieldnames = [
            "command_id",
            "trace_id",
            "robot_id",
            "action",
            "status",
            "start_time",
            "end_time",
            "duration_ms",
            "error",
            "retry_count"
        ]

        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for cmd_result in result.commands:
                row = {
                    "command_id": cmd_result.command_id,
                    "trace_id": cmd_result.trace_id,
                    "robot_id": cmd_result.robot_id,
                    "action": cmd_result.action,
                    "status": cmd_result.status.value,
                    "start_time": cmd_result.start_time.isoformat(),
                    "end_time": cmd_result.end_time.isoformat() if cmd_result.end_time else "",
                    "duration_ms": cmd_result.duration_ms or "",
                    "error": cmd_result.error or "",
                    "retry_count": cmd_result.retry_count,
                }
                writer.writerow(row)

        logger.info("CSV result exported successfully")

    def export_text(self, result: BatchResult, output_path: str):
        """
        輸出為純文字格式（人類可讀的報告）

        Args:
            result: 批次執行結果
            output_path: 輸出檔案路徑
        """
        logger.info(f"Exporting text result to: {output_path}")

        lines = []

        # 標題
        lines.append("=" * 80)
        lines.append(f"Batch Execution Report: {result.batch_id}")
        lines.append("=" * 80)
        lines.append("")

        # 摘要資訊
        lines.append("Summary:")
        lines.append(f"  Status: {result.status.value}")
        lines.append(f"  Start Time: {result.start_time.isoformat()}")
        if result.end_time:
            lines.append(f"  End Time: {result.end_time.isoformat()}")
        if result.duration_ms:
            duration_sec = result.duration_ms / 1000
            mins = int(duration_sec // 60)
            secs = int(duration_sec % 60)
            lines.append(f"  Duration: {mins:02d}:{secs:02d} ({result.duration_ms}ms)")
        lines.append("")

        # 統計資訊
        lines.append("Statistics:")
        lines.append(f"  Total Commands: {result.total_commands}")
        lines.append(f"  Successful: {result.successful}")
        lines.append(f"  Failed: {result.failed}")
        lines.append(f"  Timeout: {result.timeout}")
        lines.append(f"  Cancelled: {result.cancelled}")

        if result.total_commands > 0:
            success_rate = (result.successful / result.total_commands) * 100
            lines.append(f"  Success Rate: {success_rate:.1f}%")

        lines.append("")

        # 詳細指令結果
        lines.append("Command Results:")
        lines.append("-" * 80)

        for cmd_result in result.commands:
            status_icon = "✓" if cmd_result.status.value == "success" else "✗"
            duration_str = f"{cmd_result.duration_ms}ms" if cmd_result.duration_ms else "N/A"

            lines.append(
                f"{status_icon} [{cmd_result.status.value.upper()}] "
                f"{cmd_result.robot_id}:{cmd_result.action} "
                f"({duration_str})"
            )

            if cmd_result.error:
                lines.append(f"    Error: {cmd_result.error}")

            if cmd_result.retry_count > 0:
                lines.append(f"    Retries: {cmd_result.retry_count}")

        lines.append("")
        lines.append("=" * 80)

        # 寫入檔案
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines))

        logger.info("Text result exported successfully")

    def print_summary(self, result: BatchResult):
        """
        列印批次結果摘要到標準輸出

        Args:
            result: 批次執行結果
        """
        print(f"\n{'=' * 80}")
        print(f"Batch: {result.batch_id}")
        print(f"Status: {result.status.value}")
        print(f"{'=' * 80}")
        print(f"Total: {result.total_commands} | "
              f"Success: {result.successful} | "
              f"Failed: {result.failed} | "
              f"Timeout: {result.timeout}")

        if result.duration_ms:
            duration_sec = result.duration_ms / 1000
            mins = int(duration_sec // 60)
            secs = int(duration_sec % 60)
            print(f"Duration: {mins:02d}:{secs:02d}")

        print(f"{'=' * 80}\n")
