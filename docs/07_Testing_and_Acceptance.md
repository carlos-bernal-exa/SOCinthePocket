# Testing & Acceptance

## Unit Tests
- Rule gating logic (fact*/profile* vs CR/rule_sequence)
- Entity extraction from case summaries
- Similarity scoring

## Integration Tests
- With sample data, ensure correct kept/skipped rules
- Ensure SIEM queries executed for eligible rules

## Load Tests
- Parallel enrichment runs, cache performance

## Acceptance Criteria
- Extract correct IOCs from sample raw case
- Produce audit log with token usage & prompt version
- Populate Neo4j with Case→Rule, Case→Entity edges
