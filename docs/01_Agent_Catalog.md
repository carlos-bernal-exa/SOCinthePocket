# Agent Catalog

## ControllerAgent
- Purpose: orchestrates modes (ReAct, Planner, Deep), Gemini model choice, autonomy enforcement.
- Inputs: task spec, autonomy, SLA.
- Outputs: execution plan, mode.

## TriageAgent
- IR Phase: Detection & Analysis
- Purpose: normalize input, extract entities, set initial severity & hypotheses.
- Model: Gemini 2.5 Flash
- Outputs: entities, severity, hypotheses

## EnrichmentAgent
- IR Phase: Detection & Analysis
- Purpose: find similar cases/alerts in Redis, fetch Exabeam raw cases, apply rule filter.
- Model: Flash
- Outputs: related_items, raw_cases, kept_cases, skipped_cases

## InvestigationAgent
- IR Phase: Detection & Analysis
- Purpose: Execute search_query in SIEM, build timeline, extract IOC set.
- Model: Gemini 2.5 Pro

## CorrelationAgent
- Purpose: correlate across cases, build attack story, MITRE mapping.
- Model: Pro

## ResponseAgent
- Purpose: propose (and later execute) containment actions.
- Model: Pro

## ReportingAgent
- Purpose: produce incident report with citations.
- Model: Pro

## KnowledgeAgent
- Purpose: ingest notes/SOPs, retrieve past investigations.
- Model: Pro / Flash Lite
