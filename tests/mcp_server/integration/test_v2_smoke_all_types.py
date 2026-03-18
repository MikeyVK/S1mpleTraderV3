# SCAFFOLD: integration_test:smoke135 | 2026-02-19T00:00:00Z
"""Integration Step 1: V2 pipeline smoke test for all 16 artifact types.

Validates that PYDANTIC_SCAFFOLDING_ENABLED=true produces non-empty output
for every type registered in _v2_context_registry. One parametrized test per type.

@module: tests.integration.test_v2_smoke_all_types
@layer: Test Infrastructure
@dependencies: mcp_server.managers.artifact_manager, mcp_server.config
@responsibilities:
  - E2E smoke: V2 pipeline → non-empty string output for all 16 types
  - Covers: 8 code, 5 doc, 3 tracking (ephemeral)
  - Does NOT assert file existence for ephemeral artifacts
"""

# Standard library
import shutil
from pathlib import Path

# Third-party
import pytest

# Project
from mcp_server.config.loader import ConfigLoader
from mcp_server.managers.artifact_manager import ArtifactManager

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent


@pytest.fixture(name="v2_manager")
def _v2_manager(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ArtifactManager:
    """ArtifactManager configured for V2 pipeline with production registry + templates.

    Setup:
    - Copies production .st3/artifacts.yaml into hermetic tmp workspace
    - Sets TEMPLATE_ROOT → production mcp_server/scaffolding/templates/
    - Changes CWD → tmp_path (so registry + ephemeral writes resolve there)
    - Enables PYDANTIC_SCAFFOLDING_ENABLED=true
    """
    # Enable V2 pipeline
    monkeypatch.setenv("PYDANTIC_SCAFFOLDING_ENABLED", "true")

    # Point template discovery to actual production templates
    template_root = _PROJECT_ROOT / "mcp_server" / "scaffolding" / "templates"
    monkeypatch.setenv("TEMPLATE_ROOT", str(template_root))

    # Hermetic workspace: copy production artifacts.yaml so registry loads correctly
    config_dir = tmp_path / ".st3" / "config"
    config_dir.mkdir(parents=True)
    artifacts_path = config_dir / "artifacts.yaml"
    shutil.copy(_PROJECT_ROOT / ".st3" / "config" / "artifacts.yaml", artifacts_path)

    # CWD → tmp_path: registry loads from tmp_path/.st3/config/artifacts.yaml,
    # ephemeral writes go to tmp_path/.st3/temp/ (not project root)
    monkeypatch.chdir(tmp_path)

    registry = ConfigLoader(artifacts_path.parent).load_artifact_registry_config(
        config_path=artifacts_path
    )
    return ArtifactManager(workspace_root=str(tmp_path), registry=registry)


# ---------------------------------------------------------------------------
# Smoke test cases
# ---------------------------------------------------------------------------
# Format: (artifact_type, context_kwargs, is_ephemeral, file_extension)
# output_path is always provided — for ephemeral types _validate_and_write ignores it
# and writes to .st3/temp/ instead (but it avoids DirectoryPolicyResolver call).

_SMOKE_CASES: list[tuple[str, dict, bool, str]] = [
    # --- Code artifacts ---
    (
        "dto",
        # Non-empty fields required: empty fields renders invalid Python
        # (V2 template issue with 0 fields — see test_dto_parity.py pytest.skip)
        {"dto_name": "SmokeDTO", "fields": ["id: str", "name: str"]},
        False,
        ".py",
    ),
    (
        "worker",
        {"name": "SmokeWorker", "layer": "platform"},
        False,
        ".py",
    ),
    (
        "tool",
        {"name": "SmokeTool"},
        False,
        ".py",
    ),
    (
        "schema",
        {"name": "SmokeSchema"},
        False,
        ".py",
    ),
    (
        "service",
        {"name": "SmokeService"},
        False,
        ".py",
    ),
    (
        "generic",
        {"name": "SmokeGeneric"},
        False,
        ".py",
    ),
    (
        "unit_test",
        {
            "module_under_test": "mcp_server.schemas.contexts.dto",
            "test_class_name": "TestSmokeDTOContext",
            # Provide imported_classes explicitly: default=[] would render
            # `from x import ` and produce invalid syntax.
            "imported_classes": ["DTOContext"],
        },
        False,
        ".py",
    ),
    (
        "integration_test",
        {
            "test_scenario": "smoke_flow",
            "test_class_name": "TestSmokeFlow",
        },
        False,
        ".py",
    ),
    # --- Document artifacts ---
    (
        "research",
        {
            "title": "Smoke Research",
            "problem_statement": "What needs investigating?",
            "goals": ["Validate V2 pipeline for research type"],
        },
        False,
        ".md",
    ),
    (
        "planning",
        {
            "title": "Smoke Planning",
            "summary": "Validate V2 pipeline for planning type",
            "tdd_cycles": ["RED: write failing test", "GREEN: implement", "REFACTOR: clean up"],
        },
        False,
        ".md",
    ),
    (
        "design",
        {
            "title": "Smoke Design",
            "status": "DRAFT",
            "version": "1.0",
            "problem_statement": "Validate V2 pipeline for design type",
            "requirements_functional": ["Must produce non-empty output"],
            "requirements_nonfunctional": ["Must complete within 5 seconds"],
            "decision": "Use V2 Pydantic pipeline",
            "rationale": "Type-safe context validation",
        },
        False,
        ".md",
    ),
    (
        "architecture",
        {
            "title": "Smoke Architecture",
            "concepts": ["V2 context schema validation", "Pydantic render contexts"],
        },
        False,
        ".md",
    ),
    (
        "reference",
        {
            "title": "Smoke Reference",
            "source_file": "mcp_server/schemas/contexts/dto.py",
            "test_file": "tests/unit/schemas/contexts/test_dto_context.py",
            "api_reference": [
                {"name": "DTOContext", "description": "DTO artifact context schema"},
            ],
        },
        False,
        ".md",
    ),
    # --- Tracking artifacts (ephemeral: write to .st3/temp/, not via fs_adapter) ---
    (
        "commit",
        {"type": "feat", "message": "add V2 smoke test coverage"},
        True,
        ".txt",
    ),
    (
        "pr",
        {
            "title": "Smoke PR",
            "changes": "Added V2 pipeline smoke tests for all 16 artifact types",
        },
        True,
        ".md",
    ),
    (
        "issue",
        {
            "title": "Smoke Issue",
            "problem": "V2 pipeline lacks integration smoke coverage for all types",
        },
        True,
        ".md",
    ),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "artifact_type,context_kwargs,_is_ephemeral,file_ext",
    _SMOKE_CASES,
    ids=[case[0] for case in _SMOKE_CASES],
)
async def test_v2_smoke_produces_nonempty_output(
    v2_manager: ArtifactManager,
    tmp_path: Path,
    artifact_type: str,
    context_kwargs: dict,
    _is_ephemeral: bool,
    file_ext: str,
) -> None:
    """V2 pipeline produces a non-empty string for every registered artifact type.

    Passing criteria:
    - result is a non-empty str
    - For file artifacts: output path exists on disk
    - For ephemeral: output path exists in .st3/temp/ (CWD-relative tmp_path)
    """
    # Provide explicit output_path for all types to bypass DirectoryPolicyResolver
    # (ephemeral types ignore this value in _validate_and_write, but it avoids resolver errors)
    output_path = str(tmp_path / f"smoke_{artifact_type}{file_ext}")

    result = await v2_manager.scaffold_artifact(
        artifact_type,
        output_path=output_path,
        **context_kwargs,
    )

    # Core assertion: V2 pipeline returns a non-empty string path
    assert isinstance(result, str), (
        f"[{artifact_type}] scaffold_artifact should return str, got {type(result).__name__}"
    )
    assert result.strip(), f"[{artifact_type}] scaffold_artifact returned empty string"

    # Verify output file exists on disk
    result_path = Path(result)
    assert result_path.exists(), f"[{artifact_type}] output file not found at {result_path}"
    assert result_path.is_file(), f"[{artifact_type}] output path is not a file: {result_path}"

    # Verify content is non-trivial (at least some chars)
    content = result_path.read_text(encoding="utf-8")
    assert len(content.strip()) > 0, f"[{artifact_type}] output file is empty: {result_path}"
