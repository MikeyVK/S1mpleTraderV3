<!-- d:\dev\SimpleTraderV3\tmp\caching-strategy-final.md -->
<!-- template=design version=f48e8620 created=2026-01-26T22:01Z updated= -->---
title: Caching Strategy for Market Data
type: design
created: 2026-01-26T22:01Z
---# Caching Strategy for Market Data

**Status:** Draft | **Phase:** Design

---

## Purpose

Define caching architecture for real-time market data to reduce API calls and improve performance

## Scope

**In Scope:**
Redis caching layer, TTL strategies, cache invalidation patterns

**Out of Scope:**
Database optimization, CDN caching, browser-side caching

## Prerequisites

- Understanding of Redis data structures
- Familiarity with market data flow

## 1. Context & Requirements

### Problem Statement

Current system makes excessive API calls to market data providers, resulting in rate limiting and increased costs. Need efficient caching layer that balances data freshness with API usage.

### Requirements

Sub-second cache lookups, automatic expiration based on data type, support for 10K+ symbols, invalidation on market events

### Constraints

Must work with existing Redis infrastructure, cannot exceed 2GB memory budget, must handle market hours vs after-hours differently

## 2. Design Options

### Option 1: TTL-Based Caching

Use fixed TTL values per data type (quotes: 1s, fundamentals: 1h, historical: 24h)

**Pros:**
- Simple to implement
- Predictable behavior
- Low complexity

**Cons:**
- May serve stale data during volatility
- No event-based invalidation
- Wastes resources during low activity

### Option 2: Event-Driven Invalidation

Cache indefinitely and invalidate only on specific market events (trades, corporate actions)

**Pros:**
- Always fresh data
- Efficient resource usage
- Responsive to real-time events

**Cons:**
- Complex event handling
- Risk of missed invalidations
- Requires event bus integration

### Option 3: Hybrid TTL + Events

Combine short TTL (safety net) with event-based invalidation (optimization)

**Pros:**
- Best of both worlds
- Fault tolerant
- Optimizes for common cases

**Cons:**
- Most complex implementation
- Two invalidation paths to maintain
- Potential race conditions

## 3. Chosen Design

### Decision

Implement Hybrid TTL + Events approach (Option 3)

### Rationale

Trading systems require both reliability (TTL safety net) and performance (event optimization). The additional complexity is justified by the fault tolerance gained. Start with TTL-only in MVP, add events in Phase 2.

### Key Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| Use Redis HASH for quote storage | Efficient field updates without full object serialization | More memory than STRING but better update performance |
| Separate TTL per data category | Quotes need 1s freshness, fundamentals can be 1h | More configuration complexity but better resource usage |
| EventBus integration for invalidation | Reuse existing event infrastructure | Couples caching to EventBus availability |
## 4. Open Questions
- What happens to cache during market circuit breakers?
- Should we pre-warm cache at market open?
- How to handle multi-region cache synchronization?

<!-- Link definitions -->

[data-flow]: docs/architecture/data-flow.md
[performance-requirements]: docs/development/performance-requirements.md

## Related Documentation- [data-flow][data-flow]
- [performance-requirements][performance-requirements]

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-01-26T22:01Z | Initial draft | Agent |