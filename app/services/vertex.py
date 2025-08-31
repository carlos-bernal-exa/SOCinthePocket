"""
Google Generative AI wrapper with token tracking and cost calculation
Real implementation with google-generativeai library
"""
import os
import json
import asyncio
from typing import Dict, Any, Tuple, Optional
import logging

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

logger = logging.getLogger(__name__)

# Model pricing per million tokens (USD) - Based on Google AI pricing
MODEL_PRICING = {
    "gemini-2.5-pro": {"input": 3.50, "output": 14.00},  # $3.50 input / $14.00 output per 1M tokens
    "gemini-2.5-flash": {"input": 0.35, "output": 1.40},  # $0.35 input / $1.40 output per 1M tokens  
    "gemini-2.5-flash-lite": {"input": 0.10, "output": 0.40}  # $0.10 input / $0.40 output per 1M tokens
}

class VertexAIService:
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        self.initialized = False
        
        if GENAI_AVAILABLE and self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.initialized = True
                logger.info("Google Generative AI initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Google Generative AI: {e}")
                logger.info("Falling back to mock mode")
        elif not self.api_key:
            logger.warning("GOOGLE_API_KEY not found, using mock mode")
        else:
            logger.warning("google-generativeai package not available, using mock mode")
    
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
        Real Gemini model execution via Vertex AI
        """
        # Always try real API first if available - no mock fallback
        if not (self.initialized and GENAI_AVAILABLE):
            error_msg = "Google Generative AI not initialized or not available"
            logger.error(error_msg)
            error_response = {
                "text": f"Configuration Error: {error_msg}",
                "model": model,
                "finish_reason": "error",
                "real_mode": False,
                "error": error_msg
            }
            zero_usage = {
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "cost_usd": 0.0
            }
            return error_response, zero_usage
        
        try:
            return await self._run_real_gemini(model, prompt, system_instruction, temperature, max_output_tokens)
                
        except Exception as e:
            logger.error(f"Error in Gemini {model}: {e}")
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
    
    async def _run_real_gemini(
        self, 
        model: str, 
        prompt: str, 
        system_instruction: Optional[str] = None,
        temperature: float = 0.1,
        max_output_tokens: int = 8192
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Execute real Gemini API call using google-generativeai"""
        try:
            # Map model names to actual Gemini 2.5 model names
            model_mapping = {
                "gemini-2.5-pro": "gemini-2.5-pro",  # Gemini 2.5 Pro
                "gemini-2.5-flash": "gemini-2.5-flash",  # Gemini 2.5 Flash
                "gemini-2.5-flash-lite": "gemini-2.5-flash-lite"  # Gemini 2.5 Flash-Lite
            }
            actual_model = model_mapping.get(model, "gemini-2.5-flash")
            
            # Initialize the model
            gemini_model = genai.GenerativeModel(actual_model)
            
            # Prepare the full prompt
            if system_instruction:
                full_prompt = f"System: {system_instruction}\n\nUser: {prompt}"
            else:
                full_prompt = prompt
            
            # Configure generation parameters
            generation_config = genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_output_tokens,
            )
            
            # Make the API call without timeout to ensure real responses
            response = await asyncio.to_thread(
                gemini_model.generate_content,
                full_prompt,
                generation_config=generation_config
            )
            
            # Extract response text
            response_text = response.text if response.text else str(response)
            
            # Extract token usage if available
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                usage = response.usage_metadata
                input_tokens = usage.prompt_token_count if hasattr(usage, 'prompt_token_count') else 0
                output_tokens = usage.candidates_token_count if hasattr(usage, 'candidates_token_count') else 0
                total_tokens = usage.total_token_count if hasattr(usage, 'total_token_count') else input_tokens + output_tokens
            else:
                # Fallback estimation
                input_tokens = int(len(full_prompt.split()) * 1.3)
                output_tokens = int(len(response_text.split()) * 1.3)
                total_tokens = input_tokens + output_tokens
            
            # Calculate cost using original model for pricing
            cost_usd = self._calculate_cost(model, input_tokens, output_tokens)
            
            # Prepare response
            response_dict = {
                "text": response_text,
                "model": model,
                "finish_reason": "stop",
                "real_mode": True,
                "actual_model": actual_model
            }
            
            token_usage = {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": total_tokens,
                "cost_usd": cost_usd
            }
            
            logger.info(f"Real Gemini {actual_model} ({model}) - Input: {input_tokens}, Output: {output_tokens}, Cost: ${cost_usd}")
            
            return response_dict, token_usage
            
        except Exception as e:
            logger.error(f"Real Gemini API error: {e}")
            # Return error response instead of falling back to mock
            error_response = {
                "text": f"API Error: {str(e)}",
                "model": model,
                "finish_reason": "error",
                "real_mode": False,
                "error": str(e)
            }
            zero_usage = {
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "cost_usd": 0.0
            }
            return error_response, zero_usage
    
    async def _run_mock_gemini(self, model: str, prompt: str, agent_name: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Fallback mock implementation"""
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

# Global service instance
vertex_service = VertexAIService()

# Legacy function for backward compatibility
async def run_gemini(model: str, prompt: str, **kwargs):
    """Legacy function wrapper"""
    return await vertex_service.run_gemini(model, prompt, **kwargs)