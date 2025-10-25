# **Addendum: 3.8 Configuratie en Vertaal Filosofie v2.1**

Dit addendum beschrijft een fundamentele verfijning van de S1mpleTrader-architectuur, gericht op het versterken van het Single Responsibility Principle (SRP) tijdens het opstarten en uitvoeren van strategieën. Het introduceert een heldere hiërarchie van configuratielagen en een centrale vertaalslag, wat de OperationService transformeert tot een pure levenscyclus-manager.

## **1. Impact op Bestaande Documentatie**

Deze nieuwe filosofie heeft een significante impact op de conceptuele beschrijving van de orkestratie in de gehele documentatieset. De volgende secties in de originele documenten zijn door dit addendum achterhaald en moeten worden gelezen in de context van deze nieuwe architectuur.

### **Hoofdstuk 1: 1_BUS_COMMUNICATION_ARCHITECTURE.md**

* **Paragraaf 1.5. De Levenscyclus in de Praktijk**:
  * De sub-paragraaf **De Bootstrap Fase** is volledig vervangen door de nieuwe, meer gedetailleerde fases (Hydratatie, Assemblage, Bedrading) die worden georkestreerd door de OperationService en zijn specialisten. De oude beschrijving van de ContextBootstrapper en EventWiringFactory is niet langer correct.

### **Hoofdstuk 2: 2_ARCHITECTURE.md**

* **Paragraaf 2.3. De Gelaagde Architectuur**:
  * De beschrijving van de **SERVICE LAAG** is onvolledig. De rol van de OperationService als de enige, centrale orkestrator en levenscyclus-manager is hierin niet adequaat beschreven.
* **Paragraaf 2.10. Componenten in Detail**:
  * De sub-paragraaf **Assembly Components** is grotendeels achterhaald. De ContextBuilder bestaat niet meer in die vorm. De interactie en verantwoordelijkheden van de OperatorFactory, WorkerBuilder (WorkerFactory), en andere assemblage-componenten worden nu direct aangestuurd door de OperationService op basis van BuildSpecs.
* **Paragraaf 2.11. Dataflow & Orchestratie**:
  * De beschrijving van de opstart-dataflow en de rol van de ContextBuilder is incorrect. De OperationService is nu de start van alle orkestratie.

### **Hoofdstuk 3: 3_DE_CONFIGURATIE_TREIN.md**

* **Paragraaf 3.8. De Onderlinge Samenhang - De "Configuratie Trein" in Actie**:
  * Deze paragraaf is **volledig vervangen** door de filosofie in dit addendum. De oude beschrijving van hoe Operations de bestanden koppelt en de ContextBuilder aanroept, is achterhaald.
* **Concepten operators.yaml en wiring_map.yaml als globale bestanden**:
  * Onze nieuwe filosofie stelt dat deze configuraties onderdeel zijn van de StrategyConfig (afkomstig uit strategy_blueprint.yaml), en dus niet globaal. De paragrafen 3.3.2, 3.3.6 en 3.3.7 moeten in dit licht herzien worden.

## **2. De Architectuurfilosofie**

Dit document beschrijft de fundamentele filosofie achter de configuratiestructuur en het vertaalproces van S1mpleTrader. Het definieert een heldere hiërarchie om een perfecte scheiding van verantwoordelijkheden (SRP) te garanderen.

### **2.1. De Drie Gescheiden Configuratielagen**

Om SRP te waarborgen, splitsen we de configuratie op in drie strikt gescheiden lagen, elk met een eigen doel en levenscyclus.

#### **Laag 1: PlatformConfig (De Fundering)**

* **Doel:** Bevat alle **globale, statische en run-onafhankelijke** configuratie van het platform. Dit is de context waarin *alle* operaties draaien.
* **Bron:** platform.yaml.
* **Inhoud:** Logging-instellingen, paden (zoals plugins_root_path), taalinstellingen.
* **Levenscyclus:** Wordt **één keer** geladen bij de start van de OperationService.
* **Belangrijk:** Deze laag bevat **geen** connectors, data_sources, environments of schedules. Deze zijn operationeel van aard.

#### **Laag 2: OperationConfig (De Werkruimte)**

* **Doel:** Definieert een specifieke "werkruimte" of "campagne". Het groepeert alle technische middelen (connectors, data_sources, environments), de te draaien strategieën (strategy_links) en de timing (schedule).
* **Bron:** Het operation.yaml bestand zelf, plus de bestanden waarnaar het verwijst (connectors.yaml, data_sources.yaml, environments.yaml, schedule.yaml).
* **Inhoud:**
  * De volledige definitie van alle beschikbare connectors, data-bronnen en environments voor *deze specifieke operatie*.
  * De scheduler-configuratie voor deze specifieke operatie.
  * De lijst van strategy_links die de OperationService moet uitvoeren.
* **Levenscyclus:** Wordt geladen wanneer de OperationService een specifieke operatie start.

#### **Laag 3: StrategyConfig (De Blauwdruk)**

* **Doel:** Vertegenwoordigt de volledige, **gebruikersvriendelijke intentie** voor één specifieke, uit te voeren strategie-instantie.
* **Bron:** Wordt per strategy_link samengesteld uit het corresponderende strategy_blueprint.yaml.
* **Inhoud:** De workforce, en de strategie-specifieke operator_config en wiring_config.
* **Levenscyclus:** Wordt "just-in-time" geladen binnen de start_strategy methode voor elke strategie die wordt opgestart.

$$Afbeelding van drie gestapelde lagen: Platform, Operation, Strategy$$

### **2.2. Specialisten voor Laden en Valideren**

Om deze lagen schoon te houden, definiëren we gespecialiseerde componenten voor het laden en valideren. Dit zijn **backend-componenten**, geen services.

#### **config/loader.py met ConfigLoader**

Deze klasse heeft nu drie duidelijke, SRP-conforme methoden:

1. **load_platform_config() -> PlatformConfig:** Laadt en valideert de schema van platform.yaml.
2. **load_operation_config(operation_name) -> OperationConfig:** Laadt het operation.yaml en de bijbehorende connectors.yaml, data_sources.yaml, environments.yaml en schedule.yaml.
3. **load_strategy_config(blueprint_id) -> StrategyConfig:** Laadt het specifieke strategy_blueprint.yaml.

#### **config/validator.py met ConfigValidator**

Deze klasse valideert de *consistentie* tussen en binnen de geladen configuratie-objecten.

1. **validate_platform_config(platform_config):** Valideert de PlatformConfig. Controleert basisinstellingen zoals of de gedefinieerde paden bestaan.
2. **validate_operation_config(operation_config):** Valideert de OperationConfig. Controleert bijvoorbeeld of de connector_id in een environment ook daadwerkelijk is gedefinieerd in connectors.yaml.
3. **validate_strategy_config(strategy_config, operation_config):** Valideert de StrategyConfig *binnen de context van de operatie*. Cruciaal, want hier controleert het of de execution_environment_id van een strategy_link ook echt bestaat in de OperationConfig.

### **2.3. De Centrale Vertaler: config/translator.py**

De ConfigTranslator (in translator.py) is de specialist die de brug slaat tussen de gebruikersintentie en de machine-instructies.

* **Single Responsibility:** Zijn enige taak is het vertalen van de configuratielagen naar een collectie van machine-instructies.
* **Methode:** collect_build_specs(strategy_config, platform_config, operation_config) -> BuildSpecCollection.

**Wat heeft de translator nodig?**

1. **StrategyConfig:** De primaire input. Bevat de workforce en strategie-specifieke orkestratie die vertaald moet worden.
2. **PlatformConfig:** Nodig voor globale context, zoals paden (plugins_root_path) om de manifesten van de plugins te kunnen vinden en lezen.
3. **OperationConfig:** Essentieel om de execution_environment_id van de strategie te kunnen opzoeken en te bepalen welke connector of data_source gebouwd moet worden.

De translator ontvangt dus alle drie de configuratielagen en gebruikt deze om één complete BuildSpecCollection te genereren.

### **2.4. Factories als "Domme" Specialisten**

De BuildSpecs maken elke factory radicaal eenvoudiger en 100% SRP-conform.

* **De Workflow:** De OperationService roept een factory aan en geeft hem alleen zijn eigen, specifieke BuildSpec (bv. persistor_factory.build_from_spec(build_specs.persistor_spec)).
* **De Logica van de Factory:** De factory hoeft niet meer door complexe configuraties te bladeren. Hij ontvangt een simpele DTO met een duidelijke opdracht (bv. "bouw een state persistor voor worker X en Y") en voert deze blindelings uit. Hij is een pure, "domme" uitvoerder geworden.

Deze aanpak garandeert dat de OperationService een pure dirigent blijft, de ConfigTranslator de enige denker is, en de factories pure bouwers zijn.

## **3. De Verfijnde OperationService als Levenscyclus-Manager**

Met deze heldere structuur wordt de OperationService een pure levenscyclus-manager ("state machine") voor actieve strategie-instanties.

**Bij de Initialisatie van de OperationService:**

1. Initialiseer alle **backend-componenten** en **singleton-services**:
    * **Configuratie-specialisten:** ConfigLoader, ConfigValidator, ConfigTranslator.
    * **Platform-Singletons:** Scheduler, AggregatedLedger, MultiTimeframeProvider, PluginRegistry, DependencyValidator.
    * **Alle Factories:** PersistorFactory, ConnectorFactory, DataSourceFactory, EnvironmentFactory, WorkerFactory, OperatorFactory, EventAdapterFactory, EventWiringFactory.
2. Laad de platform_config en operation_config en valideer deze.
3. Houd een interne dictionary bij: self.actieve_strategieen: Dict[str, StrategieInstantie] = {}.

**De Levenscyclus Methoden:**

* **start_all_strategies()**
  * Ittereert door de strategy_links in de operation_config.
  * Roept voor elke link self.start_strategy(strategy_link) aan.
* **start_strategy(strategy_link) -> strategy_instance_id**
  * Dit is de **enige, universele en atomaire startprocedure**.
  * **Stap 1: Laden & Valideren:**
    * strategy_config = config_loader.load_strategy_config(strategy_link.blueprint_id)
    * config_validator.validate_strategy_config(strategy_config, operation_config)
  * **Stap 2: Vertalen:**
    * build_specs = config_translator.collect_build_specs(strategy_config, platform_config, operation_config)
  * **Stap 3: Assembleren & Starten (de "Factory Chain"):**
    * **A: Bouw Technische Bronnen:**
      * connector_map = connector_factory.build_from_spec(build_specs.connector_spec)
      * data_source_map = data_source_factory.build_from_spec(build_specs.data_source_spec)
    * **B: Bouw de Omgeving:**
      * environment = environment_factory.build_from_spec(build_specs.environment_spec, connectors=connector_map, data_sources=data_source_map)
    * **C: Bouw Strategie-Componenten:**
      * persistor_map = persistor_factory.build_from_spec(build_specs.persistor_spec)
      * event_handler_map = event_adapter_factory.build_from_spec(build_specs.event_handler_spec)
      * worker_instances = worker_factory.build_from_spec(build_specs.workforce_spec, persistor_map, event_handler_map)
      * operator_map = operator_factory.build_from_spec(build_specs.operator_spec, worker_instances)
    * **D: Bedraad het Systeem:**
      * event_wiring_factory.wire_all_from_spec(build_specs.wiring_spec, operator_map, worker_instances, event_bus)
    * **E: Start de Executie:**
      * environment.start()
  * **Stap 4: Registreer Instantie:**
    * Creëer een StrategieInstantie-object met alle gebouwde componenten en de status 'Running'.
    * Voeg toe aan self.actieve_strategieen.
    * Retourneer de unieke ID van deze instantie.
* **stop_strategy(strategy_instance_id)**
  * Zoekt de StrategieInstantie op.
  * Roept environment.stop() aan en geeft alle resources vrij.
  * Verandert de status naar Stopped.
* **restart_strategy(strategy_instance_id)**
  * Roep stop_strategy() aan.
  * Roep start_strategy() aan met de originele strategy_link.
* **get_strategy_status(strategy_instance_id)**
  * Zoekt de StrategieInstantie op.
  * Retourneert de status (Running, Stopped, Error) en eventuele relevante runtime-statistieken (bv. PnL, aantal trades) uit de StrategyLedger.

## **4. Scenario Toetsing: Dynamisch Strategieën Toevoegen**

Laten we de huidige filosofie toetsen aan het scenario dat je schetst.

* **Scenario:** De OperationService draait. In de Web UI bouwt een gebruiker een nieuwe strategie. Deze strategie gebruikt een connector die wel bestaat, maar nog niet is opgenomen in de connectors.yaml van de *huidige*, draaiende operatie. De gebruiker klikt op 'Run strategy'.

**Analyse:**

1. **UI Actie:** De Web UI stuurt een verzoek naar de backend. Dit verzoek bevat idealiter niet alleen de nieuwe strategy_link, maar ook de benodigde aanpassingen aan de OperationConfig (de nieuwe connector definitie).
2. **Backend Trigger:** Een API-endpoint roept een nieuwe, speciale methode aan op de OperationService, bijvoorbeeld add_strategy_dynamically(new_strategy_link, new_connector_config).
3. **Het Knelpunt:** De OperationService heeft een operation_config in het geheugen die **verouderd** is. De validate_strategy_config methode (stap 1 van start_strategy) zal falen, omdat de execution_environment_id van de nieuwe strategie verwijst naar een connector_id die niet bestaat in de *huidige, in-memory* OperationConfig.

**Conclusie van de Toetsing:**

**Nee, met de huidige opzet gaat het laden niet goed.** De filosofie is perfect voor het opstarten en beheren van een *statische* set strategieën, maar mist een mechanisme voor het **dynamisch aanpassen van de operationele context (de OperationConfig)** terwijl de service draait.

**De Oplossing: Een "Hot-Reload" Mechanisme**

Om dit scenario te ondersteunen, moet de OperationService worden uitgebreid met de mogelijkheid om zijn eigen context te vernieuwen.

De add_strategy_dynamically-methode zou de volgende stappen moeten doorlopen:

1. **Persisteer de Wijziging:** Schrijf de nieuwe connector-configuratie naar het connectors.yaml-bestand op schijf. Voeg de nieuwe strategy_link toe aan het operation.yaml-bestand.
2. **Herlaad de Operationele Context:** Roep intern self.config_loader.load_operation_config() opnieuw aan om de bijgewerkte OperationConfig in het geheugen te laden.
3. **Valideer de Nieuwe Context:** Roep self.config_validator.validate_operation_config() aan om de nieuwe, complete configuratie te valideren.
4. **Start de Nieuwe Strategie:** Roep nu de reguliere, universele self.start_strategy(new_strategy_link) aan. Deze zal nu slagen, omdat de OperationConfig up-to-date is en de benodigde connector kent.

Deze aanpak behoudt de uniformiteit van het start_strategy-proces, maar voegt een cruciale stap toe voor het beheren van de dynamische, langlevende OperationService zelf.

## **5. Stresstest: De Architectuur Getoetst aan Geavanceerde Quant-Scenario's**

Dit document test de robuustheid en flexibiliteit van de S1mpleTrader-architectuur door deze te confronteren met een reeks geavanceerde, realistische scenario's die een kwantitatieve strateeg zou willen implementeren via de Web UI.

### **Scenario 1: De "Smart DCA" Strategie**

* **Doel van de Quant:** "Ik wil een Dollar Cost Averaging (DCA) strategie bouwen die elke maandag om 10:00 uur een aankoop doet, maar **alleen als** de marktcondities gunstig zijn. Een OpportunityWorker moet de 'koopkans' scoren, en een ThreatWorker moet het risico beoordelen. Alleen als de kans hoog is en het risico laag, mag de aankoop doorgaan."
* **Architecturale Toets:** Dit scenario test de kern van de event-driven capaciteiten van het systeem. Het vereist:
  1. Een systeembrede Scheduler die een WEEKLY_TICK event publiceert.
  2. Twee onafhankelijke workers (dca_opportunity_scorer en dca_risk_assessor) die **parallel** op hetzelfde WEEKLY_TICK event reageren.
  3. Een derde worker (adaptive_dca_planner) die moet **wachten** tot de *beide* voorgaande workers hun werk hebben gedaan en hun respectievelijke events (OPPORTUNITY_SCORED en RISK_ASSESSED) hebben gepubliceerd.
  4. Een ExecutionWorker die pas getriggerd wordt als de adaptive_dca_planner het definitieve DCA_PLAN_READY event publiceert.
* **Het Oordeel: ✅ Geslaagd met Vlag en Wimpel**
  De architectuur is hier perfect voor ontworpen.
  * **ROL & CAPABILITIES:** De scorer, assessor en planner worden geïmplementeerd als EventDrivenWorker en vragen de events capability aan in hun manifest.
  * **CONFIGURATIE:** De strategy_blueprint.yaml legt de event-keten vast. De adaptive_dca_planner gebruikt de requires_all: true eigenschap in zijn event-configuratie.
  * **VALIDATIE:** De EventChainValidator controleert tijdens de bootstrap-fase of deze complexe "fan-in" event-keten logisch is en geen doodlopende paden bevat.

De scheiding van Scheduler (platform-singleton) en de strategie-specifieke workers zorgt voor een schone implementatie.

[Afbeelding van een 'fan-in' data flow diagram]

### **Scenario 2: De "Portfolio Heatmap" (Overkoepelend Risicobeheer)**

* **Doel van de Quant:** "Ik draai drie strategieën tegelijk: een voor BTC, een voor ETH, en een voor SOL. Ik wil een 'noodrem'-mechanisme bouwen. Als de **totale drawdown van mijn hele portfolio** (alle strategieën bij elkaar) boven de 15% komt, wil ik dat *alle* strategieën onmiddellijk stoppen met het openen van nieuwe posities en hun risico verlagen."
* **Architecturale Toets:** Dit is een cruciale test voor de scheiding tussen geïsoleerde StrategieInstanties en gedeelde Platform-Singleton Services. Het vereist:
  1. Een AggregatedLedger (singleton) die luistert naar de LedgerStateChanged-events van **alle** actieve strategieën en het totale portfolio-risico berekent.
  2. De mogelijkheid voor deze AggregatedLedger om een **systeembreed PORTFOLIO_RISK_HIGH event** te publiceren.
  3. Een ThreatWorker binnen **elke** actieve StrategieInstantie die zich kan abonneren op dit systeembrede event.
  4. De mogelijkheid voor deze ThreatWorker om de interne werking van zijn eigen strategie te beïnvloeden (bv. door een intern STRATEGY_HALT event te publiceren).
* **Het Oordeel: ✅ Geslaagd**
  De architectuur ondersteunt dit scenario elegant.
  * **SINGLETONS:** De AggregatedLedger wordt één keer geïnitialiseerd door de OperationService en is beschikbaar voor alle componenten.
  * **CENTRALE EVENTBUS:** De enkele, gedeelde EventBus maakt communicatie mogelijk tussen platform-services en strategie-instanties. Events kunnen systeembreed zijn (zonder strategy_link_id) of specifiek.
  * **DEPENDENCY INJECTION:** Een ThreatWorker kan via zijn manifest een dependency op de AggregatedLedger aanvragen om direct de status te kunnen bevragen, of hij kan luisteren naar de events die de AggregatedLedger publiceert.

Dit toont de kracht aan van het hebben van een gedeelde service-laag die over de geïsoleerde strategie-instanties heen opereert.

### **Scenario 3: De "Multi-Asset Arbitrage" Strategie**

* **Doel van de Quant:** "Ik wil een arbitrage-strategie bouwen die continu de prijzen van BTC/EUR op Kraken en BTC/EUR op Binance vergelijkt. Als er een significant prijsverschil is, wil ik op de ene exchange kopen en op de andere verkopen."
* **Architecturale Toets:** Dit scenario test of een **enkele StrategieInstantie** tegelijkertijd data kan ontvangen, verwerken en acteren op basis van meerdere, onafhankelijke databronnen (connectors).
  1. Kan de EnvironmentFactory een "gecombineerde" environment bouwen die data van twee connectors ontvangt?
  2. Kan een ContextWorker een TradingContext verwerken die data van twee assets bevat?
  3. Kan een ExecutionWorker orders naar twee verschillende connectors sturen?
* **Het Oordeel: ⚠️ Geslaagd, maar vereist een aanpassing (Zwakke Plek Blootgelegd)**
  De huidige architectuur, zoals beschreven, stuit hier op een grens. Het TradingContext object is ontworpen rond één asset_pair. Een ExecutionEnvironment is gekoppeld aan één connector of data_source.
  **Echter, de architectuur is flexibel genoeg om dit op te lossen:**
  1. **DE OPLOSSING:** We introduceren een nieuwe MultiAssetEnvironment. Deze environment wordt door de EnvironmentFactory gebouwd en krijgt **meerdere connectors** geïnjecteerd.
  2. In plaats van één ContextReady-event met één TradingContext, publiceert deze environment voor elke tick twee aparte events, bv. KrakenContextReady en BinanceContextReady.
  3. De ArbitrageOpportunityWorker wordt een EventDrivenWorker die zich op **beide** events abonneert. Hij slaat de data intern op en vergelijkt de prijzen zodra hij van beide exchanges een update heeft ontvangen.
  4. De ExecutionWorker krijgt de connector_map geïnjecteerd, zodat hij de execute-methode op de juiste connector kan aanroepen.

**Conclusie van de test:** De basisbouwstenen zijn robuust, maar dit scenario toont aan dat we een **gespecialiseerde ExecutionEnvironment** en **event-gedreven workers** nodig hebben om multi-asset strategieën elegant te implementeren. De stresstest heeft een waardevol punt voor verdere ontwikkeling blootgelegd.

### **Scenario 4: De "Walk-Forward Optimizer"**

* **Doel van de Quant:** "Ik wil niet zomaar een backtest. Ik wil een volledige walk-forward analyse uitvoeren. Optimaliseer mijn strategie op de data van 2022 en test de beste parameters op Q1 2023. Optimaliseer vervolgens op 2022 + Q1 2023 en test op Q2 2023, enzovoort."
* **Architecturale Toets:** Dit scenario test de flexibiliteit van de **meta-workflow laag** en de OperationService. Vereist dit grote aanpassingen aan de kern?
  1. Kan de OperationService programmatisch worden aangeroepen met verschillende configuraties (met name datumbereiken)?
  2. Kunnen de OptimizationService en de BacktestService (in essentie de OperationService in backtest-modus) in een hogere-orde lus worden geplaatst?
* **Het Oordeel: ✅ Geslaagd**
  De architectuur is hier perfect geschikt voor.
  * **MODULARITEIT:** De OperationService en OptimizationService zijn ontworpen als modulaire "motoren". Ze kunnen perfect worden aangeroepen vanuit een andere, overkoepelende service.
  * **DE OPLOSSING:** We creëren een nieuwe service, de WalkForwardService.
    * Deze service leest een walk_forward.yaml-configuratie die de "in-sample" (training) en "out-of-sample" (testing) periodes definieert.
    * In een lus roept de WalkForwardService eerst de OptimizationService aan met de in-sample periode.
    * Vervolgens pakt hij de beste parameters uit het resultaat en roept de OperationService aan om een backtest te draaien op de out-of-sample periode.
    * Hij aggregeert de resultaten van alle out-of-sample periodes tot één finaal rapport.

Dit scenario vereist **geen enkele aanpassing** aan de kernarchitectuur van de OperationService of de factories. Het toont aan dat de meta-workflow laag flexibel en uitbreidbaar is.