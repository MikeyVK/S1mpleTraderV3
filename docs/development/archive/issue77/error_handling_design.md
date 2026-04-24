# MCP Tool Error Handling Infrastructure

**Status:** DRAFT
**Author:** GitHub Copilot
**Created:** 2026-01-03
**Last Updated:** 2026-01-03
**Issue:** #77

---

## 1. Overview

### 1.1 Purpose

This document describes the design of a global error handling infrastructure for MCP tools that prevents VS Code from permanently disabling tools when exceptions occur. The solution implements a decorator-based approach that converts uncaught exceptions into structured error responses, keeping tools available during chat sessions.

### 1.2 Scope

**In Scope:**
- Global `@tool_error_handler` decorator for all MCP tools
- Error classification system (user/config/system/bug)
- Structured error response format compatible with MCP protocol
- Integration strategy for existing 44 MCP tools
- Logging and debugging infrastructure

**Out of Scope:**
- VS Code MCP client behavior (external dependency)
- Individual tool-specific error recovery logic
- User-facing error UI (handled by VS Code)
- Network/API retry mechanisms (handled by individual tools)

### 1.3 Related Documents

- [Core Principles](docs/architecture/CORE_PRINCIPLES.md)
- [Architectural Shifts](docs/architecture/ARCHITECTURAL_SHIFTS.md)

---

## 2. Background

### 2.1 Current State

**Problem:** MCP tool exceptions cause VS Code to permanently disable tools during chat sessions.

**Current Behavior:**
1. MCP tool raises uncaught exception (e.g., `ValueError`, `FileNotFoundError`)
2. VS Code MCP client receives exception as tool crash
3. VS Code marks tool as "disabled" for safety
4. Tool remains disabled for entire chat session
5. Agent sees: "Tool is currently disabled by the user" (misleading message)
6. Only recovery: Restart VS Code or start new chat

**Evidence from Logs:**
```
2026-01-03 12:35:50 [error] Error from tool mcp_st3-workflow_safe_edit_file
2026-01-03 12:44:43 [error] Error from tool read_file: cannot open file...
```

**Impact:**
- Affects all 44 MCP tools in st3-workflow server
- Breaks chat-based development workflow
- Agent cannot debug or recover
- User frustration and lost productivity

### 2.2 Problem Statement

**Root Cause:** Uncaught exceptions in MCP tools are interpreted by VS Code as "tool crashes" rather than normal error conditions, causing the client to disable tools permanently for the session.

**Desired State:** Tools return structured error responses that VS Code treats as valid tool outputs, keeping tools available while providing actionable error information to the agent.

### 2.3 Requirements

#### Functional Requirements
- [ ] **FR1:** All tool exceptions MUST be caught and converted to structured error responses
- [ ] **FR2:** Error responses MUST include error type, message, and context
- [ ] **FR3:** Tools MUST remain "enabled" in VS Code after returning errors
- [ ] **FR4:** Errors MUST be logged to server logs for debugging
- [ ] **FR5:** Decorator MUST preserve tool function signatures and metadata

#### Non-Functional Requirements
- [ ] **NFR1:** Performance - Decorator adds <1ms overhead per tool call
- [ ] **NFR2:** Testability - All error paths must be unit testable
- [ ] **NFR3:** Maintainability - Single point of change for error handling logic
- [ ] **NFR4:** Backward Compatibility - Existing tool implementations unchanged

---

## 3. Design

### 3.1 Architecture Overview

The error handling infrastructure consists of three layers:

```
┌─────────────────────────────────────────────────┐
│           VS Code MCP Client                     │
│  (Receives structured error responses)           │
└────────────────┬────────────────────────────────┘
                 │ MCP Protocol
┌────────────────▼────────────────────────────────┐
│      @tool_error_handler Decorator               │
│  - Catches all exceptions                        │
│  - Classifies error type                         │
│  - Logs to server logs                           │
│  - Returns ToolResult.error()                    │
└────────────────┬────────────────────────────────┘
                 │ Wraps
┌────────────────▼────────────────────────────────┐
│            MCP Tool Implementation               │
│  - git_checkout, safe_edit_file, etc.           │
│  - Raises exceptions normally                    │
│  - No error handling required                    │
└──────────────────────────────────────────────────┘
```

### 3.2 Error Classification

Errors are classified into four categories to provide context:

| Category | Description | Example | Recovery |
|----------|-------------|---------|----------|
| **USER** | Invalid user input | Missing required field | Agent fixes input, retries |
| **CONFIG** | Configuration issue | File not found | User fixes config, retry |
| **SYSTEM** | External system failure | GitHub API down | Wait and retry later |
| **BUG** | Internal code bug | Unexpected exception | Report to developers |

### 3.3 Decorator Implementation

```python
# File: mcp_server/core/error_handling.py

import functools
import logging
from typing import TypeVar, Callable, Any
from mcp.types import ToolResult

logger = logging.getLogger(__name__)

T = TypeVar('T')

def tool_error_handler(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator that catches all tool exceptions and returns structured errors.
    
    Prevents VS Code from disabling tools by converting exceptions into
    valid ToolResult.error() responses.
    
    Usage:
        @tool_error_handler
        async def execute(self, params: SomeInput) -> ToolResult:
            # Tool implementation
            ...
    """
    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> ToolResult:
        try:
            return await func(*args, **kwargs)
        except ValueError as e:
            # USER error - invalid input
            error_msg = f"Invalid input: {str(e)}"
            logger.warning(f"[USER ERROR] {func.__name__}: {error_msg}")
            return ToolResult.error(error_msg)
        except FileNotFoundError as e:
            # CONFIG error - missing file
            error_msg = f"Configuration error: {str(e)}"
            logger.error(f"[CONFIG ERROR] {func.__name__}: {error_msg}")
            return ToolResult.error(error_msg)
        except Exception as e:
            # SYSTEM/BUG - unexpected error
            error_msg = f"Unexpected error: {type(e).__name__}: {str(e)}"
            logger.exception(f"[BUG] {func.__name__}: {error_msg}")
            return ToolResult.error(error_msg)
    
    return wrapper
```

### 3.4 Error Response Format

All errors return `ToolResult.error(message)` which VS Code treats as valid tool output:

```python
# Success case
return ToolResult.text("Switched to branch: feature/123")

# Error case (same ToolResult type, different method)
return ToolResult.error("Branch 'feature/123' not found")
```

**Key Insight:** Using `ToolResult.error()` instead of raising exceptions keeps the tool "enabled" in VS Code.
```

---

## 4. Implementation Plan

### 4.1 Phases

#### Phase 1: Core Decorator (TDD)

**Goal:** Implement and test @tool_error_handler decorator

**Tasks:**
- [ ] Create `mcp_server/core/error_handling.py`
- [ ] Write failing tests for decorator (RED)
  - Test ValueError → ToolResult.error (USER)
  - Test FileNotFoundError → ToolResult.error (CONFIG)
  - Test generic Exception → ToolResult.error (BUG)
  - Test successful execution (passthrough)
  - Test async function wrapping
  - Test function metadata preservation
- [ ] Implement decorator (GREEN)
- [ ] Refactor and add logging (REFACTOR)

**Exit Criteria:**
- [ ] All tests passing (6+ tests)
- [ ] Quality gates passed (10/10 Pylint)
- [ ] Decorator preserves function signatures

#### Phase 2: Tool Integration

**Goal:** Apply decorator to all MCP tools

**Strategy:** Update base tool class to apply decorator automatically

**Tasks:**
- [ ] Modify `mcp_server/core/base_tool.py` to apply decorator
- [ ] OR: Apply decorator to each tool's `execute()` method
- [ ] Test with 3-5 representative tools
- [ ] Verify tools stay "enabled" after errors in VS Code
- [ ] Document integration pattern

**Exit Criteria:**
- [ ] All 44 tools using decorator
- [ ] Manual testing: tool errors don't disable tools
- [ ] Logging shows error classification

#### Phase 3: Validation & Documentation

**Goal:** Validate solution and document usage

**Tasks:**
- [ ] Test error scenarios in live VS Code chat session
- [ ] Verify tools remain available after errors
- [ ] Update tool development documentation
- [ ] Add examples to error_handling.py docstrings

**Exit Criteria:**
- [ ] Tool availability confirmed in VS Code
- [ ] Documentation updated
- [ ] Issue #77 resolved

### 4.2 Testing Strategy

| Test Type | Scope | Count Target | Coverage |
|-----------|-------|--------------|----------|
| Unit | Decorator | 6+ tests | All error paths |
| Integration | Sample tools | 3-5 tools | Representative tools |
| Manual | VS Code | Error scenarios | Tool availability |

**Test Cases:**
1. **User Error:** Invalid parameter value → Error message, tool stays enabled
2. **Config Error:** Missing file → Error message, tool stays enabled
3. **System Error:** GitHub API failure → Error message, tool stays enabled
4. **Success:** Valid input → Normal execution, no decorator interference

---

## 5. Alternatives Considered

### Alternative A: Try-Catch in Every Tool

**Description:** Add try-catch blocks to each of 44 tools individually

**Pros:**
- Fine-grained control per tool
- Tool-specific error messages

**Cons:**
- Code duplication across 44 tools
- Easy to forget in new tools
- Inconsistent error handling
- High maintenance burden

**Decision:** ❌ Rejected - Violates DRY principle, not maintainable

### Alternative B: Base Class Error Handling

**Description:** Implement error handling in base tool class `call_tool()` method

**Pros:**
- Centralized logic
- Automatic for all tools
- Similar to decorator approach

**Cons:**
- Requires modifying base class
- May conflict with MCP server internals
- Less flexible than decorator

**Decision:** ⚠️ Viable alternative - Consider if decorator doesn't work

### Alternative C: MCP Server Middleware

**Description:** Add error handling at MCP server level (outside tools)

**Pros:**
- Most centralized approach
- Catches errors from all sources

**Cons:**
- Requires understanding MCP server internals
- May be overridden by framework
- Less control over error classification

**Decision:** ❌ Rejected - Too invasive, harder to test

**Selected Approach:** Decorator (@tool_error_handler) - Best balance of centralization, testability, and flexibility

---

## 6. Open Questions

- [ ] **Q1:** Should we add error codes (e.g., `E_USER_001`) for programmatic handling?
  - **Status:** Defer to future iteration
  - **Rationale:** Start simple, add if needed

- [ ] **Q2:** Should different error categories have different log levels?
  - **Proposal:** USER=warning, CONFIG=error, BUG=exception
  - **Status:** ✅ Included in design

- [ ] **Q3:** Should we include stack traces in error messages sent to VS Code?
  - **Proposal:** No - stack traces in logs only, not in chat
  - **Rationale:** Agent doesn't need stack traces, users find them confusing
  - **Status:** ✅ Decided

- [ ] **Q4:** How to handle async vs sync tools?
  - **Status:** Decorator handles both (using functools.wraps)
  - **Note:** May need separate sync decorator if async wrapper causes issues

---

## 7. Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-01-03 | Use decorator pattern | Centralized, testable, non-invasive |
| 2026-01-03 | 4-category error classification | Provides actionable context without complexity |
| 2026-01-03 | Return ToolResult.error() | Keeps tools enabled in VS Code |
| 2026-01-03 | Logs only, no stack traces in chat | Cleaner error messages for agent |

---

## 8. References

- [TDD Workflow](docs/coding_standards/TDD_WORKFLOW.md)
- [Quality Gates](docs/coding_standards/QUALITY_GATES.md)
