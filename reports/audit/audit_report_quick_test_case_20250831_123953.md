# 🔍 SOC Platform Audit Report

**Case ID:** `quick-test-case`
**Generated:** 2025-08-31 12:39:53 UTC
**Total Steps:** 2

---

## 📋 Audit Steps

### Step 1: TriageAgent

- **Timestamp:** `2025-08-31 16:39:33.906089+00:00`
- **Step ID:** `stp_b573b44a2461`
- **Model:** gemini-2.5-flash
- **Autonomy Level:** supervised
- **Tokens:** 2,734
- **Cost:** $0.001406
- **Hash:** `ee2a0e89755651b356fd5fd0c07b567b...`
- **Status:** ✅ SUCCESS
  - **Severity:** CRITICAL
  - **Entities:** 4 extracted

### Step 2: EnrichmentAgent

- **Timestamp:** `2025-08-31 16:39:53.028733+00:00`
- **Step ID:** `stp_d8670e65ce2c`
- **Model:** gemini-2.5-flash
- **Autonomy Level:** supervised
- **Tokens:** 4,724
- **Cost:** $0.004097
- **Hash:** `a1761db23c32b6b72c95aabf8b0d5224...`
- **Status:** ✅ SUCCESS
  - **Similar Cases:** 3 found
  - **Eligible Cases:** 2 for SIEM

## 📊 Summary

| Metric | Value |
|--------|-------|
| **Case ID** | `quick-test-case` |
| **Total Steps** | 2 |
| **Agents Used** | EnrichmentAgent, TriageAgent |
| **Total Tokens** | 7,458 |
| **Total Cost** | $0.005503 |
| **Duration** | 16:39:33 → 16:39:53 |

## 🔒 Hash Chain Verification

| Step | Hash | Status |
|------|------|--------|
| Genesis | `ee2a0e89755651b3...` | ✅ |
| Step 2 | `a1761db23c32b6b7...` | ✅ LINKED |

**Chain Integrity:** ✅ VERIFIED

---

## ✅ Compliance Verification

- ✅ **Complete audit trail maintained**
- ✅ **Cryptographic integrity verified**
- ✅ **Real data processing confirmed**
- ✅ **SOX/GDPR/SOC2 compliance ready**

*Report generated automatically on 2025-08-31 12:39:53 UTC*