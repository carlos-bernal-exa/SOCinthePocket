# 🔍 SOC Investigation Report

**Case ID:** `exabeam-test-case`
**Generated:** 2025-08-31 12:33:23 UTC
**Investigation Type:** Multi-Agent AI Analysis

---

## 📋 Case Overview

| Field | Value |
|-------|-------|
| **Case ID** | `exabeam-test-case` |
| **Alert ID** | `ALERT-est-case` |
| **Title** | Suspicious Network Activity Detected |
| **Status** | OPEN |
| **Severity** | HIGH |
| **Created** | `2025-08-31T16:32:59.584106+00:00` |

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
- **Processing Cost:** $0.001727

**Entities Extracted by AI:** 4

1. **ip:** `192.168.1.100` (confidence: 0.95)
2. **email:** `admin@company.com` (confidence: 0.95)
3. **username:** `admin` (confidence: 0.95)
4. **file_hash:** `5d41402abc4b2a76b9719d911017c592` (confidence: 0.95)

**AI-Generated Hypotheses:** 4

1. **External Brute-Force with Malware Delivery:** An external attacker is attempting to brute-force the admin account, and simultaneously, a malicious file (possibly a dropper, backdoor, or credential stealer) has been introduced into the environment, potentially via another vector or as part of the same attack chain.
2. **Internal Compromise and Lateral Movement:** An internal system (192.168.1.100) is already compromised and is attempting to gain elevated privileges by brute-forcing the admin account, possibly to facilitate lateral movement, privilege escalation, or further malicious activity. The malicious file hash could be related to the initial compromise or a tool being deployed.
3. **Insider Threat:** A malicious insider is attempting to gain unauthorized access to the admin account and has introduced a malicious file to aid in their objectives or establish persistence.
4. **Misconfigured Application/Service Account:** A misconfigured application or service account on 192.168.1.100 is repeatedly attempting to authenticate as 'admin', causing the failed login alerts. The malicious file hash, in this less likely scenario, would be an unrelated detection on the same host.

### 🔍 Enrichment Analysis

- **Similar Cases Found:** 0
- **Cases Eligible for SIEM:** 0 (fact*/profile* rules)
- **Cases Skipped:** 1 (other rule types)
- **Processing Cost:** $0.001569

## 🎯 Investigation Summary

### Key Findings
- ✅ Case successfully processed with real data integration
- ✅ Multi-agent AI analysis completed
- ✅ Forensic timeline analyzed (0 events)
- ✅ Entity extraction and correlation performed
- ✅ Rule-based filtering applied for SIEM queries

### Cost Analysis
- **Total AI Processing Cost:** $0.003296
- **Triage Cost:** $0.001727
- **Enrichment Cost:** $0.001569

### Technical Verification
- ✅ **Data Source:** Redis investigation keys
- ✅ **AI Platform:** Google Vertex AI (real billing)
- ✅ **Processing Mode:** 100% real data, zero mock responses
- ✅ **Audit Trail:** Complete PostgreSQL logging

---

*Investigation completed and report generated automatically on 2025-08-31 12:33:23 UTC*