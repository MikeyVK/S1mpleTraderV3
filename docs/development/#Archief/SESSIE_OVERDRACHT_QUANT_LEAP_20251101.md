# **[ARCHIVED] Sessie Overdracht: De "Quant Leap" Architectuur**

> **⚠️ ARCHIEF DOCUMENT**  
> **Datum Archivering:** 2 november 2025  
> **Reden:** Geformaliseerd in [OBJECTIVE_DATA_PHILOSOPHY.md](../../architecture/OBJECTIVE_DATA_PHILOSOPHY.md)  
> **Status:** Referentie - Originele besluitvorming sessie overdracht  
> **Gebruik:** Bewaard voor historische context. Voor actuele implementatie zie de officiële architectuur docs.

Datum Origineel: 1 november 2025  
Status Origineel: Architectuur Definitief (Conceptueel)  
Doel: Gedetailleerde analyse van de verschuiving van een dwingend SWOT-model naar een objectief, flexibel data-leveranciersmodel, en de impact hiervan op de V3-architectuur en documentatie.

## **1\. Executive Summary: De "Quant Leap"**

Naar aanleiding van ons gesprek hebben we een cruciale architecturale beslissing genomen die de flexibiliteit en 'quant-vriendelijkheid' van het S1mpleTrader V3 platform fundamenteel versterkt.

De Beslissing (De "Quant Leap"):  
We verwijderen de subjectieve SWOT-aggregatielaag (Strengths/Weaknesses) uit het platform. De architectuur wordt gezuiverd tot een puur objectief data-leveranciersmodel, waarbij de volledige verantwoordelijkheid voor interpretatie bij de consumerende workers (plugins) ligt.  
**Kernpunten van de Nieuwe Architectuur:**

1. **ContextWorkers \= Objectieve Feiten:** ContextWorkers \[cite: docs/architecture/WORKER\_TAXONOMY.md\] produceren **geen** oordelen (zoals "Strength" of "Weakness"). Hun *enige* verantwoordelijkheid is het publiceren van objectieve, feitelijke DTOs (Data Transfer Objects) naar de TickCache, zoals MarketStructureDTO(bos\_detected=True) of EMAOutputDTO(ema\_20=50100.50) \[cite: docs/architecture/POINT\_IN\_TIME\_MODEL.md\].  
2. **Consumenten \= Subjectieve Tolken:** OpportunityWorkers, ThreatWorkers en StrategyPlanners \[cite: docs/architecture/WORKER\_TAXONOMY.md\] zijn nu de *enige* componenten die subjectieve interpretatie toepassen. Zij consumeren de feitelijke DTOs uit de TickCache en passen hun eigen, ingekapselde logica toe (bv. "voor mijn strategie *is* een EMAOutputDTO boven de 200-lijn een kans").  
3. **Taxonomie \= Beschrijvende Labels:** De 27+ sub-categorieën (bv. TECHNICAL\_PATTERN, PORTFOLIO\_RISK) \[cite: docs/architecture/WORKER\_TAXONOMY.md\] zijn **niet** dwingend. Het zijn puur beschrijvende *labels* (tags) in het manifest.yaml \[cite: docs/architecture/PLUGIN\_ANATOMY.md\] die helpen bij filtering, documentatie en de UI, maar ze leggen geen architecturale regels of interfaces op.

Deze verschuiving sluit perfect aan bij de kernprincipes "Plugin First" en "Separation of Concerns" \[cite: docs/architecture/CORE\_PRINCIPLES.md\], en maakt het platform aanzienlijk krachtiger voor kwantitatieve analyse.

Impact op Documentatie:  
Deze beslissing maakt diverse documenten en componenten obsoleet (bv. ContextAggregator, AggregatedContextAssessment.py, decision\_framework.md). Dit document dient als de nieuwe bron van waarheid en stelt een actieplan op om de documentatie op te schonen.

## **2\. De Architecturale Verschuiving in Detail**

### **Principe 1: ContextWorkers als Objectieve Data-leveranciers**

De rol van de ContextWorker \[cite: docs/architecture/WORKER\_TAXONOMY.md\] wordt helderder en eenvoudiger.

* **VEROUDERD (SWOT-model):** Een ContextWorker berekent een EMA, classificeert deze als "bullish" (een "Strength"), en een ContextAggregator \[cite: docs/development/\#Archief/STRATEGY\_PIPELINE\_ARCHITECTURE.md\] berekent een gewogen "Strength Score".  
* **NIEUW (Objectief Model):** Een ContextWorker berekent de EMA.  
  * **Input:** BaseContextDTO (voor de timestamp en asset) \[cite: docs/development/\#Archief/ITRADINGCONTEXTPROVIDER\_DESIGN.md\].  
  * **Capability:** IOhlcvProvider (om de prijsdata op te halen) \[cite: docs/architecture/PLUGIN\_ANATOMY.md\].  
  * **Logica:** ema\_20 \= ohlcv\_data\['close'\].ewm(span=20).mean().iloc\[-1\]  
  * **Output:** self.strategy\_cache.set\_result\_dto(self, EMAOutputDTO(ema\_20=ema\_20)) \[cite: docs/architecture/POINT\_IN\_TIME\_MODEL.md, docs/architecture/DATA\_FLOW.md\].

De ContextWorker heeft **geen oordeel** over de ema\_20. Het is slechts een feit. De TickCache \[cite: docs/architecture/POINT\_IN\_TIME\_MODEL.md\] wordt een *verzameling van objectieve feiten* over de markt op dat specifieke "Point-in-Time".

### **Principe 2: Consumenten (Plugins) als Subjectieve Tolken**

De volledige verantwoordelijkheid voor interpretatie verschuift naar de consumerende workers (OpportunityWorker, ThreatWorker, StrategyPlanner).

* **VOORBEELD 1: Trend-Following Opportunity Worker**  
  * **manifest.yaml:**  
    dependencies:  
      requires\_dtos:  
        \- source: "backend.dto\_reg.s1mple.ema\_detector.v1\_0\_0.ema\_output\_dto"  
          dto\_class: "EMAOutputDTO"

  * **worker.py (pseudo-code):**  
    \# Haalt feiten op uit de TickCache  
    dtos \= self.strategy\_cache.get\_required\_dtos(self)  
    ema\_data \= dtos.get(EMAOutputDTO)  
    price \= self.strategy\_cache.get\_base\_context().current\_price

    \# SUBJECTIEVE INTERPRETATIE (de "quant logic")  
    if price \> ema\_data.ema\_20:  
        \# Mijn logica interpreteert dit als een kans  
        return DispositionEnvelope(  
            disposition="PUBLISH",  
            event\_name="OPPORTUNITY\_DETECTED",  
            event\_payload=OpportunitySignal(confidence=0.7)  
        )  
    return DispositionEnvelope(disposition="CONTINUE")

* **VOORBEELD 2: Mean-Reversion Opportunity Worker (Contradictorisch)**  
  * **manifest.yaml:** (Vereist dezelfde DTO)  
  * **worker.py (pseudo-code):**  
    dtos \= self.strategy\_cache.get\_required\_dtos(self)  
    ema\_data \= dtos.get(EMAOutputDTO)  
    price \= self.strategy\_cache.get\_base\_context().current\_price

    distance \= (price \- ema\_data.ema\_20) / ema\_data.ema\_20

    \# SUBJECTIEVE INTERPRETATIE (tegengestelde logica)  
    if distance \> 0.05: \# Prijs is 5% boven de EMA  
        \# Mijn logica interpreteert dit als 'overbought' (een kans om te shorten)  
        return DispositionEnvelope(  
            disposition="PUBLISH",  
            event\_name="OPPORTUNITY\_DETECTED",  
            event\_payload=OpportunitySignal(direction="short", confidence=0.8)  
        )  
    return DispositionEnvelope(disposition="CONTINUE")

Deze twee workers, die *dezelfde objectieve feiten* consumeren, komen tot *tegengestelde conclusies*, wat de kern is van een flexibel kwantitatief platform. Het platform faciliteert de feiten, de plugins bevatten de mening.

### **Principe 3: Taxonomie als Beschrijvende Labels**

De WORKER\_TAXONOMY.md \[cite: docs/architecture/WORKER\_TAXONOMY.md\] en PLUGIN\_ANATOMY.md \[cite: docs/architecture/PLUGIN\_ANATOMY.md\] blijven geldig, maar de *semantiek* van de subtype verandert.

* **type (Hoofdcategorie):** Blijft een **dwingende architecturale rol**.  
  * context\_worker: *Mag alleen* naar TickCache schrijven via set\_result\_dto().  
  * opportunity\_worker: *Mag* OpportunitySignal publiceren via DispositionEnvelope.  
  * ...etc.  
* **subtype (Sub-categorie):** Wordt een **beschrijvend label (tag)**.  
  * **manifest.yaml:**  
    identification:  
      type: "context\_worker" \# Dwingende ROL  
      subtype: "indicator\_calculation" \# Beschrijvend LABEL

  * **Doel van subtype:**  
    1. **Documentatie:** Helpt ontwikkelaars te begrijpen wat de plugin doet.  
    2. **Filtering:** Stelt de UI (Strategy Builder) in staat om plugins te groeperen (bv. "Toon mij alle indicator\_calculation plugins").  
  * Het platform zal **geen** validatie meer uitvoeren op basis van subtype. Een context\_worker met subtype: "indicator\_calculation" is architectonisch identiek aan een met subtype: "structural\_analysis".

## **3\. Impact Analyse: Verouderde Componenten & Documentatie**

Deze "Quant Leap" vereenvoudigt de architectuur aanzienlijk en maakt de volgende componenten en documenten overbodig (obsoleet).

### **3.1. Obsolete Componenten (Implementatie)**

De volgende DTOs en platformcomponenten **VERVALLEN** en moeten uit de codebase en IMPLEMENTATION\_STATUS.md \[cite: docs/implementation/IMPLEMENTATION\_STATUS.md\] verwijderd worden:

1. **backend/dtos/strategy/context\_factor.py** \[cite: backend/dtos/strategy/context\_factor.py\]  
   * **Reden:** Dit DTO was de drager voor individuele "Strength" of "Weakness" scores. Aangezien ContextWorkers geen oordelen meer vellen, vervalt dit DTO.  
2. **backend/dtos/strategy/aggregated\_context\_assessment.py** \[cite: backend/dtos/strategy/aggregated\_context\_assessment.py\]  
   * **Reden:** Dit DTO was de output van de ContextAggregator en bevatte de geaggregeerde strength en weakness scores. Deze hele aggregatielaag vervalt.  
3. **backend/core/context\_factors.py** \[cite: backend/core/context\_factors.py\]  
   * **Reden:** Dit was de FactorRegistry voor het beheren van de ContextFactor types. Aangezien het DTO vervalt, vervalt de registry ook.  
4. **ContextAggregator (Platform Component)**  
   * **Reden:** Deze component, beschreven in STRATEGY\_PIPELINE\_ARCHITECTURE.md \[cite: docs/development/\#Archief/STRATEGY\_PIPELINE\_ARCHITECTURE.md\] als Fase 1b, had als enige taak het aggregeren van ContextFactor DTOs. Aangezien deze DTOs vervallen, vervalt de ContextAggregator in zijn geheel.

### **3.2. Obsolete Documentatie (Archivering)**

De volgende documenten zijn nu **achterhaald** en moeten worden verplaatst naar docs/development/\#Archief/ om verwarring te voorkomen:

1. **docs/development/\#Archief/decision\_framework.md** \[cite: docs/development/\#Archief/decision\_framework.md\]  
   * **Reden:** Dit document beschrijft *volledig* het SWOT-raamwerk (Maxi-Maxi, Mini-Maxi, etc.) en de ContextAggregator die we zojuist hebben afgeschaft.

### **3.3. Documentatie die Aanpassing Vereist (MODIFICATIE)**

De volgende documenten blijven grotendeels correct, maar moeten worden bijgewerkt om de nieuwe filosofie te weerspiegelen:

1. **docs/development/\#Archief/STRATEGY\_PIPELINE\_ARCHITECTURE.md**  
   * **Aanpassing:** Fase 1b (Context Aggregatie) moet worden **verwijderd**. De pipeline versimpelt van 6+1 fases naar 6 fases. De flow gaat nu direct van Fase 1a (Context Analyse) naar Fase 2 (Opportunity/Threat Detectie).  
   * **Aanpassing:** Alle verwijzingen naar ContextAssessment DTO als input voor StrategyPlanner (Fase 3\) moeten worden vervangen door: "De StrategyPlanner consumeert de *rauwe* context DTOs (bv. EMAOutputDTO, MarketStructureDTO) direct uit de TickCache."  
2. **docs/architecture/WORKER\_TAXONOMY.md** \[cite: docs/architecture/WORKER\_TAXONOMY.md\]  
   * **Aanpassing:** De beschrijving van de 5 hoofdcategorieën blijft **correct** (dit is de architecturale ROL).  
   * **Aanpassing:** De beschrijving van de *sub-categorieën* moet worden herschreven. Het moet duidelijk stellen dat dit **beschrijvende labels (tags)** zijn voor filtering en documentatie, en *geen* dwingende contracten.  
   * **Aanpassing:** De Mermaid-diagrammen moeten worden bijgewerkt om de ContextAggregator te verwijderen.  
3. **docs/architecture/DATA\_FLOW.md** \[cite: docs/architecture/DATA\_FLOW.md\]  
   * **Aanpassing:** De diagrammen en tekst moeten de ContextAggregator verwijderen. De flow "ContextWorker \-\> TickCache" en "OpportunityWorker \-\> TickCache (read)" wordt nu *nog* belangrijker en moet benadrukt worden.  
4. **docs/architecture/PLUGIN\_ANATOMY.md** \[cite: docs/architecture/PLUGIN\_ANATOMY.md\]  
   * **Aanpassing:** De beschrijving van het manifest.yaml subtype veld moet expliciet vermelden dat dit een *beschrijvend label* is en geen functionele impact heeft op de uitvoering, in tegenstelling tot het type veld, dat de ROL definieert.  
5. **docs/development/\#Archief/CONTEXT\_SIGNAL\_DEPENDENCY\_ANALYSIS.md** \[cite: docs/development/\#Archief/CONTEXT\_SIGNAL\_DEPENDENCY\_ANALYSIS.md\]  
   * **Aanpassing:** Dit document is grotendeels *correcter* geworden. Het analyseert reeds de directe dependency tussen OpportunityWorkers en ContextWorker-DTOs (zoals MarketStructureDTO). De verwijzingen naar MarketRegimeDTO als een soort S/W score moeten worden geherformuleerd naar "objectief feit".

## **4\. De Gezuiverde V3 Architectuur (De Nieuwe Waarheid)**

Dit beschrijft de volledige, vereenvoudigde dataflow van begin tot eind, met de "Quant Leap" filosofie als basis.

### **Fase 0: Bootstrap & Configuratie**

* **Componenten:** ConfigLoader, ConfigValidator, ConfigTranslator, Factories \[cite: docs/architecture/LAYERED\_ARCHITECTURE.md, docs/system/addendums/Addendum\_ 3.8 Configuratie en Vertaal Filosofie.md\].  
* **Flow:**  
  1. Alle YAMLs worden geladen \[cite: docs/architecture/CONFIGURATION\_LAYERS.md\].  
  2. De ConfigValidator draait.  
  3. De ConfigTranslator zet de gevalideerde YAMLs om in BuildSpecs \[cite: docs/development/CONFIG\_BUILDSPEC\_TRANSLATION\_DESIGN.md\].  
  4. De Factories (bv. WorkerFactory, EventWiringFactory) assembleren de strategie-instantie op basis van de BuildSpecs.  
* **Impact van Nieuwe Inzichten:** De ConfigValidator hoeft **geen** ContextAggregator meer te valideren. De DependencyValidator \[cite: docs/system/addendums/Addendum\_ 11\_6.7 dependency\_validator.md\] wordt *belangrijker*, omdat het de directe requires\_dtos dependencies tussen (bijv.) een OpportunityWorker en de ContextWorkers moet valideren.

### **Fase 1: Context Analyse (Objectieve Feitenfabriek)**

* **Componenten:** ContextWorkers (Plugins) \[cite: docs/architecture/WORKER\_TAXONOMY.md\].  
* **Trigger:** TICK\_FLOW\_START (System Event van TickCacheManager) \[cite: docs/development/EVENT\_LIFECYCLE\_ARCHITECTURE.md\].  
* **Orkestratie:** Draait (meestal) sequentieel, zoals gedefinieerd in de strategy\_wiring\_map.yaml \[cite: docs/architecture/EVENT\_DRIVEN\_WIRING.md\].  
* **Taak:** Converteer ruwe data naar objectieve, feitelijke DTOs.  
* **Output:** self.strategy\_cache.set\_result\_dto(self, DTO) \[cite: docs/architecture/DATA\_FLOW.md\].

**ICT/SMC Voorbeeld Keten:**

1. **Worker:** MTF\_Bias\_Detector (ContextWorker)  
   * **Capability:** IMtfProvider \[cite: docs/system/addendums/Addendum\_ 5.1 Data Landschap & Point-in-Time Architectuur.md\]  
   * **Logica:** Haalt Daily (1D) data, vindt de trend.  
   * **Output:** set\_result\_dto(self, HTF\_BiasDTO(bias="BULLISH"))  
2. **Worker:** H4\_Structure\_Detector (ContextWorker)  
   * **Capability:** IMtfProvider (4H)  
   * **Dependency:** HTF\_BiasDTO (uit vorige stap)  
   * **Logica:** if bias.is\_bullish: find\_h4\_swing\_leg()  
   * **Output:** set\_result\_dto(self, MarketStructureDTO(high=..., low=...))  
3. **Worker:** PD\_Array\_Calculator (ContextWorker)  
   * **Dependency:** MarketStructureDTO  
   * **Logica:** Trekt Fibo van low naar high.  
   * **Output:** set\_result\_dto(self, PD\_ArrayDTO(premium\_zone=..., discount\_zone=...))  
4. **Worker:** FVG\_Finder (ContextWorker)  
   * **Capability:** IOhlcvProvider (15M)  
   * **Dependency:** PD\_ArrayDTO  
   * **Logica:** find\_fvgs\_in\_zone(pd\_array.discount\_zone)  
   * **Output:** set\_result\_dto(self, FVG\_DataDTO(found\_fvgs=\[...\]))

Aan het einde van Fase 1 is de TickCache \[cite: docs/architecture/POINT\_IN\_TIME\_MODEL.md\] gevuld met een rijke, objectieve "kaart" van de markt.

### **Fase 2: Signaal Detectie (Subjectieve Tolken)**

* **Componenten:** OpportunityWorkers & ThreatWorkers (Plugins) \[cite: docs/architecture/WORKER\_TAXONOMY.md\].  
* **Trigger:** (Meestal) CONTEXT\_ASSESSMENT\_READY (verwijderde term) \-\> Moet nu CONTEXT\_CHAIN\_COMPLETE heten, of getriggerd worden door de *laatste* ContextWorker. Laten we aannemen dat ze TICK\_FLOW\_START als trigger gebruiken en *wachten* op hun dependencies.  
* **Orkestratie:** Draaien parallel.  
* **Taak:** Consumeren de feitelijke DTOs uit Fase 1 en passen hun *eigen subjectieve logica* toe.

**ICT/SMC Voorbeeld (OpportunityWorker):**

* **Plugin:** LTF\_Entry\_Model (OpportunityWorker)  
* **manifest.yaml requires\_dtos:**  
  dependencies:  
    requires\_dtos:  
      \- { dto\_class: "HTF\_BiasDTO" }  
      \- { dto\_class: "H4\_SetupDTO" } \# Hypothetisch, uit Fase 1  
      \- { dto\_class: "FVG\_DataDTO" }

* **Stateful Logic (Geheugen):** Zoals we bespraken, als deze worker moet *wachten* op een retest, vraagt hij de state\_persistence capability aan \[cite: docs/architecture/PLUGIN\_ANATOMY.md\].  
* **worker.py (pseudo-code):**  
  def process(self) \-\> DispositionEnvelope:  
      \# 1\. Haal feiten (Context) op uit TickCache  
      dtos \= self.strategy\_cache.get\_required\_dtos(self)  
      bias \= dtos\[HTF\_BiasDTO\]  
      fvgs \= dtos\[FVG\_DataDTO\]

      \# 2\. Haal geheugen (State) op  
      pending\_retest \= self.state\_provider.get("pending\_fvg\_retest")

      \# 3\. Voer SUBJECTIEVE interpretatie uit  
      \# (Logica van de vorige sessie)  
      if bias.is\_bullish and fvgs.in\_discount and ...:  
          \# ... (logica voor het vinden/wachten op de setup) ...

          \# 4\. Gevonden\! Publiceer signaal.  
          return DispositionEnvelope(  
              disposition="PUBLISH",  
              event\_name="OPPORTUNITY\_DETECTED",  
              event\_payload=OpportunitySignal(confidence=0.9, ...)  
          )

      \# 5\. Geen actie  
      return DispositionEnvelope(disposition="CONTINUE")

* **Output:** OpportunitySignal (Systeem DTO) naar de EventBus \[cite: docs/architecture/DATA\_FLOW.md\].

### **Fase 3: Strategische Planning (De "CEO")**

* **Component:** StrategyPlanner (Plugin, 1-per-strategie) \[cite: docs/architecture/WORKER\_TAXONOMY.md\].  
* **Trigger:** Luistert naar OPPORTUNITY\_DETECTED en THREAT\_DETECTED events.  
* **Taak:** De "Go/No-Go" beslissing. Dit is de *echte* confrontatie.  
* **Logica:**  
  1. Ontvangt OpportunitySignal(confidence=0.9) via de EventBus.  
  2. Leest *ook* de TickCache voor extra feiten (bv. HTF\_BiasDTO, NewsEventDTO).  
  3. Checkt ThreatSignal (bv. MAX\_DRAWDOWN\_REACHED).  
  4. **Beslissing:** if signal.confidence \> 0.8 and not threat.is\_active and bias.is\_bullish:  
* **Output:** StrategyDirective (Systeem DTO) met *hints* (bv. entry\_hint="AGGRESSIVE", exit\_hint="TARGET\_BSL") naar de EventBus \[cite: docs/development/\#Archief/STRATEGY\_PIPELINE\_ARCHITECTURE.md\].

### **Fase 4: Tactische Planning (De Specialisten)**

* **Componenten:** PlanningWorkers (Plugins) \[cite: docs/architecture/WORKER\_TAXONOMY.md\].  
* **Trigger:** Luisteren naar STRATEGY\_DIRECTIVE\_ISSUED.  
* **Taak:** "Confidence-Driven Specialization" \[cite: docs/development/\#Archief/STRATEGY\_PIPELINE\_ARCHITECTURE.md\].  
  * De EntryPlanner die getagged is voor "AGGRESSIVE" pakt de taak op.  
  * De ExitPlanner die getagged is voor "TARGET\_BSL" pakt de taak op.  
* **Output:** EntryPlanDTO, ExitPlanDTO, SizePlanDTO, ExecutionIntentDTO naar de TickCache.

### **Fase 5: Executie Orkestratie (Platform)**

* **Component:** PlanningAggregator (Platform Component) \[cite: docs/development/\#Archief/STRATEGY\_PIPELINE\_ARCHITECTURE.md\].  
* **Taak:** Detecteert dat alle 4 de plan-DTOs in de TickCache aanwezig zijn.  
* **Output:** Bundelt ze in één ExecutionDirective (Systeem DTO) en publiceert dit.

### **Fase 6: Uitvoering (Platform)**

* **Component:** ExecutionTranslator & ExecutionHandler (Platform Componenten) \[cite: docs/development/\#Archief/STRATEGY\_PIPELINE\_ARCHITECTURE.md\].  
* **Taak:** Vertaalt de ExecutionIntent (bv. visibility=0.1) naar een connector-specifieke order (bv. iceberg=True) \[cite: docs/development/\#Archief/EXECUTION\_INTENT\_DESIGN.md\] en stuurt deze naar de exchange.

## **5\. Actieplan: Documentatie Opschonen & Verfijnen**

Om deze "Quant Leap" te formaliseren, stel ik het volgende actieplan voor:

### **Stap 1: Archiveren & Verwijderen (Opschonen)**

1. **Archiveren:**  
   * docs/development/\#Archief/decision\_framework.md (Verplaats naar .../\#Archief/DEPRECATED\_SWOT/)  
2. **Code Verwijderen:**  
   * backend/dtos/strategy/context\_factor.py (en de test)  
   * backend/dtos/strategy/aggregated\_context\_assessment.py (en de test)  
   * backend/core/context\_factors.py (en de test)  
3. **Implementatieplan Verwijderen:**  
   * Verwijder ContextAggregator uit de roadmap in docs/TODO.md.

### **Stap 2: Aanpassen Bestaande Documenten (Verfijnen)**

1. **docs/development/\#Archief/STRATEGY\_PIPELINE\_ARCHITECTURE.md:**  
   * **Actie:** Verwijder Fase 1b (Context Aggregatie).  
   * **Actie:** Hernoem de fases om de nieuwe flow te weerspiegelen.  
   * **Actie:** Update de diagrammen om de ContextAggregator te verwijderen.  
   * **Actie:** Herschrijf Fase 3 (Strategy Planning) om te benadrukken dat de StrategyPlanner nu *direct* de rauwe context-DTOs uit de TickCache consumeert voor zijn Go/No-Go beslissing.  
2. **docs/architecture/WORKER\_TAXONOMY.md:**  
   * **Actie:** Herschrijf de introductie van de 27 sub-categorieën. Maak expliciet dat dit **beschrijvende labels (tags)** zijn voor filtering en documentatie, en geen dwingende contracten.  
   * **Actie:** Verwijder ContextAggregator en AggregatedContextAssessment uit alle beschrijvingen en diagrammen.  
3. **docs/architecture/PLUGIN\_ANATOMY.md:**  
   * **Actie:** Voeg een paragraaf toe bij het subtype veld in het manifest.yaml voorbeeld, die het verschil tussen het dwingende type (ROL) en het beschrijvende subtype (LABEL) uitlegt.  
4. **docs/architecture/DATA\_FLOW.md:**  
   * **Actie:** Update de diagrammen om de directe consumptie van TickCache-feiten door OpportunityWorkers en StrategyPlanners te tonen, zonder de ContextAggregator ertussen.  
5. **docs/implementation/IMPLEMENTATION\_STATUS.md:**  
   * **Actie:** Verwijder de regels voor context\_factor.py en aggregated\_context\_assessment.py uit de DTO-tabel. Pas het totale test-aantal aan.

### **Stap 3: Creëren Nieuwe "Bron van Waarheid" (Formaliseren)**

1. **Actie:** Promoveer *dit document* (of een opgeschoonde versie hiervan) van een "Sessie Overdracht" naar een permanent architectuurdocument, bijvoorbeeld: docs/architecture/OBJECTIVE\_DATA\_FLOW\_MODEL.md.  
   * Dit nieuwe document wordt de "single source of truth" die de gezuiverde, objectieve dataflow beschrijft en hoe deze de "Quant Leap" filosofie ondersteunt.

## **6\. Volgende Stappen & Roadmap**

**Dit verandert de roadmap in docs/TODO.md \[cite: docs/TODO.md\] NIET.**

Het maakt het juist *eenvoudiger*.

* **Week 0 (Foundation):** Is nog steeds compleet. We hebben alleen 2 DTOs minder (304 tests \-\> \~260 tests).  
* **Week 1 (Config Schemas):** Blijft de kritieke volgende stap. De schemas voor WorkerManifest, WiringConfig en StrategyBlueprint zijn *nog belangrijker* geworden, omdat de requires\_dtos dependency nu de kern van de strategie-logica vormt.  
* **Week 2 (Bootstrap):** Blijft hetzelfde, maar de ConfigValidator hoeft geen ContextAggregator meer te valideren.  
* **Week 3 (Factories):** Blijft hetzelfde.  
* **Week 4 (Platform Components):** De EventAdapter en TickCacheManager blijven nodig. De ContextAggregator en PlanningAggregator vervallen of worden eenvoudiger. (De PlanningAggregator is nog steeds nodig om de 4 *plan*\-DTOs te verzamelen \[cite: docs/development/\#Archief/STRATEGY\_PIPELINE\_ARCHITECTURE.md\]).

Deze architecturale verschuiving is een **verfijning en een vereenvoudiging**. Het verwijdert onnodige complexiteit en versterkt de "Plugin First" filosofie.

Ik ben klaar om verder te gaan met deze nieuwe, gezuiverde visie.