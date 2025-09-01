# 🔍 SOC Platform Audit Report

**Case ID:** `test-real-ai`
**Generated:** 2025-08-31 06:39:32 UTC
**Total Steps:** 2

---

## 📋 Audit Steps

### Step 1: TriageAgent

- **Timestamp:** `2025-08-31 10:39:13.902802+00:00`
- **Step ID:** `stp_06b5ad154bf2`
- **Model:** gemini-2.5-flash
- **Autonomy Level:** autonomous
- **Tokens:** 2,716
- **Cost:** $0.001383
- **Hash:** `b34ccd05e00d831642ecadaf26ae8462...`
- **Status:** ✅ SUCCESS
  - **Severity:** HIGH
  - **Entities:** 4 extracted

### Step 2: EnrichmentAgent

- **Timestamp:** `2025-08-31 10:39:32.403792+00:00`
- **Step ID:** `stp_b8b2f7eacd32`
- **Model:** gemini-2.5-flash
- **Autonomy Level:** autonomous
- **Tokens:** 4,228
- **Cost:** $0.002365
- **Hash:** `a3e35bbcef38ec5f31b763b41e718c5d...`
- **Status:** ✅ SUCCESS
  - **Similar Cases:** 4 found
  - **Eligible Cases:** 2 for SIEM

## 📊 Summary

| Metric | Value |
|--------|-------|
| **Case ID** | `test-real-ai` |
| **Total Steps** | 2 |
| **Agents Used** | EnrichmentAgent, TriageAgent |
| **Total Tokens** | 6,944 |
| **Total Cost** | $0.003748 |
| **Duration** | 10:39:13 → 10:39:32 |

## 🔒 Hash Chain Verification

| Step | Hash | Status |
|------|------|--------|
| Genesis | `b34ccd05e00d8316...` | ✅ |
| Step 2 | `a3e35bbcef38ec5f...` | ✅ LINKED |

**Chain Integrity:** ✅ VERIFIED

---

## ✅ Compliance Verification

- ✅ **Complete audit trail maintained**
- ✅ **Cryptographic integrity verified**
- ✅ **Real data processing confirmed**
- ✅ **SOX/GDPR/SOC2 compliance ready**

*Report generated automatically on 2025-08-31 06:39:32 UTC*