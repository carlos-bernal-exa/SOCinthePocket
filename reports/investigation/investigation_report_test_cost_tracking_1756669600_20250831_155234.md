# 🔍 SOC Investigation Report

**Case ID:** `test-cost-tracking-1756669600`
**Generated:** 2025-08-31 15:52:34 UTC
**Investigation Type:** Multi-Agent AI Analysis

---

## 📋 Case Overview

| Field | Value |
|-------|-------|
| **Case ID** | `test-cost-tracking-1756669600` |
| **Alert ID** | `ALERT-56669600` |
| **Title** | Suspicious Network Activity Detected |
| **Status** | OPEN |
| **Severity** | HIGH |
| **Created** | `2025-08-31T19:51:53.844030+00:00` |

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
- **Processing Cost:** $0.001667

**Entities Extracted by AI:** 4

1. **ip:** `192.168.1.100` (confidence: 0.95)
2. **email:** `admin@company.com` (confidence: 0.95)
3. **username:** `admin` (confidence: 0.95)
4. **file_hash:** `5d41402abc4b2a76b9719d911017c592` (confidence: 0.95)

**AI-Generated Hypotheses:** 4

1. **External Brute-Force Attack**: An external attacker is attempting to gain unauthorized access to the 'admin' account. The malicious file hash could be related to a tool used by the attacker or a secondary payload if access is gained.
2. **Internal Compromised Host**: An internal system (192.168.1.100) has been compromised and is being used to launch a brute-force attack against the 'admin' account. The malicious file hash could be the malware responsible for the compromise of 192.168.1.100.
3. **Insider Threat/Misconfiguration**: A malicious insider or a misconfigured system is attempting to access the admin account. The file hash could be a tool being used by the insider or a component of the misconfiguration.
4. **Credential Stuffing**: The attacker is using a list of compromised credentials (from a different breach) to attempt logins, and the 'admin@company.com' account is one of the targets. The malicious file hash could be a secondary payload if access is gained.

### 🔍 Enrichment Analysis

- **Similar Cases Found:** 3
- **Cases Eligible for SIEM:** 1 (fact*/profile* rules)
- **Cases Skipped:** 3 (other rule types)
- **Processing Cost:** $0.003447

**Cases Kept for SIEM Analysis:**
- `fact_suspicious_login_12345`: fact_suspicious_login

## 🎯 Investigation Summary

### Key Findings
- ✅ Case successfully processed with real data integration
- ✅ Multi-agent AI analysis completed
- ✅ Forensic timeline analyzed (0 events)
- ✅ Entity extraction and correlation performed
- ✅ Rule-based filtering applied for SIEM queries

### Cost Analysis
- **Total AI Processing Cost:** $0.005114
- **Triage Cost:** $0.001667
- **Enrichment Cost:** $0.003447

### Technical Verification
- ✅ **Data Source:** Redis investigation keys
- ✅ **AI Platform:** Google Vertex AI (real billing)
- ✅ **Processing Mode:** 100% real data, zero mock responses
- ✅ **Audit Trail:** Complete PostgreSQL logging

---

*Investigation completed and report generated automatically on 2025-08-31 15:52:34 UTC*