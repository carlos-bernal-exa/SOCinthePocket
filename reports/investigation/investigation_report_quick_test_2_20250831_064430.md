# 🔍 SOC Investigation Report

**Case ID:** `quick-test-2`
**Generated:** 2025-08-31 06:44:30 UTC
**Investigation Type:** Multi-Agent AI Analysis

---

## 📋 Case Overview

| Field | Value |
|-------|-------|
| **Case ID** | `quick-test-2` |
| **Alert ID** | `ALERT-k-test-2` |
| **Title** | Suspicious Network Activity Detected |
| **Status** | OPEN |
| **Severity** | HIGH |
| **Created** | `2025-08-31T10:43:57.508931+00:00` |

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
- **Processing Cost:** $0.001590

**Entities Extracted by AI:** 4

1. **ip:** `192.168.1.100` (confidence: 0.9)
2. **email:** `admin@company.com` (confidence: 0.9)
3. **file_hash:** `5d41402abc4b2a76b9719d911017c592` (confidence: 0.9)
4. **username:** `admin` (confidence: 0.9)

**AI-Generated Hypotheses:** 4

1. Compromised Internal Host: An internal system (192.168.1.100) has been compromised by malware (potentially associated with the file hash) and is attempting to gain elevated privileges or spread laterally by brute-forcing the admin account.
2. Insider Threat: A malicious insider is using the internal host 192.168.1.100 to attempt to gain unauthorized access to the admin account.
3. Misconfiguration/Legitimate Error: A misconfigured internal application or service on 192.168.1.100 is repeatedly attempting to authenticate with incorrect credentials, generating a high volume of failed logins. However, the associated malicious file hash makes this less likely unless the hash is a false positive.
4. Malware Activity: Malware on 192.168.1.100 is performing credential stuffing or brute-forcing as part of its attack chain.

### 🔍 Enrichment Analysis

- **Similar Cases Found:** 3
- **Cases Eligible for SIEM:** 2 (fact*/profile* rules)
- **Cases Skipped:** 2 (other rule types)
- **Processing Cost:** $0.002665

**Cases Kept for SIEM Analysis:**
- `case_2023-001`: fact_malware_alert
- `case_2023-005`: profile_unusual_login

## 🎯 Investigation Summary

### Key Findings
- ✅ Case successfully processed with real data integration
- ✅ Multi-agent AI analysis completed
- ✅ Forensic timeline analyzed (0 events)
- ✅ Entity extraction and correlation performed
- ✅ Rule-based filtering applied for SIEM queries

### Cost Analysis
- **Total AI Processing Cost:** $0.004255
- **Triage Cost:** $0.001590
- **Enrichment Cost:** $0.002665

### Technical Verification
- ✅ **Data Source:** Redis investigation keys
- ✅ **AI Platform:** Google Vertex AI (real billing)
- ✅ **Processing Mode:** 100% real data, zero mock responses
- ✅ **Audit Trail:** Complete PostgreSQL logging

---

*Investigation completed and report generated automatically on 2025-08-31 06:44:30 UTC*