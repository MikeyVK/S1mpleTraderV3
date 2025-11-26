# The Refined Role of ExecutionService

Nu de `TwapAlgo` zelf zijn protectie regelt (Integrated Protection), is de `ExecutionService` geen "Strategisch Coördinator" meer. Wat doet hij nog wel?

Hij is de **Infrastructure Host** (het "Besturingssysteem") voor de algoritmen.

## 1. Factory & Lifecycle Management
De Service is de enige die weet hoe een `ExecutionDirective` omgezet moet worden in een draaiend object.
*   **Instantiatie:** `if type == "TWAP": return TwapAlgo(params)`.
*   **Lifecycle:** Start de algo, houdt hem in leven, en ruimt hem op (`finish()`).
*   **Concurrency:** Beheert de collectie van *alle* actieve strategieën (BTC TWAP, ETH Iceberg, SOL Grid).

## 2. Event Routing (The Postman)
De Algo weet niet waar events vandaan komen. De Service regelt de bezorging.
*   **Fills:** De Service ontvangt *alle* fills van de exchange. Hij kijkt naar de `ClientOrderId`, zoekt de bijbehorende Algo, en roept `algo.on_fill()` aan.
*   **Timers:** De Service beheert de `Asyncio` timers en wekt de juiste Algo op het juiste moment.

## 3. Context & Resource Provisioning
De Algo heeft toegang nodig tot de buitenwereld, maar mag die niet direct aanraken (Dependency Injection).
*   De Service geeft de `ExecutionContext` mee:
    *   `context.execute_order()` -> Service stuurt naar Handler.
    *   `context.get_ledger()` -> Service geeft toegang tot state.

## 4. State Persistence (The Save Game)
De Algo is vluchtig (in memory). De Service garandeert persistentie.
*   Na elke `algo.on_event()` call, pakt de Service de `algo.state` en slaat deze op in de Ledger/Disk.
*   Bij een restart (crash/reboot) laadt de Service de state weer in en hervat de Algo.

## Conclusie
De **ExecutionService** is de **Container**.
De **Algo** is de **Content**.

Zonder de Service zou elke Algo zijn eigen event loop, websocket connectie en database logic moeten schrijven. De Service abstraheert al die "saaie" infrastructuur weg, zodat de Algo puur logica kan zijn.
