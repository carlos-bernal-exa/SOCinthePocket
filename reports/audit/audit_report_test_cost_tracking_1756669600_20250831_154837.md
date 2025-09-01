# 🔍 SOC Platform Audit Report

**Case ID:** `test-cost-tracking-1756669600`
**Generated:** 2025-08-31 15:48:37 UTC
**Total Steps:** 5

---

## 📋 Audit Steps

### Step 1: TriageAgent

- **Timestamp:** `2025-08-31 19:46:49.023659+00:00`
- **Step ID:** `stp_b81756ac9daf`
- **Model:** gemini-2.5-flash
- **Autonomy Level:** autonomous
- **Tokens:** 2,298
- **Cost:** $0.001281
- **Hash:** `a04896504e072b4bc6494da57698bb5d...`
- **Status:** ✅ SUCCESS
  - **Severity:** HIGH
  - **Entities:** 4 extracted

### Step 2: EnrichmentAgent

- **Timestamp:** `2025-08-31 19:47:08.133800+00:00`
- **Step ID:** `stp_c6c51bf901ed`
- **Model:** gemini-2.5-flash
- **Autonomy Level:** autonomous
- **Tokens:** 4,399
- **Cost:** $0.002654
- **Hash:** `74dc2484acfd960ed300e1caa97bcfb2...`
- **Status:** ✅ SUCCESS
  - **Similar Cases:** 3 found
  - **Eligible Cases:** 3 for SIEM

### Step 3: CorrelationAgent

- **Timestamp:** `2025-08-31 19:47:19.158779+00:00`
- **Step ID:** `stp_529acac95ac7`
- **Model:** gemini-2.5-pro
- **Autonomy Level:** autonomous
- **Tokens:** 1,543
- **Cost:** $0.007350
- **Hash:** `b4cc20fa2a42ca87f0ca63ab911200e6...`
- **Status:** ✅ SUCCESS

### Step 4: ResponseAgent

- **Timestamp:** `2025-08-31 19:47:50.549802+00:00`
- **Step ID:** `stp_4fedfc49fe82`
- **Model:** gemini-2.5-pro
- **Autonomy Level:** autonomous
- **Tokens:** 4,183
- **Cost:** $0.025638
- **Hash:** `8d91aa262b8ef26d022614e84b309fc2...`
- **Status:** ✅ SUCCESS

### Step 5: ReportingAgent

- **Timestamp:** `2025-08-31 19:48:37.353385+00:00`
- **Step ID:** `stp_c9a04be593be`
- **Model:** gemini-2.5-pro
- **Autonomy Level:** autonomous
- **Tokens:** 5,577
- **Cost:** $0.043082
- **Hash:** `3d10d8243737b0cdeae7f0460149b375...`
- **Status:** ✅ SUCCESS
  - **Response:** Of course. Here is the comprehensive incident report for case **test-cost-tracking-1756669600**.

***

### **CONFIDENTIAL: INCIDENT RESPONSE REPORT**

| | |
| :--- | :--- |
| **Case ID** | `test-cost-... (11456 chars)

## 📊 Summary

| Metric | Value |
|--------|-------|
| **Case ID** | `test-cost-tracking-1756669600` |
| **Total Steps** | 5 |
| **Agents Used** | CorrelationAgent, EnrichmentAgent, ReportingAgent, ResponseAgent, TriageAgent |
| **Total Tokens** | 18,000 |
| **Total Cost** | $0.080005 |
| **Duration** | 19:46:49 → 19:48:37 |

## 🔒 Hash Chain Verification

| Step | Hash | Status |
|------|------|--------|
| Genesis | `a04896504e072b4b...` | ✅ |
| Step 2 | `74dc2484acfd960e...` | ✅ LINKED |
| Step 3 | `b4cc20fa2a42ca87...` | ✅ LINKED |
| Step 4 | `8d91aa262b8ef26d...` | ✅ LINKED |
| Step 5 | `3d10d8243737b0cd...` | ✅ LINKED |

**Chain Integrity:** ✅ VERIFIED

---

## ✅ Compliance Verification

- ✅ **Complete audit trail maintained**
- ✅ **Cryptographic integrity verified**
- ✅ **Real data processing confirmed**
- ✅ **SOX/GDPR/SOC2 compliance ready**

*Report generated automatically on 2025-08-31 15:48:37 UTC*