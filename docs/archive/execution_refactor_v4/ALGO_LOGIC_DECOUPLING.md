# Algo Logic Decoupling: From Event-Aware to State-Aware

Dit document adresseert het fundamentele probleem: *"Algos mogen niet Event-Aware zijn."*

## 1. De Omslag: Van Event-Driven naar State-Based
We stappen af van het idee dat een Algo reageert op een *Event* (`on_news_event`).
We gaan terug naar de kernfilosofie van S1mpleTraderV3: **Point-in-Time State**.

### Het Nieuwe Model
1.  **Events** (Ticks, Fills, News) zijn puur **State Updates**.
2.  De **ExecutionService** ontvangt events en update de **Execution Context**.
3.  De **Algo** is een pure **State Machine** die naar de Context kijkt.

## 2. De Nieuwe Interface: `evaluate()`
De Algo kent geen events. Hij kent alleen:
1.  **Context:** De huidige waarheid (Prijs, Volume, Orders, Nieuws).
2.  **State:** Zijn eigen voortgang (Gevuld, Timer).

```python
class BaseExecutionAlgorithm(ABC):
    def evaluate(self, context: ExecutionContext) -> List[Command]:
        """
        Kijk naar de context.
        Kijk naar je eigen state.
        Beslis wat te doen.
        """
        pass
```

## 3. Hoe werkt de Flow?

### Scenario: POV (Percentage of Volume)
1.  **Configuratie:** StrategyBuilder kiest POV. POV Algo declareert: `triggers = [MARKET_UPDATE]`.
2.  **Event:** `MARKET_TICK` komt binnen bij Adapter.
3.  **Service (The Updater):**
    *   Update `context.market_data` (Volume, Prijs).
    *   Ziet dat POV getriggerd wordt door Market Updates.
    *   Roept `algo.evaluate(context)`.
4.  **Algo (The Logic):**
    *   Leest `context.market_data.volume`.
    *   Berekent: "Is volume > threshold?"
    *   Return: `PlaceOrderCommand` of `None`.

### Scenario: Nieuws Sentiment
1.  **Event:** `NEWS_EVENT` komt binnen.
2.  **Service:**
    *   Update `context.sentiment` (Nieuwe data!).
    *   Roept `algo.evaluate(context)` (als de algo dat wil).
3.  **Algo:**
    *   Leest `context.sentiment`.
    *   Besluit: "Sentiment slecht -> Cancel Orders".

## 4. Waarom dit beter is
1.  **Decoupling:** De Algo weet niet of de data van een Websocket, een REST call of een CSV file kwam. Hij ziet alleen `context.sentiment`.
2.  **Testbaarheid:** Je kunt een Algo testen door gewoon een `MockContext` te geven en `evaluate()` te roepen. Geen events simuleren.
3.  **Consistentie:** Dit is exact het **Point-in-Time** model van de rest van het platform.

## 5. De Rol van de StrategyBuilder
De StrategyBuilder bepaalt de **Relatie**:
*   Strategie X gebruikt Algo Y.
*   Algo Y heeft Data Z nodig.
*   Het Platform (Service) garandeert dat Data Z in de Context zit en dat `evaluate()` wordt aangeroepen als Z verandert.

De Algo is nu weer "Pure Logica".
