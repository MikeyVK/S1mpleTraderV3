# Execution Service Flow Visualization

Dit diagram visualiseert hoe de `ExecutionService` fungeert als de centrale "Fleet Manager" voor parallelle algoritmen, geïntegreerd in de Event-Driven architectuur.

## 1. The Big Picture (Component Relaties)

```mermaid
graph TD
    subgraph "Event Layer"
        EB[EventBus]
    end

    subgraph "Execution Layer (The New Design)"
        EA[ExecutionAdapter]
        ES[ExecutionService]
        AR[AlgoRegistry]
        
        subgraph "Active Algorithms (Concurrency)"
            A1[Algo 1: TWAP Entry]
            A2[Algo 2: Stop Loss]
            A3[Algo 3: Iceberg Exit]
        end
    end

    subgraph "IO Layer"
        EH[ExecutionHandler]
        SL[StrategyLedger]
        XC[ExchangeConnector]
    end

    EB -->|Events: Directive, Tick, Fill| EA
    EA -->|Method Calls| ES
    ES -->|Factory Create| AR
    ES -->|Manage & Route| A1
    ES -->|Manage & Route| A2
    ES -->|Manage & Route| A3
    
    A1 -->|OrderRequest| ES
    A2 -->|OrderRequest| ES
    A3 -->|OrderRequest| ES
    
    ES -->|Atomic Command| EH
    EH -->|REST| XC
    EH -->|Record| SL
```

## 2. Detailed Sequence Flow

Hier zien we de levenscyclus van een **TWAP Algo** (Algo A) en een **Stop Loss** (Algo B) die tegelijk draaien.

```mermaid
sequenceDiagram
    participant EB as EventBus
    participant EA as ExecutionAdapter
    participant ES as ExecutionService
    participant AA as Algo A (TWAP)
    participant AB as Algo B (StopLoss)
    participant EH as ExecutionHandler
    participant SL as StrategyLedger

    Note over EB, SL: SCENARIO 1: START TWAP (New Trade)

    EB->>EA: EXECUTION_DIRECTIVE_READY (TWAP)
    EA->>ES: start_algo(directive)
    ES->>ES: Create Algo A (TWAP)
    ES->>AA: on_start()
    
    AA->>AA: Calc chunks
    AA->>ES: place_order(Chunk 1)
    ES->>EH: execute_order(Chunk 1)
    EH->>SL: record_order()
    EH->>EB: ORDER_PLACED
    
    AA->>ES: schedule_timer(5 min)

    Note over EB, SL: SCENARIO 2: MARKET TICK (Update Stop Loss)

    EB->>EA: MARKET_TICK (Price Update)
    EA->>ES: handle_tick(tick)
    
    par Route to Algo A
        ES->>AA: on_tick(tick)
        AA->>AA: (No-Op for TWAP)
    and Route to Algo B
        ES->>AB: on_tick(tick)
        AB->>AB: Check Price vs Stop
    end

    Note over EB, SL: SCENARIO 3: TIMER EXPIRED (TWAP Next Chunk)

    ES->>AA: on_timer()
    AA->>ES: place_order(Chunk 2)
    ES->>EH: execute_order(Chunk 2)
    
    Note over EB, SL: SCENARIO 4: FILL RECEIVED (Iceberg Logic)

    EB->>EA: ORDER_FILLED (Fill for Chunk 2)
    EA->>ES: handle_fill(fill)
    ES->>ES: Lookup Algo (It's Algo A)
    ES->>AA: on_fill(fill)
    AA->>AA: Update state (filled += qty)
    
    Note over AA: Algo A is done?
    AA->>ES: finish("Done")
    ES->>SL: Close ExecutionGroup
```

## 3. Toelichting

1.  **De Adapter (EA):** Is de enige die de EventBus kent. Hij vertaalt events naar method calls op de Service.
2.  **De Service (ES):**
    *   Is de "Router". Bij een Tick roept hij *alle* relevante algo's aan. Bij een Fill roept hij *alleen* de eigenaar aan.
    *   Is de "Gateway". Alle orders van alle algo's gaan via de Service naar de Handler.
3.  **De Algo's (AA, AB):**
    *   Leven in hun eigen bubbel.
    *   Weten niet dat ze naast elkaar draaien.
    *   Reageren puur op hooks (`on_tick`, `on_timer`).

Dit diagram laat zien dat multipliciteit (Concurrency) volledig wordt gemanaged door de `ExecutionService`, zonder dat de rest van het systeem complexer wordt.
