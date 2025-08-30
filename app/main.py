from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import json
import logging
import uuid

from app.agents.triage import TriageAgent

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Agentic SOC Platform",
    description="AI-powered Security Operations Center with autonomous agents",
    version="1.0.0"
)

# Pydantic models
class CaseEnrichmentRequest(BaseModel):
    autonomy_level: str = "supervised"
    max_depth: int = 2
    include_raw_logs: bool = True

# Initialize agents
agents = {
    "triage": TriageAgent(),
}

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok", "version": "1.0.0"}

@app.post("/cases/{case_id}/enrich")
async def enrich_case(case_id: str, request: CaseEnrichmentRequest):
    """Enrich a security case using AI agents"""
    try:
        logger.info(f"Starting case enrichment for {case_id}")
        
        # Initialize enrichment context
        enrichment_context = {
            "case_id": case_id,
            "autonomy_level": request.autonomy_level,
            "max_depth": request.max_depth,
            "include_raw_logs": request.include_raw_logs,
            "steps": [],
            "entities": [],
            "related_cases": [],
            "total_cost": 0.0,
            "total_tokens": 0,
        }
        
        # Start with triage agent
        triage_agent = agents["triage"]
        triage_inputs = {
            "case_id": case_id,
            "case_data": request.dict(),
            "autonomy_level": request.autonomy_level
        }
        triage_result = await triage_agent.execute(case_id, triage_inputs, request.autonomy_level)
        
        enrichment_context["steps"].append(triage_result)
        
        # Extract entities from triage result
        triage_output = triage_result.get("triage_result", {})
        enrichment_context["entities"] = triage_output.get("entities", [])
        
        # For deeper analysis, add more processing
        if request.max_depth > 1:
            # Add additional mock entities for demonstration
            if not enrichment_context["entities"]:
                enrichment_context["entities"] = [
                    {"type": "ip", "value": "192.168.1.100", "confidence": 0.9},
                    {"type": "user", "value": "suspicious_user", "confidence": 0.8}
                ]
            
            enrichment_context["related_cases"] = [
                {"case_id": "CASE-456", "similarity": 0.7, "status": "resolved"},
                {"case_id": "CASE-789", "similarity": 0.6, "status": "open"}
            ]
        
        # Mock audit trail for demonstration
        audit_trail = [
            {
                "step_id": "stp_001",
                "timestamp": "2025-08-30T11:40:00Z",
                "agent": "TriageAgent",
                "action": "case_analysis"
            }
        ]
        
        return {
            "case_id": case_id,
            "status": "completed",
            "entities": enrichment_context["entities"],
            "related_cases": enrichment_context["related_cases"],
            "total_cost_usd": enrichment_context["total_cost"],
            "total_tokens": enrichment_context["total_tokens"],
            "audit_trail": audit_trail,
            "steps": len(enrichment_context["steps"]),
            "final_report": triage_output.get("summary", "Case analysis completed using Triage Agent"),
            "triage_assessment": {
                "severity": triage_output.get("severity", "medium"),
                "priority": triage_output.get("priority", 3),
                "escalation_needed": triage_output.get("escalation_needed", False),
                "initial_steps": triage_output.get("initial_steps", [])
            }
        }
        
    except Exception as e:
        logger.error(f"Error enriching case {case_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/audit/{case_id}")
async def get_case_audit(case_id: str):
    """Get audit trail for a case"""
    # Mock audit trail for demonstration
    audit_trail = [
        {
            "step_id": "stp_001",
            "timestamp": "2025-08-30T11:40:00Z",
            "agent": "TriageAgent",
            "action": "case_analysis"
        },
        {
            "step_id": "stp_002", 
            "timestamp": "2025-08-30T11:41:00Z",
            "agent": "TriageAgent",
            "action": "risk_assessment"
        }
    ]
    return {
        "case_id": case_id,
        "audit_trail": audit_trail,
        "total_steps": len(audit_trail)
    }

@app.get("/audit/verify/{case_id}")
async def verify_integrity(case_id: str):
    """Verify integrity of audit trail for a case"""
    # Mock integrity verification
    return {
        "case_id": case_id,
        "integrity_valid": True
    }

class KnowledgeIngestRequest(BaseModel):
    title: str
    content: str
    type: str
    tags: List[str] = []

@app.post("/knowledge/ingest")
async def ingest_knowledge(request: KnowledgeIngestRequest):
    """Ingest new knowledge into the platform"""
    # Mock knowledge ingestion
    knowledge_id = f"kb_{str(uuid.uuid4())[:8]}"
    return {"status": "success", "knowledge_id": knowledge_id}

@app.get("/knowledge/search")
async def search_knowledge(query: str, limit: int = 10):
    """Search knowledge base"""
    # Mock knowledge search results
    results = [
        {
            "id": "kb_001",
            "title": f"Knowledge about {query}",
            "content": f"This is relevant knowledge about {query}",
            "relevance_score": 0.9,
            "type": "threat_intel"
        },
        {
            "id": "kb_002", 
            "title": f"Analysis of {query}",
            "content": f"Additional analysis related to {query}",
            "relevance_score": 0.8,
            "type": "case_study"
        }
    ]
    return {"query": query, "results": results[:limit], "count": len(results)}

@app.get("/prompts/{agent_name}")
async def get_prompt(agent_name: str, version: Optional[str] = None):
    """Get prompt for an agent"""
    # Mock prompt data
    mock_prompt = {
        "content": f"You are the {agent_name} for the SOC platform. Your role is to analyze security incidents and provide actionable insights.",
        "version": version or "v1.0",
        "created_at": "2025-08-30T11:00:00Z",
        "modified_by": "admin"
    }
    return {
        "agent": agent_name,
        "prompt": mock_prompt,
        "version": mock_prompt["version"]
    }

class PromptUpdateRequest(BaseModel):
    content: str
    modified_by: str

@app.post("/prompts/{agent_name}")
async def update_prompt(agent_name: str, request: PromptUpdateRequest):
    """Update prompt for an agent"""
    # Mock prompt update
    new_version = "v1.1"
    return {"status": "success", "version": new_version}

@app.get("/stats")
async def get_platform_stats():
    """Get platform statistics"""
    # Mock platform statistics
    agent_status = {}
    for name, agent in agents.items():
        agent_status[name] = {
            "status": "active",
            "type": agent.__class__.__name__
        }
    
    return {
        "platform": {
            "status": "running",
            "version": "1.0.0",
            "agents_count": len(agents)
        },
        "agents": agent_status,
        "statistics": {
            "total_cases_processed": 42,
            "active_investigations": 3,
            "threat_indicators_detected": 127,
            "system_uptime_hours": 168
        }
    }

@app.on_event("startup")
async def startup_event():
    """Initialize platform on startup"""
    logger.info("SOC Platform starting up...")
    logger.info("SOC Platform startup complete - running in demonstration mode")