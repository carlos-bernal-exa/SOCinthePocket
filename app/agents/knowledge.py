"""
KnowledgeAgent - Ingest and retrieve security knowledge
"""
import asyncio
from typing import Dict, Any, List, Optional
from .base import AgentBase
from ..adapters.neo4j_store import neo4j_store
from ..adapters.qdrant_store import qdrant_store
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class KnowledgeAgent(AgentBase):
    """
    Knowledge Agent that ingests, stores, and retrieves security knowledge
    including SOPs, threat intelligence, past investigations, and lessons learned.
    """
    
    def __init__(self):
        super().__init__(
            name="KnowledgeAgent", 
            model="gemini-2.5-flash-lite",
            role="knowledge"
        )
    
    def _format_prompt(self, prompt_content: str, inputs: Dict[str, Any]) -> str:
        """Format knowledge-specific prompt"""
        case_id = inputs.get("case_id", "unknown")
        operation = inputs.get("operation", "retrieve")
        query = inputs.get("query", "")
        knowledge_items = inputs.get("knowledge_items", [])
        
        formatted = f"""You are a SOC Knowledge Management Agent for case {case_id}.

Your role is to:
1. Ingest, store, and retrieve security knowledge
2. Provide contextual knowledge retrieval for ongoing investigations
3. Manage SOPs, threat intelligence, past investigations, and lessons learned
4. Support knowledge discovery and correlation across cases

Operation: {operation}
Query: {query}

Available Knowledge Types:
- SOPs: Standard Operating Procedures for incident response
- Threat Intel: External threat intelligence and IOCs
- Investigations: Past investigation results and findings
- Lessons Learned: Post-incident analysis and improvements

Knowledge Items Available:
{json.dumps(knowledge_items, indent=2)}

For retrieval operations, provide relevant knowledge items with:
1. Relevance scoring based on query similarity
2. Knowledge type classification
3. Source attribution and trust levels
4. Contextual relationships to current investigation

For ingestion operations, structure knowledge with:
1. Proper categorization and tagging
2. Trust level assessment
3. Source verification
4. Integration with existing knowledge base

Respond with structured knowledge results."""

        return formatted
    
    async def _ingest_knowledge(self, knowledge_data: Dict[str, Any]) -> Dict[str, Any]:
        """Ingest new knowledge into the system with Neo4j storage"""
        # Generate ID first
        item_id = f"know_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # KnowledgeItem following data contract: id, kind, author, created_at, case_id?, text, tags[], links[], trust, embeddings_ref?
        knowledge_item = {
            "id": item_id,
            "kind": knowledge_data.get("type", "general"),
            "author": knowledge_data.get("author", "system"),
            "created_at": datetime.now().isoformat(),
            "case_id": knowledge_data.get("case_id"),  # Optional field
            "text": knowledge_data.get("content", ""),
            "tags": knowledge_data.get("tags", []),
            "links": knowledge_data.get("links", []),
            "trust": self._assess_trust_level(knowledge_data),
            "embeddings_ref": f"embed_{item_id}"  # Optional field
        }
        
        # Store in Neo4j using knowledge items template
        await neo4j_store.create_knowledge_item(
            knowledge_id=knowledge_item["id"],
            kind=knowledge_item["kind"],
            author=knowledge_item["author"],
            created_at=knowledge_item["created_at"],
            text=knowledge_item["text"],
            tags=knowledge_item["tags"],
            trust=knowledge_item["trust"],
            embeddings_ref=knowledge_item.get("embeddings_ref")
        )
        
        # Store in Qdrant with embeddings
        qdrant_success = await qdrant_store.store_knowledge_item(knowledge_item)
        
        logger.info(f"Ingested knowledge item: {knowledge_item['id']} (Neo4j: ✓, Qdrant: {'✓' if qdrant_success else '✗'})")
        
        return {
            "knowledge_id": knowledge_item["id"],
            "status": "ingested",
            "trust": knowledge_item["trust"],
            "embeddings_created": qdrant_success,
            "neo4j_stored": True,
            "qdrant_stored": qdrant_success
        }
    
    def _assess_trust_level(self, knowledge_data: Dict) -> str:
        """Assess trust level of knowledge source"""
        author = knowledge_data.get("author", "")
        source_type = knowledge_data.get("type", "")
        
        if author == "system" or source_type == "sop":
            return "high"
        elif source_type in ["threat_intel", "investigation"]:
            return "medium"
        else:
            return "low"
    
    async def _retrieve_knowledge(self, query: str, limit: int = 10) -> List[Dict]:
        """Retrieve relevant knowledge items using Qdrant vector search"""
        try:
            # Use Qdrant for semantic knowledge retrieval
            knowledge_items = await qdrant_store.search_knowledge(
                query=query,
                limit=limit,
                min_score=0.3
            )
            
            logger.info(f"Retrieved {len(knowledge_items)} knowledge items for query: {query[:50]}")
            return knowledge_items
            
        except Exception as e:
            logger.error(f"Knowledge retrieval failed: {e}")
            # Return empty list on error
            return []
    
    def _create_knowledge_summary(self, knowledge_items: List[Dict], query: str) -> Dict[str, Any]:
        """Create summary of retrieved knowledge"""
        if not knowledge_items:
            return {
                "summary": f"No relevant knowledge found for query: {query}",
                "items_found": 0,
                "categories": []
            }
        
        # Categorize knowledge
        categories = {}
        for item in knowledge_items:
            kind = item.get("kind", "general")
            if kind not in categories:
                categories[kind] = []
            categories[kind].append(item)
        
        # Create summary
        summary_parts = []
        for kind, items in categories.items():
            summary_parts.append(f"{len(items)} {kind} items")
        
        return {
            "summary": f"Found {len(knowledge_items)} relevant items: {', '.join(summary_parts)}",
            "items_found": len(knowledge_items),
            "categories": list(categories.keys()),
            "average_relevance": sum(item.get("relevance_score", 0) for item in knowledge_items) / len(knowledge_items),
            "top_relevance": max(item.get("relevance_score", 0) for item in knowledge_items)
        }
    
    async def process(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Process knowledge management logic"""
        try:
            operation = inputs.get("operation", "retrieve")
            case_id = inputs.get("case_id")
            
            if operation == "ingest":
                # Ingest new knowledge
                knowledge_data = inputs.get("knowledge_data", {})
                result = await self._ingest_knowledge(knowledge_data)
                
                return {
                    "operation": "ingest",
                    "result": result,
                    "knowledge_id": result.get("knowledge_id"),
                    "status": "success"
                }
            
            elif operation == "retrieve":
                # Retrieve relevant knowledge
                query = inputs.get("query", "")
                limit = inputs.get("limit", 10)
                
                knowledge_items = await self._retrieve_knowledge(query, limit)
                knowledge_summary = self._create_knowledge_summary(knowledge_items, query)
                
                return {
                    "operation": "retrieve",
                    "query": query,
                    "knowledge_items": knowledge_items,
                    "knowledge_summary": knowledge_summary,
                    "contextual_recommendations": self._generate_contextual_recommendations(knowledge_items),
                    "status": "success"
                }
            
            else:
                return {
                    "error": f"Unknown operation: {operation}",
                    "status": "failed"
                }
                
        except Exception as e:
            logger.error(f"Knowledge processing failed: {e}")
            return {
                "error": f"Knowledge processing failed: {str(e)}",
                "operation": inputs.get("operation", "unknown"),
                "status": "failed"
            }
    
    def _generate_contextual_recommendations(self, knowledge_items: List[Dict]) -> List[str]:
        """Generate contextual recommendations based on retrieved knowledge"""
        recommendations = []
        
        # Analyze knowledge types and suggest actions
        sop_items = [item for item in knowledge_items if item.get("kind") == "sop"]
        threat_intel_items = [item for item in knowledge_items if item.get("kind") == "threat_intel"]
        
        if sop_items:
            recommendations.append(f"Review {len(sop_items)} relevant SOPs for procedural guidance")
        
        if threat_intel_items:
            recommendations.append(f"Consider {len(threat_intel_items)} threat intelligence items for context")
        
        # Check for high-relevance items
        high_relevance = [item for item in knowledge_items if item.get("relevance_score", 0) > 0.8]
        if high_relevance:
            recommendations.append(f"High relevance match found: {high_relevance[0].get('title', 'Unknown')}")
        
        return recommendations