# **Addendum: Data Landschap & Point-in-Time Architectuur**

Status: Definitief Concept  
Datum: 2025-10-23  
Gerelateerd aan: Heroverweging van Data Flow en Worker Interactie

## **0. Impact op Bestaande Documentatie (docs.md)**

Dit addendum introduceert een fundamentele verschuiving in hoe data wordt beheerd en uitgewisseld tussen workers binnen S1mpleTrader, overstappend van een enriched_df-gebaseerd model naar een **"Point-in-Time", DTO-gedreven architectuur** met expliciete data-aanvraag via een ITradingContextProvider. Deze wijziging heeft een **brede impact** op de conceptuele beschrijvingen in de originele docs.md documentatie. De volgende secties zijn door dit addendum achterhaald of vereisen significante herinterpretatie:

### **Hoofdstuk 2: 2_ARCHITECTURE.md**

* **Paragraaf 2.4. Het Worker Ecosysteem:** De beschrijving van de *dataflow* tussen worker-categorieën (diagram en tekst) is conceptueel veranderd. De TradingContext is geen doorgeefluik meer met een groeiend enriched_df. Data-uitwisseling verloopt nu via de Tick Cache en ITradingContextProvider.  
* **Paragraaf 2.10.1. Core Components (TradingContext):** De beschrijving van TradingContext als container voor enriched_df is **volledig vervangen**. De context is nu minimalistisch (timestamp, current_price) en specifieke data wordt via de ITradingContextProvider geleverd.  
* **Paragraaf 2.11. Dataflow & Orchestratie:** De beschrijving van de dataflow en de rol van ContextEnriched event is achterhaald. De flow wordt nu beheerd via ITradingContextProvider en de Tick Cache, getriggerd door initiële events en gestuurd door de wiring_map via Adapters.

### **Hoofdstuk 3: 3_DE_CONFIGURATIE_TREIN.md**

* **Paragraaf 3.4.2. strategy_blueprint.yaml:** De structuur blijft grotendeels gelijk, maar de *interpretatie* van de worker-volgorde binnen context_workers verandert. Het gaat niet meer om het sequentieel *muteren* van een DataFrame, maar om het sequentieel *produceren* van DTOs voor de Tick Cache.  
* **Paragraaf 3.7.1. manifest.yaml (dependencies):** De velden requires en provides (voor DataFrame kolommen) zijn **vervangen/aangevuld** door requires_capability, requires_dtos en produces_dtos. De manier waarop dependencies worden gedeclareerd en gevalideerd is fundamenteel anders.

### **Hoofdstuk 4: 4_DE_PLUGIN_ANATOMIE.md**

* **Paragraaf 4.3.2. Dependencies (Het Data Contract):** Deze sectie is **volledig vervangen** door de nieuwe DTO-gebaseerde aanpak. De concepten requires, provides, requires_context zijn geherdefinieerd of vervangen.  
* **Paragraaf 4.4. De Worker & het BaseWorker Raamwerk:** De *implementatie* van de process-methode verandert significant. Workers interacteren nu met ITradingContextProvider (get_required_dtos, set_result_dto) en Platform Providers. Ze muteren geen gedeelde context meer direct. De WorkerOutput envelope wordt nu gebruikt voor flow control en event publicatie.

### **Hoofdstuk 5: 5_DE_WORKFLOW_ORKESTRATIE.md**

* **Gehele Hoofdstuk:** Dit hoofdstuk is het **meest ingrijpend beïnvloed**. Het beschreef de flow grotendeels gebaseerd op de enriched_df en impliciete data-overdracht. De nieuwe architectuur met de Tick Cache, ITradingContextProvider en expliciete DTOs vereist een **volledige herschrijving** van hoe de workflow wordt geconceptualiseerd en geïmplementeerd.  
* **Paragraaf 5.1. Introductie: De Paradigma Shift:** Deze paragraaf dient nu als de **centrale "hook"** (zie sectie 5 hieronder) om de *nieuwe* paradigmaverschuiving naar het "Point-in-Time" model te introduceren.  
* **Dataflow Diagrammen:** Alle diagrammen die de flow via een groeiende TradingContext tonen, zijn incorrect.

### **Hoofdstuk 8: 8_DEVELOPMENT_STRATEGY.md**

* **Paragraaf 8.6. Development Workflow per Worker Type:** De codevoorbeelden en beschrijvingen van de I/O per worker type moeten volledig worden herschreven om de interactie met ITradingContextProvider en het gebruik van DTOs te weerspiegelen.  
* **Paragraaf 8.7. Testing Strategieën:** De beschrijving van unit testing (met name fixtures) moet worden bijgewerkt om te laten zien hoe de ITradingContextProvider en andere providers gemockt worden.

### **Hoofdstuk 10: 10_CODING_STANDAARDS_DESIGN_PRINCIPLES.md**

* **Paragraaf 10.2. Contract-Gedreven Ontwikkeling:** Dit principe wordt *versterkt*, maar de *implementatie* verschuift van (deels impliciete) DataFrame contracten naar expliciete DTO-contracten voor *alle* data-uitwisseling.  
* **Paragraaf 10.8.5. CQRS:** Blijft relevant, maar de implementatie binnen workers (scheiding tussen data opvragen en data produceren/registreren) wordt explicieter.

### **Conclusie Impact Analyse:**

De introductie van het "Point-in-Time", DTO-gedreven model is een fundamentele architecturale wijziging die vrijwel alle hoofdstukken raakt die de interne werking, dataflow, configuratie en ontwikkeling beschrijven. De originele documentatie moet primair gelezen worden voor de *hoge-niveau concepten* (lagen, component-rollen, principes), maar de *concrete implementatie* van de data-uitwisseling is significant veranderd zoals beschreven in dit addendum.

## **1. Doel & Kernprincipes**

Dit document formaliseert de **"Point-in-Time", DTO-gedreven architectuur** voor data-uitwisseling tussen workers in S1mpleTrader. Het vervangt het eerdere model dat gebaseerd was op een enriched_df binnen een muterende TradingContext.

Het doel is het definiëren van een **expliciet, type-veilig, consistent en testbaar data landschap** dat voldoet aan de hoge eisen van een financiële applicatie. Dit wordt bereikt door de volgende **kernprincipes** te hanteren:

1. **Point-in-Time Principe:** Alle data-uitwisseling is gebaseerd op de informatie die relevant is voor één specifiek moment (tick). Workers opereren op basis van de staat *nu*, niet op basis van een groeiende historische dataset binnen de context.  
2. **DTO-Centric Contracten:** *Alle* data die wordt uitgewisseld tussen workers binnen de standaard flow, of geproduceerd voor de Tick Cache, wordt verpakt in **specifieke, getypeerde Pydantic DTOs**. Dit maximaliseert type-veiligheid en maakt contracten expliciet. Primitieve types worden *niet* direct in de cache geplaatst.  
3. **Expliciete Data Afhankelijkheid:** Workers declareren hun exacte data-behoeften (requires_capability, requires_dtos) en output (produces_dtos, publishes) in hun manifest.yaml. Er wordt geen data impliciet doorgegeven.  
4. **Minimale TradingContext:** De TradingContext bevat alleen de meest essentiële basisinformatie (timestamp, current_price). Alle andere benodigde data wordt *on-demand* geleverd via de ITradingContextProvider.  
5. **ITradingContextProvider als Data Hub:** Een centrale service (ITradingContextProvider) beheert de toegang tot de tijdelijke Tick Cache (die alleen DTOs bevat) en levert data aan workers op basis van hun gedeclareerde behoeften.  
6. **Gescheiden Communicatiepaden (Cache vs. EventBus):**  
   * **Tick Cache (via ITradingContextProvider):** Voor *interne, synchrone* data-doorgifte tussen workers binnen de standaard flow van één tick, gebruikmakend van **plugin-specifieke DTOs**.  
   * **EventBus (via IEventPublisher):** Voor *externe, asynchrone* signalen, resultaten, alerts of status-updates naar mogelijk meerdere/onbekende luisteraars, gebruikmakend van **standaard Systeem DTOs**.  
7. **Platform als "Toolbox":** Het platform biedt data en diensten (OHLCV, state, journaling, etc.) aan via geïnjecteerde *Provider Interfaces* (IOhlcvProvider, IStateProvider, etc.), die door workers via manifest.requires_capability worden aangevraagd.  
8. **Beheerde DTO Deling:** Plugin-specifieke DTOs worden centraal beschikbaar gesteld via een "Enrollment Exposure" mechanisme met een gestructureerd, versie-bewust pad (backend/dto_reg/...), gefaciliteerd door de Plugin IDE en het platform.  
9. **Testbaarheid:** De architectuur is ontworpen voor maximale unit-testbaarheid van workers door expliciete contracten en het gebruik van interfaces voor alle externe afhankelijkheden.

Dit document legt deze principes vast en werkt de details uit voor de implementatie van het data landschap.

## **2. De Anatomie van een Worker-Aanroep**

Deze sectie beschrijft de interactiepatronen en data flow binnen het "Point-in-Time" model, gebaseerd op een strikt DTO-gedreven aanpak voor alle data-uitwisseling, inclusief de methode voor het delen en beheren van deze DTOs en de levenscyclus van de data-cache.

### **2.1. De WorkerBuilder: Eenmalige Injectie van de Toolbox**

* **Rol:** Tijdens de bootstrap-fase (georkestreerd door OperationService via BuildSpecs) instantieert de WorkerBuilder (nu WorkerFactory) elke worker.  
* **Injectie:** Op basis van de requires_capability declaraties in het manifest.yaml, injecteert de WorkerBuilder **éénmalig** de benodigde **singleton Platform Provider interfaces** (de "Toolbox") in de worker-instantie. Dit omvat ook de **ITradingContextProvider**.  
  class MyWorker(BaseWorker):  
      # Dependencies worden type-hinted en geïnjecteerd  
      ohlcv_provider: IOhlcvProvider  
      context_provider: ITradingContextProvider  
      state_provider: Optional[IStateProvider] # Optioneel, alleen als capability is aangevraagd

      def __init__(self, params, **kwargs): # Ontvangt geïnjecteerde providers via kwargs  
          super().__init__(params)  
          # Store providers (voorbeeld, kan ook via directe attributen)  
          self.ohlcv_provider = kwargs['ohlcv_provider']  
          self.context_provider = kwargs['context_provider']  
          self.state_provider = kwargs.get('state_provider')  
          # ... etc  
* **Geen Runtime Rol:** De WorkerBuilder speelt geen rol meer *nadat* de worker is geïnstantieerd.

### **2.2. De ITradingContextProvider: De Poort naar "Point-in-Time" DTOs**

* **Rol:** **Singleton service** die fungeert als DTO hub voor de **huidige tick/flow**. Beheert toegang tot de tijdelijke Tick Cache, die **alleen DTO-instanties** bevat. Wordt per tick geconfigureerd door de TickCacheManager.  
* **Interface:**  
  # backend/core/interfaces/context_provider.py  
  from typing import Protocol, Any, Dict, Type, List  
  from datetime import datetime  
  from pydantic import BaseModel  
  from backend.core.interfaces.worker import IWorker

  # Type alias voor de cache  
  TickCacheType = Dict[Type[BaseModel], BaseModel]

  class BaseContextDTO(BaseModel):  
      """Bevat de minimale basis context voor een tick."""  
      timestamp: datetime  
      current_price: float

  class ITradingContextProvider(Protocol):  
      """  
      Interface voor de service die DTO-gebaseerde 'point-in-time'  
      context beheert en levert.  
      """

      def start_new_tick(self, tick_cache: TickCacheType, timestamp: datetime, current_price: float):  
          """Configureert de provider voor een nieuwe tick met een specifieke DTO-cache."""  
          ...

      def get_base_context(self) -> BaseContextDTO:  
          """Haalt de minimale basis context (timestamp, price) voor de huidige tick op."""  
          ...

      def get_required_dtos(self, requesting_worker: IWorker) -> Dict[Type[BaseModel], BaseModel]:  
          """  
          Haalt de DTO-instanties op die de worker nodig heeft (volgens manifest.requires_dtos)  
          uit de cache van de huidige tick.

          Returns:  
              Een dictionary die DTO-types mapt naar hun instanties.

          Raises:  
              MissingContextDataError: Als een vereist DTO niet in de cache zit.  
          """  
          ...

      def set_result_dto(self, producing_worker: IWorker, result_dto: BaseModel):  
          """  
          Voegt het geproduceerde DTO toe aan de cache van de huidige tick.  
          Gebruikt het type van de DTO als sleutel.  
          Valideert of dit DTO overeenkomt met manifest.produces_dtos.  
          """  
          ...

* **Cache:** Werkt intern met een current_tick_cache (een Dict[Type[BaseModel], BaseModel]) die **per tick** wordt aangemaakt en beheerd (zie 2.7).

### **2.3. De DispositionEnvelope**

Om de intentie van een worker na uitvoering duidelijk te communiceren naar de orkestrerende laag (de Adapter) en tegelijkertijd de worker bus-agnostisch te houden, gebruiken we de volgende mechanismen:

1. **Data voor de Flow Cache:** Als een worker data produceert die bedoeld is voor direct volgende workers *binnen dezelfde tick/flow*, gebruikt hij **uitsluitend** de geïnjecteerde ITradingContextProvider:  
   self.context_provider.set_result_dto(self, mijn_plugin_dto)

   In dit geval retourneert de process of event handler methode None of een DispositionEnvelope met disposition="CONTINUE".  
2. **Communicatie naar de EventBus (Signalen/Alerts):** Als een worker een signaal, alert, of voltooid resultaat wil publiceren naar de **brede EventBus** (voor onbekende/meerdere/onafhankelijke luisteraars of om een nieuwe flow te triggeren), retourneert zijn process of event handler methode een DispositionEnvelope object:

# backend/shared_dtos/disposition_envelope.py  
from pydantic import BaseModel  
from typing import Optional, Literal, Any

class DispositionEnvelope(BaseModel):  
    """  
    Een gestandaardiseerde 'envelope' die de intentie van een worker  
    (of andere component) na uitvoering aangeeft. Bevat GEEN data voor de flow cache.  
    """  
    # Enkel de intentie  
    disposition: Literal["CONTINUE", "PUBLISH", "STOP"] = "CONTINUE"

    # --- Alleen relevant bij disposition="PUBLISH" ---  
    # De naam van het event dat op de EventBus gepubliceerd moet worden  
    # (moet gedeclareerd zijn in manifest.publishes)  
    event_name: Optional[str] = None

    # De payload voor het event (MOET een standaard Systeem DTO zijn)  
    event_payload: Optional[BaseModel] = None

**Gebruik:**  
# In EMACrossOpportunity worker  
if cross_detected:  
    signal_dto = OpportunitySignalDTO(...) # Een Systeem DTO  
    return DispositionEnvelope(  
        disposition="PUBLISH",  
        event_name="SIGNAL_GENERATED",  
        event_payload=signal_dto  
    )  
else:  
    return DispositionEnvelope(disposition="STOP")

3. **De Rol van de EventAdapter:** De adapter die de worker aanriep, ontvangt de DispositionEnvelope. * Bij CONTINUE: De adapter triggert de volgende worker(s) volgens de wiring_map. * Bij PUBLISH: De adapter valideert event_name en event_payload tegen het manifest van de worker en roept EventBus.publish(...) aan. Daarna triggert het mogelijk ook de volgende worker(s) (afhankelijk van wiring_map configuratie: moet publicatie de flow stoppen of mag deze doorgaan?). * Bij STOP: De adapter stopt de verdere verwerking voor deze specifieke flow-tak.

Deze aanpak houdt de worker volledig gefocust op zijn logica en data-productie, terwijl de DispositionEnvelope een schoon, expliciet signaal geeft over hoe de output verwerkt moet worden, zonder dat de worker zich met de EventBus zelf hoeft bezig te houden.

### **2.4. Data Toegang voor Workers**

Een worker verkrijgt data als volgt:

1. **Basis Context:** base_context = self.context_provider.get_base_context() (altijd beschikbaar).  
2. **Benodigde DTOs:** required_dtos = self.context_provider.get_required_dtos(self) (haalt DTOs uit cache op basis van manifest.requires_dtos).  
3. **Platform Diensten:** data = self.ohlcv_provider.get_window(...) (roept geïnjecteerde provider aan met base_context.timestamp).  
4. **Interne State:** prev_state = self.state_provider.get() (indien capability aanwezig).  
5. **Event Payloads:** Worden direct meegegeven aan de event handler methode door de Adapter.

### 

### **2.5. Het Delen van DTOs: Enrollment Exposure & Centrale Registratie**

Het delen van **plugin-specifieke DTOs** (geproduceerd voor de Tick Cache) gebeurt via een centraal mechanisme dat wordt gefaciliteerd door de Plugin IDE en het platform:

1. **Definitie & Generatie:** De ontwikkelaar definieert (via de IDE) de structuur van zijn output-DTO. De IDE **genereert** de Pydantic klasse in de dtos/ map van de plugin. De IDE voegt ook **versie-informatie** toe, gekoppeld aan de **plugin-versie**.  
2. **Manifest Declaratie:** Het manifest.yaml declareert de geproduceerde DTO (produces_dtos) met een verwijzing naar het **lokale** pad binnen de plugin. Consumerende plugins declareren de benodigde DTO (requires_dtos) met een verwijzing naar het **verwachte centrale pad**.  
3. **Enrollment Proces:** Bij het enrollen van de producerende plugin:  
   * Het platform detecteert de DTO-definities.  
   * Het **kopieert** de DTO-bestanden naar een **centrale, versie-specifieke locatie** binnen de S1mpleTrader backend.  
   * **Padstructuur:** backend/dto_reg/<vendor>/<plugin_name>/v<plugin_version>/<dto_name>.py  
     * **Voorbeeld:** backend/dto_reg/s1mple/ema_detector/v1_0_0/ema_output_dto.py  
   * Het platform **registreert** deze centrale locatie (bv. in een interne DTORegistry).  
4. **Import door Consumer:** Een consumerende plugin **importeert** de benodigde DTO altijd **vanuit de centrale backend/dto_reg/... locatie**.  
   from backend.dto_reg.s1mple.ema_detector.v1_0_0.ema_output_dto import EMAOutputDTO  
5. **Testbaarheid:** Unit tests importeren de DTOs ook vanaf de (verwachte) centrale locatie om mocks te configureren.  
6. **Dependency Management:** Het platform (of de marketplace/dependency manager) wordt verantwoordelijk voor het controleren of de door een consumer (requires_dtos) gevraagde DTO-versie beschikbaar is en compatibel is met de geïnstalleerde versie van de producerende plugin.

Dit model handhaaft DRY in de broncode, biedt maximale type-veiligheid via directe imports, maakt versioning expliciet (gekoppeld aan de plugin-versie), en houdt de worker-code relatief schoon van lange, instabiele paden.

### **2.6. De Platform "Toolbox": Diensten als Capabilities**

* **Concept:** Het platform biedt een reeks **singleton services** (Providers) aan die toegang geven tot data of functionaliteit.  
* **Toegang:** Workers declareren welke providers ze nodig hebben via manifest.requires_capability (bv. "ohlcv_window", "state_persistence").  
* **Injectie:** De WorkerBuilder injecteert de corresponderende **interface** (IOhlcvProvider, IStateProvider) in de worker-instantie.  
* **Point-in-Time:** Alle providers die tijdreeksdata leveren (IOhlcvProvider, IMtfProvider) *moeten* de timestamp uit de BaseContextDTO respecteren.

**Overzichtstabel Platform Providers (Toolbox):**

| Dienst (Interface) | Declaratie (requires_capability in manifest) | Geïnjecteerd als (self.<naam>) | Voorbeeld Gebruik in Worker |
| :---- | :---- | :---- | :---- |
| **Context Provider** | (Standaard geïnjecteerd) | self.context_provider | base_ctx = self.context_provider.get_base_context() dtos = self.context_provider.get_required_dtos(self) self.context_provider.set_result_dto(self, dto) |
| IOhlcvProvider | "ohlcv_window" | self.ohlcv_provider | df = self.ohlcv_provider.get_window(base_ctx.timestamp, ...) |
| IMtfProvider | "multi_timeframe" | self.mtf_provider | df_4h = self.mtf_provider.get_window(base_ctx.timestamp, '4H') |
| IStateProvider | "state_persistence" | self.state_provider | last_value = self.state_provider.get(...) self.state_provider.set(...) |
| IDepthProvider | "market_depth" | self.depth_provider | imbalance = self.depth_provider.get_imbalance(base_ctx.timestamp) |
| ILedgerProvider | "ledger_state" | self.ledger_provider | drawdown = self.ledger_provider.get_current_drawdown() |
| IJournalWriter | "journaling" | self.journal_writer | self.journal_writer.log_entry(...) |
| *(Andere toekomstige providers...)* | *(Specifieke capability key)* | *(self.provider_naam)* | *(Provider-specifieke methode)* |

### 

### **2.7. De Start van de Flow: TickCacheManager als Event Listener (SRP-Conform v6 - Finale Rol)**

De levenscyclus van de current_tick_cache wordt beheerd door een centrale component die reageert op de startsignalen van de EventBus, in lijn met Addendum 3.8:

1. **TickCacheManager (Singleton Backend Component met Adapter):**  
   * **Rol:** Beheert de levenscyclus (creatie, vrijgave) van current_tick_cache dictionaries *per flow*. Is de **initiator** van elke nieuwe dataverwerkingsflow (tick).  
   * **Bootstrap:** Wordt als singleton geïnitialiseerd door OperationService. Zijn **Adapter** (geconfigureerd door EventWiringFactory tijdens bootstrap) abonneert zich op alle **initiërende events** (bv. RAW_TICK, SCHEDULED_TASK:{name}, NEWS_RECEIVED).  
   * **Runtime Workflow bij Ontvangst Initiërend Event:**  
     1. Creëert een nieuwe, lege cache: cache = {}.  
     2. Haalt basis-info (timestamp, price) uit het trigger-event.  
     3. Configureert de (singleton) ITradingContextProvider: context_provider.start_new_tick(cache, timestamp, price).  
     4. **Cruciaal:** Publiceert een **nieuw intern event**, bv. TICK_FLOW_START, met een referentie naar de geconfigureerde context_provider (of een unieke tick ID waarmee de provider de juiste cache kan vinden).  
     5. (Optioneel): Luistert naar een TICK_FLOW_COMPLETE event om de cache vrij te geven via release_cache(cache).  
   * **Interface:** Interne logica, plus mogelijk release_cache.  
2. **ITradingContextProvider (Singleton Service):**  
   * **Rol:** Blijft de actieve data-leverancier en -ontvanger *binnen* een tick.  
   * **Configuratie per Tick:** Wordt geconfigureerd door de TickCacheManager via start_new_tick(). Weet welke cache bij welke (actieve) tick hoort.  
3. **Flow Start voor Workers:**  
   * De **Adapters** van de *eerste* workers in de flow (zoals gedefinieerd in wiring_map) luisteren nu **niet** meer naar de ruwe initiërende events (RAW_TICK), maar naar het door de TickCacheManager gepubliceerde **TICK_FLOW_START** event.  
   * Bij ontvangst van TICK_FLOW_START, roepen deze adapters hun respectievelijke workers aan. De workers gebruiken vervolgens de (nu correct geconfigureerde) ITradingContextProvider om hun data op te halen en te plaatsen.

**Voordelen van deze Opzet:**

* **Strikte SRP:** TickCacheManager focust op cache levenscyclus en startsignalen. ITradingContextProvider focust op data toegang binnen een actieve tick. Adapters focussen op worker aanroepen.  
* **DRY:** Cache creatie en provider configuratie gebeurt centraal in TickCacheManager.  
* **Event-Driven:** De start van de flow is nu volledig geïntegreerd in de EventBus-architectuur.  
* **Testbaarheid:** De TickCacheManager kan getest worden door initiërende events te sturen en te controleren of TICK_FLOW_START correct wordt gepubliceerd en de provider juist wordt geconfigureerd.

### **2.8. Definitie Tick Cache vs. Journaling**

* **Tick Cache:**  
  * **Levensduur:** **Extreem kort:** bestaat alleen gedurende de synchrone verwerking van één enkele tick/flow.  
  * **Inhoud:** **Alleen DTO-instanties** die *intermediaire resultaten* binnen die ene tick vertegenwoordigen.  
  * **Doel:** Efficiënte, type-veilige data-doorgifte *tussen* workers in een sequentiële/parallelle flow *binnen één tick*.  
  * **Persistentie:** **Absoluut niet persistent.** Wordt weggegooid na elke tick.  
* **Journaling (IJournalWriter -> StrategyJournal):**  
  * **Levensduur:** **Permanent** (voor de duur van de operation/backtest).  
  * **Inhoud:** **Geselecteerde, significante gebeurtenissen** (events, beslissingen, trade executies) met causale context.  
  * **Doel:** Historische logging, analyse, debugging, audit trail.  
  * **Persistentie:** **Wordt persistent opgeslagen** (bv. in een bestand).  
* **Geen Overlap:** Data in de Tick Cache is *niet* bedoeld voor de journal. Een worker die iets wil loggen, gebruikt *expliciet* de IJournalWriter capability. Een worker die data doorgeeft aan de volgende stap, gebruikt *expliciet* set_result_dto. Dit zijn **gescheiden mechanismen** met **gescheiden doelen**. Er is dus **geen DRY-schending**; het zijn verschillende data met verschillende bestemmingen.

### **2.9. "Point-in-Time" Garantie en Validatie (Expliciet)**

* **Garantie:** Komt voort uit:  
  1. De **Flow Initiator Adapter** die de timestamp en current_price vastlegt bij het starten van de tick en doorgeeft aan de TickCacheManager / ITradingContextProvider.  
  2. De **Platform Providers** (IOhlcvProvider, etc.) die *verplicht* zijn de timestamp uit get_base_context() te respecteren en geen data uit de toekomst te lekken.  
  3. De **Tick Cache** die alleen data bevat die *binnen diezelfde tick* is berekend.  
* **Validatie:**  
  1. **Bootstrap (DependencyValidator):** Controleert of de produces_dtos van de ene worker overeenkomen met de requires_dtos van de volgende, gebruikmakend van het centrale DTO-register. Kan ook **type-consistentie** checken.  
  2. **Runtime (ITradingContextProvider.set_result_dto):** Valideert of het aangeboden result_dto overeenkomt met manifest.produces_dtos en (optioneel) het type in het Data Dictionary.  
  3. **Runtime (Worker):** Kan optioneel timestamps checken.

### **2.10. Scherpe Definitie: Cache DTO vs. Event Payload DTO**

Een worker gebruikt...

* **ITradingContextProvider.set_result_dto(dto: PluginSpecificDTO)**:  
  * **Wanneer?** Als de dto primair bedoeld is als **directe input** voor de **onmiddellijk volgende worker(s)** in de **standaard, geconfigureerde flow** (wiring_map).  
  * **Aard van de data:** **Specifieke, door de plugin (via IDE) gegenereerde DTOs** die intermediaire resultaten bevatten voor de *lopende verwerkingsketen*.  
  * **Analogie:** Een specifiek, getypeerd onderdeel doorgeven op een lopende band.  
* **self.event_publisher.publish(event_name: str, payload: StandardSystemDTO)**:  
  * **Wanneer?** Als de payload een **significant resultaat, signaal, alert of statusverandering** is dat het einde van een fase markeert, voor meerdere/onbekende luisteraars is, of een nieuwe flow triggert.  
  * **Aard van de data:** **Standaard, door het platform gedefinieerde Systeem DTOs** (bv. OpportunitySignalDTO, CriticalEventDTO, RoutedTradePlanDTO).  
  * **Analogie:** Een gestandaardiseerd rapport of signaal publiceren via de intercom.

**Vuistregel:** Data voor de *interne, synchrone flow* -> **Cache** (via set_result_dto met **plugin-specifieke DTO**). Data als *extern signaal/resultaat* -> **EventBus** (via publish met **standaard Systeem DTO**).

## **3. Gedetailleerde Inventarisatie per Worker Subtype & EventBus Deelnemers (v6 - Finale DTO Strategie & Scope)**

Deze sectie combineert de inventarisatie van data I/O per worker subtype met een overzicht van alle deelnemers aan de EventBus en hun scope, om een compleet beeld te geven van het data landschap en de interacties binnen het "Point-in-Time" model.

### **3.1. Overzicht EventBus Deelnemers & Scope**

Het is cruciaal om onderscheid te maken tussen componenten die één keer per operatie bestaan (singletons) en componenten waarvan er één instantie per draaiende strategie is. De EventBus fungeert als de centrale lijm tussen deze scopes.

| Component/Concept | Scope | Aantal Instanties per Operation | Notities |
| :---- | :---- | :---- | :---- |
| **Operation-Brede Singletons (Infrastructuur & Diensten)** |  |  |  |
| EventBus | Operation-breed (Singleton) | 1 | Centrale communicatiehub. |
| Scheduler | Operation-breed (Singleton) | 1 | Initieert tijd-triggers; geconfigureerd door operation.yaml. |
| TickCacheManager | Operation-breed (Singleton) | 1 | Beheert levenscyclus van tijdelijke caches per tick; Luistert naar initiërende events. |
| ITradingContextProvider | Operation-breed (Singleton) | 1 | Wordt per tick geconfigureerd door TickCacheManager. |
| Platform Providers (Toolbox) | Operation-breed (Singleton) | 1 per type | IOhlcvProvider, IMtfProvider, IStateProvider, IJournalWriter, etc. Worden geïnjecteerd. |
| Factories | Operation-breed (Singleton) | 1 per type | WorkerBuilder, PersistorFactory, ConnectorFactory, etc. Herbruikt voor elke strategie-setup. |
| Validators | Operation-breed (Singleton) | 1 per type | DependencyValidator, EventChainValidator, ConfigValidator. Herbruikt voor validaties. |
| PluginRegistry | Operation-breed (Singleton) | 1 | Kennisbank van alle beschikbare plugins. |
| OperationService | Operation-breed (Singleton) | 1 | Hoofd-orkestrator van strategie-levenscycli. |
| AggregatedLedger (opt.) | Operation-breed (Singleton) | 1 | Aggregeert data over alle strategieën; luistert naar events. |
| UI Backend / BFF | Operation-breed (Singleton) | 1 | Interface naar de frontend; luistert naar events. |
| External Data Adapters | Operation-breed (Singleton) | 1 per externe bron | Beheert verbinding met externe bron; publiceert events. |
| --- | --- | --- | --- |
| **Strategie-Specifieke Instanties (Logica & Staat)** |  |  |  |
| Workers (alle subtypes) | Strategie-specifiek | N workers * Aantal Strategieën | Kernlogica van de strategie. |
| EventAdapter (per Worker) | Strategie-specifiek | 1 per Worker Instantie | Lokale router/communicatie-interface voor de worker. |
| StrategyLedger | Strategie-specifiek | 1 per Strategie | Operationele staat van *deze* strategie. |
| StrategyJournal | Strategie-specifiek | 1 per Strategie | Historische data van *deze* strategie (de data zelf). |
| ExecutionEnvironment | Strategie-specifiek | 1 per Strategie | De "wereld" waarin *deze* strategie draait (backtest/live). |
| Tick Cache (current_...) | Tick/Flow-specifiek | 1 per actieve tick/flow | Tijdelijke dataopslag *binnen* een tick, beheerd door TickCacheManager. |

### **3.2. Data I/O Inventarisatie per Worker Subtype**

Deze sectie beschrijft de *typische* data-interacties voor elk subtype binnen het DTO-Centric "Point-in-Time" model. Specifieke plugins kunnen hiervan afwijken.

*(Noot: req_cap = requires_capability, req_dto = requires_dtos, prod_dto = produces_dtos (type DTO via set_result_dto), disp_env = DispositionEnvelope)*

#### **3.2.1. ContextWorker Subtypes (7)**

* **Algemeen:**  
  * **Rol:** Produceert objectieve context data voor de Tick Cache.  
  * **Output:** set_result_dto() met specifieke Plugin DTO. disp_env: CONTINUE of STOP. Publiceert NOOIT events.  
* **REGIME_CLASSIFICATION:**  
  * req_cap: Meestal ohlcv_window.  
  * req_dto: Kan indicatoren van eerdere workers vereisen (bv. VolatilityOutputDTO).  
  * prod_dto: Bv. MarketRegimeDTO(regime='trending'/'ranging', strength=0.8).  
* **STRUCTURAL_ANALYSIS:**  
  * req_cap: ohlcv_window.  
  * req_dto: -  
  * prod_dto: Bv. MarketStructureDTO(is_bos=True, swing_high=123.45), LiquidityZoneDTO(zones=[...]), OrderBlockDTO(blocks=[...]).  
* **INDICATOR_CALCULATION:**  
  * req_cap: ohlcv_window (soms mtf_window).  
  * req_dto: -  
  * prod_dto: Specifieke DTOs zoals EMAOutputDTO(ema_20=...), RSIOutputDTO(rsi_14=...), ATROutputDTO(atr_14=...).  
* **MICROSTRUCTURE_ANALYSIS:**  
  * req_cap: market_depth.  
  * req_dto: -  
  * prod_dto: Bv. OrderbookImbalanceDTO(imbalance_ratio=1.5).  
* **TEMPORAL_CONTEXT:**  
  * req_cap: - (Werkt op base_context.timestamp).  
  * req_dto: -  
  * prod_dto: Bv. SessionInfoDTO(session='london', is_killzone=True).  
* **SENTIMENT_ENRICHMENT:**  
  * req_cap: news_feed (of andere externe feed).  
  * req_dto: -  
  * prod_dto: Bv. SentimentScoreDTO(source='news', score=0.65).  
* **FUNDAMENTAL_ENRICHMENT:**  
  * req_cap: Specifieke provider (bv. onchain_data).  
  * req_dto: -  
  * prod_dto: Bv. OnChainMetricsDTO(nvt_ratio=...).

#### **3.2.2. OpportunityWorker Subtypes (7)**

* **Algemeen:**  
  * **Rol:** Detecteert subjectieve kansen.  
  * **Output:** disp_env: PUBLISH (met event_name="SIGNAL_GENERATED", payload=OpportunitySignalDTO) bij detectie, anders STOP. Kan *ook* set_result_dto() gebruiken voor intermediaire scores/data (Plugin DTO) voor andere OpportunityWorkers binnen dezelfde fase.  
* **TECHNICAL_PATTERN:**  
  * req_dto: Diverse Context DTOs (MarketStructureDTO, EMAOutputDTO, LiquidityZoneDTO, etc.).  
  * req_cap: state_persistence (opt. voor patroonherkenning over tijd).  
  * Output: OpportunitySignalDTO (payload) met signal_type='fvg', 'breakout', etc. en confidence_score. prod_dto: Kan bv. PatternConfirmationDTO produceren voor cache.  
* **MOMENTUM_SIGNAL:**  
  * req_dto: Indicatoren (EMAOutputDTO, MACDOutputDTO), MarketStructureDTO.  
  * Output: OpportunitySignalDTO (payload) met signal_type='trend_continuation', 'momentum_burst'.  
* **MEAN_REVERSION:**  
  * req_dto: Indicatoren (RSIOutputDTO, BollingerBandDTO).  
  * Output: OpportunitySignalDTO (payload) met signal_type='oversold_bounce', 'range_reversion'.  
* **STATISTICAL_ARBITRAGE:**  
  * req_dto: Context DTOs van *meerdere assets* (vereist MultiAsset support).  
  * Output: OpportunitySignalDTO (payload) met signal_type='pair_divergence'.  
* **EVENT_DRIVEN:**  
  * Input: Event Payload (bv. NewsEventDTO). req_dto: Context DTOs voor validatie.  
  * Output: OpportunitySignalDTO (payload) met signal_type='news_reaction'.  
* **SENTIMENT_SIGNAL:**  
  * req_dto: SentimentScoreDTO.  
  * Output: OpportunitySignalDTO (payload) met signal_type='extreme_fear_entry'.  
* **ML_PREDICTION:**  
  * req_dto: Grote set Context DTOs (features). req_cap: Model provider?  
  * Output: OpportunitySignalDTO (payload) met signal_type='ml_predicted_upmove', confidence_score van model.

#### **3.2.3. ThreatWorker Subtypes (5)**

* **Algemeen:**  
  * **Rol:** Detecteert risico's.  
  * **Output:** disp_env: PUBLISH (met event_name="THREAT_DETECTED", payload=CriticalEventDTO) bij detectie. Kan ook set_result_dto() gebruiken voor intermediaire risico-indicatoren (Plugin DTO). disp_env: CONTINUE of STOP indien geen dreiging.  
* **PORTFOLIO_RISK:**  
  * req_cap: ledger_state.  
  * Input: Event Payload (LEDGER_STATE_CHANGED).  
  * Output: CriticalEventDTO (payload) met threat_type='max_drawdown', 'over_exposure'. prod_dto: Bv. CurrentDrawdownDTO.  
* **MARKET_RISK:**  
  * req_dto: Context DTOs (ATROutputDTO, OrderbookImbalanceDTO).  
  * Output: CriticalEventDTO (payload) met threat_type='volatility_spike', 'liquidity_issue'.  
* **SYSTEM_HEALTH:**  
  * req_cap: Provider voor connectiviteit/datafeed status.  
  * Output: CriticalEventDTO (payload) met threat_type='connection_lost', 'data_gap'.  
* **STRATEGY_PERFORMANCE:**  
  * req_cap: state_persistence (om historie bij te houden), journal_reader?  
  * Output: CriticalEventDTO (payload) met threat_type='winrate_decline'.  
* **EXTERNAL_EVENT:**  
  * Input: Event Payload (NEWS_RECEIVED).  
  * Output: CriticalEventDTO (payload) met threat_type='high_impact_news'.

#### **3.2.4. PlanningWorker Subtypes (5, incl. Qualification)**

* **Algemeen:**  
  * **Rol:** Transformeert signalen/context naar plan-onderdelen.  
  * **Output:** Intermediair: set_result_dto() (met plan.* DTOs), disp_env: CONTINUE. Laatste Planner: disp_env: PUBLISH (met event_name="PLAN_READY", payload=RoutedTradePlanDTO). Qualification (Reject): disp_env: STOP.  
* **PLANNING_QUALIFICATION (NIEUW):**  
  * **Input:** Event Payloads (SIGNAL_GENERATED, THREAT_DETECTED). req_dto: Context DTOs, OpportunitySignalDTO, CriticalEventDTO.  
  * **Output:** prod_dto: Bv. PlanQualificationDTO(decision='PROCEED', score=0.75). set_result_dto(). disp_env: CONTINUE of STOP.  
* **ENTRY_PLANNING:**  
  * req_dto: PlanQualificationDTO (als input check), OpportunitySignalDTO, Context DTOs (MarketStructureDTO, etc.).  
  * Output: prod_dto: Bv. EntryPlanDTO(entry_price=..., entry_type='LIMIT'). set_result_dto(). disp_env: CONTINUE.  
* **EXIT_PLANNING:**  
  * req_dto: EntryPlanDTO, Context DTOs (LiquidityZoneDTO, ATROutputDTO).  
  * Output: prod_dto: Bv. ExitPlanDTO(stop_loss=..., take_profit=...). set_result_dto(). disp_env: CONTINUE.  
* **SIZE_PLANNING:**  
  * req_dto: ExitPlanDTO. req_cap: ledger_state.  
  * Output: prod_dto: Bv. SizePlanDTO(position_size=0.1). set_result_dto(). disp_env: CONTINUE.  
* **ORDER_ROUTING:**  
  * req_dto: SizePlanDTO.  
  * **Output:** disp_env: PUBLISH (met event_name="PLAN_READY", payload=RoutedTradePlanDTO(volledig plan incl. order type)).

#### **3.2.5. ExecutionWorker Subtypes (4)**

* **Algemeen:**  
  * **Rol:** Voert acties uit.  
  * **Input:** Event Payloads (PLAN_READY, THREAT_DETECTED, SCHEDULED_TASK, etc.). req_cap: execution_provider, ledger_state, state_persistence, journal_writer.  
  * **Output:** Side-effects via IExecutionProvider. Kan events publiceren (TRADE_EXECUTED, etc.) via disp_env: PUBLISH. Logt via IJournalWriter. disp_env: Meestal STOP.  
* **TRADE_INITIATION:**  
  * Input: Event Payload (PLAN_READY).  
  * **Output:** Roept IExecutionProvider.place_order(...) aan. Publiceert TRADE_OPENING / TRADE_OPENED event.  
* **POSITION_MANAGEMENT:**  
  * req_cap: state_persistence (vaak). Input: Trigger event (bv. tijd, prijsupdate, custom event MOVE_STOP).  
  * **Output:** Roept IExecutionProvider.modify_order(...) aan. Publiceert POSITION_MODIFIED event. Updates state.  
* **RISK_SAFETY:**  
  * Input: Event Payload (THREAT_DETECTED).  
  * **Output:** Roept IExecutionProvider.cancel_order(...) / close_position(...) aan. Publiceert EMERGENCY_EXIT event.  
* **OPERATIONAL:**  
  * Input: Event Payload (SCHEDULED_TASK). req_cap: ledger_state, execution_provider.  
  * **Output:** Roept IExecutionProvider.place_order(...) aan (bv. voor DCA). Publiceert OPERATIONAL_TASK_COMPLETE event.

Dit is een uitgebreide eerste opzet. Het formaliseert de data-interacties per subtype binnen het DTO-centric, Point-in-Time model. Dit document moet iteratief verfijnd worden naarmate specifieke plugins worden ontworpen.

## **4. Voorbeeld Data Flow in Detail (EMACrossOpportunity)**

*(Deze sectie moet worden bijgewerkt om de nieuwe rol van TickCacheManager en TICK_FLOW_START te reflecteren)*

1. **Trigger:** ExecutionEnvironment publiceert RAW_TICK.  
2. **TickCacheManager Adapter:** Ontvangt RAW_TICK.  
   * Roept tick_cache_manager.create_cache() -> cache = {}.  
   * Extraheert timestamp, price.  
   * Roept context_provider.start_new_tick(cache, timestamp, price).  
   * Publiceert TICK_FLOW_START (met tick ID / provider ref).  
3. **EMADetector Adapter:** Ontvangt TICK_FLOW_START.  
   * Roept EMADetector.process() aan.  
4. **EMADetector (ContextWorker):**  
   * base_ctx = worker.context_provider.get_base_context()  
   * df = worker.ohlcv_provider.get_window(...)  
   * Berekent EMAOutputDTO.  
   * worker.context_provider.set_result_dto(self, dto).  
   * Retourneert DispositionEnvelope(CONTINUE).  
5. **EMADetector Adapter:** Ontvangt CONTINUE. Raadpleegt wiring_map. Ziet EMACrossOpportunity volgt. Publiceert een *intern sturings-event* specifiek voor de EMACrossOpportunity Adapter (bv. TRIGGER_WORKER_EMACrossOpp).  
6. **EMACrossOpportunity Adapter:** Ontvangt TRIGGER_WORKER_EMACrossOpp.  
   * Roept EMACrossOpportunity.process() aan.  
7. **EMACrossOpportunity (OpportunityWorker):**  
   * required_dtos = worker.context_provider.get_required_dtos(self) -> Haalt EMAOutputDTO uit de *actieve tick cache*.  
   * prev_state = worker.state_provider.get().  
   * Detecteert cross. Update state. Maakt OpportunitySignalDTO.  
   * Retourneert DispositionEnvelope(PUBLISH, event_name="SIGNAL_GENERATED", payload=signal_dto).  
8. **EMACrossOpportunity Adapter:** Ontvangt PUBLISH. Valideert. Roept EventBus.publish("SIGNAL_GENERATED", signal_dto) aan.  
9. **EventBus:** Stuurt SIGNAL_GENERATED naar subscribers.  
10. **(Flow Einde):** Een component (mogelijk de TickCacheManager luisterend naar TICK_FLOW_COMPLETE of de laatste adapter) roept tick_cache_manager.release_cache(cache) aan.

## **5. Testbaarheid**

De DTO-Centric architectuur, gecombineerd met Provider Interfaces en het Enrollment Exposure model voor DTO-deling, maximaliseert de unit-testbaarheid van individuele workers.

* **Duidelijke Contracten:** Tests kunnen exact de benodigde input DTOs mocken (geïmporteerd van de centrale locatie) en de output DTOs (via set_result_dto mock) of DispositionEnvelope valideren.  
* **Geïsoleerde Logica:** Externe afhankelijkheden (data, state, cache, bus) worden via gemockte interfaces aangeleverd/gecontroleerd.  
* **Focus op Functionaliteit:** De test valideert puur de dataverwerkingslogica van de worker.

# Voorbeeld test_plugin_b.py  
from unittest.mock import MagicMock  
# Importeer DTO van centrale locatie  
from backend.dto_reg.s1mple.ema_detector.v1_0_0.ema_output_dto import EMAOutputDTO  
from backend.dtos.pipeline.signal import OpportunitySignalDTO # Systeem DTO  
from backend.core.interfaces.context_provider import ITradingContextProvider  
from backend.shared_dtos.disposition_envelope import DispositionEnvelope  
# ... other imports ...

def test_plugin_b_logic():  
    mock_provider = MagicMock(spec=ITradingContextProvider)  
    test_ema_dto = EMAOutputDTO(ema_20=50.0, ema_50=49.0)  
    # Configureer mock om de DTO terug te geven op basis van type  
    mock_provider.get_required_dtos.return_value = {EMAOutputDTO: test_ema_dto}  
    # ... mock state_provider ...

    worker_b = EMACrossOpportunity(params={})  
    worker_b.context_provider = mock_provider # Inject mocks  
    worker_b.state_provider = mock_state_provider

    result_envelope = worker_b.process()

    # Assertions  
    mock_provider.get_required_dtos.assert_called_once()  
    assert isinstance(result_envelope, DispositionEnvelope)  
    assert result_envelope.disposition == "PUBLISH"  
    assert result_envelope.event_name == "SIGNAL_GENERATED"  
    assert isinstance(result_envelope.event_payload, OpportunitySignalDTO)  
    # ... verify state_provider calls ...

## **6. Belangrijkste Paragraaf in Originele Documentatie ("Hook")**

**Hoofdstuk 5: 5_DE_WORKFLOW_ORKESTRATIE.md, Paragraaf 5.1. Introductie: De Paradigma Shift.**

Deze paragraaf blijft de meest geschikte plek om de fundamentele verschuiving weg van de enriched_df naar het "Point-in-Time", DTO-gedreven model te introduceren. Vanuit hier kan verwezen worden naar dit addendum voor de volledige, gedetailleerde uitwerking.