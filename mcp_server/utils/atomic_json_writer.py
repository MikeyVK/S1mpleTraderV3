# mcp_server\utils\atomic_json_writer.py
# template=generic version=f35abd82 created=2026-03-12T15:02Z updated=
"""Atomic JSON file writer utilities."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class AtomicJsonWriter:
    """Write JSON payloads via temp file replacement."""

    def write_json(
        self,
        path: Path,
        payload: dict[str, Any],
        *,
        temp_name: str = ".tmp",
    ) -> None:
        """Write JSON data to a temp file and rename it into place."""
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.parent / temp_name
        content = json.dumps(payload, indent=2)
        temp_path.write_text(content, encoding="utf-8")
        temp_path.rename(path)
