# Agentic SOC Platform

AI-powered Security Operations Center with autonomous agents for comprehensive security incident analysis and response.

## 🎯 Overview

This platform implements a multi-agent AI system for security operations, featuring 8 specialized AI agents that work together to analyze security incidents, correlate threats, and generate actionable response plans. The system integrates with real security tools and generates comprehensive reports automatically.

## 🤖 AI Agents

- **ControllerAgent** - Orchestrates the investigation workflow
- **TriageAgent** - Initial threat assessment and entity extraction
- **EnrichmentAgent** - Finds similar cases and filters for SIEM analysis
- **InvestigationAgent** - Deep forensic analysis and timeline reconstruction
- **CorrelationAgent** - Attack pattern correlation and MITRE mapping
- **ResponseAgent** - Containment and remediation planning
- **ReportingAgent** - Executive summary and technical report generation
- **KnowledgeAgent** - Threat intelligence and knowledge base queries

## 📊 Automatic Report Generation

The platform automatically generates comprehensive reports for every investigation:

### Report Types
- **Audit Reports** - Complete audit trail with cryptographic verification
- **Investigation Reports** - Detailed case analysis and findings

### Report Formats
- **Markdown (.md)** - Human-readable format with rich formatting
- **JSON (.json)** - Machine-readable structured data

### Report Structure
```
reports/
├── audit/
│   ├── audit_report_{case_id}.md
│   └── audit_report_{case_id}.json
└── investigation/
    ├── investigation_report_{case_id}.md
    └── investigation_report_{case_id}.json
```

## 🔧 Technology Stack

- **AI Platform**: Google Vertex AI (Gemini 2.5-pro, 2.5-flash)
- **Database**: PostgreSQL (audit trail), Redis (case data), Neo4j (relationships), Qdrant (vector search)
- **SIEM Integration**: Exabeam
- **Cryptography**: SHA-256 hash chains with Ed25519 signatures
- **API**: FastAPI with async support
- **Authentication**: Service Account Key authentication

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- Google Cloud Service Account Key
- Redis instance with case data
- PostgreSQL database

### Environment Setup
1. Place your Google Cloud service account key in the root directory
2. Configure Redis connection for case data access
3. Set up PostgreSQL for audit trail storage

### Running the Platform
```bash
# Start with Docker Compose
docker-compose up -d

# Or run directly
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 📡 API Endpoints

### Core Investigation
- `POST /cases/{case_id}/enrich` - Start AI-powered case investigation
- `GET /audit/{case_id}` - Get audit trail for a case
- `GET /audit/verify/{case_id}` - Verify audit trail integrity

### Knowledge Management
- `POST /knowledge/ingest` - Add knowledge to the platform
- `GET /knowledge/search` - Search knowledge base

### Agent Management
- `GET /prompts/{agent_name}` - Get agent prompt
- `POST /prompts/{agent_name}` - Update agent prompt
- `GET /prompts/{agent_name}/latest` - Get latest prompt version

### Platform Status
- `GET /health` - Health check
- `GET /stats` - Platform statistics

## 🔍 How to Interpret Reports

### Audit Report Fields
- **Step ID**: Unique identifier for each agent execution
- **Hash Chain**: Cryptographic verification of audit integrity
- **Token Usage**: AI model token consumption and costs
- **Agent Outputs**: Detailed results from each agent

### Investigation Report Fields
- **Forensic Timeline**: Chronological sequence of security events
- **Entity Extraction**: IP addresses, devices, users identified by AI
- **MITRE Mapping**: Attack tactics and techniques classification
- **Threat Score**: AI-calculated risk assessment (0-100)
- **IOC Set**: Indicators of Compromise extracted from analysis

## 💡 Key Features

### Real Data Integration
- ✅ Zero mock data - all analysis uses real security data
- ✅ Redis case data integration with investigation keys
- ✅ Exabeam forensic data processing
- ✅ Real-time AI processing with cost tracking

### Audit Trail & Compliance
- ✅ Complete cryptographic audit trail
- ✅ Tamper-evident hash chain verification
- ✅ SOX, GDPR, SOC 2 compliance ready
- ✅ Immutable PostgreSQL logging

### SIEM Integration
- ✅ Rule-based filtering (fact*/profile* patterns)
- ✅ Automated SIEM query generation
- ✅ Case correlation and deduplication
- ✅ Timeline reconstruction from logs

## 🔐 Security & Compliance

- **Data Protection**: All sensitive data is encrypted and access-controlled
- **Audit Integrity**: SHA-256 hash chains with Ed25519 signatures
- **Access Control**: Service account authentication with principle of least privilege
- **Compliance**: Built for SOX, GDPR, and SOC 2 requirements

## 📈 Performance Metrics

- **Processing Speed**: Sub-minute analysis for complex cases
- **Cost Efficiency**: Optimized AI model selection (Flash for routine, Pro for complex analysis)
- **Accuracy**: Real-time entity extraction and correlation
- **Scalability**: Async processing with horizontal scaling support

## 🛠️ Development & Testing

### Test with Real Cases
```bash
# Run investigation with real case data
curl -X POST "http://localhost:8000/cases/6c7a11e3-5fbd-4cf9-8eee-e826aa40f9dc/enrich" \
  -H "Content-Type: application/json" \
  -d '{"autonomy_level": "supervised", "max_depth": 2}'
```

### View Generated Reports
```bash
# Check reports folder after investigation
ls -la reports/audit/
ls -la reports/investigation/
```

## 🎯 Use Cases

- **Incident Response**: Automated triage and investigation of security alerts
- **Threat Hunting**: Proactive threat detection and analysis
- **Forensic Analysis**: Timeline reconstruction and evidence correlation
- **Compliance Reporting**: Automated audit trail generation
- **Knowledge Management**: Centralized threat intelligence and case studies

## 📞 Support

For technical issues or questions about report interpretation, refer to the automatically generated documentation in the reports folder.

---

**Note**: This platform processes real security data and generates actual AI-powered analysis. All costs and token usage are tracked and reported in the audit trails.