from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import json
import logging
import uuid

from app.agents.triage import TriageAgent
from app.agents.controller import ControllerAgent
from app.agents.enrichment import EnrichmentAgent
from app.agents.investigation import InvestigationAgent
from app.agents.correlation import CorrelationAgent
from app.agents.response import ResponseAgent
from app.agents.reporting import ReportingAgent
from app.agents.knowledge import KnowledgeAgent

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
    "controller": ControllerAgent(),
    "triage": TriageAgent(),
    "enrichment": EnrichmentAgent(),
    "investigation": InvestigationAgent(),
    "correlation": CorrelationAgent(),
    "response": ResponseAgent(),
    "reporting": ReportingAgent(),
    "knowledge": KnowledgeAgent(),
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
        
        # Execute agent pipeline in proper sequence
        pipeline_results = {}
        
        # Step 1: Triage Agent
        logger.info(f"Step 1: Triage analysis for case {case_id}")
        triage_agent = agents["triage"]
        triage_inputs = {
            "case_id": case_id,
            "case_data": request.dict(),
            "autonomy_level": request.autonomy_level
        }
        triage_result = await triage_agent.execute(case_id, triage_inputs, request.autonomy_level)
        pipeline_results["triage"] = triage_result
        enrichment_context["steps"].append(triage_result)
        
        # Extract entities from triage
        triage_output = triage_result.get("triage_result", {})
        entities = triage_output.get("entities", [])
        enrichment_context["entities"] = entities
        
        # Step 2: Enrichment Agent
        logger.info(f"Step 2: Enrichment analysis for case {case_id}")
        enrichment_agent = agents["enrichment"]
        enrichment_inputs = {
            "case_id": case_id,
            "entities": entities,
            "case_data": request.dict()
        }
        enrichment_result = await enrichment_agent.execute(case_id, enrichment_inputs, request.autonomy_level)
        pipeline_results["enrichment"] = enrichment_result
        enrichment_context["steps"].append(enrichment_result)
        
        # Extract kept cases for investigation
        enrichment_output = enrichment_result.get("enrichment_result", {})
        kept_cases = enrichment_output.get("kept_cases", [])
        enrichment_context["related_cases"] = enrichment_output.get("related_items", [])
        
        # Step 3: Investigation Agent (only if we have eligible cases)
        investigation_output = {}
        if kept_cases and request.max_depth > 1:
            logger.info(f"Step 3: Investigation analysis for case {case_id}")
            investigation_agent = agents["investigation"]
            investigation_inputs = {
                "case_id": case_id,
                "kept_cases": kept_cases,
                "entities": entities
            }
            investigation_result = await investigation_agent.execute(case_id, investigation_inputs, request.autonomy_level)
            pipeline_results["investigation"] = investigation_result
            enrichment_context["steps"].append(investigation_result)
            investigation_output = investigation_result.get("investigation_result", {})
        
        # Step 4: Correlation Agent
        correlation_output = {}
        if request.max_depth > 1:
            logger.info(f"Step 4: Correlation analysis for case {case_id}")
            correlation_agent = agents["correlation"]
            correlation_inputs = {
                "case_id": case_id,
                "timeline_events": investigation_output.get("timeline_events", []),
                "ioc_set": investigation_output.get("ioc_set", {}),
                "attack_patterns": investigation_output.get("attack_patterns", [])
            }
            correlation_result = await correlation_agent.execute(case_id, correlation_inputs, request.autonomy_level)
            pipeline_results["correlation"] = correlation_result
            enrichment_context["steps"].append(correlation_result)
            correlation_output = correlation_result.get("correlation_result", {})
        
        # Step 5: Response Agent
        response_output = {}
        if request.max_depth > 1:
            logger.info(f"Step 5: Response planning for case {case_id}")
            response_agent = agents["response"]
            response_inputs = {
                "case_id": case_id,
                "attack_story": correlation_output.get("attack_story", {}),
                "ioc_set": investigation_output.get("ioc_set", {}),
                "mitre_mapping": correlation_output.get("mitre_mapping", {})
            }
            response_result = await response_agent.execute(case_id, response_inputs, request.autonomy_level)
            pipeline_results["response"] = response_result
            enrichment_context["steps"].append(response_result)
            response_output = response_result.get("response_result", {})
        
        # Step 6: Reporting Agent
        report_output = {}
        if request.max_depth > 1:
            logger.info(f"Step 6: Report generation for case {case_id}")
            reporting_agent = agents["reporting"]
            reporting_inputs = {
                "case_id": case_id,
                "attack_story": correlation_output.get("attack_story", {}),
                "containment_actions": response_output.get("containment_actions", []),
                "remediation_steps": response_output.get("remediation_steps", []),
                "timeline_events": investigation_output.get("timeline_events", []),
                "ioc_set": investigation_output.get("ioc_set", {}),
                "mitre_mapping": correlation_output.get("mitre_mapping", {})
            }
            reporting_result = await reporting_agent.execute(case_id, reporting_inputs, request.autonomy_level)
            pipeline_results["reporting"] = reporting_result
            enrichment_context["steps"].append(reporting_result)
            report_output = reporting_result.get("reporting_result", {})
        
        # Build comprehensive audit trail from all steps
        audit_trail = []
        for i, step_result in enumerate(enrichment_context["steps"]):
            audit_entry = {
                "step_id": f"stp_{str(i+1).zfill(3)}",
                "timestamp": step_result.get("timestamp", "2025-08-30T11:40:00Z"),
                "agent": step_result.get("agent_name", "Unknown"),
                "action": step_result.get("action_type", "analysis"),
                "status": step_result.get("status", "completed"),
                "tokens_used": step_result.get("token_usage", {}).get("total_tokens", 0),
                "cost_usd": step_result.get("token_usage", {}).get("cost_usd", 0.0)
            }
            audit_trail.append(audit_entry)
        
        # Calculate totals
        total_tokens = sum(step.get("token_usage", {}).get("total_tokens", 0) for step in enrichment_context["steps"])
        total_cost = sum(step.get("token_usage", {}).get("cost_usd", 0.0) for step in enrichment_context["steps"])
        
        return {
            "case_id": case_id,
            "status": "completed",
            "entities": enrichment_context["entities"],
            "related_cases": enrichment_context["related_cases"],
            "total_cost_usd": total_cost,
            "total_tokens": total_tokens,
            "audit_trail": audit_trail,
            "steps": len(enrichment_context["steps"]),
            "pipeline_results": pipeline_results,
            "final_report": report_output.get("incident_report", triage_output.get("summary", "Case analysis completed")),
            "triage_assessment": {
                "severity": triage_output.get("severity", "medium"),
                "priority": triage_output.get("priority", 3),
                "escalation_needed": triage_output.get("escalation_needed", False),
                "initial_steps": triage_output.get("initial_steps", [])
            },
            "investigation_summary": investigation_output.get("investigation_summary", {}),
            "attack_story": correlation_output.get("attack_story", {}),
            "containment_actions": response_output.get("containment_actions", []),
            "ioc_set": investigation_output.get("ioc_set", {})
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
    try:
        from app.services.prompts import prompt_manager
        prompt_content = await prompt_manager.get(agent_name, version)
        prompt_info = await prompt_manager.get_info(agent_name, version)
        
        return {
            "agent": agent_name,
            "prompt": {
                "content": prompt_content,
                "version": prompt_info.get("version", "v1.0"),
                "created_at": prompt_info.get("created_at", "2025-08-30T11:00:00Z"),
                "modified_by": prompt_info.get("modified_by", "system")
            },
            "version": prompt_info.get("version", "v1.0")
        }
    except Exception as e:
        # Fallback to mock data if prompt manager fails
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
    try:
        from app.services.prompts import prompt_manager
        new_version = await prompt_manager.update(agent_name, request.content, request.modified_by)
        return {"status": "success", "version": new_version}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update prompt: {str(e)}")

@app.get("/prompts/{agent_name}/latest")
async def get_latest_prompt(agent_name: str):
    """Get latest prompt version for an agent"""
    try:
        from app.services.prompts import prompt_manager
        prompt_content = await prompt_manager.get_latest(agent_name)
        prompt_info = await prompt_manager.get_info(agent_name)
        
        return {
            "agent": agent_name,
            "prompt": {
                "content": prompt_content,
                "version": prompt_info.get("version", "v1.0"),
                "created_at": prompt_info.get("created_at", "2025-08-30T11:00:00Z"),
                "modified_by": prompt_info.get("modified_by", "system")
            },
            "version": prompt_info.get("version", "v1.0"),
            "is_latest": True
        }
    except Exception as e:
        # Fallback to mock data if prompt manager fails
        mock_prompt = {
            "content": f"You are the {agent_name} for the SOC platform. Your role is to analyze security incidents and provide actionable insights.",
            "version": "v1.0",
            "created_at": "2025-08-30T11:00:00Z",
            "modified_by": "system"
        }
        return {
            "agent": agent_name,
            "prompt": mock_prompt,
            "version": "v1.0",
            "is_latest": True
        }

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