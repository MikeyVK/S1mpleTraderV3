"""Baseline capture script for Cycle 0 GREEN phase.

Renders 5 representative templates with minimal context to create
immutable baseline outputs for regression validation in Cycle 4.

CRITICAL: Uses JinjaRenderer (not direct Jinja2) to ensure identical config.
"""

from pathlib import Path

from mcp_server.scaffolding.renderer import JinjaRenderer


def capture_baselines() -> None:
    """Capture baseline outputs from current JinjaRenderer implementation."""
    baselines_dir = Path("tests/baselines")
    baselines_dir.mkdir(parents=True, exist_ok=True)

    # Use JinjaRenderer to ensure identical config (trim_blocks, lstrip_blocks, etc.)
    renderer = JinjaRenderer(template_dir=Path("mcp_server/scaffolding/templates"))

    # Baseline 1: DTO
    print("Capturing DTO baseline...")
    dto_output = renderer.render(
        "concrete/dto.py.jinja2",
        # tier0
        artifact_type="dto",
        version_hash="baseline_v1",
        timestamp="2026-02-13T14:30:00Z",
        output_path="tests/baselines/baseline_dto.py",
        format="python",
        # tier1
        name="BaselineTestDTO",
        layer="dtos",
        dependencies=[],
        description="Test DTO for baseline capture",
        # dto-specific
        fields=[
            {"name": "id", "type": "str", "description": "Identifier"},
            {"name": "value", "type": "int", "description": "Test value"},
        ],
        validators=[],
        examples=["BaselineTestDTO(id='test', value=42)"],
        frozen=True,
    )
    (baselines_dir / "baseline_dto.py").write_text(dto_output, encoding="utf-8")
    print(f"  ✅ Saved {len(dto_output)} bytes")

    # Baseline 2: Worker
    print("Capturing Worker baseline...")
    worker_output = renderer.render(
        "concrete/worker.py.jinja2",
        # tier0
        artifact_type="worker",
        version_hash="baseline_v1",
        timestamp="2026-02-13T14:30:00Z",
        output_path="tests/baselines/baseline_worker.py",
        format="python",
        # tier1
        name="BaselineTestWorker",
        layer="workers",
        dependencies=["logging"],
        description="Test worker for baseline capture",
        # worker-specific
        input_dto="BaselineInputDTO",
        output_dto="BaselineOutputDTO",
        responsibilities=["Process test data"],
    )
    (baselines_dir / "baseline_worker.py").write_text(worker_output, encoding="utf-8")
    print(f"  ✅ Saved {len(worker_output)} bytes")

    # Baseline 3: Tool
    print("Capturing Tool baseline...")
    tool_output = renderer.render(
        "concrete/tool.py.jinja2",
        # tier0
        artifact_type="tool",
        version_hash="baseline_v1",
        timestamp="2026-02-13T14:30:00Z",
        output_path="tests/baselines/baseline_tool.md",
        format="python",
        # tier1
        name="baseline_test_tool",
        layer="tools",
        dependencies=[],
        description="Test tool for baseline capture",
        # tool-specific
        input_schema={"type": "object", "properties": {}},
        output_format="json",
        responsibilities=["Perform test operation"],
    )
    (baselines_dir / "baseline_tool.md").write_text(tool_output, encoding="utf-8")
    print(f"  ✅ Saved {len(tool_output)} bytes")

    # Baseline 4: Research
    print("Capturing Research baseline...")
    research_output = renderer.render(
        "concrete/research.md.jinja2",
        # tier0
        artifact_type="research",
        version_hash="baseline_v1",
        timestamp="2026-02-13T14:30:00Z",
        output_path="tests/baselines/baseline_research.md",
        format="markdown",
        # tier1
        title="Baseline Test Research",
        status="Draft",
        phase="Research",
        purpose="Test research document for baseline capture",
        scope_in="Baseline output validation",
        scope_out="Actual research work",
        prerequisites=[],
        related_docs=[],
        # tier2
        frontmatter={"title": "Baseline Test Research", "type": "research"},
    )
    (baselines_dir / "baseline_research.md").write_text(research_output, encoding="utf-8")
    print(f"  ✅ Saved {len(research_output)} bytes")

    # Baseline 5: Planning
    print("Capturing Planning baseline...")
    planning_output = renderer.render(
        "concrete/planning.md.jinja2",
        # tier0
        artifact_type="planning",
        version_hash="baseline_v1",
        timestamp="2026-02-13T14:30:00Z",
        output_path="tests/baselines/baseline_planning.md",
        format="markdown",
        # tier1
        title="Baseline Test Planning",
        status="Draft",
        phase="Planning",
        purpose="Test planning document for baseline capture",
        scope_in="Baseline output validation",
        scope_out="Actual planning work",
        prerequisites=[],
        related_docs=[],
        # tier2
        frontmatter={"title": "Baseline Test Planning", "type": "planning"},
    )
    (baselines_dir / "baseline_planning.md").write_text(planning_output, encoding="utf-8")
    print(f"  ✅ Saved {len(planning_output)} bytes")

    print("\n✅ All 5 baselines captured successfully using JinjaRenderer")


if __name__ == "__main__":
    capture_baselines()
