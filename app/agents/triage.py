from .base import AgentBase
from typing import Dict, Any

class TriageAgent(AgentBase):
    def __init__(self):
        super().__init__(name="TriageAgent", model="gemini-2.5-flash", role="triage")
    
    def _format_prompt(self, prompt_content: str, inputs: Dict[str, Any]) -> str:
        """Format triage-specific prompt"""
        case_id = inputs.get("case_id", "unknown")
        case_data = inputs.get("case_data", {})
        
        formatted = f"""You are a SOC Triage Agent analyzing security case {case_id}.

Your role is to:
1. Assess the severity and priority of the security incident
2. Identify key entities (IPs, domains, users, files, etc.) 
3. Determine if immediate escalation is needed
4. Suggest initial investigation steps

Case Data:
{case_data}

Please provide a structured JSON response with:
- severity: (low/medium/high/critical)
- priority: (1-5, where 1 is highest)
- entities: {{type: value, confidence: 0.0-1.0}}
- escalation_needed: boolean
- initial_steps: [list of suggested investigation steps]
- summary: brief analysis summary
"""
        return formatted
    
    def _process_outputs(self, response: Dict[str, Any], inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Process triage outputs into structured format"""
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
        
        return {
            "case_id": inputs.get("case_id"),
            "triage_result": structured_output,
            "raw_analysis": text_response,
            "model_info": {
                "model": response.get("model"),
                "finish_reason": response.get("finish_reason")
            }
        }
