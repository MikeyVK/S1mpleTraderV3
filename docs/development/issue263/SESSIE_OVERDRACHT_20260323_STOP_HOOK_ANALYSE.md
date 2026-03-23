# Sessieoverdracht — 23 maart 2026 — Stop Hook Compliance Analyse

## Context

Branch: `feature/263-vscode-implementation-orchestration`
Sessie: QA analyse van stop hook compliance na alle F1/F2/F3 fixes.
Aanleiding: Stop hook vuurde correct (BLOCK stop in log), maar model negeerde de
correction prompt en produceerde geen cross-chat handover block.

## Analyse: VS Code Stop Hook Contract

De VS Code Stop hook is **soft-blocking by design**:

1. Hook retourneert `"decision": "block"` → VS Code stuurt correction prompt naar model
2. Bij retry zet VS Code `stop_hook_active: true` in de event payload
3. Hook **moet** dan `{}` retourneren (pass-through) om infinite loops te voorkomen
4. Model krijgt exact **één** retry-kans — daarna wordt de chat gesloten

Het probleem is model compliance: het model kan de correction prompt negeren.

## Drie-vlaks verbetervoorstel — Kritische beoordeling

### Strategie 1: Front-loading via UserPromptSubmit — PASS

**Concept**: Injecteer een `systemMessage` vooraan in de sessie zodra een sub-role
met `requires_crosschat_block: true` gedetecteerd wordt. Het model ziet de instructie
*voordat* het begint te genereren, niet pas bij de stop.

**Implementatie**: `detect_sub_role.py` uitbreiden met `hookSpecificOutput`:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "UserPromptSubmit",
    "systemMessage": "Your active sub-role requires a cross-chat handover block..."
  }
}
```

**Beoordeling**:
- Architecturaal correct — UserPromptSubmit is het juiste hook-punt (sub-role is dan
  al gedetecteerd, in tegenstelling tot SessionStart waar sub-role nog onbekend is)
- Hoogste verwachte impact op compliance
- Geen afhankelijkheid van ongedocumenteerd VS Code-gedrag
- Risico: context bloat bij lange sessies (elke prompt krijgt de systemMessage).
  Houd tekst kort (max ~200 chars)

**Prioriteit**: **EERST implementeren** — hoogste impact, laagste risico.

### Strategie 2: Reason text optimalisatie — PASS

**Concept**: Optimaliseer de `build_stop_reason()` output in `stop_handover_guard.py`
voor maximale directiviteit binnen de ene retry-kans.

**Concrete verbeterrichting**:
- Korter en assertiever — "Write the block NOW" in plaats van uitgebreide uitleg
- Herhaal de front-load instructie zodat het model twee keer dezelfde opdracht ziet
- Verwijder meta-instructies die tokens verspillen zonder compliance te verhogen
  (bijv. "No prose, explanation, or apology")
- Houd tekst model-agnostisch (niet optimaliseren voor één specifiek model)

**Beoordeling**:
- Low-hanging fruit, complementair aan strategie 1
- De huidige `build_stop_reason()` is al goed gestructureerd (6 regels, template)
  maar kan assertiever

**Prioriteit**: Tweede — laag risico, direct toepasbaar.

### Strategie 3: Configureerbare retry counter — CONCERN

**Concept**: Vervang de binaire `stop_hook_active` check door een teller die bijhoudt
hoeveel keer de stop hook getriggerd is, tot `max_stop_retries` bereikt is.

**Twee fundamentele problemen**:

#### Probleem A: Ongedocumenteerd VS Code-gedrag

De strategie draait om de aanname dat VS Code een **tweede** `"decision": "block"`
honoreert wanneer `stop_hook_active=true` al gezet is. Er zijn twee scenario's:

| VS Code gedrag | Resultaat |
|---|---|
| (a) Honoreert herhaalde block | Counter werkt, model krijgt meerdere retries |
| (b) Negeert block bij stop_hook_active=true | Counter is dode code |

Er is **geen documentatie** die scenario (a) bevestigt.

**Vereiste handmatige test** voordat implementatie zinvol is:
1. Hardcode `return {"decision": "block", "reason": "test"}` (negeer stop_hook_active)
2. Trigger een stop in VS Code
3. Observeer: stuurt VS Code een tweede correction prompt, of sluit het de chat?

#### Probleem B: State management complexiteit

De counter moet gepersisteerd worden (hook draait als subprocess zonder geheugen):
- Waar? Apart bestand of in bestaand state file?
- Reset timing: bij elke UserPromptSubmit? Bij SessionStart? Stale counter-risico
- Race conditions: meerdere hooks als subprocessen (theoretisch)
- Testbaarheid: unit tests moeten counter-state mocken

**Prioriteit**: **BLOKKEER tot handmatige VS Code test** — investeer pas na bewijs
dat scenario (a) werkt.

## Eindoordeel

| # | Strategie | Verdict | Prioriteit |
|---|---|---|---|
| 1 | Front-loading via UserPromptSubmit | **PASS** | Eerst implementeren |
| 2 | Reason text optimalisatie | **PASS** | Tweede |
| 3 | Retry counter | **CONCERN** | Geblokkeerd tot handmatige test |

Combinatie 1 + 2 geeft twee verdedigingslinies (preventief + correctief) zonder
afhankelijkheid van ongedocumenteerd gedrag. Strategie 3 is pas zinvol na empirisch
bewijs dat VS Code herhaalde blocks honoreert.

## Status tests

- 101 tests passing (3.42s)
- Alle F1 (dead config), F2 (PYTHONPATH), F3 (stale editable install) fixes verified
- Stop hook vuurt correct (`BLOCK stop` in orchestration.log)
- Model compliance is het resterende open punt

## Volgende stap

@imp implementeert strategie 1 (front-loading in `detect_sub_role.py`) en
strategie 2 (reason text optimalisatie in `stop_handover_guard.py`).
Strategie 3 wacht op handmatige VS Code test van herhaalde block-honorering.
