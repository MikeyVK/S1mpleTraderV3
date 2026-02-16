"""Unit tests for structured generic document template."""

from pathlib import Path
from typing import Any

import pytest
from jinja2 import Environment, FileSystemLoader


@pytest.fixture
def template_env() -> Environment:
    """Create Jinja2 environment rooted at scaffolding templates."""
    template_dir = (
        Path(__file__).parent.parent.parent.parent / "mcp_server" / "scaffolding" / "templates"
    )
    return Environment(loader=FileSystemLoader(template_dir))


@pytest.fixture
def base_system_context() -> dict[str, Any]:
    """System metadata variables normally injected by scaffolder."""
    return {
        "output_path": "docs/reference/mcp/migration_v2.0.md",
        "artifact_type": "generic_doc",
        "version_hash": "abc1234",
        "timestamp": "2026-02-16T10:30:00Z",
        "format": "markdown",
    }


@pytest.fixture
def minimal_context(base_system_context: dict[str, Any]) -> dict[str, Any]:
    """Minimal valid context for generic_doc template."""
    return {
        **base_system_context,
        "title": "Migration Guide: v1.x → v2.0",
        "purpose": "Guide the transition to workflow-first commit scopes.",
        "summary": "This migration updates commit scope conventions and tool parameters.",
    }


@pytest.fixture
def full_context(base_system_context: dict[str, Any]) -> dict[str, Any]:
    """Full context exercising all structured optional sections."""
    return {
        **base_system_context,
        "title": "Migration Guide: v1.x → v2.0",
        "purpose": "Guide the transition to workflow-first commit scopes.",
        "summary": "This migration updates commit scope conventions and tool parameters.",
        "status": "APPROVED",
        "version": "2.0.0",
        "last_updated": "2026-02-16",
        "scope_in": "Commit scope migration and workflow phase mapping.",
        "scope_out": "Implementation internals and unrelated refactors.",
        "prerequisites": ["Read agent.md", "Initialize workflow state"],
        "related_docs": ["agent.md", "docs/development/issue138/planning.md"],
        "key_changes": [
            "New P_{PHASE}_SP_{SUBPHASE} commit scope format",
            "phase parameter deprecated in favor of workflow_phase/sub_phase",
        ],
        "migration_steps": [
            "Update git_add_or_commit invocations",
            "Use transition_phase between workflow phases",
            "Run quality gates before merge",
        ],
        "validation_checklist": [
            "All commits use workflow-first scopes",
            "No legacy phase parameter in new changes",
            "Tests and quality gates are green",
        ],
        "faq": [
            {
                "question": "Can old commits stay as-is?",
                "answer": "Yes, old commits remain valid and readable.",
            },
            {
                "question": "Can I skip phases?",
                "answer": "Only via force_phase_transition with approval and reason.",
            },
        ],
        "custom_sections": [
            {
                "heading": "Rollout Strategy",
                "content": "Roll out in feature branches first.",
                "bullets": ["Pilot on one team", "Expand after validation"],
                "checklist": ["Pilot completed", "Metrics reviewed"],
            }
        ],
    }


class TestGenericDocTemplate:
    """Behavioral coverage for generic.md.jinja2."""

    def test_renders_scaffold_metadata_fingerprint(
        self,
        template_env: Environment,
        minimal_context: dict[str, Any],
    ) -> None:
        """Template must inherit tier0 fingerprint comments via tier chain."""
        template = template_env.get_template("concrete/generic.md.jinja2")

        result = template.render(**minimal_context)

        assert "<!-- docs/reference/mcp/migration_v2.0.md -->" in result
        assert (
            "<!-- template=generic_doc version=abc1234 created=2026-02-16T10:30:00Z updated= -->"
            in result
        )
        assert "# Migration Guide: v1.x → v2.0" in result

    def test_renders_structured_sections_without_freeform_content_dump(
        self,
        template_env: Environment,
        full_context: dict[str, Any],
    ) -> None:
        """Template should render canonical structured sections from typed fields."""
        template = template_env.get_template("concrete/generic.md.jinja2")

        result = template.render(**full_context)

        assert "## Summary" in result
        assert "## Key Changes" in result
        assert "## Migration Steps" in result
        assert "## Validation Checklist" in result
        assert "## FAQ" in result
        assert "## Rollout Strategy" in result
        assert "- [ ] Pilot completed" in result
        assert "- [ ] Metrics reviewed" in result

        assert "## Related Documentation" in result
        assert "- **[agent.md][related-1]**" in result
        assert "- **[docs/development/issue138/planning.md][related-2]**" in result

    def test_normalizes_scalar_inputs_for_list_sections(
        self,
        template_env: Environment,
        minimal_context: dict[str, Any],
    ) -> None:
        """String inputs for list-like fields should not render char-by-char bullets."""
        template = template_env.get_template("concrete/generic.md.jinja2")

        context = {
            **minimal_context,
            "prerequisites": "Read agent.md",
            "related_docs": "agent.md",
        }

        result = template.render(**context)

        assert "1. Read agent.md" in result
        assert "- **[agent.md][related-1]**" in result
        assert "- **[a][related-1]**" not in result
        assert "- **[g][related-" not in result

    def test_ignores_legacy_content_field(
        self,
        template_env: Environment,
        minimal_context: dict[str, Any],
    ) -> None:
        """Legacy free-form content field should not be rendered anymore."""
        template = template_env.get_template("concrete/generic.md.jinja2")

        context = {
            **minimal_context,
            "content": "THIS SHOULD NOT APPEAR IN OUTPUT",
        }

        result = template.render(**context)

        assert "THIS SHOULD NOT APPEAR IN OUTPUT" not in result
