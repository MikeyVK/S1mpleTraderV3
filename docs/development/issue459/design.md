<!-- docs\development\issue459\design.md -->
<!-- template=design version=5827e841 created=2026-08-22T08:08Z updated= -->
# Structured Quality-Gate Findings

**Status:** APPROVED  
**Version:** 1.0  
**Last Updated:** 2026-08-22

---

## Purpose

Define the public data contract and declarative presentation path for actionable quality-gate findings without parsing presentation prose.

## Scope

**In Scope:**
A frozen serializable GateFindingDTO; additive GateResultDTO.findings; structural mapping of existing QAManager issue records; a declarative nested run_quality_gates projection; existing startup alignment validation; and durable public-boundary tests.

**Out of Scope:**
Changes to QAManager or ViolationParser normalization; prose parsing; new limit mechanisms; sorting or deduplication; cleanup of unused QA formatting helpers; broader presentation abstractions; and Documentation-phase reference edits.

## Prerequisites

Read these first:
1. Approved Research strategy in research.md
2. Existing nested collection support and UTF-8 byte limiter delivered by issue 456
3. Existing QAManager issue dictionaries and ViolationParser normalization
---

## 1. Context & Requirements

### 1.1. Problem Statement

QAManager already produces ordered structured issue dictionaries, but RunQualityGatesTool drops that structure when mapping manager results into GateResultDTO. The public output therefore exposes actionable diagnostics only through opaque gate-level details text, preventing the generic collection presenter from rendering bounded findings while the cached DTO remains complete.

### 1.2. Requirements

**Functional:**
- [ ] RunQualityGatesOutput must expose every manager-provided issue as an ordered GateFindingDTO nested under its GateResultDTO.
- [ ] GateFindingDTO must preserve gate identity, required message, optional file/location/code/severity fields, fixable state, and optional diagnostic details.
- [ ] RunQualityGatesTool may only map already structured fields; it must not parse prose or invent fallback diagnostic content.
- [ ] The run_quality_gates presentation template must render findings as a child collection beneath each gate by using only generic presenter mechanisms.
- [ ] The existing tool max_items value must bound inline findings per gate; the existing 8000-byte final limiter remains the total response bound.
- [ ] All structured findings and optional details must remain in the cached DTO even when inline output omits items or reaches the byte ceiling.
- [ ] Message-only operational failures must use the same finding contract with absent optional location and code fields.
- [ ] Gate results with no findings must retain their existing observable text behavior apart from the additive structured empty collection.

**Non-Functional:**
- [ ] Preserve gate order and manager issue order exactly; do not sort or deduplicate.
- [ ] Keep presentation formatting in presentation.yaml and generic presenter code, never in QAManager, RunQualityGatesTool, or DTO methods.
- [ ] Use frozen Pydantic DTOs with forbidden extra fields and serializable defaults consistent with the existing tool-output contract.
- [ ] Fail fast during server startup when configured collection paths or placeholders do not match the DTO graph.
- [ ] Test production behavior through RunQualityGatesTool.execute and TextPresenter.present_text rather than private helpers.
- [ ] Reuse the existing generic renderer and limiter without speculative abstractions.

### 1.3. Constraints

- The approved Research strategy is binding: QAManager and ViolationParser remain normalization owners.
- Existing output fields, inputs, verbose details behavior, cache URI, and failure envelopes remain compatible.
- GateResultDTO.details remains available and cache-only; findings is additive.
- The current collection schema applies tool-level max_items at every nested collection level.
- Documentation updates are owned by the later Documentation phase.
---

## 2. Design Options

### 2.1. Option A: Nested additive finding DTO

Add GateFindingDTO and GateResultDTO.findings, structurally map QAManager issue records in the tool, and render them as a declarative child collection.

**Pros:**
- ✅ Preserves gate grouping and ordered structured evidence
- ✅ Reuses the generic presenter, startup validator, cache path, and existing bounds
- ✅ Keeps normalization, transport, and presentation ownership separated
- ✅ Provides an additive compatibility path

**Cons:**
- ❌ Adds one public DTO and one nested collection to cached output
- ❌ Requires explicit mapping from manager dictionary keys to public DTO field names

### 2.2. Option B: Flat top-level findings

Expose every finding directly on RunQualityGatesOutput and repeat gate identity on each item.

**Pros:**
- ✅ Makes one top-level collection easy to render

**Cons:**
- ❌ Duplicates gate grouping already present in manager results
- ❌ Creates two authorities for grouping and ordering
- ❌ Weakens the natural nested presentation structure

### 2.3. Option C: Manager-wide Pydantic graph

Replace manager result dictionaries with DTOs throughout the QA pipeline.

**Pros:**
- ✅ Strengthens typing inside the manager boundary

**Cons:**
- ❌ Expands the blast radius beyond the presentation defect
- ❌ Couples internal execution contracts to a public tool DTO
- ❌ Provides no necessary benefit for the approved outcome

### 2.4. Option D: Parse details in the presenter

Retain the current DTO and derive findings from gate-level prose during presentation.

**Pros:**
- ✅ Avoids a public DTO change

**Cons:**
- ❌ Violates the presentation boundary
- ❌ Creates format-dependent behavior
- ❌ Cannot provide reliable structured cache evidence
- ❌ Duplicates normalization already performed upstream

### 2.5. Option E: Dedicated child and global limits

Add separate per-child and total finding-count controls.

**Pros:**
- ✅ Offers more tuning dimensions

**Cons:**
- ❌ Duplicates protection from max_items and the byte ceiling
- ❌ Adds configuration complexity without an approved use case
---

## 3. Chosen Design

**Decision:** Choose the nested additive finding DTO: map it structurally in RunQualityGatesTool and project it through the existing generic collection presenter.

**Rationale:** This repairs the precise information-loss seam while preserving ownership. QAManager and ViolationParser normalize execution output; the tool adapts already structured records into the public DTO graph; presentation.yaml owns concise inline text; and the cache retains complete evidence. It is the smallest design satisfying bounded actionable output, startup-validatable configuration, compatibility, and the architecture principles.

### 3.1. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Public DTO shape | GateFindingDTO is frozen with extra fields forbidden and defines gate: str, message: str, file: str | None, line: int | None, column: int | None, code: str | None, severity: str | None, fixable: bool = False, and details: str | None. |
| Additive gate contract | GateResultDTO gains findings: list[GateFindingDTO] with an empty default factory; every existing field remains unchanged. |
| Mapping contract | Map message, file, line, col to column, rule to code, severity, fixable, and details. The enclosing gate name supplies gate. Missing optional values become None; missing required message fails fast. |
| Ownership | QAManager and ViolationParser remain normalization owners. The tool performs structural adaptation only; neither it nor the presenter parses diagnostic prose. |
| Declarative projection | presentation.yaml adds findings as a child of gates with optional location/code placeholders, message, severity, and fixable state. SafeNoneFormatter handles absent optional values uniformly. |
| Bounds | Existing max_items applies per gate to nested findings; the 8000 UTF-8 byte ceiling bounds the complete inline response. No additional limit configuration is introduced. |
| Ordering | Preserve gate and finding iteration order exactly from manager output; add no sorting or deduplication. |
| Cache authority | Cache the complete RunQualityGatesOutput, including every finding and optional details, before presentation. Inline omission never mutates evidence. |
| Failure semantics | Message-only operational failures are valid findings with absent optional fields. Top-level execution failures retain existing generic failure-envelope behavior. |
| Startup validation | The existing alignment validator traverses GateResultDTO.findings and validates child placeholders against GateFindingDTO during startup; no new validator is needed. |
| Test design | Adapt public-boundary tests for full and message-only mapping, ordering, empty compatibility, nested omission, cache completeness, raw-details exclusion inline, failure envelopes, and real-config startup alignment. Avoid private-helper and exact prose snapshots. |

## 4. Interface Contracts

### 4.1. Public finding DTO

The public transport contract is additive and belongs in the existing tool-output schema module:

```python
class GateFindingDTO(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    gate: str
    message: str
    file: str | None = None
    line: int | None = None
    column: int | None = None
    code: str | None = None
    severity: str | None = None
    fixable: bool = False
    details: str | None = None
```

`gate` and `message` are required because every cached finding must remain
self-identifying and actionable outside its inline nesting context. All source-location
and classification fields are optional because operational failures such as a missing
binary or timeout legitimately have no file, line, column, or rule.

`details` carries diagnostic evidence that does not belong in the concise inline
projection. It does not replace the existing gate-level `details` field.

### 4.2. Additive gate-result contract

```python
class GateResultDTO(BaseModel):
    # Existing fields remain unchanged.
    findings: list[GateFindingDTO] = Field(default_factory=list)
```

The empty default preserves construction by existing consumers. Serialization adds an
empty `findings` array for gates without issues; no existing field is removed, renamed,
or repurposed.

### 4.3. Structural adapter contract

`RunQualityGatesTool.execute(...)` maps each ordered manager issue record as follows:

| Manager key | Public field | Rule |
|---|---|---|
| enclosing gate name | `gate` | Required; copy without transformation |
| `message` | `message` | Required; absence is an invalid internal result and fails fast |
| `file` | `file` | Optional; absent or empty becomes `None` |
| `line` | `line` | Optional integer |
| `col` | `column` | Optional integer; public naming is normalized at the tool boundary |
| `rule` | `code` | Optional diagnostic code |
| `severity` | `severity` | Optional; preserve source value |
| `fixable` | `fixable` | Default `False` when absent |
| `details` | `details` | Optional cache evidence |

The adapter must not inspect `details`, split messages, infer locations, classify
severity, or synthesize user-facing fallback text. Those operations would transfer
normalization or presentation ownership into the tool.

### 4.4. Presentation contract

The existing `run_quality_gates.collections[gates]` declaration gains a
`children` entry for `findings`. The child item template references only public
`GateFindingDTO` fields and uses the generic formatter for absent values. The intended
projection contains location, code, message, severity, and fixability while keeping
`details` cache-only.

The existing configuration contract supplies both bounds:

- `run_quality_gates.max_items` limits rendered gates and, through current generic
  nesting semantics, rendered findings per gate.
- The global 8,000 UTF-8 byte limiter bounds the final inline tool response.

The existing startup alignment validator must resolve the path
`RunQualityGatesOutput.gates[].findings[]` and validate every child-template
placeholder against `GateFindingDTO`. A mismatch is a startup `ConfigError`, not a
runtime omission.

---

## 5. Data and Control Flow

1. A configured quality gate executes through `QAManager`.
2. `ViolationParser` and `QAManager` normalize diagnostics and operational failures
   into ordered issue dictionaries.
3. `RunQualityGatesTool` maps gate summaries and issue dictionaries into
   `RunQualityGatesOutput -> GateResultDTO -> GateFindingDTO`.
4. The complete DTO graph is cached as the authoritative MCP Resource.
5. `TextPresenter` renders gate results and nested findings using
   `presentation.yaml`.
6. Collection omission notices and the final byte limiter constrain only inline text;
   they never alter the cached DTO.

```text
gate process output
      |
      v
ViolationParser / QAManager  -- normalization authority
      |
      v
ordered gate + issue records
      |
      v
RunQualityGatesTool          -- structural adapter only
      |
      v
RunQualityGatesOutput
      |\
      | \--> MCP Resource cache (complete)
      v
TextPresenter + presentation.yaml
      |
      v
bounded inline summary
```

No reverse dependency from presentation into QA execution is introduced.

---

## 6. Failure and Compatibility Behavior

| Condition | Required behavior |
|---|---|
| Parsed code violation | Emit a fully populated finding for every available source field |
| Operational failure with message only | Emit a finding with required gate/message and `None` optional fields |
| Issue record lacks `message` | Fail fast while constructing the public DTO; do not invent text |
| Gate has no issues | Emit `findings=[]`; existing gate summary remains renderable |
| More than `max_items` findings | Render the configured prefix plus generic omission notice; cache all findings |
| Inline response exceeds 8,000 bytes | Apply the existing UTF-8-safe final truncation; cache remains complete |
| Top-level tool failure envelope | Preserve existing generic failure presentation and collection suppression |
| Verbose execution | Preserve raw gate details in the cache; do not inline raw details through the finding template |
| Invalid configured finding field | Reject configuration during startup with path/field context |

Compatibility is additive at the DTO boundary and unchanged at the tool-input, resource
URI, gate summary, verbose-details, and failure-envelope boundaries.

---

## 7. Test Design

Tests are durable behavior evidence, not textual snapshots.

### 7.1. Tool-boundary mapping

Adapt the existing `RunQualityGatesTool.execute` tests to prove:

- a representative fully populated manager issue maps every public field correctly;
- a message-only operational issue maps optional fields to `None`;
- gate order and finding order are retained;
- gates without issues receive an empty collection;
- existing gate-level `details` remains available;
- absence of required `message` fails rather than yielding fabricated content.

### 7.2. Presentation and cache behavior

Use the public `TextPresenter.present_text` path with the real
`run_quality_gates` presentation config to prove:

- findings render below their owning gate through generic nested collections;
- more than ten findings produces the generic omission notice;
- omitted findings and finding details remain in `model_dump()`, representing the
  graph cached by the tool wrapper;
- raw diagnostic details are not present in normal inline output;
- a representative failure envelope remains safe and unchanged;
- a gate with no findings retains its existing summary presentation.

### 7.3. Startup alignment

Reuse the real-config alignment test to prove that the nested collection field and every
configured placeholder resolve against the DTO graph. No test should duplicate the
complete template wording.

### 7.4. Verification scope

Implementation cycles run only the focused tool-output, quality-tool, and presentation
configuration tests needed by the changed surface. Validation owns the complete
workspace test run and branch-wide quality gates.

---

## 8. Documentation Boundary

The later Documentation phase must update the active quality-tool and presentation
architecture references to describe the structured finding graph, bounded nested inline
projection, and complete cached evidence. Research, Design, and Planning remain
historical decision artifacts and must not be rewritten as active user documentation.

## Related Documentation
- **[research.md][related-1]**
- **[../issue456/design.md][related-2]**
- **[../../reference/presentation_architecture.md][related-3]**
- **[../../reference/tools/quality.md][related-4]**

<!-- Link definitions -->

[related-1]: research.md
[related-2]: ../issue456/design.md
[related-3]: ../../reference/presentation_architecture.md
[related-4]: ../../reference/tools/quality.md

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-08-22 | Agent | Initial draft |