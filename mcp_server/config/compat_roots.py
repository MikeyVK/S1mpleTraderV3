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


def get_candidate_config_roots(preferred_root: Path | str | None = None) -> list[Path]:
    """Return workspace-first candidate .st3 roots used by runtime config resolution."""
    return _iter_candidate_config_roots(preferred_root)


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


def resolve_config_root(
    preferred_root: Path | str | None = None,
    explicit_root: Path | str | None = None,
    required_files: Iterable[str] = (),
) -> Path:
    """Resolve one authoritative .st3 config root for runtime and tests."""
    if explicit_root is not None:
        explicit_candidate = _normalize_workspace_root(explicit_root)
        if explicit_candidate.exists() and all(
            (explicit_candidate / file_name).exists() for file_name in required_files
        ):
            return explicit_candidate
        missing = [file_name for file_name in required_files if not (explicit_candidate / file_name).exists()]
        if missing:
            missing_text = ", ".join(str(file_name) for file_name in missing)
            raise FileNotFoundError(
                f"Explicit config_root is missing required files: {missing_text} ({explicit_candidate})"
            )
        raise FileNotFoundError(f"Explicit config_root does not exist: {explicit_candidate}")

    compatible_root = find_compatible_config_root(
        preferred_root=preferred_root,
        required_files=required_files,
    )
    if compatible_root is None:
        raise FileNotFoundError("Could not locate a compatible .st3 config directory")
    return compatible_root
