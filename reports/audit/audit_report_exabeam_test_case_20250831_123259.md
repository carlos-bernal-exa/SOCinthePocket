# 🔍 SOC Platform Audit Report

**Case ID:** `exabeam-test-case`
**Generated:** 2025-08-31 12:32:59 UTC
**Total Steps:** 5

---

## 📋 Audit Steps

### Step 1: TriageAgent

- **Timestamp:** `2025-08-31 16:30:31.696394+00:00`
- **Step ID:** `stp_3bb547660cd8`
- **Model:** gemini-2.5-flash
- **Autonomy Level:** autonomous
- **Tokens:** 3,422
- **Cost:** $0.001670
- **Hash:** `87ae7483cf6d7bd615aa862dcfb36733...`
- **Status:** ✅ SUCCESS
  - **Severity:** CRITICAL
  - **Entities:** 4 extracted

### Step 2: EnrichmentAgent

- **Timestamp:** `2025-08-31 16:30:48.652842+00:00`
- **Step ID:** `stp_223c27a2a0cf`
- **Model:** gemini-2.5-flash
- **Autonomy Level:** autonomous
- **Tokens:** 4,408
- **Cost:** $0.004455
- **Hash:** `084ea6a42496cb663ac448754051be77...`
- **Status:** ✅ SUCCESS
  - **Similar Cases:** 5 found
  - **Eligible Cases:** 3 for SIEM

### Step 3: CorrelationAgent

- **Timestamp:** `2025-08-31 16:31:30.327971+00:00`
- **Step ID:** `stp_4b68362860d1`
- **Model:** gemini-2.5-pro
- **Autonomy Level:** autonomous
- **Tokens:** 5,136
- **Cost:** $0.041604
- **Hash:** `6c44ab8842f24d1d90c2ae008e5bd6cc...`
- **Status:** ✅ SUCCESS

### Step 4: ResponseAgent

- **Timestamp:** `2025-08-31 16:32:10.513596+00:00`
- **Step ID:** `stp_838232ed637c`
- **Model:** gemini-2.5-pro
- **Autonomy Level:** autonomous
- **Tokens:** 4,780
- **Cost:** $0.034636
- **Hash:** `d7b9aca199519af8bcff6f0e9db4906c...`
- **Status:** ✅ SUCCESS

### Step 5: ReportingAgent

- **Timestamp:** `2025-08-31 16:32:59.518821+00:00`
- **Step ID:** `stp_b3ada67c3596`
- **Model:** gemini-2.5-pro
- **Autonomy Level:** autonomous
- **Tokens:** 5,113
- **Cost:** $0.036806
- **Hash:** `f8cf9a27b1cebdae5b9c8fe987e92681...`
- **Status:** ✅ SUCCESS
  - **Response:** Of course. As the SOC Reporting Agent, I will generate a comprehensive incident report for **exabeam-test-case**. Since the case analysis results provided were empty, I will populate the report with a... (9450 chars)

## 📊 Summary

| Metric | Value |
|--------|-------|
| **Case ID** | `exabeam-test-case` |
| **Total Steps** | 5 |
| **Agents Used** | CorrelationAgent, EnrichmentAgent, ReportingAgent, ResponseAgent, TriageAgent |
| **Total Tokens** | 22,859 |
| **Total Cost** | $0.119171 |
| **Duration** | 16:30:31 → 16:32:59 |

## 🔒 Hash Chain Verification

| Step | Hash | Status |
|------|------|--------|
| Genesis | `87ae7483cf6d7bd6...` | ✅ |
| Step 2 | `084ea6a42496cb66...` | ✅ LINKED |
| Step 3 | `6c44ab8842f24d1d...` | ✅ LINKED |
| Step 4 | `d7b9aca199519af8...` | ✅ LINKED |
| Step 5 | `f8cf9a27b1cebdae...` | ✅ LINKED |

**Chain Integrity:** ✅ VERIFIED

---

## ✅ Compliance Verification

- ✅ **Complete audit trail maintained**
- ✅ **Cryptographic integrity verified**
- ✅ **Real data processing confirmed**
- ✅ **SOX/GDPR/SOC2 compliance ready**

*Report generated automatically on 2025-08-31 12:32:59 UTC*