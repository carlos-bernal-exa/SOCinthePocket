"""
OpenTUI Terminal Interface for SOC Platform

A rich terminal interface using OpenTUI for interactive SOC operations with:
- Real-time case analysis dashboard
- Autonomy level controls
- Agent execution monitoring
- Approval workflow management
- Performance metrics and alerts
"""

import asyncio
import json
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import requests
import subprocess
import sys
from pathlib import Path

# OpenTUI Terminal Interface Configuration
OPENTUI_CONFIG = {
    "name": "SOC Platform Terminal",
    "version": "1.0.0",
    "description": "Interactive terminal interface for SOC operations",
    "theme": "dark",
    "components": {
        "dashboard": {
            "type": "layout",
            "direction": "vertical",
            "components": [
                {
                    "type": "header",
                    "title": "🛡️ SOC Platform - Agent Command Center",
                    "subtitle": "AI-Powered Security Operations"
                },
                {
                    "type": "tabs",
                    "tabs": [
                        {
                            "name": "Dashboard",
                            "key": "dashboard",
                            "component": "dashboard_view"
                        },
                        {
                            "name": "Cases", 
                            "key": "cases",
                            "component": "cases_view"
                        },
                        {
                            "name": "Agents",
                            "key": "agents", 
                            "component": "agents_view"
                        },
                        {
                            "name": "Approvals",
                            "key": "approvals",
                            "component": "approvals_view"
                        },
                        {
                            "name": "Analytics",
                            "key": "analytics",
                            "component": "analytics_view"
                        }
                    ]
                }
            ]
        },
        "dashboard_view": {
            "type": "layout",
            "direction": "horizontal",
            "components": [
                {
                    "type": "layout",
                    "direction": "vertical",
                    "flex": 2,
                    "components": [
                        {
                            "type": "card",
                            "title": "🎯 Quick Actions",
                            "component": "quick_actions"
                        },
                        {
                            "type": "card", 
                            "title": "📊 System Status",
                            "component": "system_status"
                        }
                    ]
                },
                {
                    "type": "layout",
                    "direction": "vertical", 
                    "flex": 3,
                    "components": [
                        {
                            "type": "card",
                            "title": "🔄 Recent Activity",
                            "component": "activity_feed"
                        }
                    ]
                }
            ]
        },
        "cases_view": {
            "type": "layout",
            "direction": "vertical",
            "components": [
                {
                    "type": "form",
                    "title": "🔍 Case Analysis",
                    "component": "case_form"
                },
                {
                    "type": "table",
                    "title": "Recent Cases",
                    "component": "cases_table"
                }
            ]
        },
        "agents_view": {
            "type": "layout",
            "direction": "vertical", 
            "components": [
                {
                    "type": "grid",
                    "columns": 2,
                    "component": "agents_grid"
                }
            ]
        },
        "approvals_view": {
            "type": "layout",
            "direction": "vertical",
            "components": [
                {
                    "type": "card",
                    "title": "⏳ Pending Approvals",
                    "component": "pending_approvals"
                },
                {
                    "type": "card",
                    "title": "📈 Approval Statistics", 
                    "component": "approval_stats"
                }
            ]
        },
        "analytics_view": {
            "type": "layout",
            "direction": "vertical",
            "components": [
                {
                    "type": "chart",
                    "title": "Case Volume Trends",
                    "chartType": "line",
                    "component": "case_trends"
                },
                {
                    "type": "chart", 
                    "title": "Autonomy Level Usage",
                    "chartType": "pie",
                    "component": "autonomy_stats"
                }
            ]
        }
    }
}

class SOCTerminalInterface:
    """
    Main terminal interface controller for SOC platform.
    """
    
    def __init__(self, api_base_url: str = "http://localhost:8000"):
        self.api_base_url = api_base_url
        self.current_case_id: Optional[str] = None
        self.current_autonomy_level = "supervised"
        self.cases_history: List[Dict[str, Any]] = []
        self.agents_status: Dict[str, str] = {}
        self.activity_feed: List[Dict[str, Any]] = []
        
    def generate_opentui_config(self) -> Dict[str, Any]:
        """Generate dynamic OpenTUI configuration with current state."""
        
        # Update components with current data
        config = OPENTUI_CONFIG.copy()
        
        # Add dynamic data bindings
        config["data"] = {
            "quick_actions": self._get_quick_actions_data(),
            "system_status": self._get_system_status_data(),
            "activity_feed": self._get_activity_feed_data(),
            "case_form": self._get_case_form_data(),
            "cases_table": self._get_cases_table_data(),
            "agents_grid": self._get_agents_grid_data(),
            "pending_approvals": self._get_pending_approvals_data(),
            "approval_stats": self._get_approval_stats_data(),
            "case_trends": self._get_case_trends_data(),
            "autonomy_stats": self._get_autonomy_stats_data()
        }
        
        # Add event handlers
        config["handlers"] = {
            "case_analyze": self._handle_case_analyze,
            "autonomy_change": self._handle_autonomy_change,
            "approve_request": self._handle_approve_request,
            "reject_request": self._handle_reject_request,
            "refresh_data": self._handle_refresh_data
        }
        
        return config
    
    def _get_quick_actions_data(self) -> Dict[str, Any]:
        """Get quick actions panel data."""
        return {
            "type": "actions",
            "actions": [
                {
                    "id": "analyze_case",
                    "label": "🔍 Analyze Case", 
                    "type": "button",
                    "variant": "primary",
                    "handler": "case_analyze",
                    "inputs": [
                        {
                            "name": "case_id",
                            "label": "Case ID",
                            "type": "text",
                            "placeholder": "22712942-ba96-4fe4-886d-443bfec14e8a",
                            "required": True
                        },
                        {
                            "name": "autonomy_level",
                            "label": "Autonomy Level",
                            "type": "select",
                            "options": [
                                {"value": "manual", "label": "🔴 Manual - Human approval each step"},
                                {"value": "supervised", "label": "🟡 Supervised - Critical steps only"},
                                {"value": "autonomous", "label": "🟢 Autonomous - Full automation"},
                                {"value": "research", "label": "🔵 Research - Deep analysis mode"}
                            ],
                            "default": "supervised"
                        },
                        {
                            "name": "max_depth",
                            "label": "Analysis Depth",
                            "type": "slider",
                            "min": 1,
                            "max": 5,
                            "default": 2,
                            "step": 1
                        }
                    ]
                },
                {
                    "id": "health_check",
                    "label": "❤️ Health Check",
                    "type": "button", 
                    "variant": "secondary",
                    "handler": "health_check"
                },
                {
                    "id": "emergency_stop",
                    "label": "⛔ Emergency Stop",
                    "type": "button",
                    "variant": "danger",
                    "handler": "emergency_stop",
                    "confirm": "Are you sure you want to stop all agent operations?"
                }
            ]
        }
    
    def _get_system_status_data(self) -> Dict[str, Any]:
        """Get system status data."""
        try:
            # Try to get health status from API
            response = requests.get(f"{self.api_base_url}/health", timeout=5)
            if response.status_code == 200:
                health_status = "🟢 Online"
                health_color = "green"
            else:
                health_status = "🟡 Degraded"
                health_color = "yellow"
        except:
            health_status = "🔴 Offline"
            health_color = "red"
        
        return {
            "type": "metrics",
            "metrics": [
                {
                    "label": "API Status",
                    "value": health_status,
                    "color": health_color
                },
                {
                    "label": "Active Cases",
                    "value": len(self.cases_history),
                    "color": "blue"
                },
                {
                    "label": "Current Mode",
                    "value": self.current_autonomy_level.title(),
                    "color": {
                        "manual": "red",
                        "supervised": "yellow", 
                        "autonomous": "green",
                        "research": "blue"
                    }.get(self.current_autonomy_level, "gray")
                },
                {
                    "label": "Agents Ready",
                    "value": "8/8",
                    "color": "green"
                }
            ]
        }
    
    def _get_activity_feed_data(self) -> Dict[str, Any]:
        """Get activity feed data."""
        return {
            "type": "feed",
            "items": self.activity_feed[-10:],  # Last 10 activities
            "auto_refresh": True,
            "refresh_interval": 5000  # 5 seconds
        }
    
    def _get_case_form_data(self) -> Dict[str, Any]:
        """Get case analysis form data."""
        return {
            "type": "form",
            "fields": [
                {
                    "name": "case_id",
                    "label": "Case ID",
                    "type": "text",
                    "placeholder": "Enter case ID or UUID",
                    "validation": "required|uuid"
                },
                {
                    "name": "autonomy_level",
                    "label": "Autonomy Level",
                    "type": "radio",
                    "options": [
                        {
                            "value": "manual",
                            "label": "Manual",
                            "description": "Human approval required for each step"
                        },
                        {
                            "value": "supervised", 
                            "label": "Supervised",
                            "description": "Approval needed for critical actions only"
                        },
                        {
                            "value": "autonomous",
                            "label": "Autonomous",
                            "description": "Full automation with no interruptions"
                        },
                        {
                            "value": "research",
                            "label": "Research",
                            "description": "Deep analysis with extended context"
                        }
                    ],
                    "default": "supervised"
                },
                {
                    "name": "priority",
                    "label": "Priority",
                    "type": "select",
                    "options": [
                        {"value": "low", "label": "Low"},
                        {"value": "medium", "label": "Medium"}, 
                        {"value": "high", "label": "High"},
                        {"value": "critical", "label": "Critical"}
                    ],
                    "default": "medium"
                }
            ],
            "submit": {
                "label": "🚀 Start Analysis",
                "handler": "case_analyze"
            }
        }
    
    def _get_cases_table_data(self) -> Dict[str, Any]:
        """Get cases table data."""
        return {
            "type": "table",
            "headers": ["Case ID", "Status", "Autonomy", "Started", "Duration", "Actions"],
            "rows": [
                {
                    "id": case["case_id"],
                    "cells": [
                        case["case_id"][:8] + "...",
                        {
                            "type": "badge",
                            "text": case.get("status", "completed"),
                            "color": {
                                "running": "blue",
                                "completed": "green", 
                                "failed": "red",
                                "pending": "yellow"
                            }.get(case.get("status", "completed"), "gray")
                        },
                        case.get("autonomy_level", "supervised"),
                        case.get("started_at", "Unknown")[:16],
                        case.get("duration", "N/A"),
                        {
                            "type": "actions",
                            "actions": [
                                {"label": "View", "handler": f"view_case:{case['case_id']}"},
                                {"label": "Report", "handler": f"export_report:{case['case_id']}"}
                            ]
                        }
                    ]
                }
                for case in self.cases_history[-10:]  # Last 10 cases
            ],
            "pagination": True,
            "page_size": 10
        }
    
    def _get_agents_grid_data(self) -> Dict[str, Any]:
        """Get agents grid data."""
        agents = [
            {"name": "TriageAgent", "status": "ready", "description": "Initial threat assessment"},
            {"name": "EnrichmentAgent", "status": "ready", "description": "Case correlation and filtering"},
            {"name": "InvestigationAgent", "status": "ready", "description": "Deep forensic analysis"},
            {"name": "CorrelationAgent", "status": "ready", "description": "Attack pattern mapping"},
            {"name": "ResponseAgent", "status": "ready", "description": "Containment planning"},
            {"name": "ReportingAgent", "status": "ready", "description": "Report generation"},
            {"name": "KnowledgeAgent", "status": "ready", "description": "Threat intelligence"},
            {"name": "ControllerAgent", "status": "ready", "description": "Workflow orchestration"}
        ]
        
        return {
            "type": "grid",
            "items": [
                {
                    "id": agent["name"],
                    "title": agent["name"],
                    "status": agent["status"],
                    "description": agent["description"],
                    "metrics": {
                        "executions": "0",
                        "avg_time": "0ms",
                        "success_rate": "100%"
                    },
                    "actions": [
                        {"label": "Test", "handler": f"test_agent:{agent['name']}"},
                        {"label": "Logs", "handler": f"view_logs:{agent['name']}"}
                    ]
                }
                for agent in agents
            ]
        }
    
    def _get_pending_approvals_data(self) -> Dict[str, Any]:
        """Get pending approvals data."""
        # Mock data for now - would integrate with AutonomyManager
        pending = []
        
        return {
            "type": "approvals",
            "items": pending,
            "empty_message": "No pending approvals",
            "refresh_interval": 3000  # 3 seconds
        }
    
    def _get_approval_stats_data(self) -> Dict[str, Any]:
        """Get approval statistics data."""
        return {
            "type": "stats",
            "metrics": [
                {"label": "Total Requests", "value": "0", "change": "+0%"},
                {"label": "Approved", "value": "0", "change": "+0%"},
                {"label": "Rejected", "value": "0", "change": "+0%"},
                {"label": "Avg Response Time", "value": "0s", "change": "+0%"}
            ]
        }
    
    def _get_case_trends_data(self) -> Dict[str, Any]:
        """Get case trends chart data."""
        return {
            "type": "line_chart",
            "data": {
                "labels": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
                "datasets": [
                    {
                        "label": "Cases Analyzed",
                        "data": [2, 1, 4, 3, 2, 1, 0],
                        "color": "blue"
                    }
                ]
            },
            "options": {
                "responsive": True,
                "scales": {
                    "y": {
                        "beginAtZero": True
                    }
                }
            }
        }
    
    def _get_autonomy_stats_data(self) -> Dict[str, Any]:
        """Get autonomy level usage statistics."""
        return {
            "type": "pie_chart",
            "data": {
                "labels": ["Supervised", "Autonomous", "Manual", "Research"],
                "datasets": [
                    {
                        "data": [60, 25, 10, 5],
                        "colors": ["#ffd700", "#00ff00", "#ff0000", "#0066ff"]
                    }
                ]
            }
        }
    
    async def _handle_case_analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle case analysis request."""
        case_id = data.get("case_id")
        autonomy_level = data.get("autonomy_level", "supervised")
        max_depth = data.get("max_depth", 2)
        
        if not case_id:
            return {"error": "Case ID is required"}
        
        try:
            # Add to activity feed
            self.activity_feed.append({
                "id": len(self.activity_feed),
                "timestamp": datetime.now().isoformat(),
                "type": "case_analysis",
                "message": f"Started analysis of case {case_id} in {autonomy_level} mode",
                "status": "running",
                "details": {
                    "case_id": case_id,
                    "autonomy_level": autonomy_level,
                    "max_depth": max_depth
                }
            })
            
            # Make API call to analyze case
            response = requests.post(
                f"{self.api_base_url}/cases/{case_id}/enrich",
                json={
                    "autonomy_level": autonomy_level,
                    "max_depth": max_depth
                },
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Add to cases history
                self.cases_history.append({
                    "case_id": case_id,
                    "autonomy_level": autonomy_level,
                    "status": "completed",
                    "started_at": datetime.now().isoformat(),
                    "duration": "45s",  # Would calculate from actual timing
                    "result": result
                })
                
                # Update activity feed
                self.activity_feed.append({
                    "id": len(self.activity_feed),
                    "timestamp": datetime.now().isoformat(),
                    "type": "case_analysis",
                    "message": f"Completed analysis of case {case_id}",
                    "status": "completed",
                    "details": {
                        "case_id": case_id,
                        "steps": result.get("steps", 0),
                        "severity": result.get("triage_assessment", {}).get("severity", "unknown")
                    }
                })
                
                return {
                    "success": True,
                    "message": f"Analysis completed for case {case_id}",
                    "result": result
                }
            else:
                error_msg = f"API error: {response.status_code}"
                self.activity_feed.append({
                    "id": len(self.activity_feed),
                    "timestamp": datetime.now().isoformat(),
                    "type": "error",
                    "message": f"Failed to analyze case {case_id}: {error_msg}",
                    "status": "error"
                })
                return {"error": error_msg}
                
        except Exception as e:
            error_msg = str(e)
            self.activity_feed.append({
                "id": len(self.activity_feed),
                "timestamp": datetime.now().isoformat(),
                "type": "error",
                "message": f"Error analyzing case {case_id}: {error_msg}",
                "status": "error"
            })
            return {"error": error_msg}
    
    async def _handle_autonomy_change(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle autonomy level change."""
        new_level = data.get("autonomy_level")
        if new_level:
            self.current_autonomy_level = new_level
            self.activity_feed.append({
                "id": len(self.activity_feed),
                "timestamp": datetime.now().isoformat(),
                "type": "config_change",
                "message": f"Autonomy level changed to {new_level}",
                "status": "info"
            })
        return {"success": True}
    
    async def _handle_approve_request(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle approval request."""
        request_id = data.get("request_id")
        # Would integrate with AutonomyManager here
        return {"success": True, "message": f"Approved request {request_id}"}
    
    async def _handle_reject_request(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle rejection request."""
        request_id = data.get("request_id")
        reason = data.get("reason", "No reason provided")
        # Would integrate with AutonomyManager here
        return {"success": True, "message": f"Rejected request {request_id}: {reason}"}
    
    async def _handle_refresh_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle data refresh request."""
        # Refresh all dynamic data
        return {"success": True, "message": "Data refreshed"}
    
    def write_opentui_config(self, output_path: str = "soc_terminal_config.json"):
        """Write OpenTUI configuration to file."""
        config = self.generate_opentui_config()
        
        with open(output_path, 'w') as f:
            json.dump(config, f, indent=2, default=str)
        
        return output_path
    
    def launch_terminal_interface(self):
        """Launch the OpenTUI terminal interface."""
        config_path = self.write_opentui_config()
        
        # Create launch script
        launch_script = f'''#!/bin/bash
# SOC Platform Terminal Interface Launch Script

echo "🛡️ Starting SOC Platform Terminal Interface..."
echo "Configuration: {config_path}"
echo "API Endpoint: {self.api_base_url}"
echo ""

# Check if OpenTUI is installed
if ! command -v opentui &> /dev/null; then
    echo "❌ OpenTUI not found. Installing..."
    # Try different package managers
    if command -v npm &> /dev/null; then
        npm install -g @sst/opentui
    elif command -v bun &> /dev/null; then
        bun install -g @sst/opentui
    elif command -v pnpm &> /dev/null; then
        pnpm install -g @sst/opentui
    else
        echo "❌ No supported package manager found (npm, bun, pnpm)"
        echo "Please install Node.js and npm first:"
        echo "  curl -fsSL https://nodejs.org/install.sh | bash"
        exit 1
    fi
fi

# Launch OpenTUI with our config
echo "🚀 Launching terminal interface..."
opentui --config {config_path} --port 3001 --host 0.0.0.0

# Alternative launch methods if direct config doesn't work
if [ $? -ne 0 ]; then
    echo "⚡ Trying alternative launch method..."
    
    # Create a simple HTML page that loads our config
    cat > soc_terminal.html << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>SOC Platform Terminal</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <script src="https://unpkg.com/@sst/opentui@latest/dist/index.js"></script>
    <style>
        body {{ margin: 0; padding: 0; font-family: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, 'Courier New', monospace; }}
        .terminal {{ height: 100vh; background: #1a1a1a; color: #00ff00; }}
    </style>
</head>
<body>
    <div id="terminal" class="terminal"></div>
    <script>
        // Load configuration and initialize OpenTUI
        fetch('./{config_path}')
            .then(response => response.json())
            .then(config => {{
                const terminal = new OpenTUI(config);
                terminal.mount('#terminal');
            }})
            .catch(error => {{
                console.error('Failed to load terminal config:', error);
                document.getElementById('terminal').innerHTML = 
                    '<div style="padding: 20px;">❌ Failed to load terminal interface</div>';
            }});
    </script>
</body>
</html>
EOF
    
    echo "📄 Created HTML interface: soc_terminal.html"
    echo "🌐 Open http://localhost:8080/soc_terminal.html in your browser"
    
    # Start a simple HTTP server
    if command -v python3 &> /dev/null; then
        echo "Starting Python HTTP server..."
        python3 -m http.server 8080
    elif command -v python &> /dev/null; then
        echo "Starting Python HTTP server..."
        python -m http.server 8080
    elif command -v node &> /dev/null; then
        echo "Starting Node.js HTTP server..."
        npx http-server -p 8080
    else
        echo "⚠️  No HTTP server available. Please open soc_terminal.html manually."
    fi
fi
'''
        
        # Write launch script
        script_path = "launch_soc_terminal.sh"
        with open(script_path, 'w') as f:
            f.write(launch_script)
        
        # Make executable
        subprocess.run(["chmod", "+x", script_path])
        
        print(f"🛡️ SOC Terminal Interface Ready!")
        print(f"📄 Configuration: {config_path}")
        print(f"🚀 Launch script: {script_path}")
        print(f"")
        print(f"To start the terminal interface:")
        print(f"  ./{script_path}")
        print(f"")
        print(f"Or manually install OpenTUI and run:")
        print(f"  npm install -g @sst/opentui")
        print(f"  opentui --config {config_path}")
        
        return script_path


def create_soc_terminal_interface():
    """Create and launch the SOC terminal interface."""
    interface = SOCTerminalInterface()
    
    # Add some sample data for demonstration
    interface.activity_feed.extend([
        {
            "id": 1,
            "timestamp": datetime.now().isoformat(),
            "type": "startup",
            "message": "SOC Terminal Interface initialized",
            "status": "info"
        },
        {
            "id": 2, 
            "timestamp": datetime.now().isoformat(),
            "type": "agent_status",
            "message": "All 8 agents are online and ready",
            "status": "success"
        }
    ])
    
    return interface


if __name__ == "__main__":
    print("🛡️ SOC Platform - OpenTUI Terminal Interface")
    print("=" * 50)
    
    # Check if API is running
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            print("✅ SOC API is running")
        else:
            print("⚠️  SOC API is not responding correctly")
    except:
        print("❌ SOC API is not running. Please start it first:")
        print("   python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000")
        print("")
    
    # Create interface
    interface = create_soc_terminal_interface()
    
    if len(sys.argv) > 1 and sys.argv[1] == "--config-only":
        # Just generate config file
        config_path = interface.write_opentui_config()
        print(f"📄 Configuration written to: {config_path}")
    else:
        # Launch full interface
        launch_script = interface.launch_terminal_interface()
        print("🚀 Ready to launch terminal interface!")