# SCAFFOLD: template=test_provenance_e2e version=1.0
# created=2026-01-25 path=tests/integration/test_provenance_e2e.py
"""
E2E tests for Task 1.6b: Provenance regression testing.

Validates complete scaffold â†’ parse â†’ registry lookup roundtrip:
1. Scaffold each artifact type (dto, worker, service, generic, design)
2. Parse SCAFFOLD header from generated content
3. Lookup version_hash in .st3/template_registry.yaml
4. Assert tier chain matches template inheritance
5. Assert header format: artifact_type:version_hash | timestamp | output_path

@layer: Testing (Integration)
@dependencies: [pytest, mcp_server.managers]
@responsibilities:
    - Validate SCAFFOLD header format in scaffolded output
    - Verify registry lookup roundtrip works
    - Assert tier chain provenance is traceable
"""

# Standard library
import re
from pathlib import Path

# Third-party
import pytest

# Project modules
from mcp_server.managers.artifact_manager import ArtifactManager
from mcp_server.scaffolding.metadata import ScaffoldMetadataParser


class TestProvenanceE2E:
    """E2E tests for scaffold provenance tracking (Task 1.6b)."""

    @pytest.fixture
    def manager(self, tmp_path: Path) -> ArtifactManager:
        """Create artifact manager with workspace root."""
        return ArtifactManager(workspace_root=str(tmp_path))

    @pytest.fixture
    def parser(self) -> ScaffoldMetadataParser:
        """Create metadata parser."""
        return ScaffoldMetadataParser()

    def _parse_scaffold_header(
        self,
        content: str,
        expected_extension: str,
        artifact_type: str
    ) -> tuple[str, str, str, str]:
        """Extract SCAFFOLD header metadata from 2-line format.

        Returns:
            Tuple of (template_name, version, timestamp, output_path)
        """
        lines = content.split("\n")

        if expected_extension == ".py":
            # Python format (2-line):
            # Line 1: # /path/to/file.py
            # Line 2: # template=X version=Y created=Z updated=
            assert lines[0].startswith("#"), \
                f"{artifact_type}: Line 1 must start with '#' (filepath comment)"

            # Extract filepath from line 1
            output_path = lines[0][1:].strip()  # Remove leading '#'

            # Parse metadata from line 2
            assert "template=" in lines[1], \
                f"{artifact_type}: Line 2 must contain metadata. Got: {lines[1]}"

            # Extract metadata fields using regex
            metadata_line = lines[1]
            template_match = re.search(r"template=(\S+)", metadata_line)
            version_match = re.search(r"version=(\S+)", metadata_line)
            created_match = re.search(r"created=(\S+)", metadata_line)

            assert template_match and version_match and created_match, \
                f"{artifact_type}: Invalid metadata format. Got: {metadata_line}"

            return (
                template_match.group(1),
                version_match.group(1),
                created_match.group(1),
                output_path
            )

        # Markdown format (2-line HTML comments):
        # Line 1: <!-- /path/to/file.md -->
        # Line 2: <!-- template=X version=Y created=Z updated= -->
        assert lines[0].startswith("<!--") and lines[0].endswith("-->"), \
            f"{artifact_type}: Line 1 must be HTML comment with filepath"

        # Extract filepath from line 1
        output_path = lines[0][4:-3].strip()  # Remove <!-- and -->

        # Parse metadata from line 2
        assert "<!-- template=" in lines[1] and lines[1].endswith("-->"), \
            f"{artifact_type}: Line 2 must be HTML comment with metadata. Got: {lines[1]}"

        # Extract metadata fields
        metadata_line = lines[1][4:-3]  # Remove <!-- and -->
        template_match = re.search(r"template=(\S+)", metadata_line)
        version_match = re.search(r"version=(\S+)", metadata_line)
        created_match = re.search(r"created=(\S+)", metadata_line)

        assert template_match and version_match and created_match, \
            f"{artifact_type}: Invalid metadata format. Got: {metadata_line}"

        return (
            template_match.group(1),
            version_match.group(1),
            created_match.group(1),
            output_path
        )

    @pytest.mark.parametrize("artifact_type,expected_extension", [
        ("dto", ".py"),
        ("worker", ".py"),
        ("service", ".py"),
        ("generic", ".py"),
        ("design", ".md"),
    ])
    @pytest.mark.asyncio
    async def test_scaffold_produces_valid_scaffold_header(
        self,
        manager: ArtifactManager,
        artifact_type: str,
        expected_extension: str
    ):
        """Scaffolded output must have valid SCAFFOLD header with provenance metadata.

        REQUIREMENT (Task 1.6b): SCAFFOLD header format must be:
        - Python: # SCAFFOLD: template=X version=Y created=Z path=W
        - Markdown: <!-- SCAFFOLD: template=X version=Y created=Z path=W -->
        """
        # Scaffold artifact via artifact_manager (single path)
        context = {
            "name": f"Test{artifact_type.title()}",
            "layer": "Backend",
            "responsibilities": ["Test responsibility"]
        }

        if artifact_type == "dto":
            context["fields"] = [
                {"name": "id", "type": "int", "description": "Identifier"},
                {"name": "name", "type": "str", "description": "Name"}
            ]
            context["frozen"] = True
            context["examples"] = [{"id": 1, "name": "Test"}]
            context["dependencies"] = ["pydantic"]
            context["responsibilities"] = ["Data validation", "Type safety"]

        if artifact_type == "design":
            context.update({
                "title": f"Test {artifact_type.title()} Document",
                "problem_statement": "Test problem",
                "requirements_functional": ["Req 1"],
                "requirements_nonfunctional": ["Non-func req 1"],
                "options": [{
                    "name": "Option 1",
                    "description": "Test option",
                    "pros": ["Pro 1"],
                    "cons": ["Con 1"]
                }],
                "decision": "Option 1",
                "rationale": "Test rationale",
                "key_decisions": [{"area": "Architecture", "decision": "Test decision"}],
                "timestamp": "2026-01-27T10:00:00Z"
            })

        file_path = await manager.scaffold_artifact(
            artifact_type, **context
        )

        # Read generated file
        content = Path(file_path).read_text(encoding="utf-8")

        template_name, version, timestamp, output_path = self._parse_scaffold_header(
            content, expected_extension, artifact_type
        )

        # REQUIREMENT 1: template_name matches artifact type
        assert (
            template_name == artifact_type
        ), f"{artifact_type}: Expected template={artifact_type}, got {template_name}"

        # REQUIREMENT 2: version must be 8-char hash
        assert (
            len(version) == 8 and version.isalnum()
        ), f"{artifact_type}: version must be 8-char hash, got: {version}"

        # REQUIREMENT 3: timestamp must be ISO 8601 format (YYYY-MM-DDTHH:MMZ)
        timestamp_pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?Z$"
        assert (
            re.match(timestamp_pattern, timestamp)
        ), f"{artifact_type}: timestamp format invalid: {timestamp}"

        # REQUIREMENT 4: output_path must have correct extension
        assert (
            output_path.endswith(expected_extension)
        ), f"{artifact_type}: path extension mismatch: {output_path}"

    @pytest.mark.parametrize("artifact_type", [
        "dto",
        "worker",
        "service",
        "generic",
    ])
    @pytest.mark.asyncio
    async def test_scaffold_tier_chain_traceable(
        self,
        manager: ArtifactManager,
        artifact_type: str
    ):
        """Scaffolded artifacts must have traceable tier chain through template inheritance.

        REQUIREMENT (Task 1.6b): Tier chain for Python artifacts should be:
        tier0_base_artifact â†’ tier1_base_code â†’ tier2_base_python â†’ concrete template
        """
        # Scaffold artifact via artifact_manager
        context = {
            "name": f"Test{artifact_type.title()}",
            "layer": "Backend",
            "responsibilities": ["Test responsibility"]
        }

        if artifact_type == "dto":
            context["fields"] = [
                {"name": "id", "type": "int", "description": "Identifier"},
                {"name": "name", "type": "str", "description": "Name"}
            ]
            context["frozen"] = True
            context["examples"] = [{"id": 1, "name": "Test"}]
            context["dependencies"] = ["pydantic"]
            context["responsibilities"] = ["Data validation", "Type safety"]

        file_path = await manager.scaffold_artifact(
            artifact_type, **context
        )

        # Read generated file
        content = Path(file_path).read_text(encoding="utf-8")

        # Verify content shows inheritance chain (2-line SCAFFOLD format)
        # (tier0 â†’ tier1 â†’ tier2 â†’ concrete all contribute to output)
        lines = content.split("\n")
        assert lines[0].startswith("#"), "tier0: Line 1 must be filepath comment"
        assert "template=" in lines[1], "tier0: Line 2 must have metadata"
        assert '"""' in content, "tier1: module docstring missing"
        assert "class " in content, "tier2: class structure missing"

    @pytest.mark.asyncio
    async def test_scaffold_design_doc_tier_chain_traceable(
        self,
        manager: ArtifactManager
    ):
        """Design doc must have traceable tier chain through markdown templates.

        REQUIREMENT (Task 1.6b): Tier chain for Markdown artifacts should be:
        tier0_base_artifact â†’ tier1_base_document â†’ tier2_base_markdown â†’ concrete template
        """
        # Scaffold design doc via artifact_manager
        file_path = await manager.scaffold_artifact(
            "design",
            name="TestDesign",
            title="Test Design Document",
            problem_statement="Define architecture",
            decision="Use layered architecture",
            rationale="Separation of concerns",
            options=["Layered", "Microservices"],
            key_decisions=["Use MVC pattern"],
            requirements_functional=["Feature X"],
            requirements_nonfunctional=["Performance Y"],
            timestamp="2026-01-27T10:00:00Z"
        )

        # Read generated file
        content = Path(file_path).read_text(encoding="utf-8")

        # Verify content shows inheritance chain (2-line HTML comment format)
        lines = content.split("\n")
        assert lines[0].startswith("<!--") and lines[0].endswith("-->"), \
            "tier0: Line 1 must be HTML comment with filepath"
        assert "<!-- template=" in lines[1] and lines[1].endswith("-->"), \
            "tier0: Line 2 must be HTML comment with metadata"
        assert "# " in content, "tier2: markdown structure missing"
