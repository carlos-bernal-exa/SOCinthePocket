from .base import AgentBase
from ..adapters.neo4j_store import neo4j_store
from ..adapters.redis_store import RedisStore
from typing import Dict, Any
import os

class TriageAgent(AgentBase):
    def __init__(self):
        super().__init__(name="TriageAgent", model="gemini-2.5-flash", role="triage")
        self.redis_store = RedisStore(os.getenv("REDIS_URL", "redis://localhost:6379"))
    
    async def _format_prompt(self, prompt_content: str, inputs: Dict[str, Any]) -> str:
        """Format triage-specific prompt with automatic case data fetching"""
        case_id = inputs.get("case_id", "unknown")
        case_data = inputs.get("case_data", {})
        
        # If no case data provided, try to fetch from Redis
        if not case_data and case_id != "unknown":
            try:
                case_summary = await self.redis_store.get_summary(case_id)
                if case_summary:
                    case_data = case_summary
                    self.logger.info(f"Retrieved case data for {case_id} from Redis")
                else:
                    self.logger.warning(f"No case data found for {case_id} in Redis")
            except Exception as e:
                self.logger.error(f"Failed to fetch case data for {case_id}: {e}")
        
        # Format case data for display
        if case_data:
            case_display = f"""
Case ID: {case_data.get('case_id', case_id)}
Alert ID: {case_data.get('alert_id', 'N/A')}
Title: {case_data.get('title', 'N/A')}
Description: {case_data.get('description', 'N/A')}
Current Status: {case_data.get('status', 'N/A')}
Created: {case_data.get('created_at', 'N/A')}
Existing Severity Assessment: {case_data.get('severity', 'N/A')}

Entities Found:
{self._format_entities(case_data.get('entities', {}))}

Raw Investigation Data:
- Threat Score: {case_data.get('raw_data', {}).get('threat_score', 'N/A')}
- MITRE Tactics: {', '.join(case_data.get('raw_data', {}).get('mitre_tactics', []))}
- Timeline Events: {len(case_data.get('raw_data', {}).get('timeline_events', []))} events
- Investigation Type: {case_data.get('raw_data', {}).get('response_type', 'N/A')}
"""
        else:
            case_display = f"No case data available for case ID: {case_id}"
        
        formatted = f"""You are a SOC Triage Agent analyzing security case {case_id}.

Your role is to:
1. Assess the severity and priority of the security incident
2. Identify key entities (IPs, domains, users, files, etc.) from the case data
3. Determine if immediate escalation is needed
4. Suggest initial investigation steps based on the available evidence

{case_display}

Based on this case data, please provide a structured JSON response with:
- severity: (low/medium/high/critical) - based on the evidence and threat indicators
- priority: (1-5, where 1 is highest) - based on severity and impact assessment
- entities: [{{type: "ip", value: "192.168.1.1", confidence: 0.9}}, ...] - extract all relevant entities with confidence scores
- escalation_needed: boolean - true if this requires immediate analyst attention
- initial_steps: [list of suggested investigation steps] - specific actionable recommendations
- summary: brief analysis summary explaining your assessment
- hypotheses: [list of potential attack scenarios or explanations for the observed activity]
"""
        return formatted
    
    def _format_entities(self, entities: Dict[str, Any]) -> str:
        """Format entities dictionary for display"""
        if not entities:
            return "No entities found"
        
        formatted_entities = []
        for entity_type, entity_list in entities.items():
            if isinstance(entity_list, list) and entity_list:
                formatted_entities.append(f"- {entity_type}: {', '.join(map(str, entity_list))}")
            elif entity_list:
                formatted_entities.append(f"- {entity_type}: {entity_list}")
        
        return "\n".join(formatted_entities) if formatted_entities else "No entities found"
    
    async def _process_outputs(self, response: Dict[str, Any], inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Process triage outputs into structured format with Neo4j integration"""
        text_response = response.get("text", "")
        
        # Try to extract JSON from response or create structured output
        try:
            import json
            # Look for JSON in the response
            if "{" in text_response and "}" in text_response:
                start = text_response.find("{")
                end = text_response.rfind("}") + 1
                json_str = text_response[start:end]
                structured_output = json.loads(json_str)
            else:
                # Create default structure if no JSON found
                structured_output = {
                    "severity": "medium",
                    "priority": 3,
                    "entities": [],
                    "escalation_needed": False,
                    "initial_steps": ["Review case details", "Validate indicators"],
                    "summary": text_response[:200] + "..." if len(text_response) > 200 else text_response
                }
        except (json.JSONDecodeError, Exception):
            # Fallback structure
            structured_output = {
                "severity": "medium", 
                "priority": 3,
                "entities": [],
                "escalation_needed": False,
                "initial_steps": ["Review case details"],
                "summary": text_response[:200] + "..." if len(text_response) > 200 else text_response
            }
        
        # Store entities in Neo4j (temporarily disabled for debugging)
        case_id = inputs.get("case_id")
        if case_id and structured_output.get("entities"):
            print(f"Would store {len(structured_output['entities'])} entities in Neo4j (disabled for debugging)")
            # for entity in structured_output["entities"]:
            #     if isinstance(entity, dict):
            #         entity_type = entity.get("type", "unknown")
            #         entity_value = entity.get("value", "")
            #         if entity_value:
            #             await neo4j_store.create_observed_entity(case_id, entity_type, entity_value)
        
        return {
            "case_id": inputs.get("case_id"),
            "triage_result": structured_output,
            "raw_analysis": text_response,
            "model_info": {
                "model": response.get("model"),
                "finish_reason": response.get("finish_reason")
            }
        }
