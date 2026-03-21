"""Shared fixtures for copilot_orchestration subprocess smoke tests."""

import shutil
from pathlib import Path

import pytest

_WORKSPACE_ROOT = Path(__file__).parents[3]
_HOOKS_SRC = _WORKSPACE_ROOT / "src" / "copilot_orchestration" / "hooks"
_COPILOT_DIR = _WORKSPACE_ROOT / ".copilot"


@pytest.fixture()
def hook_workspace(tmp_path: Path) -> Path:
    """Minimal hermetic workspace for subprocess hook tests.

    Creates:
      tmp_path/pyproject.toml                         <- workspace sentinel
      tmp_path/.copilot/sub-role-requirements.yaml    <- config copy
      tmp_path/.copilot/                              <- state dir
      tmp_path/detect_sub_role.py                    <- hook script copy
      tmp_path/notify_compaction.py                  <- hook script copy
      tmp_path/stop_handover_guard.py                <- hook script copy

    Because the hook scripts use ``find_workspace_root(Path(__file__))`` to
    locate the workspace, running copies from tmp_path makes the state file
    land in ``tmp_path/.copilot/session-sub-role.json`` — fully isolated.
    """
    (tmp_path / "pyproject.toml").write_text("[project]\nname = \"test\"\n")

    copilot_dir = tmp_path / ".copilot"
    copilot_dir.mkdir()
    shutil.copy(
        _COPILOT_DIR / "sub-role-requirements.yaml",
        copilot_dir / "sub-role-requirements.yaml",
    )

    for script in [
        "detect_sub_role.py",
        "notify_compaction.py",
        "stop_handover_guard.py",
    ]:
        shutil.copy(_HOOKS_SRC / script, tmp_path / script)

    return tmp_path
