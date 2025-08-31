"""
EnrichmentAgent - Find similar cases and apply rule filtering
"""
import asyncio
from typing import Dict, Any, List, Optional
from .base import AgentBase
from ..adapters.neo4j_store import neo4j_store
from ..adapters.redis_store import RedisStore
from ..adapters.exabeam import exabeam_client
import logging
import json
import re

logger = logging.getLogger(__name__)

class EnrichmentAgent(AgentBase):
    """
    Enrichment Agent that finds similar cases/alerts in Redis, 
    fetches raw cases from Exabeam, and applies rule filtering.
    """
    
    def __init__(self):
        super().__init__(
            name="EnrichmentAgent", 
            model="gemini-2.5-flash",
            role="enrichment"
        )
        self.redis_store = RedisStore()
    
    def _format_prompt(self, prompt_content: str, inputs: Dict[str, Any]) -> str:
        """Format enrichment-specific prompt"""
        case_id = inputs.get("case_id", "unknown")
        entities = inputs.get("entities", [])
        case_data = inputs.get("case_data", {})
        
        formatted = f"""You are a SOC Enrichment Agent analyzing security case {case_id}.

Your role is to:
1. Find similar cases and alerts using entity overlap and text similarity
2. Apply rule-based filtering to determine SIEM query eligibility
3. Fetch raw case data from Exabeam when available
4. Only allow SIEM queries for fact* and profile* detection rules

Entities from triage: {json.dumps(entities, indent=2)}
Case data: {json.dumps(case_data, indent=2)}

CRITICAL RULE FILTERING:
- Only cases with detection rules matching "fact*" or "profile*" patterns are eligible for SIEM queries
- All other rules (like "behavioral*", "anomaly*", etc.) should be skipped for SIEM execution
- Mark each case as "eligible" or "skipped" with reasoning

Respond with:
1. Similar cases found (with similarity scores)
2. Raw case data retrieved from Exabeam
3. Rule filtering results (eligible vs skipped cases)
4. Entity enrichment and context

Format your response as structured JSON with fields:
- related_items: List of similar cases with scores
- raw_cases: List of raw case data from Exabeam  
- kept_cases: Cases eligible for SIEM queries (fact*/profile* rules only)
- skipped_cases: Cases skipped due to rule patterns
- enriched_entities: Enhanced entity information
- similarity_analysis: Methodology used for matching"""

        return formatted
    
    async def _find_similar_cases(self, entities: List[Dict], case_data: Dict) -> List[Dict]:
        """Find similar cases in Redis based on entity overlap"""
        try:
            # Convert entities to Redis format
            target_entities = {}
            for entity in entities:
                entity_type = entity.get("type", "unknown")
                entity_value = entity.get("value", "")
                
                # Map entity types to Redis format
                redis_type = self._map_entity_type(entity_type)
                if redis_type and entity_value:
                    if redis_type not in target_entities:
                        target_entities[redis_type] = []
                    target_entities[redis_type].append(entity_value)
            
            # Find similar cases using Redis
            similar_cases_data = await self.redis_store.find_similar_cases(
                target_entities=target_entities,
                limit=10,
                min_similarity=0.3
            )
            
            # Convert to expected format
            similar_cases = []
            for case in similar_cases_data:
                similar_cases.append({
                    "case_id": case.case_id,
                    "similarity_score": case.similarity_score,
                    "matching_entities": case.matched_entities,
                    "overlap_reason": f"Entity overlap: {', '.join(case.matched_entities[:3])}"
                })
            
            logger.info(f"Found {len(similar_cases)} similar cases from Redis")
            return similar_cases
            
        except Exception as e:
            logger.error(f"Error finding similar cases in Redis: {e}")
            # Return empty list on error
            return []
    
    def _map_entity_type(self, entity_type: str) -> Optional[str]:
        """Map triage entity types to Redis entity types"""
        type_mapping = {
            "ip": "ip_addresses",
            "domain": "domains", 
            "email": "email_addresses",
            "hash": "file_hashes",
            "user": "usernames",
            "file": "file_paths",
            "url": "urls",
            "cve": "cve_ids"
        }
        return type_mapping.get(entity_type.lower())
    
    async def _fetch_exabeam_raw_data(self, case_ids: List[str]) -> List[Dict]:
        """Fetch raw case data from Exabeam"""
        try:
            if not case_ids:
                return []
            
            # Use the real Exabeam client to fetch case data
            raw_cases = await exabeam_client.fetch_cases(case_ids)
            
            logger.info(f"Retrieved raw data for {len(raw_cases)} cases from Exabeam")
            return raw_cases
            
        except Exception as e:
            logger.error(f"Error fetching raw data from Exabeam: {e}")
            return []
    
    def _apply_rule_filter(self, raw_cases: List[Dict]) -> Dict[str, List[Dict]]:
        """Apply rule-based filtering for SIEM query eligibility"""
        kept_cases = []
        skipped_cases = []
        
        for case in raw_cases:
            rule_name = case.get("raw_data", {}).get("detection_rule", "")
            
            # Check if rule matches fact* or profile* patterns
            if re.match(r'^(fact|profile)', rule_name.lower()):
                kept_cases.append({
                    **case,
                    "siem_eligible": True,
                    "filter_reason": f"Rule '{rule_name}' matches fact*/profile* pattern"
                })
            else:
                skipped_cases.append({
                    **case,
                    "siem_eligible": False,
                    "filter_reason": f"Rule '{rule_name}' does not match fact*/profile* pattern"
                })
        
        logger.info(f"Rule filtering: {len(kept_cases)} kept, {len(skipped_cases)} skipped")
        return {"kept_cases": kept_cases, "skipped_cases": skipped_cases}
    
    async def _enrich_entities(self, entities: List[Dict], similar_cases: List[Dict]) -> List[Dict]:
        """Enrich entities with context from similar cases"""
        enriched = []
        
        for entity in entities:
            enriched_entity = {
                **entity,
                "enrichment": {
                    "seen_in_cases": [],
                    "reputation": "unknown",
                    "context": []
                }
            }
            
            # Find occurrences in similar cases
            for case in similar_cases:
                if entity["value"] in case.get("matching_entities", []):
                    enriched_entity["enrichment"]["seen_in_cases"].append({
                        "case_id": case["case_id"],
                        "similarity": case["similarity_score"]
                    })
            
            enriched.append(enriched_entity)
        
        return enriched
    
    async def process(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Process enrichment logic with Neo4j integration"""
        try:
            case_id = inputs.get("case_id")
            entities = inputs.get("entities", [])
            case_data = inputs.get("case_data", {})
            
            # Create case-rule relationship in Neo4j (temporarily disabled for debugging)
            rule_id = case_data.get("rule_id", f"rule_{case_id}")
            print(f"Would create case-rule relationship for {case_id} (disabled for debugging)")
            
            # Find similar cases in Redis
            similar_cases = await self._find_similar_cases(entities, case_data)
            
            # Create related cases in Neo4j (temporarily disabled for debugging)
            if similar_cases:
                print(f"Would create {len(similar_cases)} related cases in Neo4j (disabled for debugging)")
            
            # Extract case IDs for Exabeam lookup - include the current case AND similar cases
            case_ids = [case_id]  # Start with the current case
            case_ids.extend([case["case_id"] for case in similar_cases])  # Add similar cases
            
            # Remove duplicates while preserving order
            case_ids = list(dict.fromkeys(case_ids))
            
            # Fetch raw data from Exabeam for ALL cases (current + similar)
            raw_cases = await self._fetch_exabeam_raw_data(case_ids)
            
            # Apply rule filtering
            filtering_results = self._apply_rule_filter(raw_cases)
            
            # Enrich entities with context
            enriched_entities = await self._enrich_entities(entities, similar_cases)
            
            # Store observed entities in Neo4j (temporarily disabled for debugging)
            for entity in enriched_entities:
                entity_type = entity.get("type", "unknown")
                entity_value = entity.get("value", "")
                if entity_value:
                    print(f"Would store entity {entity_type}:{entity_value} in Neo4j (disabled for debugging)")
            
            return {
                "related_items": similar_cases,
                "raw_cases": raw_cases,
                "kept_cases": filtering_results["kept_cases"],
                "skipped_cases": filtering_results["skipped_cases"],
                "enriched_entities": enriched_entities,
                "similarity_analysis": {
                    "method": "entity_overlap",
                    "threshold": 0.3,
                    "total_found": len(similar_cases)
                },
                "rule_filter_summary": {
                    "total_cases": len(raw_cases),
                    "siem_eligible": len(filtering_results["kept_cases"]),
                    "skipped": len(filtering_results["skipped_cases"])
                }
            }
            
        except Exception as e:
            logger.error(f"Enrichment processing failed: {e}")
            return {
                "error": f"Enrichment processing failed: {str(e)}",
                "related_items": [],
                "raw_cases": [],
                "kept_cases": [],
                "skipped_cases": []
            }