# Research: State.json Write Hang Bug (Issue #85)

**Status:** COMPLETE | **Date:** 2026-01-04 | **Author:** AI Agent

---

## Executive Summary

MCP tools die `state.json` schrijven (zoals `git_checkout`, `force_phase_transition`, `transition_phase`) 
laten de chat/stream "hangen" totdat de gebruiker de chat stopt. Het bestand wordt pas geschreven 
**nadat** de stream is afgebroken.

**Root Cause:** Blocking I/O (`f.flush()`) in async context blokkeert de event loop.

**Architectuur Issue:** State.json write logica wordt niet consistent via één interface aangeroepen.

---

## 🔍 Analyse

### Symptomen
1. Tool wordt aangeroepen (bijv. `git_checkout` of `force_phase_transition`)
2. Chat hangt - geen response
3. Gebruiker stopt chat
4. **Dan pas** wordt `state.json` geschreven/geüpdatet

### Root Cause: Blocking I/O in Async Context

**Probleem locatie:** [phase_state_engine.py#L259-L274](../../mcp_server/managers/phase_state_engine.py#L259-L274)

```python
def _save_state(self, branch: str, state: dict[str, Any]) -> None:
    self.state_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(self.state_file, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2)
        f.flush()  # ❌ BLOCKING FLUSH - blokkeert event loop!
```

Het `f.flush()` commando blokkeert de main event loop omdat:
1. Het wacht op OS buffer flush naar disk
2. Windows file system notifications (VS Code file watcher)
3. Mogelijke antivirus scanning

### Waarom hangt de stream?

MCP communiceert via **stdio** (stdin/stdout). Wanneer `f.flush()` blokkeert:
1. De MCP server kan geen JSON-RPC berichten lezen
2. De MCP server kan geen response berichten schrijven
3. VS Code wacht op een response die nooit komt
4. Gebruiker ziet stream "hangen"

---

## 🏗️ Architectuur Issue: SRP/DRY Violation

### Huidige Situatie

De `_save_state()` methode is correct gedefinieerd op **één plek** in `PhaseStateEngine`, 
maar wordt **inconsistent** aangeroepen:

| Aanroeper | Locatie | Methode | SRP Violation? |
|-----------|---------|---------|----------------|
| `initialize_branch()` | phase_state_engine.py:117 | `self._save_state()` | ✅ Correct |
| `transition()` | phase_state_engine.py:164 | `self._save_state()` | ✅ Correct |
| `force_transition()` | phase_state_engine.py:209 | `self._save_state()` | ✅ Correct |
| `get_state()` (auto-recovery) | phase_state_engine.py:256 | `self._save_state()` | ✅ Correct |
| **`GitCheckoutTool`** | git_tools.py:233 | `engine._save_state()` | ❌ **VIOLATION!** |

### Probleem: Protected Member Access in git_tools.py

```python
# git_tools.py line 233
engine._save_state(params.branch, state)  # ❌ Direct access to protected method!
```

Dit is een **SRP/encapsulation violation**:
1. `_save_state()` is een **protected method** (underscore prefix)
2. `GitCheckoutTool` zou **geen** directe toegang moeten hebben
3. Dit creëert **tight coupling** tussen tool en engine internals

### Oplossing: Public Interface

`PhaseStateEngine` zou een **public method** moeten exposeren voor branch switch state sync:

```python
# In PhaseStateEngine
def sync_branch_state(self, branch: str) -> dict[str, Any]:
    """Public method for external state synchronization after branch switch.
    
    Returns:
        Current state dict after sync
    """
    state = self.get_state(branch)  # Triggers auto-recovery if needed
    return state
```

Dan in `git_tools.py`:
```python
# Clean public interface call
state = engine.sync_branch_state(params.branch)
current_phase = state.get('current_phase', 'unknown')
```

---

## 🔬 Vergelijking: Wat werkt vs Wat faalt

### ✅ `safe_edit_file` - WERKT

**Bestand:** [safe_edit_tool.py#L315](../../mcp_server/tools/safe_edit_tool.py#L315)

```python
# Write file
file_path.write_text(new_content, encoding="utf-8")
```

**Waarom werkt dit:**
- `write_text()` doet GEEN expliciete `flush()`
- Bestand wordt direct gesloten na write
- OS buffert de write, file handle wordt snel vrijgegeven

### ⚠️ `git_checkout` - ARCHITECTUUR VIOLATION

**Bestand:** [git_tools.py#L207-L244](../../mcp_server/tools/git_tools.py#L207-L244)

```python
async def execute(self, params: GitCheckoutInput) -> ToolResult:
    # ... branch switch ...
    
    def sync_state() -> str:
        engine._save_state(params.branch, state)  # ❌ Protected access!
        return current_phase

    current_phase = await asyncio.to_thread(sync_state)
```

**Issues:**
1. Direct access to protected `_save_state()` method
2. Dupliceert logica die al in `get_state()` auto-recovery zit

### ❌ `force_phase_transition` / `transition_phase` - FAALT

**Bestand:** [phase_tools.py#L100-L130](../../mcp_server/tools/phase_tools.py#L100-L130)

```python
async def execute(self, params: ForcePhaseTransitionInput) -> ToolResult:
    engine = self._create_engine()
    result = engine.force_transition(...)  # ❌ DIRECT blocking call!
```

**Probleem:** GEEN `asyncio.to_thread()` wrapper - direct blocking call in async function!

---

## 📊 Impact Matrix

| Tool | Blocking Call? | `asyncio.to_thread`? | Protected Access? | Status |
|------|---------------|----------------------|-------------------|--------|
| `safe_edit_file` | ❌ Nee | N/A | N/A | ✅ Werkt |
| `git_checkout` | ✅ Ja | ✅ Ja | ❌ **Ja** | ⚠️ Werkt maar dirty |
| `force_phase_transition` | ✅ Ja | ❌ **Nee** | ✅ Nee | ❌ Hangt |
| `transition_phase` | ✅ Ja | ❌ **Nee** | ✅ Nee | ❌ Hangt |

---

## 🔧 Oplossingen

### Fix 1: Verwijder blocking `f.flush()` (Quick Fix)

In `phase_state_engine.py`:

```python
def _save_state(self, branch: str, state: dict[str, Any]) -> None:
    self.state_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Gebruik write_text() zoals safe_edit_file - geen blocking flush
    self.state_file.write_text(
        json.dumps(state, indent=2),
        encoding='utf-8'
    )
```

### Fix 2: Wrap blocking calls in `asyncio.to_thread()` (phase_tools.py)

```python
async def execute(self, params: ForcePhaseTransitionInput) -> ToolResult:
    import asyncio
    engine = self._create_engine()

    def do_transition() -> dict:
        return engine.force_transition(...)

    try:
        result = await asyncio.to_thread(do_transition)
```

### Fix 3: Refactor git_checkout to use public interface (Architecture)

1. Add public method to `PhaseStateEngine`:
```python
def sync_branch_state(self, branch: str) -> dict[str, Any]:
    """Sync state after branch switch. Public interface."""
    return self.get_state(branch)  # get_state already handles auto-recovery + save
```

2. Update `git_tools.py`:
```python
def sync_state() -> str:
    state = engine.sync_branch_state(params.branch)  # ✅ Public method
    return state.get('current_phase', 'unknown')
```

---

## 🎯 Aanbeveling

**Implementeer alle 3 fixes** voor een robuuste oplossing:

| Fix | Prioriteit | Impact |
|-----|------------|--------|
| Fix 1: `write_text()` | 🔴 HIGH | Lost blocking issue op |
| Fix 2: `asyncio.to_thread()` | 🔴 HIGH | Maakt phase_tools async-safe |
| Fix 3: Public interface | 🟡 MEDIUM | Verbetert architectuur/encapsulation |

---

## 🧪 Reproduceerbare Test Resultaten

| Test | `state.json` status | Resultaat | Analyse |
|------|---------------------|-----------|---------|
| `git_checkout` | Leeg bestand | ✅ Direct response | JSON parse faalt, exception handler vangt af |
| `git_checkout` | Bestand niet bestaat | ❌ **Hangt** | `_reconstruct_branch_state()` blocking flow |
| `git_checkout` | Correct gevuld voor branch | ✅ Direct response | Geen reconstructie nodig, state direct gelezen |
| `force_phase_transition` | N/A | ❌ **Hangt** | Geen `asyncio.to_thread()` wrapper |

**Conclusie:** Het probleem zit **100% in de `_reconstruct_branch_state()` flow** die alleen wordt aangeroepen als:
1. `state.json` niet bestaat, OF
2. `state.json` voor een andere branch is

De blocking operaties in die flow:
1. `subprocess.run()` voor git log (blocking)
2. `projects.json` leest (blocking I/O)
3. `_save_state()` met `f.flush()` (blocking)

---

## 📋 Test Plan

1. **Unit test**: Verifieer dat `_save_state()` geen blocking calls heeft
2. **Integration test**: `force_phase_transition`, verifieer geen hang
3. **Integration test**: `transition_phase`, verifieer geen hang
4. **Integration test**: `git_checkout` met niet-bestaand state.json, verifieer geen hang

---

## ✅ Conclusie

Het probleem is **tweeledig**:

1. **Technical:** Blocking I/O (`f.flush()`) in async context blokkeert event loop
2. **Architectural:** Protected member access in `git_tools.py` schendt encapsulation

De fix vereist zowel de technische aanpassing (geen blocking flush) als een 
architectuurverbetering (public interface voor state sync).
