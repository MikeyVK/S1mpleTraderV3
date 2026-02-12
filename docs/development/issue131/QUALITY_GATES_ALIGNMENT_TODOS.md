<!-- docs/development/issue131/QUALITY_GATES_ALIGNMENT_TODOS.md -->
<!-- template=design version=5827e841 created=2026-02-12T00:00Z updated= -->
# Issue 131 — Quality Gates Alignment (TODOs + Acceptance Criteria)

**Status:** DRAFT  
**Version:** 1.0  
**Last Updated:** 2026-02-12

## Prerequisites

Read these first:
1. Review `.st3/quality.yaml` current gate commands and flags
2. Review `docs/coding_standards/QUALITY_GATES.md` and `docs/coding_standards/README.md` for drift
---

## 1. Context & Requirements

### 1.1. Problem Statement

Align quality gate doctrine and documentation so CI/PR enforcement is strict and authoritative while IDE configuration remains pragmatic. Ensure formatting is enforced explicitly, gates apply to tests as well as production code, and coverage is enforced as a separate SRP-aligned gate (branch coverage >= 90% hard fail).

### 1.2. Requirements

**Functional:**
- [ ] Docs clearly state: `pyproject.toml` is IDE baseline; `.st3/quality.yaml` is CI authority.
- [ ] Ruff gates in CI run with `--isolated` and docs reflect exact commands/flags.
- [ ] Gates apply to both production code and `tests/**/*.py`.
- [ ] Gate 6 exists: pytest + coverage with `--cov-branch` and `--cov-fail-under=90`, covering `backend` + `mcp_server`.
- [ ] Coverage enforcement is separated from Gate 5 (tests-only).

**Non-Functional:**
- [ ] Copy/paste reproducibility: docs commands match `.st3/quality.yaml` byte-for-byte.
- [ ] SRP clarity: formatting (Gate 0), lint (Gate 1), imports (Gate 2), line length (Gate 3), typing (Gate 4), tests (Gate 5), coverage (Gate 6) are unambiguous.
- [ ] Developer experience: local `pytest tests/` runs without automatic coverage noise by default.
- [ ] Future-proof coverage scope: easy to extend to new production packages without mixing toolchains.

### 1.3. Constraints

## Source of Truth

This doc is the handoff checklist for implementing the agreed policy and aligning:
- `pyproject.toml` (IDE / developer experience baseline)
- `.st3/quality.yaml` (CI/PR quality gates authority)
- `docs/coding_standards/*` (documentation must match reality)

## TODO 1 — Document the doctrine (IDE vs CI)

**Work**
- Update `docs/coding_standards/QUALITY_GATES.md` to explicitly document:
  - `pyproject.toml` = IDE baseline (pragmatic allowed)
  - `.st3/quality.yaml` = CI authority (strict)
  - Ruff gates use `--isolated`
  - Gates apply to `tests/**/*.py`
- Update `docs/coding_standards/README.md` with a short summary and link to the above.

**Acceptance Criteria**
- `docs/coding_standards/QUALITY_GATES.md` contains a short “Config doctrine” section with the four bullets above.
- `docs/coding_standards/README.md` no longer implies IDE == CI; it points to QUALITY_GATES.md as source.

---

## TODO 2 — Remove/replace outdated Pylint metrics from docs

**Problem**
- `docs/coding_standards/README.md` contains a “Quality Metrics” table referencing Pylint, while CI uses Ruff gates 0–3.

**Work**
- Replace that table with the current gates (0–6) and tools (Ruff/Mypy/Pytest/Coverage).

**Acceptance Criteria**
- README does not reference Pylint as an active gate for 0–3.
- README lists Ruff format + Ruff strict lint + imports + line length + mypy (DTO scoped) + pytest + coverage.

---

## TODO 3 — Make docs commands match `.st3/quality.yaml` exactly

**Work**
- Ensure Gate 0–3 command examples in `docs/coding_standards/QUALITY_GATES.md` are **exact copies** of the flags used in `.st3/quality.yaml`.
  - Gate 0 must include `--isolated`.
  - Gate 2/3 examples must include the same `--target-version` and `--line-length` flags as the gate config.
- Include examples for both:
  - A production file (e.g. `backend/...`)
  - A test file (e.g. `tests/.../test_*.py`)

**Acceptance Criteria**
- For each gate (0–3), docs show a production + test example.
- Flags in docs are byte-for-byte aligned with `.st3/quality.yaml` for those gates.

---

## TODO 4 — Clarify Gate 1 SRP (naming + explanation)

**Problem**
- Gate 1 is “strict lint” but intentionally excludes `E501` and `PLC0415`, which are checked by Gate 3 and Gate 2.

**Work**
- Rename Gate 1 in `.st3/quality.yaml` (and in docs) to something unambiguous, e.g.:
  - “Gate 1: Ruff Strict Lint (excl. line length + import placement)”
- Update docs to explain the split:
  - Gate 2 == import placement (PLC0415)
  - Gate 3 == line length (E501)

**Acceptance Criteria**
- Gate 1 name and docs clearly state what is included/excluded.
- No reader confusion that Gate 1 is “formatting” (formatting is Gate 0).

---

## TODO 5 — Explain Ruff `ANN` rules in plain language (tests included)

**Problem**
- Gate 1 selects `ANN` rules; users may not know what `ANN` means.

**Work**
- Add a short explanation in `docs/coding_standards/QUALITY_GATES.md`:
  - `ANN` = type annotation rules (function params + return types should be annotated).
- Add one minimal failure/fix example in a test file.

**Acceptance Criteria**
- Docs contain a short “What is ANN?” section.
- Docs include a test-oriented example.

---

## TODO 6 — Decouple coverage from default pytest runs (SRP prerequisite)

**Problem**
- `pyproject.toml` currently sets `pytest` `addopts` to include coverage flags. This couples coverage to every test run and can make Gate 5 noisy/non-deterministic.

**Work**
- Remove coverage flags from `[tool.pytest.ini_options].addopts` in `pyproject.toml`.
- Update docs to instruct that coverage is enforced by Gate 6.

**Acceptance Criteria**
- Running `pytest tests/` locally no longer automatically emits coverage unless Gate 6 command is used.
- Gate 5 can run tests without coverage warnings.

---

## TODO 7 — Add Gate 6: Coverage (branch, hard fail, >= 90%)

**Work**
- Extend `.st3/quality.yaml`:
  - Add `gate6_coverage` to `active_gates`.
  - Define `gate6_coverage` as an `exit_code` gate.
  - Command must:
    - run pytest over `tests/`
    - enable coverage for production packages:
      - `--cov=backend`
      - `--cov=mcp_server`
    - enable branch coverage: `--cov-branch`
    - hard fail below 90%: `--cov-fail-under=90`

**Acceptance Criteria**
- Gate 6 exists in `.st3/quality.yaml` and is active.
- Gate 6 fails when branch coverage is < 90%.
- Gate 6 covers both `backend` and `mcp_server`.

---

## TODO 8 — Keep Gate 5 “tests only” (no coverage)

**Work**
- Ensure Gate 5 command in `.st3/quality.yaml` remains tests-only.

**Acceptance Criteria**
- Coverage failure cannot cause Gate 5 to fail; coverage failures occur only in Gate 6.

---

## TODO 9 — Update QUALITY_GATES.md to include Gate 6

**Work**
- Add “Gate 6: Coverage (branch >= 90%)” to `docs/coding_standards/QUALITY_GATES.md`.
- Include exact copy/paste command matching `.st3/quality.yaml`.

**Acceptance Criteria**
- Docs include Gate 6 with the same flags as `.st3/quality.yaml`.

---

## TODO 10 — Future-proofing: production scope expansion policy

**Work**
- Document how Gate 6 scope expands when new production Python packages are added.

**Acceptance Criteria**
- Docs define how scope changes are handled.

---

## Verification Checklist (for the implementer)

- Docs are consistent with `.st3/quality.yaml` for gates 0–6 commands.
- Gate 5 does not emit coverage warnings.
- Gate 6 fails if branch coverage < 90% and passes otherwise.
- Gates apply to test files.

---

## Files explicitly in scope for changes

- `pyproject.toml`
- `.st3/quality.yaml`
- `docs/coding_standards/QUALITY_GATES.md`
- `docs/coding_standards/README.md`

---

## 2. Design Options

### 2.1. Option A: Keep IDE and CI aligned (single config)

Use `pyproject.toml` as the single source for both IDE and CI behavior.

**Pros:**
- ✅ Simpler mental model: one config file.
- ✅ Less duplication of flags/settings.

**Cons:**
- ❌ CI inherits IDE pragmatism/ignores; strictness becomes fragile.
- ❌ Harder to guarantee deterministic PR gating.

### 2.2. Option B: Strict CI authority + pragmatic IDE baseline (chosen)

Treat `.st3/quality.yaml` as strict CI authority; keep `pyproject.toml` pragmatic for local dev/IDE; CI uses `--isolated` where needed.

**Pros:**
- ✅ CI/PR enforcement is deterministic and strict.
- ✅ IDE remains productive (pragmatic ignores allowed).
- ✅ Clear SRP split across gates; docs can mirror gates exactly.

**Cons:**
- ❌ Some duplication of settings/flags across config and docs.
- ❌ Requires disciplined doc maintenance to avoid drift.

### 2.3. Option C: Relax CI to match IDE

Loosen `.st3/quality.yaml` to match `pyproject.toml` behavior to reduce friction.

**Pros:**
- ✅ Fewer local/CI discrepancies.

**Cons:**
- ❌ Violates the requirement that CI must be stricter than IDE.
- ❌ Lets quality regressions slip into PRs.
---

## 3. Chosen Design

**Decision:** Adopt strict CI gates in `.st3/quality.yaml` (authoritative), keep `pyproject.toml` pragmatic for IDE/dev; enforce gates on tests; add separate coverage gate (branch >= 90% hard fail) and decouple coverage from default pytest runs.

**Rationale:** This matches the agreed policy: CI must be stricter than IDE, formatting is a first-class gate, and coverage enforcement must be explicit and SRP-aligned. Using isolated Ruff in CI prevents IDE-only ignores from weakening PR enforcement.

### 3.1. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| CI uses `.st3/quality.yaml` as authority | Allows strict PR gating independent of IDE convenience settings. |
| Ruff gates in CI use `--isolated` | Prevents inheriting `pyproject.toml` ignores/config that are intended for IDE/dev only. |
| Gates apply to `tests/**/*.py` | Ensures tests meet the same baseline quality standards as production code. |
| Coverage is a separate Gate 6 (branch >= 90%) | Keeps SRP: tests gate validates correctness; coverage gate validates test thoroughness. |
| Remove default coverage from pytest `addopts` | Avoids noisy/non-deterministic test runs and ensures coverage is enforced only by Gate 6. |

---
## 4. Open Questions

| Question | Options | Status |
|----------|---------|--------|
| Should the old manually-created TODO file be deleted (preferred) or replaced with a pointer to this scaffolded doc given `.agent/reboot.md` forbids terminal git/file commands? |  |  |
## Related Documentation
- **[docs/coding_standards/QUALITY_GATES.md][related-1]**
- **[docs/coding_standards/README.md][related-2]**
- **[.st3/quality.yaml][related-3]**
- **[pyproject.toml][related-4]**
- **[docs/development/issue131/design.md][related-5]**

<!-- Link definitions -->

[related-1]: docs/coding_standards/QUALITY_GATES.md
[related-2]: docs/coding_standards/README.md
[related-3]: .st3/quality.yaml
[related-4]: pyproject.toml
[related-5]: docs/development/issue131/design.md

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 |  | Agent | Initial draft |