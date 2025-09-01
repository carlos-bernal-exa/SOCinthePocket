"""
Neo4j Graph Store implementing Cypher Templates from 03_Cypher_Templates.md
"""
import asyncio
import logging
from typing import Dict, Any, List, Optional
from neo4j import GraphDatabase
import os

logger = logging.getLogger(__name__)

class Neo4jStore:
    def __init__(self, uri: str = None, username: str = None, password: str = None):
        self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.username = username or os.getenv("NEO4J_USERNAME", "neo4j") 
        self.password = password or os.getenv("NEO4J_PASSWORD", "soc_neo4j_password")
        self.driver = None
        
    async def connect(self):
        """Initialize Neo4j driver connection"""
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.username, self.password))
            logger.info("Connected to Neo4j")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            
    async def close(self):
        """Close Neo4j driver connection"""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j connection closed")
    
    # Template 1: Case + Rule
    async def create_case_rule_relationship(self, case_id: str, rule_id: str):
        """
        Create Case and Rule nodes with TRIGGERED_BY relationship
        MERGE (c:Case {id: $case_id})
        MERGE (r:Rule {id: $rule_id})
        MERGE (c)-[:TRIGGERED_BY]->(r)
        """
        if not self.driver:
            await self.connect()
            
        cypher = """
        MERGE (c:Case {id: $case_id})
        MERGE (r:Rule {id: $rule_id})
        MERGE (c)-[:TRIGGERED_BY]->(r)
        RETURN c, r
        """
        
        try:
            with self.driver.session() as session:
                result = session.run(cypher, case_id=case_id, rule_id=rule_id)
                record = result.single()
                logger.info(f"Created Case-Rule relationship: {case_id} -> {rule_id}")
                return record
        except Exception as e:
            logger.error(f"Failed to create case-rule relationship: {e}")
            return None
    
    # Template 2: Observed Entities  
    async def create_observed_entity(self, case_id: str, entity_type: str, entity_value: str):
        """
        Create observed entity relationships
        MERGE (i:IP {value: $ip})
        MERGE (c:Case {id:$case_id})-[:OBSERVED_IN]->(i)
        """
        if not self.driver:
            await self.connect()
            
        # Map entity types to node labels
        label_map = {
            "ip": "IP",
            "user": "User", 
            "host": "Host",
            "domain": "Domain",
            "hash": "Hash"
        }
        
        label = label_map.get(entity_type.lower(), "Entity")
        
        cypher = f"""
        MERGE (e:{label} {{value: $entity_value}})
        MERGE (c:Case {{id: $case_id}})
        MERGE (c)-[:OBSERVED_IN]->(e)
        RETURN c, e
        """
        
        try:
            with self.driver.session() as session:
                result = session.run(cypher, case_id=case_id, entity_value=entity_value)
                record = result.single()
                logger.info(f"Created observed entity: {case_id} -> {entity_type}:{entity_value}")
                return record
        except Exception as e:
            logger.error(f"Failed to create observed entity: {e}")
            return None
    
    # Template 3: Related Cases
    async def create_related_cases(self, case_id: str, related_cases: List[Dict[str, Any]]):
        """
        Create relationships between related cases
        UNWIND $related AS rel
        MATCH (c:Case {id:$case_id})
        MERGE (d:Case {id: rel.id})
        MERGE (c)-[r:RELATES_TO]->(d)
        SET r.score = rel.score
        """
        if not self.driver:
            await self.connect()
            
        cypher = """
        UNWIND $related AS rel
        MATCH (c:Case {id:$case_id})
        MERGE (d:Case {id: rel.id})
        MERGE (c)-[r:RELATES_TO]->(d)
        SET r.score = rel.score
        RETURN c, r, d
        """
        
        try:
            with self.driver.session() as session:
                result = session.run(cypher, case_id=case_id, related=related_cases)
                records = list(result)
                logger.info(f"Created {len(records)} related case relationships for {case_id}")
                return records
        except Exception as e:
            logger.error(f"Failed to create related cases: {e}")
            return []
    
    # Template 4: Knowledge Items
    async def create_knowledge_item(self, knowledge_id: str, kind: str, author: str, created_at: str, text: str = None, tags: List[str] = None, trust: str = None, embeddings_ref: str = None, **additional_props):
        """
        Create knowledge item nodes
        MERGE (k:KnowledgeItem {id:$kid})
        SET k.kind=$kind, k.author=$author, k.created_at=datetime($created_at)
        """
        if not self.driver:
            await self.connect()
            
        cypher = """
        MERGE (k:KnowledgeItem {id:$kid})
        SET k.kind=$kind, k.author=$author, k.created_at=datetime($created_at)
        """
        
        # Add additional properties dynamically
        set_clauses = []
        
        # Add specific property setters
        if text:
            set_clauses.append("k.text=$text")
        if tags:
            set_clauses.append("k.tags=$tags")
        if trust:
            set_clauses.append("k.trust=$trust")
        if embeddings_ref:
            set_clauses.append("k.embeddings_ref=$embeddings_ref")
            
        # Add any additional properties
        if additional_props:
            for key, value in additional_props.items():
                set_clauses.append(f"k.{key}=${key}")
        
        if set_clauses:
            cypher += ", " + ", ".join(set_clauses)
        
        cypher += " RETURN k"
        
        params = {
            "kid": knowledge_id,
            "kind": kind,
            "author": author, 
            "created_at": created_at
        }
        
        # Add specific fields
        if text:
            params["text"] = text
        if tags:
            params["tags"] = tags
        if trust:
            params["trust"] = trust
        if embeddings_ref:
            params["embeddings_ref"] = embeddings_ref
        
        # Add any additional properties
        params.update(additional_props)
        
        try:
            with self.driver.session() as session:
                result = session.run(cypher, **params)
                record = result.single()
                logger.info(f"Created knowledge item: {knowledge_id}")
                return record
        except Exception as e:
            logger.error(f"Failed to create knowledge item: {e}")
            return None
    
    # Legacy method for backward compatibility
    async def upsert_case_rule_entities(self, case_id: str, inv: dict, enr: dict, source_label: str, ts: str):
        """Legacy method - creates case with entities from investigation and enrichment"""
        try:
            # Create case first
            await self.create_case_rule_relationship(case_id, f"rule_{case_id}")
            
            # Add entities from investigation
            ioc_set = inv.get("ioc_set", {})
            for entity_type, entities in ioc_set.items():
                if isinstance(entities, list):
                    for entity_value in entities:
                        await self.create_observed_entity(case_id, entity_type.rstrip('s'), entity_value)
            
            # Add related cases from enrichment  
            related_items = enr.get("related_items", [])
            if related_items:
                related_cases = []
                for item in related_items:
                    related_cases.append({
                        "id": item.get("case_id", "unknown"),
                        "score": item.get("similarity_score", 0.5)
                    })
                await self.create_related_cases(case_id, related_cases)
                
            return True
            
        except Exception as e:
            logger.error(f"Failed to upsert case entities: {e}")
            return False

    async def get_graph_visualization_data(self, limit: int = 50):
        """Get graph data for visualization in frontend"""
        if not self.driver:
            await self.connect()
            
        cypher = """
        MATCH (n)-[r]->(m)
        RETURN n, r, m
        LIMIT $limit
        """
        
        try:
            with self.driver.session() as session:
                result = session.run(cypher, limit=limit)
                
                nodes = {}
                edges = []
                
                for record in result:
                    n = record["n"]
                    r = record["r"] 
                    m = record["m"]
                    
                    # Add source node
                    node_id = n.element_id
                    if node_id not in nodes:
                        labels = list(n.labels)
                        # Use 'value' property if available, otherwise 'id', otherwise label
                        label = n.get("value") or n.get("id") or (labels[0] if labels else "Node")
                        nodes[node_id] = {
                            "id": node_id,
                            "label": label,
                            "type": labels[0] if labels else "Unknown",
                            "properties": dict(n)
                        }
                    
                    # Add target node
                    target_id = m.element_id
                    if target_id not in nodes:
                        labels = list(m.labels)
                        # Use 'value' property if available, otherwise 'id', otherwise label
                        label = m.get("value") or m.get("id") or (labels[0] if labels else "Node")
                        nodes[target_id] = {
                            "id": target_id,
                            "label": label,
                            "type": labels[0] if labels else "Unknown", 
                            "properties": dict(m)
                        }
                    
                    # Add edge
                    edges.append({
                        "from": node_id,
                        "to": target_id,
                        "relationship": r.type,
                        "properties": dict(r)
                    })
                
                return {
                    "nodes": list(nodes.values()),
                    "edges": edges
                }
                
        except Exception as e:
            logger.error(f"Failed to get graph visualization data: {e}")
            return {"nodes": [], "edges": []}

# Global instance
neo4j_store = Neo4jStore()
