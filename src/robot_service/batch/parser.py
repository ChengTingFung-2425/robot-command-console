"""
Batch Parser

解析批次檔案（JSON/YAML/CSV）為 BatchSpec 物件。
"""

import csv
import json
import logging
from pathlib import Path
from typing import Dict, Any

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

from .models import BatchSpec, BatchCommand

logger = logging.getLogger(__name__)


class BatchParser:
    """
    批次解析器

    支援的格式：
    - JSON (.json)
    - YAML (.yaml, .yml) - 需要 PyYAML
    - CSV (.csv)
    """

    def __init__(self):
        """初始化批次解析器"""
        pass

    def parse_file(self, file_path: str) -> BatchSpec:
        """
        根據檔案副檔名自動選擇解析器

        Args:
            file_path: 批次檔案路徑

        Returns:
            解析後的 BatchSpec

        Raises:
            ValueError: 不支援的檔案格式
            FileNotFoundError: 檔案不存在
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"Batch file not found: {file_path}")

        suffix = path.suffix.lower()

        if suffix == ".json":
            return self.parse_json(file_path)
        elif suffix in [".yaml", ".yml"]:
            return self.parse_yaml(file_path)
        elif suffix == ".csv":
            return self.parse_csv(file_path)
        else:
            raise ValueError(f"Unsupported file format: {suffix}")

    def parse_json(self, file_path: str) -> BatchSpec:
        """
        解析 JSON 批次檔案

        Args:
            file_path: JSON 檔案路徑

        Returns:
            解析後的 BatchSpec
        """
        logger.info(f"Parsing JSON batch file: {file_path}")

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return self._parse_dict(data)

    def parse_yaml(self, file_path: str) -> BatchSpec:
        """
        解析 YAML 批次檔案

        Args:
            file_path: YAML 檔案路徑

        Returns:
            解析後的 BatchSpec

        Raises:
            ImportError: PyYAML 未安裝
        """
        if not YAML_AVAILABLE:
            raise ImportError(
                "PyYAML is required for YAML parsing. "
                "Install it with: pip install pyyaml"
            )

        logger.info(f"Parsing YAML batch file: {file_path}")

        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        return self._parse_dict(data)

    def parse_csv(self, file_path: str) -> BatchSpec:
        """
        解析 CSV 批次檔案

        CSV 格式：
        robot_id,action,params_json,priority,timeout_ms

        Args:
            file_path: CSV 檔案路徑

        Returns:
            解析後的 BatchSpec
        """
        logger.info(f"Parsing CSV batch file: {file_path}")

        commands = []

        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            for row in reader:
                # 解析參數 JSON
                params = {}
                params_json = row.get('params_json', '{}')
                if params_json:
                    try:
                        params = json.loads(params_json)
                    except json.JSONDecodeError as e:
                        logger.warning(f"Invalid params JSON in row: {e}")

                command = BatchCommand(
                    robot_id=row.get('robot_id', ''),
                    action=row.get('action', ''),
                    params=params,
                    priority=row.get('priority', 'normal'),
                    timeout_ms=int(row.get('timeout_ms', 10000)),
                )
                commands.append(command)

        # 從檔案名生成 batch_id
        batch_id = Path(file_path).stem

        return BatchSpec(
            batch_id=batch_id,
            description=f"Batch from CSV: {file_path}",
            commands=commands,
        )

    def parse_string(self, content: str, format: str = "json") -> BatchSpec:
        """
        解析字串內容

        Args:
            content: 批次檔案內容
            format: 格式 (json, yaml, csv)

        Returns:
            解析後的 BatchSpec
        """
        if format == "json":
            data = json.loads(content)
            return self._parse_dict(data)
        elif format == "yaml":
            if not YAML_AVAILABLE:
                raise ImportError("PyYAML is required for YAML parsing")
            data = yaml.safe_load(content)
            return self._parse_dict(data)
        elif format == "csv":
            # CSV 從字串解析較複雜，建議使用檔案
            raise NotImplementedError("CSV parsing from string is not supported")
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _parse_dict(self, data: Dict[str, Any]) -> BatchSpec:
        """
        從字典解析 BatchSpec

        Args:
            data: 批次資料字典

        Returns:
            解析後的 BatchSpec
        """
        return BatchSpec.from_dict(data)

    def validate(self, batch_spec: BatchSpec) -> bool:
        """
        驗證 BatchSpec 的有效性

        Args:
            batch_spec: 批次規格

        Returns:
            是否有效

        Raises:
            ValueError: 驗證失敗時拋出
        """
        # 驗證 batch_id
        if not batch_spec.batch_id:
            raise ValueError("batch_id is required")

        # 驗證至少有一個指令
        if not batch_spec.commands:
            raise ValueError("At least one command is required")

        # 驗證每個指令
        for i, cmd in enumerate(batch_spec.commands):
            if not cmd.robot_id:
                raise ValueError(f"Command {i}: robot_id is required")

            if not cmd.action:
                raise ValueError(f"Command {i}: action is required")

            if cmd.timeout_ms <= 0:
                raise ValueError(f"Command {i}: timeout_ms must be positive")

            if cmd.priority not in ["low", "normal", "high"]:
                raise ValueError(
                    f"Command {i}: priority must be one of: low, normal, high"
                )

        # 驗證執行選項
        opts = batch_spec.options
        if opts.retry_on_failure < 0:
            raise ValueError("retry_on_failure must be non-negative")

        if opts.retry_backoff_factor <= 0:
            raise ValueError("retry_backoff_factor must be positive")

        if opts.max_parallel <= 0:
            raise ValueError("max_parallel must be positive")

        logger.info(f"Batch validated: {batch_spec.batch_id}, "
                    f"{len(batch_spec.commands)} commands")

        return True
