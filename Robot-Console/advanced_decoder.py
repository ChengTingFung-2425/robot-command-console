"""Advanced command decoder.

This module provides a small, pluggable decoder that converts high-level
advanced commands into sequences of base action names that the ActionExecutor
understands. By default it supports a local "sequence" style payload, but it
also supports calling an external MCP expansion API if configured in
`settings.yaml` (e.g. POST /api/advanced_commands/expand).

The decoder API is intentionally small and synchronous to keep integration
simple for this repo. It returns a list of base action names (strings).
"""
from typing import Any, Dict, List, Optional
import logging
import requests

logger = logging.getLogger(__name__)


class AdvancedDecoder:
    def __init__(self, mcp_base_url: Optional[str] = None, timeout: float = 2.0) -> None:
        """Create an AdvancedDecoder.

        Args:
            mcp_base_url: if provided, decoder will attempt to POST the advanced
                command to MCP at {mcp_base_url}/api/advanced_commands/expand to
                receive an expanded list of base actions.
        """
        self.mcp_base_url = mcp_base_url
        self.timeout = timeout

    def decode(self, payload: Dict[str, Any]) -> List[str]:
        """Decode an advanced command payload into a list of base action names.

        Expected local payload formats supported:
        - { "type": "sequence", "steps": [ {"action": "go_forward"}, ... ] }
        - { "toolName": "go_forward" } (treated as single base action)

        If MCP base URL is configured, the payload will first be sent to MCP for
        authoritative expansion. On failure, decoder falls back to local decoding.
        """
        # If explicit simple tool invocation
        if isinstance(payload, dict) and payload.get("toolName"):
            return [payload["toolName"]]

        # Try MCP expansion if configured
        if self.mcp_base_url:
            try:
                url = f"{self.mcp_base_url.rstrip('/')}/api/advanced_commands/expand"
                resp = requests.post(url, json=payload, timeout=self.timeout)
                resp.raise_for_status()
                data = resp.json()
                # Expecting { "actions": ["go_forward", "turn_left", ...] }
                actions = data.get("actions")
                if isinstance(actions, list) and all(isinstance(a, str) for a in actions):
                    return actions
                logger.warning("MCP expand returned unexpected shape, falling back to local decode")
            except Exception as e:
                logger.warning("MCP expansion failed: %s; falling back to local decode", e)

        # Local fallback decoding: support sequence typed payloads
        if isinstance(payload, dict) and payload.get("type") == "sequence":
            steps = payload.get("steps", [])
            result: List[str] = []
            for s in steps:
                if isinstance(s, dict) and s.get("action"):
                    result.append(s["action"])
            return result

        # Unknown format — return empty list to indicate nothing decoded
        logger.debug("AdvancedDecoder: unknown payload format: %s", payload)
        return []
