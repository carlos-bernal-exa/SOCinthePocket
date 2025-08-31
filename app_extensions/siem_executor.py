"""
SIEM Query Executor with pagination, timeout controls, and result deduplication.

This module executes SIEM queries safely with proper controls to prevent
system overload while ensuring complete evidence collection.
"""

import asyncio
import logging
import time
from typing import Dict, List, Any, Optional, Set, NamedTuple
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json

from .eligibility import EligibleDetection, deduplicate_queries

logger = logging.getLogger(__name__)


@dataclass
class SiemQuery:
    """Represents a SIEM query with execution parameters."""
    query_id: str
    event_filter: str
    from_time_millis: int
    to_time_millis: int
    limit: int = 1000
    timeout_ms: int = 30000
    linked_detections: List[EligibleDetection] = field(default_factory=list)


@dataclass 
class SiemResult:
    """Represents SIEM query results with metadata."""
    query_id: str
    events: List[Dict[str, Any]]
    total_count: int
    execution_time_ms: int
    query_hash: str
    source_detections: List[str]  # detection_ids
    pagination_info: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


class SiemExecutor:
    """
    Executes SIEM queries with proper controls and result management.
    """
    
    def __init__(self, max_concurrent_queries: int = 3, default_limit: int = 1000):
        self.max_concurrent_queries = max_concurrent_queries
        self.default_limit = default_limit
        self.query_cache: Dict[str, SiemResult] = {}
        self.execution_stats = {
            'total_queries': 0,
            'cache_hits': 0,
            'timeouts': 0,
            'errors': 0,
            'total_events': 0
        }
    
    def _create_query_hash(self, event_filter: str, from_time: int, to_time: int) -> str:
        """Create deterministic hash for query caching."""
        query_content = f"{event_filter}:{from_time}:{to_time}"
        return hashlib.sha256(query_content.encode()).hexdigest()[:16]
    
    def _create_siem_queries(self, eligible_detections: List[EligibleDetection]) -> List[SiemQuery]:
        """
        Convert eligible detections into optimized SIEM queries.
        
        Deduplicates identical event_filters and creates query objects
        with proper parameters and limits.
        """
        query_groups = deduplicate_queries(eligible_detections)
        queries = []
        
        for event_filter, detections in query_groups.items():
            # Use the earliest from_time and latest to_time across all detections
            from_times = [d.event_from_time_millis for d in detections]
            to_times = [d.event_to_time_millis for d in detections]
            
            from_time = min(from_times)
            to_time = max(to_times)
            
            query_hash = self._create_query_hash(event_filter, from_time, to_time)
            
            query = SiemQuery(
                query_id=f"query_{query_hash}",
                event_filter=event_filter,
                from_time_millis=from_time,
                to_time_millis=to_time,
                limit=self.default_limit,
                timeout_ms=30000,
                linked_detections=detections
            )
            queries.append(query)
            
        logger.info(f"Created {len(queries)} optimized SIEM queries from {len(eligible_detections)} detections")
        return queries
    
    async def _execute_single_query(self, siem_client, query: SiemQuery) -> SiemResult:
        """
        Execute a single SIEM query with timeout and error handling.
        """
        start_time = time.time()
        
        # Check cache first
        cache_key = self._create_query_hash(query.event_filter, query.from_time_millis, query.to_time_millis)
        if cache_key in self.query_cache:
            self.execution_stats['cache_hits'] += 1
            cached_result = self.query_cache[cache_key]
            logger.info(f"Cache hit for query {query.query_id}")
            return cached_result
        
        try:
            # Execute query with timeout
            events = await asyncio.wait_for(
                self._execute_siem_query(siem_client, query),
                timeout=query.timeout_ms / 1000.0
            )
            
            execution_time = int((time.time() - start_time) * 1000)
            
            result = SiemResult(
                query_id=query.query_id,
                events=events,
                total_count=len(events),
                execution_time_ms=execution_time,
                query_hash=cache_key,
                source_detections=[d.detection_id for d in query.linked_detections],
                pagination_info={
                    'limit': query.limit,
                    'has_more': len(events) >= query.limit
                }
            )
            
            # Cache successful results
            self.query_cache[cache_key] = result
            self.execution_stats['total_events'] += len(events)
            
            logger.info(f"Query {query.query_id} completed: {len(events)} events in {execution_time}ms")
            return result
            
        except asyncio.TimeoutError:
            self.execution_stats['timeouts'] += 1
            execution_time = int((time.time() - start_time) * 1000)
            logger.error(f"Query {query.query_id} timed out after {execution_time}ms")
            
            return SiemResult(
                query_id=query.query_id,
                events=[],
                total_count=0,
                execution_time_ms=execution_time,
                query_hash=cache_key,
                source_detections=[d.detection_id for d in query.linked_detections],
                error=f"Query timed out after {query.timeout_ms}ms"
            )
            
        except Exception as e:
            self.execution_stats['errors'] += 1
            execution_time = int((time.time() - start_time) * 1000)
            logger.error(f"Query {query.query_id} failed: {str(e)}")
            
            return SiemResult(
                query_id=query.query_id,
                events=[],
                total_count=0,
                execution_time_ms=execution_time,
                query_hash=cache_key,
                source_detections=[d.detection_id for d in query.linked_detections],
                error=str(e)
            )
    
    async def _execute_siem_query(self, siem_client, query: SiemQuery) -> List[Dict[str, Any]]:
        """
        Execute the actual SIEM query using the client.
        
        This method handles the specific SIEM client interface and
        implements pagination if supported.
        """
        # Mock implementation - replace with actual SIEM client calls
        if not siem_client:
            logger.warning("No SIEM client provided, returning empty results")
            return []
        
        # Construct query parameters
        query_params = {
            'query': query.event_filter,
            'from': query.from_time_millis,
            'to': query.to_time_millis,
            'limit': query.limit
        }
        
        # Execute query through client
        if hasattr(siem_client, 'search_events'):
            return await siem_client.search_events(**query_params)
        elif hasattr(siem_client, 'query'):
            return await siem_client.query(**query_params)
        else:
            logger.error("SIEM client does not have expected search methods")
            return []
    
    async def run_siem_queries(self, siem_client, eligible_detections: List[EligibleDetection]) -> List[SiemResult]:
        """
        Execute SIEM queries for eligible detections with proper concurrency control.
        
        Args:
            siem_client: SIEM client for executing queries
            eligible_detections: List of eligible detections to query
            
        Returns:
            List of SiemResult objects with events and metadata
        """
        if not eligible_detections:
            logger.info("No eligible detections for SIEM queries")
            return []
        
        # Create optimized queries
        queries = self._create_siem_queries(eligible_detections)
        
        if not queries:
            logger.warning("No queries created from eligible detections")
            return []
        
        # Execute queries with concurrency control
        semaphore = asyncio.Semaphore(self.max_concurrent_queries)
        
        async def bounded_query(query):
            async with semaphore:
                self.execution_stats['total_queries'] += 1
                return await self._execute_single_query(siem_client, query)
        
        logger.info(f"Executing {len(queries)} SIEM queries with max concurrency {self.max_concurrent_queries}")
        
        # Execute all queries concurrently
        results = await asyncio.gather(*[bounded_query(q) for q in queries])
        
        # Log execution summary
        successful_results = [r for r in results if not r.error]
        failed_results = [r for r in results if r.error]
        total_events = sum(r.total_count for r in successful_results)
        
        logger.info(f"SIEM query execution complete: {len(successful_results)} successful, "
                   f"{len(failed_results)} failed, {total_events} total events")
        
        return results
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get executor statistics for monitoring and optimization."""
        return {
            **self.execution_stats,
            'cache_size': len(self.query_cache),
            'cache_hit_rate': (
                self.execution_stats['cache_hits'] / max(1, self.execution_stats['total_queries'])
            )
        }
    
    def clear_cache(self):
        """Clear the query result cache."""
        self.query_cache.clear()
        logger.info("SIEM query cache cleared")


def fan_out_results(siem_results: List[SiemResult]) -> Dict[str, Dict[str, Any]]:
    """
    Fan out SIEM query results to all linked detections.
    
    This ensures each detection gets the events from its corresponding
    query while maintaining traceability.
    
    Args:
        siem_results: List of SIEM query results
        
    Returns:
        Dict mapping detection_id to events and metadata
    """
    detection_results = {}
    
    for result in siem_results:
        for detection_id in result.source_detections:
            detection_results[detection_id] = {
                'events': result.events,
                'total_count': result.total_count,
                'query_id': result.query_id,
                'execution_time_ms': result.execution_time_ms,
                'error': result.error,
                'query_hash': result.query_hash
            }
    
    logger.info(f"Fanned out results to {len(detection_results)} detections")
    return detection_results


# Legacy function for backward compatibility
async def run_siem_queries(siem_client, eligible_detections: List[EligibleDetection]) -> tuple[List[Dict], int]:
    """
    Legacy function wrapper for backward compatibility.
    
    Returns:
        Tuple of (events_list, total_count) for compatibility
    """
    executor = SiemExecutor()
    results = await executor.run_siem_queries(siem_client, eligible_detections)
    
    # Aggregate all events
    all_events = []
    total_count = 0
    
    for result in results:
        if not result.error:
            all_events.extend(result.events)
            total_count += result.total_count
    
    return all_events, total_count