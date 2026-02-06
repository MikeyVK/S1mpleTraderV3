"""
Task 3.7: Integration tests for tracking templates
Tests tier1_base_tracking + tier2 text/markdown + concrete tracking templates.
"""

import pytest
from pathlib import Path
from jinja2 import Environment, FileSystemLoader


TEMPLATES_DIR = Path(__file__).parents[3] / "mcp_server" / "scaffolding" / "templates"


@pytest.fixture
def jinja_env():
    """Create Jinja2 environment with templates loader."""
    return Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )


# ===== TIER1/TIER2 EXISTENCE TESTS =====

def test_tier1_base_tracking_exists():
    """tier1_base_tracking.jinja2 must exist."""
    template_path = TEMPLATES_DIR / "tier1_base_tracking.jinja2"
    assert template_path.exists(), "tier1_base_tracking.jinja2 not found"


def test_tier2_tracking_text_exists():
    """tier2_tracking_text.jinja2 must exist."""
    template_path = TEMPLATES_DIR / "tier2_tracking_text.jinja2"
    assert template_path.exists(), "tier2_tracking_text.jinja2 not found"


def test_tier2_tracking_markdown_exists():
    """tier2_tracking_markdown.jinja2 must exist."""
    template_path = TEMPLATES_DIR / "tier2_tracking_markdown.jinja2"
    assert template_path.exists(), "tier2_tracking_markdown.jinja2 not found"


# ===== CONCRETE TEMPLATE EXISTENCE TESTS =====

def test_concrete_commit_txt_exists():
    """concrete/commit.txt.jinja2 must exist."""
    template_path = TEMPLATES_DIR / "concrete" / "commit.txt.jinja2"
    assert template_path.exists(), "concrete/commit.txt.jinja2 not found"


def test_concrete_pr_md_exists():
    """concrete/pr.md.jinja2 must exist."""
    template_path = TEMPLATES_DIR / "concrete" / "pr.md.jinja2"
    assert template_path.exists(), "concrete/pr.md.jinja2 not found"


def test_concrete_issue_md_exists():
    """concrete/issue.md.jinja2 must exist."""
    template_path = TEMPLATES_DIR / "concrete" / "issue.md.jinja2"
    assert template_path.exists(), "concrete/issue.md.jinja2 not found"


# ===== COMMIT MESSAGE RENDERING TESTS =====

def test_commit_txt_renders_conventional_commits_format(jinja_env):
    """Test commit.txt renders Conventional Commits format."""
    template = jinja_env.get_template("concrete/commit.txt.jinja2")
    
    context = {
        "tracking_type": "commit",
        "type": "feat",
        "scope": "tracking",
        "message": "add tracking templates",
        "body": "Implements tier1_base_tracking + tier2 text/markdown + 3 concrete templates.",
        "refs": ["#72"],
    }
    
    output = template.render(**context)
    
    # Verify Conventional Commits format
    assert "feat(tracking): add tracking templates" in output
    assert "Implements tier1_base_tracking" in output
    assert "Refs: #72" in output


def test_commit_txt_renders_breaking_change(jinja_env):
    """Test commit.txt renders BREAKING CHANGE footer."""
    template = jinja_env.get_template("concrete/commit.txt.jinja2")
    
    context = {
        "tracking_type": "commit",
        "type": "feat",
        "message": "change API signature",
        "breaking_change": True,
        "breaking_description": "Removed deprecated parameter from public API",
    }
    
    output = template.render(**context)
    
    # Verify breaking change marker
    assert "feat!: change API signature" in output
    assert "BREAKING CHANGE: Removed deprecated parameter" in output


def test_commit_txt_minimal_context(jinja_env):
    """Test commit.txt renders with minimal required fields."""
    template = jinja_env.get_template("concrete/commit.txt.jinja2")
    
    context = {
        "tracking_type": "commit",
        "type": "fix",
        "message": "resolve bug",
    }
    
    output = template.render(**context)
    
    assert "fix: resolve bug" in output
    # Should not have optional sections
    assert "Refs:" not in output
    assert "BREAKING CHANGE:" not in output


# ===== PR DESCRIPTION RENDERING TESTS =====

def test_pr_md_renders_standard_sections(jinja_env):
    """Test pr.md renders with standard PR sections."""
    template = jinja_env.get_template("concrete/pr.md.jinja2")
    
    context = {
        "tracking_type": "pr",
        "title": "Add tracking templates",
        "summary": "Implements Task 3.7 tracking templates",
        "changes": "- Created tier1_base_tracking.jinja2\\n- Created tier2_tracking_text.jinja2\\n- Created 3 concrete templates",
        "testing": "Unit tests for all templates, integration tests passing",
        "closes_issues": [72],
    }
    
    output = template.render(**context)
    
    # Verify structure
    assert "# Add tracking templates" in output
    assert "Implements Task 3.7" in output
    
    # Verify standard sections
    assert "## Changes" in output
    assert "Created tier1_base_tracking.jinja2" in output
    
    assert "## Testing" in output
    assert "Unit tests for all templates" in output
    
    assert "## Checklist" in output
    assert "- [ ] Code follows project standards" in output
    
    # Verify closes reference
    assert "Closes: #72" in output


def test_pr_md_renders_cross_branch_related_docs(jinja_env):
    """Test pr.md uses CROSS-BRANCH tier3_pattern_markdown_related_docs."""
    template = jinja_env.get_template("concrete/pr.md.jinja2")
    
    context = {
        "tracking_type": "pr",
        "title": "Test PR",
        "changes": "Test changes",
        "related_docs": ["docs/development/issue72/planning.md", "docs/development/issue72/tracking-type-architecture.md"],
    }
    
    output = template.render(**context)
    
    # Verify cross-branch pattern works
    assert "## Related Documentation" in output
    assert "[docs/development/issue72/planning.md][related-1]" in output
    assert "[docs/development/issue72/tracking-type-architecture.md][related-2]" in output


def test_pr_md_renders_breaking_changes_section(jinja_env):
    """Test pr.md renders breaking changes section."""
    template = jinja_env.get_template("concrete/pr.md.jinja2")
    
    context = {
        "tracking_type": "pr",
        "title": "Breaking API change",
        "changes": "Changed signature",
        "breaking_changes": "Removed deprecated `old_method()` - use `new_method()` instead",
    }
    
    output = template.render(**context)
    
    assert "## ⚠️ Breaking Changes" in output
    assert "Removed deprecated `old_method()`" in output


def test_pr_md_custom_checklist(jinja_env):
    """Test pr.md renders custom checklist items."""
    template = jinja_env.get_template("concrete/pr.md.jinja2")
    
    context = {
        "tracking_type": "pr",
        "title": "Custom checklist",
        "changes": "Changes",
        "checklist_items": [
            "All tests passing",
            "Documentation updated",
            {"description": "Quality gates passing", "checked": True},
        ],
    }
    
    output = template.render(**context)
    
    assert "- [ ] All tests passing" in output
    assert "- [ ] Documentation updated" in output
    assert "- [x] Quality gates passing" in output


# ===== ISSUE DESCRIPTION RENDERING TESTS =====

def test_issue_md_renders_problem_sections(jinja_env):
    """Test issue.md renders problem/expected/actual sections."""
    template = jinja_env.get_template("concrete/issue.md.jinja2")
    
    context = {
        "tracking_type": "issue",
        "title": "Add tracking templates",
        "summary": "Implement tracking artifact templates",
        "problem": "No template library for tracking artifacts",
        "expected": "Tracking templates with consistent structure",
        "actual": "No tracking templates exist",
        "context": "Part of Issue #72 Task 3.7",
    }
    
    output = template.render(**context)
    
    # Verify structure
    assert "# Add tracking templates" in output
    assert "Implement tracking artifact templates" in output
    
    # Verify sections
    assert "## Problem" in output
    assert "No template library for tracking artifacts" in output
    
    assert "## Expected Behavior" in output
    assert "Tracking templates with consistent structure" in output
    
    assert "## Actual Behavior" in output
    assert "No tracking templates exist" in output
    
    assert "## Context" in output
    assert "Part of Issue #72 Task 3.7" in output


def test_issue_md_renders_cross_branch_related_docs(jinja_env):
    """Test issue.md uses CROSS-BRANCH tier3_pattern_markdown_related_docs."""
    template = jinja_env.get_template("concrete/issue.md.jinja2")
    
    context = {
        "tracking_type": "issue",
        "title": "Test Issue",
        "problem": "Test problem",
        "related_docs": ["docs/development/issue72/planning.md"],
    }
    
    output = template.render(**context)
    
    # Verify cross-branch pattern works
    assert "## Related Documentation" in output
    assert "[docs/development/issue72/planning.md][related-1]" in output


def test_issue_md_renders_metadata_section(jinja_env):
    """Test issue.md renders metadata (labels/milestone/assignees)."""
    template = jinja_env.get_template("concrete/issue.md.jinja2")
    
    context = {
        "tracking_type": "issue",
        "title": "Test Issue",
        "problem": "Problem description",
        "labels": ["type:feature", "area:templates"],
        "milestone": "Issue #72 Template Library",
        "assignees": ["agent", "developer"],
    }
    
    output = template.render(**context)
    
    assert "**Metadata:**" in output
    assert "Labels: type:feature, area:templates" in output
    assert "Milestone: Issue #72 Template Library" in output
    assert "Assignees: agent, developer" in output


def test_issue_md_minimal_context(jinja_env):
    """Test issue.md renders with minimal required fields."""
    template = jinja_env.get_template("concrete/issue.md.jinja2")
    
    context = {
        "tracking_type": "issue",
        "title": "Simple Issue",
        "problem": "Brief problem description",
    }
    
    output = template.render(**context)
    
    assert "# Simple Issue" in output
    assert "## Problem" in output
    assert "Brief problem description" in output
    
    # Should not have optional sections
    assert "## Expected Behavior" not in output
    assert "## Actual Behavior" not in output
    assert "## Related Documentation" not in output


# ===== TIER CHAIN VALIDATION =====

def test_tier1_extends_tier0(jinja_env):
    """Verify tier1_base_tracking extends tier0_base_artifact."""
    template_source = (TEMPLATES_DIR / "tier1_base_tracking.jinja2").read_text(encoding='utf-8')
    assert '{%- extends "tier0_base_artifact.jinja2" -%}' in template_source


def test_tier2_text_extends_tier1(jinja_env):
    """Verify tier2_tracking_text extends tier1_base_tracking."""
    template_source = (TEMPLATES_DIR / "tier2_tracking_text.jinja2").read_text(encoding='utf-8')
    assert '{%- extends "tier1_base_tracking.jinja2" -%}' in template_source


def test_tier2_markdown_extends_tier1(jinja_env):
    """Verify tier2_tracking_markdown extends tier1_base_tracking."""
    template_source = (TEMPLATES_DIR / "tier2_tracking_markdown.jinja2").read_text(encoding='utf-8')
    assert '{%- extends "tier1_base_tracking.jinja2" -%}' in template_source


def test_commit_extends_tier2_text(jinja_env):
    """Verify concrete/commit.txt extends tier2_tracking_text."""
    template_source = (TEMPLATES_DIR / "concrete" / "commit.txt.jinja2").read_text(encoding='utf-8')
    assert '{%- extends "tier2_tracking_text.jinja2" -%}' in template_source


def test_pr_extends_tier2_markdown(jinja_env):
    """Verify concrete/pr.md extends tier2_tracking_markdown."""
    template_source = (TEMPLATES_DIR / "concrete" / "pr.md.jinja2").read_text(encoding='utf-8')
    assert '{%- extends "tier2_tracking_markdown.jinja2" -%}' in template_source


def test_issue_extends_tier2_markdown(jinja_env):
    """Verify concrete/issue.md extends tier2_tracking_markdown."""
    template_source = (TEMPLATES_DIR / "concrete" / "issue.md.jinja2").read_text(encoding='utf-8')
    assert '{%- extends "tier2_tracking_markdown.jinja2" -%}' in template_source


def test_pr_imports_cross_branch_pattern(jinja_env):
    """Verify pr.md imports tier3_pattern_markdown_related_docs (cross-branch)."""
    template_source = (TEMPLATES_DIR / "concrete" / "pr.md.jinja2").read_text(encoding='utf-8')
    assert '{%- import "tier3_pattern_markdown_related_docs.jinja2" as related -%}' in template_source
    assert "CROSS-BRANCH PATTERN IMPORT" in template_source


def test_issue_imports_cross_branch_pattern(jinja_env):
    """Verify issue.md imports tier3_pattern_markdown_related_docs (cross-branch)."""
    template_source = (TEMPLATES_DIR / "concrete" / "issue.md.jinja2").read_text(encoding='utf-8')
    assert '{%- import "tier3_pattern_markdown_related_docs.jinja2" as related -%}' in template_source
    assert "CROSS-BRANCH PATTERN IMPORT" in template_source
