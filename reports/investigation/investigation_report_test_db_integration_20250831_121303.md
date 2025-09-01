# 🔍 SOC Investigation Report

**Case ID:** `test-db-integration`
**Generated:** 2025-08-31 12:13:03 UTC
**Investigation Type:** Multi-Agent AI Analysis

---

## 📋 Case Overview

| Field | Value |
|-------|-------|
| **Case ID** | `test-db-integration` |
| **Alert ID** | `ALERT-egration` |
| **Title** | Suspicious Network Activity Detected |
| **Status** | OPEN |
| **Severity** | HIGH |
| **Created** | `2025-08-31T16:12:29.634929+00:00` |

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
- **Processing Cost:** $0.001471

**Entities Extracted by AI:** 4

1. **ip:** `192.168.1.100` (confidence: 1.0)
2. **email:** `admin@company.com` (confidence: 1.0)
3. **username:** `admin` (confidence: 1.0)
4. **file_hash:** `5d41402abc4b2a76b9719d911017c592` (confidence: 1.0)

**AI-Generated Hypotheses:** 5

1. **Brute Force Attack:** An external or internal attacker is actively attempting to gain unauthorized access to the high-privilege admin account.
2. **Compromised Internal Host:** The IP 192.168.1.100 belongs to an internal system that has been compromised and is being used for lateral movement or privilege escalation attempts.
3. **Malware Activity:** A malicious payload (identified by the file hash) is present on a system, and the failed login attempts are part of its propagation, C2 communication, or privilege escalation routine.
4. **Credential Stuffing:** The attacker is using a list of previously breached credentials to test against the company's authentication systems, leading to multiple failed logins.
5. **Insider Threat:** An internal actor is attempting to gain unauthorized access to the admin account.

### 🔍 Enrichment Analysis

- **Similar Cases Found:** 4
- **Cases Eligible for SIEM:** 2 (fact*/profile* rules)
- **Cases Skipped:** 3 (other rule types)
- **Processing Cost:** $0.004014

**Cases Kept for SIEM Analysis:**
- `N/A`: profile_failed_logins_high_risk
- `N/A`: fact_data_exfil_attempt

## 🎯 Investigation Summary

### Key Findings
- ✅ Case successfully processed with real data integration
- ✅ Multi-agent AI analysis completed
- ✅ Forensic timeline analyzed (0 events)
- ✅ Entity extraction and correlation performed
- ✅ Rule-based filtering applied for SIEM queries

### Cost Analysis
- **Total AI Processing Cost:** $0.005485
- **Triage Cost:** $0.001471
- **Enrichment Cost:** $0.004014

### Technical Verification
- ✅ **Data Source:** Redis investigation keys
- ✅ **AI Platform:** Google Vertex AI (real billing)
- ✅ **Processing Mode:** 100% real data, zero mock responses
- ✅ **Audit Trail:** Complete PostgreSQL logging

---

*Investigation completed and report generated automatically on 2025-08-31 12:13:03 UTC*