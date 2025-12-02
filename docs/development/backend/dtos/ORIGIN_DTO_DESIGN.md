<!-- filepath: docs/development/backend/dtos/ORIGIN_DTO_DESIGN.md -->
# Origin Design Document

**Status:** ✅ Implemented  
**Version:** 1.0  
**Last Updated:** 2025-12-01

---

## 1. Identity

| Aspect | Value |
|--------|-------|
| **DTO Name** | Origin |
| **ID Prefix** | `TCK_` (Tick), `NWS_` (News), `SCH_` (Schedule) |
| **Layer** | Shared (Platform Data Origin) |
| **File Path** | `backend/dtos/shared/origin.py` |
| **Status** | ✅ Implemented |

---

## 2. Contract

| Role | Component |
|------|-----------|
| **Producer** | DataProvider (tick/news/schedule providers) |
| **Consumer(s)** | PlatformDataDTO, CausalityChain, StrategyJournal |
| **Trigger** | Any platform data ingestion |

**Architectural Role (per DATA_FLOW.md):**
- Type-safe platform data origin reference
- Single source of truth for origin ID + type
- Created by DataProvider, propagated through entire pipeline
- Enables type-safe quant queries (no string parsing)

**What Origin IS:**
- ✅ Type-safe ID + type reference
- ✅ Created once by DataProvider
- ✅ Propagated unchanged through pipeline

**What Origin IS NOT:**
- ❌ NOT business data container (only reference)
- ❌ NO timestamp (lives in parent DTO)
- ❌ NO payload data (separate field in PlatformDataDTO)

---

## 3. Fields

| Field | Type | Req | Producer | Consumer | Validation |
|-------|------|-----|----------|----------|------------|
| `id` | `str` | ✅ | DataProvider | All | Pattern: `^(TCK\|NWS\|SCH)_\d{8}_\d{6}_[0-9a-f]{8}$` |
| `type` | `OriginType` | ✅ | DataProvider | All | Enum: TICK, NEWS, SCHEDULE |

### OriginType Enum

```python
class OriginType(str, Enum):
    """Platform data origin types."""
    TICK = "TICK"       # Market tick data
    NEWS = "NEWS"       # News events
    SCHEDULE = "SCHEDULE"  # Scheduled events (earnings, etc.)
```

### ID Prefix Validation

| Type | Prefix | Example |
|------|--------|---------|
| TICK | `TCK_` | `TCK_20251201_143000_abc12345` |
| NEWS | `NWS_` | `NWS_20251201_143000_def67890` |
| SCHEDULE | `SCH_` | `SCH_20251201_143000_ghi11223` |

---

## 4. Causality

| Aspect | Value |
|--------|-------|
| **Category** | Pre-causality (origin reference) |
| **Has causality field** | ❌ NO - Origin IS the origin |
| **Used in CausalityChain** | `CausalityChain.origin: Origin` |

**Propagation Flow:**
```
DataProvider
    ↓
Origin created (id="TCK_...", type=TICK)
    ↓
PlatformDataDTO(origin=Origin(...))
    ↓
StrategyPlanner
    ↓
CausalityChain(origin=platform_data.origin)
    ↓
StrategyJournalWriter
    ↓
Journal entry (origin_id, origin_type indexed)
```

---

## 5. Immutability

| Decision | Rationale |
|----------|-----------|
| **frozen** | `True` |
| **Why** | Reference identity - never changes after creation. Created once by DataProvider, propagated unchanged. |

---

## 6. Examples

### Tick Origin
```json
{
  "id": "TCK_20251201_143000_abc12345",
  "type": "TICK"
}
```

### News Origin
```json
{
  "id": "NWS_20251201_091500_def67890",
  "type": "NEWS"
}
```

### Schedule Origin
```json
{
  "id": "SCH_20251201_160000_ghi11223",
  "type": "SCHEDULE"
}
```

---

## 7. Dependencies

- `pydantic.BaseModel`
- `enum.Enum`

---

## 8. Breaking Changes

None - DTO is already implemented and stable.

### Implementation Code

```python
# backend/dtos/shared/origin.py

from enum import Enum
from pydantic import BaseModel, model_validator


class OriginType(str, Enum):
    """Platform data origin types."""
    TICK = "TICK"
    NEWS = "NEWS"
    SCHEDULE = "SCHEDULE"


class Origin(BaseModel):
    """
    Platform data origin - type-safe reference.
    
    Attributes:
        id: Origin ID with type prefix (TCK_/NWS_/SCH_...)
        type: Origin type enum (TICK/NEWS/SCHEDULE)
    """
    model_config = {"frozen": True}
    
    id: str
    type: OriginType
    
    @model_validator(mode='after')
    def validate_id_prefix(self) -> 'Origin':
        """Validate ID prefix matches type."""
        prefix = self.id.split('_')[0]
        expected = {
            OriginType.TICK: "TCK",
            OriginType.NEWS: "NWS",
            OriginType.SCHEDULE: "SCH"
        }
        if prefix != expected.get(self.type):
            raise ValueError(
                f"ID prefix '{prefix}' doesn't match type '{self.type}'"
            )
        return self
```

---

## 9. Verification Checklist

### Design Document
- [x] All 8 sections completed
- [x] Reviewed against DATA_FLOW.md
- [x] Breaking changes documented (none)

### Implementation
- [x] OriginType enum defined
- [x] Origin model frozen
- [x] ID prefix validation

### Tests
- [x] Valid origins create successfully
- [x] Invalid prefix raises ValueError
- [x] Immutability enforced

### Quality Gates
- [ ] `pytest tests/unit/dtos/shared/test_origin.py` - ALL PASS
- [ ] `pyright backend/dtos/shared/origin.py` - No errors

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|--------|
| 1.0 | 2025-12-01 | AI Agent | Refactored to standard 1-8 structure |
