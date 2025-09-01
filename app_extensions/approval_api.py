"""
Approval API Endpoints for Human-in-the-Loop Workflows.

This module provides REST API endpoints for managing approval requests
in different autonomy levels.
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import Dict, List, Any, Optional
from pydantic import BaseModel
import logging

from .autonomy_manager import AutonomyManager, ApprovalStatus

logger = logging.getLogger(__name__)

# Pydantic models for API
class ApprovalResponse(BaseModel):
    approved: bool
    approved_by: str
    reason: Optional[str] = None

class ApprovalRequestInfo(BaseModel):
    request_id: str
    case_id: str
    agent_name: str
    agent_step: str
    proposed_action: Dict[str, Any]
    context: Dict[str, Any]
    autonomy_level: str
    created_at: str
    expires_at: str
    time_remaining_minutes: int

class ApprovalStats(BaseModel):
    total_requests: int
    approved_requests: int
    rejected_requests: int
    timeout_requests: int
    average_response_time_ms: float
    pending_count: int

def create_approval_router(autonomy_manager: AutonomyManager) -> APIRouter:
    """Create FastAPI router for approval endpoints."""
    
    router = APIRouter(prefix="/approvals", tags=["approvals"])
    
    @router.get("/pending", response_model=List[ApprovalRequestInfo])
    async def get_pending_approvals(case_id: Optional[str] = None):
        """Get list of pending approval requests."""
        try:
            pending = await autonomy_manager.get_pending_approvals(case_id)
            return [ApprovalRequestInfo(**req) for req in pending]
        except Exception as e:
            logger.error(f"Failed to get pending approvals: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.get("/stats", response_model=ApprovalStats)
    async def get_approval_stats():
        """Get approval system statistics."""
        try:
            stats = await autonomy_manager.get_approval_statistics()
            return ApprovalStats(
                total_requests=stats['stats']['total_requests'],
                approved_requests=stats['stats']['approved_requests'],
                rejected_requests=stats['stats']['rejected_requests'],
                timeout_requests=stats['stats']['timeout_requests'],
                average_response_time_ms=stats['stats']['average_response_time_ms'],
                pending_count=stats['pending_count']
            )
        except Exception as e:
            logger.error(f"Failed to get approval stats: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.post("/approve/{request_id}")
    async def approve_request(request_id: str, response: ApprovalResponse):
        """Approve a pending request."""
        if not response.approved:
            raise HTTPException(status_code=400, detail="Use reject endpoint for rejections")
        
        try:
            success = await autonomy_manager.approve_request(request_id, response.approved_by)
            if not success:
                raise HTTPException(status_code=404, detail="Request not found or already processed")
            
            return {"status": "approved", "request_id": request_id, "approved_by": response.approved_by}
            
        except Exception as e:
            logger.error(f"Failed to approve request {request_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.post("/reject/{request_id}")
    async def reject_request(request_id: str, response: ApprovalResponse):
        """Reject a pending request."""
        if response.approved:
            raise HTTPException(status_code=400, detail="Use approve endpoint for approvals")
        
        if not response.reason:
            raise HTTPException(status_code=400, detail="Rejection reason is required")
        
        try:
            success = await autonomy_manager.reject_request(
                request_id, response.approved_by, response.reason
            )
            if not success:
                raise HTTPException(status_code=404, detail="Request not found or already processed")
            
            return {
                "status": "rejected", 
                "request_id": request_id, 
                "rejected_by": response.approved_by,
                "reason": response.reason
            }
            
        except Exception as e:
            logger.error(f"Failed to reject request {request_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.get("/request/{request_id}")
    async def get_request_details(request_id: str):
        """Get details of a specific approval request."""
        try:
            # Try to get from pending requests first
            for req_id, request in autonomy_manager.pending_approvals.items():
                if req_id == request_id:
                    return {
                        "request_id": request.request_id,
                        "case_id": request.case_id,
                        "agent_name": request.agent_name,
                        "agent_step": request.agent_step,
                        "proposed_action": request.proposed_action,
                        "context": request.context,
                        "autonomy_level": request.autonomy_level,
                        "status": request.status.value,
                        "created_at": request.created_at.isoformat(),
                        "expires_at": request.expires_at.isoformat(),
                        "approved_by": request.approved_by,
                        "rejection_reason": request.rejection_reason,
                        "response_time_ms": request.response_time_ms
                    }
            
            # If not found in memory, try Redis (for completed requests)
            # This would require additional implementation to fetch from Redis
            raise HTTPException(status_code=404, detail="Request not found")
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get request details {request_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    return router


# HTML templates for approval UI (basic implementation)
APPROVAL_UI_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>SOC Platform - Approval Dashboard</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }
        .header { border-bottom: 1px solid #ddd; padding-bottom: 20px; margin-bottom: 20px; }
        .approval-card { border: 1px solid #ddd; margin: 10px 0; padding: 15px; border-radius: 5px; }
        .approval-card.urgent { border-left: 5px solid #ff4757; }
        .approval-card.normal { border-left: 5px solid #3742fa; }
        .btn { padding: 8px 16px; margin: 5px; border: none; border-radius: 4px; cursor: pointer; }
        .btn-approve { background: #2ed573; color: white; }
        .btn-reject { background: #ff4757; color: white; }
        .btn:hover { opacity: 0.8; }
        .meta { color: #666; font-size: 0.9em; margin: 5px 0; }
        .action-details { background: #f8f9fa; padding: 10px; margin: 10px 0; border-radius: 4px; }
        .timer { float: right; color: #ff4757; font-weight: bold; }
        pre { background: #f1f2f6; padding: 10px; border-radius: 4px; overflow-x: auto; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 SOC Platform - Approval Dashboard</h1>
            <p>Review and approve pending agent actions</p>
        </div>
        
        <div id="pending-approvals">
            <h2>Pending Approvals (<span id="approval-count">0</span>)</h2>
            <div id="approvals-list"></div>
        </div>
        
        <div id="stats">
            <h2>Statistics</h2>
            <div id="stats-content"></div>
        </div>
    </div>

    <script>
        // Auto-refresh every 5 seconds
        setInterval(loadApprovals, 5000);
        setInterval(loadStats, 30000);
        
        // Load on page load
        loadApprovals();
        loadStats();
        
        async function loadApprovals() {
            try {
                const response = await fetch('/approvals/pending');
                const approvals = await response.json();
                
                document.getElementById('approval-count').textContent = approvals.length;
                
                const listElement = document.getElementById('approvals-list');
                
                if (approvals.length === 0) {
                    listElement.innerHTML = '<p>No pending approvals</p>';
                    return;
                }
                
                listElement.innerHTML = approvals.map(approval => `
                    <div class="approval-card ${approval.time_remaining_minutes < 5 ? 'urgent' : 'normal'}">
                        <div class="timer">${approval.time_remaining_minutes} min remaining</div>
                        <h3>${approval.agent_name} - ${approval.agent_step}</h3>
                        <div class="meta">
                            <strong>Case:</strong> ${approval.case_id} | 
                            <strong>Autonomy:</strong> ${approval.autonomy_level} |
                            <strong>Created:</strong> ${new Date(approval.created_at).toLocaleString()}
                        </div>
                        
                        <div class="action-details">
                            <strong>Proposed Action:</strong>
                            <pre>${JSON.stringify(approval.proposed_action, null, 2)}</pre>
                        </div>
                        
                        <div class="action-details">
                            <strong>Context:</strong>
                            <pre>${JSON.stringify(approval.context, null, 2)}</pre>
                        </div>
                        
                        <div>
                            <button class="btn btn-approve" onclick="approveRequest('${approval.request_id}')">
                                ✅ Approve
                            </button>
                            <button class="btn btn-reject" onclick="rejectRequest('${approval.request_id}')">
                                ❌ Reject
                            </button>
                        </div>
                    </div>
                `).join('');
                
            } catch (error) {
                console.error('Failed to load approvals:', error);
            }
        }
        
        async function loadStats() {
            try {
                const response = await fetch('/approvals/stats');
                const stats = await response.json();
                
                document.getElementById('stats-content').innerHTML = `
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px;">
                        <div class="action-details">
                            <strong>Total Requests:</strong> ${stats.total_requests}
                        </div>
                        <div class="action-details">
                            <strong>Approved:</strong> ${stats.approved_requests}
                        </div>
                        <div class="action-details">
                            <strong>Rejected:</strong> ${stats.rejected_requests}
                        </div>
                        <div class="action-details">
                            <strong>Timeouts:</strong> ${stats.timeout_requests}
                        </div>
                        <div class="action-details">
                            <strong>Avg Response Time:</strong> ${Math.round(stats.average_response_time_ms)}ms
                        </div>
                        <div class="action-details">
                            <strong>Pending Now:</strong> ${stats.pending_count}
                        </div>
                    </div>
                `;
                
            } catch (error) {
                console.error('Failed to load stats:', error);
            }
        }
        
        async function approveRequest(requestId) {
            const approvedBy = prompt('Enter your name/ID:');
            if (!approvedBy) return;
            
            try {
                const response = await fetch(`/approvals/approve/${requestId}`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        approved: true,
                        approved_by: approvedBy
                    })
                });
                
                if (response.ok) {
                    alert('Request approved successfully!');
                    loadApprovals();
                } else {
                    const error = await response.json();
                    alert(`Failed to approve: ${error.detail}`);
                }
            } catch (error) {
                alert(`Error: ${error.message}`);
            }
        }
        
        async function rejectRequest(requestId) {
            const rejectedBy = prompt('Enter your name/ID:');
            if (!rejectedBy) return;
            
            const reason = prompt('Enter rejection reason:');
            if (!reason) return;
            
            try {
                const response = await fetch(`/approvals/reject/${requestId}`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        approved: false,
                        approved_by: rejectedBy,
                        reason: reason
                    })
                });
                
                if (response.ok) {
                    alert('Request rejected successfully!');
                    loadApprovals();
                } else {
                    const error = await response.json();
                    alert(`Failed to reject: ${error.detail}`);
                }
            } catch (error) {
                alert(`Error: ${error.message}`);
            }
        }
    </script>
</body>
</html>
"""

def create_approval_ui_router() -> APIRouter:
    """Create router for approval UI."""
    from fastapi.responses import HTMLResponse
    
    router = APIRouter(prefix="/ui", tags=["ui"])
    
    @router.get("/approvals", response_class=HTMLResponse)
    async def approval_dashboard():
        """Serve the approval dashboard UI."""
        return APPROVAL_UI_HTML
    
    return router