# 🔍 SOC Platform Audit Report

**Case ID:** `status-test-case`
**Generated:** 2025-08-31 12:38:03 UTC
**Total Steps:** 5

---

## 📋 Audit Steps

### Step 1: TriageAgent

- **Timestamp:** `2025-08-31 16:36:13.331118+00:00`
- **Step ID:** `stp_72e016e2348b`
- **Model:** gemini-2.5-flash
- **Autonomy Level:** supervised
- **Tokens:** 2,478
- **Cost:** $0.001457
- **Hash:** `660954b9a84aeff45a6c4a05ff550062...`
- **Status:** ✅ SUCCESS
  - **Severity:** CRITICAL
  - **Entities:** 4 extracted

### Step 2: EnrichmentAgent

- **Timestamp:** `2025-08-31 16:36:39.230196+00:00`
- **Step ID:** `stp_c3a5f2e40432`
- **Model:** gemini-2.5-flash
- **Autonomy Level:** supervised
- **Tokens:** 6,308
- **Cost:** $0.002536
- **Hash:** `e3bde8aad9f5596950264e008f9b21a8...`
- **Status:** ✅ SUCCESS
  - **Similar Cases:** 4 found
  - **Eligible Cases:** 2 for SIEM

### Step 3: CorrelationAgent

- **Timestamp:** `2025-08-31 16:36:52.819105+00:00`
- **Step ID:** `stp_bdc22d3d2ad7`
- **Model:** gemini-2.5-pro
- **Autonomy Level:** supervised
- **Tokens:** 1,629
- **Cost:** $0.007536
- **Hash:** `4bdf687cbc70d04657f8369e774e2039...`
- **Status:** ✅ SUCCESS

### Step 4: ResponseAgent

- **Timestamp:** `2025-08-31 16:37:22.488395+00:00`
- **Step ID:** `stp_a0ef6650ad19`
- **Model:** gemini-2.5-pro
- **Autonomy Level:** supervised
- **Tokens:** 3,561
- **Cost:** $0.024955
- **Hash:** `e942d09220c625b28197f880863a59ca...`
- **Status:** ✅ SUCCESS

### Step 5: ReportingAgent

- **Timestamp:** `2025-08-31 16:38:03.195327+00:00`
- **Step ID:** `stp_3775838e0cc2`
- **Model:** gemini-2.5-pro
- **Autonomy Level:** supervised
- **Tokens:** 4,360
- **Cost:** $0.035259
- **Hash:** `967f0f1db26d68b7484d32ff07854406...`
- **Status:** ✅ SUCCESS
  - **Response:** Of course. As the SOC Reporting Agent, I will generate a comprehensive incident report for **Case: status-test-case**.

***

### **Incident Report: status-test-case**

| **Case ID** | status-test-case... (9084 chars)

## 📊 Summary

| Metric | Value |
|--------|-------|
| **Case ID** | `status-test-case` |
| **Total Steps** | 5 |
| **Agents Used** | CorrelationAgent, EnrichmentAgent, ReportingAgent, ResponseAgent, TriageAgent |
| **Total Tokens** | 18,336 |
| **Total Cost** | $0.071743 |
| **Duration** | 16:36:13 → 16:38:03 |

## 🔒 Hash Chain Verification

| Step | Hash | Status |
|------|------|--------|
| Genesis | `660954b9a84aeff4...` | ✅ |
| Step 2 | `e3bde8aad9f55969...` | ✅ LINKED |
| Step 3 | `4bdf687cbc70d046...` | ✅ LINKED |
| Step 4 | `e942d09220c625b2...` | ✅ LINKED |
| Step 5 | `967f0f1db26d68b7...` | ✅ LINKED |

**Chain Integrity:** ✅ VERIFIED

---

## ✅ Compliance Verification

- ✅ **Complete audit trail maintained**
- ✅ **Cryptographic integrity verified**
- ✅ **Real data processing confirmed**
- ✅ **SOX/GDPR/SOC2 compliance ready**

*Report generated automatically on 2025-08-31 12:38:03 UTC*