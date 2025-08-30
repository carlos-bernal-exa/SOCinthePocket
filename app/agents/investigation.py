"""
InvestigationAgent - Execute SIEM queries and build timeline
"""
import asyncio
from typing import Dict, Any, List, Optional
from .base import AgentBase
from ..adapters.siem import siem_client
import logging
import json
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class InvestigationAgent(AgentBase):
    """
    Investigation Agent that executes search_query in SIEM, 
    builds timeline, and extracts IOC set.
    """
    
    def __init__(self):
        super().__init__(
            name="InvestigationAgent", 
            model="gemini-2.5-flash",
            role="investigation"
        )
    
    def _format_prompt(self, prompt_content: str, inputs: Dict[str, Any]) -> str:
        """Format investigation-specific prompt"""
        case_id = inputs.get("case_id", "unknown")
        kept_cases = inputs.get("kept_cases", [])
        entities = inputs.get("entities", [])
        
        formatted = f"""You are a SOC Investigation Agent conducting deep analysis for case {case_id}.

Your role is to:
1. Execute search queries against the SIEM for eligible detection rules
2. Build detailed timelines from log data
3. Extract comprehensive IOCs (Indicators of Compromise)
4. Correlate events and identify attack patterns

Eligible Cases for SIEM Query (fact*/profile* rules only):
{json.dumps(kept_cases, indent=2)}

Entities to investigate:
{json.dumps(entities, indent=2)}

SIEM Query Rules:
- Only process cases with fact* or profile* rule types
- Build timeline with proper event sequencing
- Extract IOCs: IPs, domains, hashes, emails, URLs
- Correlate events within 24-hour window
- Focus on lateral movement and privilege escalation indicators

Respond with structured analysis including:
1. SIEM query results and raw log analysis
2. Chronological timeline of events
3. Comprehensive IOC extraction
4. Event correlation findings
5. Attack pattern identification

Format as JSON with fields:
- siem_results: Query results from eligible cases
- timeline_events: Chronological event sequence
- ioc_set: Categorized indicators of compromise
- correlation_findings: Related events and patterns
- attack_patterns: Identified tactics and techniques
- confidence_scores: Analysis confidence levels"""

        return formatted
    
    async def _execute_siem_queries(self, kept_cases: List[Dict]) -> List[Dict]:
        """Execute SIEM queries for eligible cases using real SIEM client"""
        siem_results = []
        
        for case in kept_cases:
            try:
                case_id = case["case_id"]
                detection_rule = case.get("raw_data", {}).get("detection_rule", "")
                
                # Build SIEM query from case data
                query_filter = self._build_siem_query(case)
                
                # Set time range for query (last 24 hours)
                end_time = datetime.now().isoformat() + "Z"
                start_time = (datetime.now() - timedelta(hours=24)).isoformat() + "Z"
                
                # Execute query with real SIEM client
                query_start_time = datetime.now()
                siem_response = await siem_client.query(
                    event_filter=query_filter,
                    start=start_time,
                    end=end_time,
                    limit=100
                )
                query_duration = (datetime.now() - query_start_time).total_seconds() * 1000
                
                # Format results
                query_result = {
                    "case_id": case_id,
                    "detection_rule": detection_rule,
                    "query_executed": True,
                    "query_filter": query_filter,
                    "events_found": siem_response.get("count", 0),
                    "query_duration_ms": int(query_duration),
                    "raw_events": siem_response.get("events", [])
                }
                
                siem_results.append(query_result)
                logger.info(f"SIEM query executed for case {case_id}: {query_result['events_found']} events in {query_duration:.1f}ms")
                
            except Exception as e:
                logger.error(f"SIEM query failed for case {case_id}: {e}")
                # Add error result
                siem_results.append({
                    "case_id": case_id,
                    "detection_rule": detection_rule,
                    "query_executed": False,
                    "error": str(e),
                    "events_found": 0,
                    "query_duration_ms": 0,
                    "raw_events": []
                })
        
        return siem_results
    
    def _build_siem_query(self, case: Dict) -> str:
        """Build SIEM query from case data"""
        raw_data = case.get("raw_data", {})
        entities = raw_data.get("entities", [])
        
        # Start with basic query terms
        query_terms = []
        
        # Add entity-based filters
        for entity in entities:
            entity_type = entity.get("type", "")
            entity_value = entity.get("value", "")
            
            if entity_type == "ip" and entity_value:
                query_terms.append(f'src_ip="{entity_value}" OR dst_ip="{entity_value}"')
            elif entity_type == "user" and entity_value:
                query_terms.append(f'user="{entity_value}"')
            elif entity_type == "domain" and entity_value:
                query_terms.append(f'domain="{entity_value}" OR url="*{entity_value}*"')
            elif entity_type == "hash" and entity_value:
                query_terms.append(f'hash="{entity_value}"')
        
        # Add detection rule context
        detection_rule = raw_data.get("detection_rule", "")
        if detection_rule:
            # Extract key terms from rule name for context
            rule_terms = detection_rule.replace("_", " ").split()
            for term in rule_terms:
                if len(term) > 3 and term not in ["fact", "profile", "rule"]:
                    query_terms.append(f'*{term}*')
        
        # Build final query
        if query_terms:
            query = f"({') OR ('.join(query_terms)})"
        else:
            # Fallback query for cases without specific entities
            query = "*security* OR *logon* OR *network*"
        
        return query
    
    def _build_timeline(self, siem_results: List[Dict]) -> List[Dict]:
        """Build chronological timeline from SIEM results"""
        all_events = []
        
        for result in siem_results:
            for event in result.get("raw_events", []):
                # TimelineEvent following data contract: ts, actor?, event, src, details{}
                timeline_event = {
                    "ts": event["timestamp"],
                    "actor": event.get("user", event.get("src_ip", None)),
                    "event": self._classify_event(event),
                    "src": event["source"],
                    "details": event
                }
                all_events.append(timeline_event)
        
        # Sort by timestamp
        all_events.sort(key=lambda x: x["ts"])
        
        logger.info(f"Built timeline with {len(all_events)} events")
        return all_events
    
    def _classify_event(self, event: Dict) -> str:
        """Classify event type for timeline"""
        source = event.get("source", "")
        
        if "security" in source and event.get("event_id") == 4624:
            return "user_logon"
        elif source == "firewall":
            return "network_connection"
        elif "endpoint" in source and "process" in event:
            return "process_execution"
        else:
            return "security_event"
    
    def _extract_iocs(self, siem_results: List[Dict]) -> Dict[str, List[str]]:
        """Extract IOCs from SIEM results following IOCSet data contract: ips[], users[], hosts[], domains[], hashes[]"""
        iocs = {
            "ips": set(),
            "users": set(), 
            "hosts": set(),
            "domains": set(),
            "hashes": set()
        }
        
        for result in siem_results:
            for event in result.get("raw_events", []):
                # Extract IPs
                if "src_ip" in event:
                    iocs["ips"].add(event["src_ip"])
                if "dst_ip" in event:
                    iocs["ips"].add(event["dst_ip"])
                
                # Extract users
                if "user" in event:
                    iocs["users"].add(event["user"])
                
                # Extract hosts
                if "computer" in event:
                    iocs["hosts"].add(event["computer"])
                
                # Extract domains (from URLs, emails, etc.)
                if "domain" in event:
                    iocs["domains"].add(event["domain"])
                
                # Extract hashes
                if "hash" in event:
                    iocs["hashes"].add(event["hash"])
        
        # Convert sets to lists
        ioc_set = {key: list(values) for key, values in iocs.items()}
        
        total_iocs = sum(len(values) for values in ioc_set.values())
        logger.info(f"Extracted {total_iocs} total IOCs")
        
        return ioc_set
    
    def _correlate_events(self, timeline: List[Dict]) -> List[Dict]:
        """Correlate events within 24-hour window"""
        correlations = []
        
        for i, event1 in enumerate(timeline):
            for event2 in timeline[i+1:]:
                # Check if events are within correlation window
                time1 = datetime.fromisoformat(event1["ts"].replace("Z", "+00:00"))
                time2 = datetime.fromisoformat(event2["ts"].replace("Z", "+00:00"))
                
                if abs((time2 - time1).total_seconds()) <= 86400:  # 24 hours
                    # Check for correlations
                    correlation = self._find_correlation(event1, event2)
                    if correlation:
                        correlations.append(correlation)
        
        logger.info(f"Found {len(correlations)} event correlations")
        return correlations
    
    def _find_correlation(self, event1: Dict, event2: Dict) -> Optional[Dict]:
        """Find correlation between two events"""
        # Same actor correlation
        if event1.get("actor") == event2.get("actor"):
            return {
                "type": "same_actor",
                "event1": event1["ts"],
                "event2": event2["ts"], 
                "actor": event1["actor"],
                "confidence": 0.8
            }
        
        # IP correlation
        event1_details = event1.get("details", {})
        event2_details = event2.get("details", {})
        
        if (event1_details.get("src_ip") == event2_details.get("src_ip") or
            event1_details.get("dst_ip") == event2_details.get("dst_ip")):
            return {
                "type": "ip_correlation",
                "event1": event1["ts"],
                "event2": event2["ts"],
                "ip": event1_details.get("src_ip") or event1_details.get("dst_ip"),
                "confidence": 0.7
            }
        
        return None
    
    async def process(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Process investigation logic"""
        try:
            case_id = inputs.get("case_id")
            kept_cases = inputs.get("kept_cases", [])
            entities = inputs.get("entities", [])
            
            # Execute SIEM queries only for eligible cases
            siem_results = await self._execute_siem_queries(kept_cases)
            
            # Build timeline from results
            timeline_events = self._build_timeline(siem_results)
            
            # Extract IOCs
            ioc_set = self._extract_iocs(siem_results)
            
            # Correlate events
            correlation_findings = self._correlate_events(timeline_events)
            
            # Identify attack patterns
            attack_patterns = self._identify_attack_patterns(timeline_events, ioc_set)
            
            return {
                "siem_results": siem_results,
                "timeline_events": timeline_events,
                "ioc_set": ioc_set,
                "correlation_findings": correlation_findings,
                "attack_patterns": attack_patterns,
                "confidence_scores": {
                    "timeline_accuracy": 0.9,
                    "ioc_completeness": 0.85,
                    "correlation_confidence": 0.8
                },
                "investigation_summary": {
                    "cases_investigated": len(kept_cases),
                    "events_analyzed": len(timeline_events),
                    "iocs_extracted": sum(len(v) for v in ioc_set.values()),
                    "correlations_found": len(correlation_findings)
                }
            }
            
        except Exception as e:
            logger.error(f"Investigation processing failed: {e}")
            return {
                "error": f"Investigation processing failed: {str(e)}",
                "siem_results": [],
                "timeline_events": [],
                "ioc_set": {},
                "correlation_findings": []
            }
    
    def _identify_attack_patterns(self, timeline: List[Dict], iocs: Dict[str, List]) -> List[Dict]:
        """Identify attack patterns from timeline and IOCs"""
        patterns = []
        
        # Pattern 1: Lateral movement
        if len(iocs.get("ips", [])) > 1 and len(iocs.get("hosts", [])) > 1:
            patterns.append({
                "pattern": "lateral_movement",
                "confidence": 0.8,
                "evidence": f"Multiple IPs ({len(iocs['ips'])}) and hosts ({len(iocs['hosts'])})",
                "mitre_tactic": "TA0008"
            })
        
        # Pattern 2: Privilege escalation
        process_events = [e for e in timeline if e["event"] == "process_execution"]
        if any("powershell" in str(e.get("details", {})).lower() for e in process_events):
            patterns.append({
                "pattern": "privilege_escalation", 
                "confidence": 0.7,
                "evidence": "PowerShell execution detected",
                "mitre_tactic": "TA0004"
            })
        
        return patterns