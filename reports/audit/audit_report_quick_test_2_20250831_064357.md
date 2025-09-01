# 🔍 SOC Platform Audit Report

**Case ID:** `quick-test-2`
**Generated:** 2025-08-31 06:43:57 UTC
**Total Steps:** 2

---

## 📋 Audit Steps

### Step 1: TriageAgent

- **Timestamp:** `2025-08-31 10:43:41.798425+00:00`
- **Step ID:** `stp_2ac8eb25b1d7`
- **Model:** gemini-2.5-flash
- **Autonomy Level:** autonomous
- **Tokens:** 2,312
- **Cost:** $0.001328
- **Hash:** `73636d7cbae3585db784effff805bbf5...`
- **Status:** ✅ SUCCESS
  - **Severity:** HIGH
  - **Entities:** 4 extracted

### Step 2: EnrichmentAgent

- **Timestamp:** `2025-08-31 10:43:57.409509+00:00`
- **Step ID:** `stp_13e50a822edf`
- **Model:** gemini-2.5-flash
- **Autonomy Level:** autonomous
- **Tokens:** 3,764
- **Cost:** $0.003528
- **Hash:** `fdcd25b12bb31b1b5f2e43a1e1e91ab5...`
- **Status:** ✅ SUCCESS
  - **Similar Cases:** 4 found
  - **Eligible Cases:** 3 for SIEM

## 📊 Summary

| Metric | Value |
|--------|-------|
| **Case ID** | `quick-test-2` |
| **Total Steps** | 2 |
| **Agents Used** | EnrichmentAgent, TriageAgent |
| **Total Tokens** | 6,076 |
| **Total Cost** | $0.004856 |
| **Duration** | 10:43:41 → 10:43:57 |

## 🔒 Hash Chain Verification

| Step | Hash | Status |
|------|------|--------|
| Genesis | `73636d7cbae3585d...` | ✅ |
| Step 2 | `fdcd25b12bb31b1b...` | ✅ LINKED |

**Chain Integrity:** ✅ VERIFIED

---

## ✅ Compliance Verification

- ✅ **Complete audit trail maintained**
- ✅ **Cryptographic integrity verified**
- ✅ **Real data processing confirmed**
- ✅ **SOX/GDPR/SOC2 compliance ready**

*Report generated automatically on 2025-08-31 06:43:57 UTC*