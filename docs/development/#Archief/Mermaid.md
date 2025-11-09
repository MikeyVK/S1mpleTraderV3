```mermaid
flowchart TB
    subgraph Platform["Platform Scope"]
        A[["Externe bronnen\n(APL_* events)"]] -->|publish| B(EventBus)
        B -->|persist| S[(EventStore)]
        B -->|notify| FI[FlowInitiator]
    end

    subgraph Strategy["Strategy Scope (per instance)"]
        FI -->|start_new_strategy_run<br> transforms event| Q{{EventQueue<br>(asyncio.Queue)}}
        subgraph QueueMgr["EventQueueManager"]
            Q
        end

        Q -->|dequeue (FIFO)| W1[Context Worker]
        W1 --> W2[Signal Worker]
        W2 --> W3[Planning Worker]
        W3 --> WT[FlowTerminator]

        WT -->|clear_cache\nmark processed| QC[(StrategyCache)]
        QC -.->|DTO access| W1
        QC -.-> W2
        QC -.-> W3
    end

    subgraph Monitoring["Platform Observers"]
        PM[PerformanceMonitor]
        AM[AuditLogger]
        RM[RiskAggregator]
    end

    Strategy -->|strategy events| B
    B -->|strategy scope events| PM
    B --> AM
    B --> RM

    classDef platform fill:#1f77b4,stroke:#0d3b66,color:#fff;
    classDef strategy fill:#2ca02c,stroke:#145a32,color:#fff;
    classDef queue fill:#ff7f0e,stroke:#b35400,color:#fff;
    class A,B,S,FI platform;
    class Q,W1,W2,W3,WT,QC strategy;
    class Q queue;
    class PM,AM,RM platform;
```