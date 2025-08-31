"""
Weighted Jaccard similarity search with Redis caching for fast case correlation.

This module implements efficient similarity search over entity indices with
weighted scoring and TTL-based caching for optimal performance.
"""

import asyncio
import logging
import time
import hashlib
import json
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import redis.asyncio as redis
from app_extensions.entity_normalizer import EntityNormalizer, NormalizedEntity

logger = logging.getLogger(__name__)


@dataclass
class SimilarityConfig:
    """Configuration for similarity scoring."""
    user_weight: float = 0.5
    ip_weight: float = 0.35
    host_weight: float = 0.15
    rule_bonus: float = 0.1
    time_bonus: float = 0.1
    time_window_hours: int = 48
    min_similarity: float = 0.3
    max_results: int = 10


@dataclass 
class SimilarCase:
    """Represents a similar case with scoring metadata."""
    case_id: str
    similarity_score: float
    matched_entities: List[str]
    entity_breakdown: Dict[str, float]
    rule_match: bool
    time_proximity: bool
    summary: str = ""


class SimilaritySearchEngine:
    """
    Fast similarity search with weighted Jaccard and Redis caching.
    """
    
    def __init__(self, redis_client, config: Optional[SimilarityConfig] = None):
        self.redis = redis_client
        self.config = config or SimilarityConfig()
        self.entity_normalizer = EntityNormalizer()
        
        # Cache settings
        self.cache_ttl = 24 * 3600  # 24 hours
        self.index_refresh_interval = 6 * 3600  # 6 hours
        
        # Statistics
        self.search_stats = {
            'total_searches': 0,
            'cache_hits': 0,
            'index_builds': 0,
            'average_search_time_ms': 0.0
        }
    
    def _create_cache_key(self, entities: Dict[str, List[str]], case_id: str = None) -> str:
        """Create deterministic cache key for similarity search."""
        # Sort entities for consistent hashing
        sorted_entities = {}
        for entity_type in sorted(entities.keys()):
            sorted_entities[entity_type] = sorted(entities[entity_type])
        
        content = json.dumps(sorted_entities, sort_keys=True)
        if case_id:
            content += f":{case_id}"
            
        return f"sim:{hashlib.sha256(content.encode()).hexdigest()[:16]}"
    
    async def _maintain_entity_indices(self, case_id: str, entities: Dict[str, List[str]]):
        """
        Maintain entity indices for fast lookup.
        
        Creates indices like:
        - idx:entity:user:{username} -> set of case_ids
        - idx:entity:ip:{ip_address} -> set of case_ids  
        - idx:entity:host:{hostname} -> set of case_ids
        """
        try:
            pipe = self.redis.pipeline()
            
            for entity_type, values in entities.items():
                for value in values:
                    if value and isinstance(value, str):
                        # Add case to entity index
                        index_key = f"idx:entity:{entity_type}:{value.lower()}"
                        pipe.sadd(index_key, case_id)
                        pipe.expire(index_key, 30 * 24 * 3600)  # 30 days TTL
            
            await pipe.execute()
            logger.debug(f"Updated entity indices for case {case_id}")
            
        except Exception as e:
            logger.error(f"Failed to maintain entity indices: {e}")
    
    async def _get_candidate_cases(self, target_entities: Dict[str, List[str]]) -> Set[str]:
        """
        Get candidate cases that share entities with the target case.
        
        Returns set of case_ids that have overlapping entities.
        """
        candidate_cases = set()
        
        try:
            # Collect all candidate cases from entity indices
            for entity_type, values in target_entities.items():
                for value in values:
                    if value and isinstance(value, str):
                        index_key = f"idx:entity:{entity_type}:{value.lower()}"
                        case_ids = await self.redis.smembers(index_key)
                        candidate_cases.update(case_ids)
            
            logger.debug(f"Found {len(candidate_cases)} candidate cases")
            return candidate_cases
            
        except Exception as e:
            logger.error(f"Failed to get candidate cases: {e}")
            return set()
    
    def _calculate_weighted_jaccard(
        self, 
        target_entities: Dict[str, List[str]], 
        candidate_entities: Dict[str, List[str]],
        case_metadata: Dict[str, Any] = None
    ) -> Tuple[float, Dict[str, float]]:
        """
        Calculate weighted Jaccard similarity with bonuses.
        
        Weights: users=0.5, ips=0.35, hosts=0.15
        Bonuses: +0.1 if same rule_id, +0.1 if within 48h
        """
        total_score = 0.0
        breakdown = {}
        
        # Calculate entity type similarities
        entity_weights = {
            'users': self.config.user_weight,
            'ips': self.config.ip_weight, 
            'hosts': self.config.host_weight,
            'usernames': self.config.user_weight,  # Alternative key
            'ip_addresses': self.config.ip_weight,  # Alternative key
            'domains': 0.1  # Small weight for domains
        }
        
        for entity_type, weight in entity_weights.items():
            target_set = set(target_entities.get(entity_type, []))
            candidate_set = set(candidate_entities.get(entity_type, []))
            
            if target_set or candidate_set:
                intersection = len(target_set & candidate_set)
                union = len(target_set | candidate_set)
                
                if union > 0:
                    jaccard = intersection / union
                    weighted_score = jaccard * weight
                    total_score += weighted_score
                    breakdown[entity_type] = weighted_score
                    
                    if intersection > 0:
                        logger.debug(f"{entity_type}: {intersection}/{union} = {jaccard:.3f} * {weight} = {weighted_score:.3f}")
        
        # Apply bonuses if metadata available
        if case_metadata:
            # Rule matching bonus
            target_rule = case_metadata.get('target_rule_id')
            candidate_rule = case_metadata.get('candidate_rule_id')
            if target_rule and candidate_rule and target_rule == candidate_rule:
                total_score += self.config.rule_bonus
                breakdown['rule_bonus'] = self.config.rule_bonus
            
            # Time proximity bonus
            target_time = case_metadata.get('target_timestamp')
            candidate_time = case_metadata.get('candidate_timestamp')
            if target_time and candidate_time:
                try:
                    target_dt = datetime.fromisoformat(target_time.replace('Z', '+00:00'))
                    candidate_dt = datetime.fromisoformat(candidate_time.replace('Z', '+00:00'))
                    
                    time_diff = abs((target_dt - candidate_dt).total_seconds())
                    if time_diff <= (self.config.time_window_hours * 3600):
                        total_score += self.config.time_bonus
                        breakdown['time_bonus'] = self.config.time_bonus
                except (ValueError, AttributeError):
                    pass
        
        return total_score, breakdown
    
    async def _load_case_entities(self, case_id: str) -> Optional[Dict[str, List[str]]]:
        """Load case entities from Redis."""
        try:
            # Try different key patterns
            patterns = [f"case:{case_id}", f"case_id:{case_id}", f"investigation:{case_id}"]
            
            for pattern in patterns:
                case_data = await self.redis.get(pattern)
                if case_data:
                    data = json.loads(case_data)
                    
                    # Extract entities based on data structure
                    if 'entities' in data:
                        return data['entities']
                    elif 'raw_data' in data and 'entities' in data['raw_data']:
                        return data['raw_data']['entities']
                    else:
                        # Try to normalize entities from the data
                        normalized = self.entity_normalizer.get_normalized_dict(data)
                        if normalized:
                            return normalized
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to load entities for case {case_id}: {e}")
            return None
    
    async def find_similar_cases(
        self, 
        target_entities: Dict[str, List[str]], 
        case_id: Optional[str] = None,
        limit: int = None,
        min_similarity: float = None
    ) -> List[SimilarCase]:
        """
        Find similar cases using weighted Jaccard similarity.
        
        Args:
            target_entities: Entities to search for similarities
            case_id: Optional case ID for caching and metadata
            limit: Maximum results (defaults to config.max_results)  
            min_similarity: Minimum similarity threshold (defaults to config.min_similarity)
            
        Returns:
            List of SimilarCase objects sorted by similarity score
        """
        start_time = time.time()
        limit = limit or self.config.max_results
        min_similarity = min_similarity or self.config.min_similarity
        
        self.search_stats['total_searches'] += 1
        
        # Check cache first
        cache_key = self._create_cache_key(target_entities, case_id)
        try:
            cached_results = await self.redis.get(cache_key)
            if cached_results:
                self.search_stats['cache_hits'] += 1
                results = json.loads(cached_results)
                return [
                    SimilarCase(
                        case_id=r['case_id'],
                        similarity_score=r['similarity_score'],
                        matched_entities=r['matched_entities'],
                        entity_breakdown=r['entity_breakdown'],
                        rule_match=r.get('rule_match', False),
                        time_proximity=r.get('time_proximity', False),
                        summary=r.get('summary', '')
                    )
                    for r in results[:limit]
                    if r['similarity_score'] >= min_similarity
                ]
        except Exception as e:
            logger.debug(f"Cache miss or error: {e}")
        
        # Maintain indices for current case
        if case_id:
            await self._maintain_entity_indices(case_id, target_entities)
        
        # Get candidate cases
        candidate_cases = await self._get_candidate_cases(target_entities)
        
        # Remove current case from candidates
        if case_id:
            candidate_cases.discard(case_id)
        
        if not candidate_cases:
            logger.info("No candidate cases found")
            return []
        
        logger.info(f"Evaluating {len(candidate_cases)} candidate cases")
        
        # Calculate similarities
        similar_cases = []
        
        for candidate_id in candidate_cases:
            try:
                # Load candidate entities
                candidate_entities = await self._load_case_entities(candidate_id)
                if not candidate_entities:
                    continue
                
                # Calculate similarity
                score, breakdown = self._calculate_weighted_jaccard(
                    target_entities, candidate_entities
                )
                
                if score >= min_similarity:
                    # Determine matched entities
                    matched_entities = []
                    for entity_type in target_entities:
                        target_set = set(target_entities[entity_type])
                        candidate_set = set(candidate_entities.get(entity_type, []))
                        matched = list(target_set & candidate_set)
                        matched_entities.extend(matched)
                    
                    similar_case = SimilarCase(
                        case_id=candidate_id,
                        similarity_score=score,
                        matched_entities=matched_entities[:10],  # Limit for readability
                        entity_breakdown=breakdown,
                        rule_match='rule_bonus' in breakdown,
                        time_proximity='time_bonus' in breakdown,
                        summary=f"Similarity: {score:.3f}, Entities: {len(matched_entities)}"
                    )
                    similar_cases.append(similar_case)
                    
            except Exception as e:
                logger.error(f"Error processing candidate {candidate_id}: {e}")
                continue
        
        # Sort by similarity score
        similar_cases.sort(key=lambda x: x.similarity_score, reverse=True)
        results = similar_cases[:limit]
        
        # Cache results
        try:
            cache_data = json.dumps([
                {
                    'case_id': sc.case_id,
                    'similarity_score': sc.similarity_score,
                    'matched_entities': sc.matched_entities,
                    'entity_breakdown': sc.entity_breakdown,
                    'rule_match': sc.rule_match,
                    'time_proximity': sc.time_proximity,
                    'summary': sc.summary
                }
                for sc in results
            ])
            await self.redis.setex(cache_key, self.cache_ttl, cache_data)
        except Exception as e:
            logger.error(f"Failed to cache results: {e}")
        
        # Update statistics
        search_time = (time.time() - start_time) * 1000
        self.search_stats['average_search_time_ms'] = (
            (self.search_stats['average_search_time_ms'] * (self.search_stats['total_searches'] - 1) + search_time)
            / self.search_stats['total_searches']
        )
        
        logger.info(f"Found {len(results)} similar cases in {search_time:.1f}ms")
        return results
    
    async def get_search_stats(self) -> Dict[str, Any]:
        """Get similarity search statistics."""
        stats = dict(self.search_stats)
        stats['cache_hit_rate'] = (
            stats['cache_hits'] / max(1, stats['total_searches'])
        )
        
        # Get cache size
        try:
            cache_keys = await self.redis.keys("sim:*")
            stats['cache_size'] = len(cache_keys)
        except:
            stats['cache_size'] = 0
        
        return stats
    
    async def clear_cache(self, pattern: str = "sim:*"):
        """Clear similarity search cache."""
        try:
            keys = await self.redis.keys(pattern)
            if keys:
                await self.redis.delete(*keys)
                logger.info(f"Cleared {len(keys)} cache entries")
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
    
    async def rebuild_indices(self):
        """Rebuild entity indices from all cases (maintenance operation)."""
        try:
            logger.info("Starting entity index rebuild...")
            self.search_stats['index_builds'] += 1
            
            # Clear existing indices
            index_keys = await self.redis.keys("idx:entity:*")
            if index_keys:
                await self.redis.delete(*index_keys)
            
            # Rebuild from all cases
            case_patterns = ["case:*", "case_id:*", "investigation:*"]
            case_count = 0
            
            for pattern in case_patterns:
                case_keys = await self.redis.keys(pattern)
                
                for case_key in case_keys:
                    try:
                        case_id = case_key.split(":")[-1]
                        entities = await self._load_case_entities(case_id)
                        
                        if entities:
                            await self._maintain_entity_indices(case_id, entities)
                            case_count += 1
                            
                    except Exception as e:
                        logger.error(f"Failed to index case {case_key}: {e}")
            
            logger.info(f"Rebuilt entity indices for {case_count} cases")
            
        except Exception as e:
            logger.error(f"Index rebuild failed: {e}")


# Integration with existing RedisStore
async def enhanced_find_similar_cases(
    redis_client,
    target_entities: Dict[str, List[str]], 
    case_id: str = None,
    limit: int = 10,
    min_similarity: float = 0.3
) -> List[SimilarCase]:
    """
    Enhanced similarity search function for integration with existing code.
    """
    search_engine = SimilaritySearchEngine(redis_client)
    return await search_engine.find_similar_cases(
        target_entities, case_id, limit, min_similarity
    )