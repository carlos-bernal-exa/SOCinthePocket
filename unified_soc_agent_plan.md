# SOC Agent Console — Unified PRD (UI Platform + Approvals & Downloads)

This document defines the **UI platform, recommended technologies, and detailed workflows** for approvals, downloads, and investigation management in the SOC Agent Console.

---

## 1. Platform & Technology Stack

### Backend
- **FastAPI** (Python) for API endpoints
- **Postgres** (or equivalent) for persistence (cases, audit, approvals, reports)
- **Redis/Qdrant** for vector/related case search
- **Neo4j** for graph memory (entities, rules, cases)
- **MinIO / S3** for report & artifact storage
- **Vertex AI Gemini** (via Vertex SDK) as LLM (Pro / Flash / Flash-Lite)
- **WebSockets / SSE** for live feed (audit + approvals stream)
- **Ed25519** signatures for audit integrity

### Frontend
- **React + Vite** as app framework
- **TailwindCSS** for styling
- **shadcn/ui** for UI primitives (cards, tabs, drawers, dialogs, buttons)
- **lucide-react** for icons
- **recharts** for charts (token usage, stats)
- **vis.js / cytoscape.js** for graph visualization (Neo4j data)
- **Highcharts or custom timeline** for case event timeline

### Deployment
- Containerized (Docker / Kubernetes)
- API gateway (Caddy / Nginx) for TLS + routing
- RBAC & SSO (Okta/OIDC) for analyst access

---

## 2. Core UI Features

### 2.1 Active Investigations Dashboard
- Table of active cases (`Case ID`, `Title`, `Entities`, `Assigned Agents`, `Status`, `Step`, `Confidence`, `Elapsed`)
- Expandable **Case Detail Sheet** (timeline, evidence, report tabs)
- Live activity feed (stream of audit events)

### 2.2 Knowledge Graph
- Graph visualization (Case ↔ Rule ↔ Entity)
- Powered by Neo4j
- Filters: case, last 24h, last 7d
- Click-through to past cases

### 2.3 Token Usage & Costs
- Bar/line chart showing tokens used by stage (Triage, Enrich, Investigate, Correlate, Report)
- Daily cost summary
- Per-case budget indicator

### 2.4 Agent Marketplace (“Hire Agents”)
- Drawer interface to add new agents
- Options: Agent type, Gemini model, autonomy level, budget, max steps
- API: `POST /agents/hire`
- Registered agents appear in sidebar / agent pool view

---

## 3. Approvals Workflow

### 3.1 Triggers
- **InvestigationAgent** → privileged queries
- **ResponseAgent** → containment/remediation
- **ReportingAgent** → external publishing
- **ControllerAgent** → budget switch

### 3.2 Autonomy Levels
- **L0_OBSERVE**: never execute, always ask  
- **L1_SUGGEST**: ask for side-effectful actions  
- **L2_EXECUTE**: auto safe actions, ask for destructive/privileged  
- **L3_FULL_AUTO**: execute all (still log approvals for audit)  

### 3.3 Data Models
See Pydantic definitions for `ApprovalRequest`, `ApprovalDecision`, `ReportMeta`.

### 3.4 Backend Endpoints
- `POST /approvals/request` → agent requests approval
- `GET /approvals?status=&case_id=` → list approvals
- `GET /approvals/{approval_id}` → details
- `POST /approvals/{approval_id}/decide` → approve/deny
- `GET /approvals/stream` → SSE/WebSocket

### 3.5 UI — Approval Center
- Panel with tabs: Pending, Approved, Denied
- Table columns: Created, Case, Agent, Action, Justification, Artifacts, Expires, Decision
- Drawer with JSON input, artifact previews, approve/deny buttons
- Linked from Case Detail (badge with pending count)
- Live Feed shows approval requests & decisions

### 3.6 Agent SDK Hook
- `ApprovalGate.require()` helper to pause/resume workflows
- Controller subscribes to approval decisions; resumes workflow or stops on deny

---

## 4. Reports & Downloads

### 4.1 Pipeline
1. ReportingAgent generates Markdown
2. Render to HTML and PDF (Playwright/Puppeteer)
3. Store in S3/MinIO
4. Save metadata in DB (ReportMeta)

### 4.2 Endpoints
- `GET /cases/{id}/report.{md|html|pdf}` → download reports
- `GET /cases/{id}/artifacts.zip` → evidence bundle
- `GET /cases/{id}/audit.jsonl` → audit export
- `GET /cases/{id}/audit.sig` → detached signature
- `GET /audit/verify/{id}` → quick verification

### 4.3 UI Integration
- Case Detail → Report tab: Download buttons for PDF/Markdown/Audit
- Audit export + signature verification available

---

## 5. Audit & Integrity

- Export audit chain as JSONL (append-only)
- Chained hash per line (Merkle-like)
- Ed25519 signature over export
- `/audit/verify/{case_id}` endpoint validates signature
- UI shows verification status (✔️ green / ❌ red)

---

## 6. Security & RBAC

- Approvals require Tier-2/IR-Lead/Manager role
- Action allowlist enforced at Controller before execution
- Reason required on deny
- Decision events logged in audit chain
- Rate-limiting for decision endpoints

---

## 7. Example Workflow (Happy Path)

1. InvestigationAgent requests host isolation → `ApprovalGate.require()`  
2. UI Approval Center shows new request  
3. Analyst approves → POST decision  
4. Controller resumes ResponseAgent → executes action  
5. Audit logs updated; Report includes decision  

---

## 8. Implementation Checklist

### Backend
- Tables: approvals, reports
- APIs: approvals, reports, audit exports
- SDK: ApprovalGate helper
- Controller: subscribe to approvals
- Report rendering pipeline
- Audit signing

### Frontend
- Active Investigations Dashboard
- Knowledge Graph visualization
- Token Usage chart
- Agent Marketplace (hire drawer)
- Approval Center
- Report Download buttons
- Live Feed integration

### Tests
- Approval lifecycle
- Report rendering & downloads
- Audit export & verification
- RBAC enforcement
- End-to-end: agent pause → analyst approve → resume

---
