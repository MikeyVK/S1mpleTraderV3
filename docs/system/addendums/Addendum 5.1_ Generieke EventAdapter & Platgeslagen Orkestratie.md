# **Addendum: Generieke EventAdapter & Platgeslagen Orkestratie**

Status: Concept  
Datum: 2025-10-23  
Gerelateerd aan: Concept: Expliciet Bedraad Netwerk v2, Addendum: Data Landschap & Point-in-Time Architectuur, Addendum 3.8

## **0. Impact op Bestaande Documentatie & Addenda**

Dit addendum introduceert een **tweede fundamentele verschuiving**, voortbouwend op het "Point-in-Time" model: de **eliminatie van de Operator-laag** en de overstap naar een **plat, expliciet bedraad netwerk van workers**, georkestreerd via **generieke EventAdapters**. Deze wijziging heeft een diepgaande impact op vrijwel de gehele architectuurbeschrijving.

### **Impact op Originele docs.md:**

* **Hoofdstuk 1 (1_BUS_COMMUNICATION_ARCHITECTURE.md):**  
  * **Volledig Achterhaald:** Het EventAdapter Patroon zoals beschreven (voor Operators) vervalt. De rol van wiring_map.yaml verandert fundamenteel (wordt UI-gegenereerd). De EventWiringFactory krijgt een andere taak (configureren van *alle* adapters o.b.v. BuildSpecs). Paragraaf 1.8 (Operator Suite) vervalt volledig.  
* **Hoofdstuk 2 (2_ARCHITECTURE.md):**  
  * **Paragraaf 2.4 (Worker Ecosysteem):** De *categorieën* blijven bestaan, maar de aansturing door Operators vervalt.  
  * **Paragraaf 2.7 (Data-Gedreven Operator):** Dit gehele concept **vervalt**.  
  * **Paragraaf 2.11 (Dataflow & Orchestratie):** De beschreven Operator-gedreven flow is vervangen door de expliciete wiring_map en Adapter-gedreven flow.  
* **Hoofdstuk 3 (3_DE_CONFIGURATIE_TREIN.md):**  
  * **operators.yaml:** Dit bestand **vervalt**. De Operator-configuratie wordt irrelevant.  
  * **wiring_map.yaml:** De rol verandert drastisch: wordt UI-gegenereerd, strategie-specifiek, en beschrijft worker-naar-worker bedrading. Introductie platform_wiring_map.yaml.  
  * **Paragraaf 3.8 (Onderlinge Samenhang):** De beschreven flow via Operators is incorrect.  
* **Hoofdstuk 5 (5_DE_WORKFLOW_ORKESTRATIE.md):**  
  * **Gehele Hoofdstuk:** De beschrijving van de Operator-gedreven fases is vervangen door de expliciete, platgeslagen, Adapter-gedreven flow. Paragraaf 5.8 (Rolverdeling Operators) vervalt.  
* **Hoofdstuk 8 (8_DEVELOPMENT_STRATEGY.md):**  
  * Beschrijvingen die verwijzen naar Operator-interactie moeten worden aangepast.  
* **Hoofdstuk 10 (10_CODING_STANDAARDS_DESIGN_PRINCIPLES.md):**  
  * Voorbeelden die BaseOperator gebruiken zijn niet langer van toepassing.

### **Impact op Eerdere Addenda:**

* **Addendum 3.8 (Configuratie & Vertaal Filosofie):**  
  * De kernprincipes (3 Lagen Config, ConfigTranslator, BuildSpecs, OperationService als lifecycle manager) **blijven volledig overeind**. Sterker nog, dit model sluit *beter* aan bij Addendum 3.8.  
  * De BuildSpecs moeten nu echter wiring_specs bevatten die geschikt zijn voor de EventWiringFactory om *alle* adapters (workers + singletons) te configureren, i.p.v. operator_specs.  
* **Addendum: Data Landschap & Point-in-Time Architectuur:**  
  * De kernprincipes (Point-in-Time, DTO-Centric, ITradingContextProvider, TickCacheManager, DispositionEnvelope, DTO-deling) **blijven volledig overeind**.  
  * De interactie met de Adapter (zoals beschreven in Sectie 2.3 en 4 van dat addendum) is nu de *enige* manier van interactie; de Operator als tussenpersoon vervalt.

### **Conclusie Impact Analyse:**

Dit addendum vertegenwoordigt een **radicale vereenvoudiging** van de orkestratielaag door de Operators te verwijderen. Het bouwt direct voort op de principes van Addendum 3.8 en het "Point-in-Time" data model, maar vereist een volledige herziening van de hoofdstukken die de flow en de rol van de (nu verwijderde) Operators beschreven.

## **1. Doel & Positionering**

Dit document beschrijft het ontwerp van de EventAdapter binnen de "platgeslagen" orkestratie-architectuur, waarin de Operator-laag is verwijderd. In dit model krijgt **elke component** (zowel workers als platform singletons) die met de EventBus interacteert, een eigen EventAdapter. Deze adapter fungeert als de **enige interface** van de component met de EventBus.

**Kernprincipe:** De functionele component blijft gefocust op zijn kerntaak; zijn adapter is de poortwachter en **uitvoerder van communicatie-instructies**, volledig gestuurd door expliciete configuratie afkomstig uit de BuildSpecs.

## **2. Ontwerp: Eén Generieke, Configureerbare Klasse**

We opteren voor **één enkele, generieke EventAdapter klasse**. Het specifieke gedrag wordt bepaald door de **configuratie** (wiring_spec fragment) die elke instantie meekrijgt tijdens de bootstrap-fase via de EventWiringFactory.

### **2.1. Kernverantwoordelijkheden van de Adapter:**

1. **Event Ontvangst:** Luisteren naar (en ontvangen van) specifieke events op de EventBus waarop zijn component moet reageren, zoals geconfigureerd in zijn Subscription Lijst.  
2. **Component Aanroep:** De juiste methode op de component-instantie aanroepen met de correcte payload, zoals gedefinieerd in zijn Handler Mapping.  
3. **Output Verwerking:** De geretourneerde DispositionEnvelope van de **component** interpreteren.  
4. **Publicatie Uitvoering (Gespecificeerd):** Handelt alle publicaties af op basis van de DispositionEnvelope en zijn geconfigureerde Publication Configuration.  
   * **Bij CONTINUE:** Zoekt de corresponderende **systeem event(s)** op in zijn configuratie (afkomstig uit wiring_spec, oorspronkelijk wiring_map/base_wiring). Publiceert deze **system event(s)** (met unieke namen gegenereerd tijdens bootstrap) op de EventBus, **inclusief de relevante Systeem DTO payload** (zoals gedefinieerd in de wiring_spec).  
   * **Bij PUBLISH:** Valideert event_name tegen de geconfigureerde Allowed Custom Events. Indien toegestaan, publiceert het **custom event** (zoals gespecificeerd in de DispositionEnvelope) op de EventBus. **Er wordt GEEN payload meegegeven in dit geval**; de data moet door de producerende component al via ITradingContextProvider.set_result_dto() in de TickCache zijn geplaatst.  
   * **Bij STOP:** Publiceert een specifiek **intern _flow_stop_<uuid> event** (zoals geconfigureerd) op de EventBus om het einde van deze flow-tak aan te geven voor resource management (bv. TickCacheManager).

### **2.2. Benodigde Configuratie per Adapter Instantie (via BuildSpecs):**

De EventWiringFactory leest de wiring_specs uit de BuildSpecs (gegenereerd door ConfigTranslator) en configureert elke adapter-instantie met zijn specifieke "instructieset":

* **Component Referentie:** Een verwijzing naar de component-instantie (worker of singleton).  
* **EventBus Referentie:** Een verwijzing naar de singleton EventBus.  
* **Subscription Lijst:** Een lijst van alle event-namen waarop deze adapter moet luisteren.  
* **Handler Mapping:** Een mapping van inkomende event-namen naar component-methoden.  
* **Publication Configuration (Uniform & Gespecificeerd):** Een configuratieobject (afgeleid uit de wiring_specs) dat *alle* mogelijke publicaties definieert die deze adapter mag uitvoeren:  
  * **System Event Publications (CONTINUE):** Een mapping die aangeeft welke *interne systeem event(s)* (met unieke namen en bijbehorende **Systeem DTO types**) gepubliceerd moeten worden als de component CONTINUE retourneert.  
  * **Allowed Custom Events (PUBLISH):** Een lijst van *publieke custom event namen* die de component *mag* publiceren via de PUBLISH disposition.  
  * **Flow Stop Event (STOP):** De naam van het interne stop-event dat gepubliceerd moet worden.

**(Noot:** De ConfigTranslator is verantwoordelijk voor het correct afleiden van deze configuratie uit platform_wiring_map.yaml, base_wiring.yaml, en manifest.yaml bestanden en het plaatsen ervan in de wiring_specs.)**

## **3. Communicatie via de Centrale EventBus**

Het model gebruikt **uitsluitend** de centrale EventBus als een **pure N-N broadcast bus**. Het onderscheid zit in het *type event naam* (intern vs. publiek), zoals bepaald door de configuratie en uitgevoerd door de adapter:

1. **Gesimuleerde Gerichte Flow Control (via Unieke Interne Events):** Gebruikt voor CONTINUE disposition en STOP signalering. Deze events bevatten Systeem DTO payloads voor de flow.  
2. **Broadcast Communicatie (via Publieke Events):** Gebruikt voor PUBLISH disposition. Deze events bevatten **geen** payload (data zit in TickCache).

## **4. De Rol van de EventWiringFactory (Verfijnd)**

De EventWiringFactory is de **configurator** van de adapters, volledig gestuurd door de BuildSpecs:

1. **Leest BuildSpecs:** Ontvangt platform_wiring_spec en strategy_wiring_spec van de OperationService.  
2. **Creeërt Adapters:** Instantieert een generieke EventAdapter voor elke component die bedraad moet worden.  
3. **Configureert Adapters:** Gebruikt de details uit de wiring_specs om elke adapter zijn **volledige Publication Configuration** (system, custom, stop events) en andere instructies te geven, inclusief het genereren van interne event-namen.  
4. **Validatie:** Werkt samen met EventChainValidator (die ook BuildSpecs/wiring_specs leest) om de geconfigureerde topologie te valideren.

## **5. Voordelen**

* **Radicale Vereenvoudiging:** Eliminatie van de Operator-laag.  
* **SRP Behoud:** Componenten puur. Adapters voeren communicatie-instructies uit. EventBus is broadcast. EventWiringFactory configureert o.b.v. BuildSpecs. ConfigTranslator bepaalt *wat* geconfigureerd wordt.  
* **Expliciete Flow & Contracten:** Alle verbindingen expliciet via wiring_specs. Duidelijk onderscheid payload-dragende systeem events en payload-loze custom events.  
* **Uniformiteit:** Alle componenten gebruiken DispositionEnvelope. Publicaties via adapter.  
* **Flexibiliteit:** Ondersteunt standaard flow en custom events via hetzelfde adapter-mechanisme.  
* **Testbaarheid:** Generieke adapter testbaar. Componenten testbaar.  
* **Schaalbaarheid:** Conceptueel schaalbaar.  
* **Flow Controle:** Gecontroleerde flow-beëindiging via STOP event.

Dit concept legt de basis voor de EventAdapter als de **uniforme uitvoerder van communicatie-instructies** in het platgeslagen model, nu volledig in lijn met de BuildSpec-gedreven bootstrap, strikte SRP, gecontroleerde flow-beëindiging en een scherp onderscheid tussen systeem- en custom events.

## **6. Belangrijkste Paragraaf in Originele Documentatie ("Hook")**

**Hoofdstuk 5: 5_DE_WORKFLOW_ORKESTRATIE.md, Paragraaf 5.1. Introductie: De Paradigma Shift.**

Deze paragraaf blijft de meest geschikte plek om de fundamentele verschuivingen in de orkestratie te introduceren. De *inhoud* moet nu verwijzen naar **zowel** de verschuiving naar het "Point-in-Time" data model **als** de verschuiving naar de platgeslagen, Adapter-gedreven orkestratie zonder Operators, zoals beschreven in dit addendum.