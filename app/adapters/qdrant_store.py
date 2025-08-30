"""
Qdrant vector database adapter for knowledge storage and retrieval
"""
import os
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http import models
    from qdrant_client.http.models import Distance, VectorParams
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False

logger = logging.getLogger(__name__)

class QdrantStore:
    """Qdrant vector database adapter for knowledge management"""
    
    def __init__(self):
        self.host = os.getenv("QDRANT_HOST", "localhost")
        self.port = int(os.getenv("QDRANT_PORT", "6333"))
        self.api_key = os.getenv("QDRANT_API_KEY")
        self.collection_name = "soc_knowledge"
        self.client = None
        self.initialized = False
        
        if not QDRANT_AVAILABLE:
            logger.warning("Qdrant client not available, using mock mode")
    
    async def _ensure_connection(self):
        """Ensure Qdrant connection and collection exists"""
        if self.initialized:
            return
        
        if not QDRANT_AVAILABLE:
            logger.warning("Qdrant not available, using mock mode")
            return
        
        try:
            # Initialize client
            if self.api_key:
                self.client = QdrantClient(
                    host=self.host,
                    port=self.port,
                    api_key=self.api_key
                )
            else:
                self.client = QdrantClient(host=self.host, port=self.port)
            
            # Create collection if it doesn't exist
            collections = await asyncio.to_thread(self.client.get_collections)
            collection_exists = any(
                collection.name == self.collection_name 
                for collection in collections.collections
            )
            
            if not collection_exists:
                await asyncio.to_thread(
                    self.client.create_collection,
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=384, distance=Distance.COSINE)  # all-MiniLM-L6-v2 size
                )
                logger.info(f"Created Qdrant collection: {self.collection_name}")
            
            self.initialized = True
            logger.info("Qdrant connection initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize Qdrant: {e}")
            self.client = None
    
    async def store_knowledge_item(self, knowledge_item: Dict[str, Any], embeddings: List[float] = None) -> bool:
        """Store a knowledge item with embeddings in Qdrant"""
        await self._ensure_connection()
        
        if not self.client:
            logger.warning("Qdrant not available, knowledge item not stored")
            return False
        
        try:
            # Generate embeddings if not provided
            if embeddings is None:
                embeddings = await self._generate_embeddings(knowledge_item.get("text", ""))
            
            # Create point for Qdrant
            point = models.PointStruct(
                id=hash(knowledge_item["id"]) & 0x7FFFFFFFFFFFFFFF,  # Convert to positive int
                vector=embeddings,
                payload={
                    "id": knowledge_item["id"],
                    "kind": knowledge_item.get("kind", "general"),
                    "author": knowledge_item.get("author", "system"),
                    "created_at": knowledge_item.get("created_at"),
                    "case_id": knowledge_item.get("case_id"),
                    "text": knowledge_item.get("text", ""),
                    "tags": knowledge_item.get("tags", []),
                    "trust": knowledge_item.get("trust", "medium"),
                    "links": knowledge_item.get("links", [])
                }
            )
            
            # Store in Qdrant
            await asyncio.to_thread(
                self.client.upsert,
                collection_name=self.collection_name,
                points=[point]
            )
            
            logger.info(f"Stored knowledge item in Qdrant: {knowledge_item['id']}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store knowledge item: {e}")
            return False
    
    async def search_knowledge(self, query: str, limit: int = 10, min_score: float = 0.3) -> List[Dict[str, Any]]:
        """Search for relevant knowledge items using vector similarity"""
        await self._ensure_connection()
        
        if not self.client:
            logger.warning("Qdrant not available, returning mock data")
            return self._get_mock_knowledge_results(query, limit)
        
        try:
            # Generate query embeddings
            query_embeddings = await self._generate_embeddings(query)
            
            # Search Qdrant
            search_results = await asyncio.to_thread(
                self.client.search,
                collection_name=self.collection_name,
                query_vector=query_embeddings,
                limit=limit,
                score_threshold=min_score
            )
            
            # Format results
            knowledge_items = []
            for result in search_results:
                item = result.payload
                item["relevance_score"] = result.score
                knowledge_items.append(item)
            
            logger.info(f"Found {len(knowledge_items)} knowledge items for query: {query[:50]}")
            return knowledge_items
            
        except Exception as e:
            logger.error(f"Knowledge search failed: {e}")
            return self._get_mock_knowledge_results(query, limit)
    
    async def _generate_embeddings(self, text: str) -> List[float]:
        """Generate embeddings for text using a simple embedding model"""
        try:
            # In a real implementation, use a proper embedding model like sentence-transformers
            # For now, create simple hash-based embeddings for testing
            import hashlib
            
            # Create deterministic but varied embeddings based on text
            hash_obj = hashlib.md5(text.encode())
            hash_hex = hash_obj.hexdigest()
            
            # Convert to 384-dimensional vector (matching all-MiniLM-L6-v2)
            embeddings = []
            for i in range(0, len(hash_hex), 2):
                # Convert hex pairs to normalized floats
                val = int(hash_hex[i:i+2], 16) / 255.0
                embeddings.append(val * 2 - 1)  # Normalize to [-1, 1]
            
            # Pad to 384 dimensions
            while len(embeddings) < 384:
                embeddings.extend(embeddings[:384-len(embeddings)])
            
            return embeddings[:384]
            
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            # Return random embeddings as fallback
            import random
            return [random.uniform(-1, 1) for _ in range(384)]
    
    def _get_mock_knowledge_results(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Generate mock knowledge results when Qdrant is unavailable"""
        mock_knowledge = [
            {
                "id": "know_apt_tactics",
                "kind": "threat_intel",
                "author": "threat_analyst",
                "created_at": "2025-08-15T10:00:00Z",
                "case_id": None,
                "text": "Advanced Persistent Threat groups commonly use RDP, SMB, and WMI for lateral movement",
                "tags": ["apt", "lateral_movement", "rdp", "smb"],
                "links": [],
                "trust": "high",
                "relevance_score": 0.85
            },
            {
                "id": "know_powershell_analysis",
                "kind": "sop", 
                "author": "soc_team",
                "created_at": "2025-08-10T14:30:00Z",
                "case_id": None,
                "text": "Standard procedures for analyzing PowerShell-based attacks and encoded commands",
                "tags": ["powershell", "analysis", "sop"],
                "links": [],
                "trust": "high",
                "relevance_score": 0.78
            },
            {
                "id": "know_network_isolation",
                "kind": "sop",
                "author": "incident_response",
                "created_at": "2025-08-05T09:15:00Z",
                "case_id": None,
                "text": "Step-by-step procedures for isolating compromised systems",
                "tags": ["isolation", "containment", "network"],
                "links": [],
                "trust": "high",
                "relevance_score": 0.72
            },
            {
                "id": "know_lateral_movement_detection",
                "kind": "investigation",
                "author": "analyst_smith",
                "created_at": "2025-08-20T16:45:00Z",
                "case_id": "CASE-2025-001",
                "text": "Investigation findings on lateral movement techniques using SMB and WMI",
                "tags": ["lateral_movement", "smb", "wmi", "detection"],
                "links": [],
                "trust": "medium",
                "relevance_score": 0.68
            }
        ]
        
        # Simple text-based filtering for mock results
        query_lower = query.lower()
        relevant_items = []
        
        for item in mock_knowledge:
            score = 0.0
            
            # Check tags
            for tag in item.get("tags", []):
                if tag.lower() in query_lower:
                    score += 0.3
            
            # Check text content
            if any(word in item["text"].lower() for word in query_lower.split() if len(word) > 2):
                score += 0.6
            
            if score > 0.2:  # Lower threshold for mock data
                item["relevance_score"] = score
                relevant_items.append(item)
        
        # Sort by relevance and limit
        relevant_items.sort(key=lambda x: x["relevance_score"], reverse=True)
        return relevant_items[:limit]
    
    async def get_knowledge_by_id(self, knowledge_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific knowledge item by ID"""
        await self._ensure_connection()
        
        if not self.client:
            return None
        
        try:
            # Search by ID in payload
            results = await asyncio.to_thread(
                self.client.scroll,
                collection_name=self.collection_name,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="id",
                            match=models.MatchValue(value=knowledge_id)
                        )
                    ]
                ),
                limit=1
            )
            
            if results[0]:  # results is a tuple (points, next_page_offset)
                point = results[0][0]
                return point.payload
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to retrieve knowledge item {knowledge_id}: {e}")
            return None
    
    async def delete_knowledge_item(self, knowledge_id: str) -> bool:
        """Delete a knowledge item by ID"""
        await self._ensure_connection()
        
        if not self.client:
            return False
        
        try:
            await asyncio.to_thread(
                self.client.delete,
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="id",
                                match=models.MatchValue(value=knowledge_id)
                            )
                        ]
                    )
                )
            )
            
            logger.info(f"Deleted knowledge item: {knowledge_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete knowledge item {knowledge_id}: {e}")
            return False


# Global Qdrant store instance
qdrant_store = QdrantStore()