"""
Rule eligibility and detection selection module for SOC SIEM query pipeline.

This module implements strict rule gating to ensure only fact*/profile* detections
are eligible for SIEM queries, preventing noise and unauthorized access.
"""

import re
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class EligibleDetection:
    """Represents a detection eligible for SIEM querying."""
    detection_id: str
    rule_name: str
    rule_type: Optional[str]
    search_query: str
    event_filter: str
    event_from_time_millis: int
    event_to_time_millis: int
    window_minutes: int
    source_case_id: str


def is_fact_or_profile(rule: Dict[str, Any]) -> bool:
    """
    Determine if a rule is eligible for SIEM queries.
    
    Eligibility criteria:
    1. rule_name.lower() starts with "fact" or "prof"
    2. rule_type is "factFeature" or "profileFeature" (when present)
    
    Args:
        rule: Dictionary containing rule information
        
    Returns:
        bool: True if rule is eligible for SIEM queries
    """
    rule_name = rule.get('rule_name', '').lower()
    rule_type = rule.get('rule_type', '').lower()
    
    # Check rule name prefix
    name_eligible = rule_name.startswith(('fact', 'prof'))
    
    # Check rule type (when present)
    type_eligible = rule_type in {'factfeature', 'profilefeature'} if rule_type else False
    
    return name_eligible or type_eligible


def select_eligible_detections(raw_case: Dict[str, Any]) -> List[EligibleDetection]:
    """
    Extract eligible detections from a raw case for SIEM querying.
    
    This function implements strict gating to prevent unauthorized SIEM access
    and reduces noise by only selecting fact*/profile* detections.
    
    Args:
        raw_case: Raw case data from Exabeam
        
    Returns:
        List[EligibleDetection]: List of detections eligible for SIEM queries
    """
    eligible_detections = []
    case_id = raw_case.get('case_id', 'unknown')
    
    # Extract detections from various possible locations in raw_case
    detections = []
    
    # Check raw_data.timeline_events for detection information
    raw_data = raw_case.get('raw_data', {})
    timeline_events = raw_data.get('timeline_events', [])
    
    for event in timeline_events:
        if isinstance(event, dict) and 'detection_rule' in event:
            detections.append({
                'detection_id': event.get('detection_id', f"det_{len(detections)}"),
                'rule_name': event.get('detection_rule', ''),
                'rule_type': event.get('rule_type'),
                'search_query': event.get('search_query', ''),
                'event_filter': event.get('event_filter', event.get('search_query', '')),
                'event_from_time_millis': event.get('event_from_time_millis', 0),
                'event_to_time_millis': event.get('event_to_time_millis', 0),
                'window_minutes': event.get('window_minutes', 60)
            })
    
    # Also check detections array if present
    if 'detections' in raw_case:
        for detection in raw_case['detections']:
            if isinstance(detection, dict):
                detections.append({
                    'detection_id': detection.get('id', f"det_{len(detections)}"),
                    'rule_name': detection.get('rule_name', ''),
                    'rule_type': detection.get('rule_type'),
                    'search_query': detection.get('search_query', ''),
                    'event_filter': detection.get('event_filter', detection.get('search_query', '')),
                    'event_from_time_millis': detection.get('from_time', 0),
                    'event_to_time_millis': detection.get('to_time', 0),
                    'window_minutes': detection.get('window_minutes', 60)
                })
    
    logger.info(f"Found {len(detections)} total detections in case {case_id}")
    
    # Apply eligibility filtering
    for detection in detections:
        rule_info = {
            'rule_name': detection.get('rule_name', ''),
            'rule_type': detection.get('rule_type')
        }
        
        if is_fact_or_profile(rule_info):
            # Validate required fields
            event_filter = detection.get('event_filter', '').strip()
            if not event_filter:
                logger.warning(f"Skipping detection {detection.get('detection_id')} - no event_filter")
                continue
                
            from_time = detection.get('event_from_time_millis', 0)
            to_time = detection.get('event_to_time_millis', 0)
            
            if from_time <= 0 or to_time <= 0:
                logger.warning(f"Skipping detection {detection.get('detection_id')} - invalid time window")
                continue
                
            eligible_detection = EligibleDetection(
                detection_id=detection.get('detection_id', f"det_{len(eligible_detections)}"),
                rule_name=detection.get('rule_name', ''),
                rule_type=detection.get('rule_type'),
                search_query=detection.get('search_query', ''),
                event_filter=event_filter,
                event_from_time_millis=from_time,
                event_to_time_millis=to_time,
                window_minutes=detection.get('window_minutes', 60),
                source_case_id=case_id
            )
            eligible_detections.append(eligible_detection)
            logger.info(f"Eligible detection: {eligible_detection.rule_name} ({eligible_detection.detection_id})")
        else:
            logger.debug(f"Filtered out detection: {detection.get('rule_name')} - not fact*/prof* rule")
    
    logger.info(f"Selected {len(eligible_detections)} eligible detections from case {case_id}")
    return eligible_detections


def deduplicate_queries(eligible_detections: List[EligibleDetection]) -> Dict[str, List[EligibleDetection]]:
    """
    Deduplicate identical event_filter strings and group detections.
    
    This reduces SIEM load by executing identical queries only once and
    fanning out results to all linked detections.
    
    Args:
        eligible_detections: List of eligible detections
        
    Returns:
        Dict mapping unique event_filter to list of detections sharing that filter
    """
    query_groups = {}
    
    for detection in eligible_detections:
        filter_key = detection.event_filter.strip()
        
        if filter_key not in query_groups:
            query_groups[filter_key] = []
        
        query_groups[filter_key].append(detection)
    
    logger.info(f"Deduplicated {len(eligible_detections)} detections into {len(query_groups)} unique queries")
    return query_groups


def validate_detection_rules(raw_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validate rule gating across multiple raw cases for testing and audit purposes.
    
    Args:
        raw_cases: List of raw case data
        
    Returns:
        Dict containing validation statistics and rule analysis
    """
    stats = {
        'total_cases': len(raw_cases),
        'total_detections': 0,
        'eligible_detections': 0,
        'filtered_detections': 0,
        'rule_distribution': {},
        'eligibility_reasons': []
    }
    
    for case in raw_cases:
        detections = select_eligible_detections(case)
        stats['eligible_detections'] += len(detections)
        
        # Count all detections for comparison
        all_detections = []
        raw_data = case.get('raw_data', {})
        timeline_events = raw_data.get('timeline_events', [])
        
        for event in timeline_events:
            if isinstance(event, dict) and 'detection_rule' in event:
                all_detections.append(event)
        
        if 'detections' in case:
            all_detections.extend(case['detections'])
        
        stats['total_detections'] += len(all_detections)
        stats['filtered_detections'] += len(all_detections) - len(detections)
        
        # Track rule distribution
        for detection in all_detections:
            rule_name = detection.get('detection_rule', detection.get('rule_name', 'unknown'))
            if rule_name not in stats['rule_distribution']:
                stats['rule_distribution'][rule_name] = {'total': 0, 'eligible': 0}
            stats['rule_distribution'][rule_name]['total'] += 1
            
            if any(d.rule_name == rule_name for d in detections):
                stats['rule_distribution'][rule_name]['eligible'] += 1
    
    return stats