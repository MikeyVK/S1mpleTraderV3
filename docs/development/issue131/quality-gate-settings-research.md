<!-- D:\dev\SimpleTraderV3\.st3\quality-gate-settings.md -->
<!-- template=research version=8b7bb3ab created=2026-02-09 updated= -->
# quality-gate-settings

**Status:** DRAFT  
**Version:** 1.0  
**Last Updated:** 2026-02-09

---

## Purpose

Research optimal pyproject.toml and quality.yaml configuration for quality gates that maintains coding standards compliance while separating IDE developer experience from CI/CD strict enforcement

## Scope

**In Scope:**
Ruff check selection, pyproject.toml IDE baseline, quality.yaml CI/CD overrides, Pylint gates 1-3 equivalency, dual-user configuration patterns, coding standards compliance validation

**Out of Scope:**
New quality gates beyond existing 5, Epic #18 enforcement policies, Tool installation procedures, QAManager implementation details

## Prerequisites

Read these first:
1. docs/coding_standards/README.md - Quality metrics overview
2. docs/coding_standards/CODE_STYLE.md - PEP 8 compliance, 100 char limit
3. docs/coding_standards/QUALITY_GATES.md - 5 mandatory gates (10/10 requirement)
4. Current pylint commands for gates 1-3
5. Current mypy strict for gate 4
6. pyrightconfig.json basic mode configuration
---

## Problem Statement

Current quality gates use Pylint for gates 1-3 with strict 10/10 requirement. Need to determine if Ruff can replace Pylint while maintaining same strictness level, and how to configure IDE (lenient) vs CI/CD (strict) appropriately per dual-user scenario.

## Research Goals

- Map current quality gates (Pylint gates 1-3, Mypy gate 4, Pytest gate 5) to Ruff capabilities
- Define IDE-friendly baseline configuration for pyproject.toml per coding standards
- Design CI/CD strict overrides for quality.yaml
- Ensure 10/10 score achievability with Ruff equivalents
- Document configuration choices traceable to docs/coding_standards/
- Validate dual-user scenario (IDE lenient, CI/CD strict) implementation

## Related Documentation
- **[docs/coding_standards/QUALITY_GATES.md - 5 gates definition][related-1]**
- **[docs/coding_standards/CODE_STYLE.md - Style requirements][related-2]**
- **[pyproject.toml - Current Ruff configuration][related-3]**
- **[.st3/quality.yaml - Gate catalog][related-4]**
- **[Ruff documentation - Check equivalents][related-5]**

<!-- Link definitions -->

[related-1]: docs/coding_standards/QUALITY_GATES.md - 5 gates definition
[related-2]: docs/coding_standards/CODE_STYLE.md - Style requirements
[related-3]: pyproject.toml - Current Ruff configuration
[related-4]: .st3/quality.yaml - Gate catalog
[related-5]: Ruff documentation - Check equivalents

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-09 | Agent | Initial draft |