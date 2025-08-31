"""
Prompt Versioning and Discipline Controls for SOC Agent Safety and Repeatability.

This module provides strict controls over prompt management to ensure:
- Versioned prompt templates with change tracking
- Safety constraints and content filtering
- Reproducible LLM interactions with deterministic prompts
- Token budget enforcement and cost controls
- Audit trails for prompt modifications
"""

import hashlib
import json
import logging
import time
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import re
import yaml

logger = logging.getLogger(__name__)


class PromptRiskLevel(Enum):
    """Risk levels for prompt templates."""
    LOW = "low"
    MEDIUM = "medium" 
    HIGH = "high"
    CRITICAL = "critical"


class PromptValidationResult(Enum):
    """Results of prompt validation."""
    VALID = "valid"
    BLOCKED_CONTENT = "blocked_content"
    BLOCKED_INJECTION = "blocked_injection"
    BLOCKED_TOKENS = "blocked_tokens"
    BLOCKED_RATE_LIMIT = "blocked_rate_limit"
    ERROR = "error"


@dataclass
class PromptTemplate:
    """Versioned prompt template with metadata."""
    template_id: str
    version: str
    content: str
    placeholders: List[str]
    risk_level: PromptRiskLevel
    max_tokens: int
    author: str
    created_at: datetime
    description: str = ""
    tags: List[str] = field(default_factory=list)
    approved_by: Optional[str] = None
    content_hash: str = field(init=False)
    
    def __post_init__(self):
        self.content_hash = hashlib.sha256(self.content.encode()).hexdigest()[:16]


@dataclass
class PromptExecution:
    """Record of prompt execution with audit trail."""
    execution_id: str
    template_id: str
    template_version: str
    rendered_prompt: str
    input_variables: Dict[str, Any]
    response_text: str
    tokens_used: int
    execution_time_ms: int
    timestamp: datetime
    user_id: str
    validation_result: PromptValidationResult
    blocked_reason: Optional[str] = None
    cost_usd: Optional[float] = None


@dataclass
class SafetyConstraints:
    """Safety constraints for prompt execution."""
    max_tokens_per_request: int = 4000
    max_requests_per_minute: int = 10
    blocked_keywords: List[str] = field(default_factory=lambda: [
        "jailbreak", "ignore instructions", "system override", "dev mode",
        "sudo", "root access", "bypass", "vulnerability", "exploit"
    ])
    blocked_patterns: List[str] = field(default_factory=lambda: [
        r"```\s*system\s*```",  # System prompt injection
        r"<\s*admin\s*>",       # Admin tags
        r"\bsudo\b.*\bsu\b",    # Command injection patterns
    ])
    required_disclaimers: List[str] = field(default_factory=lambda: [
        "This is an automated SOC analysis.",
        "Human review required for critical actions."
    ])
    token_budget_per_hour: int = 100000
    cost_budget_per_hour_usd: float = 50.0


class PromptDisciplineManager:
    """
    Manages prompt templates, versioning, and safety controls.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        self.templates: Dict[str, Dict[str, PromptTemplate]] = {}  # template_id -> version -> template
        self.executions: List[PromptExecution] = []
        self.safety_constraints = SafetyConstraints()
        
        # Rate limiting tracking
        self.request_timestamps: List[float] = []
        self.hourly_token_usage = 0
        self.hourly_cost_usage = 0.0
        self.hour_window_start = time.time()
        
        # Load configuration if provided
        if config_path:
            self.load_config(config_path)
        
        # Statistics
        self.stats = {
            'total_executions': 0,
            'blocked_requests': 0,
            'templates_created': 0,
            'safety_violations': 0,
            'token_budget_exceeded': 0,
            'cost_budget_exceeded': 0
        }
    
    def load_config(self, config_path: str):
        """Load prompt templates and constraints from configuration file."""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Load safety constraints
            if 'safety_constraints' in config:
                constraints_data = config['safety_constraints']
                self.safety_constraints = SafetyConstraints(**constraints_data)
            
            # Load prompt templates
            if 'templates' in config:
                for template_data in config['templates']:
                    template = PromptTemplate(
                        template_id=template_data['template_id'],
                        version=template_data['version'],
                        content=template_data['content'],
                        placeholders=template_data['placeholders'],
                        risk_level=PromptRiskLevel(template_data['risk_level']),
                        max_tokens=template_data['max_tokens'],
                        author=template_data['author'],
                        created_at=datetime.fromisoformat(template_data['created_at']),
                        description=template_data.get('description', ''),
                        tags=template_data.get('tags', []),
                        approved_by=template_data.get('approved_by')
                    )
                    self.register_template(template)
            
            logger.info(f"Loaded configuration from {config_path}")
            
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
    
    def register_template(self, template: PromptTemplate) -> bool:
        """
        Register a new prompt template version.
        
        Args:
            template: PromptTemplate to register
            
        Returns:
            True if registered successfully, False otherwise
        """
        try:
            # Validate template content
            validation_result = self._validate_template_content(template.content)
            if validation_result != PromptValidationResult.VALID:
                logger.error(f"Template validation failed: {validation_result}")
                return False
            
            # Initialize template_id dict if needed
            if template.template_id not in self.templates:
                self.templates[template.template_id] = {}
            
            # Check for duplicate version
            if template.version in self.templates[template.template_id]:
                logger.warning(f"Template {template.template_id} version {template.version} already exists")
                return False
            
            # Register template
            self.templates[template.template_id][template.version] = template
            self.stats['templates_created'] += 1
            
            logger.info(f"Registered template {template.template_id} v{template.version}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register template: {e}")
            return False
    
    def get_template(self, template_id: str, version: str = "latest") -> Optional[PromptTemplate]:
        """
        Retrieve a prompt template by ID and version.
        
        Args:
            template_id: Template identifier
            version: Version string or "latest" for most recent
            
        Returns:
            PromptTemplate if found, None otherwise
        """
        if template_id not in self.templates:
            return None
        
        versions = self.templates[template_id]
        if not versions:
            return None
        
        if version == "latest":
            # Get the latest version (highest version string)
            latest_version = max(versions.keys())
            return versions[latest_version]
        elif version in versions:
            return versions[version]
        
        return None
    
    def render_prompt(
        self, 
        template_id: str, 
        variables: Dict[str, Any], 
        version: str = "latest"
    ) -> Tuple[Optional[str], PromptValidationResult]:
        """
        Render a prompt template with variables and safety validation.
        
        Args:
            template_id: Template identifier
            variables: Variable substitutions
            version: Template version to use
            
        Returns:
            Tuple of (rendered_prompt, validation_result)
        """
        template = self.get_template(template_id, version)
        if not template:
            return None, PromptValidationResult.ERROR
        
        try:
            # Validate input variables
            variable_validation = self._validate_input_variables(variables)
            if variable_validation != PromptValidationResult.VALID:
                return None, variable_validation
            
            # Render template
            rendered = template.content
            for placeholder in template.placeholders:
                if placeholder in variables:
                    value = str(variables[placeholder])
                    rendered = rendered.replace(f"{{{placeholder}}}", value)
                else:
                    logger.warning(f"Missing placeholder value: {placeholder}")
            
            # Validate rendered prompt
            content_validation = self._validate_rendered_prompt(rendered)
            if content_validation != PromptValidationResult.VALID:
                return None, content_validation
            
            # Check token limits
            estimated_tokens = self._estimate_tokens(rendered)
            if estimated_tokens > template.max_tokens:
                return None, PromptValidationResult.BLOCKED_TOKENS
            
            # Check rate limits
            rate_validation = self._check_rate_limits(estimated_tokens)
            if rate_validation != PromptValidationResult.VALID:
                return None, rate_validation
            
            # Add safety disclaimers for high-risk templates
            if template.risk_level in [PromptRiskLevel.HIGH, PromptRiskLevel.CRITICAL]:
                rendered = self._add_safety_disclaimers(rendered)
            
            return rendered, PromptValidationResult.VALID
            
        except Exception as e:
            logger.error(f"Failed to render prompt: {e}")
            return None, PromptValidationResult.ERROR
    
    def execute_prompt(
        self,
        template_id: str,
        variables: Dict[str, Any],
        user_id: str,
        llm_client,
        version: str = "latest"
    ) -> Optional[PromptExecution]:
        """
        Execute a prompt with full audit trail and safety controls.
        
        Args:
            template_id: Template identifier
            variables: Variable substitutions
            user_id: User executing the prompt
            llm_client: LLM client for execution
            version: Template version to use
            
        Returns:
            PromptExecution record with results
        """
        start_time = time.time()
        execution_id = hashlib.sha256(f"{template_id}:{user_id}:{start_time}".encode()).hexdigest()[:16]
        
        # Render prompt with validation
        rendered_prompt, validation_result = self.render_prompt(template_id, variables, version)
        
        if validation_result != PromptValidationResult.VALID:
            self.stats['blocked_requests'] += 1
            if validation_result in [PromptValidationResult.BLOCKED_CONTENT, PromptValidationResult.BLOCKED_INJECTION]:
                self.stats['safety_violations'] += 1
            
            execution = PromptExecution(
                execution_id=execution_id,
                template_id=template_id,
                template_version=version,
                rendered_prompt=rendered_prompt or "",
                input_variables=variables,
                response_text="",
                tokens_used=0,
                execution_time_ms=int((time.time() - start_time) * 1000),
                timestamp=datetime.now(timezone.utc),
                user_id=user_id,
                validation_result=validation_result,
                blocked_reason=validation_result.value
            )
            
            self.executions.append(execution)
            logger.warning(f"Prompt execution blocked: {validation_result.value}")
            return execution
        
        # Execute prompt
        try:
            response = llm_client.generate(rendered_prompt)
            response_text = response.get('text', '')
            tokens_used = response.get('tokens', self._estimate_tokens(rendered_prompt + response_text))
            cost_usd = response.get('cost_usd', self._estimate_cost(tokens_used))
            
            # Update usage tracking
            self._update_usage_tracking(tokens_used, cost_usd)
            
            execution = PromptExecution(
                execution_id=execution_id,
                template_id=template_id,
                template_version=version,
                rendered_prompt=rendered_prompt,
                input_variables=variables,
                response_text=response_text,
                tokens_used=tokens_used,
                execution_time_ms=int((time.time() - start_time) * 1000),
                timestamp=datetime.now(timezone.utc),
                user_id=user_id,
                validation_result=PromptValidationResult.VALID,
                cost_usd=cost_usd
            )
            
            self.executions.append(execution)
            self.stats['total_executions'] += 1
            
            logger.info(f"Prompt executed successfully: {execution_id} ({tokens_used} tokens, ${cost_usd:.4f})")
            return execution
            
        except Exception as e:
            logger.error(f"Prompt execution failed: {e}")
            
            execution = PromptExecution(
                execution_id=execution_id,
                template_id=template_id,
                template_version=version,
                rendered_prompt=rendered_prompt,
                input_variables=variables,
                response_text="",
                tokens_used=0,
                execution_time_ms=int((time.time() - start_time) * 1000),
                timestamp=datetime.now(timezone.utc),
                user_id=user_id,
                validation_result=PromptValidationResult.ERROR,
                blocked_reason=str(e)
            )
            
            self.executions.append(execution)
            return execution
    
    def _validate_template_content(self, content: str) -> PromptValidationResult:
        """Validate template content for safety issues."""
        # Check for blocked keywords
        content_lower = content.lower()
        for keyword in self.safety_constraints.blocked_keywords:
            if keyword in content_lower:
                return PromptValidationResult.BLOCKED_CONTENT
        
        # Check for blocked patterns
        for pattern in self.safety_constraints.blocked_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return PromptValidationResult.BLOCKED_INJECTION
        
        return PromptValidationResult.VALID
    
    def _validate_input_variables(self, variables: Dict[str, Any]) -> PromptValidationResult:
        """Validate input variables for injection attempts."""
        for key, value in variables.items():
            value_str = str(value)
            
            # Check for blocked keywords in variables
            value_lower = value_str.lower()
            for keyword in self.safety_constraints.blocked_keywords:
                if keyword in value_lower:
                    return PromptValidationResult.BLOCKED_CONTENT
            
            # Check for blocked patterns in variables
            for pattern in self.safety_constraints.blocked_patterns:
                if re.search(pattern, value_str, re.IGNORECASE):
                    return PromptValidationResult.BLOCKED_INJECTION
        
        return PromptValidationResult.VALID
    
    def _validate_rendered_prompt(self, rendered: str) -> PromptValidationResult:
        """Final validation of rendered prompt."""
        return self._validate_template_content(rendered)
    
    def _check_rate_limits(self, estimated_tokens: int) -> PromptValidationResult:
        """Check rate limits and token budgets."""
        current_time = time.time()
        
        # Clean old request timestamps (keep last minute)
        self.request_timestamps = [
            ts for ts in self.request_timestamps 
            if current_time - ts < 60
        ]
        
        # Check requests per minute
        if len(self.request_timestamps) >= self.safety_constraints.max_requests_per_minute:
            return PromptValidationResult.BLOCKED_RATE_LIMIT
        
        # Reset hourly counters if needed
        if current_time - self.hour_window_start > 3600:
            self.hourly_token_usage = 0
            self.hourly_cost_usage = 0.0
            self.hour_window_start = current_time
        
        # Check token budget
        if (self.hourly_token_usage + estimated_tokens) > self.safety_constraints.token_budget_per_hour:
            self.stats['token_budget_exceeded'] += 1
            return PromptValidationResult.BLOCKED_TOKENS
        
        # Check cost budget
        estimated_cost = self._estimate_cost(estimated_tokens)
        if (self.hourly_cost_usage + estimated_cost) > self.safety_constraints.cost_budget_per_hour_usd:
            self.stats['cost_budget_exceeded'] += 1
            return PromptValidationResult.BLOCKED_RATE_LIMIT
        
        return PromptValidationResult.VALID
    
    def _update_usage_tracking(self, tokens_used: int, cost_usd: float):
        """Update usage tracking counters."""
        current_time = time.time()
        
        # Add request timestamp
        self.request_timestamps.append(current_time)
        
        # Update hourly usage
        self.hourly_token_usage += tokens_used
        self.hourly_cost_usage += cost_usd
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text (rough approximation)."""
        # Simple estimation: ~4 characters per token for English text
        return len(text) // 4
    
    def _estimate_cost(self, tokens: int) -> float:
        """Estimate cost in USD for token count."""
        # Rough estimation: $0.01 per 1000 tokens (adjust based on actual LLM pricing)
        return (tokens / 1000) * 0.01
    
    def _add_safety_disclaimers(self, prompt: str) -> str:
        """Add safety disclaimers to high-risk prompts."""
        disclaimers = "\n".join(self.safety_constraints.required_disclaimers)
        return f"{prompt}\n\nIMPORTANT: {disclaimers}"
    
    def get_usage_statistics(self) -> Dict[str, Any]:
        """Get comprehensive usage statistics."""
        recent_executions = [
            exec for exec in self.executions
            if (datetime.now(timezone.utc) - exec.timestamp).seconds < 3600
        ]
        
        return {
            'total_stats': self.stats,
            'template_counts': {
                'total_templates': len(self.templates),
                'total_versions': sum(len(versions) for versions in self.templates.values())
            },
            'recent_usage': {
                'executions_last_hour': len(recent_executions),
                'tokens_used_last_hour': sum(exec.tokens_used for exec in recent_executions),
                'cost_last_hour_usd': sum(exec.cost_usd or 0 for exec in recent_executions)
            },
            'safety_stats': {
                'blocked_rate': self.stats['blocked_requests'] / max(1, self.stats['total_executions'] + self.stats['blocked_requests']),
                'safety_violation_rate': self.stats['safety_violations'] / max(1, self.stats['total_executions'] + self.stats['blocked_requests'])
            },
            'current_limits': {
                'requests_this_minute': len(self.request_timestamps),
                'tokens_this_hour': self.hourly_token_usage,
                'cost_this_hour_usd': self.hourly_cost_usage
            }
        }
    
    def export_audit_trail(self, start_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Export audit trail of prompt executions."""
        executions = self.executions
        
        if start_date:
            executions = [
                exec for exec in executions
                if exec.timestamp >= start_date
            ]
        
        return [
            {
                'execution_id': exec.execution_id,
                'template_id': exec.template_id,
                'template_version': exec.template_version,
                'user_id': exec.user_id,
                'timestamp': exec.timestamp.isoformat(),
                'tokens_used': exec.tokens_used,
                'cost_usd': exec.cost_usd,
                'validation_result': exec.validation_result.value,
                'blocked_reason': exec.blocked_reason,
                'execution_time_ms': exec.execution_time_ms
            }
            for exec in executions
        ]


# Integration functions
def create_soc_prompt_manager(config_path: Optional[str] = None) -> PromptDisciplineManager:
    """Create a configured prompt manager for SOC operations."""
    manager = PromptDisciplineManager(config_path)
    
    # Register default SOC templates
    default_templates = [
        PromptTemplate(
            template_id="case_analysis",
            version="1.0.0",
            content="Analyze this security case:\n\nCase ID: {case_id}\nEntities: {entities}\nTimeline: {timeline}\n\nProvide a concise analysis with risk assessment and recommendations.",
            placeholders=["case_id", "entities", "timeline"],
            risk_level=PromptRiskLevel.MEDIUM,
            max_tokens=2000,
            author="soc_team",
            created_at=datetime.now(timezone.utc),
            description="Standard case analysis template",
            tags=["analysis", "case", "security"]
        ),
        PromptTemplate(
            template_id="entity_enrichment",
            version="1.0.0", 
            content="Enrich this security entity:\n\nEntity Type: {entity_type}\nEntity Value: {entity_value}\nContext: {context}\n\nProvide threat intelligence and risk indicators.",
            placeholders=["entity_type", "entity_value", "context"],
            risk_level=PromptRiskLevel.LOW,
            max_tokens=1500,
            author="soc_team",
            created_at=datetime.now(timezone.utc),
            description="Entity enrichment template",
            tags=["enrichment", "entity", "threat_intel"]
        )
    ]
    
    for template in default_templates:
        manager.register_template(template)
    
    return manager


# Legacy wrapper for backward compatibility
def safe_llm_prompt(template_id: str, variables: Dict[str, Any], user_id: str, llm_client) -> str:
    """
    Legacy function wrapper for safe LLM prompting.
    
    Returns response text or empty string if blocked.
    """
    manager = create_soc_prompt_manager()
    execution = manager.execute_prompt(template_id, variables, user_id, llm_client)
    
    if execution and execution.validation_result == PromptValidationResult.VALID:
        return execution.response_text
    
    return ""