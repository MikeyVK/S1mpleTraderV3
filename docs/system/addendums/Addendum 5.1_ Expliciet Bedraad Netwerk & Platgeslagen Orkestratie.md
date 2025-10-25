# **Addendum: Expliciet Bedraad Netwerk & Platgeslagen Orkestratie**

Status: Definitief Concept  
Datum: 2025-10-23  
Gerelateerd aan: Addendum: Data Landschap & Point-in-Time Architectuur, Addendum 3.8, Concept: De Generieke EventAdapter

## **0\. Impact op Bestaande Documentatie**

Dit addendum introduceert een **fundamentele herstructurering van de orkestratielaag**, waarbij de Operator-componenten worden geëlimineerd en de communicatie volledig expliciet wordt gemaakt via een UI-gegenereerde strategy\_wiring\_map en BuildSpecs. Dit heeft een **zeer significante impact** op de bestaande documentatie:

### **Originele docs.md:**

* **Hoofdstuk 1 (1\_BUS\_COMMUNICATION\_ARCHITECTURE.md):**  
  * De rol van wiring\_map.yaml verandert fundamenteel (wordt platform\_wiring\_map \+ UI-gegenereerde strategy\_wiring\_map).  
  * Het concept van EventAdapter per Operator vervalt; wordt EventAdapter per component (worker/singleton).  
  * De beschrijving van de bootstrap-fase is achterhaald.  
* **Hoofdstuk 2 (2\_ARCHITECTURE.md):**  
  * **Paragraaf 2.4 (Worker Ecosysteem):** De *categorieën* blijven bestaan, maar de *aansturing* via Operators vervalt.  
  * **Paragraaf 2.7 (Data-Gedreven Operator):** Het hele concept van de BaseOperator **vervalt**.  
  * **Paragraaf 2.11 (Dataflow & Orchestratie):** De beschrijving van de Operator-gedreven flow is **volledig vervangen** door de expliciete, adapter-gedreven flow.  
* **Hoofdstuk 3 (3\_DE\_CONFIGURATIE\_TREIN.md):**  
  * De rol van operators.yaml **vervalt**.  
  * De rol van wiring\_map.yaml splitst in platform\_wiring\_map.yaml, base\_wiring.yaml en de UI-gegenereerde strategy\_wiring\_map.yaml. De beschrijving is achterhaald.  
  * De beschrijving van de "Configuratie Trein in Actie" is **volledig vervangen** door de BuildSpec-gedreven bootstrap.  
* **Hoofdstuk 5 (5\_DE\_WORKFLOW\_ORKESTRATIE.md):**  
  * **Gehele hoofdstuk is fundamenteel achterhaald.** De Operator-gedreven fases vervallen. De workflow wordt nu bepaald door de expliciete wiring\_map.  
  * **Paragraaf 5.1 (Introductie: De Paradigma Shift):** Blijft de **centrale "hook"**, maar moet nu verwijzen naar de verschuiving naar het *platgeslagen, expliciet bedrade* model.  
* **Hoofdstuk 6 (6\_FRONTEND\_INTEGRATION.md):**  
  * De beschrijving van de "Operator Configuration UI" **vervalt**.  
  * De "Strategy Builder" UI krijgt een **veel centralere rol** als generator van de strategy\_wiring\_map.yaml.  
* **Hoofdstuk 8 (8\_DEVELOPMENT\_STRATEGY.md):**  
  * De workflow verandert: geen Operator-context meer. Focus ligt op worker I/O en DispositionEnvelope.  
* **Hoofdstuk 9 (9\_META\_WORKFLOWS.md):**  
  * De services (OptimizationService, etc.) roepen nog steeds OperationService aan, maar de *interne werking* van die service verandert door de nieuwe bootstrap.  
* **Hoofdstuk 10 (10\_CODING\_STANDAARDS\_DESIGN\_PRINCIPLES.md):**  
  * Principes blijven geldig, maar voorbeelden die verwijzen naar Operators moeten worden aangepast.

### **Voorgaande Addenda:**

* **Addendum 3.8 (Configuratie & Vertaal Filosofie):** Dit addendum **blijft cruciaal** en wordt **versterkt**. De ConfigTranslator en BuildSpecs (inclusief wiring\_specs) zijn nu *essentieel* voor het functioneren van dit platgeslagen model. De rol van OperationService als levenscyclus-manager wordt nog duidelijker.  
* **Addendum: Data Landschap & Point-in-Time Architectuur:** Dit addendum **blijft volledig geldig en noodzakelijk**. Het definieert het "WAT" (de data DTOs, ITradingContextProvider, TickCacheManager). Dit huidige addendum definieert het "HOE" (de communicatie-flow zonder Operators). De DispositionEnvelope en TickCacheManager interacties zijn consistent.  
* **Concept: De Generieke EventAdapter:** Dit concept wordt **geformaliseerd en verfijnd** door dit addendum. De adapter wordt geconfigureerd via de wiring\_specs uit de BuildSpecs.

**Conclusie Impact:** Dit addendum vervangt effectief de gehele Operator-laag en de bijbehorende orkestratie-logica zoals beschreven in de originele documentatie. Het bouwt direct voort op Addendum 3.8 en Addendum: Data Landschap.

## **1\. Probleemstelling & Doel**

Voorgaande modellen introduceerden complexiteit door Operators of complexe Adapters. Dit model streeft naar een **radicale vereenvoudiging** door de orkestratielaag plat te slaan en de communicatie volledig expliciet te maken, gestuurd door configuratie die deels door de UI wordt gegenereerd en gevalideerd wordt tegen plugin-manifesten.

**Doel:** Een architectuur ontwerpen die:

1. De Operator-laag **elimineert**.  
2. De EventBus als een **pure N-N broadcast-bus** handhaaft.  
3. De **Strategy Builder UI** in staat stelt een **complete, strategie-specifieke strategy\_wiring\_map te genereren**, gebaseerd op templates (base\_wiring) en plugin-manifesten.  
4. De **kennis van de plugin** (type, sub-type, event-declaraties) centraal stelt.  
5. Strikt de **SRP** volgt voor alle componenten, inclusief de ConfigTranslator, EventWiringFactory en EventAdapter.  
6. Integreert met de **BuildSpec**\-filosofie uit Addendum 3.8.

## **2\. De Oplossing: Expliciete Bedrading via BuildSpecs (Gevoed door UI & Manifesten)**

Het kerninzicht is dat de runtime bedrading wordt gedefinieerd door wiring\_specs binnen de BuildSpecs. Deze wiring\_specs worden samengesteld door de ConfigTranslator, die input haalt uit **alle relevante bronnen**: statische platform configuratie (platform\_wiring\_map), een UI-gegenereerde strategy\_wiring\_map (die zelf gebaseerd is op een base\_wiring template en manifesten), en de manifesten van de gebruikte plugins voor validatie/verrijking. Alle wiring configuraties gebruiken (conceptueel) dezelfde WiringRule structuur.

### **2.1. Definitie: De Uniforme WiringRule Structuur**

Elke "bedrading" in *elk* van de wiring-gerelateerde configuratiebestanden en de uiteindelijke wiring\_spec volgt (conceptueel) deze structuur:

\# Conceptuele structuur van één wiring regel  
\- wiring\_id: "unique\_identifier\_for\_this\_rule" \# Uniek binnen de map/spec  
  source:  
    \# Wie publiceert het triggerende event?  
    component\_id: "component\_instance\_id\_or\_category\_or\_singleton\_id"  
    event\_name: "EVENT\_NAME\_PUBLISHED\_BY\_SOURCE"  
    event\_type: "SystemEvent | CustomEvent"

  target:  
    \# Wie moet reageren?  
    component\_id: "component\_instance\_id\_or\_category\_or\_singleton\_id"  
    handler\_method: "method\_to\_call\_on\_target"

  \# Optioneel: Voorwaardelijke logica  
  condition: "optional\_condition\_string\_or\_object"

### **2.2. De Componenten van de Configuratie-Puzzel**

1. **strategy\_blueprint.yaml (De "Strategie Blauwdruk"):** Definieert de **workforce** (welke plugin-instanties (instance\_id) met welke plugin\_name en params). Blijft de basis voor *welke* workers er zijn.  
2. **base\_wiring.yaml (De "Standaard Bouwplaat"):** Een configureerbaar template dat de *standaard* logische flow beschrijft tussen worker-**categorieën**.  
   * Bevat een lijst wiring\_rules, waarbij source.component\_id en target.component\_id verwijzen naar **categorie-namen** (bv. "ContextWorker").  
   * Alle source.event\_type in dit bestand zijn per definitie **SystemEvent**. De source.event\_name definieert de logische output van een categorie (bv. "ContextOutput").  
   * Dient als input voor de UI en ConfigTranslator. Wordt *nooit rechtstreeks* gebruikt voor runtime.

\# Voorbeeld base\_wiring.yaml  
base\_wiring\_id: "standard\_trading\_flow\_v1"  
wiring\_rules:  
  \- wiring\_id: "ctx\_to\_opp"  
    source: { component\_id: "ContextWorker", event\_name: "ContextOutput", event\_type: "SystemEvent" }  
    target: { component\_id: "OpportunityWorker", handler\_method: "process" } \# process is default  
  \- wiring\_id: "opp\_to\_plan\_entry"  
    source: { component\_id: "OpportunityWorker", event\_name: "OpportunityOutput", event\_type: "SystemEvent" }  
    target: { component\_id: "PlanningWorker", handler\_method: "process" }  
    condition: { target\_subtype: "entry\_planning" } \# Stuur alleen naar entry planners  
  \# ... etc.

3. **manifest.yaml (De "Intelligentie" van een Stukje):** Definieert de I/O, capabilities, en **Custom Event** declaraties (publishes, wirings) van een *enkele plugin*.  
   * publishes: Definieert CustomEvents die de plugin *kan* produceren (via DispositionEnvelope). Bevat event\_name. Payload zit in TickCache.  
   * wirings: Definieert op welke SystemEvents of CustomEvents (listens\_to) de plugin wil reageren en welke *methode* (invokes.method) aangeroepen moet worden.  
4. **strategy\_wiring\_map.yaml (Gegenereerd door UI \- de “Strategie bedrading”):** Dit bestand is het **resultaat** van de Strategy Builder UI voor *één specifieke strategie*. Het legt de **concrete bedrading** vast.  
   * **Inhoud:** Een **lijst van WiringRules**. Deze lijst is een *concrete invulling* van de gekozen base\_wiring.yaml, rekening houdend met:  
     * De specifieke **worker-instanties** (instance\_id uit strategy\_blueprint.yaml) die in de slots zijn geplaatst. source.component\_id en target.component\_id verwijzen nu naar deze instance\_ids.  
     * De **logische positionering** (serieel/parallel). Bij seriële positionering binnen een slot genereert de UI **extra interne SystemEvents** en bijbehorende WiringRules om de keten te vormen (bv. worker\_A\_output \-\> worker\_B\_input). Bij parallelle positionering worden meerdere workers aan dezelfde source.event\_name gekoppeld.  
     * De **CustomEvent wirings** uit de manifesten van de gebruikte plugins. De UI voegt hiervoor expliciete WiringRules toe aan de lijst, waarbij source.event\_type CustomEvent is en target verwijst naar de luisterende worker-instantie en methode.  
   * Dit bestand bevat dus een expliciete, complete lijst WiringRules met zowel **Systeem Events** als **Custom Events**, allemaal gekoppeld aan *specifieke worker-instanties*. Het is de **enige input** voor de ConfigTranslator m.b.t. strategie-bedrading.  
5. **platform\_wiring\_map.yaml (Statisch Platform):** Definieert de **bedrading voor de operation-brede singleton componenten**.  
   * Bevat een lijst wiring\_rules, waarbij source.component\_id en target.component\_id verwijzen naar de **ID's van de singleton componenten** (bv. "TickCacheManager").  
   * Alle source.event\_type zijn per definitie **SystemEvent**.  
6. **ConfigTranslator (De Puzzellegger \- Addendum 3.8):**  
   * **Input:** Leest *alle* relevante configuratie (platform\_config, operation\_config (incl. platform\_wiring\_map.yaml), strategy\_config (incl. de **gegenereerde strategy\_wiring\_map.yaml**)). **Leest GEEN manifesten meer voor wiring-info; die info zit al verwerkt in de strategy\_wiring\_map.yaml.**  
   * **Output:** **Genereert de BuildSpecs**, inclusief:  
     * platform\_wiring\_spec: Een machine-leesbare specificatie (lijst WiringRules) afgeleid van platform\_wiring\_map.yaml.  
     * strategy\_wiring\_spec: Een machine-leesbare specificatie (lijst WiringRules) **direct overgenomen of gevalideerd** uit de strategy\_wiring\_map.yaml.  
7. **BuildSpecs (De Machine-Instructie):** Bevat alle genormaliseerde instructies, inclusief de platform\_wiring\_spec en strategy\_wiring\_spec.

### **2.3. De Workflow in de Strategy Builder UI: Intelligente Generatie**

Dit is waar alles samenkomt:

1. **Start:** De gebruiker kiest een base\_wiring.yaml template. De UI toont de lege "slots" voor de categorieën.  
2. **Drag & Drop (Standaard Flow) met Positie-Intelligentie:**  
   * De gebruiker sleept twee ema\_detector plugins (niet-event-capable) in het ContextWorker slot. Hij kan ze **visueel positioneren om een seriële (opeenvolgende) of parallelle (gelijktijdige) verwerking** aan te duiden.  
   * **Slimme Generatie (Serieel):** Als ema\_fast logisch *voor* ema\_slow wordt geplaatst, genereert de UI een wiring\_map die een keten creëert:  
     * ContextReady \-\> ema\_fast  
     * Output van ema\_fast \-\> ema\_slow  
     * Output van ema\_slow \-\> OpportunityWorker categorie  
   * **Slimme Generatie (Parallel):** Als ze logisch *parallel* worden geplaatst, genereert de UI een wiring\_map die een fan-out/fan-in creëert:  
     * ContextReady \-\> ema\_fast  
     * ContextReady \-\> ema\_slow  
     * Output van ema\_fast EN ema\_slow worden beide als input voor de OpportunityWorker categorie bedraad.  
   * **Event Naming:** De UI genereert unieke, interne event-namen (bv. ema\_fast\_OUTPUT, ema\_slow\_OUTPUT) om deze verbindingen te realiseren, volledig transparant voor de gebruiker.  
3. **Drag & Drop (Event-Capable Worker):**  
   * De gebruiker sleept een emergency\_news\_monitor in een "parallel/zwevend" gedeelte.  
   * De UI **leest het manifest.yaml** en ziet:  
     * subscribes\_to: \["ExternalNewsFeed"\]  
     * publishes: \["EMERGENCY\_HALT\_TRADING"\]  
   * **Visuele Feedback:** De UI tekent automatisch de verbindingen. Als een andere geplaatste worker (bv. een ExecutionWorker) luistert naar EMERGENCY\_HALT\_TRADING, wordt de lijn direct doorgetrokken en de verbinding visueel gemaakt.  
4. **Generatie van strategy\_wiring\_map.yaml:**  
   * Wanneer de gebruiker opslaat, combineert de UI alle informatie: de base\_wiring, de instance\_id's, de logische positionering (serieel/parallel), en de manifest-declaraties van event-capable workers.  
   * Dit resulteert in een **complete, expliciete lijst van WiringRules** die de *enige* bron van waarheid is voor de runtime en de *volledige* bedrading voor deze strategie beschrijft.

### **2.4. De Koppeling in operation.yaml**

operation.yaml wordt de plek waar alles samenkomt.

**Voorbeeld operation.yaml:**

strategy\_links:  
  \- strategy\_link\_id: "my\_live\_btc\_strategy"  
    is\_active: true  
    execution\_environment\_id: "live\_kraken\_main"  
      
    \# De strategie zelf wordt nu gedefinieerd door de combinatie  
    \# van de "stukjes" en de "bedrading".  
    strategy\_config:  
      blueprint\_id: "my\_btc\_blueprint\_v3" \# Verwijst naar strategy\_blueprint.yaml  
      wiring\_map\_id: "generated\_wiring\_for\_v3" \# Verwijst naar de gegenereerde wiring\_map.yaml

## 

## **3\. De Rol van de Componenten**

* **Worker:** Blijft puur. Ontvangt input via Adapter, retourneert DispositionEnvelope. Communiceert data via ITradingContextProvider.  
* **EventAdapter (Generiek):** Blijft de "domme" uitvoerder. Wordt geconfigureerd met zijn specifieke Subscription Lijst, Handler Mapping en Publication Configuration **uit de wiring\_spec**. Weet niets van YAML, manifesten of de bredere context.  
* **EventWiringFactory:** Wordt nog zuiverder. Zijn *enige* taak is het lezen van de platform\_wiring\_spec en strategy\_wiring\_spec **uit de BuildSpecs** en op basis daarvan de EventAdapters te **instantiëren en configureren** met de exacte instructies uit die specs.  
  * **wire\_platform\_singletons(platform\_wiring\_spec, ...)**: Configureert adapters voor singletons tijdens bootstrap.  
  * **wire\_strategy\_instance(strategy\_wiring\_spec, ...)**: Configureert adapters voor workers van één strategie.  
* **ConfigTranslator:** Is de **enige** component die *alle* configuratiebronnen leest (incl. platform\_wiring\_map, base\_wiring, de UI-gegenereerde strategy\_wiring\_map  en deze vertaalt naar de machine-leesbare BuildSpecs, inclusief de gedetailleerde wiring\_specs.  
* **EventChainValidator:** Leest de wiring\_specs **uit de BuildSpecs** om de uiteindelijke, geplande topologie te valideren.

## **4\. Voordelen van dit Finale Model**

* **Maximale SRP:** Elke component heeft een extreem afgebakende taak. ConfigTranslator denkt & valideert cross-config, Factories bouwen/configureren o.b.v. BuildSpecs, Adapters voeren uit, Workers rekenen.  
* **Zuivere Scheiding Config vs. Runtime:** Complexiteit zit in ConfigTranslator (bootstrap). Runtime componenten zijn eenvoudig.  
* **Intuïtieve UI-Gedreven Configuratie:** UI ontwerpt de flow, resulterend in een expliciete strategy\_wiring\_map.  
* **Expliciet & Valideerbaar:** wiring\_specs zijn de complete, eenduidige specificatie.  
* **Testbaarheid:** Alle componenten zeer goed testbaar.  
* **Flexibiliteit & Consistentie:** Ondersteunt standaard flows (Systeem Events) en complexe interacties (Custom Events) uniform.

## **5\. Belangrijkste Paragraaf in Originele Documentatie ("Hook")**

**Hoofdstuk 5: 5\_DE\_WORKFLOW\_ORKESTRATIE.md, Paragraaf 5.1. Introductie: De Paradigma Shift.**

Deze paragraaf blijft de meest geschikte plek om de fundamentele verschuiving weg van de Operator-gedreven orkestratie naar het **platgeslagen, expliciet bedrade model** te introduceren. Vanuit hier kan verwezen worden naar dit addendum voor de volledige, gedetailleerde uitwerking.

