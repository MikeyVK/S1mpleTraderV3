<!-- docs\development\issue263\design_crosschat_block_enforcement.md -->
<!-- template=design version=5827e841 created=2026-03-24T11:56Z updated= -->
# Cross-Chat Block Enforcement — Three-Layer Injection Architecture

**Status:** APPROVED — ready for implementation  
**Version:** 1.3  
**Last Updated:** 2026-03-24

---

## Purpose

Define a consistent canonical injection strategy for cross-chat handover block instructions across all three VS Code hook intervention points: UserPromptSubmit (S1), PreCompact (S2), and Stop (S3).

## Scope

**In Scope:**
build_crosschat_block_instruction() canonical function; build_ups_output() refactor; build_compaction_output() loader injection; evaluate_stop_hook() camelCase fix; notify_compaction.py; detect_sub_role.py; stop_handover_guard.py

**Out of Scope:**
MCP server changes; new agent roles; sub-role detection algorithm changes; compliance detection via response text (confirmed impossible — Stop payload contains no response); UserPromptSubmit hook payload format changes

## Prerequisites

Read these first:
1. research_sub_role_detection_v2.md
2. design_v2_sub_role_orchestration.md
3. STOP_HOOK_REENTRANCY_FINDINGS_20260324.md
4. SESSIE_OVERDRACHT_20260323_STOP_HOOK_ANALYSE.md
---

## 1. Context & Requirements

### 1.1. Problem Statement

The model receives three different, inconsistent messages about the cross-chat handover block requirement across a single session: a minimal hint at UserPromptSubmit (S1), a plain sub-role reminder at PreCompact (no block spec), and a full verbose template at Stop (S3, too late). This inconsistency reduces compliance. Additionally, the Stop hook reads stop_hook_active (snake_case) but VS Code sends stopHookActive (camelCase), making the re-entry guard inoperative. Empirical testing confirmed the Stop payload contains no response text, so compile-time compliance detection is impossible via Stop hook alone.

### 1.2. Requirements

**Functional:**
- [ ] A single canonical function build_crosschat_block_instruction(sub_role, spec) produces one compact, complete instruction string from the YAML spec
- [ ] UserPromptSubmit (build_ups_output) uses the canonical function and injects the full block template on every sub-role detection when requires_crosschat_block=true
- [ ] PreCompact (build_compaction_output) receives loader and role as required parameters, checks requires_crosschat_block, and calls build_crosschat_block_instruction directly to inject the identical instruction after context compaction
- [ ] Stop hook (evaluate_stop_hook) also uses the canonical function for its correction prompt, prefixed with 'Write NOW.'
- [ ] Stop hook re-entry guard corrected from snake_case stop_hook_active to camelCase stopHookActive to match VS Code payload spec
- [ ] All three injection points produce recognisably identical instructions so the model sees repetition as reinforcement, not contradiction

**Non-Functional:**
- [ ] Instruction string stays under 200 characters excluding required section markers to avoid context pollution
  - *Verificatie:* parametrised unit test die alle sub-roles enumereert via de loader en voor elke sub-role asserteert: `len(build_crosschat_block_instruction(sub_role, spec).split("Required sections:")[0]) < 200`. De test mag geen hardcoded sub-role namen bevatten — enumerate rechtstreeks uit `loader.valid_sub_roles(role)` zodat nieuwe sub-roles automatisch meelopen.
- [ ] No new files — all changes in detect_sub_role.py, notify_compaction.py, stop_handover_guard.py
- [ ] Backward compatible: sub-roles with requires_crosschat_block=false are unaffected at all three points (clean-break uitzondering: bestaande test call sites voor build_ups_output en build_compaction_output moeten bijgewerkt worden vanwege de verplichte role-parameter)
- [ ] build_crosschat_block_instruction is a pure function (no I/O, no side effects) — fully unit-testable
- [ ] build_compaction_output signature change is a clean break — loader and role are required; no optional defaults

### 1.3. Constraints

None
---

## 2. Design Options

Twee alternatieven overwogen:

**Optie A — Drie afzonderlijke instructieteksten (status quo):** elke hook bouwt zijn eigen string. Leidt tot de geconstateerde inconsistentie.

**Optie B — Canonieke functie + hergebruik (gekozen):** één functie produceert de instructie; alle drie hooks delegeren. Elimineer drift per definitie.

**Optie C — Compliance detectie via `transcript_path`:** Stop hook leest het JSONL transcript om de laatste assistant message te inspecteren en blokkeert alleen bij ontbrekende markers. Verworpen: file I/O in een hot hook, kwetsbaar voor async schrijfvertragingen, en de drie-laags prevention maakt corrigerende compliance-check minder kritisch.

---

## 3. Chosen Design

**Decision:** Introduce build_crosschat_block_instruction(sub_role, spec) as the canonical source of truth for the handover block instruction. Refactor build_ups_output to use it. Extend build_compaction_output with loader+role parameters and calls build_crosschat_block_instruction directly (DIP: sibling-hook import vermeden). Update build_stop_reason to use the canonical function prefixed with Write NOW. Fix the camelCase/snake_case re-entry guard bug. No compliance detection based on response text (empirically confirmed: Stop payload has no response field).

**Rationale:** Three injection points with identical content creates reinforcement without redundancy — the model cannot claim it did not receive the instruction. Canonical function eliminates drift between the three points. The camelCase fix corrects a silent bug that made the re-entry guard dead code under VS Code. No new files and no new abstractions keeps complexity at minimum. Compliance detection via transcript_path (also present in Stop payload) is deferred — the benefit does not justify the file I/O cost of reading the transcript in a hot hook path.

### 3.1. Canonical Instruction Function

Locatie: `detect_sub_role.py` (naast de bestaande `build_ups_output`).

```python
def build_crosschat_block_instruction(sub_role: str, spec: SubRoleSpec) -> str:
    """Canonical cross-chat block instruction injected at all three hook points.

    Compact, complete, and identical at S1/S2/S3 to create reinforcement.
    Pure function — no I/O, no side effects.
    """
    markers = "\n".join(f"  {i+1}. {m}" for i, m in enumerate(spec["markers"]))
    return (
        f"[{sub_role}] End your response with this block:\n\n"
        "```text\n"
        f"{spec['block_prefix'].strip()}\n"
        f"{spec['guide_line'].strip()}\n"
        "```\n\n"
        f"Required sections:\n{markers}"
    )
```

**Ontwerpkeuzes:**
- `block_prefix` en `guide_line` worden via `.strip()` ontdaan van eventuele trailing whitespace — `sub-role-requirements.yaml` bevat block_prefix waarden met trailing spaties die anders de trigger-parse van de cross-chat ontvanger verstoren
- Markers zijn genummerd maar zonder uitgebreide uitleg — herhaling door de drie injection punten is de redundantie, niet het tekstvolume
- `block_prefix_hint` en `marker_verb` worden **niet** opgenomen — die waren meta-uitleg voor S3 (Stop), nu overbodig omdat S1 al de volledige template geeft

---

### 3.2. Injection Point S1 — UserPromptSubmit (`detect_sub_role.py`)

**Huidige `build_ups_output`:**
```python
msg = (
    f"Active sub-role: {sub_role}. "
    "Your final response MUST include a copy-paste handover block. "
    "Do not stop without it."
)
```

**Na refactor** — roept de canonieke functie aan. `role` is een **verplichte** parameter (geen default); backward compat is hier geen doel.

```python
def build_ups_output(
    sub_role: str,
    loader: ISubRoleRequirementsLoader,
    role: str,        # REQUIRED — geen default waarde
) -> JsonObject:
    if not loader.requires_crosschat_block(role, sub_role):
        return {}
    spec = loader.get_requirement(role, sub_role)
    return {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "systemMessage": build_crosschat_block_instruction(sub_role, spec),
        }
    }
```

**Call sites die bijgewerkt moeten worden:**
- `__main__`-block in `detect_sub_role.py`: huidig `build_ups_output(sub_role, loader)` → `build_ups_output(sub_role, loader, role)` (de `role`-variabele is al beschikbaar uit het state-bestand)

---

### 3.3. Injection Point S2 — PreCompact (`notify_compaction.py`)

**Huidige `build_compaction_output`** heeft geen toegang tot de loader — levert alleen de sub-role naam.

**Na refactor** — clean break: `loader` en `role` zijn **verplichte** parameters (geen defaults). Backward compat is geen doel; bestaande tests moeten bijgewerkt worden om de nieuwe signature te respecteren.

**DIP-compliance:** `notify_compaction.py` importeert `build_crosschat_block_instruction` rechtstreeks uit `detect_sub_role.py` — *niet* `build_ups_output`. Dit voorkomt directe koppeling tussen twee sibling hooks. `build_crosschat_block_instruction` is de stabiele, pure interface; `build_ups_output` is hook-specifieke output-constructie en niet bedoeld voor cross-module gebruik.

```python
from copilot_orchestration.hooks.detect_sub_role import build_crosschat_block_instruction

def build_compaction_output(
    state: dict[str, object],
    loader: ISubRoleRequirementsLoader,   # REQUIRED — geen default
    role: str,                            # REQUIRED — geen default
) -> dict[str, object]:
    sub_role = state.get("sub_role")
    if not sub_role:
        return {}

    base = (
        f"Context was compacted. Active sub-role: **{sub_role}**. "
        "Use /resume-work to restore full context."
    )

    if not loader.requires_crosschat_block(role, str(sub_role)):
        # Sub-role does not require a crosschat block — return base message only.
        return {"systemMessage": base}

    spec = loader.get_requirement(role, str(sub_role))
    # ConfigError propagates if sub_role is unknown — consistent with evaluate_stop_hook.
    base += "\n\n" + build_crosschat_block_instruction(str(sub_role), spec)

    logger.info("compaction output: sub_role=%s", sub_role)
    return {"systemMessage": base}
```

**Waarom `\n\n` en niet `" "`:** `build_crosschat_block_instruction` produceert een markdown code fence (begint met ` ```text `). Een spatie vóór een code fence geeft malformed output; `\n\n` zorgt voor correcte markdown rendering.

**`__main__`-block update** (beide parameters verplicht doorgeven):
```python
_loader = SubRoleRequirementsLoader.from_copilot_dir(workspace_root)
print(json.dumps(build_compaction_output(state, _loader, role)))
```

**Effect:** het model ziet na elke compaction exact dezelfde template als bij S1, voorafgegaan door de compaction-context zin.

---

### 3.4. Injection Point S3 — Stop (`stop_handover_guard.py`)

**Twee wijzigingen:**

#### Wijziging A — camelCase re-entry guard fix

```python
def is_stop_retry_active(event: JsonObject) -> bool:
    # VS Code sends stopHookActive (camelCase) — confirmed by VS Code source docs.
    # The live payload observed on 2026-03-24 showed "stop_hook_active" (snake_case);
    # this was a VS Code implementation artefact. Clean-break decision: read camelCase only.
    value = event.get("stopHookActive")   # ← was: "stop_hook_active"
    if isinstance(value, bool):
        return value
    return False
```

**Beslissing (clean break):** Uitsluitend `stopHookActive` (camelCase) uitlezen, conform de VS Code spec. De `stop_hook_active` snake_case observatie in de live log van 2026-03-24 was een tijdelijk VS Code implementatie-artefact. Geen dual-key fallback — zie §3.5 voor afwijzing van die aanpak.

#### Wijziging B — canonieke instructie in stop reason

`build_stop_reason()` wordt vervangen door een aanroep van de canonieke functie:

```python
def build_stop_reason(spec: SubRoleSpec, sub_role: str) -> str:
    return "Write NOW.\n\n" + build_crosschat_block_instruction(sub_role, spec)
```

Aanroep in `evaluate_stop_hook`:
```python
return {
    "hookSpecificOutput": {
        "hookEventName": "Stop",
        "decision": "block",
        "reason": build_stop_reason(spec, sub_role),
    }
}
```

**Geen compliance check** — de Stop payload bevat geen response tekst (live bevestigd 2026-03-24: payload heeft uitsluitend `timestamp`, `hook_event_name`, `session_id`, `transcript_path`, `stop_hook_active`, `cwd`). De hook blokkeert altijd wanneer `requires_crosschat_block=true` en de re-entry vlag niet gezet is.

---

### 3.5. camelCase Beslissing — Definitief

**Beslissing: uitsluitend `stopHookActive` (camelCase) uitlezen.** Geen dual-key fallback.

**Achtergrond:** De live Stop payload op 2026-03-24 bevatte `"stop_hook_active": false` (snake_case). Dit leidde in de vorige sessie tot de hypothese dat VS Code snake_case implementeert. Nader onderzoek laat zien dat dit een tijdelijk VS Code implementatie-artefact was, en de VS Code broncode documentatie specificeert `stopHookActive` (camelCase) als de canonieke naam.

**Afwijzing dual-key aanpak:** Een defensieve `event.get("stopHookActive") or event.get("stop_hook_action")` constructie is verworpen. Redenen:
1. *Correctheid boven verdediging*: als de spec camelCase zegt, implementeren we camelCase. Legacy snake_case fallback maskeert potentiële regressies bij VS Code updates.
2. *Consistentie met clean-break beleid* (zie ook §3.2 en §3.3): deze sessie maakt geen concessies voor backward compat.
3. *Testbaarheid*: één vaste key is deterministisch testbaar; een OR-expressie vereist twee testpaden per guard-call.

**Actie voor STOP_HOOK_REENTRANCY_FINDINGS_20260324.md:** Finding 1 in dat document moet bijgewerkt worden als onderdeel van de implementatie-commit — de correcte conclusie is `stopHookActive` (camelCase), niet snake_case.

---

### 3.6. Resulterende instructie (voorbeeld voor `implementer`)

Identiek op alle drie injection punten (S3 prefixed met "Write NOW."):

```
[implementer] End your response with this block:

```text
verifier
Review the latest implementation work on this branch.
```

Required sections:
  1. Scope
  2. Files Changed
  3. Proof
  4. Ready-for-QA
```

---

### 3.7. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Canonieke functie in `detect_sub_role.py` | Naast `build_ups_output` — geen nieuw bestand, directe hergebruik |
| Clean break: `loader` en `role` verplicht in `build_compaction_output` + `build_ups_output` | Correctheid boven backward compat; bestaande test call sites bijwerken is kleiner dan een optioneel-param maze |
| `notify_compaction.py` importeert `build_crosschat_block_instruction`, niet `build_ups_output` | DIP: stabiele canonieke functie als interface; hook-specifieke output-functie blijft intern |
| `\n\n` als separator voor canonical instruction in S2 | Code fence na spatie geeft malformed markdown; `\n\n` is correct |
| `block_prefix` en `guide_line` via `.strip()` | Trailing whitespace in YAML verstoort trigger-parse bij ontvanger |
| `block_prefix_hint` en `marker_verb` niet in canonieke string | Ze waren meta-uitleg voor een verbos S3 formaat; niet nodig bij drie-keer-herhaling |
| Geen compliance detectie via `transcript_path` | File I/O in een hot hook pad; baat rechtvaardigt kost niet |
| Uitsluitend `stopHookActive` (camelCase) uitlezen | Conform VS Code spec; geen dual-key fallback om regressies niet te maskeren |

## Related Documentation
- **[docs/development/issue263/design_v2_sub_role_orchestration.md][related-1]**
- **[src/copilot_orchestration/hooks/detect_sub_role.py][related-2]**
- **[src/copilot_orchestration/hooks/notify_compaction.py][related-3]**
- **[src/copilot_orchestration/hooks/stop_handover_guard.py][related-4]**

<!-- Link definitions -->

[related-1]: docs/development/issue263/design_v2_sub_role_orchestration.md
[related-2]: src/copilot_orchestration/hooks/detect_sub_role.py
[related-3]: src/copilot_orchestration/hooks/notify_compaction.py
[related-4]: src/copilot_orchestration/hooks/stop_handover_guard.py

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-03-24 | Agent | Initial draft — full design based on empirical Stop payload analysis |
| 1.1 | 2026-03-24 | Agent | QA blockers resolved: B1 (clean-break camelCase, §3.4+§3.5), B2 (role required in §3.2), B3 (\n\n separator §3.3); CS1 (DIP fix), CS2 (clean-break §3.3), CS3 (type narrowing §3.3); non-blockers: .strip() §3.1, 200-char test spec §1.2, §3.7 updated |
| 1.2 | 2026-03-24 | Agent | QA v1.1 blockers: B1 requires_crosschat_block guard toegevoegd §3.3; B2 §1.2 req-3 herschreven (DIP-beslissing); M1 dode None-check verwijderd; M2 falsy "if spec:" guard verwijderd (fail-fast) |
| 1.3 | 2026-03-24 | Agent | QA v1.2 blockers: B1 §3 Decision delegeert niet meer aan build_ups_output; B2 stale call-site bullet verwijderd §3.2; B3 list_sub_roles → valid_sub_roles §1.2; M1 stale None-guard rij verwijderd §3.7 |