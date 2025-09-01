"""
Database service for SOC Agent Platform operations
"""
import uuid
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import redis.asyncio as redis
import logging
import os

logger = logging.getLogger(__name__)

class DatabaseService:
    def __init__(self):
        # PostgreSQL connection
        self.postgres_url = os.getenv("POSTGRES_URL", "postgresql://soc_user:soc_password@localhost:5432/soc_platform")
        self.postgres_engine = create_engine(self.postgres_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.postgres_engine)
        
        # Redis connection  
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        
        # Initialize database if needed
        self._ensure_database_exists()
    
    def _ensure_database_exists(self):
        """Create database tables if they don't exist"""
        try:
            with self.postgres_engine.connect() as conn:
                # Create tables SQL
                create_tables_sql = """
                CREATE TABLE IF NOT EXISTS cases (
                    id VARCHAR(36) PRIMARY KEY,
                    title VARCHAR(255) NOT NULL,
                    description TEXT,
                    severity VARCHAR(20) DEFAULT 'medium',
                    status VARCHAR(20) DEFAULT 'pending',
                    current_step VARCHAR(50),
                    autonomy_level VARCHAR(20) DEFAULT 'supervised',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    entities JSONB,
                    threat_classification VARCHAR(50),
                    confidence_score FLOAT DEFAULT 0.0,
                    estimated_cost FLOAT DEFAULT 0.0,
                    actual_cost FLOAT DEFAULT 0.0
                );
                
                CREATE TABLE IF NOT EXISTS approvals (
                    id VARCHAR(36) PRIMARY KEY,
                    case_id VARCHAR(36) REFERENCES cases(id),
                    agent_name VARCHAR(50) NOT NULL,
                    action_type VARCHAR(50) NOT NULL,
                    action_description TEXT NOT NULL,
                    justification TEXT NOT NULL,
                    request_data JSONB,
                    artifacts JSONB,
                    status VARCHAR(20) DEFAULT 'pending',
                    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    decided_at TIMESTAMP,
                    expires_at TIMESTAMP,
                    decided_by VARCHAR(100),
                    decision_reason TEXT
                );
                
                CREATE TABLE IF NOT EXISTS reports (
                    id VARCHAR(36) PRIMARY KEY,
                    case_id VARCHAR(36) REFERENCES cases(id),
                    title VARCHAR(255) NOT NULL,
                    content_markdown TEXT,
                    content_html TEXT,
                    pdf_path VARCHAR(500),
                    markdown_path VARCHAR(500),
                    html_path VARCHAR(500),
                    audit_path VARCHAR(500),
                    signature_path VARCHAR(500),
                    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    file_size INTEGER DEFAULT 0,
                    is_verified BOOLEAN DEFAULT FALSE
                );
                
                CREATE TABLE IF NOT EXISTS agents (
                    id VARCHAR(36) PRIMARY KEY,
                    case_id VARCHAR(36) REFERENCES cases(id),
                    name VARCHAR(50) NOT NULL,
                    agent_type VARCHAR(50) NOT NULL,
                    model VARCHAR(50) DEFAULT 'gemini-2.5-flash',
                    status VARCHAR(20) DEFAULT 'idle',
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    step_number INTEGER DEFAULT 0,
                    tokens_used INTEGER DEFAULT 0,
                    cost_usd FLOAT DEFAULT 0.0,
                    execution_time_ms INTEGER DEFAULT 0,
                    autonomy_level VARCHAR(20) DEFAULT 'supervised',
                    max_steps INTEGER DEFAULT 10,
                    budget_usd FLOAT DEFAULT 1.0
                );
                
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id VARCHAR(36) PRIMARY KEY,
                    case_id VARCHAR(36),
                    event_type VARCHAR(50) NOT NULL,
                    agent_name VARCHAR(50),
                    action VARCHAR(100),
                    event_data JSONB,
                    previous_hash VARCHAR(64),
                    event_hash VARCHAR(64),
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    signature TEXT
                );
                """
                
                conn.execute(text(create_tables_sql))
                
                # Add missing columns to existing tables
                migration_sql = """
                ALTER TABLE agents ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
                """
                conn.execute(text(migration_sql))
                
                conn.commit()
                logger.info("Database tables ensured to exist and migrated")
        except Exception as e:
            logger.error(f"Failed to ensure database exists: {e}")
    
    async def get_redis(self):
        """Get Redis connection"""
        return redis.Redis.from_url(self.redis_url)
    
    # Case management
    async def get_active_cases(self) -> List[Dict[str, Any]]:
        """Get all active cases"""
        try:
            with self.SessionLocal() as db:
                query = text("""
                SELECT c.id, c.title, c.status, c.current_step, c.created_at, c.entities, c.actual_cost,
                       COUNT(a.id) as agents_count
                FROM cases c
                LEFT JOIN agents a ON c.id = a.case_id
                WHERE c.status IN ('analyzing', 'pending', 'investigating')
                GROUP BY c.id, c.title, c.status, c.current_step, c.created_at, c.actual_cost
                ORDER BY c.created_at DESC
                """)
                
                result = db.execute(query)
                cases = []
                
                for row in result:
                    # Calculate elapsed time
                    elapsed = datetime.now() - row.created_at
                    elapsed_str = f"{int(elapsed.total_seconds() // 60)}m"
                    
                    # Parse entities
                    entities = []
                    if row.entities:
                        for entity_type, values in row.entities.items():
                            # Handle both string and list values
                            if isinstance(values, str):
                                # If it's a string, treat as single entity
                                entities.append({
                                    "type": entity_type,
                                    "value": values,
                                    "confidence": 0.9
                                })
                            elif isinstance(values, list):
                                # If it's a list, take first 2
                                for value in values[:2]:
                                    entities.append({
                                        "type": entity_type,
                                        "value": value,
                                        "confidence": 0.9
                                    })
                    
                    cases.append({
                        "id": row.id,
                        "title": row.title or f"Case {row.id[:8]}",
                        "status": row.status,
                        "agents_count": row.agents_count,
                        "current_step": row.current_step or "Investigation",
                        "elapsed": elapsed_str,
                        "cost": round(row.actual_cost or 0.0, 4),
                        "entities": entities
                    })
                
                return cases
                
        except Exception as e:
            logger.error(f"Failed to get active cases: {e}")
            return []
    
    async def get_all_cases(self) -> List[Dict[str, Any]]:
        """Get all cases including completed ones"""
        try:
            with self.SessionLocal() as db:
                query = text("""
                SELECT c.id, c.title, c.status, c.current_step, c.created_at, c.completed_at, 
                       c.entities, c.actual_cost, c.threat_classification, c.description,
                       COUNT(a.id) as agents_count
                FROM cases c
                LEFT JOIN agents a ON c.id = a.case_id
                GROUP BY c.id, c.title, c.status, c.current_step, c.created_at, c.completed_at, 
                         c.actual_cost, c.threat_classification, c.description
                ORDER BY 
                    CASE WHEN c.status = 'completed' THEN c.completed_at ELSE c.created_at END DESC
                """)
                
                result = db.execute(query)
                cases = []
                
                for row in result:
                    # Calculate elapsed time
                    if row.status == 'completed' and row.completed_at:
                        elapsed = row.completed_at - row.created_at
                        elapsed_str = f"{int(elapsed.total_seconds() // 60)}m"
                        status_display = "Completed"
                    else:
                        elapsed = datetime.now() - row.created_at
                        elapsed_str = f"{int(elapsed.total_seconds() // 60)}m"
                        status_display = row.status.capitalize()
                    
                    # Parse entities
                    entities = []
                    if row.entities:
                        for entity_type, values in row.entities.items():
                            # Handle both string and list values
                            if isinstance(values, str):
                                # If it's a string, treat as single entity
                                entities.append({
                                    "type": entity_type,
                                    "value": values,
                                    "confidence": 0.9
                                })
                            elif isinstance(values, list):
                                # If it's a list, take first 2
                                for value in values[:2]:
                                    entities.append({
                                        "type": entity_type,
                                        "value": value,
                                        "confidence": 0.9
                                    })
                    
                    cases.append({
                        "id": row.id,
                        "title": row.title or f"Case {row.id[:8]}",
                        "status": status_display,
                        "raw_status": row.status,
                        "agents_count": row.agents_count,
                        "current_step": row.current_step or "Investigation",
                        "elapsed": elapsed_str,
                        "cost": round(row.actual_cost or 0.0, 4),
                        "entities": entities,
                        "threat_classification": row.threat_classification,
                        "description": row.description
                    })
                
                return cases
                
        except Exception as e:
            logger.error(f"Failed to get all cases: {e}")
            return []
    
    async def get_pending_approvals(self) -> List[Dict[str, Any]]:
        """Get all pending approvals"""
        try:
            with self.SessionLocal() as db:
                query = text("""
                SELECT a.id, a.case_id, a.agent_name, a.action_type, a.action_description, 
                       a.justification, a.requested_at, a.expires_at, a.artifacts,
                       c.title as case_title
                FROM approvals a
                JOIN cases c ON a.case_id = c.id
                WHERE a.status = 'pending' AND (a.expires_at IS NULL OR a.expires_at > CURRENT_TIMESTAMP)
                ORDER BY a.requested_at DESC
                """)
                
                result = db.execute(query)
                approvals = []
                
                for row in result:
                    approvals.append({
                        "id": row.id,
                        "case_id": row.case_id,
                        "case_title": row.case_title,
                        "agent": row.agent_name,
                        "action": f"{row.action_type}: {row.action_description}",
                        "justification": row.justification,
                        "created_at": row.requested_at.isoformat() + "Z",
                        "expires_at": row.expires_at.isoformat() + "Z" if row.expires_at else None,
                        "artifacts": row.artifacts or [],
                        "status": "pending"
                    })
                
                return approvals
                
        except Exception as e:
            logger.error(f"Failed to get pending approvals: {e}")
            return []
    
    async def get_token_stats(self) -> Dict[str, Any]:
        """Get token usage statistics"""
        try:
            with self.SessionLocal() as db:
                # Get token usage by agent type
                query = text("""
                SELECT agent_type, SUM(tokens_used) as total_tokens, SUM(cost_usd) as total_cost
                FROM agents 
                WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
                GROUP BY agent_type
                ORDER BY total_tokens DESC
                """)
                
                result = db.execute(query)
                usage_data = []
                total_tokens = 0
                total_cost = 0.0
                
                stage_mapping = {
                    "TriageAgent": "Triage",
                    "EnrichmentAgent": "Enrichment", 
                    "InvestigationAgent": "Investigation",
                    "CorrelationAgent": "Correlation",
                    "ResponseAgent": "Response",
                    "ReportingAgent": "Reporting"
                }
                
                for row in result:
                    stage = stage_mapping.get(row.agent_type, row.agent_type)
                    tokens = row.total_tokens or 0
                    cost = row.total_cost or 0.0
                    
                    total_tokens += tokens
                    total_cost += cost
                    
                    usage_data.append({
                        "stage": stage,
                        "tokens": tokens,
                        "cost": cost
                    })
                
                return {
                    "total_tokens": total_tokens,
                    "total_cost": round(total_cost, 6),
                    "daily_average": round(total_cost / 7, 6) if total_cost > 0 else 0,
                    "usage_by_stage": usage_data
                }
                
        except Exception as e:
            logger.error(f"Failed to get token stats: {e}")
            return {
                "total_tokens": 0,
                "total_cost": 0,
                "daily_average": 0,
                "usage_by_stage": []
            }
    
    async def create_case(self, case_id: str, title: str = None, autonomy_level: str = "supervised") -> bool:
        """Create a new case"""
        try:
            with self.SessionLocal() as db:
                query = text("""
                INSERT INTO cases (id, title, status, autonomy_level, current_step)
                VALUES (:id, :title, 'analyzing', :autonomy_level, 'Enrichment')
                ON CONFLICT (id) DO UPDATE SET
                    status = 'analyzing',
                    current_step = 'Enrichment',
                    updated_at = CURRENT_TIMESTAMP
                """)
                
                db.execute(query, {
                    "id": case_id,
                    "title": title or f"Investigation {case_id[:8]}",
                    "autonomy_level": autonomy_level
                })
                db.commit()
                
                logger.info(f"Created/updated case {case_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to create case {case_id}: {e}")
            return False
    
    async def update_case_from_redis(self, case_id: str) -> bool:
        """Update case with data from Redis"""
        try:
            redis_client = await self.get_redis()
            case_data = await redis_client.get(f"case_id:{case_id}")
            
            if not case_data:
                return False
            
            case_info = json.loads(case_data)
            
            with self.SessionLocal() as db:
                # Extract information from Redis case data
                case_summary = case_info.get("case_summary", {})
                entities = case_info.get("entities", {})
                
                query = text("""
                UPDATE cases SET
                    title = :title,
                    description = :description,
                    threat_classification = :threat_classification,
                    entities = :entities,
                    status = 'completed',
                    completed_at = CURRENT_TIMESTAMP,
                    current_step = 'Completed',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :case_id
                """)
                
                db.execute(query, {
                    "case_id": case_id,
                    "title": case_summary.get("title", f"Case {case_id[:8]}"),
                    "description": case_summary.get("summary", ""),
                    "threat_classification": case_summary.get("threat_classification", "Unknown"),
                    "entities": json.dumps(entities)
                })
                db.commit()
                
                logger.info(f"Updated case {case_id} from Redis data")
                return True
                
        except Exception as e:
            logger.error(f"Failed to update case {case_id} from Redis: {e}")
            return False

    async def save_agent_execution(self, case_id: str, agent_name: str, agent_type: str, 
                                 tokens_used: int, cost_usd: float, execution_time_ms: int = 0) -> bool:
        """Save agent execution record to database"""
        try:
            with self.SessionLocal() as db:
                query = text("""
                INSERT INTO agents (id, case_id, name, agent_type, status, tokens_used, cost_usd, 
                                   execution_time_ms, started_at, completed_at)
                VALUES (:id, :case_id, :name, :agent_type, 'completed', :tokens_used, :cost_usd, 
                        :execution_time_ms, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """)
                
                agent_id = f"{case_id}_{agent_type}_{str(uuid.uuid4())[:8]}"
                db.execute(query, {
                    "id": agent_id,
                    "case_id": case_id,
                    "name": agent_name,
                    "agent_type": agent_type,
                    "tokens_used": tokens_used,
                    "cost_usd": cost_usd,
                    "execution_time_ms": execution_time_ms
                })
                db.commit()
                
                logger.info(f"Saved agent execution: {agent_name} ({agent_type}) for case {case_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to save agent execution for {case_id}: {e}")
            return False

    async def update_case_costs(self, case_id: str, total_cost: float, total_tokens: int) -> bool:
        """Update case with total costs and tokens"""
        try:
            with self.SessionLocal() as db:
                query = text("""
                UPDATE cases SET
                    actual_cost = :total_cost,
                    estimated_cost = :total_cost,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :case_id
                """)
                
                db.execute(query, {
                    "case_id": case_id,
                    "total_cost": total_cost
                })
                db.commit()
                
                logger.info(f"Updated case {case_id} costs: ${total_cost:.6f} ({total_tokens} tokens)")
                return True
                
        except Exception as e:
            logger.error(f"Failed to update case costs for {case_id}: {e}")
            return False
    
    async def approve_request(self, approval_id: str, decision: str, reason: str = "") -> bool:
        """Approve or deny an approval request"""
        try:
            with self.SessionLocal() as db:
                query = text("""
                UPDATE approvals SET
                    status = :decision,
                    decided_at = CURRENT_TIMESTAMP,
                    decided_by = 'analyst',
                    decision_reason = :reason
                WHERE id = :approval_id AND status = 'pending'
                """)
                
                result = db.execute(query, {
                    "approval_id": approval_id,
                    "decision": decision,
                    "reason": reason
                })
                db.commit()
                
                if result.rowcount > 0:
                    logger.info(f"Approval {approval_id} {decision} with reason: {reason}")
                    return True
                else:
                    logger.warning(f"Approval {approval_id} not found or already decided")
                    return False
                
        except Exception as e:
            logger.error(f"Failed to process approval {approval_id}: {e}")
            return False
    
    async def create_approval(self, case_id: str, agent_name: str, description: str) -> str:
        """Create a new approval request"""
        try:
            import uuid
            approval_id = f"apr_{uuid.uuid4().hex[:8]}"
            
            with self.SessionLocal() as db:
                query = text("""
                INSERT INTO approvals (id, case_id, agent_name, description, status, created_at)
                VALUES (:approval_id, :case_id, :agent_name, :description, 'pending', CURRENT_TIMESTAMP)
                """)
                
                db.execute(query, {
                    "approval_id": approval_id,
                    "case_id": case_id,
                    "agent_name": agent_name,
                    "description": description
                })
                db.commit()
                
                logger.info(f"Created approval request {approval_id} for {agent_name} on case {case_id}")
                return approval_id
                
        except Exception as e:
            logger.error(f"Failed to create approval: {e}")
            return None
    
    async def get_approval(self, approval_id: str) -> Dict[str, Any]:
        """Get approval by ID"""
        try:
            with self.SessionLocal() as db:
                query = text("""
                SELECT id, case_id, agent_name, description, status, created_at, approved_at, approved_by, reason
                FROM approvals 
                WHERE id = :approval_id
                """)
                
                result = db.execute(query, {"approval_id": approval_id}).fetchone()
                
                if result:
                    return {
                        "id": result.id,
                        "case_id": result.case_id,
                        "agent_name": result.agent_name,
                        "description": result.description,
                        "status": result.status,
                        "created_at": result.created_at,
                        "approved_at": result.approved_at,
                        "approved_by": result.approved_by,
                        "reason": result.reason
                    }
                
                return None
                
        except Exception as e:
            logger.error(f"Failed to get approval {approval_id}: {e}")
            return None

# Global instance
db_service = DatabaseService()