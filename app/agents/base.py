"""
Enhanced AgentBase with full audit integration and Vertex AI support
"""
import asyncio
import logging
import uuid
import hashlib
import json
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
    
    def _generate_step_hash(self, agent_step: Dict[str, Any]) -> str:
        """Generate hash for AgentStep"""
        # Create a copy without hash fields for hashing
        hashable_step = agent_step.copy()
        hashable_step.pop("hash", None)
        hashable_step.pop("prev_hash", None) 
        hashable_step.pop("signature", None)
        hashable_step.pop("_metadata", None)
        
        # Create canonical JSON
        canonical_json = json.dumps(hashable_step, sort_keys=True, separators=(',', ':'))
        
        # Generate SHA-256 hash
        return hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()
    
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
        Execute agent with full audit integration following AgentStep data contract
        
        Args:
            case_id: Case ID for audit tracking
            inputs: Input data for processing
            autonomy_level: Autonomy level for this execution
            
        Returns:
            Dictionary containing outputs and metadata following AgentStep contract
        """
        start_time = datetime.now(timezone.utc)
        step_id = f"stp_{uuid.uuid4().hex[:8]}"
        
        plan = [
            f"Initialize {self.name}",
            "Retrieve versioned prompt", 
            "Format prompt with inputs",
            "Execute Gemini model",
            "Process and structure outputs",
            "Generate AgentStep record"
        ]
        observations = []
        
        try:
            # Get prompt
            observations.append({"step": "prompt_retrieval", "status": "started"})
            prompt_content = await self.get_prompt()
            
            # Get actual prompt version from prompt manager
            try:
                from app.services.prompts import prompt_manager
                prompt_info = await prompt_manager.get_info(self.name)
                prompt_version = prompt_info.get("version", f"{self.name}_v1.0")
            except:
                prompt_version = f"{self.name}_v1.0"
            
            observations.append({"step": "prompt_retrieval", "status": "completed", "version": prompt_version})
            
            # Prepare prompt with inputs
            observations.append({"step": "input_formatting", "status": "started"})
            if asyncio.iscoroutinefunction(self._format_prompt):
                formatted_prompt = await self._format_prompt(prompt_content, inputs)
            else:
                formatted_prompt = self._format_prompt(prompt_content, inputs)
            observations.append({"step": "input_formatting", "status": "completed"})
            
            # Execute model
            observations.append({"step": "model_execution", "status": "started", "model": self.model})
            response, token_usage = await self.run_model(formatted_prompt)
            observations.append({"step": "model_execution", "status": "completed", "tokens": token_usage.get("total_tokens", 0)})
            
            # Process outputs
            observations.append({"step": "output_processing", "status": "started"})
            if hasattr(self, '_process_outputs') and callable(getattr(self, '_process_outputs')):
                if asyncio.iscoroutinefunction(self._process_outputs):
                    outputs = await self._process_outputs(response, inputs)
                else:
                    outputs = self._process_outputs(response, inputs)
            else:
                outputs = self._default_process_outputs(response, inputs)
            observations.append({"step": "output_processing", "status": "completed"})
            
            # Calculate execution time
            end_time = datetime.now(timezone.utc)
            execution_time = (end_time - start_time).total_seconds()
            
            # Create AgentStep data contract
            agent_step = {
                "version": "1.0",
                "case_id": case_id,
                "step_id": step_id,
                "timestamp": end_time.isoformat(),
                "agent": {
                    "name": self.name,
                    "role": self.role,
                    "model": self.model
                },
                "prompt_version": prompt_version,
                "autonomy_level": autonomy_level,
                "inputs": inputs,
                "plan": plan,
                "observations": observations,
                "outputs": outputs,
                "token_usage": {
                    "input_tokens": token_usage.get("input_tokens", 0),
                    "output_tokens": token_usage.get("output_tokens", 0),
                    "total_tokens": token_usage.get("total_tokens", 0),
                    "cost_usd": token_usage.get("cost_usd", 0.0)
                },
                "prev_hash": None,  # Will be set by audit system
                "hash": None,       # Will be set by audit system
                "signature": None   # Will be set by audit system
            }
            
            # Generate hash for this step
            step_hash = self._generate_step_hash(agent_step)
            agent_step["hash"] = step_hash
            
            # Add legacy metadata for backwards compatibility
            agent_step["_metadata"] = {
                "agent": self.name,
                "model": self.model,
                "execution_time_seconds": execution_time,
                "timestamp": end_time.isoformat(),
                "success": True
            }
            
            # Emit audit log with AgentStep
            await audit_logger.append(agent_step)
            
            return agent_step
            
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
            
            # Create error AgentStep
            error_step = {
                "version": "1.0",
                "case_id": case_id,
                "step_id": step_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "agent": {
                    "name": self.name,
                    "role": self.role,
                    "model": self.model
                },
                "prompt_version": prompt_version,
                "autonomy_level": autonomy_level,
                "inputs": inputs,
                "plan": plan,
                "observations": observations,
                "outputs": error_outputs,
                "token_usage": {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                    "cost_usd": 0.0
                },
                "prev_hash": None,
                "hash": None,
                "signature": None
            }
            
            # Generate hash for error step
            error_hash = self._generate_step_hash(error_step)
            error_step["hash"] = error_hash
            
            # Still emit audit log for the failure
            await audit_logger.append(error_step)
            
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
    
    def _default_process_outputs(self, response: Dict[str, Any], inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Default process model outputs into structured format
        Override _process_outputs in subclasses for specific processing
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