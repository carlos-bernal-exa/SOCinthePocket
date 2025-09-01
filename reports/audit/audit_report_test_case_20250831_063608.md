# 🔍 SOC Platform Audit Report

**Case ID:** `test-case`
**Generated:** 2025-08-31 06:36:08 UTC
**Total Steps:** 2

---

## 📋 Audit Steps

### Step 1: TriageAgent

- **Timestamp:** `2025-08-31 10:35:51.663352+00:00`
- **Step ID:** `stp_cb8f6d5a9459`
- **Model:** gemini-2.5-flash
- **Autonomy Level:** supervised
- **Tokens:** 2,942
- **Cost:** $0.001595
- **Hash:** `7bb49174a990c3c0c8cc0f26910f92d4...`
- **Status:** ✅ SUCCESS
  - **Severity:** HIGH
  - **Entities:** 4 extracted

### Step 2: EnrichmentAgent

- **Timestamp:** `2025-08-31 10:36:08.616420+00:00`
- **Step ID:** `stp_1732f3f15caf`
- **Model:** gemini-2.5-flash
- **Autonomy Level:** supervised
- **Tokens:** 4,254
- **Cost:** $0.003173
- **Hash:** `934428200ce4805a0a82508e0e88dafa...`
- **Status:** ✅ SUCCESS
  - **Similar Cases:** 4 found
  - **Eligible Cases:** 2 for SIEM

## 📊 Summary

| Metric | Value |
|--------|-------|
| **Case ID** | `test-case` |
| **Total Steps** | 2 |
| **Agents Used** | EnrichmentAgent, TriageAgent |
| **Total Tokens** | 7,196 |
| **Total Cost** | $0.004768 |
| **Duration** | 10:35:51 → 10:36:08 |

## 🔒 Hash Chain Verification

| Step | Hash | Status |
|------|------|--------|
| Genesis | `7bb49174a990c3c0...` | ✅ |
| Step 2 | `934428200ce4805a...` | ✅ LINKED |

**Chain Integrity:** ✅ VERIFIED

---

## ✅ Compliance Verification

- ✅ **Complete audit trail maintained**
- ✅ **Cryptographic integrity verified**
- ✅ **Real data processing confirmed**
- ✅ **SOX/GDPR/SOC2 compliance ready**

*Report generated automatically on 2025-08-31 06:36:08 UTC*