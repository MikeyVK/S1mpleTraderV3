<!-- docs/development/issue460/deferred-work.md -->
<!-- template=generic_doc version=43c84181 created=2026-08-24 updated=2026-08-24 -->
# Issue 460 Deferred Work

**Status:** PRELIMINARY  
**Version:** 1.1  
**Last Updated:** 2026-08-24  
**Originating Issue:** 460

## Purpose

Preserve all work explicitly deferred from issue 460 in one durable, non-authoritative follow-up notice. This document keeps deferred evidence and ownership visible without enlarging the primary Research artifact or authorizing implementation.

## Status and Authority

The four deferrals below were approved during issue-460 Research. Their inventories and preliminary priorities are inputs to future Research, not future Design or implementation authorization.

The Generic Python class responsibility is approved in [Research](research.md) as a bounded body-free plain-class skeleton. That artifact-local boundary does not decide method-content policy for specialized Python templates.

| Deferred boundary | Issue-460 consequence | Future owner |
|---|---|---|
| S1mpleTrader-local specialization | Remove consumer-specific behavior from the portable PGMCP suite; perform no cross-repository edits | A later S1mpleTrader repository-local issue |
| Complete YAML artifact subset | Remove two incomplete unreachable seeds now; do not restore them piecemeal | A future PGMCP issue |
| Portable Python artifact coverage | Add no new Python artifact types in issue 460 | A future PGMCP issue with fresh consumer validation |
| Purpose-aware runtime artifact discovery | Add no new MCP tool or overloaded introspection mode in issue 460 | A future PGMCP feature issue |

---

## S1mpleTrader-Local Template Specialization

Portable PGMCP code templates must remove unconditional logging, translator, Backend-layer, and other S1mpleTrader-specific boilerplate. Those details are not valueless: they are precisely what can make a workspace-owned suite substantially more productive than the portable baseline.

The later S1mpleTrader repository-local migration issue must therefore treat the six preserved patterns and the adapter/service boilerplate as one deliberate specialization set. It must assess and, where still valid, recompose project logging, LogEnricher, Translator, lifecycle, dependency, error, and typed-ID conventions on top of the new PGMCP extension contract. In particular, removing unconditional logging/translation behavior from the package adapter is not a decision to discard it from S1mpleTrader. The distinction is ownership: generic behavior in PGMCP, project conventions in S1mpleTrader.

Issue 460 records this preservation obligation but does not design or implement the S1mpleTrader-local successor suite.

## Complete YAML Artifact Package Subset

The unreachable `tier1_base_config.jinja2` and `tier2_base_yaml.jinja2` files are incomplete seeds, not supported behavior. They have no public artifact registration, concrete renderer, complete schema, output-profile contract, or behavioral consumer. Issue 460 removes them from the official suite instead of carrying an unreachable partial tier.

A future PGMCP Research phase should evaluate a complete YAML configuration artifact subset instead of restoring the two files verbatim. The following are inherited constraints and Design hypotheses to evaluate, not selected Design or Planning:

- a public YAML/config artifact registration and complete portable context contract;
- tier-one config, tier-two YAML, and concrete renderer responsibilities;
- bounded acyclic structured entries and sections rather than an unrestricted recursive YAML DSL;
- strict-by-default YAML output-profile validation;
- startup discovery, complete graph identity, and `scaffold_schema` exposure without artifact-specific Python registration;
- minimal and property-complete rendering whose parsed YAML data proves semantic behavior without full-text snapshots;
- a temporary complete active-root fixture that proves a new artifact can be added through suite files alone;
- packaging, documentation, and extension-boundary evidence.

The current files remain recoverable through Git history and this durable specification; keeping dead package files is not required to preserve the idea.

**Deferred Strategy (human-approved 2026-08-23):** remove both incomplete files in issue 460. Hand the complete YAML artifact package subset to coordination as the explicitly recommended first follow-up PGMCP issue on its own branch.

---

## Purpose-Aware Runtime Artifact Discovery

Current scaffold tool schemas enumerate the artifact IDs resolved from the active registry, while `scaffold_schema` exposes one selected artifact's context contract. Neither surface currently lists each available ID together with its purpose before selection. This is a real usability gap, but issue 460 does not need a new runtime discovery capability to correct schema-template rendering contracts.

Issue-460 Research classified F-18 as a feature request and compared three future directions:

| Future option | Benefit | Cost, risk, and consumer impact |
|---|---|---|
| New harness-agnostic discovery tool | Clear list-first workflow and a focused ID-to-purpose response | Adds a public MCP capability, input/output DTOs, cache/presentation behavior, tests, documentation, and another tool for clients to discover |
| Extend an existing introspection surface | Reuses an existing capability and avoids a new tool name | Overloads an artifact-specific contract query with catalog behavior and changes its input/output semantics |
| Improve existing/static discovery without runtime expansion | Lowest runtime and migration cost | Retains dependence on instructions or documentation and does not fully eliminate catalog drift risk |

F-16 remains in issue 460 because it preserves an existing suite-owned purpose description through selected-artifact introspection. It does not by itself create pre-selection catalog discovery.

**Deferred Strategy (human-approved 2026-08-24):** introduce no new discovery tool or overloaded introspection mode in issue 460. A future feature issue must revalidate the consumer need and compare all three options; the previously proposed single MCP tool is retained only as a non-binding hypothesis.

---

## Portable Python Template-Suite Coverage

### Source Context

Issue 460 found that eleven current public artifact IDs resolve exclusively to Python templates: `adapter`, `dto`, `generic`, `integration_test`, `interface`, `resource`, `schema`, `service`, `tool`, `unit_test`, and `worker`. The approved F-17 strategy will give language- or technology-specific contracts explicit identities. The approved Generic responsibility remains a bounded body-free plain-class skeleton and may not absorb the deferred artifact responsibilities.

Registration demonstrates that a responsibility is represented; it does not imply that the current schema and renderer are already coherent. The [issue-460 Research](research.md) and [template-suite catalog](template-suite-catalog.md) remain authoritative for the active semantic audit and individual dispositions.

### Current Registered Python Coverage

| Responsibility family | Current artifact types | Coverage represented by the registration |
|---|---|---|
| Plain class | `generic` | One deliberately selected, bounded Python class skeleton |
| Runtime-validated data | `dto`, `schema` | Pydantic DTO and configuration/schema models |
| Behavioral contract | `interface` | A Python `typing.Protocol` contract |
| Named component roles | `adapter`, `service`, `worker` | Package-selected architectural component responsibilities |
| MCP integration | `tool`, `resource` | Python implementations of MCP concepts |
| Tests | `unit_test`, `integration_test` | Pytest-oriented test modules |

The suite is therefore comparatively strong in Pydantic, MCP, pytest, and named class-oriented architecture roles. It offers few first-class choices for ordinary Python constructs outside those areas.

### Evidence-Backed Candidate Gaps

The gaps are not merely hypothetical language features. Current PGMCP production or test code already contains:

- top-level procedural functions in [cli.py](../../../mcp_server/cli.py), [error_handling.py](../../../mcp_server/core/error_handling.py), and [version_hash.py](../../../mcp_server/scaffolding/version_hash.py);
- standard-library dataclasses in [bootstrap.py](../../../mcp_server/bootstrap.py) and [scaffold_result.py](../../../mcp_server/scaffolders/scaffold_result.py);
- `Enum`, `StrEnum`, and `IntEnum` types in [tool_outputs.py](../../../mcp_server/schemas/tool_outputs.py), [artifact_registry_config.py](../../../mcp_server/config/schemas/artifact_registry_config.py), and [pytest_runner.py](../../../mcp_server/managers/pytest_runner.py);
- exception hierarchies in [exceptions.py](../../../mcp_server/core/exceptions.py);
- abstract base classes in [base_scaffolder.py](../../../mcp_server/scaffolders/base_scaffolder.py) and [resources/base.py](../../../mcp_server/resources/base.py);
- `TypedDict` shapes in [phase_detection.py](../../../mcp_server/core/phase_detection.py);
- package initializers throughout the source tree;
- reusable pytest fixtures and helpers under [tests/mcp_server/fixtures](../../../tests/mcp_server/fixtures).

Their presence does not automatically justify a public artifact type. It does demonstrate that the retained plain-class template cannot represent the workspace's ordinary Python vocabulary without becoming an unbounded catch-all.

| Candidate responsibility | Distinct semantic value | Preliminary disposition |
|---|---|---|
| Procedural Python module | A file-level identity with a module docstring, structured imports, and zero or more structured top-level sync/async function signatures; functions are module members rather than separate persistence targets | Strong first-wave candidate; research whether one bounded module contract is preferable to a separate single-function artifact |
| Standard-library dataclass | A value/state carrier with dataclass-specific choices such as frozen and slots, without importing Pydantic validation or serialization semantics | Strong first-wave candidate; keep its purpose distinct from DTO and config schema |
| Enum | A closed named value set with explicit member names, values, documentation, and a deliberate `Enum`, `StrEnum`, or `IntEnum` form | Strong first-wave candidate; Python-version support and value constraints need an explicit profile |
| Exception | A documented exception type or coherent hierarchy with explicit bases and intentionally minimal initial state | Strong first-wave candidate; do not make arbitrary error payload conventions portable by default |
| Abstract base class | Runtime inheritance and abstract-method enforcement, which differ materially from structural `Protocol` typing | Conditional candidate; require a consumer that needs runtime inheritance rather than expanding the interface artifact |
| Static structural data contract | `TypedDict`, `NamedTuple`, `TypeAlias`, or `NewType` express shapes or identities without Pydantic runtime behavior | Conditional candidate; first determine whether these form one coherent responsibility or several small contracts |
| Package initializer | A package docstring and deliberate public re-exports in `__init__.py` | Conditional candidate; output-path and directory ownership may place this partly in workspace skeleton templating |
| Reusable test-support module | Shared fixtures and test helpers outside one unit or integration test file | Conditional candidate; hypothesis: if retained, use an explicit structured test contract rather than reviving the removed orphan fixture macro |
| Other Python protocols | Decorators, context managers, iterators, generators, descriptors, mixins, and similar forms can have distinct mechanics | Inventory-only; normal editing or the bounded class/module artifacts are preferable until repeated consumer evidence demonstrates a stable separate contract |

This list is deliberately open to additional evidence. It is neither a complete taxonomy of Python nor a promise that every row becomes a public artifact.

### Preliminary Follow-Up Priorities

A future PGMCP issue should research portable Python language-artifact coverage as a suite-extension problem, not restore a universal source generator.

#### First Evaluation Wave

1. Procedural Python module.
2. Standard-library dataclass.
3. Enum.
4. Exception.

These candidates are common, semantically distinct, portable, and already represented in current repository code.

#### Evidence-Gated Second Wave

- Abstract base class.
- Static structural data contracts.
- Package initializer.
- Reusable test-support module.
- Additional constructs discovered through supported consumer workspaces.

The future Research phase may split, merge, reprioritize, or reject candidates when concrete consumer evidence warrants it. The wave ordering is a starting hypothesis, not an implementation plan.

### Constraints Inherited from Issue 460

For every artifact responsibility selected by future Research, the following inherited constraints and hypotheses require validation; they are not a preselected Design:

- one discoverable, language-qualified ID must have one concise purpose and one finite context contract;
- symbol-name and file-target representations must be explicit rather than blindly reusing the scaffold-envelope name;
- artifact descriptions and valid Python docstrings apply at the relevant module, class, member, or field boundaries;
- declarations and signatures are structured; each specialized artifact's future Research must decide independently whether any caller-supplied implementation content belongs to its finite contract;
- an empty skeleton is supported only where the empty form has legitimate scaffolding value;
- minimal and property-complete render cases prove the public contract;
- an applicable Python output-validation capability provides objective evidence where available;
- one registered renderer and one complete suite-graph/package identity own the artifact;
- optional capabilities that materially widen the contract require consumer evidence;
- first-time-right means syntactically valid and structurally coherent scaffolding that is expected to be edited, not an application-complete implementation.

Inherited issue-460 constraint: the follow-up should reject a generic Python AST, conditional mega-schema, hidden renderer routing, or fallback substitution unless new evidence explicitly reopens that boundary.

### Ownership Boundary

Architecture patterns such as repository, factory, builder, command, query, handler, controller, event consumer, or strategy are conceivable Python templates. Framework artifacts such as ORM models, API routers, CLI commands, task-queue jobs, and migrations are also conceivable. They are not automatically portable language artifacts.

Those responsibilities remain workspace or framework specializations unless multiple supported consumers demonstrate a stable package-suite purpose. A construct being implementable in Python is insufficient evidence that the portable PGMCP package must own its template.

### Deferred Strategy

**Human-approved 2026-08-24:** implement no new Python artifact types in issue 460. Preserve this non-exhaustive inventory as durable input for a future PGMCP Research phase, initially evaluating procedural modules, standard-library dataclasses, enums, and exceptions.

The approved Generic plain-class artifact may not absorb these deferred responsibilities. Its body-free contract is artifact-local and creates no blanket prohibition for specialized Python templates considered by future Research.

## Related Documentation

- [Issue 460 Research](research.md)
- [Issue 460 Research Findings](research-findings.md)
- [Issue 460 Template-Suite Catalog](template-suite-catalog.md)
- [Documentation Standard](../../coding_standards/DOCUMENTATION_STANDARD.md)
- [Architecture Principles](../../coding_standards/ARCHITECTURE_PRINCIPLES.md)

---

## Version History

| Version | Date | Changes |
|---|---|---|
| 1.1 | 2026-08-24 | Add deferred F-18 runtime discovery, reconcile the approved Generic boundary, and remove any implied suite-wide method-body rule |
| 1.0 | 2026-08-24 | Consolidate all issue-460 deferred work and preserve the Generic Python approval boundary |
