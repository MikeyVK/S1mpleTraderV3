# tests/parity/normalization.py
# template=generic version=f35abd82 created=2026-02-17T08:23Z updated=
"""ParityNormalization module.

Output normalization utilities for parity testing

@layer: Test Infrastructure
@dependencies: [None]
@responsibilities:
    - Normalize whitespace and line endings
    - Sort Python imports alphabetically
    - Mask dynamic timestamps
    - Provide semantic equivalence validation
"""

# Standard library
import difflib
import re

# Third-party

# Project modules


def normalize_whitespace(content: str) -> str:
    """Strip trailing whitespace and normalize line endings.

    Args:
        content: Raw file content with potential CRLF/LF mix

    Returns:
        Normalized content (LF-only, no trailing whitespace)
    """
    # CRLF → LF conversion
    normalized = content.replace("\r\n", "\n")

    # Strip trailing whitespace from each line (preserve empty lines)
    lines = normalized.split("\n")
    lines = [line.rstrip() for line in lines]

    return "\n".join(lines)


def normalize_imports(content: str) -> str:
    """Sort import statements alphabetically.

    Args:
        content: Python file content with imports

    Returns:
        Content with sorted imports (preserves groupings: stdlib, third-party, local)
    """
    lines = content.split("\n")
    result = []
    current_block = []
    in_import_block = False

    for line in lines:
        # Detect import lines
        is_import = bool(re.match(r"^(import |from )", line))

        if is_import:
            if not in_import_block:
                in_import_block = True
            current_block.append(line)
        else:
            # End of import block - sort and flush
            if in_import_block and current_block:
                result.extend(sorted(current_block))
                current_block = []
                in_import_block = False
            result.append(line)

    # Flush remaining imports
    if current_block:
        result.extend(sorted(current_block))

    return "\n".join(result)


def normalize_timestamps(content: str) -> str:
    """Mask dynamic timestamp values for stable comparison.

    Args:
        content: File content with SCAFFOLD metadata or template version timestamps

    Returns:
        Content with timestamps replaced by <TIMESTAMP> placeholder
    """
    # Match ISO8601 timestamps: 2026-02-17T08:23Z or 2026-01-15T10:30:00Z
    pattern = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?Z"
    return re.sub(pattern, "<TIMESTAMP>", content)


def normalize_output(content: str, file_type: str = "python") -> str:
    """Full normalization pipeline for parity testing.

    Args:
        content: Raw scaffolded file content
        file_type: "python" or "markdown" (determines normalization rules)

    Returns:
        Fully normalized content ready for equivalence comparison
    """
    normalized = content
    normalized = normalize_whitespace(normalized)
    normalized = normalize_timestamps(normalized)

    if file_type == "python":
        normalized = normalize_imports(normalized)

    return normalized


def assert_equivalent(v1_output: str, v2_output: str, allow_diffs: list[str] | None = None) -> None:
    """Assert semantic equivalence between v1 and v2 outputs.

    Args:
        v1_output: Normalized v1 template output
        v2_output: Normalized v2 template output
        allow_diffs: Optional list of acceptable difference patterns

    Raises:
        AssertionError: If outputs are not semantically equivalent
    """
    # Exact match - fast path
    if v1_output == v2_output:
        return

    # Generate diff
    v1_lines = v1_output.splitlines(keepends=True)
    v2_lines = v2_output.splitlines(keepends=True)
    diff = list(difflib.unified_diff(v1_lines, v2_lines, fromfile="v1", tofile="v2"))

    # If allow_diffs provided, check if all differences are allowed
    if allow_diffs:
        # Extract actual differences (lines starting with + or -)
        diff_lines = [line for line in diff if line.startswith("+") or line.startswith("-")]
        # Filter out diff metadata (+++, ---)
        diff_lines = [
            line for line in diff_lines if not line.startswith("+++") and not line.startswith("---")
        ]

        # Check if all differences contain at least one allowed pattern
        # TODO(future): Line-level pattern matching kan false positives/negatives geven
        # bij complexere multi-line diffs. Overweeg context-aware matching of AST-based
        # vergelijking voor robuustere equivalence validatie. (Post-Cycle 1 verharding)
        for diff_line in diff_lines:
            has_allowed_pattern = any(pattern in diff_line for pattern in allow_diffs)
            if not has_allowed_pattern:
                # This difference is not allowed
                diff_output = "".join(diff)
                raise AssertionError(f"Outputs are not semantically equivalent:\n\n{diff_output}")

        # All differences are allowed
        return

    # Semantic difference - fail with detailed diff
    diff_output = "".join(diff)
    raise AssertionError(f"Outputs are not semantically equivalent:\n\n{diff_output}")
