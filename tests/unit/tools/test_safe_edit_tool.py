# tests/unit/mcp_server/tools/test_safe_edit_tool.py
"""
Unit tests for SafeEditTool.

Tests according to TDD principles with comprehensive coverage.

@layer: Tests (Unit)
@dependencies: [pytest]
"""
# pyright: reportCallIssue=false, reportAttributeAccessIssue=false
# Suppress Pydantic FieldInfo false positives

# Standard library
from unittest.mock import MagicMock, patch

# Third-party
import pytest

# Module under test
from pydantic import ValidationError
from mcp_server.tools.safe_edit_tool import SafeEditTool, SafeEditInput
from mcp_server.validation.base import ValidationResult, ValidationIssue


class TestSafeEditTool:
    """Test suite for SafeEditTool."""

    @pytest.fixture
    def tool(self) -> SafeEditTool:
        """Fixture for SafeEditTool."""
        return SafeEditTool()

    @pytest.mark.asyncio
    async def test_missing_arguments(self, tool: SafeEditTool) -> None:
        """Test execution with missing arguments."""
        # Missing content key raises ValidationError
        with pytest.raises(ValidationError):
            SafeEditInput(path="test.py")

        # Missing path key raises ValidationError
        with pytest.raises(ValidationError):
            SafeEditInput(content="code")

    @pytest.mark.asyncio
    async def test_execute_strict_pass(self, tool: SafeEditTool) -> None:
        """Test strict mode with passing validation."""
        path = "test.py"
        content = "valid code"

        # Mock ValidationService.validate to return passing result
        async def mock_validate(*_, **__):
            return True, ""  # passed=True, no issues

        with patch.object(tool.validation_service, "validate", side_effect=mock_validate):
            # Mock file writing
            with patch("pathlib.Path.write_text") as mock_write, \
                 patch("pathlib.Path.parent") as mock_parent:

                mock_parent.mkdir = MagicMock()

                # Execute
                result = await tool.execute(
                    SafeEditInput(path=path, content=content, mode="strict")
                )

                # Verify
                assert "File saved successfully" in result.content[0]["text"]
                mock_write.assert_called_once_with(content, encoding="utf-8")

    @pytest.mark.asyncio
    async def test_execute_strict_fail(self, tool: SafeEditTool) -> None:
        """Test strict mode with failing validation."""
        path = "test.py"
        content = "invalid code"

        # Mock ValidationService.validate to return failing result
        async def mock_validate(*_, **__):
            return False, "\n\n**Validation Issues:**\n❌ Error\n"

        with patch.object(tool.validation_service, "validate", side_effect=mock_validate):
            with patch("pathlib.Path.write_text") as mock_write:
                # Execute
                result = await tool.execute(
                    SafeEditInput(path=path, content=content, mode="strict")
                )

                # Verify
                text = result.content[0]["text"]
                assert "Edit rejected" in text
                assert "Error" in text
                mock_write.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_interactive_fail(self, tool: SafeEditTool) -> None:
        """Test interactive mode allows saving even with validation failure."""
        path = "test.py"
        content = "invalid code"

        # Mock ValidationService.validate to return failing result
        async def mock_validate(*_, **__):
            return False, "\n\n**Validation Issues:**\n❌ Error\n"

        with patch.object(tool.validation_service, "validate", side_effect=mock_validate):
            with patch("pathlib.Path.write_text") as mock_write:
                # Execute
                result = await tool.execute(
                    SafeEditInput(path=path, content=content, mode="interactive")
                )

                # Verify
                text = result.content[0]["text"]
                assert "File saved successfully" in text
                assert "Saved with validation warnings" in text
                mock_write.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_verify_only(self, tool: SafeEditTool) -> None:
        """Test verify_only mode does not write to file."""
        path = "test.py"
        content = "code"

        # Mock ValidationService.validate to return passing result
        async def mock_validate(*_, **__):
            return True, ""

        with patch.object(tool.validation_service, "validate", side_effect=mock_validate):
            with patch("pathlib.Path.write_text") as mock_write:
                # Execute
                result = await tool.execute(
                    SafeEditInput(path=path, content=content, mode="verify_only")
                )

                # Verify
                text = result.content[0]["text"]
                assert "Validation Passed" in text
                mock_write.assert_not_called()

    @pytest.mark.asyncio
    async def test_fallback_validator_logic(self, tool: SafeEditTool) -> None:
        """Test implicit addition of base TemplateValidator for python files."""
        path = "script.py"
        content = "code"

        # Mock ValidationService.validate to return passing result
        # The fallback logic is now in ValidationService, not SafeEditTool
        async def mock_validate(*_, **__):
            return True, ""

        with patch.object(tool.validation_service, "validate", side_effect=mock_validate):
            # Execute
            await tool.execute(SafeEditInput(path=path, content=content))

            # Verify that validate was called (fallback logic is internal to service)
            tool.validation_service.validate.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_duplicate_diff_in_response(self, tool: SafeEditTool) -> None:
        """Test that diff preview appears only once in response (bug fix for Issue #125)."""
        path = "test.py"
        old_content = "old code"
        new_content = "new code"

        # Mock ValidationService.validate to return failing result WITH formatted issues
        async def mock_validate(*_, **__):
            # ValidationService._run_validators returns issues_text WITH header
            formatted_issues = "\n\n**Validation Issues:**\n❌ Syntax error\n"
            return False, formatted_issues

        with patch.object(tool.validation_service, "validate", side_effect=mock_validate):
            # Mock file read/write
            with patch("pathlib.Path.exists", return_value=True), \
                 patch("pathlib.Path.read_text", return_value=old_content), \
                 patch("pathlib.Path.write_text") as mock_write:

                # Execute in strict mode (should reject + show diff)
                result = await tool.execute(
                    SafeEditInput(path=path, content=new_content, mode="strict", show_diff=True)
                )

                # Verify diff appears exactly once
                text = result.content[0]["text"]
                diff_count = text.count("**Diff Preview:**")
                assert diff_count == 1, f"Expected 1 diff block, found {diff_count}"

                # Verify validation issues appear exactly once
                issues_count = text.count("**Validation Issues:**")
                assert issues_count == 1, f"Expected 1 issues block, found {issues_count}"

                # Verify actual error message appears exactly once
                error_count = text.count("Syntax error")
                assert error_count == 1, f"Expected 1 'Syntax error', found {error_count}"

                mock_write.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_duplicate_real_validation(self, tool: SafeEditTool) -> None:
        """Test with REAL validation (no mocks) to catch duplicate bug."""
        import tempfile
        from pathlib import Path
        
        # Create temp file with invalid Python
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("valid = True\n")
            temp_path = f.name
        
        try:
            # Try to write invalid Python syntax (should fail validation)
            result = await tool.execute(
                SafeEditInput(
                    path=temp_path,
                    content="invalid syntax here @@@ not python",
                    mode="strict",
                    show_diff=True
                )
            )
            
            # Check response
            text = result.content[0]["text"]
            print(f"\n\n=== RESPONSE TEXT ===\n{text}\n=== END ===\n\n")
            
            # Count occurrences
            diff_count = text.count("**Diff Preview:**")
            issues_count = text.count("**Validation Issues:**")
            
            assert diff_count == 1, f"Expected 1 diff block, found {diff_count}\n{text}"
            assert issues_count == 1, f"Expected 1 issues block, found {issues_count}\n{text}"
            
        finally:
            # Cleanup
            Path(temp_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_pattern_not_found_shows_context(self, tool: SafeEditTool) -> None:
        """Test that 'Pattern not found' error shows file context (Issue #125 - Priority 2)."""
        import tempfile
        from pathlib import Path
        
        # Create temp file with content
        content = """# Header\nline 1\nline 2\nline 3\nline 4\nline 5\n"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(content)
            temp_path = f.name
        
        try:
            # Try to replace pattern that doesn't exist
            result = await tool.execute(
                SafeEditInput(
                    path=temp_path,
                    search="this pattern does not exist",
                    replace="new text",
                    mode="strict"
                )
            )
            
            # Check error message includes context
            assert result.is_error, "Expected error result"
            text = result.content[0]["text"]
            print(f"\n\n=== ERROR TEXT ===\n{text}\n=== END ===\n\n")
            
            # Should mention pattern not found
            assert "not found" in text.lower(), f"Expected 'not found' in error\n{text}"
            
            # NEW: Should show file preview (first N lines)
            # This is the FAILING part - current code doesn't show context
            assert "# Header" in text or "line 1" in text, (
                f"Expected file context in error message\n{text}"
            )
            
        finally:
            # Cleanup
            Path(temp_path).unlink(missing_ok=True)
            Path(temp_path).unlink(missing_ok=True)
            # Cleanup
            Path(temp_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_concurrent_edits_blocked(self, tool: SafeEditTool, tmp_path) -> None:
        """Test that concurrent edits on same file are blocked (mutex protection)."""
        import asyncio
        from pathlib import Path
        
        # Create test file
        test_file = tmp_path / "concurrent_test.py"
        test_file.write_text("line 1\nline 2\nline 3\n")
        
        # Track edit order
        edit_results = []
        
        async def edit_task(task_id: int, delay: float) -> None:
            """Simulate concurrent edit."""
            await asyncio.sleep(delay)
            try:
                result = await tool.execute(
                    SafeEditInput(
                        path=str(test_file),
                        content=f"task {task_id} content\n",
                        mode="strict"
                    )
                )
                edit_results.append({"task": task_id, "success": True, "result": result})
            except Exception as e:
                edit_results.append({"task": task_id, "success": False, "error": str(e)})
        
        # Launch 3 concurrent edits with slight delays
        tasks = [
            edit_task(1, 0.0),
            edit_task(2, 0.01),
            edit_task(3, 0.02)
        ]
        
        await asyncio.gather(*tasks)
        
        # At least one should succeed
        # At least one should succeed, but NOT all if mutex works
        successes = [r for r in edit_results if r["success"]]
        failures = [r for r in edit_results if not r["success"]]
        
        # Without mutex: all 3 succeed
        # With mutex: only 1 succeeds, 2 are blocked
        assert len(failures) >= 2, (
            f"Expected at least 2 concurrent edits to be blocked by mutex, "
            f"but got {len(failures)} failures and {len(successes)} successes. "
            f"Results: {edit_results}"
        )
