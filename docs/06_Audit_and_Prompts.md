# Audit & Prompts

## Audit
- Append-only JSONB (Postgres)
- Hash chain: hash = H(prev_hash || canonical_json)
- Signature: Ed25519 (optional)

## Prompt Manager
- Store prompts in Postgres with versioning.
- API: GET /prompts/{agent}, POST /prompts/{agent}, GET /prompts/{agent}/latest
- Agents log prompt_version in each AgentStep.
