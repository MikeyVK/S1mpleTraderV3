<!-- docs\development\issue263\research_yaml_first_handover_block.md -->
<!-- template=research version=8b7bb3ab created=2026-03-24T15:43Z updated=2026-03-24 -->
# YAML-First Handover Block Design

**Status:** COMPLETE  
**Version:** 3.1  
**Last Updated:** 2026-03-24

---

## Purpose

Ontwerp een YAML-schema dat developers volledige controle geeft over de handover-blok inhoud per sub-rol, zonder Python-logica te hoeven wijzigen.

## Scope

**In Scope:**
`build_crosschat_block_instruction` hardcoding analyse, schema-opties A/B/C, backward compatibility strategie, impact-punten in de codebase, per-sub-rol differentiatie via placeholders.

**Out of Scope:**
Implementatie (TDD cycles), CI/CD configuratie.

## Prerequisites

1. `build_crosschat_block_instruction` gelokaliseerd in `detect_sub_role.py` (lijnen 101–114)
2. `SubRoleSpec` TypedDict bekeken (`interfaces.py`)
3. YAML default (`_default_requirements.yaml`) + project-override (`.copilot/sub-role-requirements.yaml`) structuur begrepen
4. Alle call-sites en test-bestanden ge-grepped
5. Veldgebruik van `block_prefix`, `guide_line`, `block_prefix_hint`, `marker_verb` volledig geanalyseerd

---

## Problem Statement

`build_crosschat_block_instruction` in `detect_sub_role.py` bevat hardcoded template-logica:
de heading-tekst, code-fence type, sections-label en numbered-list format liggen vast in Python.
Developers kunnen de weergave van het handover-blok niet aanpassen zonder Python-code te wijzigen.
Doel: bepalen welk YAML-schema volledige controle geeft — geïmplementeerd als flag-day (geen backward compat, package nog nooit gereleased).

## Research Goals

1. Inventariseer welke delen hardcoded zijn vs. uit YAML komen.
2. Breng technische constraints in kaart (block_prefix op regel 1, code-fence vereiste, default/override-patroon).
3. Analyseer drie schema-opties: A = verbatim `block_template` string, B = Jinja2 template, C = `lines:` lijst.
4. Bepaal flag-day veldopruiming (geen backward compat).
5. Maak een complete impact-lijst van alle bestanden die moeten veranderen.
6. Identificeer edge-cases.
7. Ontwerp placeholder-strategie voor per-sub-rol differentiatie.

---

## Findings

### G1 — Hardcoded vs. YAML-sourced

Huidige functie (`detect_sub_role.py` regels 101–114):

```python
def build_crosschat_block_instruction(sub_role: str, spec: SubRoleSpec) -> str:
    markers = "\n".join(f"  {i + 1}. {m}" for i, m in enumerate(spec["markers"]))
    return (
        f"[{sub_role}] End your response with this block:\n\n"  # HARDCODED (heading)
        "```text\n"                                              # HARDCODED (fence type)
        f"{spec['block_prefix'].strip()}\n"                     # YAML: block_prefix
        f"{spec['guide_line'].strip()}\n"                       # YAML: guide_line
        "```\n\n"                                               # HARDCODED (fence close)
        f"Required sections:\n{markers}"                        # HARDCODED (label + format)
    )
```

**Hardcoded elementen (worden door `block_template` overgenomen):**

| Element | Waarde | Reden om te variëren |
|---------|--------|----------------------|
| Heading-formaat | `[{sub_role}] End your response with this block:\n\n` | Andere tonen / talen |
| Code-fence type | ` ```text ` | Sommige tools herkennen geen `text` |
| Sections-label | `Required sections:\n` | Herformuleren of weglaten |
| Numbered-list buiten fence | `  {i+1}. {m}` (2 spaties + punt) | **Fundamenteel fout — zie G7** |

**Legacy YAML-velden (worden verwijderd — zie G4):**

| Veld | TypedDict sleutel | Verdict na analyse |
|------|-------------------|--------------------|
| Eerste regel van blok | `block_prefix` | Puur feedthrough → weg |
| Tweede regel van blok | `guide_line` | Puur feedthrough → weg |
| Tooltip tekst | `block_prefix_hint` | **Dood veld** — nooit geconsumeerd → weg |
| Werkwoord prefix | `marker_verb` | **Dood veld** — hardcoded Python overschreef → weg |

---

### G2 — Technische constraints

1. **Code-fence is functioneel vereist.** Het blok moet kopieerbaar zijn als cross-chat trigger. De code-fence voorkomt Markdown-parsing. Het fence-type (`text`) is niet detectie-kritisch; vrij te kiezen in `block_template`.

2. **Package-default + project-override patroon.** `SubRoleRequirementsLoader.from_copilot_dir()` laadt óf `.copilot/sub-role-requirements.yaml` (project) óf `_default_requirements.yaml` (package); geen merge. Beide bestanden moeten bij flag-day worden bijgewerkt.

3. **Callers (3 injection-punten) krijgen een `str` terug.** De callers voegen eigen prefixes toe:
   - S1 (`detect_sub_role.py:138`): rechtstreeks in `"systemMessage"`
   - S2 (`notify_compaction.py:65`): `base += "\n\n" + result`
   - S3 (`stop_handover_guard.py:118`): `"Write NOW.\n\n" + result`

   `block_template` hoeft deze caller-prefixes niet te bevatten.

4. **`requires_crosschat_block: false` sub-rollen.** Voor sub-rollen die geen blok produceren wordt `build_crosschat_block_instruction` nooit aangeroepen (gate in callers). `block_template: ""` in YAML.

5. **Eerste regel binnen de fence moet de doelrol bevatten.**
   Python kan niet valideren of het eerste woord binnen `block_template` overeenkomt
   met een geldige sub-rol van de ontvangende agent. Conventie (niet code):
   de YAML-auteur is verantwoordelijk voor correcte doelrol op regel 1 binnen de fence.
   De loader logt een `WARNING` als `block_template` van een sub-rol met
   `requires_crosschat_block: true` geen herkenbare sub-rol-naam als eerste woord bevat
   na de openende fence — dit is een best-effort check, geen harde blokkering.

---

### G3 — Schema-opties vergelijking

#### Optie A — Verbatim `block_template` string (str.format-achtig)

Python-logica (flag-day, geen fallback naar oud gedrag):

```python
def build_crosschat_block_instruction(sub_role: str, spec: SubRoleSpec) -> str:
    markers_list = "\n\n".join(f"## {m}" for m in spec["markers"])
    try:
        return spec["block_template"].replace("\r\n", "\n").format(
            sub_role=sub_role,
            markers_list=markers_list,
        )
    except KeyError as exc:
        logger.error("block_template placeholder %s niet gevonden voor sub_role=%r", exc, sub_role)
        raise ConfigError(f"Ongeldige block_template voor sub_role={sub_role!r}: {exc}") from exc
```

| | Optie A |
|-|---------|
| **Flexibiliteit** | Maximaal — volledige controle over elke regel |
| **DRY** | Goed — `markers` list apart; `{markers_list}` als bridge |
| **YAML-complexiteit** | Laag — `\|-` literal block scalar is vertrouwd |
| **Validatie** | Duidelijk — `KeyError → ConfigError`, vroeg falen |
| **Afhankelijkheden** | Geen extra packages |

#### Optie B — Jinja2 template

| | Optie B |
|-|---------|
| **Flexibiliteit** | Maximaal + loop-constructies |
| **DRY** | Beter — `{% for m in markers %}` loop |
| **Afhankelijkheid** | Jinja2 al aanwezig, maar overkill voor dit gebruik |
| **YAML-auteur** | Moet Jinja2-syntax kennen |

#### Optie C — Gestructureerde `block_lines:` mapping

| | Optie C |
|-|---------|
| **Flexibiliteit** | Beperkt — alleen bekende sleutels instelbaar |
| **DRY** | Prima |
| **Structureel voordeel** | Geen t.o.v. huidige situatie |

#### **Beslissing: Optie A** — verbatim `block_template` + `str.format` met twee placeholders

---

### G4 — Flag-day veldopruiming

**Geen backward compatibility.** De package is nog nooit gereleased.

**Velden die verdwijnen (verified dood of puur feedthrough):**

| Veld | Bewijs | Actie |
|------|--------|-------|
| `block_prefix` | Alleen geconsumeerd in `build_crosschat_block_instruction` L111 | **Verwijderen** |
| `guide_line` | Alleen geconsumeerd in `build_crosschat_block_instruction` L112 | **Verwijderen** |
| `block_prefix_hint` | Geladen en doorgegeven, maar nooit uitgelezen door enige hook | **Verwijderen** |
| `marker_verb` | Geladen en doorgegeven, maar Python negeerde het volledig | **Verwijderen** |

**Nieuwe `SubRoleSpec` (lean):**

```python
class SubRoleSpec(TypedDict):
    requires_crosschat_block: bool
    heading: str
    markers: list[str]      # machine-leesbare lijst; Python genereert {markers_list}
    block_template: str     # required; verbatim str.format template
```

**Nieuwe `_SubRoleSchema` Pydantic (in requirements_loader.py):**

```python
from pydantic import model_validator

class _SubRoleSchema(BaseModel):
    requires_crosschat_block: bool
    heading: str
    markers: list[str]
    block_template: str = ""    # leeg voor sub-rollen zonder crosschat-blok

    @model_validator(mode="after")
    def _validate_template_required(self) -> "_SubRoleSchema":
        if self.requires_crosschat_block and not self.block_template.strip():
            raise ValueError(
                "block_template mag niet leeg zijn wanneer requires_crosschat_block=True"
            )
        return self
```

**Validatie-mechanisme:** Pydantic gooit `ValidationError` (via `@model_validator`) wanneer
`requires_crosschat_block=True` en `block_template` leeg is. De `SubRoleRequirementsLoader`-constructor
laat deze `ValidationError` opborrelen — de caller ziet hem als een constructie-fout, equivalent aan
`FileNotFoundError`. Er is geen aparte `ConfigError` nodig op dit pad.

---

### G5 — Impact-punten (volledige lijst)

**Bronbestanden:**

| Bestand | Wijziging |
|---------|-----------|
| `src/copilot_orchestration/contracts/interfaces.py` | `SubRoleSpec`: verwijder `block_prefix`, `guide_line`, `block_prefix_hint`, `marker_verb`; voeg `block_template: str` toe |
| `src/copilot_orchestration/config/requirements_loader.py` | `_SubRoleSchema`: idem + `@model_validator(mode='after')` die `ValueError` gooit wanneer `requires_crosschat_block=True` en `block_template` leeg is (door Pydantic omgezet naar `ValidationError`); `get_requirement()` aangepast |
| `src/copilot_orchestration/hooks/detect_sub_role.py` | `build_crosschat_block_instruction`: vervang volledige body door `str.format` met `{sub_role}` en `{markers_list}`; `ConfigError` bij `KeyError` |

**YAML-bestanden:**

| Bestand | Wijziging |
|---------|-----------|
| `src/copilot_orchestration/config/_default_requirements.yaml` | Verwijder `block_prefix`, `guide_line`, `block_prefix_hint`, `marker_verb` uit alle sub-rollen; voeg `block_template:` toe |
| `.copilot/sub-role-requirements.yaml` | Idem; 4 sub-rollen met `requires_crosschat_block: true` krijgen ingevulde `block_template` |

**Testbestanden:**

| Bestand | Scope |
|---------|-------|
| `tests/copilot_orchestration/unit/hooks/test_detect_sub_role.py` | Herschrijven: `block_template` aanwezig → output correct; `{sub_role}` en `{markers_list}` gevuld; onbekende placeholder → `ConfigError` |
| `tests/copilot_orchestration/unit/config/test_requirements_loader.py` | `block_template` geladen; `ValidationError` bij `requires_crosschat_block=True` + leeg |
| `tests/copilot_orchestration/unit/contracts/test_interfaces.py` | Verwijderde velden niet meer aanwezig; `block_template` aanwezig |
| `tests/copilot_orchestration/integration/test_optional_field_chain.py` | Chain werkt met nieuwe `SubRoleSpec`; `block_prefix_hint` en `marker_verb` tests verwijderen |
| `tests/copilot_orchestration/unit/hooks/test_notify_compaction.py` | Output-assertions bijwerken als ze `block_prefix` / `guide_line` letterlijk asserteren |

**Callers (geen codewijziging vereist):**

| Bestand | Reden |
|---------|-------|
| `src/copilot_orchestration/hooks/notify_compaction.py` | Interface `build_crosschat_block_instruction(sub_role, spec) → str` ongewijzigd |
| `src/copilot_orchestration/hooks/stop_handover_guard.py` | Idem |

---

### G6 — Edge-cases

| Edge-case | Risico | Mitigatie |
|-----------|--------|-----------|
| `block_template: ""` bij `requires_crosschat_block: true` | Hook produceert lege string | `@model_validator` gooit `ValidationError` bij laden |
| `block_template: null` in YAML | Pydantic krijgt `None` | Gebruik `str` (niet `Optional[str]`) in `_SubRoleSchema` |
| Windows `\r\n` in verbatim block | `\r\n` in rendered instructie | `.replace("\r\n", "\n")` vóór `.format()` |
| YAML `\|` (trailing newline) vs `\|-` (geen trailing) | Extra newline aan einde van instructie | Conventie: altijd `\|-` voor `block_template` in YAML |
| Onbekende `{placeholder}` in template | `KeyError` | `try/except KeyError → ConfigError` (hard falen, geen silent fallback) |
| Accolade in literal tekst, bijv. `{scope}` bedoeld als Markdown | `KeyError` of ongewilde substitutie | Verdubbelen: `{{scope}}` in YAML template |
| `markers` lijst leeg bij `requires_crosschat_block: true` | `{markers_list}` → lege string | Loader valideert: `markers` niet leeg wanneer `requires_crosschat_block: true` |

---

### G7 — Per-sub-rol differentiatie via `block_template`

#### Kritische UX-constraint: alles binnen de fence

Het volledige cross-chat blok — trigger én ingevulde secties — moet binnen één code-fence staan.
De gebruiker kopieert het blok integraal naar de volgende agent-chat.
Secties die buiten de fence staan gaan bij copy-paste verloren.

**Fout: secties buiten de fence (huidige situatie)**

Instructie aan agent:

```
[implementer] End your response with this block:

--BEGIN TEXT FENCE--
verifier
Review the latest implementation work on this branch.
--EINDE TEXT FENCE--

Required sections:
  1. Scope
  2. Files Changed
```

Agent-output:

```
--BEGIN TEXT FENCE--
verifier
Review the latest implementation work on this branch.
--EINDE TEXT FENCE--

**Scope**           <- BUITEN fence, gaat verloren bij copy-paste
**Files Changed**   <- idem
```

**Correct: alles binnen de fence (nieuw ontwerp)**

Instructie aan agent:

```
[implementer] End your response with this block:

--BEGIN TEXT FENCE--
verifier
Review the latest implementation work on this branch.

## Scope

## Files Changed

## Proof

## Ready-for-QA
--EINDE TEXT FENCE--
```

Agent-output:

```
--BEGIN TEXT FENCE--
verifier
Review the latest implementation work on this branch.

## Scope
YAML-first block_template support geïmplementeerd.

## Files Changed
- detect_sub_role.py
- interfaces.py

## Proof
139 tests pass.

## Ready-for-QA
Ja.
--EINDE TEXT FENCE--
```

Alles in één blok — volledig copy-pasteable naar `@qa verifier`.

#### Placeholder-contract (exact twee, niet meer)

| Placeholder | Gegenereerd door Python | Waarde |
|-------------|------------------------|--------|
| `{sub_role}` | `sub_role` parameter van de functie | Naam van de actieve sub-rol, bijv. `implementer` |
| `{markers_list}` | `"\n\n".join(f"## {m}" for m in spec["markers"])` | `## Scope`, `## Files Changed`, etc. — elk als H2-header met lege regel ertussen, zodat de agent ze als aparte secties behandelt |

`{sub_role}` is een convenience: je kunt de naam ook hardcoderen, maar de placeholder voorkomt drift bij hernoeming van een sub-rol.

Elk ander `{xyz}` in de template geeft een `ConfigError` bij rendering — hard falen, geen silent fallback.

> **Let op: `{sub_role}` is de actieve sub-rol, niet de doelrol.**
> `{sub_role}` vult de naam in van de sub-rol die het blok produceert (bijv. `implementer`).
> Het eerste woord **binnen** de fence is de detectie-trigger voor de ontvangende agent
> (bijv. `verifier`) — dit moet hardcoded in de template staan, niet als `{sub_role}`.
> Gebruik `{sub_role}` alleen in de heading buiten de fence, zoals `[{sub_role}] End your response with this block:`.

#### Developer-invloed samengevat

- `markers:` lijst → bepaalt welke secties in het blok verschijnen (via `{markers_list}`)
- `block_template` → bepaalt volledige opmaak, toon, heading, fence-inhoud en positie van de secties
- Buiten die twee velden: geen Python-kennis nodig

#### Concreet voorbeeld — twee sub-rollen naast elkaar

```yaml
# imp/implementer -> trigger naar @qa verifier
implementer:
  requires_crosschat_block: true
  heading: "Implementation Hand-Over"
  markers:
    - Scope
    - Files Changed
    - Proof
    - Ready-for-QA
  block_template: |-
    [{sub_role}] End your response with this block:

    --BEGIN TEXT FENCE--
    verifier
    Review the latest implementation work on this branch.

    {markers_list}
    --EINDE TEXT FENCE--

# qa/verifier -> trigger terug naar @imp implementer
verifier:
  requires_crosschat_block: true
  heading: "Verification Review"
  markers:
    - Findings
    - Proof Verification
    - Verdict
  block_template: |-
    [{sub_role}] End your response with this block:

    --BEGIN TEXT FENCE--
    implementer
    QA findings must be resolved before this cycle is done.

    {markers_list}
    --EINDE TEXT FENCE--
```

Rendered instructie voor `imp/implementer`:

```
[implementer] End your response with this block:

--BEGIN TEXT FENCE--
verifier
Review the latest implementation work on this branch.

## Scope

## Files Changed

## Proof

## Ready-for-QA
--EINDE TEXT FENCE--
```

**Sub-rollen zonder blok (`requires_crosschat_block: false`):** `block_template: ""` — `build_crosschat_block_instruction` wordt nooit aangeroepen (gate in caller).

---

## Open Questions

~~1. Moet `block_template` ook de `markers`-namen embedden (drifting-risico), of introduceren we `{markers_list}` als auto-gegenereerde placeholder die Python aanvult?~~
**Besloten:** A2 — `markers` apart houden, Python genereert `{markers_list}` als `## Header` regels binnen de fence.

~~2. Hoe strikt is de validatie: accepteren we onbekende `{xxx}` placeholders stilzwijgend, of loggen we een waarschuwing?~~
**Besloten:** Hard falen — `KeyError → ConfigError` met log.

~~3. Is een `validate_template` / `health_check` op de YAML-laag wenselijk om `block_template` format-fouten vroeg te signaleren?~~
**Besloten:** `@model_validator(mode='after')` in `_SubRoleSchema` gooit `ValidationError` bij opstart. Geen aparte health-check nodig.

~~4. Moet de list-format van `{markers_list}` configureerbaar zijn?~~
**Besloten:** Hardcoded als `## Header` regels binnen de fence. De agent-LLM maakt zich niets uit van opmaak; configuratie voegt geen waarde toe.

**Geen open vragen meer. Research volledig afgerond.**

## Related Documentation
- [src/copilot_orchestration/config/_default_requirements.yaml](src/copilot_orchestration/config/_default_requirements.yaml)
- [.copilot/sub-role-requirements.yaml](.copilot/sub-role-requirements.yaml)
- [src/copilot_orchestration/contracts/interfaces.py](src/copilot_orchestration/contracts/interfaces.py)
- [src/copilot_orchestration/hooks/detect_sub_role.py](src/copilot_orchestration/hooks/detect_sub_role.py)

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-03-24 | Agent | Initial research — 6 goals beantwoord, Optie A aanbevolen |
| 2.0 | 2026-03-24 | Agent | Flag-day besloten; dode velden verified; A2 + hard-fail besloten; G7 toegevoegd |
| 3.0 | 2026-03-24 | Agent | G7 herschreven: fence-UX-constraint, `{markers_list}` als `## Header` binnen fence, placeholder-contract (exact 2), alle open vragen gesloten |
| 3.1 | 2026-03-24 | Agent | QA annotaties A1/A2/A3: G2 constraint 5 (detection-conventie + WARNING), G4 `@model_validator` uitgewerkt + `ValidationError` mechanisme, G7 `{sub_role}` vs doelrol waarschuwing |
