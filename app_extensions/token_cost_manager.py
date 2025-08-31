"""
Token Usage Controls and Cost Management for Predictable LLM Spend.

This module provides comprehensive controls over LLM usage and costs:
- Real-time token tracking and budget enforcement
- Cost estimation and spend monitoring
- Usage quotas per user/team/time period
- Cost alerts and budget notifications
- Detailed usage analytics and reporting
- Emergency circuit breakers for runaway costs
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
import redis.asyncio as redis
from decimal import Decimal, ROUND_HALF_UP

logger = logging.getLogger(__name__)


class CostAlertLevel(Enum):
    """Cost alert severity levels."""
    INFO = "info"
    WARNING = "warning" 
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class BudgetPeriod(Enum):
    """Budget time periods."""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly" 
    MONTHLY = "monthly"


@dataclass
class ModelPricing:
    """LLM model pricing configuration."""
    model_name: str
    input_cost_per_1k_tokens: Decimal
    output_cost_per_1k_tokens: Decimal
    context_window: int = 4096
    max_output_tokens: int = 1000


@dataclass
class UsageBudget:
    """Usage budget configuration."""
    budget_id: str
    name: str
    period: BudgetPeriod
    token_limit: int
    cost_limit_usd: Decimal
    users: List[str]  # User IDs covered by this budget
    models: List[str]  # Model names covered by this budget
    alert_thresholds: Dict[str, float] = field(default_factory=lambda: {
        "warning": 0.75, "critical": 0.90, "emergency": 1.0
    })
    enabled: bool = True


@dataclass
class UsageRecord:
    """Individual usage record for tracking."""
    record_id: str
    user_id: str
    model_name: str
    timestamp: datetime
    input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost_usd: Decimal
    actual_cost_usd: Optional[Decimal] = None
    request_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UsageStats:
    """Aggregated usage statistics."""
    period: str
    total_tokens: int
    total_cost_usd: Decimal
    request_count: int
    unique_users: int
    model_breakdown: Dict[str, Dict[str, Any]]
    user_breakdown: Dict[str, Dict[str, Any]]
    period_start: datetime
    period_end: datetime


@dataclass
class CostAlert:
    """Cost alert notification."""
    alert_id: str
    budget_id: str
    level: CostAlertLevel
    message: str
    current_usage: Dict[str, Any]
    budget_limits: Dict[str, Any]
    timestamp: datetime
    acknowledged: bool = False


class TokenCostManager:
    """
    Comprehensive token usage and cost management system.
    """
    
    def __init__(
        self,
        redis_client,
        default_models: Optional[List[ModelPricing]] = None,
        alert_callback: Optional[Callable[[CostAlert], None]] = None
    ):
        self.redis = redis_client
        self.alert_callback = alert_callback
        
        # Model pricing database
        self.model_pricing: Dict[str, ModelPricing] = {}
        if default_models:
            for model in default_models:
                self.model_pricing[model.model_name] = model
        else:
            self._load_default_pricing()
        
        # Budget configurations
        self.budgets: Dict[str, UsageBudget] = {}
        
        # Circuit breaker states
        self.circuit_breakers: Dict[str, bool] = {}  # budget_id -> is_tripped
        
        # Cache TTL settings
        self.cache_ttl = {
            'usage_stats': 300,  # 5 minutes
            'budget_status': 60,  # 1 minute
            'alerts': 3600       # 1 hour
        }
        
        # Statistics
        self.stats = {
            'total_requests': 0,
            'total_tokens': 0,
            'total_cost_usd': 0.0,
            'rejected_requests': 0,
            'budget_overruns': 0,
            'alerts_sent': 0
        }
    
    def _load_default_pricing(self):
        """Load default LLM model pricing."""
        default_models = [
            ModelPricing(
                model_name="gpt-4",
                input_cost_per_1k_tokens=Decimal("0.03"),
                output_cost_per_1k_tokens=Decimal("0.06"),
                context_window=8192,
                max_output_tokens=2000
            ),
            ModelPricing(
                model_name="gpt-3.5-turbo",
                input_cost_per_1k_tokens=Decimal("0.001"),
                output_cost_per_1k_tokens=Decimal("0.002"),
                context_window=4096,
                max_output_tokens=1000
            ),
            ModelPricing(
                model_name="claude-3-opus",
                input_cost_per_1k_tokens=Decimal("0.015"),
                output_cost_per_1k_tokens=Decimal("0.075"),
                context_window=200000,
                max_output_tokens=4000
            ),
            ModelPricing(
                model_name="claude-3-sonnet",
                input_cost_per_1k_tokens=Decimal("0.003"),
                output_cost_per_1k_tokens=Decimal("0.015"),
                context_window=200000,
                max_output_tokens=4000
            )
        ]
        
        for model in default_models:
            self.model_pricing[model.model_name] = model
    
    async def add_budget(self, budget: UsageBudget) -> bool:
        """Add a new usage budget."""
        try:
            self.budgets[budget.budget_id] = budget
            
            # Store in Redis for persistence
            budget_data = {
                'budget_id': budget.budget_id,
                'name': budget.name,
                'period': budget.period.value,
                'token_limit': budget.token_limit,
                'cost_limit_usd': str(budget.cost_limit_usd),
                'users': budget.users,
                'models': budget.models,
                'alert_thresholds': budget.alert_thresholds,
                'enabled': budget.enabled
            }
            
            await self.redis.hset(f"budget:{budget.budget_id}", mapping=budget_data)
            logger.info(f"Added budget: {budget.name} ({budget.budget_id})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add budget: {e}")
            return False
    
    async def estimate_cost(
        self, 
        model_name: str, 
        input_tokens: int, 
        output_tokens: int = 0
    ) -> Decimal:
        """Estimate cost for a given token usage."""
        if model_name not in self.model_pricing:
            logger.warning(f"Unknown model {model_name}, using default pricing")
            # Use average pricing as fallback
            input_cost = Decimal("0.01")
            output_cost = Decimal("0.02")
        else:
            pricing = self.model_pricing[model_name]
            input_cost = pricing.input_cost_per_1k_tokens
            output_cost = pricing.output_cost_per_1k_tokens
        
        cost = (
            (Decimal(input_tokens) / 1000) * input_cost +
            (Decimal(output_tokens) / 1000) * output_cost
        )
        
        return cost.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
    
    async def check_budget_approval(
        self,
        user_id: str,
        model_name: str,
        estimated_input_tokens: int,
        estimated_output_tokens: int = 0
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if request is approved within budget limits.
        
        Returns:
            Tuple of (approved, rejection_reason)
        """
        estimated_cost = await self.estimate_cost(
            model_name, estimated_input_tokens, estimated_output_tokens
        )
        
        total_tokens = estimated_input_tokens + estimated_output_tokens
        
        # Find applicable budgets for this user and model
        applicable_budgets = [
            budget for budget in self.budgets.values()
            if (user_id in budget.users or not budget.users) and
               (model_name in budget.models or not budget.models) and
               budget.enabled
        ]
        
        if not applicable_budgets:
            # No budget restrictions
            return True, None
        
        # Check each applicable budget
        for budget in applicable_budgets:
            # Check if circuit breaker is tripped
            if self.circuit_breakers.get(budget.budget_id, False):
                return False, f"Budget {budget.name} circuit breaker is active"
            
            # Get current usage for this budget period
            current_usage = await self._get_current_usage(budget)
            
            # Check token limit
            if current_usage['tokens'] + total_tokens > budget.token_limit:
                return False, f"Would exceed token limit for budget {budget.name}"
            
            # Check cost limit
            if current_usage['cost'] + estimated_cost > budget.cost_limit_usd:
                return False, f"Would exceed cost limit for budget {budget.name}"
        
        return True, None
    
    async def record_usage(
        self,
        user_id: str,
        model_name: str,
        input_tokens: int,
        output_tokens: int,
        actual_cost_usd: Optional[Decimal] = None,
        metadata: Dict[str, Any] = None
    ) -> UsageRecord:
        """Record actual usage and update budgets."""
        timestamp = datetime.now(timezone.utc)
        record_id = f"{user_id}_{model_name}_{int(timestamp.timestamp())}"
        
        total_tokens = input_tokens + output_tokens
        estimated_cost = await self.estimate_cost(model_name, input_tokens, output_tokens)
        
        usage_record = UsageRecord(
            record_id=record_id,
            user_id=user_id,
            model_name=model_name,
            timestamp=timestamp,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=estimated_cost,
            actual_cost_usd=actual_cost_usd,
            request_metadata=metadata or {}
        )
        
        try:
            # Store usage record in Redis
            usage_data = {
                'user_id': user_id,
                'model_name': model_name,
                'timestamp': timestamp.isoformat(),
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'total_tokens': total_tokens,
                'estimated_cost_usd': str(estimated_cost),
                'actual_cost_usd': str(actual_cost_usd) if actual_cost_usd else '',
                'metadata': json.dumps(metadata or {})
            }
            
            await self.redis.hset(f"usage:{record_id}", mapping=usage_data)
            await self.redis.expire(f"usage:{record_id}", 30 * 24 * 3600)  # 30 days TTL
            
            # Update period-based usage counters
            await self._update_usage_counters(usage_record)
            
            # Check for budget alerts
            await self._check_budget_alerts(user_id, model_name, usage_record)
            
            # Update statistics
            self.stats['total_requests'] += 1
            self.stats['total_tokens'] += total_tokens
            self.stats['total_cost_usd'] += float(actual_cost_usd or estimated_cost)
            
            logger.debug(f"Recorded usage: {user_id} used {total_tokens} tokens ({model_name})")
            return usage_record
            
        except Exception as e:
            logger.error(f"Failed to record usage: {e}")
            return usage_record
    
    async def _get_current_usage(self, budget: UsageBudget) -> Dict[str, Any]:
        """Get current usage for a budget period."""
        cache_key = f"budget_usage:{budget.budget_id}:{budget.period.value}"
        
        try:
            # Try cache first
            cached = await self.redis.get(cache_key)
            if cached:
                return json.loads(cached)
        except:
            pass
        
        # Calculate current usage for the period
        period_start = self._get_period_start(budget.period)
        
        usage = {
            'tokens': 0,
            'cost': Decimal('0.0'),
            'requests': 0
        }
        
        # Query usage records for this period
        try:
            # Get all usage records for the period (this could be optimized with time-based indices)
            pattern = "usage:*"
            usage_keys = await self.redis.keys(pattern)
            
            for key in usage_keys:
                record_data = await self.redis.hgetall(key)
                if not record_data:
                    continue
                
                # Check if record falls within period and budget scope
                record_time = datetime.fromisoformat(record_data['timestamp'])
                if record_time < period_start:
                    continue
                
                user_id = record_data['user_id']
                model_name = record_data['model_name']
                
                # Check if this record applies to the budget
                if budget.users and user_id not in budget.users:
                    continue
                if budget.models and model_name not in budget.models:
                    continue
                
                # Add to usage totals
                usage['tokens'] += int(record_data['total_tokens'])
                usage['requests'] += 1
                
                cost = record_data.get('actual_cost_usd') or record_data.get('estimated_cost_usd', '0')
                if cost:
                    usage['cost'] += Decimal(cost)
            
            # Cache the result
            cache_data = {
                'tokens': usage['tokens'],
                'cost': str(usage['cost']),
                'requests': usage['requests']
            }
            await self.redis.setex(cache_key, self.cache_ttl['budget_status'], json.dumps(cache_data))
            
        except Exception as e:
            logger.error(f"Failed to calculate current usage: {e}")
        
        return usage
    
    def _get_period_start(self, period: BudgetPeriod) -> datetime:
        """Get the start time for a budget period."""
        now = datetime.now(timezone.utc)
        
        if period == BudgetPeriod.HOURLY:
            return now.replace(minute=0, second=0, microsecond=0)
        elif period == BudgetPeriod.DAILY:
            return now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == BudgetPeriod.WEEKLY:
            days_since_monday = now.weekday()
            return (now - timedelta(days=days_since_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == BudgetPeriod.MONTHLY:
            return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        return now
    
    async def _update_usage_counters(self, usage_record: UsageRecord):
        """Update period-based usage counters for analytics."""
        timestamp = usage_record.timestamp
        
        # Update hourly, daily, monthly counters
        periods = ['hour', 'day', 'month']
        for period in periods:
            if period == 'hour':
                period_key = timestamp.strftime('%Y-%m-%d-%H')
            elif period == 'day':
                period_key = timestamp.strftime('%Y-%m-%d')
            else:  # month
                period_key = timestamp.strftime('%Y-%m')
            
            counter_key = f"usage_counter:{period}:{period_key}"
            
            pipe = self.redis.pipeline()
            pipe.hincrby(counter_key, 'total_tokens', usage_record.total_tokens)
            pipe.hincrby(counter_key, 'total_requests', 1)
            pipe.hincrbyfloat(counter_key, 'total_cost_usd', float(usage_record.estimated_cost_usd))
            
            # Set expiry based on period
            ttl = 24 * 3600 if period == 'hour' else (30 * 24 * 3600 if period == 'day' else 365 * 24 * 3600)
            pipe.expire(counter_key, ttl)
            
            await pipe.execute()
    
    async def _check_budget_alerts(self, user_id: str, model_name: str, usage_record: UsageRecord):
        """Check if budget alerts should be triggered."""
        applicable_budgets = [
            budget for budget in self.budgets.values()
            if (user_id in budget.users or not budget.users) and
               (model_name in budget.models or not budget.models) and
               budget.enabled
        ]
        
        for budget in applicable_budgets:
            current_usage = await self._get_current_usage(budget)
            
            # Calculate usage percentages
            token_usage_pct = current_usage['tokens'] / budget.token_limit
            cost_usage_pct = float(current_usage['cost']) / float(budget.cost_limit_usd)
            
            max_usage_pct = max(token_usage_pct, cost_usage_pct)
            
            # Check alert thresholds
            alert_level = None
            if max_usage_pct >= budget.alert_thresholds.get('emergency', 1.0):
                alert_level = CostAlertLevel.EMERGENCY
            elif max_usage_pct >= budget.alert_thresholds.get('critical', 0.9):
                alert_level = CostAlertLevel.CRITICAL
            elif max_usage_pct >= budget.alert_thresholds.get('warning', 0.75):
                alert_level = CostAlertLevel.WARNING
            
            if alert_level:
                await self._send_budget_alert(budget, alert_level, current_usage, max_usage_pct)
    
    async def _send_budget_alert(
        self,
        budget: UsageBudget,
        level: CostAlertLevel,
        current_usage: Dict[str, Any],
        usage_percentage: float
    ):
        """Send budget alert notification."""
        alert_id = f"{budget.budget_id}_{level.value}_{int(time.time())}"
        
        # Check if we've already sent this alert recently (avoid spam)
        recent_alert_key = f"recent_alert:{budget.budget_id}:{level.value}"
        if await self.redis.exists(recent_alert_key):
            return
        
        message = (
            f"Budget '{budget.name}' has reached {usage_percentage:.1%} of its limits. "
            f"Current usage: {current_usage['tokens']} tokens, "
            f"${current_usage['cost']} spent."
        )
        
        alert = CostAlert(
            alert_id=alert_id,
            budget_id=budget.budget_id,
            level=level,
            message=message,
            current_usage=current_usage,
            budget_limits={
                'token_limit': budget.token_limit,
                'cost_limit_usd': str(budget.cost_limit_usd)
            },
            timestamp=datetime.now(timezone.utc)
        )
        
        try:
            # Store alert
            alert_data = {
                'budget_id': budget.budget_id,
                'level': level.value,
                'message': message,
                'current_usage': json.dumps(current_usage, default=str),
                'budget_limits': json.dumps(alert.budget_limits),
                'timestamp': alert.timestamp.isoformat()
            }
            await self.redis.hset(f"alert:{alert_id}", mapping=alert_data)
            await self.redis.expire(f"alert:{alert_id}", self.cache_ttl['alerts'])
            
            # Set rate limiting for this alert type
            await self.redis.setex(recent_alert_key, 300, "1")  # 5 minutes
            
            # Trip circuit breaker for emergency alerts
            if level == CostAlertLevel.EMERGENCY:
                self.circuit_breakers[budget.budget_id] = True
                logger.critical(f"Circuit breaker activated for budget {budget.name}")
            
            # Call alert callback if configured
            if self.alert_callback:
                try:
                    self.alert_callback(alert)
                except Exception as e:
                    logger.error(f"Alert callback failed: {e}")
            
            self.stats['alerts_sent'] += 1
            logger.warning(f"Budget alert sent: {level.value} for {budget.name}")
            
        except Exception as e:
            logger.error(f"Failed to send budget alert: {e}")
    
    async def reset_circuit_breaker(self, budget_id: str) -> bool:
        """Reset circuit breaker for a budget."""
        if budget_id in self.circuit_breakers:
            self.circuit_breakers[budget_id] = False
            logger.info(f"Circuit breaker reset for budget {budget_id}")
            return True
        return False
    
    async def get_usage_analytics(
        self, 
        period: str = "day",
        limit: int = 30
    ) -> List[UsageStats]:
        """Get usage analytics for a specified period."""
        analytics = []
        
        try:
            # Get usage counter keys for the period
            pattern = f"usage_counter:{period}:*"
            counter_keys = await self.redis.keys(pattern)
            
            # Sort keys to get recent periods first
            counter_keys.sort(reverse=True)
            counter_keys = counter_keys[:limit]
            
            for key in counter_keys:
                counter_data = await self.redis.hgetall(key)
                if not counter_data:
                    continue
                
                period_str = key.split(":")[-1]
                
                stats = UsageStats(
                    period=period_str,
                    total_tokens=int(counter_data.get('total_tokens', 0)),
                    total_cost_usd=Decimal(counter_data.get('total_cost_usd', '0')),
                    request_count=int(counter_data.get('total_requests', 0)),
                    unique_users=0,  # Would need more complex tracking
                    model_breakdown={},  # Would need more detailed counters
                    user_breakdown={},   # Would need more detailed counters
                    period_start=datetime.now(timezone.utc),  # Simplified
                    period_end=datetime.now(timezone.utc)     # Simplified
                )
                
                analytics.append(stats)
            
        except Exception as e:
            logger.error(f"Failed to get usage analytics: {e}")
        
        return analytics
    
    async def get_cost_summary(self) -> Dict[str, Any]:
        """Get comprehensive cost summary."""
        try:
            # Get current hour/day/month totals
            now = datetime.now(timezone.utc)
            periods = {
                'current_hour': now.strftime('%Y-%m-%d-%H'),
                'current_day': now.strftime('%Y-%m-%d'),
                'current_month': now.strftime('%Y-%m')
            }
            
            summary = {}
            
            for period_name, period_key in periods.items():
                counter_key = f"usage_counter:{period_name.split('_')[1]}:{period_key}"
                counter_data = await self.redis.hgetall(counter_key)
                
                summary[period_name] = {
                    'tokens': int(counter_data.get('total_tokens', 0)),
                    'cost_usd': float(counter_data.get('total_cost_usd', 0)),
                    'requests': int(counter_data.get('total_requests', 0))
                }
            
            # Add budget status
            budget_status = {}
            for budget_id, budget in self.budgets.items():
                if not budget.enabled:
                    continue
                
                current_usage = await self._get_current_usage(budget)
                budget_status[budget_id] = {
                    'name': budget.name,
                    'period': budget.period.value,
                    'token_usage_pct': current_usage['tokens'] / budget.token_limit,
                    'cost_usage_pct': float(current_usage['cost']) / float(budget.cost_limit_usd),
                    'circuit_breaker_active': self.circuit_breakers.get(budget_id, False)
                }
            
            summary['budgets'] = budget_status
            summary['stats'] = self.stats
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to get cost summary: {e}")
            return {'error': str(e)}


# Integration functions
async def create_default_budgets(cost_manager: TokenCostManager) -> List[str]:
    """Create default budgets for a SOC environment."""
    default_budgets = [
        UsageBudget(
            budget_id="soc_hourly",
            name="SOC Hourly Operations",
            period=BudgetPeriod.HOURLY,
            token_limit=50000,
            cost_limit_usd=Decimal("25.00"),
            users=[],  # All users
            models=["gpt-3.5-turbo", "claude-3-sonnet"],
            alert_thresholds={"warning": 0.7, "critical": 0.85, "emergency": 0.95}
        ),
        UsageBudget(
            budget_id="soc_daily",
            name="SOC Daily Operations", 
            period=BudgetPeriod.DAILY,
            token_limit=500000,
            cost_limit_usd=Decimal("200.00"),
            users=[],
            models=[],  # All models
            alert_thresholds={"warning": 0.8, "critical": 0.9, "emergency": 1.0}
        ),
        UsageBudget(
            budget_id="investigation_premium",
            name="Premium Investigation Models",
            period=BudgetPeriod.DAILY, 
            token_limit=100000,
            cost_limit_usd=Decimal("100.00"),
            users=[],
            models=["gpt-4", "claude-3-opus"],
            alert_thresholds={"warning": 0.6, "critical": 0.8, "emergency": 0.9}
        )
    ]
    
    created_budgets = []
    for budget in default_budgets:
        if await cost_manager.add_budget(budget):
            created_budgets.append(budget.budget_id)
    
    return created_budgets


# Legacy wrapper for backward compatibility
async def check_token_budget(user_id: str, estimated_tokens: int, model_name: str = "gpt-3.5-turbo") -> bool:
    """
    Legacy function to check if token usage is within budget.
    
    Returns True if approved, False if over budget.
    """
    # This would need a global cost manager instance in practice
    # For now, just implement basic logic
    if estimated_tokens > 10000:  # Simple threshold
        logger.warning(f"Token request exceeds threshold: {estimated_tokens}")
        return False
    
    return True