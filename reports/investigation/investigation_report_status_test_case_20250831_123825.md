# 🔍 SOC Investigation Report

**Case ID:** `status-test-case`
**Generated:** 2025-08-31 12:38:25 UTC
**Investigation Type:** Multi-Agent AI Analysis

---

## 📋 Case Overview

| Field | Value |
|-------|-------|
| **Case ID** | `status-test-case` |
| **Alert ID** | `ALERT-est-case` |
| **Title** | Suspicious Network Activity Detected |
| **Status** | OPEN |
| **Severity** | HIGH |
| **Created** | `2025-08-31T16:38:03.261453+00:00` |

### Description

> Multiple failed login attempts detected from IP 192.168.1.100 targeting user admin@company.com. Potential brute force attack in progress. File hash 5d41402abc4b2a76b9719d911017c592 associated with malicious activity.

## 🎯 Entities Identified

**Total Entities:** 4

### Ip Addresses
- `192.168.1.100`

### Email Addresses
- `admin@company.com`

### File Hashes
- `5d41402abc4b2a76b9719d911017c592`

### Usernames
- `admin`

## 🤖 AI Analysis Results

### 🏷️ Triage Analysis

- **Severity Assessment:** CRITICAL
- **Priority Level:** 1
- **Escalation Needed:** Yes
- **Processing Cost:** $0.001596

**Entities Extracted by AI:** 4

1. **ip:** `192.168.1.100` (confidence: 0.95)
2. **email:** `admin@company.com` (confidence: 0.95)
3. **file_hash:** `5d41402abc4b2a76b9719d911017c592` (confidence: 0.95)
4. **username:** `admin` (confidence: 0.95)

**AI-Generated Hypotheses:** 4

1. **Internal Host Compromise**: An internal workstation or server (192.168.1.100) has been compromised and is being used to brute force the admin account. The malicious file hash is likely related to the initial compromise or a tool deployed by the attacker.
2. **Insider Threat**: A malicious insider is attempting to gain elevated privileges to the 'admin@company.com' account from within the network, potentially using tools associated with the malicious file hash.
3. **Lateral Movement Attempt**: An attacker has already gained initial access to the network via another host and is now attempting to escalate privileges by targeting the admin account from 192.168.1.100.
4. **Misconfigured Service/Application (Less Likely)**: A legitimate internal service or application on 192.168.1.100 is misconfigured and repeatedly attempting to authenticate with incorrect credentials. However, the explicit association with a 'malicious file hash' makes this hypothesis less probable without further evidence.

### 🔍 Enrichment Analysis

- **Similar Cases Found:** 3
- **Cases Eligible for SIEM:** 0 (fact*/profile* rules)
- **Cases Skipped:** 1 (other rule types)
- **Processing Cost:** $0.002028

## 🎯 Investigation Summary

### Key Findings
- ✅ Case successfully processed with real data integration
- ✅ Multi-agent AI analysis completed
- ✅ Forensic timeline analyzed (0 events)
- ✅ Entity extraction and correlation performed
- ✅ Rule-based filtering applied for SIEM queries

### Cost Analysis
- **Total AI Processing Cost:** $0.003624
- **Triage Cost:** $0.001596
- **Enrichment Cost:** $0.002028

### Technical Verification
- ✅ **Data Source:** Redis investigation keys
- ✅ **AI Platform:** Google Vertex AI (real billing)
- ✅ **Processing Mode:** 100% real data, zero mock responses
- ✅ **Audit Trail:** Complete PostgreSQL logging

---

*Investigation completed and report generated automatically on 2025-08-31 12:38:25 UTC*