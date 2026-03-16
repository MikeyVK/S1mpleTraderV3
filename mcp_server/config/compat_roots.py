"""Helpers for resolving legacy-compatible .st3 config roots."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path


def _normalize_workspace_root(path: Path | str) -> Path:
    candidate = Path(path).resolve()
    if candidate.name == ".st3":
        return candidate
    return candidate / ".st3"


def _iter_candidate_config_roots(preferred_root: Path | str | None = None) -> list[Path]:
    candidates: list[Path] = []
    if preferred_root is not None:
        candidates.append(_normalize_workspace_root(preferred_root))

    candidates.append(_normalize_workspace_root(Path.cwd()))
    candidates.append(_normalize_workspace_root(Path(__file__).resolve().parents[2]))

    unique_candidates: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        unique_candidates.append(candidate)
    return unique_candidates


def find_compatible_config_root(
    preferred_root: Path | str | None = None,
    required_files: Iterable[str] = (),
) -> Path | None:
    """Find a usable .st3 directory for legacy callers."""
    required = tuple(required_files)
    for candidate in _iter_candidate_config_roots(preferred_root):
        if not candidate.exists():
            continue
        if all((candidate / file_name).exists() for file_name in required):
            return candidate

    return None


def find_compatible_config_file(
    file_name: str | Path,
    preferred_root: Path | str | None = None,
) -> Path | None:
    """Find one config file, preferring the caller workspace before global fallbacks."""
    relative_name = Path(file_name)
    for candidate in _iter_candidate_config_roots(preferred_root):
        config_file = candidate / relative_name
        if config_file.exists():
            return config_file
    return None
