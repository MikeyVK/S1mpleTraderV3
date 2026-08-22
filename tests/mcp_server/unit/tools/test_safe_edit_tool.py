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
from mcp_server.core.operation_notes import NoteContext
from mcp_server.schemas.tool_outputs import SafeEditOutput
from mcp_server.tools.safe_edit_tool import (
    AppendOp,
    PatternReplaceOp,
    ReplaceOp,
    RewriteOp,
    SafeEditInput,
    SafeEditTool,
)
from mcp_server.validation.base import ValidationIssue


class TestSafeEditTool:
    """Test suite for SafeEditTool."""

    @pytest.fixture
    def tool(self) -> SafeEditTool:
        """Fixture for SafeEditTool."""
        return SafeEditTool()

    @pytest.mark.asyncio
    async def test_missing_arguments(self) -> None:
        """Test execution with missing arguments."""
        # Missing operation raises ValidationError
        with pytest.raises(ValidationError):
            SafeEditInput(path="test.py")

        # Missing path raises ValidationError
        with pytest.raises(ValidationError):
            SafeEditInput(operation={"op": "rewrite", "content": "code"})

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_execute_strict_pass(self, tool: SafeEditTool, tmp_path: Path) -> None:
        """Test strict mode with passing validation."""
        test_file = tmp_path / "test.py"
        test_file.write_text("old", encoding="utf-8")
        content = "valid code"

        async def mock_validate(
            *_: object, **__: object
        ) -> tuple[bool, tuple[ValidationIssue, ...]]:
            return True, ()

        with (
            patch.object(tool.validation_service, "validate", side_effect=mock_validate),
            patch.object(tool.file_writer, "write_text") as mock_write,
        ):
            result = await tool.execute(
                SafeEditInput(
                    path=str(test_file),
                    operation={"op": "rewrite", "content": content},
                    mode="strict",
                ),
                NoteContext(),
            )

            assert isinstance(result, SafeEditOutput)
            assert result.success is True
            assert result.written is True
            mock_write.assert_called_once_with(Path(str(test_file)), content)

    @pytest.mark.asyncio
    async def test_execute_strict_fail(self, tool: SafeEditTool, tmp_path: Path) -> None:
        """Test strict mode with failing validation."""
        test_file = tmp_path / "test.py"
        test_file.write_text("old", encoding="utf-8")
        content = "invalid code"

        issue = ValidationIssue(message="Error")

        async def mock_validate(
            *_: object, **__: object
        ) -> tuple[bool, tuple[ValidationIssue, ...]]:
            return False, (issue,)

        with (
            patch.object(tool.validation_service, "validate", side_effect=mock_validate),
            patch.object(tool.file_writer, "write_text") as mock_write,
        ):
            result = await tool.execute(
                SafeEditInput(
                    path=str(test_file),
                    operation={"op": "rewrite", "content": content},
                    mode="strict",
                ),
                NoteContext(),
            )

            assert isinstance(result, SafeEditOutput)
            assert result.error_message is not None
            assert "rejected" in result.error_message.lower()
            assert result.issues == (issue,)
            assert result.issues[0] is issue
            mock_write.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_interactive_fail(self, tool: SafeEditTool, tmp_path: Path) -> None:
        """Test interactive mode allows saving even with validation failure."""
        test_file = tmp_path / "test.py"
        test_file.write_text("old", encoding="utf-8")
        content = "invalid code"

        issue = ValidationIssue(message="Error")

        async def mock_validate(
            *_: object, **__: object
        ) -> tuple[bool, tuple[ValidationIssue, ...]]:
            return False, (issue,)

        with (
            patch.object(tool.validation_service, "validate", side_effect=mock_validate),
            patch.object(tool.file_writer, "write_text") as mock_write,
        ):
            result = await tool.execute(
                SafeEditInput(
                    path=str(test_file),
                    operation={"op": "rewrite", "content": content},
                    mode="interactive",
                ),
                NoteContext(),
            )

            assert isinstance(result, SafeEditOutput)
            assert result.success is True
            assert result.written is True
            assert result.passed is False
            assert result.issues == (issue,)
            assert result.issues[0] is issue
            mock_write.assert_called_once_with(Path(str(test_file)), content)

    @pytest.mark.asyncio
    async def test_execute_verify_only(self, tool: SafeEditTool, tmp_path: Path) -> None:
        """Test verify_only mode does not write to file."""
        test_file = tmp_path / "test.py"
        test_file.write_text("old", encoding="utf-8")
        content = "code"

        async def mock_validate(
            *_: object, **__: object
        ) -> tuple[bool, tuple[ValidationIssue, ...]]:
            return True, ()

        with (
            patch.object(tool.validation_service, "validate", side_effect=mock_validate),
            patch.object(tool.file_writer, "write_text") as mock_write,
        ):
            result = await tool.execute(
                SafeEditInput(
                    path=str(test_file),
                    operation={"op": "rewrite", "content": content},
                    mode="verify_only",
                ),
                NoteContext(),
            )

            assert isinstance(result, SafeEditOutput)
            assert result.success is True
            assert result.written is False
            assert result.passed is True
            mock_write.assert_not_called()

    @pytest.mark.asyncio
    async def test_fallback_validator_logic(self, tool: SafeEditTool, tmp_path: Path) -> None:
        """Test implicit addition of base TemplateValidator for python files."""
        test_file = tmp_path / "script.py"
        test_file.write_text("code", encoding="utf-8")
        content = "code"

        async def mock_validate(
            *_: object, **__: object
        ) -> tuple[bool, tuple[ValidationIssue, ...]]:
            return True, ()

        with patch.object(tool.validation_service, "validate", side_effect=mock_validate):
            await tool.execute(
                SafeEditInput(
                    path=str(test_file),
                    operation={"op": "rewrite", "content": content},
                ),
                NoteContext(),
            )
            tool.validation_service.validate.assert_called_once()

    @pytest.mark.asyncio
    async def test_rejects_legacy_show_diff_argument(self, tool: SafeEditTool) -> None:
        """Contract test: SafeEditInput must reject the removed show_diff argument."""

        del tool  # Contract is enforced at input-model boundary

        with pytest.raises(ValidationError) as exc_info:
            SafeEditInput.model_validate(
                {
                    "path": "test.py",
                    "operation": {"op": "rewrite", "content": "new code"},
                    "mode": "strict",
                    "show_diff": True,
                }
            )

        assert "show_diff" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_no_duplicate_real_validation(self, tool: SafeEditTool) -> None:
        """Test with REAL validation (no duplicate validation issues in response)."""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("valid = True\n")
            temp_path = f.name

        try:
            result = await tool.execute(
                SafeEditInput(
                    path=temp_path,
                    operation={"op": "rewrite", "content": "invalid syntax here @@@ not python"},
                    mode="strict",
                ),
                NoteContext(),
            )

            assert isinstance(result, SafeEditOutput)
            assert result.success is False
            assert result.error_message is not None
            assert result.issues
            assert any("syntax" in issue.message.lower() for issue in result.issues)

        finally:
            Path(temp_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_pattern_not_found_shows_context(self, tool: SafeEditTool) -> None:
        """Test that 'Pattern not found' error shows file context."""

        content = "# Header\nline 1\nline 2\nline 3\nline 4\nline 5\n"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            result = await tool.execute(
                SafeEditInput(
                    path=temp_path,
                    operation={
                        "op": "replace",
                        "target_content": "this pattern does not exist",
                        "replacement": "new text",
                    },
                    mode="strict",
                ),
                NoteContext(),
            )

            assert isinstance(result, SafeEditOutput)
            assert result.success is False
            assert result.error_message is not None
            assert "not found" in result.error_message.lower()
            assert "# Header" in result.error_message or "line 1" in result.error_message

        finally:
            Path(temp_path).unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_concurrent_edits_blocked(self, tool: SafeEditTool, tmp_path: Path) -> None:
        """Test that concurrent edits on same file are blocked (mutex protection)."""

        test_file = tmp_path / "concurrent_test.py"
        test_file.write_text("line 1\nline 2\nline 3\n")

        edit_results: list[dict] = []

        async def edit_task(task_id: int) -> None:
            try:
                result = await tool.execute(
                    SafeEditInput(
                        path=str(test_file),
                        operation={
                            "op": "rewrite",
                            "content": f"task {task_id} line 1\nline 2\nline 3\n",
                        },
                        mode="interactive",
                    ),
                    NoteContext(),
                )
                edit_results.append({"task": task_id, "success": True, "result": result})
            except (TimeoutError, ValueError, OSError) as e:
                edit_results.append({"task": task_id, "success": False, "error": str(e)})

        await asyncio.gather(edit_task(1), edit_task(2), edit_task(3))

        assert len(edit_results) == 3, f"Expected 3 results, got {len(edit_results)}"
        assert all(r["success"] for r in edit_results), (
            f"Expected all edits to succeed with mutex, "
            f"but got failures: {[r for r in edit_results if not r['success']]}"
        )

        # Verify sequential execution via final file state — the last task wins on line 1.
        final_content = test_file.read_text()
        assert final_content.startswith("task 3 line 1\n"), (
            "Expected the last sequential edit to win and persist in the file.\n"
            f"Final file content: {final_content}"
        )


class TestSafeEditInputOperations:
    """Test suite verifying 4-operation SafeEditInput Pydantic models."""

    def test_replace_op_schema(self) -> None:
        """Verify ReplaceOp model parsing and extra='forbid' validation."""
        op = ReplaceOp(target_content="foo", replacement="bar", search_window=[1, 10])
        assert op.op == "replace"
        assert op.target_content == "foo"
        assert op.replacement == "bar"
        assert op.search_window == [1, 10]

    def test_append_op_schema(self) -> None:
        """Verify AppendOp model parsing and default values."""
        op = AppendOp(content="new line", anchor="## Section", position="before")
        assert op.op == "append"
        assert op.content == "new line"
        assert op.anchor == "## Section"
        assert op.position == "before"

    def test_rewrite_op_schema(self) -> None:
        """Verify RewriteOp model parsing."""
        op = RewriteOp(content="complete file content")
        assert op.op == "rewrite"
        assert op.content == "complete file content"

    def test_pattern_replace_op_schema(self) -> None:
        """Verify PatternReplaceOp model parsing."""
        op = PatternReplaceOp(pattern=r"def \w+", replacement="def main", regex=True)
        assert op.op == "pattern_replace"
        assert op.pattern == r"def \w+"
        assert op.replacement == "def main"
        assert op.regex is True

    def test_operation_type_discriminator_parsing(self) -> None:
        """Verify SafeEditInput parses operation dictionary via op discriminator."""
        inp = SafeEditInput(
            path="file.py",
            operation={"op": "replace", "target_content": "old", "replacement": "new"},
        )
        assert isinstance(inp.operation, ReplaceOp)
        assert inp.operation.target_content == "old"

    def test_extra_forbid_on_operations(self) -> None:
        """Verify unrecognized fields raise ValidationError on operations."""
        with pytest.raises(ValidationError):
            ReplaceOp(target_content="a", replacement="b", unknown_field="invalid")

        with pytest.raises(ValidationError):
            SafeEditInput(
                path="file.py",
                operation={"op": "rewrite", "content": "x"},
                invalid_param="forbidden",
            )


class TestSafeEditExecutionHandlers:
    """Unit tests for SafeEditTool execution handlers and governance rules."""

    @pytest.fixture
    def tool(self) -> SafeEditTool:
        """Fixture for SafeEditTool."""
        return SafeEditTool()

    @pytest.mark.asyncio
    async def test_must_exist_governance_enforcement(
        self, tool: SafeEditTool, tmp_path: Path
    ) -> None:
        """Non-existent file path returns governance error referencing scaffold_artifact."""
        non_existent_file = tmp_path / "does_not_exist.py"
        result = await tool.execute(
            SafeEditInput(
                path=str(non_existent_file),
                operation={"op": "rewrite", "content": "x = 1\n"},
            ),
            NoteContext(),
        )
        assert result.success is False
        assert result.written is False
        assert result.error_message is not None
        assert "does not exist" in result.error_message.lower()
        assert "scaffold_artifact" in result.error_message

    @pytest.mark.asyncio
    async def test_execute_replace_op_success(self, tool: SafeEditTool, tmp_path: Path) -> None:
        """ReplaceOp replaces target_content in existing file."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def old_func():\n    return 1\n", encoding="utf-8")

        result = await tool.execute(
            SafeEditInput(
                path=str(test_file),
                operation={
                    "op": "replace",
                    "target_content": "old_func",
                    "replacement": "new_func",
                },
            ),
            NoteContext(),
        )
        assert result.success is True
        assert result.written is True
        assert "def new_func():" in test_file.read_text(encoding="utf-8")

    @pytest.mark.asyncio
    async def test_execute_replace_op_search_window(
        self, tool: SafeEditTool, tmp_path: Path
    ) -> None:
        """ReplaceOp with search_window scopes replacement to line range."""
        test_file = tmp_path / "test.py"
        test_file.write_text("foo\nbar\nfoo\n", encoding="utf-8")

        result = await tool.execute(
            SafeEditInput(
                path=str(test_file),
                operation={
                    "op": "replace",
                    "target_content": "foo",
                    "replacement": "baz",
                    "search_window": [3, 3],
                },
            ),
            NoteContext(),
        )
        assert result.success is True
        assert test_file.read_text(encoding="utf-8") == "foo\nbar\nbaz\n"

    @pytest.mark.asyncio
    async def test_execute_replace_op_mismatch_with_fuzzy_diagnostic(
        self, tool: SafeEditTool, tmp_path: Path
    ) -> None:
        """ReplaceOp mismatch includes difflib fuzzy suggestions in error message."""
        test_file = tmp_path / "test.py"
        test_file.write_text("def process_items():\n    pass\n", encoding="utf-8")

        result = await tool.execute(
            SafeEditInput(
                path=str(test_file),
                operation={
                    "op": "replace",
                    "target_content": "def process_item():",
                    "replacement": "def run():",
                },
            ),
            NoteContext(),
        )
        assert result.success is False
        assert result.written is False
        assert result.error_message is not None
        assert "not found in file" in result.error_message.lower()
        assert "did you mean" in result.error_message.lower()
        assert "process_items" in result.error_message

    @pytest.mark.asyncio
    async def test_execute_append_op_eof(self, tool: SafeEditTool, tmp_path: Path) -> None:
        """AppendOp with anchor=None appends to file end."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("line 1\n", encoding="utf-8")

        result = await tool.execute(
            SafeEditInput(
                path=str(test_file),
                operation={"op": "append", "content": "line 2"},
            ),
            NoteContext(),
        )
        assert result.success is True
        assert test_file.read_text(encoding="utf-8") == "line 1\nline 2\n"

    @pytest.mark.asyncio
    async def test_execute_append_op_anchor_after(self, tool: SafeEditTool, tmp_path: Path) -> None:
        """AppendOp with anchor and position='after' inserts after anchor line."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("# Section 1\ncontent 1\n", encoding="utf-8")

        result = await tool.execute(
            SafeEditInput(
                path=str(test_file),
                operation={
                    "op": "append",
                    "anchor": "# Section 1",
                    "content": "added line",
                    "position": "after",
                },
            ),
            NoteContext(),
        )
        assert result.success is True
        assert test_file.read_text(encoding="utf-8") == "# Section 1\nadded line\ncontent 1\n"

    @pytest.mark.asyncio
    async def test_execute_append_op_anchor_before(
        self, tool: SafeEditTool, tmp_path: Path
    ) -> None:
        """AppendOp with anchor and position='before' inserts before anchor line."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("# Section 1\ncontent 1\n", encoding="utf-8")

        result = await tool.execute(
            SafeEditInput(
                path=str(test_file),
                operation={
                    "op": "append",
                    "anchor": "# Section 1",
                    "content": "# Header",
                    "position": "before",
                },
            ),
            NoteContext(),
        )
        assert result.success is True
        assert test_file.read_text(encoding="utf-8") == "# Header\n# Section 1\ncontent 1\n"

    @pytest.mark.asyncio
    async def test_execute_append_op_mismatch_with_fuzzy_diagnostic(
        self, tool: SafeEditTool, tmp_path: Path
    ) -> None:
        """AppendOp anchor mismatch includes difflib fuzzy suggestions."""
        test_file = tmp_path / "test.py"
        test_file.write_text("class DataProcessor:\n    pass\n", encoding="utf-8")

        result = await tool.execute(
            SafeEditInput(
                path=str(test_file),
                operation={
                    "op": "append",
                    "anchor": "class DataProcessors:",
                    "content": "    # TODO",
                },
            ),
            NoteContext(),
        )
        assert result.success is False
        assert result.error_message is not None
        assert "anchor" in result.error_message.lower()
        assert "did you mean" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_execute_rewrite_op_success(self, tool: SafeEditTool, tmp_path: Path) -> None:
        """RewriteOp replaces entire file content on existing file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("old content", encoding="utf-8")

        result = await tool.execute(
            SafeEditInput(
                path=str(test_file),
                operation={"op": "rewrite", "content": "new complete content\n"},
            ),
            NoteContext(),
        )
        assert result.success is True
        assert test_file.read_text(encoding="utf-8") == "new complete content\n"

    @pytest.mark.asyncio
    async def test_execute_pattern_replace_op_regex(
        self, tool: SafeEditTool, tmp_path: Path
    ) -> None:
        """PatternReplaceOp performs regex substitution."""
        test_file = tmp_path / "test.py"
        test_file.write_text("v1.0.0 and v2.1.3", encoding="utf-8")

        result = await tool.execute(
            SafeEditInput(
                path=str(test_file),
                operation={
                    "op": "pattern_replace",
                    "pattern": r"v\d+\.\d+\.\d+",
                    "replacement": "vLATEST",
                    "regex": True,
                },
            ),
            NoteContext(),
        )
        assert result.success is True
        assert test_file.read_text(encoding="utf-8") == "vLATEST and vLATEST"

    @pytest.mark.asyncio
    async def test_execute_pattern_replace_op_invalid_regex(
        self, tool: SafeEditTool, tmp_path: Path
    ) -> None:
        """PatternReplaceOp with invalid regex returns error."""
        test_file = tmp_path / "test.py"
        test_file.write_text("content", encoding="utf-8")

        result = await tool.execute(
            SafeEditInput(
                path=str(test_file),
                operation={
                    "op": "pattern_replace",
                    "pattern": r"([unclosed",
                    "replacement": "x",
                    "regex": True,
                },
            ),
            NoteContext(),
        )
        assert result.success is False
        assert result.error_message is not None
        assert "regex" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_atomic_file_writer_integration(self, tmp_path: Path) -> None:
        """SafeEditTool uses injected IAtomicFileWriter for writes."""
        mock_writer = MagicMock()
        tool = SafeEditTool(file_writer=mock_writer)
        test_file = tmp_path / "test.py"
        test_file.write_text("initial", encoding="utf-8")

        result = await tool.execute(
            SafeEditInput(
                path=str(test_file),
                operation={"op": "rewrite", "content": "updated\n"},
            ),
            NoteContext(),
        )
        assert result.success is True
        mock_writer.write_text.assert_called_once_with(Path(str(test_file)), "updated\n")
