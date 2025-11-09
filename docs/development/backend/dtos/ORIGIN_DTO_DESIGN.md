# Origin DTO - Preliminary Design

**Status:** Preliminary - Architectural Contract  
**Versie:** 0.1  
**Datum:** 2025-11-08

---

## 1. Scope & Responsibility

**What Origin DTO IS:**
- Type-safe platform data origin reference
- Single source of truth for origin ID + type
- Created by DataProvider
- Propagated through PlatformDataDTO → CausalityChain
- Enables type-safe quant queries

**What Origin DTO IS NOT:**
- ❌ NOT business data container (only reference)
- ❌ NO timestamp (lives in parent DTO)
- ❌ NO payload data (separate field in PlatformDataDTO)

---

## 2. Structure

**DTO Definition:**
```python
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
        if prefix != expected[self.type]:
            raise ValueError(
                f"ID prefix '{prefix}' doesn't match type '{self.type}'"
            )
        return self
```

---

## 3. Integration Points

**Created by:**
- DataProvider (tick/news/schedule providers)

**Used in:**
- `PlatformDataDTO.origin` - Origin reference
- `CausalityChain.origin` - Copied from PlatformDataDTO
- StrategyJournal entries - Type-safe queries

**Propagation Flow:**
```
DataProvider
    ↓
Origin DTO created
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

## 4. Benefits

**Type Safety:**
- Compiler enforces valid origin types
- No string parsing in business logic
- Validation at creation (DataProvider)

**Quant Analysis:**
- Database index on origin_type
- Type-safe queries: `WHERE origin_type = 'TICK'`
- No prefix pattern matching needed

**Scalability:**
- New origin types = add enum value
- No consumer code changes (type is explicit)

---

## 5. Open Questions

1. Should Origin include timestamp? (Or only in parent DTO?)
2. Additional metadata fields (exchange name, instrument type)?
3. Validation: Should we validate ID format beyond prefix?
4. Immutability: Frozen model or mutable?

---

## 6. Related Documents

- `CAUSALITY_CHAIN_LIFECYCLE.md` - Origin propagation
- `PlatformDataDTO` - Container for Origin
- `StrategyJournalWriter` - Uses Origin for journal entries

---

## 7. Implementation Notes

**File Location:**
- `backend/dtos/shared/origin.py` (or `platform_data.py`)

**Dependencies:**
- Pydantic BaseModel
- OriginType enum

**Validation:**
- ID prefix must match type
- ID format: `{PREFIX}_{YYYYMMDD}_{HHMMSS}_{hash}`
