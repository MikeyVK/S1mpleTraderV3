# Script to create E2E test file
from pathlib import Path

content = '''\"\"\"E2E test for ScaffoldArtifactTool.execute() - MCP protocol entry point.

This test proves that calling the tool through the MCP protocol (via execute())
works end-to-end and writes files to disk. It complements the manager-level
tests by validating the full tool layer contract.

Requirements (from implementation_plan.md):
- Call tool.execute() directly (not artifact_manager.scaffold_artifact())
- Happy path: successful scaffolding of design document and code artifact (DTO)
- Verify files are written to disk
- Verify content is correct
- Use real config and temp workspace
- Use pytest fixtures from artifact_test_harness

@layer: Test Infrastructure (E2E)
@dependencies: ScaffoldArtifactTool, artifact_test_harness fixtures
@responsibilities:
  - Validate tool.execute() contract
  - Verify MCP protocol integration
  - Prove disk I/O works through tool layer
\"\"\"

# Standard library
from pathlib import Path

# Third-party
import pytest

# Project
from mcp_server.tools.scaffold_artifact import (
    ScaffoldArtifactInput,
    ScaffoldArtifactTool,
)
from mcp_server.managers.artifact_manager import ArtifactManager


@pytest.mark.asyncio
async def test_scaffold_tool_execute_design_doc_happy_path(
    artifact_manager: ArtifactManager,
    temp_workspace: Path,
) -> None:
    \"\"\"
    E2E: ScaffoldArtifactTool.execute() creates design document on disk.

    Tests the MCP protocol entry point (tool.execute()) for document artifacts.
    Validates that calling the tool directly (as MCP server would) results in
    correct file creation and content rendering.

    Args:
        artifact_manager: Fully wired ArtifactManager from test harness
        temp_workspace: Hermetic temp directory from test harness
    \"\"\"
    # Arrange: Initialize tool with injected manager
    tool = ScaffoldArtifactTool(manager=artifact_manager)

    # Arrange: Prepare tool input parameters (as MCP client would send)
    params = ScaffoldArtifactInput(
        artifact_type=\"design\",
        name=\"feature-authentication\",
        output_path=\"docs/design/feature-authentication.md\",
        context={
            \"issue_number\": \"123\",
            \"title\": \"User Authentication System\",
            \"author\": \"Test Engineer\",
            \"sections\": [\"Overview\", \"Requirements\", \"Implementation\"],
            \"status\": \"DRAFT\",
        },
    )

    # Act: Execute tool (simulates MCP protocol call)
    result = await tool.execute(params)

    # Assert: Tool returns success result
    assert not result.is_error, f\"Expected success, got error: {result.content}\"
    assert len(result.content) > 0
    assert \"checkmark\" in result.content[0][\"text\"] or \"Scaffolded\" in result.content[0][\"text\"]
    assert \"design\" in result.content[0][\"text\"]
    assert \"feature-authentication.md\" in result.content[0][\"text\"]

    # Assert: File written to disk at expected location
    output_file = temp_workspace / \"docs\" / \"design\" / \"feature-authentication.md\"
    assert output_file.exists(), f\"Expected file at {output_file}\"
    assert output_file.is_file(), \"Expected regular file, not directory\"

    # Assert: File content is correctly rendered
    content = output_file.read_text(encoding=\"utf-8\")
    assert len(content) > 0, \"File should not be empty\"
    assert \"User Authentication System\" in content, \"Title should be in content\"
    assert \"Issue: #123\" in content, \"Issue number should be formatted correctly\"
    assert \"Test Engineer\" in content, \"Author should be in content\"


@pytest.mark.asyncio
async def test_scaffold_tool_execute_dto_happy_path(
    artifact_manager: ArtifactManager,
    temp_workspace: Path,
) -> None:
    \"\"\"
    E2E: ScaffoldArtifactTool.execute() creates DTO code artifact on disk.

    Tests the MCP protocol entry point (tool.execute()) for code artifacts.
    Validates that Python code files are correctly generated with proper
    structure and formatting.

    Args:
        artifact_manager: Fully wired ArtifactManager from test harness
        temp_workspace: Hermetic temp directory from test harness
    \"\"\"
    # Arrange: Initialize tool with injected manager
    tool = ScaffoldArtifactTool(manager=artifact_manager)

    # Arrange: Prepare tool input parameters for DTO
    params = ScaffoldArtifactInput(
        artifact_type=\"dto\",
        name=\"UserCredentialsDTO\",
        output_path=\"mcp_server/dtos/user_credentials_dto.py\",
        context={
            \"description\": \"Data transfer object for user credentials\",
            \"fields\": [
                {\"name\": \"username\", \"type\": \"str\"},
                {\"name\": \"password_hash\", \"type\": \"str\"},
                {\"name\": \"email\", \"type\": \"str\"},
                {\"name\": \"is_active\", \"type\": \"bool\"},
            ],
        },
    )

    # Act: Execute tool (simulates MCP protocol call)
    result = await tool.execute(params)

    # Assert: Tool returns success result
    assert not result.is_error, f\"Expected success, got error: {result.content}\"
    assert len(result.content) > 0
    assert \"Scaffolded\" in result.content[0][\"text\"]
    assert \"dto\" in result.content[0][\"text\"]
    assert \"user_credentials_dto.py\" in result.content[0][\"text\"]

    # Assert: File written to disk at expected location
    output_file = temp_workspace / \"mcp_server\" / \"dtos\" / \"user_credentials_dto.py\"
    assert output_file.exists(), f\"Expected file at {output_file}\"
    assert output_file.is_file(), \"Expected regular file, not directory\"

    # Assert: File content is valid Python with correct structure
    content = output_file.read_text(encoding=\"utf-8\")
    assert len(content) > 0, \"File should not be empty\"

    # Verify Python structure
    assert \"from pydantic import BaseModel\" in content, \"Should import BaseModel\"
    assert \"class UserCredentialsDTO(BaseModel):\" in content, \"Should define DTO class\"
    assert \"Data transfer object for user credentials\" in content, \"Should include description\"

    # Verify all fields are present
    assert \"username: str\" in content, \"Should have username field\"
    assert \"password_hash: str\" in content, \"Should have password_hash field\"
    assert \"email: str\" in content, \"Should have email field\"
    assert \"is_active: bool\" in content, \"Should have is_active field\"


@pytest.mark.asyncio
async def test_scaffold_tool_execute_without_optional_output_path(
    artifact_manager: ArtifactManager,
    temp_workspace: Path,
) -> None:
    \"\"\"
    E2E: ScaffoldArtifactTool.execute() with auto-resolved output path.

    Tests that the tool can scaffold artifacts without explicit output_path,
    relying on the manager to auto-resolve the path based on artifact type
    and naming conventions.

    Args:
        artifact_manager: Fully wired ArtifactManager from test harness
        temp_workspace: Hermetic temp directory from test harness
    \"\"\"
    # Arrange: Initialize tool with injected manager
    tool = ScaffoldArtifactTool(manager=artifact_manager)

    # Arrange: Prepare input WITHOUT output_path (let manager auto-resolve)
    params = ScaffoldArtifactInput(
        artifact_type=\"dto\",
        name=\"ProductDTO\",
        output_path=None,  # Explicitly test auto-resolution
        context={
            \"description\": \"Product data transfer object\",
            \"fields\": [
                {\"name\": \"product_id\", \"type\": \"int\"},
                {\"name\": \"name\", \"type\": \"str\"},
                {\"name\": \"price\", \"type\": \"float\"},
            ],
        },
    )

    # Act: Execute tool
    result = await tool.execute(params)

    # Assert: Tool returns success result
    assert not result.is_error, f\"Expected success, got error: {result.content}\"
    assert \"Scaffolded\" in result.content[0][\"text\"]
    assert \"dto\" in result.content[0][\"text\"]

    # Note: Since output_path is None, the manager will auto-resolve.
    # The exact path depends on ArtifactManager implementation.
    # We verify that SOME file was created with the expected name.
    
    # Find all files matching the pattern (should be exactly one)
    dto_files = list(temp_workspace.rglob(\"*product_dto.py\"))
    assert len(dto_files) >= 1, f\"Expected at least one DTO file, found: {dto_files}\"

    # Verify content of the file
    dto_file = dto_files[0]
    content = dto_file.read_text(encoding=\"utf-8\")
    assert \"class ProductDTO(BaseModel):\" in content
    assert \"Product data transfer object\" in content
    assert \"product_id: int\" in content
    assert \"name: str\" in content
    assert \"price: float\" in content
'''

# Write the file
target_path = Path('tests/integration/mcp_server/test_scaffold_tool_execute_e2e.py')
target_path.parent.mkdir(parents=True, exist_ok=True)
target_path.write_text(content, encoding='utf-8')
print(f'Successfully created {target_path}')
