"""
Timeline Construction with event normalization, deduplication, and source citations.

This module produces a single, ordered, annotated timeline from multi-query SIEM results
with proper event normalization and analyst-friendly formatting.
"""

import logging
import re
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class TimelineEvent:
    """
    Represents a normalized timeline event with full context and citations.
    """
    timestamp: datetime
    timestamp_iso: str
    actor: str
    event: str
    source: str
    event_type: str
    severity: str = "info"
    details: Dict[str, Any] = field(default_factory=dict)
    citations: Dict[str, Any] = field(default_factory=dict)
    raw_event: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Ensure timestamp_iso is set correctly."""
        if isinstance(self.timestamp, datetime):
            self.timestamp_iso = self.timestamp.isoformat()


@dataclass
class DeduplicationGroup:
    """Represents a group of deduplicated events."""
    representative_event: TimelineEvent
    duplicate_count: int
    source_breakdown: Dict[str, int]
    time_range_seconds: int


class TimelineBuilder:
    """
    Constructs ordered, annotated timelines from SIEM results and other sources.
    """
    
    def __init__(self):
        # Event type mappings for classification
        self.event_type_patterns = {
            'authentication': [
                r'login', r'logon', r'auth', r'signin', r'sso',
                r'password', r'credential', r'token'
            ],
            'network': [
                r'connect', r'tcp', r'udp', r'http', r'https',
                r'dns', r'traffic', r'packet', r'socket'
            ],
            'file': [
                r'file', r'download', r'upload', r'write', r'read',
                r'create', r'delete', r'modify', r'copy'
            ],
            'process': [
                r'process', r'exe', r'cmd', r'command', r'spawn',
                r'execute', r'run', r'start', r'kill'
            ],
            'security': [
                r'alert', r'block', r'deny', r'malware', r'virus',
                r'threat', r'suspicious', r'anomaly', r'breach'
            ]
        }
        
        # Severity keywords for automatic classification
        self.severity_patterns = {
            'critical': [r'critical', r'emergency', r'fatal', r'severe'],
            'high': [r'high', r'warning', r'alert', r'error', r'fail'],
            'medium': [r'medium', r'notice', r'unusual', r'anomaly'],
            'low': [r'low', r'info', r'debug', r'trace']
        }
        
        # Common timestamp formats to handle
        self.timestamp_formats = [
            '%Y-%m-%dT%H:%M:%S.%fZ',      # ISO with microseconds
            '%Y-%m-%dT%H:%M:%SZ',         # ISO without microseconds
            '%Y-%m-%dT%H:%M:%S.%f%z',     # ISO with timezone
            '%Y-%m-%dT%H:%M:%S%z',        # ISO with timezone, no microseconds
            '%Y-%m-%d %H:%M:%S.%f',       # MySQL format
            '%Y-%m-%d %H:%M:%S',          # Simple format
            '%d/%m/%Y %H:%M:%S',          # European format
            '%m/%d/%Y %H:%M:%S'           # US format
        ]
    
    def _normalize_timestamp(self, timestamp_value: Any) -> Optional[datetime]:
        """
        Normalize various timestamp formats to datetime object.
        
        Args:
            timestamp_value: Timestamp in various formats (str, int, float, datetime)
            
        Returns:
            Normalized datetime object or None if parsing fails
        """
        if isinstance(timestamp_value, datetime):
            return timestamp_value.replace(tzinfo=timezone.utc) if not timestamp_value.tzinfo else timestamp_value
        
        if isinstance(timestamp_value, (int, float)):
            # Handle epoch timestamps (both seconds and milliseconds)
            try:
                # If timestamp is too large, it's likely milliseconds
                if timestamp_value > 1e10:
                    timestamp_value = timestamp_value / 1000
                return datetime.fromtimestamp(timestamp_value, tz=timezone.utc)
            except (ValueError, OSError):
                return None
        
        if isinstance(timestamp_value, str):
            # Try each format
            for fmt in self.timestamp_formats:
                try:
                    dt = datetime.strptime(timestamp_value, fmt)
                    # Ensure UTC timezone
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return dt
                except ValueError:
                    continue
            
            # Try parsing ISO format with dateutil as fallback
            try:
                from dateutil import parser
                dt = parser.isoparse(timestamp_value)
                return dt.replace(tzinfo=timezone.utc) if not dt.tzinfo else dt
            except:
                pass
        
        logger.warning(f"Failed to parse timestamp: {timestamp_value}")
        return None
    
    def _classify_event_type(self, event_description: str, raw_event: Dict[str, Any]) -> str:
        """
        Classify event type based on description and raw event data.
        
        Args:
            event_description: Event description text
            raw_event: Raw event data for additional context
            
        Returns:
            Event type classification
        """
        text_to_check = event_description.lower()
        
        # Add relevant fields from raw event
        for field in ['event_type', 'category', 'action', 'log_source']:
            if field in raw_event and raw_event[field]:
                text_to_check += f" {str(raw_event[field]).lower()}"
        
        # Check patterns
        for event_type, patterns in self.event_type_patterns.items():
            if any(re.search(pattern, text_to_check) for pattern in patterns):
                return event_type
        
        return 'unknown'
    
    def _classify_severity(self, event_description: str, raw_event: Dict[str, Any]) -> str:
        """
        Classify event severity based on description and metadata.
        
        Args:
            event_description: Event description text
            raw_event: Raw event data for severity indicators
            
        Returns:
            Severity classification (critical, high, medium, low)
        """
        # Check if severity is explicitly provided
        for field in ['severity', 'priority', 'level', 'risk_score']:
            if field in raw_event and raw_event[field]:
                severity_value = str(raw_event[field]).lower()
                for severity, patterns in self.severity_patterns.items():
                    if any(pattern in severity_value for pattern in patterns):
                        return severity
        
        # Classify based on description
        text_to_check = event_description.lower()
        for severity, patterns in self.severity_patterns.items():
            if any(re.search(pattern, text_to_check) for pattern in patterns):
                return severity
        
        return 'low'  # Default severity
    
    def _extract_actor(self, raw_event: Dict[str, Any]) -> str:
        """
        Extract the actor/subject from raw event data.
        
        Args:
            raw_event: Raw event data
            
        Returns:
            Actor identifier (user, process, IP, etc.)
        """
        # Common actor fields in order of preference
        actor_fields = [
            'user', 'username', 'user_name', 'subject',
            'src_user', 'source_user', 'actor',
            'process_name', 'exe', 'executable',
            'src_ip', 'source_ip', 'client_ip',
            'hostname', 'host', 'computer_name'
        ]
        
        for field in actor_fields:
            if field in raw_event and raw_event[field]:
                value = str(raw_event[field]).strip()
                if value and value not in ['null', 'None', '-', 'unknown']:
                    return value
        
        return 'system'  # Default actor
    
    def _create_event_description(self, raw_event: Dict[str, Any]) -> str:
        """
        Create human-readable event description from raw event data.
        
        Args:
            raw_event: Raw event data
            
        Returns:
            Human-readable event description
        """
        # Look for existing description fields
        desc_fields = [
            'description', 'message', 'summary', 'event_desc',
            'log_message', 'raw_message', 'details'
        ]
        
        for field in desc_fields:
            if field in raw_event and raw_event[field]:
                desc = str(raw_event[field]).strip()
                if len(desc) > 10:  # Meaningful description
                    return desc
        
        # Construct description from available fields
        parts = []
        
        # Add action/event type
        for field in ['action', 'event_type', 'category']:
            if field in raw_event and raw_event[field]:
                parts.append(str(raw_event[field]))
                break
        
        # Add target/object
        for field in ['target', 'object', 'file_name', 'url', 'dest_ip']:
            if field in raw_event and raw_event[field]:
                parts.append(f"involving {raw_event[field]}")
                break
        
        # Add result/outcome
        for field in ['result', 'status', 'outcome']:
            if field in raw_event and raw_event[field]:
                parts.append(f"({raw_event[field]})")
                break
        
        if parts:
            return ' '.join(parts)
        else:
            return 'Activity detected'
    
    def _create_citations(self, 
                         case_id: str, 
                         detection_id: str, 
                         query_id: str = None,
                         siem_uri: str = None) -> Dict[str, Any]:
        """
        Create source citations for audit and traceability.
        
        Args:
            case_id: Source case ID
            detection_id: Detection ID that generated this event
            query_id: SIEM query ID (optional)
            siem_uri: Direct SIEM URI for event (optional)
            
        Returns:
            Citations dictionary with source information
        """
        citations = {
            'case_id': case_id,
            'detection_id': detection_id,
            'extracted_at': datetime.now(timezone.utc).isoformat()
        }
        
        if query_id:
            citations['query_id'] = query_id
        
        if siem_uri:
            citations['siem_uri'] = siem_uri
        
        # Generate audit hash for integrity
        citation_content = json.dumps(citations, sort_keys=True)
        citations['audit_hash'] = hashlib.sha256(citation_content.encode()).hexdigest()[:16]
        
        return citations
    
    def normalize_siem_events(self, 
                            siem_results: List[Dict[str, Any]], 
                            case_id: str) -> List[TimelineEvent]:
        """
        Normalize SIEM events into TimelineEvent objects.
        
        Args:
            siem_results: List of SIEM query results with events
            case_id: Source case ID for citations
            
        Returns:
            List of normalized TimelineEvent objects
        """
        timeline_events = []
        
        for siem_result in siem_results:
            query_id = siem_result.get('query_id')
            detection_ids = siem_result.get('source_detections', [])
            events = siem_result.get('events', [])
            
            for raw_event in events:
                try:
                    # Normalize timestamp
                    timestamp_field = None
                    timestamp_value = None
                    
                    # Try common timestamp fields
                    for field in ['timestamp', '@timestamp', 'time', 'event_time', 
                                 'created_at', 'occurred_at', '_time']:
                        if field in raw_event:
                            timestamp_field = field
                            timestamp_value = raw_event[field]
                            break
                    
                    if not timestamp_value:
                        logger.warning("No timestamp found in event, skipping")
                        continue
                    
                    normalized_timestamp = self._normalize_timestamp(timestamp_value)
                    if not normalized_timestamp:
                        logger.warning(f"Failed to parse timestamp: {timestamp_value}")
                        continue
                    
                    # Extract event components
                    actor = self._extract_actor(raw_event)
                    event_description = self._create_event_description(raw_event)
                    event_type = self._classify_event_type(event_description, raw_event)
                    severity = self._classify_severity(event_description, raw_event)
                    
                    # Determine source
                    source = raw_event.get('log_source', raw_event.get('source', 'SIEM'))
                    
                    # Create citations
                    detection_id = detection_ids[0] if detection_ids else 'unknown'
                    citations = self._create_citations(case_id, detection_id, query_id)
                    
                    # Create normalized event
                    timeline_event = TimelineEvent(
                        timestamp=normalized_timestamp,
                        timestamp_iso=normalized_timestamp.isoformat(),
                        actor=actor,
                        event=event_description,
                        source=source,
                        event_type=event_type,
                        severity=severity,
                        details={
                            'raw_fields': {k: v for k, v in raw_event.items() 
                                         if k not in ['timestamp', '@timestamp', 'time']},
                            'normalization_metadata': {
                                'timestamp_field': timestamp_field,
                                'extracted_actor_from': self._find_actor_field(raw_event),
                                'event_type_classification': event_type,
                                'severity_classification': severity
                            }
                        },
                        citations=citations,
                        raw_event=raw_event
                    )
                    
                    timeline_events.append(timeline_event)
                    
                except Exception as e:
                    logger.error(f"Failed to normalize event: {e}")
                    continue
        
        logger.info(f"Normalized {len(timeline_events)} events from SIEM results")
        return timeline_events
    
    def _find_actor_field(self, raw_event: Dict[str, Any]) -> Optional[str]:
        """Helper to identify which field was used for actor extraction."""
        actor_fields = [
            'user', 'username', 'user_name', 'subject',
            'src_user', 'source_user', 'actor',
            'process_name', 'exe', 'executable',
            'src_ip', 'source_ip', 'client_ip',
            'hostname', 'host', 'computer_name'
        ]
        
        for field in actor_fields:
            if field in raw_event and raw_event[field]:
                return field
        return None
    
    def deduplicate_events(self, 
                          events: List[TimelineEvent],
                          time_window_seconds: int = 5) -> List[TimelineEvent]:
        """
        Deduplicate near-identical events with counters.
        
        Args:
            events: List of timeline events
            time_window_seconds: Time window for considering events similar
            
        Returns:
            Deduplicated list with representative events and counts
        """
        if not events:
            return []
        
        # Group events by similarity key
        event_groups = defaultdict(list)
        
        for event in events:
            # Create similarity key based on actor, event type, and core message
            similarity_key = (
                event.actor,
                event.event_type,
                event.source,
                # Use first 100 chars of event description for grouping
                event.event[:100] if len(event.event) > 100 else event.event
            )
            
            event_groups[similarity_key].append(event)
        
        # Process each group for temporal deduplication
        deduplicated_events = []
        
        for similarity_key, group_events in event_groups.items():
            # Sort by timestamp
            group_events.sort(key=lambda x: x.timestamp)
            
            current_cluster = [group_events[0]]
            
            for event in group_events[1:]:
                # Check if event is within time window of current cluster
                time_diff = abs((event.timestamp - current_cluster[-1].timestamp).total_seconds())
                
                if time_diff <= time_window_seconds:
                    current_cluster.append(event)
                else:
                    # Process current cluster and start new one
                    dedupe_group = self._create_deduplicated_event(current_cluster)
                    deduplicated_events.append(dedupe_group)
                    current_cluster = [event]
            
            # Process final cluster
            if current_cluster:
                dedupe_group = self._create_deduplicated_event(current_cluster)
                deduplicated_events.append(dedupe_group)
        
        # Sort final results by timestamp
        deduplicated_events.sort(key=lambda x: x.timestamp)
        
        original_count = len(events)
        final_count = len(deduplicated_events)
        logger.info(f"Deduplicated {original_count} events to {final_count} ({original_count - final_count} duplicates)")
        
        return deduplicated_events
    
    def _create_deduplicated_event(self, event_cluster: List[TimelineEvent]) -> TimelineEvent:
        """
        Create a representative event from a cluster of similar events.
        
        Args:
            event_cluster: List of similar events
            
        Returns:
            Representative TimelineEvent with deduplication metadata
        """
        if len(event_cluster) == 1:
            return event_cluster[0]
        
        # Use earliest event as representative
        representative = event_cluster[0]
        
        # Aggregate source breakdown
        source_breakdown = defaultdict(int)
        for event in event_cluster:
            source_breakdown[event.source] += 1
        
        # Calculate time range
        timestamps = [event.timestamp for event in event_cluster]
        time_range = (max(timestamps) - min(timestamps)).total_seconds()
        
        # Update representative event with deduplication info
        representative.details['deduplication'] = {
            'duplicate_count': len(event_cluster) - 1,
            'total_occurrences': len(event_cluster),
            'source_breakdown': dict(source_breakdown),
            'time_range_seconds': int(time_range),
            'first_occurrence': min(timestamps).isoformat(),
            'last_occurrence': max(timestamps).isoformat()
        }
        
        # Update event description to indicate duplicates
        if len(event_cluster) > 1:
            representative.event += f" ({len(event_cluster)} occurrences)"
        
        return representative
    
    def build_timeline(self, 
                      siem_results: List[Dict[str, Any]], 
                      case_id: str,
                      additional_events: List[TimelineEvent] = None) -> List[TimelineEvent]:
        """
        Build complete timeline from SIEM results and additional events.
        
        Args:
            siem_results: SIEM query results
            case_id: Case ID for citations
            additional_events: Optional additional events to include
            
        Returns:
            Complete ordered timeline with deduplication and normalization
        """
        logger.info(f"Building timeline for case {case_id}")
        
        # Normalize SIEM events
        timeline_events = self.normalize_siem_events(siem_results, case_id)
        
        # Add additional events if provided
        if additional_events:
            timeline_events.extend(additional_events)
        
        # Deduplicate events
        timeline_events = self.deduplicate_events(timeline_events)
        
        # Final sort by timestamp
        timeline_events.sort(key=lambda x: x.timestamp)
        
        logger.info(f"Timeline built with {len(timeline_events)} events")
        return timeline_events
    
    def export_timeline_summary(self, timeline: List[TimelineEvent]) -> Dict[str, Any]:
        """
        Export timeline summary for reporting and analysis.
        
        Args:
            timeline: List of timeline events
            
        Returns:
            Summary dictionary with statistics and key events
        """
        if not timeline:
            return {'total_events': 0}
        
        # Calculate statistics
        event_types = defaultdict(int)
        severities = defaultdict(int)
        actors = defaultdict(int)
        sources = defaultdict(int)
        
        for event in timeline:
            event_types[event.event_type] += 1
            severities[event.severity] += 1
            actors[event.actor] += 1
            sources[event.source] += 1
        
        # Get time range
        first_event = min(timeline, key=lambda x: x.timestamp)
        last_event = max(timeline, key=lambda x: x.timestamp)
        duration = (last_event.timestamp - first_event.timestamp).total_seconds()
        
        # Identify key events (high severity)
        key_events = [
            {
                'timestamp': event.timestamp_iso,
                'actor': event.actor,
                'event': event.event,
                'severity': event.severity
            }
            for event in timeline
            if event.severity in ['critical', 'high']
        ][:10]  # Top 10 key events
        
        return {
            'total_events': len(timeline),
            'time_range': {
                'start': first_event.timestamp_iso,
                'end': last_event.timestamp_iso,
                'duration_seconds': int(duration)
            },
            'event_type_breakdown': dict(event_types),
            'severity_breakdown': dict(severities),
            'top_actors': dict(sorted(actors.items(), key=lambda x: x[1], reverse=True)[:5]),
            'source_breakdown': dict(sources),
            'key_events': key_events
        }


# Legacy functions for backward compatibility
def build_timeline(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Legacy function for backward compatibility."""
    return events  # Simple passthrough for now


def build_timeline_from_events(events: List[Dict[str, Any]], case_id: str) -> List[Dict[str, Any]]:
    """Legacy function for backward compatibility."""
    builder = TimelineBuilder()
    
    # Convert legacy format to SIEM results format
    siem_results = [{
        'query_id': 'legacy',
        'source_detections': ['legacy'],
        'events': events
    }]
    
    timeline = builder.build_timeline(siem_results, case_id)
    
    # Convert back to legacy format
    return [
        {
            'timestamp': event.timestamp_iso,
            'actor': event.actor,
            'event': event.event,
            'source': event.source,
            'severity': event.severity,
            'details': event.details
        }
        for event in timeline
    ]