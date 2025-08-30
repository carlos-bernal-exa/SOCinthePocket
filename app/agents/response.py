"""
ResponseAgent - Propose containment and remediation actions
"""
import asyncio
from typing import Dict, Any, List, Optional
from .base import AgentBase
import logging
import json

logger = logging.getLogger(__name__)

class ResponseAgent(AgentBase):
    """
    Response Agent that proposes (and later executes) containment actions.
    Note: v1 only proposes actions, no destructive execution.
    """
    
    def __init__(self):
        super().__init__(
            name="ResponseAgent", 
            model="gemini-2.5-pro",
            role="response"
        )
    
    def _format_prompt(self, prompt_content: str, inputs: Dict[str, Any]) -> str:
        """Format response-specific prompt"""
        case_id = inputs.get("case_id", "unknown")
        attack_story = inputs.get("attack_story", {})
        ioc_set = inputs.get("ioc_set", {})
        mitre_mapping = inputs.get("mitre_mapping", {})
        
        formatted = f"""You are a SOC Response Agent generating containment and remediation recommendations for case {case_id}.

Your role is to:
1. Generate containment and remediation recommendations based on investigation findings
2. Propose specific actions like network isolation, account disabling, system quarantine
3. Prioritize responses by severity and impact
4. Do NOT execute actions - only propose them with detailed justification

Attack Story:
{json.dumps(attack_story, indent=2)}

IOCs Identified:
{json.dumps(ioc_set, indent=2)}

MITRE ATT&CK Mapping:
{json.dumps(mitre_mapping, indent=2)}

Available Containment Actions:
- isolate: Network isolation of compromised systems
- disable: Disable compromised user accounts
- quarantine: Quarantine infected files/systems
- block: Block malicious IPs/domains at firewall
- reset: Force password resets for affected accounts
- monitor: Enhanced monitoring for suspicious activity

Response Priorities:
- critical: Immediate action required (active breach)
- high: Action needed within 1 hour
- medium: Action needed within 4 hours  
- low: Action needed within 24 hours

Respond with structured recommendations including:
1. Immediate containment actions prioritized by urgency
2. Remediation steps to eliminate threats
3. Monitoring enhancements to prevent recurrence
4. Evidence preservation requirements

Format as JSON with fields:
- containment_actions: Immediate response actions
- remediation_steps: Long-term threat elimination
- monitoring_enhancements: Improved detection capabilities
- evidence_preservation: Actions to preserve forensic evidence
- priority_matrix: Actions sorted by urgency and impact"""

        return formatted
    
    def _prioritize_responses(self, ioc_set: Dict[str, List], attack_story: Dict) -> List[Dict]:
        """Prioritize response actions by severity and impact"""
        actions = []
        
        # Immediate containment based on IOCs
        if ioc_set.get("ips"):
            for ip in ioc_set["ips"]:
                if ip.startswith("192.168.") or ip.startswith("10."):
                    # Internal IP - high priority
                    actions.append({
                        "action": "isolate",
                        "target": ip,
                        "priority": "critical",
                        "justification": f"Internal IP {ip} showing malicious activity",
                        "urgency": "immediate",
                        "impact": "high"
                    })
                else:
                    # External IP - block at firewall
                    actions.append({
                        "action": "block",
                        "target": ip,
                        "priority": "high", 
                        "justification": f"Block external malicious IP {ip}",
                        "urgency": "1_hour",
                        "impact": "medium"
                    })
        
        # User account actions
        if ioc_set.get("users"):
            for user in ioc_set["users"]:
                actions.append({
                    "action": "disable",
                    "target": user,
                    "priority": "critical",
                    "justification": f"Disable compromised account {user}",
                    "urgency": "immediate", 
                    "impact": "high"
                })
                
                actions.append({
                    "action": "reset",
                    "target": f"{user}_password",
                    "priority": "high",
                    "justification": f"Force password reset for {user}",
                    "urgency": "1_hour",
                    "impact": "medium"
                })
        
        # Host containment
        if ioc_set.get("hosts"):
            for host in ioc_set["hosts"]:
                actions.append({
                    "action": "quarantine",
                    "target": host,
                    "priority": "critical",
                    "justification": f"Quarantine compromised system {host}",
                    "urgency": "immediate",
                    "impact": "high"
                })
        
        # Sort by priority
        priority_order = {"critical": 1, "high": 2, "medium": 3, "low": 4}
        actions.sort(key=lambda x: priority_order.get(x["priority"], 4))
        
        return actions
    
    def _generate_remediation_steps(self, attack_story: Dict, mitre_mapping: Dict) -> List[Dict]:
        """Generate long-term remediation steps"""
        steps = []
        
        # Based on MITRE tactics identified
        tactics = mitre_mapping.get("tactics", {})
        
        if "TA0001" in tactics:  # Initial Access
            steps.append({
                "step": "patch_vulnerabilities",
                "description": "Patch systems that allowed initial access",
                "timeline": "1_week",
                "priority": "high"
            })
        
        if "TA0002" in tactics:  # Execution
            steps.append({
                "step": "harden_execution_policies",
                "description": "Implement application whitelisting and PowerShell restrictions",
                "timeline": "2_weeks",
                "priority": "medium"
            })
        
        if "TA0008" in tactics:  # Lateral Movement
            steps.append({
                "step": "network_segmentation",
                "description": "Implement network segmentation to prevent lateral movement",
                "timeline": "1_month",
                "priority": "high"
            })
        
        # General remediation
        steps.extend([
            {
                "step": "update_detection_rules",
                "description": "Create detection rules for identified attack patterns",
                "timeline": "1_week",
                "priority": "high"
            },
            {
                "step": "security_awareness_training",
                "description": "Conduct targeted training for affected users",
                "timeline": "2_weeks", 
                "priority": "medium"
            }
        ])
        
        return steps
    
    def _generate_monitoring_enhancements(self, mitre_mapping: Dict, ioc_set: Dict) -> List[Dict]:
        """Generate monitoring enhancement recommendations"""
        enhancements = []
        
        # Based on techniques identified
        techniques = mitre_mapping.get("techniques", {})
        
        if "T1059.001" in techniques:  # PowerShell
            enhancements.append({
                "enhancement": "powershell_logging",
                "description": "Enable PowerShell script block logging and monitoring",
                "implementation": "Group Policy + SIEM rules",
                "priority": "high"
            })
        
        if "T1021" in techniques:  # Remote Services
            enhancements.append({
                "enhancement": "rdp_monitoring", 
                "description": "Enhanced monitoring of RDP and remote access",
                "implementation": "Windows Event Log collection + alerting",
                "priority": "medium"
            })
        
        # IOC-based monitoring
        if ioc_set.get("ips"):
            enhancements.append({
                "enhancement": "ip_reputation_monitoring",
                "description": "Implement IP reputation checking and alerting",
                "implementation": "Threat intelligence feeds + firewall integration",
                "priority": "medium"
            })
        
        return enhancements
    
    async def process(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Process response generation logic"""
        try:
            case_id = inputs.get("case_id")
            attack_story = inputs.get("attack_story", {})
            ioc_set = inputs.get("ioc_set", {})
            mitre_mapping = inputs.get("mitre_mapping", {})
            
            # Generate prioritized containment actions
            containment_actions = self._prioritize_responses(ioc_set, attack_story)
            
            # Generate remediation steps
            remediation_steps = self._generate_remediation_steps(attack_story, mitre_mapping)
            
            # Generate monitoring enhancements
            monitoring_enhancements = self._generate_monitoring_enhancements(mitre_mapping, ioc_set)
            
            # Evidence preservation requirements
            evidence_preservation = self._define_evidence_preservation(ioc_set, attack_story)
            
            return {
                "containment_actions": containment_actions,
                "remediation_steps": remediation_steps,
                "monitoring_enhancements": monitoring_enhancements,
                "evidence_preservation": evidence_preservation,
                "priority_matrix": self._create_priority_matrix(containment_actions),
                "response_summary": {
                    "immediate_actions": len([a for a in containment_actions if a["urgency"] == "immediate"]),
                    "total_recommendations": len(containment_actions) + len(remediation_steps),
                    "estimated_implementation_time": "2-4 hours for containment, 2-4 weeks for full remediation"
                }
            }
            
        except Exception as e:
            logger.error(f"Response processing failed: {e}")
            return {
                "error": f"Response processing failed: {str(e)}",
                "containment_actions": [],
                "remediation_steps": [],
                "monitoring_enhancements": []
            }
    
    def _define_evidence_preservation(self, ioc_set: Dict, attack_story: Dict) -> List[Dict]:
        """Define evidence preservation requirements"""
        preservation_actions = []
        
        # Preserve system images
        if ioc_set.get("hosts"):
            for host in ioc_set["hosts"]:
                preservation_actions.append({
                    "action": "create_system_image",
                    "target": host,
                    "justification": f"Preserve forensic image of compromised system {host}",
                    "retention": "90_days",
                    "priority": "high"
                })
        
        # Preserve network logs
        preservation_actions.append({
            "action": "preserve_network_logs",
            "target": "firewall_and_proxy_logs",
            "justification": "Preserve network traffic logs for attack timeframe",
            "retention": "180_days",
            "priority": "medium"
        })
        
        # Preserve memory dumps
        if attack_story.get("sophistication") == "advanced":
            preservation_actions.append({
                "action": "memory_dump",
                "target": "all_compromised_systems",
                "justification": "Capture memory for advanced threat analysis",
                "retention": "30_days",
                "priority": "high"
            })
        
        return preservation_actions
    
    def _create_priority_matrix(self, actions: List[Dict]) -> Dict[str, List[Dict]]:
        """Create priority matrix organizing actions by urgency and impact"""
        matrix = {
            "immediate_critical": [],
            "immediate_high": [],
            "hour_critical": [],
            "hour_high": [],
            "day_medium": []
        }
        
        for action in actions:
            urgency = action.get("urgency", "day")
            impact = action.get("impact", "medium")
            
            key = f"{urgency}_{impact}"
            if key in matrix:
                matrix[key].append(action)
            else:
                matrix["day_medium"].append(action)
        
        return matrix