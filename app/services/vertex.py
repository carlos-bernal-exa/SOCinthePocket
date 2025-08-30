"""
Vertex AI Gemini wrapper with token tracking and cost calculation
Mock implementation for initial testing
"""
import os
import json
import asyncio
import random
from typing import Dict, Any, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

# Model pricing per million tokens (USD)
MODEL_PRICING = {
    "gemini-2.5-pro": {"input": 3.50, "output": 10.50},
    "gemini-2.5-flash": {"input": 0.35, "output": 1.40},
    "gemini-2.5-flash-lite": {"input": 0.05, "output": 0.20}
}

class VertexAIService:
    def __init__(self):
        self.project_id = "threatexplainer"
        self.location = "us-central1"
        logger.info("VertexAI Service initialized (mock mode)")
    
    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost in USD based on token usage and model pricing"""
        if model not in MODEL_PRICING:
            logger.warning(f"Unknown model {model}, using default pricing")
            return 0.0
        
        pricing = MODEL_PRICING[model]
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        return round(input_cost + output_cost, 6)
    
    def _mock_response_for_agent(self, agent_name: str, prompt: str) -> str:
        """Generate mock responses based on agent type"""
        mock_responses = {
            "TriageAgent": {
                "entities": [
                    {"type": "ip", "value": "192.168.1.100", "confidence": 0.95},
                    {"type": "domain", "value": "suspicious.example.com", "confidence": 0.85},
                    {"type": "hash", "value": "a1b2c3d4e5f6", "confidence": 0.90}
                ],
                "severity": "high",
                "hypotheses": ["Potential malware infection", "Lateral movement detected"]
            },
            "EnrichmentAgent": {
                "related_items": [
                    {"case_id": "case-456", "similarity": 0.85, "reason": "Similar IP addresses"},
                    {"case_id": "case-789", "similarity": 0.72, "reason": "Same malware family"}
                ],
                "raw_cases": ["case-123", "case-456"],
                "kept_cases": ["case-123"],  # Only fact/profile rules
                "skipped_cases": ["case-456"]  # Other rule types
            },
            "InvestigationAgent": {
                "timeline": [
                    {"timestamp": "2025-08-30T10:00:00Z", "event": "Initial access detected"},
                    {"timestamp": "2025-08-30T10:05:00Z", "event": "Privilege escalation attempt"}
                ],
                "iocs": ["192.168.1.100", "suspicious.example.com"],
                "query_results": "25 matching events found in SIEM"
            },
            "CorrelationAgent": {
                "attack_chain": ["Initial Access", "Privilege Escalation", "Lateral Movement"],
                "mitre_tactics": ["T1190", "T1068", "T1021"],
                "threat_actor": "APT-Generic"
            },
            "ResponseAgent": {
                "recommendations": [
                    {"action": "isolate", "target": "192.168.1.100", "priority": "high"},
                    {"action": "disable", "target": "user.account", "priority": "medium"}
                ]
            },
            "ReportingAgent": {
                "report": {
                    "executive_summary": "High-severity security incident detected",
                    "technical_details": "Malware infection with lateral movement",
                    "recommendations": "Immediate containment required"
                }
            },
            "KnowledgeAgent": {
                "results": [
                    {"title": "Similar incident from 2024", "relevance": 0.85},
                    {"title": "Malware family analysis", "relevance": 0.78}
                ]
            }
        }
        
        # Extract agent name from prompt or use default
        for agent in mock_responses:
            if agent.lower() in prompt.lower():
                return json.dumps(mock_responses[agent], indent=2)
        
        return json.dumps(mock_responses.get(agent_name, {"status": "processed", "result": "Mock analysis complete"}), indent=2)
    
    async def run_gemini(
        self,
        model: str,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.1,
        max_output_tokens: int = 8192,
        agent_name: str = "GenericAgent",
        **kwargs
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Mock Gemini model execution with realistic token tracking
        """
        try:
            # Simulate processing time
            await asyncio.sleep(0.5)
            
            # Generate mock response
            response_text = self._mock_response_for_agent(agent_name, prompt)
            
            # Simulate realistic token counts
            input_tokens = len(prompt.split()) * 1.3  # Approximate tokenization
            output_tokens = len(response_text.split()) * 1.3
            total_tokens = int(input_tokens + output_tokens)
            input_tokens = int(input_tokens)
            output_tokens = int(output_tokens)
            
            # Calculate cost
            cost_usd = self._calculate_cost(model, input_tokens, output_tokens)
            
            # Prepare response
            response_dict = {
                "text": response_text,
                "model": model,
                "finish_reason": "stop",
                "mock_mode": True
            }
            
            token_usage = {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
                "cost_usd": cost_usd
            }
            
            logger.info(f"Mock Gemini {model} - Input: {input_tokens}, Output: {output_tokens}, Cost: ${cost_usd}")
            
            return response_dict, token_usage
            
        except Exception as e:
            logger.error(f"Error in mock Gemini {model}: {e}")
            # Return error response with zero token usage
            error_response = {
                "text": f"Error: {str(e)}",
                "model": model,
                "finish_reason": "error",
                "error": str(e)
            }
            zero_usage = {
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "cost_usd": 0.0
            }
            return error_response, zero_usage

# Global service instance
vertex_service = VertexAIService()

# Legacy function for backward compatibility
async def run_gemini(model: str, prompt: str, **kwargs):
    """Legacy function wrapper"""
    return await vertex_service.run_gemini(model, prompt, **kwargs)