"""
Tests for Issue #52 alignment - Validation TEMPLATE_METADATA (Issue #72 Task 1.5).

RED phase: Tests for TemplateAnalyzer.extract_metadata() on Tier 0-2 templates.
Validates that all base templates have enforcement/level/validates structure.
"""

from pathlib import Path

import pytest

from mcp_server.validation.template_analyzer import TemplateAnalyzer


class TestTier0ValidationMetadata:
    """Tests for Tier 0 base template validation metadata."""

    @staticmethod
    def get_templates_dir():
        """Get templates directory path."""
        return Path(__file__).parent.parent.parent / "mcp_server" / "scaffolding" / "templates"

    def test_tier0_has_validation_metadata(self):
        """Tier 0 template should have validation TEMPLATE_METADATA."""
        analyzer = TemplateAnalyzer(self.get_templates_dir())
        template_path = self.get_templates_dir() / "tier0_base_artifact.jinja2"

        metadata = analyzer.extract_metadata(template_path)

        assert metadata, "Tier 0 should have TEMPLATE_METADATA"
        assert "enforcement" in metadata
        assert "level" in metadata
        # validates.strict removed in v2.3.0 (descriptive strings, not machine-readable)
        # SCAFFOLD validation now handled by ScaffoldMetadataParser, not layered validator

    def test_tier0_enforcement_strict(self):
        """Tier 0 should use STRICT enforcement (universal constraints)."""
        analyzer = TemplateAnalyzer(self.get_templates_dir())
        template_path = self.get_templates_dir() / "tier0_base_artifact.jinja2"

        metadata = analyzer.extract_metadata(template_path)

        assert metadata["enforcement"] == "STRICT"

    def test_tier0_validates_scaffold_pattern(self):
        """Tier 0 SCAFFOLD format documented in notes (not validates.strict)."""
        analyzer = TemplateAnalyzer(self.get_templates_dir())
        template_path = self.get_templates_dir() / "tier0_base_artifact.jinja2"

        metadata = analyzer.extract_metadata(template_path)

        # validates.strict removed in v2.3.0 - was descriptive strings, not patterns
        # SCAFFOLD format now documented in notes field
        assert "notes" in metadata
        notes_text = " ".join(metadata["notes"])
        assert "SCAFFOLD format" in notes_text or "Line 1" in notes_text


class TestTier1ValidationMetadata:
    """Tests for Tier 1 base templates validation metadata."""

    @staticmethod
    def get_templates_dir():
        """Get templates directory path."""
        return Path(__file__).parent.parent.parent / "mcp_server" / "scaffolding" / "templates"

    def test_tier1_code_has_validation_metadata(self):
        """Tier 1 CODE template should have validation metadata."""
        analyzer = TemplateAnalyzer(self.get_templates_dir())
        template_path = self.get_templates_dir() / "tier1_base_code.jinja2"

        metadata = analyzer.extract_metadata(template_path)

        assert metadata, "Tier 1 CODE should have TEMPLATE_METADATA"
        assert "enforcement" in metadata
        assert metadata["enforcement"] == "STRICT"

    def test_tier1_code_validates_imports_classes(self):
        """Tier 1 CODE should validate import/class/function structure."""
        analyzer = TemplateAnalyzer(self.get_templates_dir())
        template_path = self.get_templates_dir() / "tier1_base_code.jinja2"

        metadata = analyzer.extract_metadata(template_path)

        strict_rules = metadata["validates"]["strict"]
        # Should validate CODE structure: imports, class, def
        assert any("import" in rule.lower() or "from" in rule.lower() for rule in strict_rules)
        assert any("class" in rule.lower() for rule in strict_rules)

    def test_tier1_document_has_validation_metadata(self):
        """Tier 1 DOCUMENT template should have validation metadata."""
        analyzer = TemplateAnalyzer(self.get_templates_dir())
        template_path = self.get_templates_dir() / "tier1_base_document.jinja2"

        metadata = analyzer.extract_metadata(template_path)

        assert metadata, "Tier 1 DOCUMENT should have TEMPLATE_METADATA"
        assert metadata["enforcement"] == "STRICT"

    def test_tier1_document_validates_headings(self):
        """Tier 1 DOCUMENT should validate document structure."""
        analyzer = TemplateAnalyzer(self.get_templates_dir())
        template_path = self.get_templates_dir() / "tier1_base_document.jinja2"

        metadata = analyzer.extract_metadata(template_path)

        # Document templates validate structure, not regex patterns
        validates = metadata["validates"]
        assert "required_blocks" in validates or "structure" in validates
        # Should validate document sections
        if "structure" in validates:
            structure_rules = validates["structure"]
            assert any("Purpose" in rule or "Scope" in rule for rule in structure_rules)

    def test_tier2_python_has_validation_metadata(self):
        """Tier 2 Python template should have validation metadata."""
        analyzer = TemplateAnalyzer(self.get_templates_dir())
        template_path = self.get_templates_dir() / "tier2_base_python.jinja2"

        metadata = analyzer.extract_metadata(template_path)

        assert metadata, "Tier 2 Python should have TEMPLATE_METADATA"
        assert "enforcement" in metadata
        assert metadata["enforcement"] == "STRICT"  # Tier 0+1+2 are STRICT (Issue #72)

    def test_tier2_python_validates_typing_docstrings(self):
        """Tier 2 Python should validate type hints and docstrings."""
        analyzer = TemplateAnalyzer(self.get_templates_dir())
        template_path = self.get_templates_dir() / "tier2_base_python.jinja2"

        metadata = analyzer.extract_metadata(template_path)

        # Tier 2 uses strict rules for language patterns
        assert "validates" in metadata
        strict_rules = metadata["validates"].get("strict", [])
        # Should validate Python patterns: class, def, docstrings
        assert any(
            "class" in rule.lower() or "def" in rule.lower() or '"""' in rule
            for rule in strict_rules
        )

    def test_tier2_markdown_has_validation_metadata(self):
        """Tier 2 Markdown template should have validation metadata."""
        analyzer = TemplateAnalyzer(self.get_templates_dir())
        template_path = self.get_templates_dir() / "tier2_base_markdown.jinja2"

        metadata = analyzer.extract_metadata(template_path)

        assert metadata, "Tier 2 Markdown should have TEMPLATE_METADATA"
        assert metadata["enforcement"] == "STRICT"  # Tier 0+1+2 are STRICT (Issue #72)

    def test_tier2_yaml_has_validation_metadata(self):
        """Tier 2 YAML template should have validation metadata."""
        analyzer = TemplateAnalyzer(self.get_templates_dir())
        template_path = self.get_templates_dir() / "tier2_base_yaml.jinja2"

        metadata = analyzer.extract_metadata(template_path)

        assert metadata, "Tier 2 YAML should have TEMPLATE_METADATA"
        assert metadata["enforcement"] == "STRICT"  # Tier 0+1+2 are STRICT (Issue #72)


class TestValidationMetadataStructure:
    """Tests for TEMPLATE_METADATA structure compliance."""

    @staticmethod
    def get_templates_dir():
        """Get templates directory path."""
        return Path(__file__).parent.parent.parent / "mcp_server" / "scaffolding" / "templates"

    @pytest.mark.parametrize(
        "template_file",
        [
            "tier0_base_artifact.jinja2",
            "tier1_base_code.jinja2",
            "tier1_base_document.jinja2",
            "tier1_base_config.jinja2",
            "tier2_base_python.jinja2",
            "tier2_base_markdown.jinja2",
            "tier2_base_yaml.jinja2",
        ],
    )
    def test_all_templates_have_required_fields(self, template_file):
        """All base templates should have required validation metadata fields."""
        analyzer = TemplateAnalyzer(self.get_templates_dir())
        template_path = self.get_templates_dir() / template_file

        metadata = analyzer.extract_metadata(template_path)

        # Required fields per Issue #52
        assert "enforcement" in metadata, f"{template_file} missing 'enforcement'"
        assert "level" in metadata, f"{template_file} missing 'level'"
        # validates field is optional for tier0 (SCAFFOLD validation is special-cased)
        if template_file != "tier0_base_artifact.jinja2":
            assert "validates" in metadata, f"{template_file} missing 'validates'"

        # enforcement must be valid value
        assert metadata["enforcement"] in ["STRICT", "ARCHITECTURAL", "GUIDELINE"]

        # level must be valid value
        assert metadata["level"] in ["format", "content", "structure"]

        # validates must have appropriate structure (optional for tier0)
        if "validates" in metadata:
            validates = metadata["validates"]
            assert isinstance(validates, dict)
            if metadata["enforcement"] == "STRICT":
                # Strict enforcement can have strict rules OR structural validation
                assert (
                    "strict" in validates
                    or "required_blocks" in validates
                    or "structure" in validates
                )
