"""
Enhanced AgentBase with full audit integration and Vertex AI support
"""
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from app.services.vertex import vertex_service
from app.services.audit import audit_logger
from app.services.prompts import prompt_manager

logger = logging.getLogger(__name__)

class AgentBase:
    def __init__(self, name: str = None, model: str = "gemini-2.5-flash", role: str = "analysis"):
        """
        Initialize agent with audit integration
        
        Args:
            name: Agent name (defaults to class name)
            model: Gemini model to use
            role: Agent role for audit logging
        """
        self.name = name or self.__class__.__name__
        self.model = model
        self.role = role
        self.logger = logging.getLogger(f"agents.{self.name}")
    
    async def emit_audit(self, 
                        case_id: str,
                        inputs: Dict[str, Any],
                        outputs: Dict[str, Any],
                        plan: List[str] = None,
                        observations: List[str] = None,
                        prompt_version: str = None,
                        autonomy_level: str = "L1_SUGGEST",
                        token_usage: Dict[str, Any] = None):
        """
        Emit comprehensive audit log for agent step
        
        Args:
            case_id: Case ID this step belongs to
            inputs: Input data for the step
            outputs: Output data from the step
            plan: Planning steps taken
            observations: Observations made during execution
            prompt_version: Version of prompt used
            autonomy_level: Autonomy level (L1_SUGGEST, L2_APPROVE, L3_AUTO)
            token_usage: Token usage statistics
        """
        try:
            step_data = {
                "version": "1.0",
                "case_id": case_id,
                "agent": {
                    "name": self.name,
                    "role": self.role,
                    "model": self.model
                },
                "prompt_version": prompt_version or f"{self.name}_v1.0",
                "autonomy_level": autonomy_level,
                "inputs": inputs or {},
                "plan": plan or [],
                "observations": observations or [],
                "outputs": outputs or {},
                "token_usage": token_usage or {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                    "cost_usd": 0.0
                }
            }
            
            agent_step = await audit_logger.append(step_data)
            self.logger.info(f"Audit step {agent_step.step_id} emitted for case {case_id}")
            return agent_step
            
        except Exception as e:
            self.logger.error(f"Failed to emit audit: {e}")
            return None
    
    async def get_prompt(self, version: str = None) -> str:
        """Get the prompt for this agent"""
        try:
            return await prompt_manager.get(self.name, version)
        except Exception as e:
            self.logger.error(f"Failed to get prompt: {e}")
            return f"You are a {self.name} specialized in security operations."
    
    async def run_model(self, 
                       prompt: str,
                       system_instruction: str = None,
                       temperature: float = 0.1,
                       max_output_tokens: int = 8192) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Run the Gemini model with proper error handling
        
        Returns:
            Tuple of (response_dict, token_usage_dict)
        """
        try:
            return await vertex_service.run_gemini(
                model=self.model,
                prompt=prompt,
                system_instruction=system_instruction,
                temperature=temperature,
                max_output_tokens=max_output_tokens
            )
        except Exception as e:
            self.logger.error(f"Model execution failed: {e}")
            error_response = {
                "text": f"Model execution failed: {str(e)}",
                "model": self.model,
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
    
    async def execute(self, 
                     case_id: str,
                     inputs: Dict[str, Any],
                     autonomy_level: str = "L1_SUGGEST") -> Dict[str, Any]:
        """
        Execute agent with full audit integration
        
        Args:
            case_id: Case ID for audit tracking
            inputs: Input data for processing
            autonomy_level: Autonomy level for this execution
            
        Returns:
            Dictionary containing outputs and metadata
        """
        start_time = datetime.now(timezone.utc)
        plan = [f"Initialize {self.name}", "Get prompt", "Process inputs", "Generate outputs"]
        observations = []
        
        try:
            # Get prompt
            observations.append("Retrieved agent prompt")
            prompt_content = await self.get_prompt()
            prompt_version = f"{self.name}_v1.0"  # TODO: Get actual version
            
            # Prepare prompt with inputs
            observations.append("Prepared model inputs")
            formatted_prompt = self._format_prompt(prompt_content, inputs)
            
            # Execute model
            observations.append("Executing Gemini model")
            response, token_usage = await self.run_model(formatted_prompt)
            
            # Process outputs
            observations.append("Processing model outputs")
            outputs = self._process_outputs(response, inputs)
            
            # Calculate execution time
            end_time = datetime.now(timezone.utc)
            execution_time = (end_time - start_time).total_seconds()
            
            # Add metadata
            outputs["_metadata"] = {
                "agent": self.name,
                "model": self.model,
                "execution_time_seconds": execution_time,
                "timestamp": end_time.isoformat(),
                "success": True
            }
            
            observations.append(f"Execution completed in {execution_time:.2f}s")
            
            # Emit audit log
            await self.emit_audit(
                case_id=case_id,
                inputs=inputs,
                outputs=outputs,
                plan=plan,
                observations=observations,
                prompt_version=prompt_version,
                autonomy_level=autonomy_level,
                token_usage=token_usage
            )
            
            return outputs
            
        except Exception as e:
            error_msg = f"Agent execution failed: {str(e)}"
            self.logger.error(error_msg)
            observations.append(error_msg)
            
            # Return error response
            error_outputs = {
                "error": str(e),
                "success": False,
                "_metadata": {
                    "agent": self.name,
                    "model": self.model,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "success": False
                }
            }
            
            # Still emit audit log for the failure
            await self.emit_audit(
                case_id=case_id,
                inputs=inputs,
                outputs=error_outputs,
                plan=plan,
                observations=observations,
                autonomy_level=autonomy_level
            )
            
            return error_outputs
    
    def _format_prompt(self, prompt_content: str, inputs: Dict[str, Any]) -> str:
        """
        Format the prompt with input data
        Override in subclasses for specific formatting
        """
        formatted = f"{prompt_content}\n\n"
        formatted += "Input Data:\n"
        for key, value in inputs.items():
            formatted += f"{key}: {value}\n"
        formatted += "\nPlease provide a structured response:"
        return formatted
    
    def _process_outputs(self, response: Dict[str, Any], inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process model outputs into structured format
        Override in subclasses for specific processing
        """
        return {
            "response": response.get("text", ""),
            "model_info": {
                "model": response.get("model"),
                "finish_reason": response.get("finish_reason"),
                "safety_ratings": response.get("safety_ratings", [])
            },
            "raw_response": response
        }