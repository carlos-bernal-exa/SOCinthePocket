# 🔍 SOC Investigation Report

**Case ID:** `quick-test-case`
**Generated:** 2025-08-31 12:40:22 UTC
**Investigation Type:** Multi-Agent AI Analysis

---

## 📋 Case Overview

| Field | Value |
|-------|-------|
| **Case ID** | `quick-test-case` |
| **Alert ID** | `ALERT-est-case` |
| **Title** | Suspicious Network Activity Detected |
| **Status** | OPEN |
| **Severity** | HIGH |
| **Created** | `2025-08-31T16:39:53.088470+00:00` |

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
- **Processing Cost:** $0.001510

**Entities Extracted by AI:** 4

1. **ip_address:** `192.168.1.100` (confidence: 0.95)
2. **email_address:** `admin@company.com` (confidence: 0.95)
3. **file_hash:** `5d41402abc4b2a76b9719d911017c592` (confidence: 0.95)
4. **username:** `admin` (confidence: 0.95)

**AI-Generated Hypotheses:** 4

1. **External Brute Force Attack:** An external attacker is attempting to gain initial access to the organization's network by brute-forcing the 'admin' account.
2. **Internal Lateral Movement/Privilege Escalation:** An internal compromised host (192.168.1.100) is attempting to escalate privileges or move laterally by brute-forcing the 'admin' account.
3. **Malware-Initiated Attack:** A system (potentially 192.168.1.100) is infected with malware (indicated by the file hash) that is attempting to brute-force accounts or spread further within the network.
4. **Credential Stuffing Attack:** The attacker is using a list of compromised credentials from a third-party breach to attempt logins against the 'admin' account.

### 🔍 Enrichment Analysis

- **Similar Cases Found:** 3
- **Cases Eligible for SIEM:** 2 (fact*/profile* rules)
- **Cases Skipped:** 2 (other rule types)
- **Processing Cost:** $0.003755

**Cases Kept for SIEM Analysis:**
- `case_fact_failed_logins_from_new_ip_123`: fact_failed_logins_from_new_ip
- `case_profile_unusual_admin_activity_456`: profile_unusual_admin_activity

## 🎯 Investigation Summary

### Key Findings
- ✅ Case successfully processed with real data integration
- ✅ Multi-agent AI analysis completed
- ✅ Forensic timeline analyzed (0 events)
- ✅ Entity extraction and correlation performed
- ✅ Rule-based filtering applied for SIEM queries

### Cost Analysis
- **Total AI Processing Cost:** $0.005265
- **Triage Cost:** $0.001510
- **Enrichment Cost:** $0.003755

### Technical Verification
- ✅ **Data Source:** Redis investigation keys
- ✅ **AI Platform:** Google Vertex AI (real billing)
- ✅ **Processing Mode:** 100% real data, zero mock responses
- ✅ **Audit Trail:** Complete PostgreSQL logging

---

*Investigation completed and report generated automatically on 2025-08-31 12:40:22 UTC*