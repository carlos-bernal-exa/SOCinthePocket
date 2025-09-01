"""
Autonomy Manager - Handles approval workflows and human-in-the-loop processes.

This module implements the actual approval mechanisms for different autonomy levels:
- Manual: Requires approval for each step
- Supervised: Requires approval for critical actions only  
- Autonomous: No approval needed
- Research: Deep analysis with optional checkpoints
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import redis.asyncio as redis

logger = logging.getLogger(__name__)


class ApprovalStatus(Enum):
    """Approval request status."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    TIMEOUT = "timeout"


@dataclass
class ApprovalRequest:
    """Approval request for agent execution."""
    request_id: str
    case_id: str
    agent_name: str
    agent_step: str
    proposed_action: Dict[str, Any]
    context: Dict[str, Any]
    autonomy_level: str
    created_at: datetime
    expires_at: datetime
    status: ApprovalStatus = ApprovalStatus.PENDING
    approved_by: Optional[str] = None
    rejection_reason: Optional[str] = None
    response_time_ms: Optional[int] = None


@dataclass
class AutonomyConfig:
    """Configuration for autonomy behaviors."""
    manual_timeout_minutes: int = 30
    supervised_timeout_minutes: int = 15
    auto_approve_low_risk: bool = True
    require_approval_agents: List[str] = field(default_factory=lambda: [
        "ResponseAgent", "InvestigationAgent"
    ])
    notification_channels: List[str] = field(default_factory=lambda: ["slack", "email"])


class AutonomyManager:
    """
    Manages approval workflows and human-in-the-loop processes for different autonomy levels.
    """
    
    def __init__(
        self, 
        redis_client,
        config: Optional[AutonomyConfig] = None,
        notification_callback: Optional[Callable] = None
    ):
        self.redis = redis_client
        self.config = config or AutonomyConfig()
        self.notification_callback = notification_callback
        
        # Active approval requests
        self.pending_approvals: Dict[str, ApprovalRequest] = {}
        
        # Statistics
        self.stats = {
            'total_requests': 0,
            'approved_requests': 0,
            'rejected_requests': 0,
            'timeout_requests': 0,
            'average_response_time_ms': 0.0
        }
    
    async def request_approval(
        self,
        case_id: str,
        agent_name: str,
        agent_step: str,
        proposed_action: Dict[str, Any],
        context: Dict[str, Any],
        autonomy_level: str
    ) -> ApprovalStatus:
        """
        Request approval for agent execution based on autonomy level.
        
        Args:
            case_id: Case being processed
            agent_name: Name of the agent requesting approval
            agent_step: Specific step/action being requested
            proposed_action: What the agent wants to do
            context: Additional context for approval decision
            autonomy_level: Current autonomy level
            
        Returns:
            ApprovalStatus indicating the result
        """
        # Determine if approval is needed
        if not self._requires_approval(agent_name, agent_step, autonomy_level):
            logger.info(f"Auto-approving {agent_name} step {agent_step} (autonomy: {autonomy_level})")
            return ApprovalStatus.APPROVED
        
        # Create approval request
        request_id = f"{case_id}_{agent_name}_{int(time.time())}"
        timeout_minutes = (
            self.config.manual_timeout_minutes if autonomy_level == "manual" 
            else self.config.supervised_timeout_minutes
        )
        
        approval_request = ApprovalRequest(
            request_id=request_id,
            case_id=case_id,
            agent_name=agent_name,
            agent_step=agent_step,
            proposed_action=proposed_action,
            context=context,
            autonomy_level=autonomy_level,
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc).replace(
                minute=datetime.now().minute + timeout_minutes
            )
        )
        
        # Store in memory and Redis
        self.pending_approvals[request_id] = approval_request
        await self._store_approval_request(approval_request)
        
        # Send notification
        await self._send_approval_notification(approval_request)
        
        logger.info(f"Approval requested: {request_id} for {agent_name} ({autonomy_level})")
        
        # Wait for approval or timeout
        return await self._wait_for_approval(request_id, timeout_minutes)
    
    def _requires_approval(self, agent_name: str, agent_step: str, autonomy_level: str) -> bool:
        """Determine if this agent/step requires approval based on autonomy level."""
        if autonomy_level == "autonomous":
            return False
        elif autonomy_level == "manual":
            return True
        elif autonomy_level == "supervised":
            # Only require approval for critical agents
            return agent_name in self.config.require_approval_agents
        elif autonomy_level == "research":
            # Research mode has optional checkpoints
            return agent_step in ["critical_finding", "containment_action"]
        
        return False
    
    async def _store_approval_request(self, request: ApprovalRequest):
        """Store approval request in Redis for persistence."""
        try:
            request_data = {
                'request_id': request.request_id,
                'case_id': request.case_id,
                'agent_name': request.agent_name,
                'agent_step': request.agent_step,
                'proposed_action': json.dumps(request.proposed_action),
                'context': json.dumps(request.context),
                'autonomy_level': request.autonomy_level,
                'created_at': request.created_at.isoformat(),
                'expires_at': request.expires_at.isoformat(),
                'status': request.status.value
            }
            
            await self.redis.hset(f"approval:{request.request_id}", mapping=request_data)
            await self.redis.expire(f"approval:{request.request_id}", 3600)  # 1 hour TTL
            
        except Exception as e:
            logger.error(f"Failed to store approval request: {e}")
    
    async def _send_approval_notification(self, request: ApprovalRequest):
        """Send notification about pending approval."""
        notification_data = {
            'type': 'approval_request',
            'request_id': request.request_id,
            'case_id': request.case_id,
            'agent_name': request.agent_name,
            'agent_step': request.agent_step,
            'proposed_action': request.proposed_action,
            'autonomy_level': request.autonomy_level,
            'expires_at': request.expires_at.isoformat(),
            'approval_url': f"/approve/{request.request_id}"
        }
        
        try:
            if self.notification_callback:
                await self.notification_callback(notification_data)
            
            # Also store notification in Redis for UI polling
            await self.redis.lpush("approval_notifications", json.dumps(notification_data))
            await self.redis.expire("approval_notifications", 3600)
            
            logger.info(f"Sent approval notification for {request.request_id}")
            
        except Exception as e:
            logger.error(f"Failed to send approval notification: {e}")
    
    async def _wait_for_approval(self, request_id: str, timeout_minutes: int) -> ApprovalStatus:
        """Wait for approval response or timeout."""
        start_time = time.time()
        timeout_seconds = timeout_minutes * 60
        
        while (time.time() - start_time) < timeout_seconds:
            # Check if approval was given
            request = self.pending_approvals.get(request_id)
            if not request:
                logger.warning(f"Approval request {request_id} disappeared")
                return ApprovalStatus.TIMEOUT
            
            if request.status != ApprovalStatus.PENDING:
                # Calculate response time
                response_time_ms = (time.time() - start_time) * 1000
                request.response_time_ms = int(response_time_ms)
                
                # Update statistics
                self.stats['total_requests'] += 1
                if request.status == ApprovalStatus.APPROVED:
                    self.stats['approved_requests'] += 1
                elif request.status == ApprovalStatus.REJECTED:
                    self.stats['rejected_requests'] += 1
                
                # Update average response time
                prev_avg = self.stats['average_response_time_ms']
                total_requests = self.stats['total_requests']
                self.stats['average_response_time_ms'] = (
                    (prev_avg * (total_requests - 1) + response_time_ms) / total_requests
                )
                
                # Cleanup
                del self.pending_approvals[request_id]
                
                logger.info(f"Approval {request.status.value} for {request_id} in {response_time_ms:.1f}ms")
                return request.status
            
            # Wait a bit before checking again
            await asyncio.sleep(1.0)
        
        # Timeout occurred
        request = self.pending_approvals.get(request_id)
        if request:
            request.status = ApprovalStatus.TIMEOUT
            del self.pending_approvals[request_id]
            self.stats['timeout_requests'] += 1
        
        logger.warning(f"Approval request {request_id} timed out after {timeout_minutes} minutes")
        return ApprovalStatus.TIMEOUT
    
    async def approve_request(self, request_id: str, approved_by: str) -> bool:
        """Approve a pending request."""
        try:
            request = self.pending_approvals.get(request_id)
            if not request:
                logger.warning(f"Approval request {request_id} not found")
                return False
            
            if request.status != ApprovalStatus.PENDING:
                logger.warning(f"Request {request_id} already {request.status.value}")
                return False
            
            # Update request
            request.status = ApprovalStatus.APPROVED
            request.approved_by = approved_by
            
            # Update in Redis
            await self.redis.hset(f"approval:{request_id}", "status", "approved")
            await self.redis.hset(f"approval:{request_id}", "approved_by", approved_by)
            
            logger.info(f"Request {request_id} approved by {approved_by}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to approve request {request_id}: {e}")
            return False
    
    async def reject_request(self, request_id: str, rejected_by: str, reason: str) -> bool:
        """Reject a pending request."""
        try:
            request = self.pending_approvals.get(request_id)
            if not request:
                logger.warning(f"Approval request {request_id} not found")
                return False
            
            if request.status != ApprovalStatus.PENDING:
                logger.warning(f"Request {request_id} already {request.status.value}")
                return False
            
            # Update request
            request.status = ApprovalStatus.REJECTED
            request.approved_by = rejected_by
            request.rejection_reason = reason
            
            # Update in Redis
            await self.redis.hset(f"approval:{request_id}", "status", "rejected")
            await self.redis.hset(f"approval:{request_id}", "rejected_by", rejected_by)
            await self.redis.hset(f"approval:{request_id}", "rejection_reason", reason)
            
            logger.info(f"Request {request_id} rejected by {rejected_by}: {reason}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to reject request {request_id}: {e}")
            return False
    
    async def get_pending_approvals(self, case_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get list of pending approval requests."""
        pending = []
        
        for request_id, request in self.pending_approvals.items():
            if case_id and request.case_id != case_id:
                continue
            
            if request.status == ApprovalStatus.PENDING:
                pending.append({
                    'request_id': request.request_id,
                    'case_id': request.case_id,
                    'agent_name': request.agent_name,
                    'agent_step': request.agent_step,
                    'proposed_action': request.proposed_action,
                    'context': request.context,
                    'autonomy_level': request.autonomy_level,
                    'created_at': request.created_at.isoformat(),
                    'expires_at': request.expires_at.isoformat(),
                    'time_remaining_minutes': max(0, int(
                        (request.expires_at - datetime.now(timezone.utc)).total_seconds() / 60
                    ))
                })
        
        return pending
    
    async def get_approval_statistics(self) -> Dict[str, Any]:
        """Get approval system statistics."""
        return {
            'stats': self.stats,
            'pending_count': len(self.pending_approvals),
            'config': {
                'manual_timeout_minutes': self.config.manual_timeout_minutes,
                'supervised_timeout_minutes': self.config.supervised_timeout_minutes,
                'require_approval_agents': self.config.require_approval_agents
            }
        }


# Integration with existing agent workflow
async def execute_with_autonomy_check(
    autonomy_manager: AutonomyManager,
    case_id: str,
    agent_name: str,
    agent_step: str,
    agent_execute_func: Callable,
    proposed_action: Dict[str, Any],
    context: Dict[str, Any],
    autonomy_level: str
) -> Dict[str, Any]:
    """
    Execute agent with autonomy check and approval if needed.
    
    This function wraps agent execution with approval workflow.
    """
    # Request approval if needed
    approval_status = await autonomy_manager.request_approval(
        case_id=case_id,
        agent_name=agent_name,
        agent_step=agent_step,
        proposed_action=proposed_action,
        context=context,
        autonomy_level=autonomy_level
    )
    
    if approval_status == ApprovalStatus.APPROVED:
        # Execute the agent
        logger.info(f"Executing {agent_name} step {agent_step} (approved)")
        result = await agent_execute_func()
        
        return {
            'status': 'success',
            'result': result,
            'approval_status': approval_status.value,
            'execution_time': time.time()
        }
    
    elif approval_status == ApprovalStatus.REJECTED:
        logger.warning(f"Agent execution rejected: {agent_name} step {agent_step}")
        return {
            'status': 'rejected', 
            'result': None,
            'approval_status': approval_status.value,
            'message': 'Execution rejected by human operator'
        }
    
    elif approval_status == ApprovalStatus.TIMEOUT:
        logger.error(f"Agent approval timed out: {agent_name} step {agent_step}")
        return {
            'status': 'timeout',
            'result': None, 
            'approval_status': approval_status.value,
            'message': 'Approval request timed out'
        }
    
    else:
        logger.error(f"Unknown approval status: {approval_status}")
        return {
            'status': 'error',
            'result': None,
            'approval_status': approval_status.value,
            'message': 'Unknown approval status'
        }


# Notification callback example
async def slack_notification_callback(notification_data: Dict[str, Any]):
    """Example notification callback for Slack integration."""
    message = f"""
🤖 **SOC Agent Approval Request**

**Case:** {notification_data['case_id']}
**Agent:** {notification_data['agent_name']}
**Step:** {notification_data['agent_step']}
**Autonomy Level:** {notification_data['autonomy_level']}

**Proposed Action:**
{json.dumps(notification_data['proposed_action'], indent=2)}

**Expires:** {notification_data['expires_at']}

[Approve]({notification_data['approval_url']}) | [Reject]({notification_data['approval_url']}/reject)
"""
    
    # Here you would integrate with actual Slack API
    logger.info(f"Would send Slack notification: {message}")


# Example usage function
async def demo_autonomy_levels():
    """Demonstrate how autonomy levels work in practice."""
    
    # Mock Redis client for demo
    class MockRedis:
        async def hset(self, *args, **kwargs): pass
        async def expire(self, *args, **kwargs): pass  
        async def lpush(self, *args, **kwargs): pass
    
    redis_client = MockRedis()
    
    # Create autonomy manager
    autonomy_manager = AutonomyManager(
        redis_client=redis_client,
        notification_callback=slack_notification_callback
    )
    
    # Example: Different behaviors by autonomy level
    
    print("=== MANUAL MODE EXAMPLE ===")
    # In manual mode, EVERY agent step requires approval
    manual_status = await autonomy_manager.request_approval(
        case_id="CASE-001",
        agent_name="TriageAgent", 
        agent_step="extract_entities",
        proposed_action={"action": "extract_entities", "source": "case_data"},
        context={"severity": "medium"},
        autonomy_level="manual"
    )
    print(f"Manual mode result: {manual_status}")
    
    print("\\n=== SUPERVISED MODE EXAMPLE ===")  
    # In supervised mode, only critical agents require approval
    supervised_status = await autonomy_manager.request_approval(
        case_id="CASE-002",
        agent_name="TriageAgent",  # This would auto-approve
        agent_step="extract_entities", 
        proposed_action={"action": "extract_entities", "source": "case_data"},
        context={"severity": "medium"},
        autonomy_level="supervised"
    )
    print(f"Supervised mode (TriageAgent): {supervised_status}")
    
    critical_status = await autonomy_manager.request_approval(
        case_id="CASE-002",
        agent_name="ResponseAgent",  # This requires approval
        agent_step="isolate_system",
        proposed_action={"action": "isolate", "target": "host-123"},
        context={"severity": "high"},
        autonomy_level="supervised"
    )
    print(f"Supervised mode (ResponseAgent): {critical_status}")
    
    print("\\n=== AUTONOMOUS MODE EXAMPLE ===")
    # In autonomous mode, nothing requires approval
    autonomous_status = await autonomy_manager.request_approval(
        case_id="CASE-003",
        agent_name="ResponseAgent",
        agent_step="isolate_system",
        proposed_action={"action": "isolate", "target": "host-456"},
        context={"severity": "high"}, 
        autonomy_level="autonomous"
    )
    print(f"Autonomous mode result: {autonomous_status}")


if __name__ == "__main__":
    asyncio.run(demo_autonomy_levels())