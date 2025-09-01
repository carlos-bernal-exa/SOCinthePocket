# 🔍 SOC Investigation Report

**Case ID:** `real-data-test-1756660104`
**Generated:** 2025-08-31 13:11:23 UTC
**Investigation Type:** Multi-Agent AI Analysis

---

## 📋 Case Overview

| Field | Value |
|-------|-------|
| **Case ID** | `real-data-test-1756660104` |
| **Alert ID** | `ALERT-56660104` |
| **Title** | Suspicious Network Activity Detected |
| **Status** | OPEN |
| **Severity** | HIGH |
| **Created** | `2025-08-31T17:10:37.204616+00:00` |

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

- **Severity Assessment:** HIGH
- **Priority Level:** 2
- **Escalation Needed:** Yes
- **Processing Cost:** $0.001469

**Entities Extracted by AI:** 4

1. **ip_address:** `192.168.1.100` (confidence: 0.95)
2. **email_address:** `admin@company.com` (confidence: 0.95)
3. **file_hash:** `5d41402abc4b2a76b9719d911017c592` (confidence: 0.9)
4. **username:** `admin` (confidence: 0.95)

**AI-Generated Hypotheses:** 4

1. An external attacker is attempting to gain unauthorized access to the 'admin' account via brute force, potentially using a compromised system or botnet node (if 192.168.1.100 is external).
2. An internal host (192.168.1.100) is compromised with malware (potentially related to the identified file hash) and is attempting to escalate privileges by brute-forcing the 'admin' account.
3. A credential stuffing attack is underway, where previously leaked credentials are being tested against the 'admin' account.
4. The malicious file hash is part of a toolkit being used by an attacker to facilitate the brute force, or it's a separate, but related, malware infection on the source system.

### 🔍 Enrichment Analysis

- **Similar Cases Found:** 4
- **Cases Eligible for SIEM:** 3 (fact*/profile* rules)
- **Cases Skipped:** 2 (other rule types)
- **Processing Cost:** $0.004819

**Cases Kept for SIEM Analysis:**
- `past_case_12345`: fact_failed_logins_threshold
- `past_case_67890`: profile_user_login_deviation
- `past_case_44556`: fact_brute_force_attempt

## 🎯 Investigation Summary

### Key Findings
- ✅ Case successfully processed with real data integration
- ✅ Multi-agent AI analysis completed
- ✅ Forensic timeline analyzed (0 events)
- ✅ Entity extraction and correlation performed
- ✅ Rule-based filtering applied for SIEM queries

### Cost Analysis
- **Total AI Processing Cost:** $0.006288
- **Triage Cost:** $0.001469
- **Enrichment Cost:** $0.004819

### Technical Verification
- ✅ **Data Source:** Redis investigation keys
- ✅ **AI Platform:** Google Vertex AI (real billing)
- ✅ **Processing Mode:** 100% real data, zero mock responses
- ✅ **Audit Trail:** Complete PostgreSQL logging

---

*Investigation completed and report generated automatically on 2025-08-31 13:11:23 UTC*