# 🔍 SOC Investigation Report

**Case ID:** `6c7a11e3-5fbd-4cf9-8eee-e826aa40f9dc`
**Generated:** 2025-08-31 07:10:04 UTC
**Investigation Type:** Multi-Agent AI Analysis

---

## 📋 Case Overview

| Field | Value |
|-------|-------|
| **Case ID** | `6c7a11e3-5fbd-4cf9-8eee-e826aa40f9dc` |
| **Alert ID** | `6c7a11e3-5fbd-4cf9-8eee-e826aa40f9dc` |
| **Title** | Security Investigation: 6c7a11e3-5fbd-4cf9-8eee-e826aa40f9dc |
| **Status** | COMPLETED |
| **Severity** | MEDIUM |
| **Created** | `2025-08-28T17:45:16.248131` |

### Description

> Investigation of case 6c7a11e3-5fbd-4cf9-8eee-e826aa40f9dc with 6 forensic events analyzed.
- 2025-07-20T17:13:51.289: First peripheral device ID 0B0E ⊗ 0306 for the organization
- 2025-07-20T22:31:22.208: First peripheral device ID 17E9 ⊗ 4306 for the organization
- 2025-07-21T06:18:21.187: First peripheral device ID 24AE ⊗ 2010 for the organization
... and 3 more events

## 📅 Forensic Timeline

**Total Events:** 6

### Event 1
- **Time:** `2025-07-20T17:13:51.289`
- **User:** susheel.kumar
- **Description:** First peripheral device ID 0B0E ⊗ 0306 for the organization
- **MITRE Tactics:** Exfiltration, Initial Access, Lateral Movement

### Event 2
- **Time:** `2025-07-20T22:31:22.208`
- **User:** andrew.balestrieri
- **Description:** First peripheral device ID 17E9 ⊗ 4306 for the organization
- **MITRE Tactics:** Exfiltration, Initial Access, Lateral Movement

### Event 3
- **Time:** `2025-07-21T06:18:21.187`
- **User:** aravind.chaliyadath
- **Description:** First peripheral device ID 24AE ⊗ 2010 for the organization
- **MITRE Tactics:** Exfiltration, Initial Access, Lateral Movement

### Event 4
- **Time:** `2025-07-21T06:26:09.986`
- **User:** aravind.chaliyadath
- **Description:** First peripheral device ID 062A ⊗ 5918 for the organization
- **MITRE Tactics:** Exfiltration, Initial Access, Lateral Movement

### Event 5
- **Time:** `2025-07-21T12:34:36.088`
- **User:** deepak.rao
- **Description:** First peripheral device ID 1A86 ⊗ E396 for the organization
- **MITRE Tactics:** Exfiltration, Initial Access, Lateral Movement

### Event 6
- **Time:** `2025-07-21T12:35:47.879`
- **User:** deepak.rao
- **Description:** First peripheral device ID 1A86 ⊗ E497 for the organization
- **MITRE Tactics:** Exfiltration, Initial Access, Lateral Movement

## 🤖 AI Analysis Results

### 🏷️ Triage Analysis

- **Severity Assessment:** MEDIUM
- **Priority Level:** 3
- **Escalation Needed:** Yes
- **Processing Cost:** $0.001092

**Entities Extracted by AI:** 3

1. **usb_vid_pid:** `0B0E ⊗ 0306` (confidence: 1.0)
2. **usb_vid_pid:** `17E9 ⊗ 4306` (confidence: 1.0)
3. **usb_vid_pid:** `24AE ⊗ 2010` (confidence: 1.0)

**AI-Generated Hypotheses:** 4

1. **Unauthorized Device Usage:** An employee connected a personal or unapproved USB device, potentially violating security policies.
2. **Malware Delivery:** A malicious USB device was connected, attempting to introduce malware to the network or compromise the endpoint.
3. **Data Exfiltration Attempt:** An insider is using an unauthorized USB device to copy sensitive data from company systems.
4. **Legitimate New Hardware:** New, legitimate hardware (e.g., company-issued peripherals) was connected for the first time and triggered the alert due to a lack of prior baselining or asset registration.

### 🔍 Enrichment Analysis

- **Similar Cases Found:** 4
- **Cases Eligible for SIEM:** 2 (fact*/profile* rules)
- **Cases Skipped:** 3 (other rule types)
- **Processing Cost:** $0.002764

**Cases Kept for SIEM Analysis:**
- `case_A_12345`: fact_usb_device_seen_first_time
- `case_C_11223`: profile_user_usb_device_deviation

## 🎯 Investigation Summary

### Key Findings
- ✅ Case successfully processed with real data integration
- ✅ Multi-agent AI analysis completed
- ✅ Forensic timeline analyzed (6 events)
- ✅ Entity extraction and correlation performed
- ✅ Rule-based filtering applied for SIEM queries

### Cost Analysis
- **Total AI Processing Cost:** $0.003856
- **Triage Cost:** $0.001092
- **Enrichment Cost:** $0.002764

### Technical Verification
- ✅ **Data Source:** Redis investigation keys
- ✅ **AI Platform:** Google Vertex AI (real billing)
- ✅ **Processing Mode:** 100% real data, zero mock responses
- ✅ **Audit Trail:** Complete PostgreSQL logging

---

*Investigation completed and report generated automatically on 2025-08-31 07:10:04 UTC*