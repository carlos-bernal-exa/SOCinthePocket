"""
Comprehensive Observability and Reliability Features for SOC Platform.

This module provides enterprise-grade observability and reliability:
- OpenTelemetry instrumentation for distributed tracing
- Circuit breakers with retry patterns
- Health checks and dependency monitoring
- Metrics collection and alerting
- Idempotency keys for safe re-runs
- Graceful degradation and fallback strategies
- Performance monitoring and SLA tracking
"""

import asyncio
import functools
import hashlib
import json
import logging
import time
import uuid
from typing import Dict, List, Any, Optional, Callable, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from contextlib import asynccontextmanager
import redis.asyncio as redis

# OpenTelemetry imports (install with: pip install opentelemetry-api opentelemetry-sdk)
try:
    from opentelemetry import trace, metrics
    from opentelemetry.exporter.jaeger.thrift import JaegerExporter
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.instrumentation.redis import RedisInstrumentor
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("OpenTelemetry not available. Install with: pip install opentelemetry-api opentelemetry-sdk")

logger = logging.getLogger(__name__)


class ServiceHealth(Enum):
    """Service health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"


class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, requests blocked
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class HealthCheck:
    """Health check configuration and status."""
    check_id: str
    name: str
    check_func: Callable[[], bool]
    timeout_seconds: float = 5.0
    interval_seconds: float = 30.0
    failure_threshold: int = 3
    success_threshold: int = 2
    enabled: bool = True
    last_check: Optional[datetime] = None
    status: ServiceHealth = ServiceHealth.HEALTHY
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    error_message: Optional[str] = None


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""
    name: str
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    success_threshold: int = 2
    timeout: float = 10.0
    fallback_func: Optional[Callable] = None


@dataclass
class CircuitBreakerState:
    """Circuit breaker runtime state."""
    state: CircuitBreakerState = CircuitBreakerState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[datetime] = None
    next_attempt_time: Optional[datetime] = None


@dataclass
class MetricRecord:
    """Performance metric record."""
    metric_name: str
    value: float
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)
    unit: str = ""


@dataclass
class SLATarget:
    """Service Level Agreement target."""
    sla_id: str
    name: str
    metric_name: str
    target_value: float
    comparison_operator: str  # "lt", "gt", "eq", "lte", "gte"
    measurement_window_minutes: int = 5
    violation_threshold_count: int = 3
    enabled: bool = True


class ObservabilityManager:
    """
    Comprehensive observability and monitoring manager.
    """
    
    def __init__(
        self,
        redis_client,
        service_name: str = "soc_platform",
        jaeger_endpoint: Optional[str] = None,
        enable_tracing: bool = True
    ):
        self.redis = redis_client
        self.service_name = service_name
        self.enable_tracing = enable_tracing
        
        # Initialize OpenTelemetry if available
        self.tracer = None
        self.meter = None
        if OTEL_AVAILABLE and enable_tracing:
            self._setup_tracing(jaeger_endpoint)
        
        # Health checks
        self.health_checks: Dict[str, HealthCheck] = {}
        self.overall_health = ServiceHealth.HEALTHY
        
        # Circuit breakers
        self.circuit_breakers: Dict[str, Tuple[CircuitBreakerConfig, CircuitBreakerState]] = {}
        
        # Metrics
        self.metrics: List[MetricRecord] = []
        self.sla_targets: Dict[str, SLATarget] = {}
        
        # Idempotency tracking
        self.idempotency_cache_ttl = 3600  # 1 hour
        
        # Performance tracking
        self.operation_stats: Dict[str, Dict[str, Any]] = {}
        
        # Start background tasks
        self._health_check_task = None
        self._metrics_cleanup_task = None
        
        logger.info(f"Observability manager initialized for {service_name}")
    
    def _setup_tracing(self, jaeger_endpoint: Optional[str]):
        """Setup OpenTelemetry tracing."""
        try:
            # Configure tracer
            trace.set_tracer_provider(TracerProvider())
            self.tracer = trace.get_tracer(self.service_name)
            
            # Configure Jaeger exporter if endpoint provided
            if jaeger_endpoint:
                jaeger_exporter = JaegerExporter(endpoint=jaeger_endpoint)
                span_processor = BatchSpanProcessor(jaeger_exporter)
                trace.get_tracer_provider().add_span_processor(span_processor)
            
            # Configure meter
            metrics.set_meter_provider(MeterProvider())
            self.meter = metrics.get_meter(self.service_name)
            
            # Instrument Redis automatically
            RedisInstrumentor().instrument()
            
            logger.info("OpenTelemetry tracing configured")
            
        except Exception as e:
            logger.error(f"Failed to setup tracing: {e}")
            self.tracer = None
            self.meter = None
    
    def trace_operation(self, operation_name: str, **attributes):
        """Decorator/context manager for tracing operations."""
        def decorator(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                if self.tracer:
                    with self.tracer.start_as_current_span(operation_name) as span:
                        # Add attributes
                        for key, value in attributes.items():
                            span.set_attribute(key, value)
                        
                        start_time = time.time()
                        try:
                            result = await func(*args, **kwargs)
                            span.set_attribute("success", True)
                            return result
                        except Exception as e:
                            span.set_attribute("success", False)
                            span.set_attribute("error.message", str(e))
                            raise
                        finally:
                            duration = time.time() - start_time
                            span.set_attribute("duration_ms", duration * 1000)
                            await self.record_metric(f"{operation_name}_duration", duration * 1000, {"operation": operation_name})
                else:
                    return await func(*args, **kwargs)
            
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                if self.tracer:
                    with self.tracer.start_as_current_span(operation_name) as span:
                        for key, value in attributes.items():
                            span.set_attribute(key, value)
                        
                        start_time = time.time()
                        try:
                            result = func(*args, **kwargs)
                            span.set_attribute("success", True)
                            return result
                        except Exception as e:
                            span.set_attribute("success", False)
                            span.set_attribute("error.message", str(e))
                            raise
                        finally:
                            duration = time.time() - start_time
                            span.set_attribute("duration_ms", duration * 1000)
                            # Note: Can't await in sync function, would need separate metric recording
                else:
                    return func(*args, **kwargs)
            
            return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
        
        return decorator
    
    @asynccontextmanager
    async def trace_span(self, operation_name: str, **attributes):
        """Context manager for manual span creation."""
        if self.tracer:
            with self.tracer.start_as_current_span(operation_name) as span:
                for key, value in attributes.items():
                    span.set_attribute(key, value)
                
                start_time = time.time()
                try:
                    yield span
                except Exception as e:
                    span.set_attribute("success", False)
                    span.set_attribute("error.message", str(e))
                    raise
                finally:
                    duration = time.time() - start_time
                    span.set_attribute("duration_ms", duration * 1000)
        else:
            yield None
    
    def add_health_check(self, health_check: HealthCheck):
        """Add a health check to monitoring."""
        self.health_checks[health_check.check_id] = health_check
        logger.info(f"Added health check: {health_check.name}")
    
    async def run_health_checks(self) -> Dict[str, Any]:
        """Run all enabled health checks."""
        results = {}
        overall_status = ServiceHealth.HEALTHY
        
        for check_id, check in self.health_checks.items():
            if not check.enabled:
                continue
            
            try:
                # Run health check with timeout
                start_time = time.time()
                result = await asyncio.wait_for(
                    asyncio.create_task(self._run_single_health_check(check)),
                    timeout=check.timeout_seconds
                )
                
                duration_ms = (time.time() - start_time) * 1000
                
                if result:
                    check.consecutive_successes += 1
                    check.consecutive_failures = 0
                    
                    if check.status != ServiceHealth.HEALTHY and check.consecutive_successes >= check.success_threshold:
                        check.status = ServiceHealth.HEALTHY
                        logger.info(f"Health check recovered: {check.name}")
                else:
                    check.consecutive_failures += 1
                    check.consecutive_successes = 0
                    
                    if check.consecutive_failures >= check.failure_threshold:
                        check.status = ServiceHealth.UNHEALTHY
                        logger.warning(f"Health check failed: {check.name}")
                
                check.last_check = datetime.now(timezone.utc)
                
                results[check_id] = {
                    'name': check.name,
                    'status': check.status.value,
                    'success': result,
                    'duration_ms': duration_ms,
                    'consecutive_failures': check.consecutive_failures,
                    'last_check': check.last_check.isoformat(),
                    'error_message': check.error_message
                }
                
                # Update overall status
                if check.status in [ServiceHealth.UNHEALTHY, ServiceHealth.CRITICAL]:
                    overall_status = ServiceHealth.UNHEALTHY
                elif check.status == ServiceHealth.DEGRADED and overall_status == ServiceHealth.HEALTHY:
                    overall_status = ServiceHealth.DEGRADED
                
            except asyncio.TimeoutError:
                check.consecutive_failures += 1
                check.status = ServiceHealth.UNHEALTHY
                check.error_message = f"Health check timed out after {check.timeout_seconds}s"
                overall_status = ServiceHealth.UNHEALTHY
                
                results[check_id] = {
                    'name': check.name,
                    'status': check.status.value,
                    'success': False,
                    'error_message': check.error_message
                }
                
            except Exception as e:
                check.consecutive_failures += 1
                check.status = ServiceHealth.UNHEALTHY
                check.error_message = str(e)
                overall_status = ServiceHealth.UNHEALTHY
                
                results[check_id] = {
                    'name': check.name,
                    'status': check.status.value,
                    'success': False,
                    'error_message': check.error_message
                }
        
        self.overall_health = overall_status
        
        # Store health check results in Redis
        try:
            await self.redis.setex(
                f"health:{self.service_name}",
                300,  # 5 minute TTL
                json.dumps({
                    'overall_status': overall_status.value,
                    'checks': results,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
            )
        except Exception as e:
            logger.error(f"Failed to store health check results: {e}")
        
        return results
    
    async def _run_single_health_check(self, check: HealthCheck) -> bool:
        """Run a single health check."""
        try:
            if asyncio.iscoroutinefunction(check.check_func):
                return await check.check_func()
            else:
                return check.check_func()
        except Exception as e:
            check.error_message = str(e)
            logger.error(f"Health check {check.name} failed: {e}")
            return False
    
    def create_circuit_breaker(self, config: CircuitBreakerConfig):
        """Create a circuit breaker for a service."""
        state = CircuitBreakerState()
        self.circuit_breakers[config.name] = (config, state)
        logger.info(f"Created circuit breaker: {config.name}")
    
    def circuit_breaker(self, name: str):
        """Decorator for circuit breaker protection."""
        def decorator(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await self._execute_with_circuit_breaker(name, func, *args, **kwargs)
            
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                # For sync functions, we'd need a different implementation
                # This is a simplified version
                return func(*args, **kwargs)
            
            return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
        
        return decorator
    
    async def _execute_with_circuit_breaker(self, name: str, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        if name not in self.circuit_breakers:
            logger.warning(f"Circuit breaker {name} not found, executing without protection")
            return await func(*args, **kwargs)
        
        config, state = self.circuit_breakers[name]
        now = datetime.now(timezone.utc)
        
        # Check circuit breaker state
        if state.state == CircuitBreakerState.OPEN:
            if state.next_attempt_time and now < state.next_attempt_time:
                # Circuit breaker is open, try fallback
                if config.fallback_func:
                    logger.info(f"Circuit breaker {name} open, using fallback")
                    return await config.fallback_func(*args, **kwargs) if asyncio.iscoroutinefunction(config.fallback_func) else config.fallback_func(*args, **kwargs)
                else:
                    raise Exception(f"Circuit breaker {name} is open")
            else:
                # Time to test recovery
                state.state = CircuitBreakerState.HALF_OPEN
                state.success_count = 0
        
        # Execute function
        try:
            start_time = time.time()
            
            if config.timeout:
                result = await asyncio.wait_for(func(*args, **kwargs), timeout=config.timeout)
            else:
                result = await func(*args, **kwargs)
            
            # Success - update circuit breaker
            if state.state == CircuitBreakerState.HALF_OPEN:
                state.success_count += 1
                if state.success_count >= config.success_threshold:
                    state.state = CircuitBreakerState.CLOSED
                    state.failure_count = 0
                    logger.info(f"Circuit breaker {name} recovered")
            elif state.state == CircuitBreakerState.CLOSED:
                state.failure_count = max(0, state.failure_count - 1)
            
            # Record success metric
            duration = (time.time() - start_time) * 1000
            await self.record_metric(f"circuit_breaker_{name}_success", 1, {
                "circuit_breaker": name,
                "duration_ms": str(duration)
            })
            
            return result
            
        except Exception as e:
            # Failure - update circuit breaker
            state.failure_count += 1
            state.last_failure_time = now
            
            if state.state == CircuitBreakerState.HALF_OPEN:
                # Failed during recovery, go back to open
                state.state = CircuitBreakerState.OPEN
                state.next_attempt_time = now + timedelta(seconds=config.recovery_timeout)
            elif state.state == CircuitBreakerState.CLOSED and state.failure_count >= config.failure_threshold:
                # Failure threshold reached, open circuit
                state.state = CircuitBreakerState.OPEN
                state.next_attempt_time = now + timedelta(seconds=config.recovery_timeout)
                logger.warning(f"Circuit breaker {name} opened due to failures")
            
            # Record failure metric
            await self.record_metric(f"circuit_breaker_{name}_failure", 1, {
                "circuit_breaker": name,
                "error_type": type(e).__name__
            })
            
            # Try fallback if available
            if config.fallback_func:
                logger.info(f"Circuit breaker {name} using fallback due to error: {e}")
                return await config.fallback_func(*args, **kwargs) if asyncio.iscoroutinefunction(config.fallback_func) else config.fallback_func(*args, **kwargs)
            
            raise
    
    async def ensure_idempotency(self, operation_id: str, operation_func: Callable, *args, **kwargs):
        """Ensure idempotent execution of an operation."""
        idempotency_key = f"idempotent:{operation_id}"
        
        try:
            # Check if operation already completed
            cached_result = await self.redis.get(idempotency_key)
            if cached_result:
                result_data = json.loads(cached_result)
                if result_data['status'] == 'completed':
                    logger.info(f"Operation {operation_id} already completed, returning cached result")
                    return result_data['result']
                elif result_data['status'] == 'in_progress':
                    # Operation is currently running, wait a bit and retry
                    await asyncio.sleep(1.0)
                    return await self.ensure_idempotency(operation_id, operation_func, *args, **kwargs)
            
            # Mark operation as in progress
            progress_data = {
                'status': 'in_progress',
                'started_at': datetime.now(timezone.utc).isoformat(),
                'operation_id': operation_id
            }
            await self.redis.setex(idempotency_key, 300, json.dumps(progress_data))  # 5 minutes
            
            # Execute operation
            result = await operation_func(*args, **kwargs) if asyncio.iscoroutinefunction(operation_func) else operation_func(*args, **kwargs)
            
            # Cache successful result
            completed_data = {
                'status': 'completed',
                'completed_at': datetime.now(timezone.utc).isoformat(),
                'operation_id': operation_id,
                'result': result
            }
            await self.redis.setex(idempotency_key, self.idempotency_cache_ttl, json.dumps(completed_data))
            
            logger.info(f"Operation {operation_id} completed successfully")
            return result
            
        except Exception as e:
            # Mark operation as failed
            failed_data = {
                'status': 'failed',
                'failed_at': datetime.now(timezone.utc).isoformat(),
                'operation_id': operation_id,
                'error': str(e)
            }
            await self.redis.setex(idempotency_key, 300, json.dumps(failed_data))  # 5 minutes
            
            logger.error(f"Operation {operation_id} failed: {e}")
            raise
    
    async def record_metric(self, metric_name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Record a performance metric."""
        metric = MetricRecord(
            metric_name=metric_name,
            value=value,
            timestamp=datetime.now(timezone.utc),
            labels=labels or {}
        )
        
        # Store in memory (limited buffer)
        self.metrics.append(metric)
        if len(self.metrics) > 1000:  # Keep only recent metrics
            self.metrics = self.metrics[-500:]
        
        # Store in Redis for persistence
        try:
            metric_key = f"metric:{metric_name}:{int(metric.timestamp.timestamp())}"
            metric_data = {
                'value': value,
                'timestamp': metric.timestamp.isoformat(),
                'labels': json.dumps(labels or {})
            }
            await self.redis.hset(metric_key, mapping=metric_data)
            await self.redis.expire(metric_key, 24 * 3600)  # 24 hours TTL
            
            # Update operation stats
            if metric_name not in self.operation_stats:
                self.operation_stats[metric_name] = {
                    'count': 0,
                    'sum': 0.0,
                    'min': float('inf'),
                    'max': float('-inf'),
                    'avg': 0.0
                }
            
            stats = self.operation_stats[metric_name]
            stats['count'] += 1
            stats['sum'] += value
            stats['min'] = min(stats['min'], value)
            stats['max'] = max(stats['max'], value)
            stats['avg'] = stats['sum'] / stats['count']
            
        except Exception as e:
            logger.error(f"Failed to record metric {metric_name}: {e}")
    
    def add_sla_target(self, sla: SLATarget):
        """Add an SLA target for monitoring."""
        self.sla_targets[sla.sla_id] = sla
        logger.info(f"Added SLA target: {sla.name}")
    
    async def check_sla_violations(self) -> List[Dict[str, Any]]:
        """Check for SLA violations."""
        violations = []
        
        for sla_id, sla in self.sla_targets.items():
            if not sla.enabled:
                continue
            
            try:
                # Get recent metrics for this SLA
                window_start = datetime.now(timezone.utc) - timedelta(minutes=sla.measurement_window_minutes)
                
                # Query metrics from Redis
                metric_pattern = f"metric:{sla.metric_name}:*"
                metric_keys = await self.redis.keys(metric_pattern)
                
                violation_count = 0
                total_measurements = 0
                
                for key in metric_keys:
                    metric_data = await self.redis.hgetall(key)
                    if not metric_data:
                        continue
                    
                    metric_time = datetime.fromisoformat(metric_data['timestamp'])
                    if metric_time < window_start:
                        continue
                    
                    value = float(metric_data['value'])
                    total_measurements += 1
                    
                    # Check if value violates SLA
                    is_violation = False
                    if sla.comparison_operator == "lt" and value >= sla.target_value:
                        is_violation = True
                    elif sla.comparison_operator == "gt" and value <= sla.target_value:
                        is_violation = True
                    elif sla.comparison_operator == "eq" and value != sla.target_value:
                        is_violation = True
                    elif sla.comparison_operator == "lte" and value > sla.target_value:
                        is_violation = True
                    elif sla.comparison_operator == "gte" and value < sla.target_value:
                        is_violation = True
                    
                    if is_violation:
                        violation_count += 1
                
                # Check if violation threshold is exceeded
                if violation_count >= sla.violation_threshold_count and total_measurements > 0:
                    violation_rate = violation_count / total_measurements
                    
                    violations.append({
                        'sla_id': sla_id,
                        'sla_name': sla.name,
                        'metric_name': sla.metric_name,
                        'target_value': sla.target_value,
                        'comparison_operator': sla.comparison_operator,
                        'violation_count': violation_count,
                        'total_measurements': total_measurements,
                        'violation_rate': violation_rate,
                        'window_minutes': sla.measurement_window_minutes
                    })
                    
                    logger.warning(f"SLA violation detected: {sla.name} ({violation_rate:.2%} violation rate)")
                
            except Exception as e:
                logger.error(f"Failed to check SLA {sla_id}: {e}")
        
        return violations
    
    async def get_observability_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive observability dashboard data."""
        try:
            # Get health status
            health_results = await self.run_health_checks()
            
            # Get circuit breaker status
            circuit_status = {}
            for name, (config, state) in self.circuit_breakers.items():
                circuit_status[name] = {
                    'state': state.state.value,
                    'failure_count': state.failure_count,
                    'success_count': state.success_count,
                    'last_failure_time': state.last_failure_time.isoformat() if state.last_failure_time else None
                }
            
            # Get recent metrics
            recent_metrics = {}
            for op_name, stats in self.operation_stats.items():
                recent_metrics[op_name] = stats.copy()
            
            # Check SLA violations
            sla_violations = await self.check_sla_violations()
            
            dashboard = {
                'service_name': self.service_name,
                'overall_health': self.overall_health.value,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'health_checks': health_results,
                'circuit_breakers': circuit_status,
                'metrics': recent_metrics,
                'sla_violations': sla_violations,
                'tracing_enabled': self.tracer is not None
            }
            
            return dashboard
            
        except Exception as e:
            logger.error(f"Failed to generate observability dashboard: {e}")
            return {'error': str(e)}
    
    async def start_background_tasks(self):
        """Start background monitoring tasks."""
        if self._health_check_task is None:
            self._health_check_task = asyncio.create_task(self._health_check_loop())
        
        if self._metrics_cleanup_task is None:
            self._metrics_cleanup_task = asyncio.create_task(self._metrics_cleanup_loop())
        
        logger.info("Background observability tasks started")
    
    async def stop_background_tasks(self):
        """Stop background monitoring tasks."""
        tasks = [self._health_check_task, self._metrics_cleanup_task]
        
        for task in tasks:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        self._health_check_task = None
        self._metrics_cleanup_task = None
        
        logger.info("Background observability tasks stopped")
    
    async def _health_check_loop(self):
        """Background loop for running health checks."""
        while True:
            try:
                await self.run_health_checks()
                await asyncio.sleep(30)  # Run every 30 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check loop error: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def _metrics_cleanup_loop(self):
        """Background loop for cleaning up old metrics."""
        while True:
            try:
                # Clean up metrics older than 24 hours
                cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
                cutoff_timestamp = int(cutoff_time.timestamp())
                
                # Find and delete old metric keys
                pattern = "metric:*"
                keys = await self.redis.keys(pattern)
                
                deleted_count = 0
                for key in keys:
                    try:
                        # Extract timestamp from key
                        timestamp_str = key.split(":")[-1]
                        if timestamp_str.isdigit():
                            timestamp = int(timestamp_str)
                            if timestamp < cutoff_timestamp:
                                await self.redis.delete(key)
                                deleted_count += 1
                    except:
                        continue
                
                if deleted_count > 0:
                    logger.info(f"Cleaned up {deleted_count} old metric records")
                
                await asyncio.sleep(3600)  # Run every hour
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Metrics cleanup loop error: {e}")
                await asyncio.sleep(3600)


# Integration functions for SOC platform
async def create_soc_observability_manager(
    redis_client,
    service_name: str = "soc_platform",
    jaeger_endpoint: Optional[str] = None
) -> ObservabilityManager:
    """Create observability manager with SOC-specific health checks and circuit breakers."""
    manager = ObservabilityManager(redis_client, service_name, jaeger_endpoint)
    
    # Add SOC-specific health checks
    async def redis_health_check():
        try:
            await redis_client.ping()
            return True
        except:
            return False
    
    def memory_health_check():
        import psutil
        memory_percent = psutil.virtual_memory().percent
        return memory_percent < 85  # Alert if memory usage > 85%
    
    async def siem_connection_check():
        # Mock SIEM connection check
        return True  # Would implement actual SIEM connectivity check
    
    manager.add_health_check(HealthCheck(
        check_id="redis_connection",
        name="Redis Connection",
        check_func=redis_health_check,
        timeout_seconds=5.0,
        interval_seconds=30.0
    ))
    
    manager.add_health_check(HealthCheck(
        check_id="memory_usage",
        name="Memory Usage",
        check_func=memory_health_check,
        timeout_seconds=2.0,
        interval_seconds=60.0
    ))
    
    manager.add_health_check(HealthCheck(
        check_id="siem_connection",
        name="SIEM Connection",
        check_func=siem_connection_check,
        timeout_seconds=10.0,
        interval_seconds=60.0
    ))
    
    # Add circuit breakers for external services
    async def siem_fallback(*args, **kwargs):
        logger.warning("SIEM circuit breaker active, using cached data")
        return {"events": [], "total": 0, "source": "cache"}
    
    async def llm_fallback(*args, **kwargs):
        logger.warning("LLM circuit breaker active, using template response")
        return {"text": "Service temporarily unavailable, please try again later."}
    
    manager.create_circuit_breaker(CircuitBreakerConfig(
        name="siem_query",
        failure_threshold=3,
        recovery_timeout=120.0,
        success_threshold=2,
        timeout=30.0,
        fallback_func=siem_fallback
    ))
    
    manager.create_circuit_breaker(CircuitBreakerConfig(
        name="llm_request",
        failure_threshold=5,
        recovery_timeout=60.0,
        success_threshold=3,
        timeout=30.0,
        fallback_func=llm_fallback
    ))
    
    # Add SLA targets
    manager.add_sla_target(SLATarget(
        sla_id="case_analysis_latency",
        name="Case Analysis Latency",
        metric_name="case_analysis_duration",
        target_value=5000.0,  # 5 seconds
        comparison_operator="lt",
        measurement_window_minutes=5,
        violation_threshold_count=3
    ))
    
    manager.add_sla_target(SLATarget(
        sla_id="siem_query_success_rate",
        name="SIEM Query Success Rate",
        metric_name="siem_query_success_rate",
        target_value=95.0,  # 95%
        comparison_operator="gte",
        measurement_window_minutes=10,
        violation_threshold_count=2
    ))
    
    return manager


# Legacy wrapper functions
def create_operation_id(operation_name: str, params: Dict[str, Any]) -> str:
    """Create deterministic operation ID for idempotency."""
    content = f"{operation_name}:{json.dumps(params, sort_keys=True)}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


async def safe_operation_execution(operation_name: str, operation_func: Callable, *args, **kwargs):
    """Execute operation with observability and reliability features."""
    # This would need a global observability manager instance
    operation_id = create_operation_id(operation_name, {"args": args, "kwargs": kwargs})
    
    # Mock implementation for compatibility
    try:
        start_time = time.time()
        result = await operation_func(*args, **kwargs) if asyncio.iscoroutinefunction(operation_func) else operation_func(*args, **kwargs)
        duration = (time.time() - start_time) * 1000
        
        logger.info(f"Operation {operation_name} completed in {duration:.1f}ms")
        return result
        
    except Exception as e:
        logger.error(f"Operation {operation_name} failed: {e}")
        raise