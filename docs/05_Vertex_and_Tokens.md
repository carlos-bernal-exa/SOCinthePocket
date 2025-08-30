# Vertex & Token Tracking

## Model Choices
- gemini-2.5-pro: reasoning, correlation, reporting.
- gemini-2.5-flash: triage, enrichment.
- gemini-2.5-flash-lite: micro extraction.

## Pricing (example)
- Pro: $3.50 / 1M tokens
- Flash: $0.35 / 1M
- Flash Lite: $0.05 / 1M

## Tracking
Every call stores:
- input_tokens, output_tokens, total_tokens, cost_usd
in AgentStep.token_usage.

## Wrapper
Python wrapper captures response.usage, computes USD, attaches to audit log.
