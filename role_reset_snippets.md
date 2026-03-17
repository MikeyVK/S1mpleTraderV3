# Role Reset Snippets

Gebruik deze korte reset-prompts direct na context compaction.

## QA Reset

```text
Gebruik @qa als actieve rol voor deze sessie.
Gebruik `.github/agents/qa.agent.md` als rolhandleiding.
Ga ervan uit dat je context leeg of onbetrouwbaar is en voer eerst de startup-procedure uit die in dat bestand staat.
Doe daarna strikte read-only QA op de hand-over die ik hierna stuur.
```

## Implementation Reset

```text
Gebruik @imp als actieve rol voor deze sessie.
Gebruik `.github/agents/imp.agent.md` als rolhandleiding.
Ga ervan uit dat je context leeg of onbetrouwbaar is en voer eerst de startup-procedure uit die in dat bestand staat.
Implementeer daarna alleen de taak of cycle die ik hierna stuur, binnen planning en deliverables.
```

## Gebruiksmoment

Geef exact een van deze snippets mee in je eerste bericht na compaction, direct voor de nieuwe hand-over of taak.
