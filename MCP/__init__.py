"""Compatibility package exposing Edge/MCP as top-level MCP."""

from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[1]
_EDGE_MCP_DIR = _REPO_ROOT / "Edge" / "MCP"
__path__ = [str(_EDGE_MCP_DIR)]
