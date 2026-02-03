# Jinja2 Template Whitespace Control Strategy (Issue #72)

## Goal
Make whitespace output deterministic across multi-tier Jinja template inheritance (tier0–tier2 + concrete), so we can normalize templates once and stop doing ad-hoc whitespace patches per artifact type.

This document is intended to be *runnable* as a checklist for an implementation agent.

## Assumptions: Jinja Environment Configuration (Project Truth)
This project renders templates with these Jinja2 `Environment` options:

- `trim_blocks=True`
  - Removes the **first newline after a block tag** (`{% ... %}`) only.
  - Does **not** apply to variable tags (`{{ ... }}`).
- `lstrip_blocks=True`
  - Strips **leading spaces and tabs** from the start of a line **up to the start of a block tag**.
  - If there are non-whitespace characters before the tag, nothing is stripped.
- `keep_trailing_newline=True`
  - Preserves a single trailing newline at the end of the template output *if the template source results in it*.
  - Without this, Jinja strips a single trailing newline by default.

These rules are defined by Jinja2 itself and are the basis for everything below.

## Ground Truth: How Jinja2 Whitespace Actually Works
Jinja templates are plain text. Apart from the whitespace-control features below, whitespace in the template source is emitted as-is.

### A. Default behavior (conceptual baseline)
- Whitespace (spaces, tabs, newlines) in the template source is output unchanged.
- Block tags (`{% ... %}`) and variable tags (`{{ ... }}`) are not themselves printed, but the whitespace around them is still part of the template source and may be printed.

### B. `trim_blocks=True`
- Only affects block tags (`{% ... %}`), not variable tags (`{{ ... }}`).
- If a block tag is followed by a newline in the template source, that single newline is removed.
- Consequence: “block lines” (tags placed on their own line) often disappear cleanly without leaving an empty output line.

### C. `lstrip_blocks=True`
- Only affects block tags (`{% ... %}`).
- If a line begins with spaces/tabs followed by a block tag, those spaces/tabs are removed.
- Consequence: indentation spaces placed *before* `{% if ... %}` / `{% for ... %}` are generally not safe to rely on as output indentation.

### D. Manual whitespace control with `-` on delimiters
Jinja supports explicit whitespace stripping by adding `-` to the start or end of:
- block tags: `{%- ... %}` and `{% ... -%}`
- variable tags: `{{- ... }}` and `{{ ... -}}`
- comments: `{#- ... #}` and `{# ... -#}`

Important:
- The `-` must be directly adjacent to the delimiter. This is invalid: `{% - if foo - %}`.

Rule of thumb:
- Use `-` only when you are intentionally removing whitespace that would otherwise be emitted.
- Prefer *surgical* use around known-problem boundaries (super calls, endfor/endif edges), not blanket trimming everywhere.

### E. Manual opt-out with `+`
Jinja supports `+` markers that locally disable environment trimming behavior:
- `{%+ ... %}` disables `lstrip_blocks` for that tag.
- `{% ... +%}` disables `trim_blocks` for that tag.

Use these only when you are intentionally preserving whitespace for a specific construct.

### F. Trailing newlines and `keep_trailing_newline=True`
With `keep_trailing_newline=True`, output will keep a trailing newline **if the rendered output ends with one**.

Project implication:
- The renderer does not “normalize” the last newline for you.
- Templates must explicitly *decide* what they want at EOF.

## Project Strategy (Deterministic Output Under These Semantics)

### 1) “Structure tags on their own lines” is the default, but not magic
Placing control tags on their own lines is still the cleanest approach, especially with `trim_blocks=True` and `lstrip_blocks=True`.

However, do not assume that “block boundaries create exactly one newline”. Newlines are created (or removed) by:
- literal newlines in the template source,
- the effect of `trim_blocks` on block tags,
- any explicit `-` trimming,
- and the text returned by called macros / `super()`.

### 2) Never inject raw newlines with expressions
Avoid `{{ "\n" }}`. It bypasses Jinja’s whitespace controls and tends to double up with literal source newlines or inherited block content.

If you need a blank line, express it as a literal blank line in the template source where it belongs.

### 3) Control whitespace at “merge points”
The most fragile whitespace boundaries are where content is *merged*:
- `{{ super() }}` calls
- macro calls that include trailing newlines
- loop/conditional edges where template authors accidentally include blank lines between `{% endif %}` and `{% endfor %}`

These are the locations where surgical trimming is allowed and expected.

## Required Pattern: `super()` Is a Merge Point
`super()` returns the parent block’s rendered text as-is.

Because `trim_blocks` does **not** apply to `{{ ... }}`, it will not help you if `super()` returns a string that ends with a newline and you also have a newline in your child template.

Therefore, at merge points we require right-trimming of the `super()` expression:

```jinja
{{ super() -}}
```

Meaning:
- If there is whitespace/newline in the template source immediately after the expression, it is removed.
- This prevents the classic “double blank line” after inherited content.

Notes:
- This does not remove whitespace *inside* whatever `super()` returns.
- If the parent intentionally ends with a blank line, that is still inherited.

## Tier Guidance (What Each Tier Is Allowed to Do)

### Tier 0: metadata header only
Tier 0 should emit the scaffold metadata line and then hand off to child templates.

Rules:
- No explicit newline injection via expressions.
- Decide intentionally whether the header ends with a newline.
  - If you want exactly one newline after the header, include a literal newline after the header text and rely on the environment consistently.
  - If you want no trailing newline at this point, do not include one.

### Tier 1 CODE: structural blocks (docstring/imports/class)
Tier 1 CODE is responsible for the *structure* of a Python file (docstring section, import section, class section).

Rules:
- Use `{{ super() -}}` at the top of the content block if Tier 0 provides header content.
- Prefer blocks on their own lines.
- Inside `if`/`for`, never rely on indentation placed before `{% ... %}` tags for output indentation (because `lstrip_blocks=True`).
  - Put the indentation in emitted text (inside the branches) or render whole lines.

### Tier 1 DOCUMENT: structural blocks (title/sections)
Tier 1 DOCUMENT is responsible for Markdown structure.

Rules:
- Avoid a leading blank line before the first header.
- Ensure exactly one blank line between major markdown headings and their content.
- Keep the decision about EOF newline in the *template*, not in the renderer.

### Tier 2 specializations (Python / Markdown / YAML)
Tier 2 may add domain-specific scaffolding (typing imports, yaml boilerplate, markdown front matter, etc.).

Rules:
- If Tier 2 overrides a block that also calls `super()`, treat it as a merge point and right-trim the `super()` expression unless there is a deliberate reason not to.

### Concrete templates
Concrete templates should override only specific blocks and avoid whitespace micromanagement.

Rules:
- Do not introduce aggressive `{%- ... -%}` trimming unless fixing a known merge-point artifact.
- Avoid introducing blank lines around `{% endif %}` / `{% endfor %}` unless you truly want a blank line in output.

## EOF Policy (Project Decision)
This project treats “newline at EOF” as *artifact-type owned by templates*, not globally enforced by the writer.

- For CODE artifacts (Python): prefer exactly one trailing newline.
- For DOCUMENT artifacts (especially tracking/docs): do not require a trailing newline; templates may intentionally omit it.

Because `keep_trailing_newline=True`, templates must be explicit and consistent about whether they end with a newline.

## Deterministic Indentation: Correct Explanation (Issue #72.3)
**Observed problem:** methods generated at column 0 even though the template visually showed indentation.

**Actual root cause under this project’s env:**
- With `lstrip_blocks=True`, leading spaces before a `{% if ... %}` tag are stripped.
- With `trim_blocks=True`, the newline immediately after a `{% ... %}` tag is removed.

So indentation and line breaks around block tags can be removed in ways that surprise you.

**Correct fix pattern:** emit indentation as output text, not as “spaces before a block tag”.

Example (safe):
```jinja
{% if method.async %}    async def {{ method.name }}({% else %}    def {{ method.name }}({% endif %}
```

This keeps indentation inside the emitted text in both branches.

## Trailing Blank Lines in Loops: Correct Explanation and Fix
**Problem:** output ends with extra blank lines.

**Common cause:** a literal blank line in the template source between control tags is still part of the template source unless removed by trimming.

**Fix pattern (surgical):** trim only at the edges that cause the blank line.

```jinja
{% if method.assertions %}
{{ method.assertions | indent(8) }}
{% else %}
# TODO: Add assertions
assert True
{% endif -%}
{%- endfor %}
```

What this does:
- `{% endif -%}` removes the whitespace/newline after the `endif` tag.
- `{%- endfor %}` removes whitespace/newlines before the `endfor` tag.

## Implementation Checklist (Drive the Refactor)

### Environment alignment
- [ ] Confirm the renderer keeps `trim_blocks=True`, `lstrip_blocks=True`, `keep_trailing_newline=True` (do not silently change these).

### Template normalization rules
- [ ] Replace any `{{ "\n" }}` usage with structural whitespace.
- [ ] Treat every `{{ super() }}` call as a merge point; use `{{ super() -}}` unless there is a deliberate reason not to.
- [ ] Remove reliance on indentation before `{% ... %}` tags; emit indentation inside output text.
- [ ] Apply loop-edge trimming only where blank lines are accidental.

### Testing
- [ ] Add/keep render-based tests that assert whitespace for at least one representative template per artifact category (CODE/DOCUMENT/CONFIG).
- [ ] Include at least one test that asserts EOF behavior for a document/tracking artifact (so we don’t regress to “always newline”).

## Anti-Patterns
- Explicit newlines: `{{ "\n" }}`
- “Trim everything” style: `{%- block content -%}` everywhere
- Relying on indentation before `{% if %}` / `{% for %}` for output indentation under `lstrip_blocks=True`
- Fixing one artifact type’s whitespace by breaking another’s (no ad-hoc exceptions without tests)
