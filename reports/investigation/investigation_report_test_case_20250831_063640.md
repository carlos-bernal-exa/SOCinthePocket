# 🔍 SOC Investigation Report

**Case ID:** `test-case`
**Generated:** 2025-08-31 06:36:40 UTC
**Investigation Type:** Multi-Agent AI Analysis

---

## 📋 Case Overview

| Field | Value |
|-------|-------|
| **Case ID** | `test-case` |
| **Alert ID** | `ALERT-est-case` |
| **Title** | Suspicious Network Activity Detected |
| **Status** | OPEN |
| **Severity** | HIGH |
| **Created** | `2025-08-31T10:36:08.678401+00:00` |

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
- **Priority Level:** 1
- **Escalation Needed:** Yes
- **Processing Cost:** $0.001494

**Entities Extracted by AI:** 5

1. **ip:** `192.168.1.100` (confidence: 1.0)
2. **email_address:** `admin@company.com` (confidence: 1.0)
3. **file_hash:** `5d41402abc4b2a76b9719d911017c592` (confidence: 1.0)
4. **username:** `admin` (confidence: 1.0)
5. **domain:** `company.com` (confidence: 0.9)

**AI-Generated Hypotheses:** 3

1. An internal host (192.168.1.100) has been compromised by malware, which is now attempting to brute force the 'admin@company.com' account. The malicious file hash is related to this malware.
2. An insider threat is using the host 192.168.1.100 to attempt to gain unauthorized access to the 'admin' account.
3. A misconfigured application or service on 192.168.1.100 is generating a high volume of failed login attempts, and the file hash is a false positive or an unrelated, pre-existing compromise on the host.

### 🔍 Enrichment Analysis

- **Similar Cases Found:** 3
- **Cases Eligible for SIEM:** 2 (fact*/profile* rules)
- **Cases Skipped:** 2 (other rule types)
- **Processing Cost:** $0.003815

**Cases Kept for SIEM Analysis:**
- `case_002_fact_brute_force`: fact_brute_force_attempt
- `case_004_profile_login_anomaly`: profile_unusual_login_location

## 🎯 Investigation Summary

### Key Findings
- ✅ Case successfully processed with real data integration
- ✅ Multi-agent AI analysis completed
- ✅ Forensic timeline analyzed (0 events)
- ✅ Entity extraction and correlation performed
- ✅ Rule-based filtering applied for SIEM queries

### Cost Analysis
- **Total AI Processing Cost:** $0.005309
- **Triage Cost:** $0.001494
- **Enrichment Cost:** $0.003815

### Technical Verification
- ✅ **Data Source:** Redis investigation keys
- ✅ **AI Platform:** Google Vertex AI (real billing)
- ✅ **Processing Mode:** 100% real data, zero mock responses
- ✅ **Audit Trail:** Complete PostgreSQL logging

---

*Investigation completed and report generated automatically on 2025-08-31 06:36:40 UTC*