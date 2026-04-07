# VS Code Agent Orchestration — Design & Implementation Plan

**Status:** APPROVED DESIGN  
**Version:** 2.0  
**Created:** 2026-03-17  
**Updated:** 2026-03-17  
**Author:** Research phase, issue #257 branch  
**Scope:** Cross-cutting infrastructure — VS Code hooks, custom agents, instructions, prompts  

---

## 1. Executive Summary

Dit document beschrijft een complete, uitvoerbare architectuur voor VS Code Copilot's native orchestratiefuncties, naadloos geïntegreerd met de bestaande ST3 MCP Server. Het doel is vierledig:

1. **Automatische context-recovery na compaction** — via `PreCompact` en `SessionStart` hooks
2. **Fase-bewuste agent orchestratie voor ALLE workphases** — via 4 gespecialiseerde agents met handoffs
3. **Domeinspecifieke instructies** — via `.instructions.md` bestanden per bestandstype
4. **Fase-specifieke slash commands** — via `.prompt.md` bestanden per workflow fase

### Het Producer/Verifier Patroon

De kern van de orchestratie is een universeel **producer/verifier** patroon dat op elke fase toepasbaar is:

```
┌────────────────┐          hand-over          ┌────────────────┐
│   PRODUCER     │ ───────────────────────────► │   VERIFIER     │
│   (fase-       │                              │   (@qa)        │
│    specifiek)  │ ◄─────────────────────────── │                │
│                │    GO / NOGO / CONDITIONAL   │   Universeel   │
└────────────────┘                              └────────────────┘
     @researcher (research/planning/design)
     @imp        (implementation)
     @writer     (documentation/coordination)
```

| Workphase | Producer Agent | Verifier Agent | Artifact Type |
|-----------|---------------|----------------|---------------|
| Research | `@researcher` | `@qa` | research.md, findings |
| Planning | `@researcher` | `@qa` | planning.md, projects.json |
| Design | `@researcher` | `@qa` | design.md, contracts |
| Implementation | `@imp` | `@qa` | Code + tests (TDD) |
| Validation | `@imp` | `@qa` | e2e/acceptance tests |
| Documentation | `@writer` | `@qa` | Reference docs, guides |
| Coordination | `@writer` | `@qa` | Child issues, epic sync |

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

### Laag 2 — Custom Agents (producer/verifier per fase)

| Bestand | Rol | Fasen |
|---------|-----|-------|
| `.github/agents/researcher.agent.md` | Research/Planning/Design producer | research, planning, design |
| `.github/agents/imp.agent.md` | Implementation producer (TDD) | implementation, validation |
| `.github/agents/writer.agent.md` | Documentation/Coordination producer | documentation, coordination |
| `.github/agents/qa.agent.md` | Universele verifier (alle fasen) | ALLE fasen |

### Laag 3 — Instructions (domeinspecifiek)

| Bestand | `applyTo` | Doel |
|---------|----------|------|
| `.github/instructions/python-backend.instructions.md` | `backend/**/*.py` | Architectuur principes voor backend code |
| `.github/instructions/python-mcp.instructions.md` | `mcp_server/**/*.py` | MCP server conventies (BaseTool, ToolResult) |
| `.github/instructions/tests.instructions.md` | `tests/**/*.py` | Test conventies (zones, fixtures, markers) |
| `.github/instructions/yaml-config.instructions.md` | `.st3/config/**/*.yaml` | Config schema regels |
| `.github/instructions/docs.instructions.md` | `docs/**/*.md` | Documentatie standaarden |

### Laag 4 — Prompt Files (herbruikbare taken)

| Bestand | Slash Command | Fase |
|---------|--------------|------|
| `.github/prompts/resume-after-compaction.prompt.md` | `/resume-after-compaction` | Alle fasen |
| `.github/prompts/prepare-handover.prompt.md` | `/prepare-handover` | Alle fasen |
| `.github/prompts/qa-verify.prompt.md` | `/qa-verify` | Alle fasen |
| `.github/prompts/start-research.prompt.md` | `/start-research` | Research |
| `.github/prompts/start-planning.prompt.md` | `/start-planning` | Planning |
| `.github/prompts/start-design.prompt.md` | `/start-design` | Design |
| `.github/prompts/start-tdd-cycle.prompt.md` | `/start-tdd-cycle` | Implementation |
| `.github/prompts/start-validation.prompt.md` | `/start-validation` | Validation |
| `.github/prompts/start-documentation.prompt.md` | `/start-documentation` | Documentation |
| `.github/prompts/start-coordination.prompt.md` | `/start-coordination` | Coordination |

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

## 4. Fase-Bewust Agent Model (Architectuur)

### 4.1 Design Rationale: Waarom 4 Agents

Elke van de 7 workphases (research, planning, design, implementation, validation, documentation, coordination) heeft een fundamenteel andere aard. Maar het **producer/verifier** patroon is universeel. De keuze voor precies 4 agents is gebaseerd op:

1. **Minimale set** — Minder agents = minder onderhoud, minder verwarring
2. **Natuurlijke clustering** — Fasen met vergelijkbare tooling en output clusteren samen
3. **Universele verifier** — QA past zich aan per fase maar houdt dezelfde skeptische core

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    Workflow Phase Progression                            │
│                                                                         │
│  research → planning → design → implementation → validation → docs     │
│  ▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀   ▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀▀   ▀▀▀▀▀  │
│       @researcher                      @imp                   @writer  │
│                                                                         │
│  ◄──────── @qa verifieert ELKE faseovergang ────────────────────────►  │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Agent Mapping per Workflow Type

De 6 workflow types (uit `workflows.yaml`) gebruiken verschillende fase-combinaties. De agent-toewijzing volgt automatisch uit de fase:

| Workflow | Fases | Agent Sequentie |
|----------|-------|-----------------|
| **feature** | research → planning → design → implementation → validation → documentation | `@researcher` → `@qa` → `@researcher` → `@qa` → `@researcher` → `@qa` → `@imp` → `@qa` → `@imp` → `@qa` → `@writer` → `@qa` |
| **bug** | research → planning → design → implementation → validation → documentation | Zelfde als feature |
| **hotfix** | implementation → validation → documentation | `@imp` → `@qa` → `@imp` → `@qa` → `@writer` → `@qa` |
| **refactor** | research → planning → implementation → validation → documentation | `@researcher` → `@qa` → `@researcher` → `@qa` → `@imp` → `@qa` → `@imp` → `@qa` → `@writer` → `@qa` |
| **docs** | planning → documentation | `@researcher` → `@qa` → `@writer` → `@qa` |
| **epic** | research → planning → design → coordination → documentation | `@researcher` → `@qa` → `@researcher` → `@qa` → `@researcher` → `@qa` → `@writer` → `@qa` → `@writer` → `@qa` |

**Patroon:** Elke fase = 1 producer + 1 verifier stap. De `SessionStart` hook detecteert de huidige fase en adviseert welke agent gebruikt moet worden.

### 4.3 Agent: `@researcher` — Pre-Implementation Fasen

**Scope:** Research, Planning, Design  
**Kerngedrag:** Analyseren, structureren, documenteren (geen code-productie)

**Bestand:** `.github/agents/researcher.agent.md`

```markdown
---
description: "Researcher Agent — Analyse, planning en design voor pre-implementatie fasen"
tools:
  - mcp_st3-workflow_scaffold_artifact
  - mcp_st3-workflow_safe_edit_file
  - mcp_st3-workflow_create_file
  - mcp_st3-workflow_git_add_or_commit
  - mcp_st3-workflow_git_status
  - mcp_st3-workflow_git_diff_stat
  - mcp_st3-workflow_git_stash
  - mcp_st3-workflow_git_restore
  - mcp_st3-workflow_git_list_branches
  - mcp_st3-workflow_transition_phase
  - mcp_st3-workflow_force_phase_transition
  - mcp_st3-workflow_get_work_context
  - mcp_st3-workflow_get_issue
  - mcp_st3-workflow_get_project_plan
  - mcp_st3-workflow_save_planning_deliverables
  - mcp_st3-workflow_update_planning_deliverables
  - mcp_st3-workflow_validate_architecture
  - mcp_st3-workflow_search_documentation
  - mcp_st3-workflow_health_check
  - mcp_st3-workflow_create_issue
  - mcp_st3-workflow_list_issues
  - mcp_st3-workflow_update_issue
---

# Researcher Agent

Je bent de **Researcher Agent** voor het ST3 platform. Je opereert in de **research**, **planning** en **design** fasen.

## Startup Protocol

Bij elke sessie (inclusief na compaction):

1. Lees `agent.md` — het volledige cooperation protocol
2. Lees `.github/.copilot-instructions.md` — de auto-loaded regels
3. Lees `docs/coding_standards/ARCHITECTURE_PRINCIPLES.md` — het bindend architectuurcontract
4. Controleer werkstatus via `get_work_context`
5. Lees bestaande issue-documenten in `docs/development/issue{N}/`
6. Inspecteer de worktree: `git_status` + `git_diff_stat`

## Fase-Specifiek Gedrag

### Research Fase
- **Doel:** Probleemanalyse, requirements gathering, technische verkenning
- **Output:** `research.md` in `docs/development/issue{N}/`
- **Subphases:** Geen
- **Tool:** `scaffold_artifact(artifact_type="research", ...)`
- **Exit criterium:** Research document aanwezig (file glob check)
- **Commit type:** `docs(P_RESEARCH): ...`

### Planning Fase
- **Doel:** TDD cycle breakdown, taakdecompositie, dependency analyse
- **Output:** `planning.md` + `save_planning_deliverables` naar `projects.json`
- **Subphases:** c1, c2, c3, c4 (planning cycles)
- **Tool:** `scaffold_artifact(artifact_type="planning", ...)`
- **Exit criterium:** Planning deliverables opgeslagen in projects.json
- **Commit type:** `docs(P_PLANNING): ...`

### Design Fase
- **Doel:** Interface contracts, data flows, schemas, architectuurbeslissingen
- **Output:** `design.md` in `docs/development/issue{N}/`
- **Subphases:** contracts, flows, schemas
- **Tool:** `scaffold_artifact(artifact_type="design", ...)`
- **Exit criterium:** Design document met contracts en flows
- **Commit type:** `docs(P_DESIGN): ...`

## Kernregels

- **Geen productie-code schrijven.** Alleen documentatie, analyse en planning.
- **Architectuurcontract is bindend.** Ontwerpen die het contract schenden = NOGO.
- **Gebruik alleen MCP tools.** Scaffolding via `scaffold_artifact`, nooit handmatig.
- **English artifacts, Dutch chat.**
- **Exit criteria zijn verplicht.** Geen fase-transitie zonder bewezen exit criteria.

## Hand-Over Format (Onderzoek/Planning/Design)

Na afronding van een fase, lever een hand-over met deze secties:

1. **Fase** — welke fase afgerond (research/planning/design)
2. **Artifacts** — geproduceerde documenten met pad en samenvatting
3. **Beslissingen** — genomen architectuur/design beslissingen met rationale
4. **Open Vragen** — onbeantwoorde vragen die in latere fasen opgepakt moeten worden
5. **Exit Criteria Proof** — bewijs dat exit criteria voldaan (file exists, deliverables saved)
6. **Aanbeveling Volgende Fase** — wat de volgende fase nodig heeft als input
7. **Ready-for-QA** — `yes` of `no`

## Scope Lock

- **Research:** Scope = issue beschrijving + expliciete research vragen
- **Planning:** Scope = research findings → cycle breakdown + deliverables
- **Design:** Scope = planning cycles → interface contracts + data flows

[handoff:qa] Stuur door naar QA voor verificatie
```

### 4.4 Agent: `@imp` — Implementation & Validation

**Scope:** Implementation (TDD), Validation (e2e/acceptance)  
**Kerngedrag:** Code schrijven via TDD, tests uitbreiden, quality gates

> De `@imp` agent specificatie uit v1.0 blijft ongewijzigd (zie sectie 5.2). Het enige verschil is dat `@imp` nu ook de **validation** fase dekt.

**Validation fase toevoeging aan `@imp`:**

```markdown
## Fase-Specifiek Gedrag

### Implementation Fase
- **Doel:** RED → GREEN → REFACTOR
- **Subphases:** red, green, refactor
- **Exit criterium:** Alle cycle deliverables groen, quality gates pass
- **Commit types:** `test(P_IMPLEMENTATION_SP_RED)`, `feat(P_IMPLEMENTATION_SP_GREEN)`, `refactor(P_IMPLEMENTATION_SP_REFACTOR)`

### Validation Fase
- **Doel:** End-to-end testing, acceptance testing, systeemintegratie
- **Subphases:** e2e, acceptance
- **Output:** e2e test suites, acceptance test suites
- **Exit criterium:** Alle e2e/acceptance tests groen, integratietest coverage voldoende
- **Commit type:** `test(P_VALIDATION_SP_E2E)`, `test(P_VALIDATION_SP_ACCEPTANCE)`
- **Verschil met implementation:** Geen RED→GREEN→REFACTOR loop, maar bredere test coverage
- **Tool focus:** `run_tests(scope="full")`, `run_quality_gates(scope="branch")`
```

### 4.5 Agent: `@writer` — Documentation & Coordination

**Scope:** Documentation, Coordination  
**Kerngedrag:** Referentiedocumentatie schrijven, epic-coördinatie, child issue management

**Bestand:** `.github/agents/writer.agent.md`

```markdown
---
description: "Writer Agent — Documentatie en epic-coördinatie"
tools:
  - mcp_st3-workflow_scaffold_artifact
  - mcp_st3-workflow_safe_edit_file
  - mcp_st3-workflow_create_file
  - mcp_st3-workflow_git_add_or_commit
  - mcp_st3-workflow_git_status
  - mcp_st3-workflow_git_diff_stat
  - mcp_st3-workflow_git_stash
  - mcp_st3-workflow_git_restore
  - mcp_st3-workflow_git_list_branches
  - mcp_st3-workflow_transition_phase
  - mcp_st3-workflow_force_phase_transition
  - mcp_st3-workflow_get_work_context
  - mcp_st3-workflow_get_issue
  - mcp_st3-workflow_get_project_plan
  - mcp_st3-workflow_validate_architecture
  - mcp_st3-workflow_search_documentation
  - mcp_st3-workflow_health_check
  - mcp_st3-workflow_create_issue
  - mcp_st3-workflow_list_issues
  - mcp_st3-workflow_update_issue
  - mcp_st3-workflow_close_issue
  - mcp_st3-workflow_create_pr
  - mcp_st3-workflow_list_prs
---

# Writer Agent

Je bent de **Writer Agent** voor het ST3 platform. Je opereert in de **documentation** en **coordination** fasen.

## Startup Protocol

Bij elke sessie (inclusief na compaction):

1. Lees `agent.md` — het volledige cooperation protocol
2. Lees `.github/.copilot-instructions.md` — de auto-loaded regels
3. Lees `docs/coding_standards/ARCHITECTURE_PRINCIPLES.md` — het bindend architectuurcontract
4. Controleer werkstatus via `get_work_context`
5. Lees het actieve planning document en design document
6. Inspecteer de worktree: `git_status` + `git_diff_stat`

## Fase-Specifiek Gedrag

### Documentation Fase
- **Doel:** Referentiedocumentatie, handleidingen, agent instructies
- **Subphases:** reference, guides, agent
- **Output:** Bestanden in `docs/` (reference, architecture, coding_standards)
- **Tool:** `scaffold_artifact(artifact_type="reference|generic", ...)`
- **Exit criterium:** Alle geplande documentatie geschreven en gelinkt
- **Commit type:** `docs(P_DOCUMENTATION_SP_REFERENCE)`, `docs(P_DOCUMENTATION_SP_GUIDES)`, `docs(P_DOCUMENTATION_SP_AGENT)`

### Coordination Fase (Epics)
- **Doel:** Child issue aanmaak, cross-issue synchronisatie, epic-level review
- **Subphases:** delegation, sync, review
- **Output:** Child issues in GitHub, epic tracking document
- **Tools:** `create_issue`, `list_issues`, `update_issue`, `create_pr`
- **Exit criterium:** Alle child issues aangemaakt en gekoppeld aan epic
- **Commit type:** `chore(P_COORDINATION_SP_DELEGATION)`, `chore(P_COORDINATION_SP_SYNC)`

## Kernregels

- **Geen productie-code schrijven.** Alleen documentatie en issue-management.
- **Volg documentatiestandaarden.** Zie `docs/coding_standards/` voor formatting.
- **English artifacts, Dutch chat.**
- **Scaffold templates gebruiken.** `scaffold_artifact` voor alle doc types.
- **Coordination = child issues.** Geen directe code in epics; delegeer naar child issues.

## Hand-Over Format (Documentation/Coordination)

Na afronding van een fase:

1. **Fase** — welke fase afgerond (documentation/coordination)
2. **Artifacts** — geproduceerde documenten of aangemaakte issues met pad/nummer
3. **Coverage** — welke onderdelen gedocumenteerd/gedelegeerd, welke nog niet
4. **Links** — kruisverwijzingen tussen docs, of parent↔child issue koppelingen
5. **Exit Criteria Proof** — documentatie compleet, issues aangemaakt
6. **Ready-for-QA** — `yes` of `no`

[handoff:qa] Stuur door naar QA voor verificatie
```

### 4.6 Agent: `@qa` — Universele Verifier (Fase-Bewust)

**Scope:** ALLE fasen — maar met fase-specifieke verificatiecriteria

De QA agent is de **constante** in het systeem. Het kerngedrag (skeptisch, read-only, bewijs-gebaseerd) verandert niet. Wat wél verandert per fase zijn de **verificatiecriteria** en de **specifieke checks**.

**Bestand:** `.github/agents/qa.agent.md`

```markdown
---
description: "QA Agent — Universele verifier met fase-specifieke GO/NOGO criteria"
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
  - mcp_st3-workflow_list_issues
---

# QA Agent

Je bent de **QA Agent** voor het ST3 platform. Je bent **read-only** en **skeptisch**.
Je verifieert het werk van ALLE producer agents (`@researcher`, `@imp`, `@writer`) in ALLE fasen.

## Startup Protocol

Bij elke sessie (inclusief na compaction):

1. Lees `agent.md` — het volledige cooperation protocol
2. Lees `.github/.copilot-instructions.md` — de auto-loaded regels
3. Lees `docs/coding_standards/ARCHITECTURE_PRINCIPLES.md` — het bindend architectuurcontract
4. Controleer werkstatus via `get_work_context` — **bepaal huidige fase**
5. Lees het relevante planning/design/research document
6. Inspecteer diffs: `git_status` + `git_diff_stat`

## Kernregels (ALLE Fasen)

- **Read-only.** Je wijzigt NOOIT bestanden. Geen edits, geen commits.
- **Skeptisch.** Vertrouw geen enkele claim zonder bewijs. Verifieer alles zelf.
- **Architectuurcontract is bindend.** Purity drift = NOGO, zelfs bij groene tests.
- **English artifacts, Dutch chat.**

## Fase-Specifieke Verificatie

### Research Fase — QA Criteria

**Verifieer het werk van `@researcher`:**

| Check | Methode | GO als... |
|-------|---------|-----------|
| Research document bestaat | `file glob: docs/development/issue{N}/*research*.md` | Bestand bestaat en is niet leeg |
| Probleemstelling helder | Lees document | Problem statement bevat concrete, verifieerbare claims |
| Scope duidelijk afgebakend | Lees document | In-scope en out-of-scope secties aanwezig |
| Research vragen beantwoord | Lees document | Alle gestelde vragen hebben een beargumenteerd antwoord |
| Architectuur alignment | Cross-check met ARCHITECTURE_PRINCIPLES.md | Geen voorstellen die het architectuurcontract schenden |

**NOGO triggers:**
- Research document ontbreekt of is placeholder-only
- Conclusies niet onderbouwd met bewijs (code analyse, grep resultaten, etc.)
- Scope te vaag om planning op te baseren
- Voorgestelde richting schendt architectuurprincipes

### Planning Fase — QA Criteria

**Verifieer het werk van `@researcher`:**

| Check | Methode | GO als... |
|-------|---------|-----------|
| Planning document compleet | File check | planning.md bevat alle cycles |
| Deliverables geregistreerd | `get_project_plan` | projects.json bevat cycle deliverables |
| Cycles hebben clear exit criteria | Lees planning | Elke cycle heeft verifieerbare "validates" |
| Dependencies correct | Lees planning | Cycle ordering respecteert afhankelijkheden |
| Realistische scope per cycle | Lees planning | Geen cycle met >5 deliverables |
| Rule P-4 (Built and Wired) | Cross-check | Elke component heeft consumer + test + old-path removal |

**NOGO triggers:**
- Cycles ontbreken verifieerbare exit criteria
- Dependencies zijn circulair of ontbreken
- Deliverables niet in projects.json geregistreerd
- Cycle scope onrealistisch (te veel of te vaag)

### Design Fase — QA Criteria

**Verifieer het werk van `@researcher`:**

| Check | Methode | GO als... |
|-------|---------|-----------|
| Design document compleet | File check | design.md bevat contracts, flows, schemas |
| Interface contracts verifieerbaar | Lees document | Contracts bevatten method signatures, types, pre/postcondities |
| Data flows compleet | Lees document | Alle entry/exit punten beschreven |
| Architectuur alignment | `validate_architecture` + cross-check | Geen DIP/SRP/ISP violations in ontwerp |
| Backward compatibility | Lees document | Breaking changes expliciet benoemd |
| Design volgt planning | Cross-check planning.md | Design dekt alle geplande cycles |

**NOGO triggers:**
- Contracts zijn te abstract (geen concrete types/signatures)
- Data flows hebben gaten (onbeschreven edge cases)
- Design schendt architectuurprincipes
- Geen backward compatibility analyse voor bestaande code

### Implementation Fase — QA Criteria

> Identiek aan de bestaande QA specificatie (v1.0). Zie de volledige verificatie sequentie (8 stappen), GO/NOGO criteria, en purity drift checks hieronder in sectie 5.3.

### Validation Fase — QA Criteria

**Verifieer het werk van `@imp`:**

| Check | Methode | GO als... |
|-------|---------|-----------|
| E2E tests bestaan | File check in tests/acceptance/ of tests/integration/ | Test bestanden voor alle geplande scenarios |
| E2E tests groen | `run_tests(path="tests/acceptance/")` | Alle tests PASS |
| Coverage voldoende | `run_quality_gates(scope="branch")` | Coverage ≥90% voor gewijzigde code |
| Regressie check | `run_tests(path="tests/")` | Full suite geen nieuwe failures |
| Integration completeness | Grep/search | Nieuwe componenten daadwerkelijk geïntegreerd (Rule P-4) |

**NOGO triggers:**
- E2E tests ontbreken voor geplande scenarios
- Nieuwe failures in de volledige test suite
- Coverage onder drempel
- Componenten gebouwd maar niet geïntegreerd (wiring gaps)

### Documentation Fase — QA Criteria

**Verifieer het werk van `@writer`:**

| Check | Methode | GO als... |
|-------|---------|-----------|
| Geplande docs geschreven | File check | Alle geplande documenten bestaan |
| Cross-referenties correct | Link check | Links naar andere docs zijn geldig |
| Technische accuraatheid | Cross-check met code | Beschreven API's/interfaces matchen met actual code |
| Formatting correct | Lees document | Volgt docs/coding_standards/ standaarden |
| Agent instructions actueel | Lees `.copilot-instructions.md` | Nieuwe tools/workflows gedocumenteerd |

**NOGO triggers:**
- Documenten ontbreken of zijn placeholder-only
- Links verwijzen naar niet-bestaande bestanden
- Beschreven interfaces wijken af van actual code
- Agent instructions niet bijgewerkt na code wijzigingen

### Coordination Fase — QA Criteria

**Verifieer het werk van `@writer`:**

| Check | Methode | GO als... |
|-------|---------|-----------|
| Child issues aangemaakt | `list_issues` | Alle geplande child issues bestaan |
| Parent-child koppeling | `get_issue` per child | Child issues verwijzen naar epic |
| Scope coverage | Cross-check epic met children | Alle epic deliverables gedekt door child issues |
| Geen overlap | Vergelijk child scopes | Geen dubbele scope tussen child issues |
| Labels correct | `list_issues` | Alle children hebben correcte type/priority/scope labels |

**NOGO triggers:**
- Geplande child issues ontbreken
- Child issues niet aan epic gekoppeld
- Scope gaten: epic deliverables niet gedekt door children
- Scope overlap: meerdere children dekken hetzelfde

## Universele GO/NOGO (Alle Fasen)

### GO (alle waar):
- Fase-specifieke exit criteria voldaan
- Hand-over is volledig en waarheidsgetrouw
- Geen in-scope blocker over
- Architectuurcontract niet geschonden

### NOGO (één of meer waar):
- Exit criteria niet gehaald
- Geclaimde bewijs is onwaar of incompleet
- Onvermeld werk buiten scope
- Architectuurcontract geschonden

### CONDITIONAL GO (zeldzaam):
- Alleen als gebruiker expliciet pragmatisch besluit wil ondanks benoemd restrisico

## Handoff per Fase

Bij NOGO stuur je terug naar de juiste producer:

[handoff:researcher] Stuur terug naar Researcher voor fixes (research/planning/design)
[handoff:imp] Stuur terug naar Implementation voor fixes (implementation/validation)
[handoff:writer] Stuur terug naar Writer voor fixes (documentation/coordination)
```

### 4.7 Volledige Handoff Matrix

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Handoff Flow per Fase                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  RESEARCH:                                                          │
│    @researcher ──► hand-over ──► @qa                               │
│       ▲                           │                                 │
│       └── NOGO ◄─────────────────┘                                 │
│                    GO → transition_phase("planning")                │
│                                                                     │
│  PLANNING:                                                          │
│    @researcher ──► hand-over ──► @qa                               │
│       ▲                           │                                 │
│       └── NOGO ◄─────────────────┘                                 │
│                    GO → transition_phase("design")                  │
│                                                                     │
│  DESIGN:                                                            │
│    @researcher ──► hand-over ──► @qa                               │
│       ▲                           │                                 │
│       └── NOGO ◄─────────────────┘                                 │
│                    GO → transition_phase("implementation")          │
│                                                                     │
│  IMPLEMENTATION:                                                    │
│    @imp ──► hand-over (9 secties) ──► @qa                          │
│      ▲                                 │                            │
│      └── NOGO ◄───────────────────────┘                            │
│                    GO → transition_phase("validation")              │
│                                                                     │
│  VALIDATION:                                                        │
│    @imp ──► hand-over ──► @qa                                      │
│      ▲                     │                                        │
│      └── NOGO ◄───────────┘                                        │
│                    GO → transition_phase("documentation")           │
│                                                                     │
│  DOCUMENTATION:                                                     │
│    @writer ──► hand-over ──► @qa                                   │
│       ▲                       │                                     │
│       └── NOGO ◄─────────────┘                                     │
│                    GO → create_pr / close_issue                     │
│                                                                     │
│  COORDINATION (epics):                                              │
│    @writer ──► hand-over ──► @qa                                   │
│       ▲                       │                                     │
│       └── NOGO ◄─────────────┘                                     │
│                    GO → transition_phase("documentation")           │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 4.8 SessionStart Hook — Fase-Bewuste Agent Suggestie

De `session_start.py` hook (sectie 3.2) wordt uitgebreid met fase-specifieke agent-aanbevelingen:

```python
# In _build_instructions() — toevoegen na branch/phase/issue info:

PHASE_AGENT_MAP: dict[str, str] = {
    "research": "researcher",
    "planning": "researcher",
    "design": "researcher",
    "implementation": "imp",
    "validation": "imp",
    "documentation": "writer",
    "coordination": "writer",
}

# Add agent recommendation
recommended_agent = PHASE_AGENT_MAP.get(phase, "copilot")
lines.extend([
    "",
    f"**Aanbevolen agent:** `@{recommended_agent}` voor de `{phase}` fase.",
    f"Gebruik `@qa` na afronding voor verificatie.",
])
```

Dit zorgt ervoor dat de agent bij elke sessiestart direct weet welke rol-agent passend is voor de huidige fase.

### 4.9 PreToolUse Hook — Fase-Bewuste Rolbescherming

De `pre_tool_use.py` hook (sectie 3.4) wordt uitgebreid met agent→fase alignment checks:

```python
# Agent → allowed phases mapping
AGENT_PHASE_MAP: dict[str, set[str]] = {
    "researcher": {"research", "planning", "design"},
    "imp": {"implementation", "validation"},
    "writer": {"documentation", "coordination"},
    "qa": {
        "research", "planning", "design",
        "implementation", "validation",
        "documentation", "coordination",
    },
}

# In main():
agent_name = event.get("chatContext", {}).get("agentName", "copilot")
state = _read_json(workspace / ".st3" / "state.json")
phase = state.get("current_phase", "")

# Check agent→phase alignment
if agent_name in AGENT_PHASE_MAP:
    allowed_phases = AGENT_PHASE_MAP[agent_name]
    if phase and phase not in allowed_phases:
        result = {
            "instructions": (
                f"⚠️ Agent `@{agent_name}` is niet bedoeld voor de "
                f"`{phase}` fase. Overweeg `@{PHASE_AGENT_MAP.get(phase, 'copilot')}`."
            ),
        }
        sys.stdout.write(json.dumps(result))
        sys.exit(0)  # Warn, don't block
```

---

## 5. Laag 2 — Custom Agent Bestanden (v1.0 Referentie)

> **Noot:** Deze sectie bevat de oorspronkelijke v1.0 agent specs (`@imp` en `@qa`).
> In v2.0 zijn `@researcher` en `@writer` toegevoegd (zie sectie 4.3 en 4.5).
> De `@qa` agent is uitgebreid met fase-specifieke criteria (sectie 4.6).

### 5.1 Achtergrond: Hoe Custom Agents Werken

Custom agents zijn `.agent.md` bestanden in `.github/agents/`. Ze:

- Verschijnen als `@agent-naam` in de chat
- Hebben YAML frontmatter met `description`, `tools`, en optioneel `hooks`
- Ondersteunen **handoffs** — knoppen die de gebruiker naar een andere agent sturen
- Kunnen tool-gebruik beperken (whitelist)
- Kunnen agent-specifieke hooks hebben (vereist `chat.useCustomAgentHooks: true`)

### 5.2 Agent: `imp.agent.md`

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

### 5.3 Agent: `qa.agent.md`

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

### 5.4 Handoff Flow

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

## 6. Laag 3 — Instructions (Gedetailleerd)

### 6.1 Achtergrond: Hoe Instructions Werken

`.instructions.md` bestanden in `.github/instructions/` worden automatisch aan het system prompt toegevoegd wanneer de agent werkt met bestanden die matchen met het `applyTo` glob pattern in de YAML frontmatter. Dit voorkomt dat het volledige context window gevuld wordt met irrelevante regels.

### 6.2 Instruction: `python-backend.instructions.md`

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

### 6.3 Instruction: `python-mcp.instructions.md`

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

### 6.4 Instruction: `tests.instructions.md`

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

### 6.5 Instruction: `yaml-config.instructions.md`

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

### 6.6 Instruction: `docs.instructions.md`

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

## 7. Laag 4 — Prompt Files (Gedetailleerd)

### 7.1 Prompt: `resume-after-compaction.prompt.md`

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

### 7.2 Prompt: `prepare-handover.prompt.md`

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

### 7.3 Prompt: `qa-verify.prompt.md`

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

### 7.4 Prompt: `start-tdd-cycle.prompt.md`

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

### 7.5 Fase-Specifieke Prompts (v2.0)

De volgende prompts bieden gestructureerde workflows voor elke workphase:

#### `/start-research`

**Bestand:** `.github/prompts/start-research.prompt.md`

```markdown
---
description: "Start de research fase voor een issue"
mode: "agent"
---

# Research Fase Starten

Start het research-proces voor de actieve issue.

## Voorbereiding

1. Check werkstatus: `get_work_context`
2. Lees de issue beschrijving: `get_issue`
3. Verifieer dat je in de `research` fase bent

## Research Protocol

1. **Probleemanalyse** — Analyseer de issue en identificeer de kernvraag
2. **Codebase verkenning** — Zoek relevante code met `search_documentation` en codebase reads
3. **Bestaande docs** — Check `docs/development/` voor gerelateerd werk
4. **Architectuur alignment** — Cross-check met `docs/coding_standards/ARCHITECTURE_PRINCIPLES.md`

## Output

Scaffold het research document:
```
scaffold_artifact(artifact_type="research", name="issue-research", context={
    "title": "Research — Issue #{N}",
    "purpose": "...",
    "scope_in": "...",
    "scope_out": "...",
})
```

Commit: `git_add_or_commit(workflow_phase="research", message="...")`

## Afronding

Gebruik `/prepare-handover` om een hand-over te genereren voor `@qa`.
```

#### `/start-planning`

**Bestand:** `.github/prompts/start-planning.prompt.md`

```markdown
---
description: "Start de planning fase — cycle breakdown en deliverables"
mode: "agent"
---

# Planning Fase Starten

Start het planningsproces op basis van het research document.

## Voorbereiding

1. Check werkstatus: `get_work_context`
2. Lees het research document: `docs/development/issue{N}/*research*.md`
3. Verifieer dat je in de `planning` fase bent

## Planning Protocol

1. **Research findings reviewen** — Wat zijn de conclusies uit de research?
2. **Cycle breakdown** — Splits het werk in TDD-able cycles (max 5 deliverables per cycle)
3. **Dependencies bepalen** — Welke cycles hangen af van andere?
4. **Exit criteria per cycle** — Elke cycle heeft verifieerbare "validates"
5. **Deliverables registreren** — Via `save_planning_deliverables`

## Output

Scaffold het planning document:
```
scaffold_artifact(artifact_type="planning", name="issue-planning", context={
    "title": "Planning — Issue #{N}",
    "purpose": "...",
})
```

Registreer deliverables: `save_planning_deliverables(issue_number=N, deliverables={...})`
Commit: `git_add_or_commit(workflow_phase="planning", message="...")`

## Afronding

Gebruik `/prepare-handover` om een hand-over te genereren voor `@qa`.
```

#### `/start-design`

**Bestand:** `.github/prompts/start-design.prompt.md`

```markdown
---
description: "Start de design fase — interface contracts en data flows"
mode: "agent"
---

# Design Fase Starten

Start het design-proces op basis van planning en research.

## Voorbereiding

1. Check werkstatus: `get_work_context`
2. Lees het planning document: `docs/development/issue{N}/planning.md`
3. Lees het research document: `docs/development/issue{N}/*research*.md`
4. Verifieer dat je in de `design` fase bent

## Design Protocol

### Subphase: Contracts
1. **Interface definities** — Protocol classes met method signatures, types, pre/postcondities
2. **API contracts** — Input/output schemas, foutcondities
3. **Backward compatibility** — Welke bestaande interfaces wijzigen?

### Subphase: Flows
1. **Data flow diagrammen** — Entry points, transformaties, exit points
2. **Sequence diagrams** — Interaction tussen componenten
3. **Error flows** — Wat gebeurt als stap X faalt?

### Subphase: Schemas
1. **Data structuren** — DTOs, config schemas, state schemas
2. **Validatie regels** — Pydantic validators, constraints

## Output

Scaffold het design document:
```
scaffold_artifact(artifact_type="design", name="issue-design", context={
    "title": "Design — Issue #{N}",
    "purpose": "...",
})
```

Commit: `git_add_or_commit(workflow_phase="design", message="...")`

## Afronding

Gebruik `/prepare-handover` om een hand-over te genereren voor `@qa`.
```

#### `/start-validation`

**Bestand:** `.github/prompts/start-validation.prompt.md`

```markdown
---
description: "Start de validation fase — e2e en acceptance testing"
mode: "agent"
---

# Validation Fase Starten

Start het validatieproces na afronding van de implementation fase.

## Voorbereiding

1. Check werkstatus: `get_work_context`
2. Lees het planning document voor geplande test scenarios
3. Verifieer dat je in de `validation` fase bent

## Validation Protocol

### Subphase: E2E
1. **Scenario identificatie** — Welke end-to-end scenarios moeten getest?
2. **Test schrijven** — E2E tests in `tests/integration/` of `tests/acceptance/`
3. **Draai tests** — `run_tests(path="tests/integration/")`
4. **Commit** — `git_add_or_commit(workflow_phase="validation", sub_phase="e2e", message="...")`

### Subphase: Acceptance
1. **Acceptance criteria** — Vanuit planning deliverables
2. **Acceptance tests** — In `tests/acceptance/`
3. **Full suite check** — `run_tests(path="tests/")` voor regressie
4. **Quality gates** — `run_quality_gates(scope="branch")`
5. **Commit** — `git_add_or_commit(workflow_phase="validation", sub_phase="acceptance", message="...")`

## Afronding

Gebruik `/prepare-handover` om een hand-over te genereren voor `@qa`.
```

#### `/start-documentation`

**Bestand:** `.github/prompts/start-documentation.prompt.md`

```markdown
---
description: "Start de documentation fase — referentiedocs en handleidingen"
mode: "agent"
---

# Documentation Fase Starten

Start het documentatieproces na afronding van validation.

## Voorbereiding

1. Check werkstatus: `get_work_context`
2. Lees de design en planning documenten voor context
3. Verifieer dat je in de `documentation` fase bent

## Documentation Protocol

### Subphase: Reference
1. **API documentatie** — Nieuwe tools, resources, endpoints documenteren
2. **Architectuur docs** — Updates aan `docs/architecture/` indien nodig
3. **Coding standards** — Updates aan `docs/coding_standards/` indien nodig

### Subphase: Guides
1. **Gebruikershandleidingen** — Voor nieuwe functionaliteit
2. **Migratiegids** — Als breaking changes geïntroduceerd zijn

### Subphase: Agent
1. **Agent instructies** — Update `.copilot-instructions.md` als nieuwe tools/workflows zijn toegevoegd
2. **Issue overdracht** — `docs/development/issue{N}/` opruimen en afronden

## Output

Scaffold documenten via:
```
scaffold_artifact(artifact_type="reference|generic", name="...", context={...})
```

Commit: `git_add_or_commit(workflow_phase="documentation", sub_phase="reference", message="...")`

## Afronding

Gebruik `/prepare-handover` om een hand-over te genereren voor `@qa`.
Na QA GO: `create_pr` voor merge naar main.
```

#### `/start-coordination`

**Bestand:** `.github/prompts/start-coordination.prompt.md`

```markdown
---
description: "Start de coordination fase — epic child issue management"
mode: "agent"
---

# Coordination Fase Starten (Epics)

Start het coördinatieproces voor een epic issue.

## Voorbereiding

1. Check werkstatus: `get_work_context`
2. Lees het design document voor de epic breakdown
3. Verifieer dat je in de `coordination` fase bent en workflow = `epic`

## Coordination Protocol

### Subphase: Delegation
1. **Child issues identificeren** — Welke deelgebieden uit het design?
2. **Issues aanmaken** — `create_issue` per child met correcte labels en parent-referentie
3. **Scope verdeling** — Label elke child met `scope:*` en `priority:*`
4. **Milestone koppeling** — Indien van toepassing

### Subphase: Sync
1. **Voortgang check** — `list_issues` om child status te bekijken
2. **Cross-issue afhankelijkheden** — Documenteer in epic tracking doc
3. **Blocker identificatie** — Welke children blokkeren andere?

### Subphase: Review
1. **Epic completeness** — Alle children afgerond of in progress?
2. **Scope coverage** — Alle epic deliverables gedekt door children?
3. **Tracking document** — Update epic-level tracking

## Output

Child issues via `create_issue(issue_type="feature|bug", parent_issue=N, ...)`
Tracking doc via `scaffold_artifact(artifact_type="tracking", ...)`
Commit: `git_add_or_commit(workflow_phase="coordination", sub_phase="delegation", message="...")`

## Afronding

Gebruik `/prepare-handover` om een hand-over te genereren voor `@qa`.
```

---

## 8. Workspace Settings

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

## 9. Compaction Strategie

### 9.1 Het Probleem

VS Code Copilot comprimeert de conversatiecontext wanneer het token window vol raakt (~50-100K tokens). Na compaction:

- Gaat gedetailleerde implementatiecontext verloren
- Weet de agent niet meer welke fase/cycle actief is
- Gaan hand-over details en test resultaten verloren
- Kan de agent verkeerde aannames maken

### 9.2 De Oplossing: Drielaags Recovery

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

### 9.3 Compaction State Schema

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

### 9.4 Compaction vs. Hand-Over Boundary

| Situatie | Mechanisme | Trigger |
|----------|-----------|---------|
| **Mid-task compaction** | `PreCompact` → `compaction_state.json` → `SessionStart` recovery | Automatisch |
| **Role switch IMP→QA** | IMP hand-over (9 secties) → `@qa` handoff | Gebruiker klikt handoff |
| **Nieuwe sessie** | `SessionStart` hook injecteert werkcontext | Automatisch |
| **Post-compaction in bestaande sessie** | Compacted context + `PreCompact` instructie | Automatisch |

---

## 10. Integratie met MCP Server

### 10.1 Geen Duplicatie Principe

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

### 10.2 Data Flow

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

### 10.3 Enforcement Alignment

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

## 11. Implementatie Stappenplan

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
| 1.10 | Research prompt | `.github/prompts/start-research.prompt.md` | Geen |
| 1.11 | Planning prompt | `.github/prompts/start-planning.prompt.md` | Geen |
| 1.12 | Design prompt | `.github/prompts/start-design.prompt.md` | Geen |
| 1.13 | Validation prompt | `.github/prompts/start-validation.prompt.md` | Geen |
| 1.14 | Documentation prompt | `.github/prompts/start-documentation.prompt.md` | Geen |
| 1.15 | Coordination prompt | `.github/prompts/start-coordination.prompt.md` | Geen |
| 1.16 | Functionele test | Handmatig: nieuwe chat openen, verify context injectie | 1.1-1.15 |

**Validatie Fase 1:**
- [ ] Nieuwe chat sessie toont branch/fase/issue context
- [ ] `compaction_state.json` wordt aangemaakt vóór compaction
- [ ] `/resume-after-compaction` werkt na compaction event
- [ ] Alle 10 prompts verschijnen in slash-command menu
- [ ] Fase-specifieke prompts bevatten correcte MCP tool aanroepen

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

### Fase 2b: Fase-Bewuste Agents (v2.0) — @researcher & @writer

**Prioriteit:** HOOG — Maakt alle fases agentic

| # | Actie | Bestand | Afhankelijkheden |
|---|-------|---------|-----------------|
| 2b.1 | Researcher agent aanmaken | `.github/agents/researcher.agent.md` | Fase 1 |
| 2b.2 | Writer agent aanmaken | `.github/agents/writer.agent.md` | Fase 1 |
| 2b.3 | Update SessionStart voor fase→agent mapping | `scripts/hooks/session_start.py` | 2b.1, 2b.2 |
| 2b.4 | Update PreToolUse voor agent→fase alignment | `scripts/hooks/pre_tool_use.py` | 2b.1, 2b.2 |
| 2b.5 | QA uitbreiden met per-fase GO/NOGO criteria | `.github/agents/qa.agent.md` | 2.2 |
| 2b.6 | Functionele test | `@researcher` en `@writer` beschikbaar, fase-routing werkt | 2b.1-2b.5 |

**Validatie Fase 2b:**
- [ ] `@researcher` beschikbaar in research/planning/design fases
- [ ] `@writer` beschikbaar in documentation/coordination fases
- [ ] SessionStart suggereert correct agent per fase
- [ ] PreToolUse blokkeert code-editing tools voor `@researcher`
- [ ] `@qa` levert fase-specifieke GO/NOGO criteria (niet alleen TDD)

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

## 12. Relatie tot Bestaande Bestanden

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

## 13. Bekende Beperkingen & Risico's

| Risico | Impact | Mitigatie |
|--------|--------|----------|
| Hooks zijn Preview feature (VS Code 1.108+) | API kan wijzigen | Hooks zijn lichtgewicht scripts; makkelijk aan te passen |
| Hook timeout (max 60s) | Trage state reads kunnen falen | Scripts lezen alleen JSON; << 1s execution time |
| `PreCompact` heeft geen garantie op volledige history | Sommige context kan al verloren zijn | `compaction_state.json` bevat altijd `.st3/state.json` data (persistent) |
| Custom agents delen geen in-memory context | Handoff verliest conversatie-nuance | Hand-over document (9 secties) compenseert; MCP state is persistent |
| `.instructions.md` `applyTo` is file-based | Kan niet conditioneren op fase | Fase-gating via hooks, niet via instructions |
| Tool whitelist in `.agent.md` is statisch | Kan niet dynamisch per fase wijzigen | Fase-based tool gating via `PreToolUse` hook (Fase 4) |

---

## 14. Toekomstige Uitbreidingen

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
│   ├── qa.agent.md                   # QA agent (Fase 2)
│   ├── researcher.agent.md           # Research/Planning/Design agent (Fase 2b)
│   └── writer.agent.md               # Documentation/Coordination agent (Fase 2b)
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
    ├── start-tdd-cycle.prompt.md                            # Fase 1
    ├── start-research.prompt.md                             # Fase 1
    ├── start-planning.prompt.md                             # Fase 1
    ├── start-design.prompt.md                               # Fase 1
    ├── start-validation.prompt.md                           # Fase 1
    ├── start-documentation.prompt.md                        # Fase 1
    └── start-coordination.prompt.md                         # Fase 1

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
│  ST3 Agent Orchestration — Quick Reference (v2.0)              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  🔄 Context Recovery:                                          │
│     /resume-after-compaction  → Herstel na compaction          │
│                                                                 │
│  📋 Fase-Specifieke Workflows:                                  │
│     /start-research           → Research fase protocol         │
│     /start-planning           → Planning cyclus breakdown      │
│     /start-design             → Design contracts & flows       │
│     /start-tdd-cycle          → RED→GREEN→REFACTOR (impl)      │
│     /start-validation         → E2E en acceptance testing      │
│     /start-documentation      → Reference docs & guides        │
│     /start-coordination       → Epic child issue management    │
│                                                                 │
│  🤝 Handover & Verificatie:                                     │
│     /prepare-handover         → Genereer 9-sectie hand-over   │
│     /qa-verify                → QA verificatie op hand-over    │
│                                                                 │
│  👤 Producer Agents (schrijven output):                         │
│     @researcher               → Research / Planning / Design   │
│     @imp                      → Implementation (TDD + scope)   │
│     @writer                   → Documentation / Coordination   │
│                                                                 │
│  🔍 Verifier Agent (read-only controle):                       │
│     @qa                       → Universeel GO/NOGO (alle fases)│
│                                                                 │
│  🔗 Handoff Patronen:                                           │
│     @researcher → @qa   na research/planning/design output     │
│     @imp → @qa           na TDD cycle of validation            │
│     @writer → @qa        na documentation output               │
│     @qa → producer       bij NOGO (terug naar juiste agent)    │
│                                                                 │
│  📂 State:                                                      │
│     .st3/state.json           → Fase/cycle (MCP owned)         │
│     .st3/compaction_state.json → Recovery data (hook owned)    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```
