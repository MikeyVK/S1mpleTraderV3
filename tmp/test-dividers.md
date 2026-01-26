<!-- d:\dev\SimpleTraderV3\tmp\test-dividers.md -->
<!-- template=design version=89c6c82d created=2026-01-26T12:30:00Z updated= -->
# Cache Design
**Status:** DRAFT  
**Version:** 1.0  
**Created:** 2026-01-26  
**Last Updated:** 2026-01-26  
**Implementation Phase:** Phase 2.1  

---

## Purpose

Caching

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

Slow system.

### 1.2. Requirements

**Functional:**
- [ ] Cache

**Non-Functional:**
- [ ] Sub-ms

### 1.3. Constraints

Redis only.
---

## 2. Design Options

### 2.1. Option A: Memory

Memory cache

**Pros:**
- ✅ Fast

**Cons:**
- ❌ Isolated

---

## 3. Chosen Design

**Decision:** Hybrid

**Rationale:** Hybrid approach.

### 3.1. Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| L1 100ms | Fast |

---

## 4. Open Questions

| Question | Options | Status |
|----------|---------|--------|
| Warming? | - | 🔴 Open |

## Related Documentation
- **[arch.md][related-1]**

<!-- Link definitions -->

[related-1]: arch.md

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-26 | Agent | Initial draft |