<!-- d:\dev\SimpleTraderV3\tmp\websocket-architecture-design.md -->
<!-- template=design version=3438d176 created=2026-01-26T22:07Z updated= -->---
title: WebSocket Architecture for Real-Time Market Data
type: design
created: 2026-01-26T22:07Z
---


# WebSocket Architecture for Real-Time Market Data

**Status:** Draft | **Phase:** Design

---

## Purpose

Design a scalable WebSocket architecture for streaming real-time market data to multiple clients with minimal latency

## Scope

**In Scope:**
WebSocket server design, connection management, message routing, authentication

**Out of Scope:**
Frontend client implementation, load balancing infrastructure, database design

## Prerequisites

- Understanding of WebSocket protocol
- Familiarity with Redis pub/sub
- Knowledge of existing EventBus architecture

## 1. Context & Requirements

### Problem Statement

Current HTTP polling approach creates excessive server load and introduces 500ms+ latency. Need bidirectional real-time communication for price updates, order fills, and account changes.

### Requirements

Sub-100ms message delivery, support 1000+ concurrent connections, automatic reconnection, message ordering guarantees, authentication/authorization

### Constraints

Must integrate with existing EventBus, cannot exceed 4GB memory per server instance, must support horizontal scaling

## 2. Design Options

### Option 1: Single WebSocket Server

Monolithic WebSocket server handling all connections and message routing

**Pros:**
- Simple architecture
- No coordination overhead
- Easy to debug

**Cons:**
- Single point of failure
- Cannot scale beyond single machine
- All clients disconnected on deploy

### Option 2: WebSocket Farm + Redis Pub/Sub

Multiple WebSocket servers with Redis pub/sub for message distribution

**Pros:**
- Horizontal scaling
- No single point of failure
- Rolling deploys possible

**Cons:**
- Redis becomes bottleneck
- More complex architecture
- Message ordering challenges

### Option 3: Hybrid: WebSocket Farm + Direct EventBus

WebSocket servers subscribe directly to EventBus, Redis only for coordination

**Pros:**
- Best performance (direct events)
- Leverages existing EventBus
- Reduced Redis load

**Cons:**
- Each server needs full EventBus subscription
- More memory usage per server
- Complex failover logic

## 3. Chosen Design

### Decision

Implement Hybrid approach (Option 3) with staged rollout

### Rationale

Trading applications demand lowest possible latency and highest reliability. Direct EventBus subscription eliminates Redis hop while maintaining scalability. Start with single server (MVP), add farm when load increases.

### Key Decisions

| Decision | Rationale | Trade-offs |
|----------|-----------|------------|
| Use FastAPI WebSockets | Already using FastAPI, native async support, good documentation | Tied to Python ecosystem, cannot use Node.js optimizations |
| JWT authentication at connection time | Reuse existing auth infrastructure, validate once per connection | Cannot revoke tokens mid-session without disconnect |
| Room-based subscriptions | Clients subscribe to specific symbols/accounts, reduces unnecessary traffic | More complex subscription management |
## 4. Open Questions
- How to handle client reconnection storms after server deploy?
- Should we implement message compression (deflate)?
- What metrics do we need for monitoring WebSocket health?

<!-- Link definitions -->

[event-bus-design]: docs/architecture/event-bus-design.md
[caching-strategy-design]: docs/development/caching-strategy-design.md
[authentication]: docs/architecture/authentication.md

## Related Documentation
- [event-bus-design][event-bus-design]
- [caching-strategy-design][caching-strategy-design]
- [authentication][authentication]

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 0.1 | 2026-01-26T22:07Z | Initial draft | Agent |