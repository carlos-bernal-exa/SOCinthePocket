"""
ControllerAgent - Orchestrates execution modes and autonomy
"""
import asyncio
from typing import Dict, Any, List, Optional
from .base import AgentBase
import logging

logger = logging.getLogger(__name__)

class ControllerAgent(AgentBase):
    """
    Controller Agent that orchestrates modes (ReAct, Planner, Deep), 
    Gemini model choice, and autonomy enforcement.
    """
    
    def __init__(self):
        super().__init__(
            name="ControllerAgent", 
            model="gemini-2.5-pro",
            role="orchestration"
        )
    
    def _format_prompt(self, prompt_content: str, inputs: Dict[str, Any]) -> str:
        """Format controller-specific prompt"""
        task_spec = inputs.get("task_spec", {})
        autonomy_level = inputs.get("autonomy_level", "supervised")
        sla = inputs.get("sla", {})
        
        formatted = f"""You are the SOC Controller Agent responsible for orchestrating investigation workflows.

Your role is to:
1. Analyze the task specification and determine the optimal execution mode
2. Select appropriate Gemini models for each phase
3. Enforce autonomy levels and user approval gates
4. Create execution plans with proper sequencing

Task Specification:
{task_spec}

Autonomy Level: {autonomy_level}
SLA Requirements: {sla}

Available Execution Modes:
- ReAct: Real-time reactive investigation 
- Planner: Strategic multi-step planning
- Deep: Comprehensive analysis with correlation

Available Models:
- gemini-2.5-pro: Complex reasoning, correlation, reporting
- gemini-2.5-flash: Standard triage and enrichment
- gemini-2.5-flash-lite: Quick entity extraction

Autonomy Levels:
- autonomous: Full automation, no approval needed
- supervised: Require approval for critical actions
- manual: User controls each step

Based on the task, determine:
1. Execution mode (ReAct/Planner/Deep)
2. Model assignments per agent
3. Approval gates needed
4. Execution sequence

Respond with a structured execution plan."""

        return formatted
    
    async def _determine_execution_mode(self, task_spec: Dict[str, Any]) -> str:
        """Determine optimal execution mode based on task specification"""
        case_severity = task_spec.get("severity", "medium")
        complexity = task_spec.get("complexity", "standard")
        time_sensitivity = task_spec.get("time_sensitivity", "normal")
        
        # Logic for mode selection
        if time_sensitivity == "urgent" and case_severity in ["high", "critical"]:
            return "ReAct"
        elif complexity == "complex" or case_severity == "critical":
            return "Deep"
        else:
            return "Planner"
    
    async def _select_models(self, execution_mode: str, agents_needed: List[str]) -> Dict[str, str]:
        """Select appropriate Gemini models for each agent based on execution mode"""
        model_assignments = {}
        
        # Default model assignments
        model_map = {
            "TriageAgent": "gemini-2.5-flash",
            "EnrichmentAgent": "gemini-2.5-flash", 
            "InvestigationAgent": "gemini-2.5-pro",
            "CorrelationAgent": "gemini-2.5-pro",
            "ResponseAgent": "gemini-2.5-pro",
            "ReportingAgent": "gemini-2.5-pro",
            "KnowledgeAgent": "gemini-2.5-flash-lite"
        }
        
        # Adjust based on execution mode
        if execution_mode == "Deep":
            # Use Pro models for more thorough analysis
            for agent in ["TriageAgent", "EnrichmentAgent"]:
                if agent in agents_needed:
                    model_assignments[agent] = "gemini-2.5-pro"
        elif execution_mode == "ReAct":
            # Use faster Flash models for quick response
            for agent in ["InvestigationAgent", "CorrelationAgent"]:
                if agent in agents_needed:
                    model_assignments[agent] = "gemini-2.5-flash"
        
        # Apply defaults for unassigned agents
        for agent in agents_needed:
            if agent not in model_assignments:
                model_assignments[agent] = model_map.get(agent, "gemini-2.5-flash")
        
        return model_assignments
    
    async def _create_execution_plan(
        self, 
        mode: str, 
        model_assignments: Dict[str, str],
        autonomy_level: str,
        task_spec: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create detailed execution plan"""
        
        # Standard agent sequence
        agent_sequence = [
            "TriageAgent",
            "EnrichmentAgent", 
            "InvestigationAgent",
            "CorrelationAgent",
            "ResponseAgent",
            "ReportingAgent"
        ]
        
        # Adjust sequence based on mode
        if mode == "ReAct":
            # Skip correlation for faster response
            agent_sequence = ["TriageAgent", "EnrichmentAgent", "InvestigationAgent", "ResponseAgent"]
        elif mode == "Deep":
            # Add knowledge agent for comprehensive analysis
            agent_sequence.append("KnowledgeAgent")
        
        # Create execution steps
        execution_steps = []
        for i, agent in enumerate(agent_sequence):
            step = {
                "step_number": i + 1,
                "agent": agent,
                "model": model_assignments.get(agent, "gemini-2.5-flash"),
                "dependencies": agent_sequence[:i] if i > 0 else [],
                "approval_required": autonomy_level == "manual" or (
                    autonomy_level == "supervised" and agent in ["ResponseAgent", "InvestigationAgent"]
                )
            }
            execution_steps.append(step)
        
        return {
            "mode": mode,
            "autonomy_level": autonomy_level,
            "execution_steps": execution_steps,
            "model_assignments": model_assignments,
            "estimated_tokens": self._estimate_token_usage(execution_steps),
            "estimated_cost_usd": self._estimate_cost(execution_steps)
        }
    
    def _estimate_token_usage(self, execution_steps: List[Dict[str, Any]]) -> Dict[str, int]:
        """Estimate token usage for execution plan"""
        # Rough estimates based on agent complexity
        base_estimates = {
            "TriageAgent": 800,
            "EnrichmentAgent": 1200,
            "InvestigationAgent": 2000,
            "CorrelationAgent": 1500,
            "ResponseAgent": 1000,
            "ReportingAgent": 1800,
            "KnowledgeAgent": 600
        }
        
        total_input = 0
        total_output = 0
        
        for step in execution_steps:
            agent = step["agent"]
            base = base_estimates.get(agent, 1000)
            total_input += int(base * 0.4)  # 40% input
            total_output += int(base * 0.6)  # 60% output
        
        return {
            "input_tokens": total_input,
            "output_tokens": total_output,
            "total_tokens": total_input + total_output
        }
    
    def _estimate_cost(self, execution_steps: List[Dict[str, Any]]) -> float:
        """Estimate cost in USD for execution plan"""
        # Pricing per 1M tokens
        pricing = {
            "gemini-2.5-pro": 3.50,
            "gemini-2.5-flash": 0.35,
            "gemini-2.5-flash-lite": 0.05
        }
        
        total_cost = 0.0
        for step in execution_steps:
            model = step["model"]
            rate = pricing.get(model, 0.35) / 1_000_000  # Per token rate
            
            # Rough estimate: 1000 tokens per step
            estimated_tokens = 1000
            total_cost += estimated_tokens * rate
        
        return round(total_cost, 6)
    
    async def process(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Process controller orchestration logic"""
        try:
            # Extract inputs
            task_spec = inputs.get("task_spec", {})
            autonomy_level = inputs.get("autonomy_level", "supervised")
            sla = inputs.get("sla", {})
            
            # Determine execution mode
            execution_mode = await self._determine_execution_mode(task_spec)
            
            # Determine agents needed
            agents_needed = task_spec.get("agents", [
                "TriageAgent", "EnrichmentAgent", "InvestigationAgent", 
                "CorrelationAgent", "ResponseAgent", "ReportingAgent"
            ])
            
            # Select models
            model_assignments = await self._select_models(execution_mode, agents_needed)
            
            # Create execution plan
            execution_plan = await self._create_execution_plan(
                execution_mode, model_assignments, autonomy_level, task_spec
            )
            
            return {
                "execution_plan": execution_plan,
                "mode": execution_mode,
                "model_assignments": model_assignments,
                "autonomy_level": autonomy_level,
                "agents_sequence": [step["agent"] for step in execution_plan["execution_steps"]],
                "estimated_duration_minutes": len(execution_plan["execution_steps"]) * 2,
                "approval_gates": [
                    step for step in execution_plan["execution_steps"] 
                    if step.get("approval_required", False)
                ]
            }
            
        except Exception as e:
            logger.error(f"Controller processing failed: {e}")
            return {
                "error": f"Controller processing failed: {str(e)}",
                "execution_plan": None,
                "mode": "fallback"
            }