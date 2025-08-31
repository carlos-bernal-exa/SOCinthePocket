"""
Enhanced Neo4j Graph Store with batch operations, hygiene, and optimization.

This module provides improved Neo4j integration with:
- Batch node upserts using UNWIND for performance
- Nightly hygiene jobs to prune orphan nodes
- Case-insensitive host/domain deduplication
- Connection pooling and retry logic
- Performance monitoring and statistics
"""

import asyncio
import logging
import time
import hashlib
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
import neo4j
from neo4j import GraphDatabase

logger = logging.getLogger(__name__)


@dataclass
class BatchUpsertStats:
    """Statistics for batch upsert operations."""
    total_nodes: int = 0
    created_nodes: int = 0
    updated_nodes: int = 0
    relationships_created: int = 0
    execution_time_ms: int = 0
    errors: int = 0


@dataclass
class HygieneStats:
    """Statistics for hygiene operations."""
    orphan_nodes_removed: int = 0
    duplicate_nodes_merged: int = 0
    execution_time_ms: int = 0
    affected_node_types: List[str] = field(default_factory=list)


class EnhancedNeo4jStore:
    """
    Enhanced Neo4j store with batch operations and maintenance features.
    """
    
    def __init__(
        self, 
        uri: str = "bolt://localhost:7687",
        username: str = "neo4j",
        password: str = "soc_neo4j_password",
        max_connections: int = 10,
        batch_size: int = 100
    ):
        self.uri = uri
        self.username = username
        self.password = password
        self.max_connections = max_connections
        self.batch_size = batch_size
        self.driver = None
        
        # Statistics
        self.stats = {
            'total_operations': 0,
            'batch_upserts': 0,
            'hygiene_runs': 0,
            'connection_errors': 0,
            'query_retries': 0
        }
    
    async def connect(self):
        """Initialize Neo4j driver with enhanced connection settings."""
        try:
            self.driver = GraphDatabase.driver(
                self.uri,
                auth=(self.username, self.password),
                max_connection_pool_size=self.max_connections,
                connection_timeout=30,
                max_retry_time=30
            )
            
            # Test connection
            with self.driver.session() as session:
                session.run("RETURN 1")
            
            logger.info(f"Connected to Neo4j at {self.uri} with pool size {self.max_connections}")
            
        except Exception as e:
            self.stats['connection_errors'] += 1
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise
    
    async def close(self):
        """Close Neo4j driver connection."""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j connection closed")
    
    @asynccontextmanager
    async def get_session(self):
        """Context manager for Neo4j sessions with error handling."""
        if not self.driver:
            await self.connect()
        
        session = self.driver.session()
        try:
            yield session
        finally:
            session.close()
    
    def _execute_with_retry(self, session, query: str, parameters: dict, max_retries: int = 3):
        """Execute query with retry logic."""
        last_error = None
        
        for attempt in range(max_retries):
            try:
                result = session.run(query, parameters)
                return result
            except neo4j.exceptions.TransientError as e:
                self.stats['query_retries'] += 1
                last_error = e
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) * 0.1  # Exponential backoff
                    time.sleep(wait_time)
                    logger.warning(f"Query retry {attempt + 1}/{max_retries} after {wait_time}s: {e}")
            except Exception as e:
                logger.error(f"Non-retryable error in query execution: {e}")
                raise
        
        raise last_error
    
    async def batch_upsert_nodes(
        self, 
        node_data: List[Dict[str, Any]], 
        node_type: str,
        merge_keys: List[str]
    ) -> BatchUpsertStats:
        """
        Batch upsert nodes using UNWIND for performance.
        
        Args:
            node_data: List of node property dictionaries
            node_type: Node label (Case, Rule, IP, Host, User, Domain)
            merge_keys: Keys to use for MERGE operation
            
        Returns:
            BatchUpsertStats with operation details
        """
        if not node_data:
            return BatchUpsertStats()
        
        start_time = time.time()
        stats = BatchUpsertStats(total_nodes=len(node_data))
        
        try:
            async with self.get_session() as session:
                # Build MERGE clause based on keys
                merge_conditions = ", ".join([f"{key}: item.{key}" for key in merge_keys])
                
                # Build SET clause for all other properties
                all_keys = set()
                for item in node_data:
                    all_keys.update(item.keys())
                
                set_keys = all_keys - set(merge_keys)
                set_clause = ", ".join([f"n.{key} = item.{key}" for key in set_keys])
                
                query = f"""
                UNWIND $items AS item
                MERGE (n:{node_type} {{{merge_conditions}}})
                """
                
                if set_clause:
                    query += f"SET {set_clause}"
                
                query += """
                RETURN 
                    count(*) as total_processed,
                    count(CASE WHEN n.created_at IS NULL THEN 1 END) as newly_created
                """
                
                # Process in batches
                total_created = 0
                for i in range(0, len(node_data), self.batch_size):
                    batch = node_data[i:i + self.batch_size]
                    
                    result = self._execute_with_retry(
                        session, query, {'items': batch}
                    )
                    
                    record = result.single()
                    if record:
                        batch_created = record.get('newly_created', 0)
                        total_created += batch_created
                        
                        logger.debug(f"Processed batch {i//self.batch_size + 1}: "
                                   f"{len(batch)} items, {batch_created} new nodes")
                
                stats.created_nodes = total_created
                stats.updated_nodes = stats.total_nodes - total_created
                
                self.stats['batch_upserts'] += 1
                logger.info(f"Batch upsert complete: {stats.total_nodes} {node_type} nodes "
                           f"({stats.created_nodes} created, {stats.updated_nodes} updated)")
                
        except Exception as e:
            stats.errors += 1
            logger.error(f"Batch upsert failed for {node_type}: {e}")
            
        finally:
            stats.execution_time_ms = int((time.time() - start_time) * 1000)
            self.stats['total_operations'] += 1
        
        return stats
    
    async def batch_upsert_relationships(
        self,
        relationship_data: List[Dict[str, Any]],
        relationship_type: str,
        from_node_type: str,
        to_node_type: str,
        from_key: str,
        to_key: str
    ) -> BatchUpsertStats:
        """
        Batch upsert relationships using UNWIND.
        
        Args:
            relationship_data: List of relationship property dictionaries
            relationship_type: Relationship type (TRIGGERED_BY, OBSERVED_IN, etc.)
            from_node_type: Source node label
            to_node_type: Target node label  
            from_key: Property key for source node matching
            to_key: Property key for target node matching
            
        Returns:
            BatchUpsertStats with operation details
        """
        if not relationship_data:
            return BatchUpsertStats()
        
        start_time = time.time()
        stats = BatchUpsertStats(total_nodes=len(relationship_data))
        
        try:
            async with self.get_session() as session:
                # Build relationship properties if any
                rel_properties = set()
                for item in relationship_data:
                    rel_properties.update(item.keys() - {from_key, to_key})
                
                set_clause = ""
                if rel_properties:
                    props = ", ".join([f"r.{key} = item.{key}" for key in rel_properties])
                    set_clause = f"SET {props}"
                
                query = f"""
                UNWIND $items AS item
                MATCH (from:{from_node_type} {{{from_key}: item.{from_key}}})
                MATCH (to:{to_node_type} {{{to_key}: item.{to_key}}})
                MERGE (from)-[r:{relationship_type}]->(to)
                {set_clause}
                RETURN count(*) as relationships_created
                """
                
                # Process in batches
                total_relationships = 0
                for i in range(0, len(relationship_data), self.batch_size):
                    batch = relationship_data[i:i + self.batch_size]
                    
                    result = self._execute_with_retry(
                        session, query, {'items': batch}
                    )
                    
                    record = result.single()
                    if record:
                        batch_rels = record.get('relationships_created', 0)
                        total_relationships += batch_rels
                
                stats.relationships_created = total_relationships
                logger.info(f"Batch relationship upsert complete: {total_relationships} {relationship_type} relationships")
                
        except Exception as e:
            stats.errors += 1
            logger.error(f"Batch relationship upsert failed: {e}")
            
        finally:
            stats.execution_time_ms = int((time.time() - start_time) * 1000)
        
        return stats
    
    async def run_hygiene_job(self, dry_run: bool = False) -> HygieneStats:
        """
        Run nightly hygiene job to clean up orphan nodes and duplicates.
        
        Args:
            dry_run: If True, only report what would be cleaned without making changes
            
        Returns:
            HygieneStats with cleanup details
        """
        start_time = time.time()
        stats = HygieneStats()
        
        logger.info(f"Starting hygiene job (dry_run={dry_run})...")
        
        try:
            async with self.get_session() as session:
                # 1. Remove orphan nodes (nodes with no relationships)
                orphan_stats = await self._cleanup_orphan_nodes(session, dry_run)
                stats.orphan_nodes_removed = orphan_stats
                
                # 2. Merge duplicate hosts (case-insensitive)
                host_merge_stats = await self._merge_duplicate_hosts(session, dry_run)
                stats.duplicate_nodes_merged += host_merge_stats
                stats.affected_node_types.append('Host')
                
                # 3. Merge duplicate domains (case-insensitive)  
                domain_merge_stats = await self._merge_duplicate_domains(session, dry_run)
                stats.duplicate_nodes_merged += domain_merge_stats
                stats.affected_node_types.append('Domain')
                
                # 4. Remove old temporary nodes (older than 30 days)
                temp_cleanup_stats = await self._cleanup_temp_nodes(session, dry_run)
                stats.orphan_nodes_removed += temp_cleanup_stats
                
                self.stats['hygiene_runs'] += 1
                logger.info(f"Hygiene job complete: {stats.orphan_nodes_removed} orphans removed, "
                           f"{stats.duplicate_nodes_merged} duplicates merged")
                
        except Exception as e:
            logger.error(f"Hygiene job failed: {e}")
            
        finally:
            stats.execution_time_ms = int((time.time() - start_time) * 1000)
        
        return stats
    
    async def _cleanup_orphan_nodes(self, session, dry_run: bool) -> int:
        """Remove orphan nodes with no relationships."""
        query = """
        MATCH (n)
        WHERE NOT (n)--()
        """
        
        if dry_run:
            query += "RETURN count(n) as orphan_count"
            result = self._execute_with_retry(session, query, {})
            record = result.single()
            count = record.get('orphan_count', 0) if record else 0
            logger.info(f"Would remove {count} orphan nodes")
            return count
        else:
            query += "DELETE n RETURN count(n) as deleted_count"
            result = self._execute_with_retry(session, query, {})
            record = result.single()
            count = record.get('deleted_count', 0) if record else 0
            logger.info(f"Removed {count} orphan nodes")
            return count
    
    async def _merge_duplicate_hosts(self, session, dry_run: bool) -> int:
        """Merge duplicate host nodes with case-insensitive matching."""
        # Find duplicates (case-insensitive)
        find_query = """
        MATCH (h:Host)
        WITH toLower(h.value) as lower_value, collect(h) as hosts
        WHERE size(hosts) > 1
        RETURN lower_value, hosts
        """
        
        result = self._execute_with_retry(session, find_query, {})
        duplicate_groups = list(result)
        
        if not duplicate_groups:
            return 0
        
        if dry_run:
            total_duplicates = sum(len(record['hosts']) - 1 for record in duplicate_groups)
            logger.info(f"Would merge {total_duplicates} duplicate host nodes")
            return total_duplicates
        
        # Merge duplicates
        merged_count = 0
        for record in duplicate_groups:
            hosts = record['hosts']
            if len(hosts) <= 1:
                continue
            
            # Keep the first host, merge others into it
            primary_host = hosts[0]
            duplicate_hosts = hosts[1:]
            
            merge_query = """
            UNWIND $duplicate_ids AS dup_id
            MATCH (primary:Host {value: $primary_value})
            MATCH (duplicate:Host) WHERE id(duplicate) = dup_id
            MATCH (duplicate)-[r]-(other)
            CREATE (primary)-[r2]-(other)
            SET r2 = properties(r)
            DELETE r, duplicate
            """
            
            parameters = {
                'primary_value': primary_host['value'],
                'duplicate_ids': [host.id for host in duplicate_hosts]
            }
            
            self._execute_with_retry(session, merge_query, parameters)
            merged_count += len(duplicate_hosts)
        
        logger.info(f"Merged {merged_count} duplicate host nodes")
        return merged_count
    
    async def _merge_duplicate_domains(self, session, dry_run: bool) -> int:
        """Merge duplicate domain nodes with case-insensitive matching."""
        # Similar logic to hosts but for domains
        find_query = """
        MATCH (d:Domain)
        WITH toLower(d.value) as lower_value, collect(d) as domains
        WHERE size(domains) > 1
        RETURN lower_value, domains
        """
        
        result = self._execute_with_retry(session, find_query, {})
        duplicate_groups = list(result)
        
        if not duplicate_groups:
            return 0
        
        if dry_run:
            total_duplicates = sum(len(record['domains']) - 1 for record in duplicate_groups)
            logger.info(f"Would merge {total_duplicates} duplicate domain nodes")
            return total_duplicates
        
        merged_count = 0
        for record in duplicate_groups:
            domains = record['domains']
            if len(domains) <= 1:
                continue
            
            primary_domain = domains[0]
            duplicate_domains = domains[1:]
            
            merge_query = """
            UNWIND $duplicate_ids AS dup_id
            MATCH (primary:Domain {value: $primary_value})
            MATCH (duplicate:Domain) WHERE id(duplicate) = dup_id
            MATCH (duplicate)-[r]-(other)
            CREATE (primary)-[r2]-(other)
            SET r2 = properties(r)
            DELETE r, duplicate
            """
            
            parameters = {
                'primary_value': primary_domain['value'],
                'duplicate_ids': [domain.id for domain in duplicate_domains]
            }
            
            self._execute_with_retry(session, merge_query, parameters)
            merged_count += len(duplicate_domains)
        
        logger.info(f"Merged {merged_count} duplicate domain nodes")
        return merged_count
    
    async def _cleanup_temp_nodes(self, session, dry_run: bool) -> int:
        """Remove temporary nodes older than 30 days."""
        thirty_days_ago = datetime.now() - timedelta(days=30)
        
        query = """
        MATCH (n)
        WHERE n.temporary = true 
        AND n.created_at < datetime($cutoff_date)
        """
        
        if dry_run:
            query += "RETURN count(n) as temp_count"
            result = self._execute_with_retry(session, query, {
                'cutoff_date': thirty_days_ago.isoformat()
            })
            record = result.single()
            count = record.get('temp_count', 0) if record else 0
            logger.info(f"Would remove {count} old temporary nodes")
            return count
        else:
            query += "DELETE n RETURN count(n) as deleted_count"
            result = self._execute_with_retry(session, query, {
                'cutoff_date': thirty_days_ago.isoformat()
            })
            record = result.single()
            count = record.get('deleted_count', 0) if record else 0
            logger.info(f"Removed {count} old temporary nodes")
            return count
    
    async def upsert_case_with_entities(
        self,
        case_id: str,
        rule_id: str,
        entities: Dict[str, List[str]],
        metadata: Dict[str, Any] = None
    ) -> BatchUpsertStats:
        """
        Comprehensive case upsert with all entities and relationships.
        
        This is the main entry point for case creation with full entity graph.
        """
        total_stats = BatchUpsertStats()
        metadata = metadata or {}
        
        try:
            # 1. Upsert Case node
            case_data = [{
                'id': case_id,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                **metadata
            }]
            case_stats = await self.batch_upsert_nodes(case_data, 'Case', ['id'])
            total_stats.created_nodes += case_stats.created_nodes
            total_stats.updated_nodes += case_stats.updated_nodes
            
            # 2. Upsert Rule node
            rule_data = [{
                'id': rule_id,
                'created_at': datetime.now().isoformat()
            }]
            rule_stats = await self.batch_upsert_nodes(rule_data, 'Rule', ['id'])
            total_stats.created_nodes += rule_stats.created_nodes
            total_stats.updated_nodes += rule_stats.updated_nodes
            
            # 3. Create Case -> Rule relationship
            case_rule_rels = [{'case_id': case_id, 'rule_id': rule_id}]
            rel_stats = await self.batch_upsert_relationships(
                case_rule_rels, 'TRIGGERED_BY', 'Case', 'Rule', 'case_id', 'rule_id'
            )
            total_stats.relationships_created += rel_stats.relationships_created
            
            # 4. Upsert entity nodes and relationships
            entity_type_map = {
                'users': 'User',
                'ips': 'IP', 
                'hosts': 'Host',
                'domains': 'Domain'
            }
            
            for entity_type, entity_values in entities.items():
                if not entity_values:
                    continue
                
                node_type = entity_type_map.get(entity_type, 'Entity')
                
                # Create entity nodes
                entity_data = [{'value': value} for value in entity_values]
                entity_stats = await self.batch_upsert_nodes(entity_data, node_type, ['value'])
                total_stats.created_nodes += entity_stats.created_nodes
                total_stats.updated_nodes += entity_stats.updated_nodes
                
                # Create Case -> Entity relationships
                case_entity_rels = [
                    {'case_id': case_id, 'entity_value': value} 
                    for value in entity_values
                ]
                rel_stats = await self.batch_upsert_relationships(
                    case_entity_rels, 'OBSERVED_IN', 'Case', node_type, 'case_id', 'entity_value'
                )
                total_stats.relationships_created += rel_stats.relationships_created
            
            logger.info(f"Case upsert complete: {case_id} with {sum(len(vals) for vals in entities.values())} entities")
            
        except Exception as e:
            total_stats.errors += 1
            logger.error(f"Failed to upsert case {case_id}: {e}")
        
        return total_stats
    
    async def get_store_statistics(self) -> Dict[str, Any]:
        """Get comprehensive store statistics."""
        try:
            async with self.get_session() as session:
                # Node counts by type
                node_count_query = """
                MATCH (n)
                RETURN labels(n)[0] as node_type, count(*) as count
                ORDER BY count DESC
                """
                result = self._execute_with_retry(session, node_count_query, {})
                node_counts = {record['node_type']: record['count'] for record in result}
                
                # Relationship counts by type
                rel_count_query = """
                MATCH ()-[r]->()
                RETURN type(r) as relationship_type, count(*) as count
                ORDER BY count DESC
                """
                result = self._execute_with_retry(session, rel_count_query, {})
                rel_counts = {record['relationship_type']: record['count'] for record in result}
                
                # Database size metrics
                size_query = "CALL db.stats.retrieve('GRAPH COUNTS')"
                result = self._execute_with_retry(session, size_query, {})
                size_stats = dict(result.single()) if result.single() else {}
                
                return {
                    'node_counts': node_counts,
                    'relationship_counts': rel_counts,
                    'database_stats': size_stats,
                    'operation_stats': self.stats,
                    'connection_info': {
                        'uri': self.uri,
                        'max_connections': self.max_connections,
                        'batch_size': self.batch_size
                    }
                }
                
        except Exception as e:
            logger.error(f"Failed to get store statistics: {e}")
            return {'error': str(e)}


# Integration functions for backward compatibility
async def enhanced_upsert_case_entities(
    neo4j_client,
    case_id: str,
    rule_id: str,
    entities: Dict[str, List[str]],
    metadata: Dict[str, Any] = None
) -> bool:
    """
    Enhanced case upsert function for integration with existing code.
    """
    if isinstance(neo4j_client, EnhancedNeo4jStore):
        store = neo4j_client
    else:
        # Wrap legacy client
        store = EnhancedNeo4jStore()
        store.driver = getattr(neo4j_client, 'driver', neo4j_client)
    
    stats = await store.upsert_case_with_entities(case_id, rule_id, entities, metadata)
    return stats.errors == 0


# Scheduled hygiene job function
async def run_nightly_hygiene(neo4j_store: EnhancedNeo4jStore, dry_run: bool = False):
    """
    Run nightly hygiene job - can be called by scheduler.
    """
    logger.info("Starting nightly Neo4j hygiene job...")
    
    try:
        stats = await neo4j_store.run_hygiene_job(dry_run)
        
        logger.info(f"Nightly hygiene complete in {stats.execution_time_ms}ms: "
                   f"{stats.orphan_nodes_removed} orphans removed, "
                   f"{stats.duplicate_nodes_merged} duplicates merged")
        
        return stats
        
    except Exception as e:
        logger.error(f"Nightly hygiene job failed: {e}")
        raise