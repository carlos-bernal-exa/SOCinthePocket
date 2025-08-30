# Product Requirements Document (PRD)

## 1. Summary
Build an agentic SOC platform that—given a `case_id` or `alert_id`—reads a case summary from Redis, extracts entities, finds similar alerts/cases in Redis, fetches raw cases from Exabeam, and (only when the detection rule is fact* or profile*), executes the case’s `search_query` against the SIEM to retrieve raw logs. The system updates graph memory (Neo4j) and knowledge (Qdrant), and emits an append-only, tamper-evident JSON audit for every agent step.  
Models run exclusively via Vertex AI: Gemini 2.5 (Pro / Flash / Flash Lite).

## 2. Goals
- End-to-end, auditable investigation aligned to NIST/SANS IR phases.
- Accurate rule gating: run SIEM only for fact* / profile* rules.
- High recall entity matching and similarity across Redis summaries.
- Graph memory for cross-case correlation and future enrichment.
- Editable, versioned prompts per agent.
- Token/cost tracking per step, per case, per agent.
- Modes: Fully autonomous and User-in-the-loop.

## 3. Non-Goals
- No destructive response actions in v1 (containment proposals only).
- No UI beyond minimal REST responses (report/JSON suitable for any UI).
- No non-Vertex models.

## 4. Users & Use Cases
- Tier-1 Analyst: request enrichment & context.
- Tier-2 IR: deep analysis, ATT&CK mapping.
- Manager: audit, cost/latency/quality metrics.
- Admin: manage prompts, policies, memory.

... (trimmed for brevity; include full PRD content as drafted above)
