<!-- docs\development\issue263\research_yaml_first_handover_block.md -->
<!-- template=research version=8b7bb3ab created=2026-03-24T15:43Z updated= -->
# YAML-First Handover Block Design

**Status:** COMPLETE  
**Version:** 1.0  
**Last Updated:** 2026-03-24

---

## Purpose

Ontwerp een YAML-schema dat developers volledige controle geeft over de handover-blok inhoud per sub-rol, zonder Python-logica te hoeven wijzigen.

## Scope

**In Scope:**
`build_crosschat_block_instruction` hardcoding analyse, schema-opties A/B/C, backward compatibility strategie, impact-punten in de codebase.

**Out of Scope:**
Implementatie (TDD cycles), test-aanpassingen, CI/CD configuratie.

## Prerequisites

1. `build_crosschat_block_instruction` gelokaliseerd in `detect_sub_role.py` (lijnen 101–114)
2. `SubRoleSpec` TypedDict bekeken (`interfaces.py`)
3. YAML default (`_default_requirements.yaml`) + project-override (`.copilot/sub-role-requirements.yaml`) structuur begrepen
4. Alle call-sites en test-bestanden ge-grepped

---

## Problem Statement

`build_crosschat_block_instruction` in `detect_sub_role.py` bevat hardcoded template-logica:
de heading-tekst, code-fence type, sections-label en numbered-list format liggen vast in Python.
Developers kunnen de weergave van het handover-blok niet aanpassen zonder Python-code te wijzigen.
Doel: bepalen welk YAML-schema volledige controle geeft met minimale backward-compatibility impact.

## Research Goals

1. Inventariseer welke delen hardcoded zijn vs. uit YAML komen.
2. Breng technische constraints in kaart (block_prefix op regel 1, code-fence vereiste, default/override-patroon).
3. Analyseer drie schema-opties: A = verbatim `block_template` string, B = Jinja2 template, C = `lines:` lijst.
4. Bepaal de backward-compatibility strategie.
5. Maak een complete impact-lijst van alle bestanden die moeten veranderen.
6. Identificeer edge-cases.

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

**Hardcoded elementen:**

| Element | Waarde | Reden om te variëren |
|---------|--------|----------------------|
| Heading-formaat | `[{sub_role}] End your response with this block:\n\n` | Andere tonen / talen |
| Code-fence type | `\`\`\`text` | Sommige tools herkennen geen `text` |
| Sections-label | `Required sections:\n` | Herformuleren of weglaten |
| Numbered-list indent | `  {i+1}. {m}` (2 spaties + punt) | Bullet `- ` of ander formaat |
| Fence-close | `\`\`\`` + 2 newlines | Compactheid |

**YAML-sourced elementen (reeds flexibel):**

| Veld | TypedDict sleutel | Gebruik |
|------|-------------------|---------|
| Eerste regel van blok | `block_prefix` | Target-sub-role naam |
| Tweede regel van blok | `guide_line` | Taakomschrijving |
| Sections namen | `markers` | Vereiste secties (namen) |
| (optioneel) | `block_prefix_hint` | Tooltip tekst buiten het blok |
| (optioneel) | `marker_verb` | Werkwoord in de instructie |

---

### G2 — Technische constraints

1. **`block_prefix` op regel 1 van de code-fence body.** De `stop_handover_guard.py` en `notify_compaction.py` injecteren de instructie via `build_crosschat_block_instruction`; het blok is instructietekst naar de *agent*, niet een regex die op de output van de agent matcht. De volgorde (block_prefix op regel 1) is een UX-conventie, niet een hard-gecodeerde detectie. Vrijheid om dit in `block_template` te herschikken is dus aanwezig.

2. **Code-fence is functioneel vereist.** Het output die de agent schrijft moet kopieerbaar zijn als cross-chat trigger. De code-fence zorgt dat de inhoud niet als Markdown wordt geparsed en integraal bewaard blijft. Het fence-type (`text`) is *niet* detectie-kritisch; het kan worden gewijzigd.

3. **Package-default + project-override patroon.** `SubRoleRequirementsLoader.from_copilot_dir()` laadt óf `.copilot/sub-role-requirements.yaml` (project) óf `_default_requirements.yaml` (package); geen merge. Dit betekent dat `block_template` in het project-override YAML aanwezig moet zijn, dan wel als fallback-logica in Python.

4. **Callers (3 injection-punten) krijgen de string terug, niet de spec.** `build_crosschat_block_instruction` retourneert een `str`. De callers doen hier altijd iets mee:
   - S1 (`detect_sub_role.py:138`): rechtstreeks in `"systemMessage"`
   - S2 (`notify_compaction.py:65`): `base += "\n\n" + result`
   - S3 (`stop_handover_guard.py:118`): `"Write NOW.\n\n" + result`

   Het prefix `"Write NOW.\n\n"` en `"\n\n"` worden door de *caller* toegevoegd, niet door de functie. Een `block_template` in YAML hoeft die caller-prefixes dus niet te bevatten.

---

### G3 — Schema-opties vergelijking

#### Optie A — Verbatim `block_template` string (str.format-achtig)

```yaml
implementer:
  block_template: |
    [{sub_role}] End your response with this block:

    ```text
    {block_prefix}
    {guide_line}
    ```

    Required sections:
      1. Scope
      2. Files Changed
      3. Proof
      4. Ready-for-QA
```

Python-logica:

```python
if tpl := spec.get("block_template", "").strip():
    return tpl.format(sub_role=sub_role, **spec)
# else: bestaand pad
```

| | Optie A |
|-|---------|
| **Flexibiliteit** | Maximaal — volledige controle |
| **DRY** | Slecht — `markers` namen staan dubbel (ook in `markers:` lijst) |
| **YAML-complexiteit** | Laag — `\|` literal block scalar is vertrouwd |
| **Validatie** | Lastig — onbekende format-keys geven `KeyError` |
| **Backward compat** | Prima — opt-in, absent = oud gedrag |

**Aanbeveling:** Geschikt als er geen `markers`-synchronisatie nodig is. Risico op drifting als `markers` apart wordt bijgehouden.

---

#### Optie B — Jinja2 template

```yaml
implementer:
  block_template: |
    [{{ sub_role }}] End your response with this block:

    ```text
    {{ block_prefix }}
    {{ guide_line }}
    ```

    Required sections:
    {% for m in markers %}  {{ loop.index }}. {{ m }}
    {% endfor %}
```

| | Optie B |
|-|---------|
| **Flexibiliteit** | Maximaal + DRY via `{{ markers }}` loop |
| **DRY** | Goed — `markers` worden hergebruikt |
| **YAML-complexiteit** | Matig — backtick-escaping in YAML is lastiger (`{{ }}` safe, maar ` ``` ` moet in een literal block) |
| **Validatie** | Beter — Jinja2 kent `undefined` variabelen en `StrictUndefined` |
| **Afhankelijkheid** | Jinja2 al aanwezig in project (scaffold templates) |
| **Backward compat** | Prima — opt-in |

**Aanbeveling:** Krachtigst, maar overengineered voor dit gebruik. Jinja2-kennis vereist van YAML-auteurs.

---

#### Optie C — Gestructureerde `block_lines:` lijst

```yaml
implementer:
  block_lines:
    heading: "[{sub_role}] End your response with this block:"
    fence_type: "text"
    sections_label: "Required sections:"
    list_indent: "  "
```

| | Optie C |
|-|---------|
| **Flexibiliteit** | Beperkt — alleen bekende velden instelbaar |
| **DRY** | Prima — `markers` worden hergebruikt |
| **YAML-complexiteit** | Laag — standaard mapping |
| **Validatie** | Sterk — elk veld apart te valideren |
| **Backward compat** | Prima — opt-in |

**Aanbeveling:** Laagste inspanning voor de meest voorkomende use-cases (heading/label aanpassen). Maar structureel niet flexibeler dan de huidige situatie.

---

#### Aanbevolen keuze: **Optie A** (verbatim `block_template` + `str.format`)

Redenen:
- Maximale flexibiliteit zonder extra dependency.
- Eenvoudige implementatie (3–5 regels Python).
- Opt-in: absent = volledig backward compatible.
- `markers` duplicatie is acceptabel: de `block_template` is de presentatie-laag; `markers`  
  blijft de machine-leesbare structuur voor eventuele validatie door de Stop-hook.
- Als DRY later cruciaal blijkt, is migratie naar Optie B incrementeel.

---

### G4 — Backward-compatibility strategie

**Aanbeveling: opt-in `block_template` veld in `SubRoleSpec`**

```python
class SubRoleSpec(TypedDict):
    # Bestaand:
    requires_crosschat_block: bool
    heading: str
    block_prefix: str
    guide_line: str
    markers: list[str]
    block_prefix_hint: NotRequired[str]
    marker_verb: NotRequired[str]
    # Nieuw:
    block_template: NotRequired[str]   # ← YAML override voor build_crosschat_block_instruction
```

Gedrag in `build_crosschat_block_instruction`:

```python
def build_crosschat_block_instruction(sub_role: str, spec: SubRoleSpec) -> str:
    tpl = spec.get("block_template", "")
    if tpl and tpl.strip():
        return tpl.format(sub_role=sub_role, **spec)          # NIEUW pad
    # BESTAAND pad (ongewijzigd):
    markers = "\n".join(f"  {i + 1}. {m}" for i, m in enumerate(spec["markers"]))
    return (
        f"[{sub_role}] End your response with this block:\n\n"
        "```text\n"
        f"{spec['block_prefix'].strip()}\n"
        f"{spec['guide_line'].strip()}\n"
        "```\n\n"
        f"Required sections:\n{markers}"
    )
```

Oud gedrag (geen `block_template` in YAML) is identiek aan de huidige versie. Geen breaking change.

---

### G5 — Impact-punten (volledige lijst)

**Bronbestanden (vereist):**

| Bestand | Wijziging |
|---------|-----------|
| `src/copilot_orchestration/contracts/interfaces.py` | `block_template: NotRequired[str]` toevoegen aan `SubRoleSpec` |
| `src/copilot_orchestration/config/requirements_loader.py` | `block_template: str = ""` in `_SubRoleSchema`; doorgeven in `get_requirement()` |
| `src/copilot_orchestration/hooks/detect_sub_role.py` | `build_crosschat_block_instruction` uitbreiden met `block_template`-pad |

**YAML-bestanden (optioneel):**

| Bestand | Wijziging |
|---------|-----------|
| `src/copilot_orchestration/config/_default_requirements.yaml` | Geen wijziging (backward compat) |
| `.copilot/sub-role-requirements.yaml` | `block_template:` toevoegen aan sub-roles wanneer gewenst |

**Testbestanden (vereist):**

| Bestand | Scope |
|---------|-------|
| `tests/copilot_orchestration/unit/hooks/test_detect_sub_role.py` | Nieuw test-pad: `block_template` aanwezig → template gebruikt; absent → oud gedrag |
| `tests/copilot_orchestration/unit/config/test_requirements_loader.py` | `block_template` veld geladen + doorgegeven |
| `tests/copilot_orchestration/unit/contracts/test_interfaces.py` | `block_template` NotRequired constraint |
| `tests/copilot_orchestration/integration/test_optional_field_chain.py` | chain met `block_template` |
| `tests/copilot_orchestration/unit/hooks/test_notify_compaction.py` | indirecte impact indien block-text geassert wordt |

**Callers (geen codewijziging vereist):**

| Bestand | Reden geen wijziging |
|---------|----------------------|
| `src/copilot_orchestration/hooks/notify_compaction.py` | Roept `build_crosschat_block_instruction` aan; interface ongewijzigd |
| `src/copilot_orchestration/hooks/stop_handover_guard.py` | Idem |

---

### G6 — Edge-cases

| Edge-case | Risico | Mitigatie |
|-----------|--------|-----------|
| `block_template: ""` (leeg) | Fallback werkt niet als `if tpl` gebruikt wordt | `if tpl and tpl.strip():` — lege string → oud pad |
| `block_template: null` YAML null | Pydantic valideert `str = ""` → wordt `None` als Optional | In `_SubRoleSchema` als `block_template: str = ""` definiëren (geen `Optional`) |
| Windows `\r\n` in verbatim block | `format()` geeft `\r\n` door naar instructie-tekst | `.replace("\r\n", "\n")` na `.format()` |
| YAML `\|` vs `\|-` | `\|` behoudt trailing newline; `\|-` niet | In documentatie/schema-help: gebruik `\|-` voor `block_template` |
| `{sub_role}` of `{block_prefix}` ontbreekt in template | `KeyError` | try/except `KeyError` → log waarschuwing + fallback naar oud pad |
| `markers` lijst leeg | Template met `{markers}` geeft leeg resultaat | Geen crash; wel UX-probleem → valideren dat `markers` niet leeg is wanneer `block_template` `{markers}` gebruikt |
| Backticks in `block_template` YAML | Geen escaping nodig in YAML literal block scalar | Documenteer: gebruik altijd `\|` of `\|-` voor `block_template` in YAML |

---

## Open Questions

1. Moet `block_template` ook de `markers`-namen embedden (drifting-risico), of introduceren we `{markers_list}` als auto-gegenereerde placeholder die Python aanvult?
2. Hoe strikt is de validatie: accepteren we onbekende `{xxx}` placeholders stilzwijgend, of loggen we een waarschuwing?
3. Is een `validate_template` / `health_check` op de YAML-laag wenselijk om `block_template` format-fouten vroeg te signaleren?

## Related Documentation
- **[src/copilot_orchestration/config/_default_requirements.yaml](src/copilot_orchestration/config/_default_requirements.yaml)**
- **[.copilot/sub-role-requirements.yaml](.copilot/sub-role-requirements.yaml)**
- **[src/copilot_orchestration/contracts/interfaces.py](src/copilot_orchestration/contracts/interfaces.py)**
- **[src/copilot_orchestration/hooks/detect_sub_role.py](src/copilot_orchestration/hooks/detect_sub_role.py)**

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-03-24 | Agent | Initial research — 6 goals volledig beantwoord |
