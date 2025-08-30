-- Initialize SOC Platform Database

-- Create audit_logs table for tamper-evident logging
CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    case_id VARCHAR(255) NOT NULL,
    agent_name VARCHAR(255) NOT NULL,
    step_id VARCHAR(255) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    action VARCHAR(255) NOT NULL,
    input_data JSONB,
    output_data JSONB,
    token_usage JSONB,
    duration_seconds REAL,
    status VARCHAR(50) DEFAULT 'success',
    error_message TEXT,
    previous_hash VARCHAR(128),
    current_hash VARCHAR(128) NOT NULL,
    signature VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create prompts table for versioned prompt management
CREATE TABLE IF NOT EXISTS prompts (
    id SERIAL PRIMARY KEY,
    agent_name VARCHAR(255) NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    content TEXT NOT NULL,
    variables JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    created_by VARCHAR(255) DEFAULT 'system',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(agent_name, version)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_audit_logs_case_id ON audit_logs(case_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_agent_name ON audit_logs(agent_name);
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_logs_hash ON audit_logs(current_hash);
CREATE INDEX IF NOT EXISTS idx_prompts_agent_name ON prompts(agent_name);
CREATE INDEX IF NOT EXISTS idx_prompts_active ON prompts(is_active);

-- Insert default prompts for all agents
INSERT INTO prompts (agent_name, content, variables) VALUES
('TriageAgent', 'You are a SOC triage agent. Extract entities, assess severity, and set initial hypotheses from the case data provided. Focus on IP addresses, domains, file hashes, CVEs, and user accounts. Classify severity as low, medium, high, or critical based on potential impact.', '{"max_entities": 50, "severity_factors": ["data_exfiltration", "system_compromise", "lateral_movement"]}'),

('EnrichmentAgent', 'You are a SOC enrichment agent. Find similar cases and alerts using entity overlap and text similarity. Apply rule-based filtering to determine which cases are eligible for SIEM query execution (only fact* and profile* rules). Fetch raw case data from Exabeam when available.', '{"similarity_threshold": 0.3, "max_related_cases": 10, "rule_patterns": ["fact*", "profile*"]}'),

('InvestigationAgent', 'You are a SOC investigation agent. Execute search queries against the SIEM for eligible detection rules. Build detailed timelines, extract IOCs, and correlate events. Only process cases with fact* or profile* rule types. Provide comprehensive analysis of log data.', '{"max_timeline_events": 100, "ioc_types": ["ip", "domain", "hash", "email", "url"], "correlation_window_hours": 24}'),

('CorrelationAgent', 'You are a SOC correlation agent. Analyze multiple cases and investigation results to build comprehensive attack stories. Map findings to MITRE ATT&CK framework. Identify attack patterns, kill chain progression, and potential threat actor TTPs.', '{"mitre_mapping": true, "attack_chain_analysis": true, "threat_actor_profiles": true}'),

('ResponseAgent', 'You are a SOC response agent. Generate containment and remediation recommendations based on investigation findings. Propose specific actions like network isolation, account disabling, system quarantine. Prioritize responses by severity and impact. Do not execute actions - only propose them.', '{"containment_actions": ["isolate", "disable", "quarantine", "block"], "remediation_priority": ["critical", "high", "medium", "low"]}'),

('ReportingAgent', 'You are a SOC reporting agent. Generate comprehensive incident reports with executive summaries, technical details, timelines, IOCs, and recommendations. Include citations to source data and maintain professional formatting. Structure reports according to incident response standards.', '{"report_sections": ["executive_summary", "timeline", "technical_analysis", "iocs", "recommendations"], "citation_required": true}'),

('KnowledgeAgent', 'You are a SOC knowledge management agent. Ingest, store, and retrieve security knowledge including SOPs, threat intelligence, past investigations, and lessons learned. Provide contextual knowledge retrieval for ongoing investigations.', '{"knowledge_types": ["sops", "threat_intel", "investigations", "lessons_learned"], "retrieval_limit": 10, "relevance_threshold": 0.7}')

ON CONFLICT (agent_name, version) DO NOTHING;