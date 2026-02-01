# tests/mcp_server/scaffolding/test_task34_concrete_code_templates.py
# template=unit_test version=dev created=2026-02-01T00:00Z updated=
"""Task 3.4 regression tests for concrete CODE template composition.

Validates that concrete CODE templates:
- use Tier 3 pattern macro libraries via `{% import %}`
- set TEMPLATE_METADATA enforcement to GUIDELINE

These tests intentionally inspect template SOURCE (not rendered output).
"""

from __future__ import annotations

from pathlib import Path

import pytest


TEMPLATE_ROOT = (
    Path(__file__).parent.parent.parent.parent
    / "mcp_server"
    / "scaffolding"
    / "templates"
    / "concrete"
)


@pytest.mark.parametrize(
    ("template_name", "required_imports"),
    [
        (
            "worker.py.jinja2",
            [
                'import "tier3_pattern_python_async.jinja2"',
                'import "tier3_pattern_python_lifecycle.jinja2"',
                'import "tier3_pattern_python_error.jinja2"',
                'import "tier3_pattern_python_logging.jinja2"',
                'import "tier3_pattern_python_di.jinja2"',
                'import "tier3_pattern_python_log_enricher.jinja2"',
                'import "tier3_pattern_python_translator.jinja2"',
            ],
        ),
        (
            "dto.py.jinja2",
            [
                'import "tier3_pattern_python_pydantic.jinja2"',
                'import "tier3_pattern_python_typed_id.jinja2"',
                'import "tier3_pattern_python_logging.jinja2"',
            ],
        ),
        (
            "service_command.py.jinja2",
            [
                'import "tier3_pattern_python_async.jinja2"',
                'import "tier3_pattern_python_error.jinja2"',
                'import "tier3_pattern_python_logging.jinja2"',
                'import "tier3_pattern_python_di.jinja2"',
                'import "tier3_pattern_python_translator.jinja2"',
            ],
        ),
        (
            "generic.py.jinja2",
            [
                'import "tier3_pattern_python_logging.jinja2"',
            ],
        ),
        (
            "tool.py.jinja2",
            [
                'import "tier3_pattern_python_error.jinja2"',
                'import "tier3_pattern_python_logging.jinja2"',
            ],
        ),
        (
            "config_schema.py.jinja2",
            [
                'import "tier3_pattern_python_pydantic.jinja2"',
                'import "tier3_pattern_python_typed_id.jinja2"',
                'import "tier3_pattern_python_logging.jinja2"',
            ],
        ),
    ],
)
def test_concrete_code_templates_use_tier3_imports(
    template_name: str,
    required_imports: list[str],
) -> None:
    """Concrete templates import expected Tier3 macro libraries."""
    template_path = TEMPLATE_ROOT / template_name
    assert template_path.exists(), f"Missing template: {template_path}"

    content = template_path.read_text(encoding="utf-8")

    for import_stmt in required_imports:
        assert import_stmt in content, (
            f"{template_name} missing tier3 import: {import_stmt}"
        )


@pytest.mark.parametrize(
    "template_name",
    [
        "worker.py.jinja2",
        "dto.py.jinja2",
        "service_command.py.jinja2",
        "generic.py.jinja2",
        "tool.py.jinja2",
        "config_schema.py.jinja2",
    ],
)
def test_concrete_code_templates_are_guideline_enforcement(template_name: str) -> None:
    """Concrete templates declare GUIDELINE enforcement (not STRICT)."""
    template_path = TEMPLATE_ROOT / template_name
    assert template_path.exists(), f"Missing template: {template_path}"

    content = template_path.read_text(encoding="utf-8")

    assert "TEMPLATE_METADATA" in content
    assert "enforcement: GUIDELINE" in content
    assert "enforcement: STRICT" not in content
