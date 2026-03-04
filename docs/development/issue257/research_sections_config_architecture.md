<!-- docs\development\issue257\research_sections_config_architecture.md -->
<!-- template=research version=8b7bb3ab created=2026-03-04T09:28Z updated= -->
# sections.yaml architecture: workflow-aware document content contracts

**Status:** DRAFT  
**Version:** 1.0  
**Last Updated:** 2026-03-04

---

## Purpose

Establish the architectural blueprint for workflow-aware document content contracts before issue #257 enters design. The findings here determine which parts belong in #257 and which spawn new issues under epics #49 and #73.

## Scope

**In Scope:**
sections.yaml config schema; workflows.yaml phase_contracts extension; workphases.yaml content_contract gate type; PSE content_contract gate handler; ArtifactManager sections injection into template context; template iteration over sections list; issue boundary analysis for #257 / enforcement / template integration

**Out of Scope:**
content_rules validation beyond heading presence (min_words, required_subheadings — defined in architecture, not yet implemented); integration with CI/CD or external tooling; migration of existing documents to new section structure

## Prerequisites

Read these first:
1. Issue #257 research.md findings 1–10 (PSE SOLID violations, phase reordering, heading_present gate)
2. Epic #49 completed: workflows.yaml, artifacts.yaml, workphases.yaml, quality.yaml all operational as config-driven SSOT files
3. Epic #73 open: Template Governance — owner of template/scaffold architecture decisions
4. Understanding of ArtifactManager V2 pipeline: scaffold_artifact → ResearchContext → research.md.jinja2 tier chain
---

## Problem Statement

The current scaffolding and phase-enforcement system has no concept of per-workflow document content requirements. A research doc for a feature issue, a bug issue and a refactor issue are structurally identical — the system cannot enforce that a bug research doc contains a Root Cause Analysis section, or that a feature design doc contains Interface Contracts. Solving this requires a dedicated SSOT for section definitions (sections.yaml) combined with a workflow-to-phase contract mapping in workflows.yaml, without coupling templates, schemas or workphases.yaml to workflow-specific knowledge.

## Research Goals

- Define the sections.yaml config schema as SSOT for document section definitions (heading, description, content_rules)
- Define the phase_contracts extension to workflows.yaml that maps (workflow, phase) → required/optional section keys
- Prove that workphases.yaml, templates and Pydantic schemas remain fully workflow-agnostic
- Establish the precise boundary between sections.yaml (what is valid) and templates (how it looks)
- Map the architecture to three distinct implementation issues: #257 (PSE infrastructure), enforcement issue (under epic #49), template integration issue (under epic #73)

---

## Background

During issue #257 research (phase reordering + PSE SOLID fixes), the question arose how to enforce that different workflow types produce different document content. Initial exploration of workflow-filter flags in workphases.yaml (applies_to_workflows) was rejected as a DRY violation — it would duplicate workflow names across both config files. A tier/weight abstraction was rejected as unnecessary indirection. The solution emerged from the principle that workflows.yaml is the sole owner of workflow semantics: it should also own the mapping from (workflow, phase) to required content. sections.yaml then becomes the SSOT for what a section IS, completely decoupled from where it is used.

---

## Findings

**F1 — Four-layer config architecture (no cross-file name coupling):**

`sections.yaml` owns section definitions — heading string, description, content_rules (min_words, required_subheadings). No phase, no workflow, no required/optional status.

`workflows.yaml` owns phase_contracts — per workflow, per phase: which section keys are required and which optional. This is the only file that knows both workflow names and section keys.

`workphases.yaml` owns gate mechanisms — exit_requires entries reference gate types (file_glob, content_contract) but contain no workflow names and no section definitions.

Templates own rendering — they receive a sections list (key + heading) injected by ArtifactManager and iterate over it. They contain no workflow conditionals.

**F2 — sections.yaml schema:**
```yaml
sections:
  expected_results:
    heading: '## Expected Results'
    description: 'Measurable KPIs that define done'
    content_rules:
      min_words: 20
  root_cause_analysis:
    heading: '## Root Cause Analysis'
    description: 'Why the bug exists'
    content_rules:
      min_words: 30
  interface_contracts:
    heading: '## Interface Contracts'
    description: 'Public API and method signatures'
    content_rules: {}
```

**F3 — workflows.yaml phase_contracts extension:**
```yaml
feature:
  phases: [research, design, planning, tdd, validation, documentation]
  phase_contracts:
    research:
      required: [expected_results, background]
      optional: [findings, open_questions]
    design:
      required: [interface_contracts, data_flow]
      optional: [alternatives]
bug:
  phase_contracts:
    research:
      required: [expected_results, root_cause_analysis]
      optional: [background]
refactor:
  phase_contracts:
    research:
      required: [expected_results, solid_analysis]
      optional: [background]
```

**F4 — workphases.yaml stays workflow-agnostic:**
```yaml
research:
  exit_requires:
    - type: file_glob
      file: 'docs/development/issue{issue_number}/*research*.md'
    - type: content_contract  # PSE resolves contract from workflows.yaml + sections.yaml
```
No workflow names. No section keys. Only the gate type.

**F5 — Template boundary principle:**
templates = how it looks (rendering); sections.yaml = what is valid (PSE enforcement at exit). ArtifactManager injects sections list into template context as [(key, heading)] for rendering. Templates iterate — no conditionals on workflow type. PSE reads sections.yaml content_rules for validation.

**F6 — PSE content_contract gate handler (after OCP registry from #257):**
1. Read active workflow type from state.json
2. Load workflows.yaml[workflow].phase_contracts[phase] → required section keys
3. For each required key: load sections.yaml[key].heading → check presence in document
4. (Future) load sections.yaml[key].content_rules → check content depth

**F7 — ArtifactManager sections injection:**
At scaffold time: load state.json → workflow type → workflows.yaml phase_contracts[phase] → section keys → sections.yaml[key].heading → inject sections list into template context. ResearchContext schema gains no new fields — workflow awareness lives entirely in ArtifactManager and config.

**F8 — Issue boundary:**
Issue #257: PSE OCP registry (gate type extensibility infrastructure) + heading_present gate as first concrete type (## Expected Results on research, unconditional). No sections.yaml, no phase_contracts.
New issue under epic #49: sections.yaml config file + WorkflowConfig.phase_contracts model + WorkphasesConfig content_contract gate type + PSE content_contract handler. Full enforcement.
New issue under epic #73: ArtifactManager sections injection from workflow contract + research.md.jinja2 refactor to iterate sections list. Template/scaffold integration.

## Open Questions

- ❓ Should content_rules in sections.yaml be validated by a Pydantic model at load time, or remain as loose dict for extensibility?
- ❓ When no phase_contract is defined for a workflow+phase combination (e.g. hotfix has no research phase), should the content_contract gate silently pass or warn?
- ❓ Should ArtifactManager inject sections even when scaffold is called outside a workflow context (no state.json)? Fallback: inject no sections, template renders empty sections list.
- ❓ How does the sections injection interact with the V2 Pydantic pipeline — does ResearchContext need a sections field, or is it injected post-validation in _enrich_context_v2?


## Related Documentation
- **[docs/development/issue257/research.md][related-1]**
- **[.st3/workflows.yaml][related-2]**
- **[.st3/workphases.yaml][related-3]**
- **[.st3/artifacts.yaml][related-4]**
- **[mcp_server/managers/phase_state_engine.py][related-5]**
- **[mcp_server/managers/artifact_manager.py][related-6]**
- **[mcp_server/schemas/contexts/research.py][related-7]**
- **[mcp_server/scaffolding/templates/concrete/research.md.jinja2][related-8]**

<!-- Link definitions -->

[related-1]: docs/development/issue257/research.md
[related-2]: .st3/workflows.yaml
[related-3]: .st3/workphases.yaml
[related-4]: .st3/artifacts.yaml
[related-5]: mcp_server/managers/phase_state_engine.py
[related-6]: mcp_server/managers/artifact_manager.py
[related-7]: mcp_server/schemas/contexts/research.py
[related-8]: mcp_server/scaffolding/templates/concrete/research.md.jinja2

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 |  | Agent | Initial draft |