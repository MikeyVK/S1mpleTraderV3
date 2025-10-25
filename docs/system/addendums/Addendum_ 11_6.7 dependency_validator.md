### **6.7. backend/assembly/dependency_validator.py**

Bestandsnaam: dependency_validator.py  
Plek in architectuur: Backend > Assembly  
Type: Validator  
Layer: Backend (Assembly)  
Dependencies: [backend.config.schemas, backend.assembly.plugin_registry, typing]  
Beschrijving: Systeembrede validator die garandeert dat data-afhankelijkheden tussen workers consistent zijn met de geconfigureerde executie-volgorde en strategieën van de operators.  
**Responsibilities:**

* Bouwt een complete data-afhankelijkheidsgrafiek voor alle workers in de strategie.  
* Analyseert de operator-configuratie (operators.yaml) en wiring_map.yaml om de executie-volgorde te bepalen.  
* Detecteert conflicten waar een data-afhankelijkheid bestaat tussen workers die (potentieel) parallel worden uitgevoerd.  
* Valideert de logische volgorde van ContextWorkers in een sequentiële pijplijn.  
* Voorkomt 'race conditions' door configuratiefouten tijdens de bootstrap-fase (Fail Fast).

```python
# backend/assembly/dependency_validator.py  
"""  
Contains the system-aware DependencyValidator.

@layer: Backend (Assembly)  
@dependencies: [backend.config.schemas, backend.assembly.plugin_registry, typing]  
@responsibilities:  
    - Builds a complete data dependency graph for all workers in the strategy.  
    - Analyzes operator configuration (operators.yaml) to determine execution strategies.  
    - Detects conflicts where a data dependency exists between workers that  
      are configured to run in parallel.  
    - Prevents configuration-induced race conditions during the bootstrap phase.  
"""  
from typing import List, Dict, Set, Any  
from backend.assembly.plugin_registry import PluginRegistry  
from backend.config.schemas.strategy_blueprint_schema import StrategyBlueprintConfig  
from backend.config.schemas.operators_schema import OperatorSuiteConfig

class DependencyValidator:  
    """  
    Validates the dataflow integrity across the entire workforce,  
    considering operator execution strategies.  
    """

    def __init__(self, plugin_registry: PluginRegistry):  
        """  
        Initializes the DependencyValidator.

        Args:  
            plugin_registry (PluginRegistry): The registry to fetch manifests from.  
        """  
        self._registry = plugin_registry

    def validate(  
        self,  
        blueprint: StrategyBlueprintConfig,  
        operator_config: OperatorSuiteConfig  
    ) -> None:  
        """  
        Validates the entire workforce for dependency and execution conflicts.

        Args:  
            blueprint (StrategyBlueprintConfig): The strategy blueprint defining the workforce.  
            operator_config (OperatorSuiteConfig): The configuration defining operator behavior.

        Raises:  
            ValueError: If a dependency conflict is found.  
        """  
        # Creëer een map van operator ID naar zijn execution strategy voor snelle lookup.  
        operator_strategies = {  
            op.operator_id: op.execution_strategy  
            for op in operator_config.operators  
        }

        # Bouw een map van elke worker naar zijn parent operator.  
        worker_to_operator_map = self._map_workers_to_operators(blueprint)

        # De initiële set van kolommen die beschikbaar is.  
        available_columns = {"open", "high", "low", "close", "volume"}

        # We verwerken de workers per operator-fase (conceptueel).  
        # We beginnen met de ContextWorkers.  
        context_workers = blueprint.workforce.context_workers  
        context_op_strategy = operator_strategies.get("ContextOperator", "SEQUENTIAL")

        if context_op_strategy == "SEQUENTIAL":  
            # Als de strategie sequentieel is, valideren we de keten stap voor stap.  
            self._validate_sequential_pipeline(context_workers, available_columns)  
        else: # PARALLEL  
            # Als de strategie parallel is, mogen er GEEN inter-dependencies zijn.  
            self._validate_parallel_execution(context_workers, "ContextOperator")

        # Update de beschikbare kolommen met alles wat de context-fase heeft geproduceerd.  
        for worker_config in context_workers:  
            manifest, _ = self._registry.get_plugin_data(worker_config.plugin)  
            if manifest.dependencies and manifest.dependencies.provides:  
                available_columns.update(manifest.dependencies.provides)

        # Valideer nu de volgende fases (Opportunity, Threat, etc.)  
        # Deze workers draaien na de context-fase en hebben toegang tot de 'available_columns'.  
        # Voorbeeld voor OpportunityWorkers:  
        opportunity_workers = blueprint.workforce.opportunity_workers  
        opportunity_op_strategy = operator_strategies.get("OpportunityOperator", "PARALLEL")

        if opportunity_op_strategy == "PARALLEL":  
            # Controleer of alle dependencies worden geleverd door de *vorige* (context) fase.  
            self._validate_parallel_dependencies(opportunity_workers, available_columns, "OpportunityOperator")  
        else: # SEQUENTIAL  
            self._validate_sequential_pipeline(opportunity_workers, available_columns.copy())  
              
        # ... Herhaal dit proces voor Threat, Planning, en Execution workers ...

    def _validate_sequential_pipeline(self, pipeline_configs: List[Any], initial_columns: Set[str]) -> None:  
        """Valideert een pijplijn die sequentieel wordt uitgevoerd."""  
        available = initial_columns.copy()  
        for worker_config in pipeline_configs:  
            manifest, _ = self._registry.get_plugin_data(worker_config.plugin)  
            if manifest.dependencies and manifest.dependencies.requires:  
                for dep in manifest.dependencies.requires:  
                    if dep not in available:  
                        raise ValueError(  
                            f"Sequential Dependency Error: Plugin '{worker_config.plugin}' requires '{dep}', "  
                            f"which is not provided by preceding workers. Available: {sorted(list(available))}"  
                        )  
            if manifest.dependencies and manifest.dependencies.provides:  
                available.update(manifest.dependencies.provides)

    def _validate_parallel_execution(self, worker_configs: List[Any], operator_id: str) -> None:  
        """  
        Valideert dat er geen onderlinge afhankelijkheden zijn tussen workers  
        die parallel worden uitgevoerd binnen dezelfde operator.  
        """  
        all_provides = set()  
        for worker_config in worker_configs:  
            manifest, _ = self._registry.get_plugin_data(worker_config.plugin)  
            if manifest.dependencies and manifest.dependencies.provides:  
                all_provides.update(manifest.dependencies.provides)

        for worker_config in worker_configs:  
            manifest, _ = self._registry.get_plugin_data(worker_config.plugin)  
            if manifest.dependencies and manifest.dependencies.requires:  
                for dep in manifest.dependencies.requires:  
                    if dep in all_provides:  
                        raise ValueError(  
                            f"Configuration Conflict in '{operator_id}': "  
                            f"Execution strategy is PARALLEL, but a dependency exists. "  
                            f"Plugin '{worker_config.plugin}' requires '{dep}', which is provided by another "  
                            f"worker within the same parallel group. This is not allowed."  
                        )

    def _validate_parallel_dependencies(self, worker_configs: List[Any], available_columns: Set[str], operator_id: str) -> None:  
        """  
        Valideert dat alle dependencies voor een parallelle groep workers  
        al beschikbaar zijn *voordat* de groep start.  
        """  
        for worker_config in worker_configs:  
            manifest, _ = self._registry.get_plugin_data(worker_config.plugin)  
            if manifest.dependencies and manifest.dependencies.requires:  
                for dep in manifest.dependencies.requires:  
                    if dep not in available_columns:  
                        raise ValueError(  
                            f"Dependency Error in '{operator_id}': Plugin '{worker_config.plugin}' requires '{dep}', "  
                            f"but it is not available from the preceding sequential phases (e.g., Context phase)."  
                        )

    def _map_workers_to_operators(self, blueprint: StrategyBlueprintConfig) -> Dict[str, str]:  
        """Creëert een mapping van plugin naam naar de ID van de beherende operator."""  
        mapping = {}  
        for worker in blueprint.workforce.context_workers:  
            mapping[worker.plugin] = "ContextOperator"  
        for worker in blueprint.workforce.opportunity_workers:  
            mapping[worker.plugin] = "OpportunityOperator"  
        # ... etc. for all worker types ...  
        return mapping  
```