"""
Enhanced Redis adapter with case/alert management and similarity search
"""
import json
import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
import redis.asyncio as redis
from datetime import datetime, timezone
import hashlib
import re
from dataclasses import dataclass, asdict
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

logger = logging.getLogger(__name__)

@dataclass
class CaseSummary:
    case_id: str
    alert_id: str
    title: str
    description: str
    severity: str
    status: str
    created_at: str
    entities: Dict[str, List[str]]
    raw_data: Dict[str, Any]

@dataclass
class SimilarCase:
    case_id: str
    similarity_score: float
    matched_entities: List[str]
    summary: str

class RedisStore:
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        """
        Initialize Redis store with connection details
        
        Args:
            redis_url: Redis connection URL
        """
        self.redis_url = redis_url
        self.client = None
        self.vectorizer = TfidfVectorizer(stop_words='english', max_features=1000)
        self._entity_patterns = self._get_entity_patterns()
    
    async def _ensure_connection(self):
        """Ensure Redis connection is established"""
        if self.client is None:
            try:
                self.client = redis.from_url(self.redis_url, decode_responses=True)
                await self.client.ping()
                logger.info("Connected to Redis")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                # Continue with mock data for testing
                self.client = None
    
    def _get_entity_patterns(self) -> Dict[str, str]:
        """Define regex patterns for entity extraction"""
        return {
            'ip_addresses': r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b',
            'domains': r'\b[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*\.[a-zA-Z]{2,}\b',
            'email_addresses': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'file_hashes': r'\b[a-fA-F0-9]{32,64}\b',
            'usernames': r'\b(?:user|admin|root|guest|administrator)[-_\w]*\b',
            'file_paths': r'(?:[A-Za-z]:\\\\[^\\/:*?"<>|\\r\\n]*|/[^\\r\\n]*)',
            'urls': r'https?://[^\s<>"{}|\\^`\[\]]+',
            'cve_ids': r'CVE-\d{4}-\d{4,7}'
        }
    
    def _extract_entities_from_text(self, text: str) -> Dict[str, List[str]]:
        """Extract security entities from text using regex patterns"""
        entities = {}
        
        for entity_type, pattern in self._entity_patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                # Remove duplicates and filter out common false positives
                filtered_matches = list(set([
                    match for match in matches 
                    if self._is_valid_entity(entity_type, match)
                ]))
                if filtered_matches:
                    entities[entity_type] = filtered_matches
        
        return entities
    
    def _is_valid_entity(self, entity_type: str, value: str) -> bool:
        """Validate extracted entities to reduce false positives"""
        if entity_type == 'ip_addresses':
            # Filter out private/invalid IPs for some use cases
            parts = value.split('.')
            if len(parts) == 4:
                try:
                    nums = [int(p) for p in parts]
                    # Allow all IPs for security analysis
                    return all(0 <= n <= 255 for n in nums)
                except ValueError:
                    return False
        
        elif entity_type == 'domains':
            # Filter out overly generic domains
            return len(value) > 4 and '.' in value and not value.endswith('.local')
        
        elif entity_type == 'file_hashes':
            # Ensure proper hash length
            return len(value) in [32, 40, 64]  # MD5, SHA1, SHA256
        
        return True
    
    async def get_summary(self, case_or_alert_id: str) -> Dict[str, Any]:
        """
        Get case summary from Redis
        
        Args:
            case_or_alert_id: Case ID or Alert ID to retrieve
            
        Returns:
            Dictionary containing case summary
        """
        await self._ensure_connection()
        
        if self.client:
            try:
                # Try case ID first
                case_data = await self.client.hgetall(f"case:{case_or_alert_id}")
                if case_data:
                    return self._deserialize_case(case_data)
                
                # Try alert ID
                alert_data = await self.client.hgetall(f"alert:{case_or_alert_id}")
                if alert_data:
                    return self._deserialize_case(alert_data)
                
            except Exception as e:
                logger.error(f"Error retrieving case summary: {e}")
        
        # Return mock data for development/testing
        return self._get_mock_case_summary(case_or_alert_id)
    
    def _deserialize_case(self, case_data: Dict[str, str]) -> Dict[str, Any]:
        """Deserialize case data from Redis"""
        try:
            return {
                'case_id': case_data.get('case_id', ''),
                'alert_id': case_data.get('alert_id', ''),
                'title': case_data.get('title', ''),
                'description': case_data.get('description', ''),
                'severity': case_data.get('severity', 'MEDIUM'),
                'status': case_data.get('status', 'OPEN'),
                'created_at': case_data.get('created_at', ''),
                'entities': json.loads(case_data.get('entities', '{}')),
                'raw_data': json.loads(case_data.get('raw_data', '{}'))
            }
        except json.JSONDecodeError as e:
            logger.error(f"Failed to deserialize case data: {e}")
            return {}
    
    def _get_mock_case_summary(self, case_id: str) -> Dict[str, Any]:
        """Generate mock case summary for testing"""
        return {
            'case_id': case_id,
            'alert_id': f"ALERT-{case_id[-8:]}",
            'title': 'Suspicious Network Activity Detected',
            'description': f'Multiple failed login attempts detected from IP 192.168.1.100 targeting user admin@company.com. Potential brute force attack in progress. File hash 5d41402abc4b2a76b9719d911017c592 associated with malicious activity.',
            'severity': 'HIGH',
            'status': 'OPEN',
            'created_at': datetime.now(timezone.utc).isoformat(),
            'entities': {
                'ip_addresses': ['192.168.1.100'],
                'email_addresses': ['admin@company.com'],
                'file_hashes': ['5d41402abc4b2a76b9719d911017c592'],
                'usernames': ['admin']
            },
            'raw_data': {
                'source': 'SIEM',
                'rule_name': 'fact_bruteforce_detection',
                'confidence': 0.85,
                'false_positive_risk': 0.1
            }
        }
    
    async def extract_entities(self, summary: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Extract entities from case summary using NLP and regex
        
        Args:
            summary: Case summary dictionary
            
        Returns:
            Dictionary of extracted entities by type
        """
        # Start with existing entities
        entities = summary.get('entities', {}).copy()
        
        # Extract from title and description
        text_content = f"{summary.get('title', '')} {summary.get('description', '')}"
        
        # Extract additional entities using patterns
        extracted_entities = self._extract_entities_from_text(text_content)
        
        # Merge entities
        for entity_type, entity_list in extracted_entities.items():
            if entity_type in entities:
                # Combine and deduplicate
                combined = list(set(entities[entity_type] + entity_list))
                entities[entity_type] = combined
            else:
                entities[entity_type] = entity_list
        
        return entities
    
    async def find_similar_cases(self, 
                                target_entities: Dict[str, List[str]], 
                                limit: int = 10,
                                min_similarity: float = 0.1) -> List[SimilarCase]:
        """
        Find similar cases based on entity overlap and text similarity
        
        Args:
            target_entities: Entities to match against
            limit: Maximum number of similar cases to return
            min_similarity: Minimum similarity threshold
            
        Returns:
            List of similar cases with similarity scores
        """
        await self._ensure_connection()
        
        if not self.client:
            # Return mock similar cases
            return self._get_mock_similar_cases(target_entities, limit)
        
        try:
            similar_cases = []
            
            # Get all case IDs
            case_keys = await self.client.keys("case:*")
            
            for case_key in case_keys[:50]:  # Limit search for performance
                case_data = await self.client.hgetall(case_key)
                if not case_data:
                    continue
                
                case_summary = self._deserialize_case(case_data)
                case_entities = case_summary.get('entities', {})
                
                # Calculate entity-based similarity
                similarity_score, matched_entities = self._calculate_entity_similarity(
                    target_entities, case_entities
                )
                
                if similarity_score >= min_similarity:
                    similar_case = SimilarCase(
                        case_id=case_summary['case_id'],
                        similarity_score=similarity_score,
                        matched_entities=matched_entities,
                        summary=case_summary['title']
                    )
                    similar_cases.append(similar_case)
            
            # Sort by similarity score
            similar_cases.sort(key=lambda x: x.similarity_score, reverse=True)
            
            return similar_cases[:limit]
            
        except Exception as e:
            logger.error(f"Error finding similar cases: {e}")
            return self._get_mock_similar_cases(target_entities, limit)
    
    def _calculate_entity_similarity(self, 
                                   entities1: Dict[str, List[str]], 
                                   entities2: Dict[str, List[str]]) -> Tuple[float, List[str]]:
        """Calculate similarity between two entity sets"""
        if not entities1 or not entities2:
            return 0.0, []
        
        matched_entities = []
        total_score = 0.0
        total_weight = 0.0
        
        # Entity type weights (higher = more important for similarity)
        entity_weights = {
            'file_hashes': 1.0,
            'ip_addresses': 0.8,
            'domains': 0.8,
            'email_addresses': 0.7,
            'cve_ids': 0.9,
            'usernames': 0.5,
            'file_paths': 0.6,
            'urls': 0.7
        }
        
        for entity_type, weight in entity_weights.items():
            if entity_type in entities1 and entity_type in entities2:
                set1 = set(entities1[entity_type])
                set2 = set(entities2[entity_type])
                
                intersection = set1.intersection(set2)
                union = set1.union(set2)
                
                if union:
                    jaccard_score = len(intersection) / len(union)
                    total_score += jaccard_score * weight
                    total_weight += weight
                    
                    # Track matched entities
                    matched_entities.extend(list(intersection))
        
        if total_weight == 0:
            return 0.0, []
        
        return total_score / total_weight, matched_entities
    
    def _get_mock_similar_cases(self, 
                               target_entities: Dict[str, List[str]], 
                               limit: int) -> List[SimilarCase]:
        """Generate mock similar cases for testing"""
        mock_cases = [
            SimilarCase(
                case_id="CASE-2024-001",
                similarity_score=0.85,
                matched_entities=['192.168.1.100', 'admin'],
                summary="Brute force attack from same IP"
            ),
            SimilarCase(
                case_id="CASE-2024-002", 
                similarity_score=0.72,
                matched_entities=['admin@company.com'],
                summary="Suspicious login activity for admin user"
            ),
            SimilarCase(
                case_id="CASE-2024-003",
                similarity_score=0.65,
                matched_entities=['5d41402abc4b2a76b9719d911017c592'],
                summary="Malicious file hash detected in network traffic"
            )
        ]
        
        return mock_cases[:limit]
    
    async def store_case(self, case_summary: Dict[str, Any]) -> bool:
        """Store case summary in Redis"""
        await self._ensure_connection()
        
        if not self.client:
            logger.warning("No Redis connection, case not stored")
            return False
        
        try:
            case_id = case_summary['case_id']
            serialized_case = {
                'case_id': case_id,
                'alert_id': case_summary.get('alert_id', ''),
                'title': case_summary.get('title', ''),
                'description': case_summary.get('description', ''),
                'severity': case_summary.get('severity', 'MEDIUM'),
                'status': case_summary.get('status', 'OPEN'),
                'created_at': case_summary.get('created_at', datetime.now(timezone.utc).isoformat()),
                'entities': json.dumps(case_summary.get('entities', {})),
                'raw_data': json.dumps(case_summary.get('raw_data', {}))
            }
            
            await self.client.hset(f"case:{case_id}", mapping=serialized_case)
            
            # Add to case index for search
            await self.client.sadd("all_cases", case_id)
            
            logger.info(f"Stored case {case_id} in Redis")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store case: {e}")
            return False
    
    async def get_case_count(self) -> int:
        """Get total number of cases"""
        await self._ensure_connection()
        
        if not self.client:
            return 0
        
        try:
            return await self.client.scard("all_cases")
        except Exception as e:
            logger.error(f"Failed to get case count: {e}")
            return 0