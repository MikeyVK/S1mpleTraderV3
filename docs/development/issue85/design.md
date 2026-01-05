# Design: Fix Blocking I/O in State.json Operations

**Status:** DRAFT | **Date:** 2026-01-04 | **Author:** AI Agent

---

## Executive Summary

Fix voor blocking I/O operaties in PhaseStateEngine en phase_tools die de MCP stream laten hangen. 
Oplossing: vervang `f.flush()` door `write_text()` en wrap blocking calls in `asyncio.to_thread()`.

---

## Problem Statement

### Symptomen
- MCP tools (`git_checkout`, `force_phase_transition`, `transition_phase`) hangen de chat/stream
- `state.json` wordt pas geschreven nadat gebruiker de chat stopt
- Specifiek: alleen bij `_reconstruct_branch_state()` flow (state.json niet bestaat of andere branch)

### Root Cause
Blocking I/O operaties in async context blokkeren de event loop:

1. **`_save_state()`**: `f.flush()` blokkeert op disk I/O
2. **`_reconstruct_branch_state()`**: `subprocess.run()` blokkeert op git process
3. **`phase_tools.py`**: Direct blocking calls zonder `asyncio.to_thread()`

### Impact
- MCP server kan geen JSON-RPC berichten verwerken
- VS Code timeout wacht op response die nooit komt
- Gebruiker moet chat stoppen om verder te kunnen

---

## Solution Design

### Principe
Volg het patroon van `safe_edit_file` dat WEL werkt:
- Gebruik `write_text()` ipv `open()` + `flush()`
- Wrap alle blocking operations in `asyncio.to_thread()`

### Architectuur Verbetering
Verwijder protected member access in `git_tools.py`:
- `engine._save_state()` → gebruik `engine.get_state()` (doet al auto-recovery + save)

---

## Implementation Details

### Fix 1: `phase_state_engine.py` - `_save_state()`

**Voor:**
```python
def _save_state(self, branch: str, state: dict[str, Any]) -> None:
    self.state_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(self.state_file, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2)
        f.flush()  # ❌ BLOCKING
```

**Na:**
```python
def _save_state(self, branch: str, state: dict[str, Any]) -> None:
    self.state_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Gebruik write_text() zoals safe_edit_file - geen blocking flush
    self.state_file.write_text(
        json.dumps(state, indent=2),
        encoding='utf-8'
    )
```

### Fix 2: `phase_tools.py` - `TransitionPhaseTool`

**Voor:**
```python
async def execute(self, params: TransitionPhaseInput) -> ToolResult:
    engine = self._create_engine()
    
    try:
        result = engine.transition(...)  # ❌ BLOCKING
```

**Na:**
```python
async def execute(self, params: TransitionPhaseInput) -> ToolResult:
    import asyncio
    engine = self._create_engine()

    def do_transition() -> dict[str, Any]:
        return engine.transition(
            branch=params.branch,
            to_phase=params.to_phase,
            human_approval=params.human_approval
        )

    try:
        result = await asyncio.to_thread(do_transition)  # ✅ NON-BLOCKING
```

### Fix 3: `phase_tools.py` - `ForcePhaseTransitionTool`

**Voor:**
```python
async def execute(self, params: ForcePhaseTransitionInput) -> ToolResult:
    engine = self._create_engine()

    try:
        result = engine.force_transition(...)  # ❌ BLOCKING
```

**Na:**
```python
async def execute(self, params: ForcePhaseTransitionInput) -> ToolResult:
    import asyncio
    engine = self._create_engine()

    def do_force_transition() -> dict[str, Any]:
        return engine.force_transition(
            branch=params.branch,
            to_phase=params.to_phase,
            skip_reason=params.skip_reason,
            human_approval=params.human_approval
        )

    try:
        result = await asyncio.to_thread(do_force_transition)  # ✅ NON-BLOCKING
```

### Fix 4: `git_tools.py` - `GitCheckoutTool` (Encapsulation)

**Voor:**
```python
def sync_state() -> str:
    # ...
    state = engine.get_state(params.branch)
    current_phase = str(state.get('current_phase', 'unknown'))
    
    # pylint: disable=protected-access
    engine._save_state(params.branch, state)  # ❌ PROTECTED ACCESS + REDUNDANT
    return current_phase
```

**Na:**
```python
def sync_state() -> str:
    # get_state() doet al auto-recovery + save indien nodig
    state = engine.get_state(params.branch)
    return str(state.get('current_phase', 'unknown'))
    # Geen extra _save_state() nodig - get_state() handled dit
```

---

## File Changes

| File | Wijziging | Regels |
|------|-----------|--------|
| `mcp_server/managers/phase_state_engine.py` | `write_text()` ipv `open()+flush()` | ~270-275 |
| `mcp_server/tools/phase_tools.py` | `asyncio.to_thread()` wrapper (2x) | ~105-130, ~145-170 |
| `mcp_server/tools/git_tools.py` | Verwijder `_save_state()` call | ~233 |

---

## Test Plan

### Unit Tests
1. Verifieer `_save_state()` gebruikt `write_text()` (mock check)

### Integration Tests
| Test | Scenario | Expected |
|------|----------|----------|
| 1 | `git_checkout` met niet-bestaand state.json | ✅ Direct response, state.json aangemaakt |
| 2 | `git_checkout` met state.json voor andere branch | ✅ Direct response, state.json bijgewerkt |
| 3 | `force_phase_transition` | ✅ Direct response, geen hang |
| 4 | `transition_phase` | ✅ Direct response, geen hang |

### Manual Verification
- Chat hangt niet meer bij branch switch
- `state.json` wordt direct geschreven (niet pas na chat stop)

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| `write_text()` zonder flush kan data verliezen bij crash | Low | OS buffert en flusht bij close; crash is edge case |
| Thread pool exhaustion bij veel requests | Low | MCP is single-user; geen high-concurrency scenario |
| Breaking change in get_state() behavior | Low | get_state() deed al auto-recovery+save; geen API change |

---

## Approval

- [ ] Design reviewed
- [ ] Ready for implementation
