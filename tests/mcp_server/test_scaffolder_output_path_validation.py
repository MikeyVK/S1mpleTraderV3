# tests\test_scaffolder_output_path_validation.py
# template=unit_test version=3d15d309 created=2026-02-21T15:35Z updated=2026-02-21
"""
Unit tests for artifact_manager.scaffold_artifact() C2 output_path gate (Issue #239 C2).

Gate location: ArtifactManager.scaffold_artifact() (not TemplateScaffolder.validate()).
TemplateScaffolder.validate() is intentionally gate-free — it handles missing output_path
by constructing a safe default (name + extension). The gate lives at the API boundary.

RED phase: file artifact + no output_path → ValidationError with hint.
           ephemeral artifact + output_path=None → no C2 gate error.

@layer: Tests (Unit)
@dependencies: [pytest, mcp_server.managers.artifact_manager]
@responsibilities:
    - Test C2 gate in ArtifactManager.scaffold_artifact() for file vs ephemeral artifacts
    - Confirm ephemeral artifacts are unaffected by the gate
"""

# Standard library
import asyncio
from pathlib import Path
from unittest.mock import Mock

# Third-party
import pytest

# Project modules
from mcp_server.core.exceptions import ValidationError
from mcp_server.managers.artifact_manager import ArtifactManager


@pytest.fixture
def manager(tmp_path: Path) -> ArtifactManager:
    """ArtifactManager with mocked write_file to avoid real I/O."""
    mgr = ArtifactManager(workspace_root=str(tmp_path))
    mgr.fs_adapter.write_file = Mock()
    return mgr


class TestArtifactManagerOutputPathValidation:
    """Test suite for ArtifactManager C2 gate (Issue #239 C2)."""

    def test_file_artifact_empty_output_path_raises(self, manager: ArtifactManager) -> None:
        """scaffold_artifact with file artifact + output_path='' raises ValidationError."""
        with pytest.raises(ValidationError, match="output_path is required"):
            asyncio.run(
                manager.scaffold_artifact("dto", output_path="", dto_name="MyDto", fields=[])
            )

    def test_file_artifact_none_output_path_raises(self, manager: ArtifactManager) -> None:
        """scaffold_artifact with file artifact + output_path=None raises ValidationError."""
        with pytest.raises(ValidationError, match="output_path is required"):
            asyncio.run(manager.scaffold_artifact("dto", dto_name="MyDto", fields=[]))

    def test_file_artifact_error_hint_message(self, manager: ArtifactManager) -> None:
        """ValidationError hints contain 'output_path is required for file artifacts'."""
        with pytest.raises(ValidationError) as exc_info:
            asyncio.run(manager.scaffold_artifact("dto", dto_name="MyDto", fields=[]))

        hints = exc_info.value.hints or []
        assert any("output_path is required for file artifacts" in h for h in hints), (
            f"Expected hint about output_path, got: {hints}"
        )

    def test_file_artifact_valid_output_path_does_not_raise_c2(
        self, manager: ArtifactManager, tmp_path: Path
    ) -> None:
        """scaffold_artifact with file artifact + valid output_path does not fire C2 gate."""
        output_path = str(tmp_path / "my_dto.py")
        try:
            asyncio.run(
                manager.scaffold_artifact(
                    "dto", output_path=output_path, dto_name="MyDto", fields=[]
                )
            )
        except ValidationError as exc:
            assert "output_path is required" not in str(exc), (
                f"C2 gate should not fire when output_path is provided, got: {exc}"
            )
        except Exception:
            pass  # Other failures (template rendering, etc.) are acceptable

    def test_ephemeral_artifact_none_output_path_no_c2(self, manager: ArtifactManager) -> None:
        """scaffold_artifact with ephemeral artifact + no output_path does NOT fire C2 gate."""
        try:
            asyncio.run(
                manager.scaffold_artifact("commit", message="test: add feature", commit_type="feat")
            )
        except ValidationError as exc:
            assert "output_path is required" not in str(exc), (
                f"C2 gate must not fire for ephemeral artifacts, got: {exc}"
            )
        except Exception:
            pass  # Other failures are acceptable — C2 gate is the only concern here
