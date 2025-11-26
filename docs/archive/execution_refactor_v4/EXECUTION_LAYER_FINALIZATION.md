# Execution Layer Finalization: Service as Handler

Dit document formaliseert de laatste architecturale stap: **De ExecutionHandler verdwijnt.**

## 1. De Nieuwe Realiteit
De `ExecutionService` heeft alle coördinerende taken overgenomen. De `ExecutionHandler` is gereduceerd tot een lege huls die alleen maar doorgeeft.

### De Oude Flow
`Service` -> `Handler` (ID Gen, Ledger, Causality) -> `Connector` (IO)

### De Nieuwe Flow
`Service` -> `Connector` (IO)
`Service` -> `Ledger` (State, IDs)

## 2. Verantwoordelijkheden van de ExecutionService
De Service is nu de **De Facto Handler**.

1.  **IO (via Connector):**
    *   De Service roept direct `connector.place_order()` aan.
    *   De Service ontvangt direct replies (via Adapter).
2.  **State (via Ledger):**
    *   De Service vraagt de Ledger om nieuwe Order IDs.
    *   De Service update de Ledger met `record_order` en `record_fill`.
3.  **Causality:**
    *   De Service weet welke `ExecutionDirective` (en dus welk Plan) aan de basis ligt.
    *   Hij koppelt de gegenereerde Order IDs aan de Causality Chain.

## 3. Stateless Algorithms & Ledger Interaction
De zorg over "Stateful Algos" lossen we op door de Ledger als **Single Source of Truth** te gebruiken.

### Het Model
1.  **Algo Logic:** Is stateless.
    *   `algo.evaluate(context)`
2.  **Context:** Is de interface naar de Ledger.
    *   `context.state` is een proxy voor `ledger.get_execution_group_state(group_id)`.
3.  **Flow:**
    *   Service laadt state uit Ledger -> `context`.
    *   Algo doet zijn ding -> update `context`.
    *   Service slaat `context` weer op in Ledger.

### Concreet: TWAP State
*   De variabele `remaining_slices` leeft niet in de Algo instance.
*   Hij leeft in de `ExecutionGroup.metadata` in de Ledger.
*   Bij een restart haalt de Service die metadata op, en de Algo gaat verder waar hij gebleven was.

## 4. Conclusie
We hebben de architectuur platgeslagen ("Platgeslagen Orkestratie"):
*   **Geen ExecutionHandler meer.**
*   **ExecutionService** is de spin in het web.
*   **ExecutionConnector** is de domme IO worker.
*   **StrategyLedger** is het geheugen.

Dit is de meest efficiënte en robuuste opzet.
