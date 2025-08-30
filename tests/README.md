# Test Suite for Agentic SOC Platform

This directory contains test scripts and utilities for the SOC platform development and validation.

## 🧪 Test Categories

### Core API Tests
- `test_api.py` - Basic API endpoint testing
- `test_complete_investigation.py` - End-to-end investigation workflow
- `test_fixed_triage.py` - Triage agent validation after Redis fix

### Real Data Integration Tests
- `test_real_case.py` - Real case data processing
- `test_real_case_final.py` - Final validation with real data
- `test_with_real_services.py` - Integration with Redis, Vertex AI, etc.
- `run_real_case.py` - Execute investigation with real case data

### Agent-Specific Tests
- `agents_audit_report.py` - Detailed agent execution audit
- `test_investigation_detailed.py` - Investigation agent deep testing
- `test_investigation_with_eligible_case.py` - SIEM rule filtering tests

### Infrastructure Tests
- `test_neo4j_integration.py` - Neo4j graph database connectivity
- `test_audit_integrity.py` - Cryptographic audit trail verification
- `check_audit_db.py` - PostgreSQL audit database validation

### Analysis & Reporting Tests
- `analyze_investigation_output.py` - Investigation output analysis
- `detailed_agent_outputs.py` - Agent output detailed inspection
- `final_reports.py` - Report generation validation
- `get_reports.py` - Report retrieval and formatting
- `show_actual_outputs.py` - Display real agent outputs

### Setup & Utilities
- `setup_real_env.py` - Environment setup for real data testing
- `test_token_costs.py` - AI model token usage and cost tracking

## 🚀 Running Tests

### Prerequisites
- Redis with case data
- PostgreSQL audit database
- Google Cloud service account key
- Neo4j database (optional)

### Quick Test with Real Data
```bash
# Run complete investigation with real case
python tests/run_real_case.py

# Test specific case ID
python tests/test_real_case_final.py
```

### API Testing
```bash
# Basic API functionality
python tests/test_api.py

# Complete workflow test
python tests/test_complete_investigation.py
```

### Analysis Tools
```bash
# Get detailed agent outputs
python tests/show_actual_outputs.py

# Generate comprehensive reports
python tests/final_reports.py

# Audit trail verification
python tests/test_audit_integrity.py
```

## 📊 Test Case: 6c7a11e3-5fbd-4cf9-8eee-e826aa40f9dc

This is the primary test case used for validation:
- **Type**: USB device detection incidents
- **Events**: 6 forensic timeline events
- **Entities**: Multiple device IDs and user accounts
- **Data Source**: Real Exabeam investigation data in Redis

## 🔍 Key Testing Insights

### Before Redis Fix
- Agents returned generic responses
- No real case data access
- Mock data fallbacks used

### After Redis Fix
- Real case data successfully retrieved
- 9 entities extracted by AI
- 4 threat hypotheses generated
- Complete forensic timeline analysis

## 🎯 Test Results Validation

Look for these indicators of successful real data integration:
- ✅ Non-zero token costs (`$0.001263` typical)
- ✅ Real entity extraction (device IDs, usernames)
- ✅ Actual timestamps from forensic events
- ✅ SIEM rule filtering working correctly
- ✅ Complete audit trail with hash verification

## 🛠️ Development Notes

These tests were created during the platform development to ensure:
1. Real data integration works correctly
2. All agents process actual security data
3. Report generation creates meaningful output
4. Audit trails maintain cryptographic integrity
5. Cost tracking accurately reflects AI usage