# **Scaffolding Strategy: Pydantic-First Architecture**

**Status:** APPROVED

**Version:** 1.0.0

**Context:** S1mpleTrader V3 Template System

**Decision Type:** Architectural Standard

## **1\. Context & Probleemstelling**

### **De Oude Situatie: Template Introspectie**

Tot nu toe probeerden we de input-requirements voor scaffolding te "raden" door de Jinja2-templates te analyseren (introspectie). We keken naar variabelen die *niet* de filter | default hadden om te bepalen wat "Required" was.

### **De Problemen**

1. **Schema by Side-Effect:** De template fungeerde tegelijkertijd als presentatielaag (View) én als datadefinitie (Schema).  
2. **Verborgen Logica:** Complexe logica in templates (zoals {% if dependencies and imports.stdlib %}) maakte automatische validatie onmogelijk zonder een volledige AST-parser.  
3. **Fragiliteit:** Een kleine wijziging in de template (bijv. een if-statement toevoegen) veranderde impliciet het contract voor de input, vaak zonder dat de developer dit doorhad.  
4. **SRP Schending:** Dit schond het *Single Responsibility Principle*. De template moest defensief programmeren tegen slechte input, wat leidde tot "rommelige" code vol default() checks.

## **2\. De Beslissing: Pydantic-First Scaffolding**

We stappen over op een **Contract-Driven** aanpak voor scaffolding. Dit sluit aan bij onze bestaande [Coding Standards](https://www.google.com/search?q=../coding_standards/CODE_STYLE.md) die "Primitive Obsession" afwijzen en Pydantic DTO's voorschrijven.

### **De Kernprincipes**

1. **Strict Separation of Concerns:**  
   * **Pydantic Model:** Definieert de data, types, defaults en architecturale regels (Single Source of Truth voor *Data*).  
   * **Jinja Template:** Definieert puur de structuur en syntaxis van de output (Single Source of Truth voor *Presentatie*).  
2. **Validatie vooraf:** Input wordt gevalideerd *voordat* de template engine start. Als de data het model passeert, is de template-rendering gegarandeerd succesvol.  
3. **Architectural Enforcement:** We gebruiken Pydantic validators om architectuurregels af te dwingen (bv. "Een Platform worker mag geen Strategy Cache hebben").

### **Nieuwe Architectuur Diagram**

flowchart LR  
    User\[User / Agent Input\] \--\> Context\[Pydantic Context Model\]  
      
    subgraph Validation Layer  
        Context \-- "Validate Types" \--\> Check1{Basic Checks}  
        Check1 \-- "Validate Logic" \--\> Check2{Arch Rules}  
        Check2 \-- "Defaults" \--\> CleanData\[Clean Context Data\]  
    end  
      
    CleanData \--\> Jinja\[Jinja2 Template Engine\]  
      
    subgraph Template Tiers  
        Jinja \--\> T1\[Tier 1: Base Structure\]  
        T1 \--\> T2\[Tier 2: Language Rules\]  
        T2 \--\> T3\[Tier 3: Patterns\]  
        T3 \--\> Concrete\[Concrete Artifact\]  
    end  
      
    Concrete \--\> Output\[Final File\]  
      
    style Validation Layer fill:\#e1f5fe,stroke:\#01579b  
    style Template Tiers fill:\#fff3e0,stroke:\#e65100

## **3\. Implementatie Strategie**

### **3.1. Het Schema (scaffold\_schemas.py)**

Voor elk artifact type (Worker, DTO, Tool) definiëren we een strikt Pydantic model. Dit vervangt de impliciete variabelen in de template.

class WorkerContext(BaseModel):  
    \# Required (Geen defaults in template meer nodig)  
    name: str \= Field(..., description="PascalCase class name")  
    layer: str \= Field(..., description="Target architectural layer")  
      
    \# Enums & Logica (Niet meer string-matching in Jinja)  
    scope: Literal\['platform', 'strategy'\] \= 'strategy'  
      
    \# Architecturale Regels (Python logic is superieur aan Jinja logic)  
    @model\_validator(mode='after')  
    def validate\_rules(self):  
        if self.scope \== 'platform' and 'cache' in self.capabilities:  
            raise ValueError("Platform workers cannot utilize strategy cache")  
        return self

### **3.2. De Template Refactoring (templates/)**

Templates worden "dom" gemaakt. Ze gaan ervan uit dat de data die ze ontvangen *altijd* correct en compleet is.

**Voorbeeld wijziging:**

* **OUD (Defensief):**  
  @dependencies: \[{{ dependencies | default(\[\]) | join(', ') }}\]

* **NIEUW (Clean):**  
  @dependencies: \[{{ dependencies | join(', ') }}\]

  *Waarom? Pydantic garandeert dat dependencies een lijst is, zelfs als die leeg is.*

## **4\. Impact op Bestaande Tiers**

Deze wijziging heeft impact op hoe we onze Tiers gebruiken:

| Tier | Huidige Rol | Nieuwe Rol (Pydantic-First) |
| :---- | :---- | :---- |
| **Tier 0 (Artifact)** | Metadata Header | Ongewijzigd. Blijft SCAFFOLD header genereren. |
| **Tier 1 (Base)** | Structuur \+ *Complex Logic* | **Structuur Only.** Logica (zoals if imports.stdlib) verhuist naar Pydantic pre-validator die de imports sorteert/prepareert. |
| **Tier 2 (Lang)** | Language Syntax | Ongewijzigd. |
| **Tier 3 (Patterns)** | Macros | Ongewijzigd. Macros worden aangeroepen met schone data. |
| **Concrete** | Implementation | **Clean.** Geen \` |

## **5\. Voordelen**

1. **Waterdichte Validatie:** Het is onmogelijk om een invalide artifact te genereren (bv. een Worker zonder naam, of een Platform worker met verkeerde dependencies). De foutmelding komt *voordat* er code gegenereerd wordt.  
2. **Testbaarheid:** We kunnen scaffold\_schemas.py unit-testen met pytest, onafhankelijk van de templates.  
3. **Leesbare Templates:** Templates worden ontdaan van ruis. Ze tonen alleen hoe de code eruit moet zien, niet hoe de input gevalideerd moet worden.  
4. **SSOT Correct Toegepast:** \* Regels staan in Python (Schema).  
   * Opmaak staat in Jinja (Template).

## **6\. Migratieplan**

1. **Stap 1:** Creëer mcp\_server/scaffolding/schemas.py.  
2. **Stap 2:** Implementeer WorkerContext als pilot.  
3. **Stap 3:** Refactor concrete/worker.py.jinja2 (verwijder defaults).  
4. **Stap 4:** Update de MCP tool scaffold\_artifact om input eerst door het Pydantic model te halen alvorens .render() aan te roepen.  
5. **Stap 5:** Rol uit naar overige artifacts (DTO, Tool, Generic).