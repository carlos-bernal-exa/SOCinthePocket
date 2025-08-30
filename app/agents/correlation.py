"""
CorrelationAgent - Correlate across cases and build attack stories
"""
import asyncio
from typing import Dict, Any, List, Optional
from .base import AgentBase
import logging
import json

logger = logging.getLogger(__name__)

class CorrelationAgent(AgentBase):
    """
    Correlation Agent that correlates across cases, builds attack stories, 
    and maps findings to MITRE ATT&CK framework.
    """
    
    def __init__(self):
        super().__init__(
            name="CorrelationAgent", 
            model="gemini-2.5-pro",
            role="correlation"
        )
    
    def _format_prompt(self, prompt_content: str, inputs: Dict[str, Any]) -> str:
        """Format correlation-specific prompt"""
        case_id = inputs.get("case_id", "unknown")
        timeline_events = inputs.get("timeline_events", [])
        ioc_set = inputs.get("ioc_set", {})
        attack_patterns = inputs.get("attack_patterns", [])
        
        formatted = f"""You are a SOC Correlation Agent building comprehensive attack stories for case {case_id}.

Your role is to:
1. Correlate multiple cases and investigation results
2. Build comprehensive attack stories with kill chain progression
3. Map findings to MITRE ATT&CK framework tactics and techniques
4. Identify potential threat actor TTPs (Tactics, Techniques, Procedures)

Timeline Events:
{json.dumps(timeline_events, indent=2)}

IOC Set:
{json.dumps(ioc_set, indent=2)}

Attack Patterns Identified:
{json.dumps(attack_patterns, indent=2)}

MITRE ATT&CK Mapping Requirements:
- Map each attack pattern to specific tactics (TA####)
- Identify techniques (T####) and sub-techniques (T####.###)
- Build kill chain progression showing attack sequence
- Assess threat actor sophistication level
- Identify gaps in detection coverage

Respond with comprehensive analysis including:
1. Attack story narrative with chronological progression
2. MITRE ATT&CK mapping for all identified activities
3. Threat actor profiling and TTP analysis
4. Kill chain reconstruction
5. Detection gap analysis

Format as JSON with fields:
- attack_story: Narrative description of the attack
- mitre_mapping: Tactics and techniques identified
- kill_chain: Chronological attack progression
- threat_actor_profile: TTP analysis and sophistication assessment
- detection_gaps: Areas lacking visibility
- confidence_assessment: Analysis confidence levels"""

        return formatted
    
    def _build_attack_story(self, timeline: List[Dict], patterns: List[Dict]) -> Dict[str, Any]:
        """Build comprehensive attack story from timeline and patterns"""
        
        # Group events by phase
        phases = {
            "initial_access": [],
            "execution": [],
            "persistence": [],
            "privilege_escalation": [],
            "defense_evasion": [],
            "credential_access": [],
            "discovery": [],
            "lateral_movement": [],
            "collection": [],
            "exfiltration": [],
            "impact": []
        }
        
        # Classify events into attack phases
        for event in timeline:
            event_type = event.get("event", "")
            details = event.get("details", {})
            
            if event_type == "user_logon":
                phases["initial_access"].append(event)
            elif event_type == "process_execution":
                if "powershell" in str(details).lower():
                    phases["execution"].append(event)
                    phases["defense_evasion"].append(event)
            elif event_type == "network_connection":
                phases["lateral_movement"].append(event)
        
        # Build narrative
        story_phases = []
        for phase, events in phases.items():
            if events:
                story_phases.append({
                    "phase": phase,
                    "event_count": len(events),
                    "timespan": {
                        "start": min(e["timestamp"] for e in events),
                        "end": max(e["timestamp"] for e in events)
                    },
                    "description": self._describe_phase(phase, events)
                })
        
        return {
            "narrative": self._create_narrative(story_phases),
            "phases": story_phases,
            "duration_minutes": self._calculate_attack_duration(timeline),
            "sophistication": self._assess_sophistication(patterns, timeline)
        }
    
    def _describe_phase(self, phase: str, events: List[Dict]) -> str:
        """Generate description for attack phase"""
        descriptions = {
            "initial_access": f"Attacker gained initial access through {len(events)} logon events",
            "execution": f"Executed {len(events)} processes, including PowerShell",
            "lateral_movement": f"Attempted lateral movement via {len(events)} network connections",
            "defense_evasion": f"Used {len(events)} evasion techniques"
        }
        return descriptions.get(phase, f"Phase involved {len(events)} events")
    
    def _create_narrative(self, phases: List[Dict]) -> str:
        """Create attack story narrative"""
        if not phases:
            return "No significant attack progression identified."
        
        narrative = "Attack progression analysis:\n"
        for i, phase in enumerate(phases, 1):
            narrative += f"{i}. {phase['phase'].replace('_', ' ').title()}: {phase['description']}\n"
        
        return narrative
    
    def _map_to_mitre(self, patterns: List[Dict], timeline: List[Dict]) -> Dict[str, Any]:
        """Map findings to MITRE ATT&CK framework"""
        tactics = {}
        techniques = {}
        
        # Map from attack patterns
        for pattern in patterns:
            tactic_id = pattern.get("mitre_tactic")
            if tactic_id:
                tactics[tactic_id] = {
                    "name": self._get_tactic_name(tactic_id),
                    "confidence": pattern.get("confidence", 0.5),
                    "evidence": pattern.get("evidence", "")
                }
        
        # Map specific techniques from timeline
        for event in timeline:
            event_type = event.get("event", "")
            details = event.get("details", {})
            
            if event_type == "process_execution" and "powershell" in str(details).lower():
                techniques["T1059.001"] = {
                    "name": "PowerShell",
                    "tactic": "TA0002",  # Execution
                    "confidence": 0.9,
                    "evidence": f"PowerShell execution detected: {details.get('command_line', '')[:50]}..."
                }
            
            if event_type == "network_connection":
                techniques["T1021"] = {
                    "name": "Remote Services",
                    "tactic": "TA0008",  # Lateral Movement
                    "confidence": 0.7,
                    "evidence": f"Network connection: {details.get('src_ip')} -> {details.get('dst_ip')}"
                }
        
        return {
            "tactics": tactics,
            "techniques": techniques,
            "kill_chain": self._build_kill_chain(tactics, techniques)
        }
    
    def _get_tactic_name(self, tactic_id: str) -> str:
        """Get MITRE tactic name from ID"""
        tactic_names = {
            "TA0001": "Initial Access",
            "TA0002": "Execution", 
            "TA0003": "Persistence",
            "TA0004": "Privilege Escalation",
            "TA0005": "Defense Evasion",
            "TA0006": "Credential Access",
            "TA0007": "Discovery",
            "TA0008": "Lateral Movement",
            "TA0009": "Collection",
            "TA0010": "Exfiltration",
            "TA0011": "Command and Control",
            "TA0040": "Impact"
        }
        return tactic_names.get(tactic_id, "Unknown Tactic")
    
    def _build_kill_chain(self, tactics: Dict, techniques: Dict) -> List[Dict]:
        """Build kill chain progression"""
        # Order tactics by typical progression
        tactic_order = ["TA0001", "TA0002", "TA0004", "TA0005", "TA0008", "TA0011", "TA0010", "TA0040"]
        
        kill_chain = []
        for tactic_id in tactic_order:
            if tactic_id in tactics:
                # Find techniques for this tactic
                tactic_techniques = [
                    {"id": tid, **tdata} for tid, tdata in techniques.items() 
                    if tdata.get("tactic") == tactic_id
                ]
                
                kill_chain.append({
                    "tactic": tactics[tactic_id],
                    "tactic_id": tactic_id,
                    "techniques": tactic_techniques
                })
        
        return kill_chain
    
    def _calculate_attack_duration(self, timeline: List[Dict]) -> int:
        """Calculate attack duration in minutes"""
        if len(timeline) < 2:
            return 0
        
        start_time = min(event["timestamp"] for event in timeline)
        end_time = max(event["timestamp"] for event in timeline)
        
        from datetime import datetime
        start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
        
        return int((end_dt - start_dt).total_seconds() / 60)
    
    def _assess_sophistication(self, patterns: List[Dict], timeline: List[Dict]) -> str:
        """Assess threat actor sophistication level"""
        sophistication_score = 0
        
        # Check for advanced patterns
        for pattern in patterns:
            if pattern.get("pattern") == "lateral_movement":
                sophistication_score += 2
            elif pattern.get("pattern") == "privilege_escalation":
                sophistication_score += 3
        
        # Check for evasion techniques
        powershell_events = [e for e in timeline if "powershell" in str(e.get("details", {})).lower()]
        if powershell_events:
            sophistication_score += 2
        
        if sophistication_score >= 5:
            return "advanced"
        elif sophistication_score >= 3:
            return "intermediate"
        else:
            return "basic"
    
    async def process(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Process correlation logic"""
        try:
            case_id = inputs.get("case_id")
            timeline_events = inputs.get("timeline_events", [])
            ioc_set = inputs.get("ioc_set", {})
            attack_patterns = inputs.get("attack_patterns", [])
            
            # Build attack story
            attack_story = self._build_attack_story(timeline_events, attack_patterns)
            
            # Map to MITRE ATT&CK
            mitre_mapping = self._map_to_mitre(attack_patterns, timeline_events)
            
            # Assess threat actor profile
            threat_actor_profile = {
                "sophistication": attack_story["sophistication"],
                "ttps": self._extract_ttps(attack_patterns, timeline_events),
                "infrastructure": self._analyze_infrastructure(ioc_set),
                "targeting": self._assess_targeting(timeline_events)
            }
            
            return {
                "attack_story": attack_story,
                "mitre_mapping": mitre_mapping,
                "kill_chain": mitre_mapping["kill_chain"],
                "threat_actor_profile": threat_actor_profile,
                "detection_gaps": self._identify_detection_gaps(mitre_mapping),
                "confidence_assessment": {
                    "attack_story": 0.85,
                    "mitre_mapping": 0.9,
                    "threat_profiling": 0.7
                }
            }
            
        except Exception as e:
            logger.error(f"Correlation processing failed: {e}")
            return {
                "error": f"Correlation processing failed: {str(e)}",
                "attack_story": {},
                "mitre_mapping": {},
                "threat_actor_profile": {}
            }
    
    def _extract_ttps(self, patterns: List[Dict], timeline: List[Dict]) -> List[Dict]:
        """Extract threat actor TTPs"""
        ttps = []
        
        for pattern in patterns:
            ttp = {
                "type": pattern.get("pattern", "unknown"),
                "confidence": pattern.get("confidence", 0.5),
                "evidence_count": 1,
                "first_seen": timeline[0]["timestamp"] if timeline else None
            }
            ttps.append(ttp)
        
        return ttps
    
    def _analyze_infrastructure(self, ioc_set: Dict[str, List]) -> Dict[str, Any]:
        """Analyze threat actor infrastructure"""
        return {
            "ip_count": len(ioc_set.get("ips", [])),
            "domain_count": len(ioc_set.get("domains", [])),
            "infrastructure_type": "mixed" if len(ioc_set.get("ips", [])) > 2 else "simple",
            "geographic_distribution": "unknown"
        }
    
    def _assess_targeting(self, timeline: List[Dict]) -> Dict[str, Any]:
        """Assess targeting patterns"""
        users = set()
        hosts = set()
        
        for event in timeline:
            details = event.get("details", {})
            if "user" in details:
                users.add(details["user"])
            if "computer" in details:
                hosts.add(details["computer"])
        
        return {
            "targeted_users": len(users),
            "targeted_hosts": len(hosts),
            "targeting_pattern": "focused" if len(users) <= 2 else "broad"
        }
    
    def _identify_detection_gaps(self, mitre_mapping: Dict[str, Any]) -> List[Dict]:
        """Identify gaps in detection coverage"""
        gaps = []
        
        # Check for common tactics not covered
        common_tactics = ["TA0001", "TA0002", "TA0003", "TA0004", "TA0008"]
        covered_tactics = set(mitre_mapping.get("tactics", {}).keys())
        
        for tactic_id in common_tactics:
            if tactic_id not in covered_tactics:
                gaps.append({
                    "tactic": tactic_id,
                    "name": self._get_tactic_name(tactic_id),
                    "reason": "No detection coverage identified",
                    "risk_level": "medium"
                })
        
        return gaps
    
    def _get_tactic_name(self, tactic_id: str) -> str:
        """Get MITRE tactic name from ID"""
        tactic_names = {
            "TA0001": "Initial Access",
            "TA0002": "Execution", 
            "TA0003": "Persistence",
            "TA0004": "Privilege Escalation",
            "TA0005": "Defense Evasion",
            "TA0006": "Credential Access",
            "TA0007": "Discovery",
            "TA0008": "Lateral Movement",
            "TA0009": "Collection",
            "TA0010": "Exfiltration",
            "TA0011": "Command and Control",
            "TA0040": "Impact"
        }
        return tactic_names.get(tactic_id, "Unknown Tactic")