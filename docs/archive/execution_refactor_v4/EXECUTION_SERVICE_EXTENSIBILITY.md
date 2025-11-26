# Execution Service Extensibility: Generic Event Routing

Dit document adresseert de zorg: *"Wat als een nieuw algo een event nodig heeft dat de ExecutionService nog niet kent?"*

## 1. Het Probleem: Hardcoded Routing
Als de `ExecutionService` expliciete methodes heeft zoals `handle_tick()` en `handle_fill()`, dan moet je bij elk nieuw event type (bijv. `handle_news()`) de Service aanpassen. Dit is een **Open/Closed violation**.

## 2. De Oplossing: Generic Routing
We maken de `ExecutionService` en de `BaseExecutionAlgorithm` **Event-Agnostisch** voor de routing.

### A. De Adapter (The Gateway)
De Adapter luistert naar *alles* wat relevant is (geconfigureerd in `manifest.yaml`).
Hij roept één generieke methode aan op de Service.

```python
class ExecutionAdapter:
    def on_any_event(self, event_name, payload):
        # Stuur alles door naar de service
        self.service.dispatch_event(event_name, payload)
```

### B. De Service (The Transparent Router)
De Service kijkt niet naar *wat* het event is, maar stuurt het door naar alle actieve algo's.

```python
class ExecutionService:
    def dispatch_event(self, event_name: str, payload: Any):
        # 1. Loop door alle actieve algo's
        for group_id, algo in self.active_algos.items():
            
            # 2. Vraag: "Ben jij geïnteresseerd?"
            if algo.is_interested_in(event_name):
                algo.on_event(event_name, payload)
```

### C. De Base Algo (The Filter)
De `BaseExecutionAlgorithm` heeft een slimme dispatch logic.

```python
class BaseExecutionAlgorithm(ABC):
    # Default interests (kan overridden worden)
    interests = {"MARKET_TICK", "ORDER_FILLED"}

    def is_interested_in(self, event_name):
        return event_name in self.interests

    def on_event(self, event_name, payload):
        # Dynamische dispatch naar on_X methodes
        handler_name = f"on_{event_name.lower()}"
        if hasattr(self, handler_name):
            getattr(self, handler_name)(payload)
```

## 3. Scenario: Nieuw "NEWS_EVENT" toevoegen

Stel we willen een `NewsSentimentAlgo` toevoegen.

1.  **Nieuwe Algo Class:**
    ```python
    class NewsSentimentAlgo(BaseExecutionAlgorithm):
        interests = {"NEWS_EVENT"} # Ik wil nieuws!

        def on_news_event(self, payload):
            if payload.sentiment < -0.5:
                self.place_order(...)
    ```
2.  **Manifest Update:**
    Voeg `NEWS_EVENT` toe aan de `wirings` van de ExecutionAdapter.

**Resultaat:**
*   De Adapter ontvangt `NEWS_EVENT`.
*   De Service ontvangt `dispatch_event("NEWS_EVENT", ...)`.
*   De Service stuurt het door.
*   De `NewsSentimentAlgo` pakt het op.
*   De `TwapAlgo` negeert het (want `NEWS_EVENT` zit niet in zijn interests).

**Conclusie:**
De `ExecutionService` hoeft **niet** aangepast te worden. Hij is een "Dumb Pipe" geworden voor events.
