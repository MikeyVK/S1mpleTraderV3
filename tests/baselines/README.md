# Baseline Outputs for Issue #108 Regression Testing

## Purpose

This directory contains **immutable baseline outputs** captured BEFORE the JinjaRenderer extraction (Cycle 0). These baselines serve as reference points for byte-identical regression validation in Cycle 4.

## Captured Baselines

| Baseline File | Template | Size | Purpose |
|--------------|----------|------|---------|
| `baseline_dto.py` | `concrete/dto.py.jinja2` | ~950 bytes | Validates DTO code generation |
| `baseline_worker.py` | `concrete/worker.py.jinja2` | ~3.9KB | Validates Worker code generation |
| `baseline_tool.md` | `concrete/tool.py.jinja2` | ~900 bytes | Validates Tool code generation |
| `baseline_research.md` | `concrete/research.md.jinja2` | ~600 bytes | Validates Research document generation |
| `baseline_planning.md` | `concrete/planning.md.jinja2` | ~600 bytes | Validates Planning document generation |

## Baseline Guarantee

**Immutability Contract:**
- Baselines captured from **pre-extraction** JinjaRenderer (`mcp_server/scaffolding/renderer.py`)
- Same input context → identical output (byte-for-byte)
- Any deviation in Cycle 4 indicates behavioral regression

## Regeneration Process

⚠️ **WARNING:** Only regenerate baselines if template changes are intentional and approved.

**When to Regenerate:**
- Template fixes (e.g., typo corrections in tier0/tier1/tier2)
- Template enhancements (e.g., new SCAFFOLD fields)
- NEVER for "extraction only" changes (would mask regressions)

**How to Regenerate:**

1. **Verify Current State:**
   ```powershell
   # Ensure all tests pass with current baselines
   pytest tests/regression/test_capture_baselines.py -v
   ```

2. **Run Baseline Capture Script:**
   ```powershell
   python scripts/capture_baselines.py
   ```

3. **Review Changes:**
   ```powershell
   git diff tests/baselines/
   ```

4. **Commit with Rationale:**
   ```powershell
   git add tests/baselines/
   git commit -m "chore(issue108): regenerate baselines after template fix

   Reason: [explain why baselines changed]
   Impact: [describe what changed in outputs]
   "
   ```

## Regression Test Usage

**Cycle 4 tests (`tests/regression/test_extraction_regression.py`) will:**
1. Render same templates with same context using **new** TemplateEngine
2. Compare outputs byte-for-byte against these baselines
3. FAIL if any differences detected (regression)

**Example:**
```python
def test_dto_output_identical():
    """TemplateEngine produces identical DTO output."""
    # Render with new TemplateEngine
    engine = TemplateEngine(template_root=get_template_root())
    new_output = engine.render("concrete/dto.py.jinja2", **dto_context)
    
    # Compare to baseline
    baseline = Path("tests/baselines/baseline_dto.py").read_text()
    assert new_output == baseline, "DTO output changed - regression detected"
```

## Context Used for Capture

All baselines use minimal, deterministic context to ensure reproducibility:

**Common Context (All Templates):**
- `version_hash`: `"baseline_v1"` (fixed, not real hash)
- `timestamp`: `"2026-02-13T14:30:00Z"` (ISO 8601 UTC)
- `artifact_type`: Matches template type
- `format`: `"python"` or `"markdown"`

**Template-Specific Context:**
- See `scripts/capture_baselines.py` for exact dictionaries per template

## Related Documentation

- [Issue #108 Planning - Cycle 0](../../docs/development/issue108/planning.md#cycle-0-baseline-capture)
- [Issue #108 Planning - Cycle 4](../../docs/development/issue108/planning.md#cycle-4-regression-validation-suite)

---

**Captured:** 2026-02-13 (Cycle 0 GREEN phase)  
**Script:** `scripts/capture_baselines.py`  
**Tests:** `tests/regression/test_capture_baselines.py`
