"""Compatibility package exposing Edge/robot_service as src.robot_service."""

from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[2]
_EDGE_ROBOT_SERVICE_DIR = _REPO_ROOT / "Edge" / "robot_service"
__path__ = [str(_EDGE_ROBOT_SERVICE_DIR)]
