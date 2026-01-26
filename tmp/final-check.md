<!-- d:\dev\SimpleTraderV3\tmp\final-check.md -->
<!-- template=design version=89c6c82d created=2026-01-26T12:15:00Z updated= -->
# Cache Design
**Status:** DRAFT  
**Version:** 1.0  
**Created:** 2026-01-26  
**Last Updated:** 2026-01-26  
**Implementation Phase:** Phase 2.1 - Architecture
---

## Purpose

Caching strategy

## Scope

**In Scope:**
- Caching

**Out of Scope:**
- History

## Prerequisites

Read these first:
1. Redis

---

## 1. Context & Requirements

### 1.1. Problem Statement

Slow.

### 1.2. Requirements

**Functional:**
- [ ] Cache

**Non-Functional:**
- [ ] Sub-ms

### 1.3. Constraints

Must integrate with Redis.
---

## 2. Design Options

### 2.1. Option A: Memory

In-process

**Pros:**
- ✅ Fast

**Cons:**
- ❌ Not shared

---

## 3. Chosen Design

**Decision:** Hybrid Cache

**Rationale:** Hybrid.

### 3.1. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| L1 TTL: 100ms | Balance |
---

## 4. Open Questions

| Question | Options | Status |
|----------|---------|--------|
| Warming? | - | 🔴 Open |

## Related Documentation
- **[docs/arch.md][related-1]**

<!-- Link definitions -->

[related-1]: docs/arch.md

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-26 | Agent | Initial draft |