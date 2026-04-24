# Issue #77 Research: MCP Tool Error Handling & VS Code Tool Availability

**Date:** 2026-01-03
**Branch:** bug/77-git-checkout-sync (will be renamed)
**Status:** Root cause identified, awaiting fix

---

## Executive Summary

Investigation into Issue #77 (git_checkout state sync) revealed a **more fundamental bug**: MCP server error handling causes VS Code to permanently disable tools during chat sessions.

**Primary Bug:** MCP tool errors → VS Code marks tools as "disabled" → Agent cannot use tools
**Secondary Bug:** git_checkout missing state synchronization (original issue)

---

## Discovery Timeline

### Initial Investigation (2026-01-03 10:00)
- **Target:** Fix git_checkout tool to sync PhaseStateEngine state after branch switch
- **Scope:** Single tool enhancement

### Root Cause Discovery (2026-01-03 12:30)
- **Trigger:** Tools working via CLI but "disabled" in chat
- **Symptom:** Agent reports "tool disabled" without explanation
- **Pattern:** Affects all MCP tools after first error in session

### Error Analysis (2026-01-03 12:35-13:00)
- Analyzed VS Code logs
- Found MCP server errors during tool execution
- Identified Pydantic ModelPrivateAttr error at server startup

---

## Primary Bug: MCP Error Handling → Tool Availability

### Symptoms

1. **Tools work in CLI but not in chat:**
   - ```bash
   gh issue view 77  # ✅ Works
   ```
   - Chat agent: "tool mcp_st3-workflow_get_issue is disabled" ❌

2. **No error visibility in chat:**
   - Agent only sees: "Tool is currently disabled by the user"
   - Real error hidden in VS Code logs
   - No way for agent to recover or debug

3. **Persistent across session:**
   - Once tool fails, stays "disabled" for entire chat
   - Requires VS Code restart to recover
   - Affects ALL MCP tools from same server

4. **Started after 2026-01-01:**
   - Coincides with VS Code update period
   - Likely stricter error handling in new version

### Root Causes Identified

#### 1. Pydantic v2 Incompatibility in label_config.py

**Error from MCP server log:**
```
2026-01-03 12:38:25.982 [ERROR] mcp_server.config.label_startup
"Unexpected error loading labels.yaml: 'ModelPrivateAttr' object has no attribute 'labels'"
```

**Location:** mcp_server/config/label_config.py lines 108-112

**Problem:**
```python
class LabelConfig(BaseModel):
    # ❌ Class-level attributes incompatible with Pydantic v2
    _instance: Optional["LabelConfig"] = None
    _labels_by_name: dict[str, Label] = {}
    _labels_by_category: dict[str, list[Label]] = {}
```

**Fix Required:**
```python
from pydantic import PrivateAttr
from typing import ClassVar

class LabelConfig(BaseModel):
    # ✅ Singleton cache (class-level)
    _instance: ClassVar[Optional["LabelConfig"]] = None
    
    # ✅ Instance caches (Pydantic-compatible)
    _labels_by_name: dict[str, Label] = PrivateAttr(default_factory=dict)
    _labels_by_category: dict[str, list[Label]] = PrivateAttr(default_factory=dict)
```

#### 2. Missing Global Error Handling in MCP Tools

**Problem:** When tools raise exceptions:
- VS Code receives uncaught exception
- Interprets as "tool crashed/unavailable"
- Marks tool as disabled for safety
- No structured error response

**Example from logs:**
```
2026-01-03 12:35:50.472 [error] Error from tool mcp_st3-workflow_safe_edit_file
2026-01-03 12:44:43.455 [error] Error from tool read_file: cannot open file...
```

**Current Architecture:**
```python
# Tool raises exception → VS Code sees crash
async def call_tool(self, arguments: dict):
    if not valid:
        raise ValueError("Invalid input")  # ❌ Uncaught
    return result
```

**Required Architecture:**
```python
# Tool returns error as valid response → VS Code keeps tool available
@tool_error_handler  # Global decorator
async def call_tool(self, arguments: dict):
    if not valid:
        raise ValueError("Invalid input")  # ✅ Caught by decorator
    return result

# Decorator converts exception → structured error response
# Tool remains "enabled" in VS Code
```

#### 3. VS Code's New Error Handling (Post 2026-01-01)

**Hypothesis:** VS Code's January update introduced stricter tool availability logic:
- **Old behavior:** Tool error → retry next time
- **New behavior:** Tool error → mark disabled for session

**Evidence:**
- Problem started appearing after new year
- Consistent across multiple chat sessions
- Requires VS Code restart to recover

### Impact Assessment

**Severity:** HIGH

**Affected Systems:**
- All 44 MCP tools in st3-workflow server
- Any tool that can throw an exception
- Entire chat-based workflow

**User Experience:**
- Agent gives up instead of debugging
- Agent tries CLI workarounds (inefficient)
- User frustration: "tools work in CLI but not chat"

**Workaround:**
- Restart VS Code to re-enable tools
- Use CLI commands directly
- Start new chat session (sometimes works)

---

## Secondary Bug: git_checkout State Sync

### Original Issue Description

**Problem:** git_checkout tool doesn't trigger PhaseStateEngine state synchronization

**Current Behavior:**
```python
async def execute(self, params: GitCheckoutInput) -> ToolResult:
    self.manager.checkout(params.branch)
    return ToolResult.text(f"Switched to branch: {params.branch}")
    # ❌ NO state sync!
```

**Expected Behavior:**
```python
async def execute(self, params: GitCheckoutInput) -> ToolResult:
    # 1. Switch branch
    self.manager.checkout(params.branch)
    
    # 2. Sync state (NEW)
    engine = PhaseStateEngine(...)
    state = engine.get_state(params.branch)
    
    # 3. Return enriched result
    return ToolResult.text(f"Switched to {params.branch} (Phase: {state['current_phase']})")
```

**Impact:** Medium (original issue remains valid but lower priority than error handling)

---

## Proposed Solution Architecture

### Layer 1: Fix Pydantic Compatibility (Immediate)

**File:** mcp_server/config/label_config.py

**Changes:**
1. Add rom pydantic import PrivateAttr and rom typing import ClassVar
2. Convert instance caches to PrivateAttr(default_factory=dict)
3. Convert singleton cache to ClassVar

**Effort:** 5 minutes
**Risk:** Low (well-defined fix)
**Impact:** Fixes startup error

### Layer 2: Global Error Handling Infrastructure (High Priority)

**New File:** mcp_server/core/error_handling.py

**Components:**
1. @tool_error_handler decorator
2. Error classification system
3. Structured error response format
4. Comprehensive logging

**Design Decisions Required:**
- Error response verbosity (development vs production)
- Error classification taxonomy
- When to disable tools vs return errors
- Backward compatibility strategy

**Effort:** 2-4 hours
**Risk:** Medium (affects all tools)
**Impact:** Solves primary bug

### Layer 3: git_checkout State Sync (Original Issue)

**File:** mcp_server/tools/git_checkout_tool.py

**Changes:**
1. Import PhaseStateEngine
2. Call get_state() after checkout
3. Enrich tool response with phase info

**Effort:** 30 minutes
**Risk:** Low
**Impact:** Solves secondary bug

---

## Implementation Strategy

### Phase 1: Stabilization (Do First)
1. ✅ Fix Pydantic PrivateAttr bug
2. ✅ Restart MCP server
3. ✅ Verify server starts without errors
4. ✅ Test basic tool calls in fresh chat

### Phase 2: Error Handling Infrastructure (Do Next)
1. Design error handling architecture (with stakeholder input)
2. Implement @tool_error_handler decorator
3. Apply to all tools via base class
4. Test error scenarios in chat
5. Verify tools stay "enabled" after errors

### Phase 3: git_checkout Enhancement (Do Last)
1. Add PhaseStateEngine integration
2. Test branch switching with state sync
3. Verify auto-recovery triggers
4. Update documentation

---

## Questions for Architecture Review

1. **Error Response Verbosity:**
   - Detailed errors in chat (development-friendly)?
   - Concise errors + log reference (production-friendly)?

2. **Error Classification:**
   - Categorize errors (user/config/system/bug)?
   - Or simple "error occurred" message?

3. **Tool Availability:**
   - Always return errors (never disable)?
   - Disable on config errors but not runtime errors?

4. **Backward Compatibility:**
   - Keep existing aise statements (decorator catches)?
   - Refactor to explicit error returns?

---

## Related Issues

- **Issue #77:** git_checkout state sync (this issue - scope expanded)
- **Issue #39:** PhaseStateEngine auto-recovery (provides state reconstruction)
- **Future:** Epic for MCP error handling infrastructure

---

## Testing Plan

### Phase 1 Tests (Pydantic Fix)
- [ ] Server starts without ModelPrivateAttr error
- [ ] Label config loads successfully
- [ ] Label tools functional in chat

### Phase 2 Tests (Error Handling)
- [ ] Tool error returns structured response
- [ ] Tool remains "enabled" after error
- [ ] Error logged to server logs
- [ ] Agent receives actionable error message

### Phase 3 Tests (git_checkout)
- [ ] Branch switch triggers state sync
- [ ] Phase info included in response
- [ ] Auto-recovery triggered for new branches
- [ ] State.json updated correctly

---

## Conclusion

Investigation uncovered a **critical infrastructure issue** more important than the original bug:

**Primary:** MCP error handling → VS Code tool availability
**Secondary:** git_checkout state sync

Both bugs will be fixed, but error handling takes priority to prevent future tool availability issues.

**Recommendation:** Expand Issue #77 scope to include both bugs, or create new Epic for error handling infrastructure.
