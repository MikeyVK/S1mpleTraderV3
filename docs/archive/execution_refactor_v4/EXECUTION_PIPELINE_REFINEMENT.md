# Execution Pipeline Refinement: EventAdapter & System Events

Dit document beschrijft de definitieve flow, strikt conform `EVENT_DRIVEN_WIRING.md`.

## 1. Het Principe: System Events voor Flow
We gebruiken **System Events** (via `Disposition.CONTINUE`) voor de koppeling tussen Planner en Worker. Dit garandeert unieke bedrading zonder dat de Worker hoeft te filteren.

## 2. De Flow: Planner -> Adapter -> Bus -> Adapter -> Worker

### Stap A: ExecutionPlanner (Producer)
De Planner doet zijn werk en signaleert "Ik ben klaar, ga door".

```python
class TwapPlanner(BaseExecutionPlanner):
    def process(self):
        # 1. Genereer Directive
        directive = self._generate_directive()
        
        # 2. Return CONTINUE (Flow Continuity)
        # Dit vertelt de Adapter: "Genereer een uniek System Event"
        return DispositionEnvelope(
            disposition="CONTINUE",
            payload=directive
        )
```

### Stap B: Planner EventAdapter (Generator)
De Adapter van de Planner ontvangt `CONTINUE`.
Hij genereert een uniek event: `_twap_planner_instance_1_output_{UUID}`.
Hij publiceert dit op de EventBus.

### Stap C: EventBus (Broadcaster)
De Bus is dom. Hij roept: "Hé, `_twap_planner_instance_1_output_{UUID}` is er!"

### Stap D: Worker EventAdapter (Listener)
De Adapter van de `TwapWorker` is (via de Strategy Builder) geconfigureerd om precies naar dit event te luisteren.

**Wiring Map (Generated):**
```yaml
wiring_rules:
  - source:
      component_id: "twap_planner_instance_1"
      event_name: "_twap_planner_instance_1_output_{UUID}" # Pattern match
    target:
      component_id: "twap_worker_instance_1"
      handler_method: "process_directive"
```

### Stap E: ExecutionWorker (Consumer)
De Worker wordt aangeroepen met de payload.
Hij hoeft **niets** te checken. Als hij wordt aangeroepen, is het voor hem.

```python
class TwapWorker(ExecutionWorker):
    def process_directive(self, directive: ExecutionDirective):
        # Geen filters. Gewoon uitvoeren.
        self.start_execution(directive)
```

## 3. Conclusie
1.  **EventBus Agnostisch:** Weet niets van types of routing. Broadcast alleen strings.
2.  **Worker Schoon:** Geen `if type != TWAP` logica.
3.  **Standard Design:** Dit is exact hoe `ContextWorkers` aan elkaar geknoopt worden (Sequential Flow).

We hebben de `ExecutionService` vervangen door standaard `EventAdapter` logica.
