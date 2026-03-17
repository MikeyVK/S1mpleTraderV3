# VS Code Agent Orchestration — Design & Implementation Plan

**Status:** APPROVED DESIGN  
**Version:** 1.0  
**Created:** 2026-03-17  
**Author:** Research phase, issue #257 branch  
**Scope:** Cross-cutting infrastructure — VS Code hooks, custom agents, instructions, prompts  

---

## 1. Executive Summary

Dit document beschrijft een complete, uitvoerbare architectuur voor VS Code Copilot's native orchestratiefuncties, naadloos geïntegreerd met de bestaande ST3 MCP Server. Het doel is drieledig:

1. **Automatische context-recovery na compaction** — via `PreCompact` en `SessionStart` hooks
2. **Gestructureerde IMP↔QA hand-overs** — via custom agents met handoff-buttons
3. **Domeinspecifieke instructies** — via `.instructions.md` bestanden per bestandstype

### Architectuurprincipe

```
┌─────────────────────────────────────────────────────┐
│  VS Code Copilot Chat                               │
│  ┌───────────────┐  ┌────────────────┐              │
│  │ Hooks Layer   │  │ Instructions   │              │
│  │ (lifecycle)   │  │ (.instructions │              │
│  │               │  │  .agent.md)    │              │
│  └──────┬────────┘  └───────┬────────┘              │
│         │                   │                       │
│         ▼                   ▼                       │
│  ┌──────────────────────────────────────┐           │
│  │  Agent Context Window                │           │
│  │  (system prompt + conversation)      │           │
│  └──────────────┬───────────────────────┘           │
│                 │                                   │
│                 ▼                                   │
│  ┌──────────────────────────────────────┐           │
│  │  MCP Server (ST3 Workflow)           │           │
│  │  ┌────────┐ ┌──────────┐ ┌────────┐ │           │
│  │  │ Tools  │ │ Resources│ │ State  │ │           │
│  │  │ (80+)  │ │ (st3://) │ │ (.st3/)│ │           │
│  │  └────────┘ └──────────┘ └────────┘ │           │
│  └──────────────────────────────────────┘           │
└─────────────────────────────────────────────────────┘
```

**Kernidee:** Hooks schrijven/lezen `.st3/` state bestanden. De MCP server is en blijft de single source of truth. Hooks zijn **lichtgewicht bruggen** die VS Code lifecycle events vertalen naar state reads/writes — ze bevatten geen business logic.

---

## 2. Bestandsoverzicht per Laag

### Laag 1 — Hooks (lifecycle events)

| Bestand | Hook Event | Doel |
|---------|-----------|------|
| `.github/hooks/session-start.json` | `SessionStart` | Injecteert fase/issue context bij nieuwe sessie |
| `.github/hooks/pre-compact.json` | `PreCompact` | Schrijft hand-over state vóór compaction |
| `.github/hooks/pre-tool-use.json` | `PreToolUse` | Bewaakt tool-gebruik (optioneel, fase 2) |

### Laag 2 — Custom Agents (role switching)

| Bestand | Rol | Doel |
|---------|-----|------|
| `.github/agents/imp.agent.md` | Implementation Agent | TDD uitvoering met scope lock |
| `.github/agents/qa.agent.md` | QA Agent | Read-only verificatie met GO/NOGO |

### Laag 3 — Instructions (domeinspecifiek)

| Bestand | `applyTo` | Doel |
|---------|----------|------|
| `.github/instructions/python-backend.instructions.md` | `backend/**/*.py` | Architectuur principes voor backend code |
| `.github/instructions/python-mcp.instructions.md` | `mcp_server/**/*.py` | MCP server conventies (BaseTool, ToolResult) |
| `.github/instructions/tests.instructions.md` | `tests/**/*.py` | Test conventies (zones, fixtures, markers) |
| `.github/instructions/yaml-config.instructions.md` | `.st3/config/**/*.yaml` | Config schema regels |
| `.github/instructions/docs.instructions.md` | `docs/**/*.md` | Documentatie standaarden |

### Laag 4 — Prompt Files (herbruikbare taken)

| Bestand | Slash Command | Doel |
|---------|--------------|------|
| `.github/prompts/resume-after-compaction.prompt.md` | `/resume-after-compaction` | Context herstel na compaction |
| `.github/prompts/prepare-handover.prompt.md` | `/prepare-handover` | Hand-over document genereren |
| `.github/prompts/qa-verify.prompt.md` | `/qa-verify` | QA verificatie op hand-over |
| `.github/prompts/start-tdd-cycle.prompt.md` | `/start-tdd-cycle` | TDD RED→GREEN→REFACTOR initialiseren |

### Workspace Settings

| Bestand | Doel |
|---------|------|
| `.vscode/settings.json` | Activeer hooks, agents, instructions |

---

## 3. Laag 1 — VS Code Hooks (Gedetailleerd)

### 3.1 Achtergrond: Hoe Hooks Werken

VS Code Copilot hooks (Preview, beschikbaar sinds VS Code 1.108+) zijn **shell commands** die op specifieke lifecycle momenten worden uitgevoerd. Ze:

- Ontvangen JSON op **stdin** (event-specifieke context)
- Retourneren JSON op **stdout** (instructies voor de agent)
- Exit code **0** = succes, **2** = blokkerende fout
- Draaien als **synchrone processen** (timeout: standaard 10s, max 60s)
- Worden geconfigureerd via JSON bestanden in `.github/hooks/`

### 3.2 Hook: `session-start.json`

**Doel:** Bij elke nieuwe chat-sessie automatisch de huidige werkcontext injecteren, zodat de agent direct weet: welke branch, welke fase, welk issue, en welke rol.

**Bestand:** `.github/hooks/session-start.json`

```json
{
  "hooks": {
    "SessionStart": [
      {
        "command": "python",
        "args": [
          "${workspaceFolder}/scripts/hooks/session_start.py"
        ],
        "timeout": 15000
      }
    ]
  }
}
```

**Script:** `scripts/hooks/session_start.py`

```python
"""
VS Code SessionStart hook — injects workspace context into agent.

Reads .st3/state.json + .st3/projects.json and returns a system prompt
fragment with current branch, phase, issue, and role context.

Input (stdin JSON):
  {
    "chatContext": {
      "history": [...],           // Previous messages (usually empty)
      "agentName": "copilot"      // Or "imp", "qa" if custom agent
    }
  }

Output (stdout JSON):
  {
    "instructions": "string"      // Injected into system prompt
  }

Exit codes:
  0 = success (instructions injected)
  2 = error (blocks session start — avoid, use fallback instead)
"""
import json
import sys
from pathlib import Path


def main() -> None:
    workspace = Path(__file__).resolve().parents[2]  # scripts/hooks/ → root
    state_path = workspace / ".st3" / "state.json"
    projects_path = workspace / ".st3" / "projects.json"
    handover_path = workspace / ".st3" / "handover.json"

    # Read current state
    state = _read_json(state_path)
    projects = _read_json(projects_path)
    handover = _read_json(handover_path)

    # Read stdin for agent context
    try:
        event = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError):
        event = {}

    agent_name = (
        event.get("chatContext", {}).get("agentName", "copilot")
    )

    # Build context instruction
    instructions = _build_instructions(
        state, projects, handover, agent_name, workspace
    )

    # Output
    result = {"instructions": instructions}
    sys.stdout.write(json.dumps(result))
    sys.exit(0)


def _build_instructions(
    state: dict,
    projects: dict,
    handover: dict | None,
    agent_name: str,
    workspace: Path,
) -> str:
    branch = state.get("branch", "unknown")
    phase = state.get("current_phase", "unknown")
    issue = state.get("issue_number")
    workflow = state.get("workflow_name", "unknown")
    cycle = state.get("current_cycle")

    lines = [
        "## Automatisch geïnjecteerde werkcontext",
        "",
        f"- **Branch:** `{branch}`",
        f"- **Fase:** `{phase}`",
        f"- **Workflow:** `{workflow}`",
    ]

    if issue:
        lines.append(f"- **Issue:** #{issue}")

        # Find issue title from projects
        issue_key = str(issue)
        if issue_key in projects:
            proj = projects[issue_key]
            title = proj.get("issue_title", "")
            if title:
                lines.append(f"- **Titel:** {title}")

    if cycle is not None:
        lines.append(f"- **TDD Cycle:** {cycle}")

    # Agent-specific role injection
    if agent_name == "imp":
        lines.extend([
            "",
            "**Rol:** Implementation Agent (imp_agent.md)",
            "Je bent in IMP-modus. Volg imp_agent.md startup protocol.",
            "Scope lock: werk alleen binnen de actieve cycle deliverables.",
        ])
    elif agent_name == "qa":
        lines.extend([
            "",
            "**Rol:** QA Agent (qa_agent.md)",
            "Je bent in QA-modus. Volg qa_agent.md startup protocol.",
            "Read-only verificatie. Geen code wijzigingen.",
        ])

    # Check for pending handover
    if handover and handover.get("pending"):
        lines.extend([
            "",
            "⚠️ **Openstaande hand-over gevonden.**",
            f"Van: {handover.get('from_role', 'unknown')}",
            f"Status: {handover.get('status', 'unknown')}",
            "Gebruik `/resume-after-compaction` om context te herstellen.",
        ])

    # Check for post-compaction state
    compaction_marker = workspace / ".st3" / "compaction_state.json"
    if compaction_marker.exists():
        comp_state = _read_json(compaction_marker)
        if comp_state.get("needs_recovery"):
            lines.extend([
                "",
                "🔄 **Post-compaction herstel nodig.**",
                f"Laatst actieve taak: {comp_state.get('last_task', 'onbekend')}",
                f"Bestanden in scope: {', '.join(comp_state.get('files_in_scope', [])[:5])}",
                "Voer `/resume-after-compaction` uit voor volledig herstel.",
            ])

    return "\n".join(lines)


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


if __name__ == "__main__":
    main()
```

**Werking:**
1. VS Code start een nieuwe chat → triggert `SessionStart`
2. Het script leest `.st3/state.json`, `.st3/projects.json`, en optioneel `.st3/handover.json`
3. Het bouwt een contextfragment met branch, fase, issue, en rol
4. Dit fragment wordt in het system prompt geïnjecteerd → agent weet direct waar hij is
5. Bij een custom agent (`imp` of `qa`) krijgt de agent rol-specifieke instructies

### 3.3 Hook: `pre-compact.json`

**Doel:** Vóórdat VS Code de context comprimeert, automatisch de huidige werkstaat opslaan zodat de volgende sessie (of post-compaction context) kan herstellen.

**Bestand:** `.github/hooks/pre-compact.json`

```json
{
  "hooks": {
    "PreCompact": [
      {
        "command": "python",
        "args": [
          "${workspaceFolder}/scripts/hooks/pre_compact.py"
        ],
        "timeout": 10000
      }
    ]
  }
}
```

**Script:** `scripts/hooks/pre_compact.py`

```python
"""
VS Code PreCompact hook — persists working state before context compaction.

Captures current task context so the agent can resume seamlessly after
the compacted conversation continues.

Input (stdin JSON):
  {
    "chatContext": {
      "history": [
        {"role": "user", "content": "..."},
        {"role": "assistant", "content": "..."}
      ],
      "agentName": "copilot"
    }
  }

Output (stdout JSON):
  {
    "instructions": "string"    // Post-compaction recovery note
  }

Side effect:
  Writes .st3/compaction_state.json with:
  - last active task summary (extracted from recent messages)
  - files in scope (extracted from conversation)
  - current phase/cycle
  - timestamp
  - role context
"""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


def main() -> None:
    workspace = Path(__file__).resolve().parents[2]

    try:
        event = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError):
        event = {}

    chat_context = event.get("chatContext", {})
    history = chat_context.get("history", [])
    agent_name = chat_context.get("agentName", "copilot")

    # Read current state
    state = _read_json(workspace / ".st3" / "state.json")

    # Extract working context from conversation history
    files_mentioned = _extract_file_paths(history)
    last_task = _extract_last_task(history)

    # Write compaction state
    compaction_state = {
        "needs_recovery": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "branch": state.get("branch", "unknown"),
        "phase": state.get("current_phase", "unknown"),
        "cycle": state.get("current_cycle"),
        "issue_number": state.get("issue_number"),
        "workflow": state.get("workflow_name", "unknown"),
        "agent_role": agent_name,
        "last_task": last_task,
        "files_in_scope": files_mentioned[:20],  # Cap at 20
    }

    compaction_path = workspace / ".st3" / "compaction_state.json"
    compaction_path.write_text(
        json.dumps(compaction_state, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # Return instruction for post-compaction context
    instructions = (
        "⚠️ Context compaction is zojuist uitgevoerd. "
        "Werkstaat is opgeslagen in .st3/compaction_state.json. "
        "Bij de volgende interactie wordt de context automatisch hersteld "
        "via de SessionStart hook."
    )

    result = {"instructions": instructions}
    sys.stdout.write(json.dumps(result))
    sys.exit(0)


def _extract_file_paths(history: list[dict]) -> list[str]:
    """Extract file paths mentioned in conversation history."""
    paths: list[str] = []
    pattern = re.compile(
        r'(?:^|\s|["\'])'
        r'((?:backend|mcp_server|tests|docs|scripts|\.st3|\.github)'
        r'/[\w./\-]+\.(?:py|yaml|json|md))'
        r'(?:\s|["\']|$)',
    )
    for msg in history:
        content = msg.get("content", "")
        if isinstance(content, str):
            matches = pattern.findall(content)
            paths.extend(matches)
    # Deduplicate preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for p in paths:
        if p not in seen:
            seen.add(p)
            unique.append(p)
    return unique


def _extract_last_task(history: list[dict]) -> str:
    """Extract a summary of the last active task from history."""
    # Walk backward through user messages
    for msg in reversed(history):
        if msg.get("role") == "user":
            content = msg.get("content", "")
            if isinstance(content, str) and len(content) > 10:
                # Truncate to reasonable summary length
                return content[:200]
    return "Geen taakcontext beschikbaar"


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


if __name__ == "__main__":
    main()
```

**Werking:**
1. VS Code detecteert dat het context window vol raakt → triggert `PreCompact`
2. Het script ontvangt de volledige conversatiegeschiedenis (vóór compressie)
3. Het extraheert: genoemde bestanden, laatste taak, huidige fase/cycle
4. Schrijft alles naar `.st3/compaction_state.json`
5. Bij de volgende interactie leest `session_start.py` dit bestand en injecteert de recovery-instructie

### 3.4 Hook: `pre-tool-use.json` (Fase 2 — Optioneel)

**Doel:** Bewaken dat bepaalde tools niet worden gebruikt buiten de juiste fase (bijv. geen `git_push` in research fase). Dit versterkt de bestaande MCP enforcement, maar dan op VS Code niveau.

> **Implementatie:** Fase 2. Eerst Laag 1 + 2 stabiel maken. De MCP server's `EnforcementRunner` handelt dit al deels af, maar de VS Code hook kan eerder ingrijpen (vóór het MCP-verzoek).

**Bestand:** `.github/hooks/pre-tool-use.json`

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "command": "python",
        "args": [
          "${workspaceFolder}/scripts/hooks/pre_tool_use.py"
        ],
        "timeout": 5000
      }
    ]
  }
}
```

**Script concept (fase 2):** `scripts/hooks/pre_tool_use.py`

```python
"""
VS Code PreToolUse hook — phase-aware tool gating.

Validates that MCP tool calls are appropriate for the current
workflow phase. This is a client-side complement to the server-side
EnforcementRunner.

Input (stdin JSON):
  {
    "toolCall": {
      "toolName": "mcp_st3-workflow_git_push",
      "parameters": {...}
    },
    "chatContext": {
      "agentName": "qa"
    }
  }

Output (stdout JSON):
  {}                          // Allow (empty = no modification)
  OR
  {
    "instructions": "⚠️ git_push is niet toegestaan in research fase."
  }

Exit code 2 = block tool call entirely.
"""
import json
import sys
from pathlib import Path

# Phase → blocked tools mapping
# Only block destructive/premature actions; keep lightweight
PHASE_BLOCKS: dict[str, set[str]] = {
    "research": {
        "mcp_st3-workflow_git_push",
        "mcp_st3-workflow_create_pr",
        "mcp_st3-workflow_merge_pr",
    },
    "planning": {
        "mcp_st3-workflow_git_push",
        "mcp_st3-workflow_create_pr",
        "mcp_st3-workflow_merge_pr",
    },
}

# QA agent should never use write tools
QA_BLOCKED_TOOLS: set[str] = {
    "mcp_st3-workflow_safe_edit_file",
    "mcp_st3-workflow_create_file",
    "mcp_st3-workflow_scaffold_artifact",
    "mcp_st3-workflow_git_add_or_commit",
}


def main() -> None:
    workspace = Path(__file__).resolve().parents[2]

    try:
        event = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError):
        sys.stdout.write("{}")
        sys.exit(0)

    tool_name = event.get("toolCall", {}).get("toolName", "")
    agent_name = event.get("chatContext", {}).get("agentName", "copilot")

    # QA agent write protection
    if agent_name == "qa" and tool_name in QA_BLOCKED_TOOLS:
        result = {
            "instructions": (
                f"⛔ Tool `{tool_name}` is geblokkeerd voor QA agent. "
                "QA is read-only. Gebruik @imp voor wijzigingen."
            ),
        }
        sys.stdout.write(json.dumps(result))
        sys.exit(2)  # Block

    # Phase-based gating
    state = _read_json(workspace / ".st3" / "state.json")
    phase = state.get("current_phase", "")

    blocked = PHASE_BLOCKS.get(phase, set())
    if tool_name in blocked:
        result = {
            "instructions": (
                f"⚠️ Tool `{tool_name}` is niet gebruikelijk in de "
                f"`{phase}` fase. Overweeg of dit juist is."
            ),
        }
        sys.stdout.write(json.dumps(result))
        # Exit 0 = warn but allow; change to 2 for hard block
        sys.exit(0)

    sys.stdout.write("{}")
    sys.exit(0)


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


if __name__ == "__main__":
    main()
```

---

## 4. Laag 2 — Custom Agents (Gedetailleerd)

### 4.1 Achtergrond: Hoe Custom Agents Werken

Custom agents zijn `.agent.md` bestanden in `.github/agents/`. Ze:

- Verschijnen als `@agent-naam` in de chat
- Hebben YAML frontmatter met `description`, `tools`, en optioneel `hooks`
- Ondersteunen **handoffs** — knoppen die de gebruiker naar een andere agent sturen
- Kunnen tool-gebruik beperken (whitelist)
- Kunnen agent-specifieke hooks hebben (vereist `chat.useCustomAgentHooks: true`)

### 4.2 Agent: `imp.agent.md`

**Doel:** Implementation agent met TDD discipline, scope lock, en automatische hand-over naar QA.

**Bestand:** `.github/agents/imp.agent.md`

```markdown
---
description: "Implementation Agent — TDD uitvoering met scope lock en hand-over naar QA"
tools:
  - mcp_st3-workflow_safe_edit_file
  - mcp_st3-workflow_create_file
  - mcp_st3-workflow_scaffold_artifact
  - mcp_st3-workflow_git_add_or_commit
  - mcp_st3-workflow_git_status
  - mcp_st3-workflow_git_checkout
  - mcp_st3-workflow_git_diff_stat
  - mcp_st3-workflow_git_stash
  - mcp_st3-workflow_git_restore
  - mcp_st3-workflow_run_tests
  - mcp_st3-workflow_run_quality_gates
  - mcp_st3-workflow_transition_phase
  - mcp_st3-workflow_transition_cycle
  - mcp_st3-workflow_force_phase_transition
  - mcp_st3-workflow_force_cycle_transition
  - mcp_st3-workflow_get_work_context
  - mcp_st3-workflow_get_issue
  - mcp_st3-workflow_get_project_plan
  - mcp_st3-workflow_validate_architecture
  - mcp_st3-workflow_validate_dto
  - mcp_st3-workflow_validate_template
  - mcp_st3-workflow_search_documentation
  - mcp_st3-workflow_health_check
  - mcp_st3-workflow_git_list_branches
---

# Implementation Agent

Je bent de **Implementation Agent** voor het ST3 platform.

## Startup Protocol

Bij elke sessie (inclusief na compaction):

1. Lees `agent.md` — het volledige cooperation protocol
2. Lees `.github/.copilot-instructions.md` — de auto-loaded regels
3. Lees `docs/coding_standards/ARCHITECTURE_PRINCIPLES.md` — het bindend architectuurcontract
4. Controleer werkstatus via `get_work_context`
5. Lees het actieve planning document in `docs/development/issue{N}/planning.md`
6. Inspecteer de worktree: `git_status` + `git_diff_stat`

## Kernregels

- **Scope lock:** Je scope = doorsnede van gebruikerverzoek + planning cycle + deliverables
- **TDD verplicht:** RED → GREEN → REFACTOR. Geen code zonder test.
- **Architectuurcontract is bindend.** Violations worden geweigerd ongeacht groene tests.
- **Gebruik alleen MCP tools.** Nooit `run_in_terminal` voor git/test/file operaties.
- **English artifacts, Dutch chat.** Code/docs/commits in het Engels; communicatie in het Nederlands.

## Hand-Over Format

Na afronding van een cycle, lever een hand-over met deze 9 secties:

1. **Scope** — welke cycle/taak uitgevoerd, wat bewust buiten scope gehouden
2. **Files** — gewijzigde bestanden gegroepeerd per rol
3. **Deliverables** — welke deliverables nu voldaan zijn
4. **Stop-Go Proof** — exact welke tests en gates gedraaid, exact resultaat
5. **Out-of-Scope** — wat bewust niet gewijzigd is
6. **Planning Changes** — `none` tenzij gebruiker expliciet planning-reparatie vroeg
7. **Open Blockers** — `none` alleen als er echt geen zijn
8. **Ready-for-QA** — `yes` of `no`
9. **Truthfulness** — nooit claimen: full suite green als alleen targeted tests gedraaid; quality gates green als alleen één bestand gecheckt

## QA Boundary

Je kunt NIET zelf cycle GO declareren. Dat doet alleen de QA agent.
Je zegt alleen: `Ready-for-QA: yes` of `Ready-for-QA: no`.

[handoff:qa] Stuur door naar QA voor verificatie
```

### 4.3 Agent: `qa.agent.md`

**Doel:** QA agent — read-only verificatie met skeptische houding en GO/NOGO autoriteit.

**Bestand:** `.github/agents/qa.agent.md`

```markdown
---
description: "QA Agent — Read-only verificatie met GO/NOGO autoriteit"
tools:
  - mcp_st3-workflow_git_status
  - mcp_st3-workflow_git_diff_stat
  - mcp_st3-workflow_git_list_branches
  - mcp_st3-workflow_run_tests
  - mcp_st3-workflow_run_quality_gates
  - mcp_st3-workflow_get_work_context
  - mcp_st3-workflow_get_issue
  - mcp_st3-workflow_get_project_plan
  - mcp_st3-workflow_validate_architecture
  - mcp_st3-workflow_validate_dto
  - mcp_st3-workflow_validate_template
  - mcp_st3-workflow_search_documentation
  - mcp_st3-workflow_health_check
---

# QA Agent

Je bent de **QA Agent** voor het ST3 platform. Je bent **read-only** en **skeptisch**.

## Startup Protocol

Bij elke sessie (inclusief na compaction):

1. Lees `agent.md` — het volledige cooperation protocol
2. Lees `.github/.copilot-instructions.md` — de auto-loaded regels
3. Lees `docs/coding_standards/ARCHITECTURE_PRINCIPLES.md` — het bindend architectuurcontract
4. Controleer werkstatus via `get_work_context`
5. Lees het actieve planning document
6. Inspecteer diffs: `git_status` + `git_diff_stat`

## Kernregels

- **Read-only.** Je wijzigt NOOIT bestanden. Geen edits, geen commits.
- **Skeptisch.** Vertrouw geen enkele claim zonder bewijs. Verifieer alles zelf.
- **Architectuurcontract is bindend.** Purity drift = NOGO, zelfs bij groene tests.
- **English artifacts, Dutch chat.**

## Verificatie Sequentie (8 stappen)

1. Lees de relevante planning cycle sectie
2. Lees de deliverables in `.st3/projects.json`
3. Inspecteer gewijzigde bestanden en diffs
4. Draai targeted tests voor het gewijzigde oppervlak
5. Draai de stop-go test of dichtstbijzijnde MCP equivalent
6. Draai bredere verificatie alleen als de cycle bredere closure claimt
7. Onderscheid changed-file issues van baseline/branch-wide ruis
8. Voor config/schema werk: expliciete grep checks voor purity drift

## GO/NOGO Criteria

### GO (alle waar):
- Changed production surface = cycle deliverables
- Stop-go proof is materieel voldaan
- Geen in-scope blocker over
- Resterende debt is expliciet deferred door planning, niet stilzwijgend genegeerd

### NOGO (één of meer waar):
- In-scope deliverable niet gehaald
- Geclaimde proof is onwaar of incompleet
- Cycle laat verboden overblijfselen achter
- Planning en deliverables zijn tegenstrijdig
- Green bereikt door source-of-truth in verkeerde laag te duwen

### CONDITIONAL GO (zeldzaam):
- Alleen als gebruiker expliciet pragmatische beslissing wil ondanks benoemd restrisico

## Purity Drift Checks

Controleer specifiek op:
- Schema/value-object classes die canonical file paths of config-root kennis dragen
- Cross-config orchestratie state in pure schema's
- Source-of-truth kennis in verkeerde laag voor betere foutmeldingen
- Tests groen gemaakt door purer layer te contamineren

[handoff:imp] Stuur terug naar Implementation voor fixes
```

### 4.4 Handoff Flow

```
Gebruiker → @imp "Implementeer cycle C_LOADER.3"
  │
  │  IMP voert TDD uit (RED → GREEN → REFACTOR)
  │  IMP genereert hand-over (9 secties)
  │  IMP toont: [Stuur door naar QA voor verificatie]  ← handoff button
  │
  ▼
Gebruiker klikt handoff → @qa ontvangt hand-over
  │
  │  QA voert 8-staps verificatie uit
  │  QA geeft GO / NOGO / CONDITIONAL GO
  │
  │  Bij NOGO: [Stuur terug naar Implementation voor fixes]  ← handoff button
  │  Bij GO:   QA rapporteert, cycle afgerond
  │
  ▼
Volgende cycle of PR
```

---

## 5. Laag 3 — Instructions (Gedetailleerd)

### 5.1 Achtergrond: Hoe Instructions Werken

`.instructions.md` bestanden in `.github/instructions/` worden automatisch aan het system prompt toegevoegd wanneer de agent werkt met bestanden die matchen met het `applyTo` glob pattern in de YAML frontmatter. Dit voorkomt dat het volledige context window gevuld wordt met irrelevante regels.

### 5.2 Instruction: `python-backend.instructions.md`

**Bestand:** `.github/instructions/python-backend.instructions.md`

```markdown
---
applyTo: "backend/**/*.py"
---

# Backend Python Code Standards

## Architectuur Principes (Bindend)

1. **Single Responsibility (SRP):** Eén klasse, één reden om te veranderen.
2. **Config-First:** Alle policy/conventions in YAML, niet in code.
3. **Fail-Fast:** Valideer vroeg. Geen silent fallbacks.
4. **Dependency Inversion (DIP):** Depend op abstracties (`Protocol`), niet op concreetheid.
5. **No Import-Time Side Effects:** Module-level code mag geen I/O, netwerk, of state mutaties bevatten.
6. **Explicit over Implicit:** Geen magic. Geen auto-discovery. Constructor injection.

## Verboden Patronen

| Patroon | Probleem |
|---------|----------|
| `from mcp_server.* import *` | Cross-boundary import |
| `Config.from_file(...)` | Schema self-loading (SRP violation) |
| `ClassVar _instance` | Singleton anti-pattern |
| `os.environ[...]` in business logic | Config-via-env buiten composition root |
| Hardcoded paths naar `.st3/` | Config kennis in verkeerde laag |

## DTO Conventies

- Alle DTO's in `backend/dtos/`
- Erven van `BaseModel` (Pydantic v2)
- Geen business logic in DTO's
- Validatie via Pydantic validators, niet custom methods
```

### 5.3 Instruction: `python-mcp.instructions.md`

**Bestand:** `.github/instructions/python-mcp.instructions.md`

```markdown
---
applyTo: "mcp_server/**/*.py"
---

# MCP Server Code Standards

## Tool Development

- Alle tools erven van `BaseTool` (`mcp_server/tools/base.py`)
- Gebruik `args_model` (Pydantic) voor input validatie
- Return altijd `ToolResult.text()`, `ToolResult.json_data()`, of `ToolResult.error()`
- Foutafhandeling: `MCPError` hierarchy met `error_code` + `hints`
- `@tool_error_handler` decorator wordt automatisch toegepast via `__init_subclass__`

## Manager Pattern

- Managers ontvangen dependencies via constructor (DI)
- Managers bevatten business logic
- Tools delegeren naar managers — tools zijn dunne wrappers

## State Management

- Gebruik `FileStateRepository` voor `.st3/state.json` CRUD
- Altijd via `AtomicJsonWriter` (temp file + rename)
- Nooit direct `json.dump()` naar state bestanden

## Config Layer

- Schema classes (Pydantic) in `mcp_server/config/schemas/`
- Schema classes laden NIET zelf — dat doet `ConfigLoader`
- Geen `ClassVar _instance`, geen `from_file()`, geen `load()` op schema's
- Alle YAML in `.st3/config/`, geladen door `ConfigLoader.load_*_config()`

## Enforcement

- Tools declareren `enforcement_event` voor pre/post hooks
- `EnforcementRunner` handelt af op basis van `enforcement.yaml`
- Policy checks via `PolicyEngine.decide()`
```

### 5.4 Instruction: `tests.instructions.md`

**Bestand:** `.github/instructions/tests.instructions.md`

```markdown
---
applyTo: "tests/**/*.py"
---

# Test Standards

## Zone Systeem

- **Zone 1** (config): YAML toegang toegestaan. Tests in `tests/unit/mcp_server/config/`
- **Zone 2** (spec/builder): Geen YAML, pre-built objecten. Tests in `tests/unit/mcp_server/`
- **Zone 3** (managers/tools/core): Geen YAML, geen config loading. Tests in `tests/unit/mcp_server/managers/`

## Conventies

- Test bestanden: `test_<module>.py`
- Test classes: `class Test<Component>:`
- Test methods: `def test_<behavior>_<scenario>(self):`
- Gebruik `pytest` fixtures uit `conftest.py` (nooit globale state)
- Markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.acceptance`

## TDD Regels

- RED: Test eerst, implementatie daarna
- Elke test verifieert exact één gedrag
- Test names beschrijven het verwachte gedrag, niet de methode
- Geen `# type: ignore` zonder uitleg in comment

## Quality Gates

- Ruff format + lint: geen violations
- Type checking: must pass
- Coverage: ≥90% voor gewijzigde bestanden
- Architectuur review: geen cross-layer imports
```

### 5.5 Instruction: `yaml-config.instructions.md`

**Bestand:** `.github/instructions/yaml-config.instructions.md`

```markdown
---
applyTo: ".st3/config/**/*.yaml"
---

# YAML Config Standards

## Structuur

- Elk config bestand heeft een Pydantic schema in `mcp_server/config/schemas/`
- Config wordt geladen door `ConfigLoader` — nooit door de schema class zelf
- Alle config is workspace-geschikt: geen absolute paden, geen machine-specifieke waarden

## Regels

- Gebruik `version: "1.0"` header op elk config bestand
- Geen issue-specifieke waarden (Rule P-3 uit planning)
- Gebruik `{issue_number}` interpolatie waar nodig — wordt runtime opgelost
- Labels: `name:value` formaat (bijv. `type:feature`, `priority:high`)
- Workflow fasen moeten matchen met `workphases.yaml` definities
```

### 5.6 Instruction: `docs.instructions.md`

**Bestand:** `.github/instructions/docs.instructions.md`

```markdown
---
applyTo: "docs/**/*.md"
---

# Documentation Standards

## Taal

- Technische documentatie: **Engels**
- Sessie-overdrachten en design docs: Engels (tenzij expliciet anders gevraagd)
- Code comments en docstrings: Engels

## Structuur

- Issue-specifieke docs: `docs/development/issue{N}/`
- Architectuur docs: `docs/architecture/`
- Coding standards: `docs/coding_standards/`
- MCP referentie: `docs/reference/mcp/`

## Template Headers

Gebruik SCAFFOLD metadata headers:
```text
# Document Title
<!-- template=X version=Y created=Z updated= -->
```

## Linking

- Relatieve links naar andere docs
- Geen absolute filesystem paden
- Link naar issues met `#N` notatie
```

---

## 6. Laag 4 — Prompt Files (Gedetailleerd)

### 6.1 Prompt: `resume-after-compaction.prompt.md`

**Doel:** Na een context compaction event de agent snel weer op snelheid brengen.

**Bestand:** `.github/prompts/resume-after-compaction.prompt.md`

```markdown
---
description: "Herstel werkcontext na VS Code context compaction"
mode: "agent"
---

# Context Herstel Na Compaction

Je context is zojuist gecomprimeerd door VS Code. Volg dit protocol om je werkstaat te herstellen:

## Stap 1: State Ophalen

Lees de compaction state:
- Open `.st3/compaction_state.json` — bevat je laatste taak, bestanden in scope, en fase
- Verifieer met `get_work_context` voor actuele MCP state

## Stap 2: Kernbestanden Herlezen

Voer het startup protocol uit:
1. Lees `agent.md` (cooperation protocol)
2. Lees `.github/.copilot-instructions.md` (auto-loaded regels)
3. Lees `docs/coding_standards/ARCHITECTURE_PRINCIPLES.md` (architectuurcontract)
4. Lees het actieve planning document: `docs/development/issue{N}/planning.md`
5. Inspecteer de worktree: `git_status` + `git_diff_stat`

## Stap 3: Taak Hervatten

Op basis van de herstelde context:
- Identificeer de actieve cycle en deliverables
- Controleer welke bestanden al gewijzigd zijn
- Hervat waar je gebleven was

## Stap 4: Compaction Marker Opruimen

Na succesvol herstel, markeer de compaction state als afgehandeld.
```

### 6.2 Prompt: `prepare-handover.prompt.md`

**Doel:** Gestructureerde hand-over genereren vanuit de huidige werkstaat.

**Bestand:** `.github/prompts/prepare-handover.prompt.md`

```markdown
---
description: "Genereer een gestructureerde hand-over voor QA verificatie"
mode: "agent"
---

# Hand-Over Genereren

Genereer een complete hand-over op basis van de huidige werkstaat.

## Vereiste Informatie

Verzamel via MCP tools:
1. `get_work_context` — actieve issue, fase, cycle
2. `git_diff_stat` — gewijzigde bestanden
3. `run_tests` — test resultaten voor gewijzigde bestanden
4. `run_quality_gates(scope="branch")` — quality gate status

## Hand-Over Structuur (9 secties)

Vul elk van deze secties in op basis van de verzamelde data:

### 1. Scope
- Welke cycle/taak is uitgevoerd
- Wat is bewust buiten scope gehouden

### 2. Files
- Gewijzigde bestanden gegroepeerd per rol (production, test, config, docs)

### 3. Deliverables
- Welke deliverables uit `projects.json` zijn nu voldaan

### 4. Stop-Go Proof
- Exact welke tests gedraaid (commando + output)
- Exact welke gates gedraaid (commando + output)
- Exact resultaat (passed/failed counts)

### 5. Out-of-Scope
- Wat bewust niet gewijzigd is en waarom

### 6. Planning Changes
- `none` tenzij planning-reparatie gevraagd

### 7. Open Blockers
- `none` alleen als er echt geen zijn

### 8. Ready-for-QA
- `yes` of `no` met onderbouwing

### 9. Truthfulness
- Bevestig: geen overclaims, geen verborgen failures
```

### 6.3 Prompt: `qa-verify.prompt.md`

**Bestand:** `.github/prompts/qa-verify.prompt.md`

```markdown
---
description: "Voer QA verificatie uit op een hand-over"
mode: "agent"
---

# QA Verificatie

Voer een strikte QA verificatie uit op de meest recente hand-over.

## Protocol

1. **Lees de hand-over** — alle 9 secties
2. **Verifieer elke claim** — draai de tests/gates zelf opnieuw
3. **Cross-check met planning** — matchen deliverables met planning cycle?
4. **Inspecteer diffs** — zijn er onvermelde wijzigingen?
5. **Architectuur check** — purity drift analyse (grep op anti-patterns)
6. **Conclusie** — GO / NOGO / CONDITIONAL GO met onderbouwing

## Verplichte Checks

- [ ] Alle geclaimde tests draaien en zijn groen
- [ ] Quality gates passeren op branch scope
- [ ] Geen onvermelde bestandswijzigingen
- [ ] Deliverables uit projects.json zijn voldaan
- [ ] Geen architectuur violations (cross-layer imports, hardcoded config)
- [ ] Type checking slaagt
- [ ] Coverage ≥90% voor gewijzigde bestanden
```

### 6.4 Prompt: `start-tdd-cycle.prompt.md`

**Bestand:** `.github/prompts/start-tdd-cycle.prompt.md`

```markdown
---
description: "Start een nieuw TDD cycle (RED → GREEN → REFACTOR)"
mode: "agent"
---

# TDD Cycle Starten

Start een nieuw TDD cycle voor de actieve issue en planning cycle.

## Voorbereiding

1. Check werkstatus: `get_work_context`
2. Lees planning: `docs/development/issue{N}/planning.md`
3. Identificeer de actieve cycle en deliverables
4. Check `get_project_plan` voor cycle details

## RED Fase

1. Schrijf de failing test(s) voor de cycle deliverables
2. Draai de test: `run_tests(path="tests/specific_test.py")`
3. Verifieer: test FAALT (expected)
4. Commit: `git_add_or_commit(workflow_phase="tdd", sub_phase="red", message="...")`

## GREEN Fase

1. Implementeer minimale code om de test te laten slagen
2. Draai de test: `run_tests(path="tests/specific_test.py")`
3. Verifieer: test SLAAGT
4. Commit: `git_add_or_commit(workflow_phase="tdd", sub_phase="green", message="...")`

## REFACTOR Fase

1. Verbeter de code (naamgeving, structuur, DRY)
2. Draai de test: `run_tests(path="tests/specific_test.py")`
3. Verifieer: test SLAAGT nog steeds
4. Draai quality gates: `run_quality_gates(scope="files", files=[...])`
5. Commit: `git_add_or_commit(workflow_phase="tdd", sub_phase="refactor", message="...")`
```

---

## 7. Workspace Settings

### 7.1 Configuratie: `.vscode/settings.json`

**Bestand:** `.vscode/settings.json`

```json
{
  "chat.agent.enabled": true,
  "chat.hookFilesLocations": [
    ".github/hooks"
  ],
  "chat.instructionsFilesLocations": [
    ".github/instructions"
  ],
  "chat.promptFilesLocations": [
    ".github/prompts"
  ],
  "chat.agentFilesLocations": [
    ".github/agents"
  ],
  "chat.useCustomAgentHooks": true
}
```

**Toelichting:**

| Setting | Doel |
|---------|------|
| `chat.agent.enabled` | Activeert agent mode (vereist voor tools) |
| `chat.hookFilesLocations` | Locatie van hook JSON bestanden |
| `chat.instructionsFilesLocations` | Locatie van `.instructions.md` bestanden |
| `chat.promptFilesLocations` | Locatie van `.prompt.md` bestanden |
| `chat.agentFilesLocations` | Locatie van `.agent.md` bestanden |
| `chat.useCustomAgentHooks` | Agent-specifieke hooks mogelijk maken |

---

## 8. Compaction Strategie

### 8.1 Het Probleem

VS Code Copilot comprimeert de conversatiecontext wanneer het token window vol raakt (~50-100K tokens). Na compaction:

- Gaat gedetailleerde implementatiecontext verloren
- Weet de agent niet meer welke fase/cycle actief is
- Gaan hand-over details en test resultaten verloren
- Kan de agent verkeerde aannames maken

### 8.2 De Oplossing: Drielaags Recovery

```
┌─────────────────────────────────────────────────┐
│  Laag A: Preventie (PreCompact hook)            │
│  - Schrijft .st3/compaction_state.json          │
│  - Vangt bestanden in scope + laatste taak      │
│  - Automatisch, geen gebruikeractie nodig       │
├─────────────────────────────────────────────────┤
│  Laag B: Detectie (SessionStart hook)           │
│  - Leest compaction_state.json bij sessiestart  │
│  - Injecteert recovery-instructie in context    │
│  - Agent weet direct dat recovery nodig is      │
├─────────────────────────────────────────────────┤
│  Laag C: Herstel (/resume-after-compaction)     │
│  - Prompt file voor gestructureerd herstel      │
│  - Leest planning, state, diffs                 │
│  - Hervat exacte taak waar gebleven            │
└─────────────────────────────────────────────────┘
```

### 8.3 Compaction State Schema

**Bestand:** `.st3/compaction_state.json` (automatisch gegenereerd door `pre_compact.py`)

```json
{
  "needs_recovery": true,
  "timestamp": "2026-03-17T14:30:00+00:00",
  "branch": "feature/257-reorder-workflow-phases",
  "phase": "implementation",
  "cycle": 3,
  "issue_number": 257,
  "workflow": "feature",
  "agent_role": "imp",
  "last_task": "Implementeer C_LOADER.3 — ConfigLoader refactoring",
  "files_in_scope": [
    "mcp_server/config/loader.py",
    "mcp_server/config/schemas/config_schemas.py",
    "tests/unit/mcp_server/config/test_loader.py"
  ]
}
```

### 8.4 Compaction vs. Hand-Over Boundary

| Situatie | Mechanisme | Trigger |
|----------|-----------|---------|
| **Mid-task compaction** | `PreCompact` → `compaction_state.json` → `SessionStart` recovery | Automatisch |
| **Role switch IMP→QA** | IMP hand-over (9 secties) → `@qa` handoff | Gebruiker klikt handoff |
| **Nieuwe sessie** | `SessionStart` hook injecteert werkcontext | Automatisch |
| **Post-compaction in bestaande sessie** | Compacted context + `PreCompact` instructie | Automatisch |

---

## 9. Integratie met MCP Server

### 9.1 Geen Duplicatie Principe

De hooks zijn **lichtgewicht bruggen**, geen vervanging van MCP tools:

| Verantwoordelijkheid | Eigenaar | Niet |
|---------------------|----------|------|
| Fase transitie validatie | MCP `PhaseStateEngine` | Hooks |
| TDD cycle tracking | MCP `StateRepository` | Hooks |
| Quality gates uitvoering | MCP `QAManager` | Hooks |
| Git operaties | MCP `GitManager` | Hooks |
| Context injectie bij sessiestart | VS Code Hook | MCP |
| Pre-compaction state capture | VS Code Hook | MCP |
| Tool-gebruik bewaking per rol | VS Code Hook | MCP |
| Domeinspecifieke instructies laden | VS Code Instructions | MCP |
| Hand-over structuur aanbieden | VS Code Prompts | MCP |

### 9.2 Data Flow

```
VS Code Hook Scripts
       │
       ├── LEEST: .st3/state.json         (via FileStateRepository format)
       ├── LEEST: .st3/projects.json       (via ProjectManager format)
       ├── LEEST: .st3/deliverables.json   (via DeliverableChecker format)
       │
       ├── SCHRIJFT: .st3/compaction_state.json  (eigen schema, alleen hooks)
       └── SCHRIJFT: .st3/handover.json          (eigen schema, alleen hooks)
```

**Belangrijk:** Hook scripts lezen `.st3/` bestanden maar wijzigen alleen hun eigen bestanden (`compaction_state.json`, `handover.json`). Ze wijzigen NOOIT `state.json`, `projects.json`, of `deliverables.json` — dat is het domein van de MCP server.

### 9.3 Enforcement Alignment

De bestaande `enforcement.yaml` en `EnforcementRunner` werken op **MCP tool-niveau** (server-side). De VS Code `PreToolUse` hook werkt op **client-side** (vóór het MCP-verzoek). Ze zijn complementair:

```
Gebruikersverzoek
    │
    ▼
VS Code PreToolUse hook          ← Client-side gating (fase 2)
    │ (mag ik deze tool?)
    ▼
MCP Server tool dispatch
    │
    ▼
EnforcementRunner.run("pre")     ← Server-side pre-check
    │
    ▼
Tool.execute()
    │
    ▼
EnforcementRunner.run("post")    ← Server-side post-action
    │
    ▼
ToolResult terug naar VS Code
```

---

## 10. Implementatie Stappenplan

### Fase 1: Fundament (Minimale Werkbare Set)

**Prioriteit:** HOOG — Direct uitvoerbaar

| # | Actie | Bestand | Afhankelijkheden |
|---|-------|---------|-----------------|
| 1.1 | Workspace settings aanmaken | `.vscode/settings.json` | Geen |
| 1.2 | Scripts directory aanmaken | `scripts/hooks/` (lege `__init__.py`) | Geen |
| 1.3 | SessionStart hook config | `.github/hooks/session-start.json` | 1.1 |
| 1.4 | SessionStart script | `scripts/hooks/session_start.py` | 1.2, 1.3 |
| 1.5 | PreCompact hook config | `.github/hooks/pre-compact.json` | 1.1 |
| 1.6 | PreCompact script | `scripts/hooks/pre_compact.py` | 1.2, 1.5 |
| 1.7 | Resume prompt | `.github/prompts/resume-after-compaction.prompt.md` | 1.6 |
| 1.8 | Handover prompt | `.github/prompts/prepare-handover.prompt.md` | Geen |
| 1.9 | TDD cycle prompt | `.github/prompts/start-tdd-cycle.prompt.md` | Geen |
| 1.10 | Functionele test | Handmatig: nieuwe chat openen, verify context injectie | 1.1-1.7 |

**Validatie Fase 1:**
- [ ] Nieuwe chat sessie toont branch/fase/issue context
- [ ] `compaction_state.json` wordt aangemaakt vóór compaction
- [ ] `/resume-after-compaction` werkt na compaction event
- [ ] Prompts verschijnen in slash-command menu

### Fase 2: Agent Rollen (IMP/QA Split)

**Prioriteit:** HOOG — Vervolg op Fase 1

| # | Actie | Bestand | Afhankelijkheden |
|---|-------|---------|-----------------|
| 2.1 | IMP agent aanmaken | `.github/agents/imp.agent.md` | Fase 1 |
| 2.2 | QA agent aanmaken | `.github/agents/qa.agent.md` | Fase 1 |
| 2.3 | QA verify prompt | `.github/prompts/qa-verify.prompt.md` | 2.2 |
| 2.4 | Update SessionStart voor rol-detectie | `scripts/hooks/session_start.py` | 2.1, 2.2 |
| 2.5 | Functionele test | `@imp` en `@qa` beschikbaar in chat, handoff knoppen werken | 2.1-2.4 |

**Validatie Fase 2:**
- [ ] `@imp` beschikbaar in chat met correcte tool whitelist
- [ ] `@qa` beschikbaar in chat, write tools geblokkeerd
- [ ] Handoff button verschijnt na IMP hand-over
- [ ] QA ontvangt context bij handoff

### Fase 3: Domain Instructions (Context Optimalisatie)

**Prioriteit:** MEDIUM — Reduceert context window druk

| # | Actie | Bestand | Afhankelijkheden |
|---|-------|---------|-----------------|
| 3.1 | Backend Python instructions | `.github/instructions/python-backend.instructions.md` | Geen |
| 3.2 | MCP Server instructions | `.github/instructions/python-mcp.instructions.md` | Geen |
| 3.3 | Test instructions | `.github/instructions/tests.instructions.md` | Geen |
| 3.4 | YAML config instructions | `.github/instructions/yaml-config.instructions.md` | Geen |
| 3.5 | Documentation instructions | `.github/instructions/docs.instructions.md` | Geen |
| 3.6 | Validatie | Open bestanden uit elke categorie, verify instructions loading | 3.1-3.5 |

**Validatie Fase 3:**
- [ ] Bij het openen van een `backend/*.py` bestand worden backend-specifieke regels geladen
- [ ] Bij het openen van een `tests/*.py` bestand worden test-conventie regels geladen
- [ ] Instructies overlappen NIET met `.copilot-instructions.md` (geen duplicatie)

### Fase 4: Tool Gating (Enforcement Verdieping)

**Prioriteit:** LAAG — Versterkt bestaande MCP enforcement

| # | Actie | Bestand | Afhankelijkheden |
|---|-------|---------|-----------------|
| 4.1 | PreToolUse hook config | `.github/hooks/pre-tool-use.json` | Fase 2 |
| 4.2 | PreToolUse script | `scripts/hooks/pre_tool_use.py` | 4.1 |
| 4.3 | Functionele test | Verifieer QA write-block en fase gating | 4.1-4.2 |

**Validatie Fase 4:**
- [ ] `@qa` kan geen write tools aanroepen (exit code 2)
- [ ] In research fase: `git_push` geeft waarschuwing
- [ ] Bestaande MCP enforcement werkt nog steeds (geen conflict)

---

## 11. Relatie tot Bestaande Bestanden

### Bestanden die NIET wijzigen

| Bestand | Reden |
|---------|-------|
| `agent.md` | Blijft het master cooperation protocol |
| `.github/.copilot-instructions.md` | Blijft auto-loaded; instructions vullen aan, vervangen niet |
| `imp_agent.md` (workspace root) | Blijft als referentie; `.github/agents/imp.agent.md` is de VS Code integratie |
| `qa_agent.md` (workspace root) | Idem |
| `role_reset_snippets.md` | Wordt geleidelijk overbodig door hooks, maar bewaar als fallback |
| `.st3/config/enforcement.yaml` | MCP-side enforcement; hooks zijn complementair |

### Bestanden die NIEUW zijn

| Bestand | Laag | Fase |
|---------|------|------|
| `.vscode/settings.json` | Settings | 1 |
| `.github/hooks/session-start.json` | Hooks | 1 |
| `.github/hooks/pre-compact.json` | Hooks | 1 |
| `.github/hooks/pre-tool-use.json` | Hooks | 4 |
| `scripts/hooks/session_start.py` | Hooks | 1 |
| `scripts/hooks/pre_compact.py` | Hooks | 1 |
| `scripts/hooks/pre_tool_use.py` | Hooks | 4 |
| `.github/agents/imp.agent.md` | Agents | 2 |
| `.github/agents/qa.agent.md` | Agents | 2 |
| `.github/instructions/python-backend.instructions.md` | Instructions | 3 |
| `.github/instructions/python-mcp.instructions.md` | Instructions | 3 |
| `.github/instructions/tests.instructions.md` | Instructions | 3 |
| `.github/instructions/yaml-config.instructions.md` | Instructions | 3 |
| `.github/instructions/docs.instructions.md` | Instructions | 3 |
| `.github/prompts/resume-after-compaction.prompt.md` | Prompts | 1 |
| `.github/prompts/prepare-handover.prompt.md` | Prompts | 1 |
| `.github/prompts/qa-verify.prompt.md` | Prompts | 2 |
| `.github/prompts/start-tdd-cycle.prompt.md` | Prompts | 1 |

### Toekomstige `.copilot-instructions.md` Optimalisatie

Na Fase 3 kan de `.copilot-instructions.md` **uitgedund** worden doordat domeinspecifieke regels in `.instructions.md` bestanden staan. Dit bespaart tokens in elke sessie. Concrete kandidaten voor verplaatsing:

- Architectuur principes → `python-backend.instructions.md` + `python-mcp.instructions.md`
- Test conventies → `tests.instructions.md`
- Config regels → `yaml-config.instructions.md`

**Let op:** Dit is een latere optimalisatie. Eerst de 4 fases stabiel uitrollen.

---

## 12. Bekende Beperkingen & Risico's

| Risico | Impact | Mitigatie |
|--------|--------|----------|
| Hooks zijn Preview feature (VS Code 1.108+) | API kan wijzigen | Hooks zijn lichtgewicht scripts; makkelijk aan te passen |
| Hook timeout (max 60s) | Trage state reads kunnen falen | Scripts lezen alleen JSON; << 1s execution time |
| `PreCompact` heeft geen garantie op volledige history | Sommige context kan al verloren zijn | `compaction_state.json` bevat altijd `.st3/state.json` data (persistent) |
| Custom agents delen geen in-memory context | Handoff verliest conversatie-nuance | Hand-over document (9 secties) compenseert; MCP state is persistent |
| `.instructions.md` `applyTo` is file-based | Kan niet conditioneren op fase | Fase-gating via hooks, niet via instructions |
| Tool whitelist in `.agent.md` is statisch | Kan niet dynamisch per fase wijzigen | Fase-based tool gating via `PreToolUse` hook (Fase 4) |

---

## 13. Toekomstige Uitbreidingen

Na succesvolle implementatie van Fase 1-4:

1. **`SubagentStart`/`SubagentStop` hooks** — Context injectie voor subagent calls (bijv. Explore agent krijgt domeincontext)
2. **`PostToolUse` hook** — Automatische state refresh na destructieve MCP operaties
3. **Agent-scoped hooks** — Verschillende hook gedrag per agent (bijv. IMP krijgt schrijf-context, QA krijgt verificatie-context)
4. **`.copilot-instructions.md` debloating** — Verplaats domeinregels naar `.instructions.md` bestanden
5. **MCP Resource integratie** — `st3://hooks/status` resource voor hook health monitoring

---

## Appendix A: Bestandsboom Na Implementatie

```
.github/
├── .copilot-instructions.md          # Bestaand (ongewijzigd)
├── agents/
│   ├── imp.agent.md                  # Implementation agent (Fase 2)
│   └── qa.agent.md                   # QA agent (Fase 2)
├── hooks/
│   ├── session-start.json            # SessionStart config (Fase 1)
│   ├── pre-compact.json              # PreCompact config (Fase 1)
│   └── pre-tool-use.json             # PreToolUse config (Fase 4)
├── instructions/
│   ├── python-backend.instructions.md # Backend rules (Fase 3)
│   ├── python-mcp.instructions.md     # MCP server rules (Fase 3)
│   ├── tests.instructions.md          # Test conventions (Fase 3)
│   ├── yaml-config.instructions.md    # Config rules (Fase 3)
│   └── docs.instructions.md           # Documentation rules (Fase 3)
└── prompts/
    ├── plan-executionDirectiveBatchCoordination.prompt.md  # Bestaand
    ├── resume-after-compaction.prompt.md                    # Fase 1
    ├── prepare-handover.prompt.md                           # Fase 1
    ├── qa-verify.prompt.md                                  # Fase 2
    └── start-tdd-cycle.prompt.md                            # Fase 1

.vscode/
└── settings.json                      # Workspace settings (Fase 1)

scripts/
├── hooks/
│   ├── session_start.py               # SessionStart script (Fase 1)
│   ├── pre_compact.py                 # PreCompact script (Fase 1)
│   └── pre_tool_use.py                # PreToolUse script (Fase 4)
├── analyze_quality.py                 # Bestaand
└── capture_baselines.py               # Bestaand

.st3/
├── state.json                         # Bestaand (gelezen door hooks)
├── projects.json                      # Bestaand (gelezen door hooks)
├── deliverables.json                  # Bestaand (gelezen door hooks)
├── compaction_state.json              # NIEUW (geschreven door pre_compact.py)
├── handover.json                      # NIEUW (optioneel, geschreven door hooks)
└── config/
    └── ...                            # Bestaand (ongewijzigd)
```

## Appendix B: Quick Reference Card

```
┌─────────────────────────────────────────────────────────────────┐
│  ST3 Agent Orchestration — Quick Reference                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  🔄 Context Recovery:                                          │
│     /resume-after-compaction  → Herstel na compaction          │
│                                                                 │
│  📋 Workflow:                                                   │
│     /start-tdd-cycle          → Start RED→GREEN→REFACTOR       │
│     /prepare-handover         → Genereer 9-sectie hand-over   │
│     /qa-verify                → QA verificatie op hand-over    │
│                                                                 │
│  👤 Agents:                                                     │
│     @imp                      → Implementation (TDD + scope)   │
│     @qa                       → QA (read-only + GO/NOGO)       │
│                                                                 │
│  🔗 Handoff:                                                    │
│     IMP → QA:  Klik "Stuur door naar QA" na hand-over         │
│     QA → IMP:  Klik "Stuur terug naar Implementation" na NOGO │
│                                                                 │
│  📂 State:                                                      │
│     .st3/state.json           → Fase/cycle (MCP owned)         │
│     .st3/compaction_state.json → Recovery data (hook owned)    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```
