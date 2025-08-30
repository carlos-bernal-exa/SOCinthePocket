"""
ReportingAgent - Generate comprehensive incident reports
"""
import asyncio
from typing import Dict, Any, List, Optional
from .base import AgentBase
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class ReportingAgent(AgentBase):
    """
    Reporting Agent that produces incident reports with citations,
    executive summaries, technical details, and recommendations.
    """
    
    def __init__(self):
        super().__init__(
            name="ReportingAgent", 
            model="gemini-2.5-pro",
            role="reporting"
        )
    
    def _format_prompt(self, prompt_content: str, inputs: Dict[str, Any]) -> str:
        """Format reporting-specific prompt"""
        case_id = inputs.get("case_id", "unknown")
        attack_story = inputs.get("attack_story", {})
        containment_actions = inputs.get("containment_actions", [])
        ioc_set = inputs.get("ioc_set", {})
        
        formatted = f"""You are a SOC Reporting Agent generating comprehensive incident reports for case {case_id}.

Your role is to:
1. Generate executive summaries suitable for management
2. Provide detailed technical analysis with proper citations
3. Create actionable timelines and IOC lists
4. Include specific recommendations aligned to incident response standards

Case Analysis Results:
Attack Story: {json.dumps(attack_story, indent=2)}
Containment Actions: {json.dumps(containment_actions, indent=2)}
IOCs: {json.dumps(ioc_set, indent=2)}

Report Requirements:
- Professional formatting suitable for incident response documentation
- Executive summary (2-3 paragraphs, non-technical language)
- Technical analysis with evidence citations
- Chronological timeline of events
- Complete IOC list with context
- Actionable recommendations with priorities
- Compliance considerations (NIST, SANS frameworks)

Structure your report with these sections:
1. Executive Summary
2. Incident Timeline  
3. Technical Analysis
4. Indicators of Compromise
5. Recommendations
6. Lessons Learned

Include proper citations to source data and maintain professional tone throughout."""

        return formatted
    
    def _generate_executive_summary(self, case_id: str, attack_story: Dict, containment_actions: List[Dict]) -> str:
        """Generate executive summary for management"""
        severity = self._assess_incident_severity(attack_story, containment_actions)
        impact = self._assess_business_impact(attack_story, containment_actions)
        
        summary = f"""## Executive Summary

**Incident ID:** {case_id}
**Severity:** {severity.upper()}
**Business Impact:** {impact}
**Status:** Under Investigation

On {datetime.now().strftime('%B %d, %Y')}, our SOC platform detected and analyzed a security incident involving {attack_story.get('sophistication', 'unknown')} threat actor activity. The incident has been contained with {len([a for a in containment_actions if a.get('urgency') == 'immediate'])} immediate containment actions implemented.

**Key Findings:**
- Attack duration: {attack_story.get('duration_minutes', 0)} minutes
- Systems affected: {len(attack_story.get('phases', []))} attack phases identified
- Immediate actions: {len([a for a in containment_actions if a.get('priority') == 'critical'])} critical containment measures

**Current Status:**
All immediate threats have been contained. Remediation efforts are underway with estimated completion in 2-4 weeks. No evidence of data exfiltration or system compromise beyond the identified scope."""
        
        return summary
    
    def _assess_incident_severity(self, attack_story: Dict, containment_actions: List[Dict]) -> str:
        """Assess overall incident severity"""
        sophistication = attack_story.get("sophistication", "basic")
        critical_actions = len([a for a in containment_actions if a.get("priority") == "critical"])
        
        if sophistication == "advanced" and critical_actions >= 3:
            return "critical"
        elif sophistication == "intermediate" or critical_actions >= 2:
            return "high"
        elif critical_actions >= 1:
            return "medium"
        else:
            return "low"
    
    def _assess_business_impact(self, attack_story: Dict, containment_actions: List[Dict]) -> str:
        """Assess business impact"""
        phases = len(attack_story.get("phases", []))
        duration = attack_story.get("duration_minutes", 0)
        
        if phases >= 4 and duration > 60:
            return "High - Multi-phase attack with extended timeline"
        elif phases >= 2 or duration > 30:
            return "Medium - Limited scope with contained timeline"
        else:
            return "Low - Minimal scope and brief duration"
    
    def _create_incident_timeline(self, timeline_events: List[Dict], attack_story: Dict) -> str:
        """Create formatted incident timeline"""
        if not timeline_events:
            return "## Incident Timeline\n\nNo timeline events available."
        
        timeline_md = "## Incident Timeline\n\n"
        
        for event in timeline_events:
            timestamp = event.get("timestamp", "Unknown")
            actor = event.get("actor", "Unknown")
            event_type = event.get("event", "Unknown")
            source = event.get("source", "Unknown")
            
            timeline_md += f"**{timestamp}** - {event_type.replace('_', ' ').title()}\n"
            timeline_md += f"- Actor: {actor}\n"
            timeline_md += f"- Source: {source}\n"
            timeline_md += f"- Details: {self._format_event_details(event.get('details', {}))}\n\n"
        
        return timeline_md
    
    def _format_event_details(self, details: Dict) -> str:
        """Format event details for report"""
        if not details:
            return "No additional details"
        
        formatted = []
        for key, value in details.items():
            if key in ["src_ip", "dst_ip", "user", "process", "event_id"]:
                formatted.append(f"{key}: {value}")
        
        return ", ".join(formatted) if formatted else "Standard security event"
    
    def _create_ioc_section(self, ioc_set: Dict[str, List]) -> str:
        """Create IOC section for report"""
        ioc_md = "## Indicators of Compromise\n\n"
        
        for ioc_type, values in ioc_set.items():
            if values:
                ioc_md += f"### {ioc_type.upper()}\n"
                for value in values:
                    ioc_md += f"- `{value}`\n"
                ioc_md += "\n"
        
        if not any(ioc_set.values()):
            ioc_md += "No specific IOCs identified in this analysis.\n"
        
        return ioc_md
    
    def _create_recommendations_section(self, containment_actions: List[Dict], remediation_steps: List[Dict]) -> str:
        """Create recommendations section"""
        rec_md = "## Recommendations\n\n"
        
        # Immediate actions
        if containment_actions:
            rec_md += "### Immediate Actions\n"
            critical_actions = [a for a in containment_actions if a.get("priority") == "critical"]
            for action in critical_actions[:5]:  # Top 5 critical
                rec_md += f"- **{action['action'].title()}** {action['target']}: {action['justification']}\n"
            rec_md += "\n"
        
        # Remediation steps
        if remediation_steps:
            rec_md += "### Long-term Remediation\n"
            for step in remediation_steps[:5]:  # Top 5 steps
                rec_md += f"- **{step['step'].replace('_', ' ').title()}**: {step['description']} (Timeline: {step['timeline']})\n"
            rec_md += "\n"
        
        return rec_md
    
    async def process(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Process reporting logic"""
        try:
            case_id = inputs.get("case_id")
            attack_story = inputs.get("attack_story", {})
            containment_actions = inputs.get("containment_actions", [])
            remediation_steps = inputs.get("remediation_steps", [])
            timeline_events = inputs.get("timeline_events", [])
            ioc_set = inputs.get("ioc_set", {})
            mitre_mapping = inputs.get("mitre_mapping", {})
            
            # Generate report sections
            executive_summary = self._generate_executive_summary(case_id, attack_story, containment_actions)
            incident_timeline = self._create_incident_timeline(timeline_events, attack_story)
            technical_analysis = self._create_technical_analysis(attack_story, mitre_mapping)
            ioc_section = self._create_ioc_section(ioc_set)
            recommendations = self._create_recommendations_section(containment_actions, remediation_steps)
            lessons_learned = self._create_lessons_learned(attack_story, mitre_mapping)
            
            # Compile full report
            full_report = f"""{executive_summary}

{incident_timeline}

{technical_analysis}

{ioc_section}

{recommendations}

{lessons_learned}

---
**Report Generated:** {datetime.now().isoformat()}
**Analyst:** SOC Platform Automated Analysis
**Case ID:** {case_id}"""

            return {
                "incident_report": full_report,
                "executive_summary": executive_summary,
                "technical_analysis": technical_analysis,
                "timeline": incident_timeline,
                "iocs": ioc_section,
                "recommendations": recommendations,
                "report_metadata": {
                    "case_id": case_id,
                    "generated_at": datetime.now().isoformat(),
                    "report_version": "1.0",
                    "sections": 6,
                    "total_length_chars": len(full_report)
                }
            }
            
        except Exception as e:
            logger.error(f"Reporting processing failed: {e}")
            return {
                "error": f"Reporting processing failed: {str(e)}",
                "incident_report": "",
                "report_metadata": {}
            }
    
    def _create_technical_analysis(self, attack_story: Dict, mitre_mapping: Dict) -> str:
        """Create technical analysis section"""
        tech_md = "## Technical Analysis\n\n"
        
        # Attack sophistication
        sophistication = attack_story.get("sophistication", "unknown")
        tech_md += f"**Attack Sophistication:** {sophistication.title()}\n\n"
        
        # MITRE ATT&CK mapping
        tactics = mitre_mapping.get("tactics", {})
        if tactics:
            tech_md += "**MITRE ATT&CK Tactics Identified:**\n"
            for tactic_id, tactic_data in tactics.items():
                tech_md += f"- {tactic_id}: {tactic_data.get('name', 'Unknown')} (Confidence: {tactic_data.get('confidence', 0)*100:.0f}%)\n"
            tech_md += "\n"
        
        # Attack phases
        phases = attack_story.get("phases", [])
        if phases:
            tech_md += "**Attack Phases:**\n"
            for phase in phases:
                tech_md += f"- {phase['phase'].replace('_', ' ').title()}: {phase['description']}\n"
            tech_md += "\n"
        
        return tech_md
    
    def _create_lessons_learned(self, attack_story: Dict, mitre_mapping: Dict) -> str:
        """Create lessons learned section"""
        lessons_md = "## Lessons Learned\n\n"
        
        # Detection gaps
        gaps = []
        tactics = mitre_mapping.get("tactics", {})
        if len(tactics) < 3:
            gaps.append("Limited tactic coverage suggests detection gaps")
        
        sophistication = attack_story.get("sophistication", "basic")
        if sophistication == "advanced":
            gaps.append("Advanced threat actor suggests need for enhanced detection capabilities")
        
        if gaps:
            lessons_md += "**Areas for Improvement:**\n"
            for gap in gaps:
                lessons_md += f"- {gap}\n"
            lessons_md += "\n"
        
        lessons_md += "**Positive Outcomes:**\n"
        lessons_md += "- Automated detection and analysis successfully identified the threat\n"
        lessons_md += "- Comprehensive audit trail maintained throughout investigation\n"
        lessons_md += "- Rapid containment actions proposed and implemented\n"
        
        return lessons_md