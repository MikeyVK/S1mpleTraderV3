"""Helpers for resolving the canonical ST3 YAML config root."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

_CANONICAL_CONFIG_DIR = Path(".st3") / "config"


def normalize_config_root(path: Path | str) -> Path:
    """Normalize a workspace, .st3, or .st3/config path to the best available config dir.

    Canonical .st3/config remains authoritative. During the staged C_LOADER migration,
    callers may still point at a legacy .st3 root in hermetic tests or temporary workspaces.
    When the canonical directory does not exist yet but the legacy directory does, preserve
    the legacy root so wrapper contracts remain coherent until C_LOADER.4 removes them.
    """
    candidate = Path(path).resolve()

    if candidate.name == "config" and candidate.parent.name == ".st3":
        legacy_candidate = candidate.parent
        if candidate.exists() or not legacy_candidate.exists():
            return candidate
        return legacy_candidate

    if candidate.name == ".st3":
        canonical_candidate = candidate / "config"
        if canonical_candidate.exists() or not candidate.exists():
            return canonical_candidate
        return candidate

    legacy_candidate = candidate / ".st3"
    canonical_candidate = legacy_candidate / "config"
    if canonical_candidate.exists() or not legacy_candidate.exists():
        return canonical_candidate
    return legacy_candidate


def normalize_config_file_path(path: Path | str) -> Path:
    """Rewrite legacy .st3/<name>.yaml paths to the best available config file path.

    Prefer the canonical .st3/config location when it exists. If only the legacy file exists,
    keep using that legacy path until the final compatibility cleanup cycle removes it.
    """
    candidate = Path(path)
    if candidate.suffix != ".yaml":
        return candidate

    if candidate.parent.name == "config" and candidate.parent.parent.name == ".st3":
        legacy_candidate = candidate.parent.parent / candidate.name
        if candidate.exists() or not legacy_candidate.exists():
            return candidate
        return legacy_candidate

    if candidate.parent.name == ".st3":
        canonical_candidate = candidate.parent / "config" / candidate.name
        if canonical_candidate.exists() or not candidate.exists():
            return canonical_candidate
        return candidate

    return candidate


def _iter_candidate_config_roots(preferred_root: Path | str | None = None) -> list[Path]:
    candidates: list[Path] = []
    if preferred_root is not None:
        candidates.append(normalize_config_root(preferred_root))

    candidates.append(normalize_config_root(Path.cwd()))
    candidates.append(normalize_config_root(Path(__file__).resolve().parents[2]))

    unique_candidates: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        unique_candidates.append(candidate)
    return unique_candidates


def get_candidate_config_roots(preferred_root: Path | str | None = None) -> list[Path]:
    """Return workspace-first candidate config dirs used by runtime resolution."""
    return _iter_candidate_config_roots(preferred_root)


def find_compatible_config_root(
    preferred_root: Path | str | None = None,
    required_files: Iterable[str] = (),
) -> Path | None:
    """Find a usable ST3 config directory, preferring canonical then legacy compatibility."""
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
    """Find one compatible config file, preferring the caller workspace before fallbacks."""
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
    """Resolve one authoritative ST3 config root for runtime and tests."""
    if explicit_root is not None:
        explicit_candidate = normalize_config_root(explicit_root)
        if explicit_candidate.exists() and all(
            (explicit_candidate / file_name).exists() for file_name in required_files
        ):
            return explicit_candidate
        missing = [
            file_name
            for file_name in required_files
            if not (explicit_candidate / file_name).exists()
        ]
        if missing:
            missing_text = ", ".join(str(file_name) for file_name in missing)
            raise FileNotFoundError(
                "Explicit config_root is missing required files: "
                f"{missing_text} ({explicit_candidate})"
            )
        raise FileNotFoundError(f"Explicit config_root does not exist: {explicit_candidate}")

    compatible_root = find_compatible_config_root(
        preferred_root=preferred_root,
        required_files=required_files,
    )
    if compatible_root is None:
        raise FileNotFoundError("Could not locate a compatible ST3 config directory")
    return compatible_root
