# Manifest-Driven Execution: The Worker Pattern

Dit document herontwerpt de executie-laag op basis van de feedback: **De ExecutionService is redundant.** We gebruiken de bestaande **Worker & Manifest** infrastructuur.

## 1. Het Concept: Self-Selecting Workers
In plaats van een centrale Service die taken uitdeelt, gebruiken we **EventDrivenWorkers** die zelf bepalen of ze een taak oppakken (het **Filter Pattern**).

*   **Trigger:** `EXECUTION_DIRECTIVE_READY` event.
*   **Filter:** `if directive.execution_plan.algo_type == my_manifest.subtype`.
*   **Action:** Start executie.

## 2. De Standard Manifest (Conform PLUGIN_ANATOMY.md)
We gebruiken **geen** verzonnen velden. We gebruiken de standaard `identification` en `capabilities`.

```yaml
identification:
  name: "twap_algo"
  type: "execution_algorithm"  # Nieuw Worker Type (moet in Taxonomy)
  subtype: "TWAP"              # De Match Key
  version: "1.0.0"
  description: "Time Weighted Average Price execution"

dependencies:
  requires_dtos: [] # Haalt data via Providers, niet via DTO flow
  produces_dtos: []

capabilities:
  # Standard Access
  context_access:
    enabled: true
  
  # State Management (Cruciaal voor Algos)
  state_persistence:
    enabled: true
    scope: "strategy"

  # IO Access
  ledger_state:
    enabled: true  # Toegang tot ExecutionGroups
  
  # Event Wiring (De Trigger)
  events:
    enabled: true
    wirings:
      - listens_to: "EXECUTION_DIRECTIVE_READY"
        invokes:
          method: "evaluate_directive"
          requires_payload: true
      - listens_to: "TIMER_TICK"
        invokes:
          method: "on_timer"
      - listens_to: "ORDER_FILLED"
        invokes:
          method: "on_fill"
```

## 3. De Relatie met ExecutionIntentPlanner (RoutingPlanner)
De `ExecutionIntentPlanner` (voorheen RoutingPlanner) bepaalt de strategie.

1.  **Planner:** Genereert `ExecutionIntent` (Urgency, Visibility).
2.  **Translator/Aggregator:** Vertaalt Intent naar concreet `algo_type="TWAP"` in de `ExecutionDirective`.
3.  **Worker (TwapAlgo):** Ziet `algo_type="TWAP"` en activeert.

## 4. Implementatie: The Filter Logic
De `ExecutionAlgorithm` base class implementeert de filter logica.

```python
class ExecutionAlgorithm(EventDrivenWorker):
    def evaluate_directive(self, payload: ExecutionDirective):
        # 1. Filter: Is dit voor mij?
        target_type = payload.execution_plan.algo_type
        my_type = self.manifest.identification.subtype
        
        if target_type != my_type:
            return DispositionEnvelope(disposition="IGNORE")

        # 2. Accept: Initialiseer State
        self.initialize_execution(payload)
        return DispositionEnvelope(disposition="ACKNOWLEDGED")
```

## 5. Conclusie
*   **Geen ExecutionService:** De Platform WorkerHost draait de plugins.
*   **Geen Custom Router:** De EventBus + Filter Logic doet de routing.
*   **Standard Compliance:** We volgen 100% de `PLUGIN_ANATOMY.md`.

Dit is de "Slimme Oplossing": De infrastructuur is er al, we hoeven het alleen maar te gebruiken.
