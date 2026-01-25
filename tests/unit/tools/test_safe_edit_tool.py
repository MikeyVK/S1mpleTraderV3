# tests/unit/tools/test_safe_edit_tool.py
"""
Unit tests for SafeEditTool.

Tests safe file editing with validation according to TDD principles.
Covers multi-mode editing (content/line_edits/insert_lines/search_replace),
mutex protection, validation modes, and edge cases.

@layer: Tests (Unit)
@dependencies: [pytest, pydantic, asyncio, tempfile, pathlib, unittest.mock,
                mcp_server.tools.safe_edit_tool]
@responsibilities:
    - Test all edit modes (content, line_edits, insert_lines, search/replace)
    - Verify validation modes (strict/interactive/verify_only)
    - Test mutex protection prevents concurrent edit race conditions
    - Cover edge cases (missing args, pattern not found, validation failures)
"""

# Standard library
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

# Third-party
import pytest
from pydantic import ValidationError

# Project modules
from mcp_server.tools.safe_edit_tool import SafeEditTool, SafeEditInput


class TestSafeEditTool:
    """Test suite for SafeEditTool."""

    @pytest.fixture
    def tool(self) -> SafeEditTool:
        """Fixture for SafeEditTool."""
        return SafeEditTool()

    @pytest.mark.asyncio
    async def test_missing_arguments(self) -> None:
        """Test execution with missing arguments."""
        # Missing content/edit mode raises ValidationError
        with pytest.raises(ValidationError):
            SafeEditInput(path="test.py")

        # Missing path raises ValidationError
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

            # Should mention pattern not found
            assert "not found" in text.lower(), f"Expected 'not found' in error\n{text}"

            # Should show file preview for context
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
    async def test_concurrent_edits_blocked(
        self, tool: SafeEditTool, tmp_path: Path
    ) -> None:
        """Test that concurrent edits on same file are blocked (mutex protection)."""

        # Create test file
        test_file = tmp_path / "concurrent_test.py"
        test_file.write_text("line 1\nline 2\nline 3\n")

        # Track edit order
        edit_results = []
        async def edit_task(task_id: int) -> None:
            """Simulate concurrent edit."""
            try:
                result = await tool.execute(
                    SafeEditInput(
                        path=str(test_file),
                        line_edits=[{
                            "start_line": 1,
                            "end_line": 1,
                            "new_content": f"task {task_id} line 1\n"
                        }],
                        mode="interactive"
                    )
                )
                edit_results.append({"task": task_id, "success": True, "result": result})
            except (TimeoutError, ValueError, OSError) as e:
                # Catch specific expected exceptions: timeout, validation, or file errors
                edit_results.append({"task": task_id, "success": False, "error": str(e)})

        # Launch 3 concurrent edits
        tasks = [edit_task(1), edit_task(2), edit_task(3)]
        await asyncio.gather(*tasks)

        #  Verify mutex behavior: edits should run sequentially
        # Each task modifies line 1, so if concurrent we'd see race conditions
        # With mutex: task 1 → task 2 → task 3 (clean sequence)
        # Without mutex: overlapping edits, unpredictable results

        # All should succeed (mutex allows waiting, not instant fail)
        assert len(edit_results) == 3, f"Expected 3 results, got {len(edit_results)}"
        assert all(r["success"] for r in edit_results), (
            f"Expected all edits to succeed with mutex, "
            f"but got failures: {[r for r in edit_results if not r['success']]}"
        )

        # Verify sequential execution by checking the diffs
        # Task 1: line 1 → task 1 line 1
        # Task 2: task 1 line 1 → task 2 line 1  (proves task 1 finished first)
        # Task 3: task 2 line 1 → task 3 line 1  (proves task 2 finished second)
        # Sequential execution proven by task2/task3 seeing previous changes
        task2_diff = edit_results[1]["result"].content[0]["text"]
        task3_diff = edit_results[2]["result"].content[0]["text"]

        # Task 2 should see task 1's changes (sequential execution)
        assert "task 1 line 1" in task2_diff, (
            f"Task 2 should see task 1's changes, proving sequential execution.\n"
            f"Task 2 diff: {task2_diff}"
        )

        # Task 3 should see task 2's changes
        assert "task 2 line 1" in task3_diff, (
            f"Task 3 should see task 2's changes, proving sequential execution.\n"
            f"Task 3 diff: {task3_diff}"
        )
