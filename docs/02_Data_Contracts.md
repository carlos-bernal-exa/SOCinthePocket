# Data Contracts

## AgentStep
```json
{
  "version": "1.0",
  "case_id": "CASE-12345",
  "step_id": "stp_01JAB...",
  "timestamp": "2025-08-30T15:22:11Z",
  "agent": {"name": "InvestigationAgent", "role": "analysis", "model": "gemini-2.5-pro"},
  "prompt_version": "InvestigationAgent_v1.2",
  "autonomy_level": "L1_SUGGEST",
  "inputs": {...},
  "plan": [...],
  "observations": [...],
  "outputs": {...},
  "token_usage": {"input_tokens": 280, "output_tokens": 422, "total_tokens": 702, "cost_usd": 0.0025},
  "prev_hash": "hash_prev",
  "hash": "hash_current",
  "signature": "ed25519:..."
}
```

## TimelineEvent
- ts, actor?, event, src, details{}

## IOCSet
- ips[], users[], hosts[], domains[], hashes[]

## KnowledgeItem
- id, kind, author, created_at, case_id?, text, tags[], links[], trust, embeddings_ref?

## AgentPrompt
- id, agent_name, version, created_at, content, modified_by
