# 🔍 SOC Platform Audit Report

**Case ID:** `test-clean-ui`
**Generated:** 2025-08-31 08:30:46 UTC
**Total Steps:** 5

---

## 📋 Audit Steps

### Step 1: TriageAgent

- **Timestamp:** `2025-08-31 12:29:16.164358+00:00`
- **Step ID:** `stp_84b29b76bffa`
- **Model:** gemini-2.5-flash
- **Autonomy Level:** autonomous
- **Tokens:** 2,544
- **Cost:** $0.001235
- **Hash:** `4dc242fe00d77ae2188f540d5fc40df2...`
- **Status:** ✅ SUCCESS
  - **Severity:** HIGH
  - **Entities:** 4 extracted

### Step 2: EnrichmentAgent

- **Timestamp:** `2025-08-31 12:29:31.769362+00:00`
- **Step ID:** `stp_4659572bffe8`
- **Model:** gemini-2.5-flash
- **Autonomy Level:** autonomous
- **Tokens:** 3,392
- **Cost:** $0.001427
- **Hash:** `80ffda0b74ba97c46811d66b1b8e2328...`
- **Status:** ✅ SUCCESS
  - **Response:** As a SOC Enrichment Agent, I've analyzed the security case `test-clean-ui` based on the provided entities and an empty case data.

Here's the enrichment and filtering analysis:

```json
{
  "related_i... (3465 chars)

### Step 3: CorrelationAgent

- **Timestamp:** `2025-08-31 12:29:47.127954+00:00`
- **Step ID:** `stp_81d1c62832a8`
- **Model:** gemini-2.5-pro
- **Autonomy Level:** autonomous
- **Tokens:** 1,783
- **Cost:** $0.006947
- **Hash:** `0928d1eb7c0095f0e9a2685f5788f7a4...`
- **Status:** ✅ SUCCESS

### Step 4: ResponseAgent

- **Timestamp:** `2025-08-31 12:30:14.677189+00:00`
- **Step ID:** `stp_4a8c3373de04`
- **Model:** gemini-2.5-pro
- **Autonomy Level:** autonomous
- **Tokens:** 3,320
- **Cost:** $0.020881
- **Hash:** `9a9891c931ad4906d727f5b779833b44...`
- **Status:** ✅ SUCCESS

### Step 5: ReportingAgent

- **Timestamp:** `2025-08-31 12:30:46.910342+00:00`
- **Step ID:** `stp_4b4fade927cd`
- **Model:** gemini-2.5-pro
- **Autonomy Level:** autonomous
- **Tokens:** 3,740
- **Cost:** $0.032529
- **Hash:** `71769cc24521885417de0bedaa3c342b...`
- **Status:** ✅ SUCCESS
  - **Response:** Of course. As a SOC Reporting Agent, I will generate a comprehensive incident report for case **test-clean-ui**.

**Note:** The provided `Case Analysis Results` were empty. Therefore, this report has ... (9538 chars)

## 📊 Summary

| Metric | Value |
|--------|-------|
| **Case ID** | `test-clean-ui` |
| **Total Steps** | 5 |
| **Agents Used** | CorrelationAgent, EnrichmentAgent, ReportingAgent, ResponseAgent, TriageAgent |
| **Total Tokens** | 14,779 |
| **Total Cost** | $0.063019 |
| **Duration** | 12:29:16 → 12:30:46 |

## 🔒 Hash Chain Verification

| Step | Hash | Status |
|------|------|--------|
| Genesis | `4dc242fe00d77ae2...` | ✅ |
| Step 2 | `80ffda0b74ba97c4...` | ✅ LINKED |
| Step 3 | `0928d1eb7c0095f0...` | ✅ LINKED |
| Step 4 | `9a9891c931ad4906...` | ✅ LINKED |
| Step 5 | `71769cc245218854...` | ✅ LINKED |

**Chain Integrity:** ✅ VERIFIED

---

## ✅ Compliance Verification

- ✅ **Complete audit trail maintained**
- ✅ **Cryptographic integrity verified**
- ✅ **Real data processing confirmed**
- ✅ **SOX/GDPR/SOC2 compliance ready**

*Report generated automatically on 2025-08-31 08:30:46 UTC*