Ik zou graag een aanvullend document met je maken met de name trade_lifecycle.md.



De geschiedenis van de documentatie is pipeline_flow, daarna kwam execution_flow. Execution flow is specifieker over de synchrone en asynchrone flows, maar laat (helaas nog) een aantal details weg die in de pipeline flow wel uitgewerkt zijn, zoals de ExecutionTranslator (die specifieke tussen component was voor het duidelijk maken van de twee soorten flows niet cruciaal dus ik heb hier niet meer aandacht aan besteed).



Voor trade_lifecycle.md, wil ik 2 scenario's met je doornemen en bespreken voordat we het document daadwerkelijk gaan uitwerken/maken:



Hoewel in grote lijnen en eigenlijk ook zeer gedetailleerd ontworpen, bestaat er binnen de V3 Execution_Flow architectuur nog veel ruimte voor vrije interpretatie, met name voor wat betreft de definitie van orders/fills/posities/trades.



Ik wil dit gaan oplossen door een lifecycle object te introduceren als container voor een complete set die begint met order(s), fill(s), postition(s), result(s). Dit object wil ik TradePlan gaan noemen. Het wordt geboren binnen een StrategyPlanner en sterft ofwel binnen de StrategyLedger (als de laatste close order volledig gefilld is/er geen open posities meer zijn), ofwel binnen de StrategyJournalWriter (als de volledige causaliteit van een tradeplan dat volledig is uitgevoerd, vast gelegd is).



Ik worstel nog een beetje met de relatie TradePlan <-> StrategyDirective.



Ik zie twee scenario's:

I. Nieuw signaal!

De StrategyPlanner, maakt een leeg TradePlan (DTO) aan en vult deze met 1 of meer sets van 4 sub directives, waarbij iedere set sub-directives de opdracht of instructie is voor een nieuwe order.

Dit Tradeplan wordt in een StrategyDirective container (DTO) gestopt en verstuurd naar de Trade planners én PlanningAggregator, die hun gefocuste/specialistische (entry-, size-, exit- en routing-) werk doen en voor iedere sub-directive een nieuw eigen plan aanmaken (bijvoorbeeld EntryPlan, SizePlan, etc.).

De PlanningAggregator ontvangt dus ook de StrategyDirective en begint met het verzamelen van alle plannen, hij weet hoeveel plannen hij per trade plan krijgen gaat aan de hand van het aantal sets sub directives. De vier sub plannen verzamelt zouden we een OrderPlan kunnen noemen. Zodra alle OrderPlans verzamelt zijn, stopt hij ze in het TradePlan dto en stuurt hij ze door naar de ExecutionTranslator als ExecutionDirective (of ExecutionDirectiveBatch met aantal 1-N) die de connector agnostische OrderPlans binnen het TradePlan gaat vertalen naar een connector specifieke executie methode (ConnectorExecutionSpec DTO).

De ExecutionHandler (onderdeel van de ExecutionEnvironment) verzend met behulp van de juiste methode/connector de orders en registreert het TradePlan (met bijbehorende geplaatste én geplande orders) met behulp van methods van de StrategyLedger in het grootboek.

De flow eindigt via de StrategyJournalWriter, die de CausalityChain gebruikt om de ContextJournalDTO's van alle sub workers uit het StrategyCache te halen en te loggen in het StrategyJournal, en uiteindelijk de FlowTerminator die het StrategyCache leegt/opruimt en de flow beeindigd.



II. Een strategisch event, bijvoorbeeld een Threat (market crash) of rebalancer- of DCA Scheduled event

Nu vraagt de specifieke StrategyPlanner via de StrategyLedger