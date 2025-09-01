# 🔍 SOC Investigation Report

**Case ID:** `test-cost-tracking-1756669600`
**Generated:** 2025-08-31 15:55:34 UTC
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
| **Created** | `2025-08-31T19:54:58.629431+00:00` |

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
- **Processing Cost:** $0.001438

**Entities Extracted by AI:** 4

1. **ip:** `192.168.1.100` (confidence: 0.95)
2. **email_address:** `admin@company.com` (confidence: 0.95)
3. **file_hash:** `5d41402abc4b2a76b9719d911017c592` (confidence: 0.9)
4. **username:** `admin` (confidence: 0.9)

**AI-Generated Hypotheses:** 4

1. An external attacker is attempting to gain unauthorized access to a high-privilege administrative account via brute force.
2. An internal compromised host (192.168.1.100) is being used as a pivot point to brute force the admin account, possibly by an attacker or malicious software.
3. The malicious file hash 5d41402abc4b2a76b9719d911017c592 is a tool being used for the brute force attack or a payload intended for delivery upon successful login.
4. A disgruntled insider or unauthorized user on 192.168.1.100 is attempting to gain elevated privileges.

### 🔍 Enrichment Analysis

- **Similar Cases Found:** 3
- **Cases Eligible for SIEM:** 2 (fact*/profile* rules)
- **Cases Skipped:** 2 (other rule types)
- **Processing Cost:** $0.003367

**Cases Kept for SIEM Analysis:**
- `fact-bruteforce-attempt-987654321`: fact_failed_logins_threshold_exceeded
- `profile-suspicious-file-download-555444333`: profile_suspicious_file_download

## 🎯 Investigation Summary

### Key Findings
- ✅ Case successfully processed with real data integration
- ✅ Multi-agent AI analysis completed
- ✅ Forensic timeline analyzed (0 events)
- ✅ Entity extraction and correlation performed
- ✅ Rule-based filtering applied for SIEM queries

### Cost Analysis
- **Total AI Processing Cost:** $0.004805
- **Triage Cost:** $0.001438
- **Enrichment Cost:** $0.003367

### Technical Verification
- ✅ **Data Source:** Redis investigation keys
- ✅ **AI Platform:** Google Vertex AI (real billing)
- ✅ **Processing Mode:** 100% real data, zero mock responses
- ✅ **Audit Trail:** Complete PostgreSQL logging

---

*Investigation completed and report generated automatically on 2025-08-31 15:55:34 UTC*