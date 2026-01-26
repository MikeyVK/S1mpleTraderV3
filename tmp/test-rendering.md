<!-- d:\dev\SimpleTraderV3\tmp\test-rendering.md -->
# Cache Design

<!--
template=design version=89c6c82d
created=2026-01-26T11:30:00Z updated=
-->
<!--
DESIGN TEMPLATE - Extends BASE_TEMPLATE
Purpose: Pre-implementation design documentation (300-600 lines)

Inherits from BASE:
├── Header (Status, Version, Last Updated)
├── Purpose, Scope, Prerequisites
├── Related Documentation + Link definitions
└── Version History

Adds:
├── Header: Created, Implementation Phase
├── Numbered decision sections
├── Design Options with pros/cons
├── Open Questions table
└── Approval section

Rules:
├── Code examples allowed (illustrative, not production)
├── Status lifecycle: PRELIMINARY → APPROVED
└── Focus on decision rationale
-->

<!-- ═══════════════════════════════════════════════════════════════════════════
     HEADER SECTION (from BASE + Design-specific fields)
     ═══════════════════════════════════════════════════════════════════════════ -->
**Status:** DRAFT  
**Version:** 1.0  
**Created:** 2026-01-26  
**Last Updated:** 2026-01-26  
**Implementation Phase:** Phase 2.1 - Architecture
---

## Purpose

Define caching strategy

## Scope

**In Scope:**
- Caching
- TTL

**Out of Scope:**
- History

## Prerequisites

Read these first:
1. Redis ready

---

## 1. Context & Requirements

### 1.1. Problem Statement

System slow.

### 1.2. Requirements

**Functional:**
- [ ] Cache data

**Non-Functional:**
- [ ] Sub-ms

### 1.3. Constraints

Must integrate with existing Redis infrastructure.
---

## 2. Design Options

### 2.1. Option A: In-Memory

In-process cache

**Pros:**
- ✅ Fast

**Cons:**
- ❌ Not shared

---

## 3. Chosen Design

**Decision:** Implement Hybrid Cache

**Rationale:** Hybrid balances performance.

### 3.1. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| L1 TTL: 100ms | Balances performance |
---

## 4. Open Questions

| Question | Options | Status |
|----------|---------|--------|
| Cache warming? | - | 🔴 Open |

## Related Documentation
- **[docs/arch.md][related-1]**

<!-- Link definitions -->

[related-1]: docs/arch.md

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-26 | Agent | Initial draft |