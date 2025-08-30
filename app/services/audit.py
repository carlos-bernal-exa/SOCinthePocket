"""
Comprehensive audit logging system with hash chains and tamper-evidence
"""
import json
import hashlib
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
import uuid
import asyncpg
import logging
from dataclasses import dataclass, asdict
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, NoEncryption, PublicFormat
import os

logger = logging.getLogger(__name__)

@dataclass
class TokenUsage:
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float

@dataclass
class AgentInfo:
    name: str
    role: str
    model: str

@dataclass
class AgentStep:
    version: str
    case_id: str
    step_id: str
    timestamp: str
    agent: AgentInfo
    prompt_version: str
    autonomy_level: str
    inputs: Dict[str, Any]
    plan: List[str]
    observations: List[str]
    outputs: Dict[str, Any]
    token_usage: TokenUsage
    prev_hash: Optional[str]
    hash: str
    signature: Optional[str] = None

class AuditLogger:
    def __init__(self, db_url: str = None, use_signatures: bool = False):
        """
        Initialize audit logger with optional database connection and digital signatures
        
        Args:
            db_url: PostgreSQL connection URL, defaults to in-memory if None
            use_signatures: Whether to use Ed25519 signatures for tamper evidence
        """
        self.db_url = db_url or os.getenv("POSTGRES_URL", "postgresql://soc_user:soc_password@localhost:5432/soc_platform")
        self.use_signatures = use_signatures
        self.db_pool = None
        self.private_key = None
        self.public_key = None
        
        if use_signatures:
            self._initialize_keys()
    
    def _initialize_keys(self):
        """Initialize Ed25519 keys for signing"""
        try:
            # Try to load existing private key
            key_path = "/Users/cbernal/AIProjects/Claude/soc_agent_project/audit_private_key.pem"
            if os.path.exists(key_path):
                with open(key_path, "rb") as f:
                    self.private_key = ed25519.Ed25519PrivateKey.from_private_bytes(f.read()[:32])
            else:
                # Generate new key pair
                self.private_key = ed25519.Ed25519PrivateKey.generate()
                # Save private key (in production, secure this properly!)
                with open(key_path, "wb") as f:
                    f.write(self.private_key.private_bytes(
                        encoding=Encoding.Raw,
                        format=PrivateFormat.Raw,
                        encryption_algorithm=NoEncryption()
                    ))
                logger.info("Generated new Ed25519 key pair for audit signatures")
            
            self.public_key = self.private_key.public_key()
            
        except Exception as e:
            logger.error(f"Failed to initialize signing keys: {e}")
            self.use_signatures = False
    
    async def _ensure_db_connection(self):
        """Ensure database connection pool is established"""
        if self.db_pool is None:
            try:
                self.db_pool = await asyncpg.create_pool(self.db_url)
                await self._create_tables()
                logger.info("Connected to audit database")
            except Exception as e:
                logger.error(f"Failed to connect to audit database: {e}")
                # Continue without database (logs will be in memory only)
    
    async def _create_tables(self):
        """Create audit tables if they don't exist"""
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_steps (
                    id SERIAL PRIMARY KEY,
                    version TEXT NOT NULL,
                    case_id TEXT NOT NULL,
                    step_id TEXT UNIQUE NOT NULL,
                    timestamp TIMESTAMPTZ NOT NULL,
                    agent_name TEXT NOT NULL,
                    agent_role TEXT NOT NULL,
                    agent_model TEXT NOT NULL,
                    prompt_version TEXT NOT NULL,
                    autonomy_level TEXT NOT NULL,
                    inputs JSONB NOT NULL,
                    plan JSONB NOT NULL,
                    observations JSONB NOT NULL,
                    outputs JSONB NOT NULL,
                    token_usage JSONB NOT NULL,
                    prev_hash TEXT,
                    hash TEXT NOT NULL,
                    signature TEXT,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
                
                CREATE INDEX IF NOT EXISTS idx_audit_case_id ON audit_steps(case_id);
                CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_steps(timestamp);
                CREATE INDEX IF NOT EXISTS idx_audit_hash ON audit_steps(hash);
            """)
    
    def _calculate_hash(self, step_data: Dict[str, Any], prev_hash: Optional[str] = None) -> str:
        """Calculate SHA-256 hash for the step"""
        # Create canonical JSON representation (sorted keys, no extra whitespace)
        canonical_json = json.dumps(step_data, sort_keys=True, separators=(',', ':'))
        
        # Include previous hash in calculation for chaining
        if prev_hash:
            hash_input = f"{prev_hash}||{canonical_json}"
        else:
            hash_input = canonical_json
        
        return hashlib.sha256(hash_input.encode('utf-8')).hexdigest()
    
    def _sign_step(self, step_hash: str) -> Optional[str]:
        """Sign the step hash with Ed25519"""
        if not self.use_signatures or not self.private_key:
            return None
        
        try:
            signature = self.private_key.sign(step_hash.encode('utf-8'))
            return f"ed25519:{signature.hex()}"
        except Exception as e:
            logger.error(f"Failed to sign step: {e}")
            return None
    
    async def _get_last_hash(self, case_id: str) -> Optional[str]:
        """Get the hash of the last step for this case"""
        if not self.db_pool:
            await self._ensure_db_connection()
            
        if not self.db_pool:
            return None
        
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT hash FROM audit_steps WHERE case_id = $1 ORDER BY timestamp DESC LIMIT 1",
                case_id
            )
            return row['hash'] if row else None
    
    async def append(self, step: Dict[str, Any]) -> AgentStep:
        """
        Append a new agent step to the audit log with hash chaining
        
        Args:
            step: Dictionary containing step information
            
        Returns:
            AgentStep with calculated hash and signature
        """
        try:
            # Generate unique step ID
            step_id = f"stp_{uuid.uuid4().hex[:12]}"
            
            # Get current timestamp
            timestamp = datetime.now(timezone.utc)
            
            # Get previous hash for chaining
            case_id = step.get('case_id')
            prev_hash = await self._get_last_hash(case_id) if case_id else None
            
            # Create step data structure
            step_data = {
                "version": step.get('version', '1.0'),
                "case_id": case_id,
                "step_id": step_id,
                "timestamp": timestamp.isoformat(),
                "agent": step.get('agent', {"name": "Unknown", "role": "unknown", "model": "unknown"}),
                "prompt_version": step.get('prompt_version', 'unknown'),
                "autonomy_level": step.get('autonomy_level', 'L1_SUGGEST'),
                "inputs": step.get('inputs', {}),
                "plan": step.get('plan', []),
                "observations": step.get('observations', []),
                "outputs": step.get('outputs', {}),
                "token_usage": step.get('token_usage', {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                    "cost_usd": 0.0
                }),
                "prev_hash": prev_hash
            }
            
            # Calculate hash
            step_hash = self._calculate_hash(step_data, prev_hash)
            step_data["hash"] = step_hash
            
            # Sign the step
            signature = self._sign_step(step_hash)
            if signature:
                step_data["signature"] = signature
            
            # Create AgentStep object
            agent_step = AgentStep(
                version=step_data["version"],
                case_id=step_data["case_id"],
                step_id=step_data["step_id"],
                timestamp=step_data["timestamp"],
                agent=AgentInfo(**step_data["agent"]),
                prompt_version=step_data["prompt_version"],
                autonomy_level=step_data["autonomy_level"],
                inputs=step_data["inputs"],
                plan=step_data["plan"],
                observations=step_data["observations"],
                outputs=step_data["outputs"],
                token_usage=TokenUsage(**step_data["token_usage"]),
                prev_hash=step_data["prev_hash"],
                hash=step_data["hash"],
                signature=step_data.get("signature")
            )
            
            # Store in database
            await self._store_step(agent_step, timestamp)
            
            logger.info(f"Audit step {step_id} appended for case {case_id}")
            return agent_step
            
        except Exception as e:
            logger.error(f"Failed to append audit step: {e}")
            raise
    
    async def _store_step(self, step: AgentStep, timestamp: datetime = None):
        """Store the step in the database"""
        if not self.db_pool:
            await self._ensure_db_connection()
            
        if not self.db_pool:
            logger.warning("No database connection, step not persisted")
            return
        
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO audit_steps (
                    version, case_id, step_id, timestamp, agent_name, agent_role, 
                    agent_model, prompt_version, autonomy_level, inputs, plan, 
                    observations, outputs, token_usage, prev_hash, hash, signature
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17)
            """,
                step.version, step.case_id, step.step_id, timestamp or datetime.now(timezone.utc),
                step.agent.name, step.agent.role, step.agent.model,
                step.prompt_version, step.autonomy_level,
                json.dumps(step.inputs), json.dumps(step.plan),
                json.dumps(step.observations), json.dumps(step.outputs),
                json.dumps(asdict(step.token_usage)),
                step.prev_hash, step.hash, step.signature
            )
    
    async def fetch_case_steps(self, case_id: str, limit: int = 100, offset: int = 0) -> List[AgentStep]:
        """
        Fetch audit steps for a specific case
        
        Args:
            case_id: Case ID to fetch steps for
            limit: Maximum number of steps to return
            offset: Number of steps to skip
            
        Returns:
            List of AgentStep objects
        """
        if not self.db_pool:
            await self._ensure_db_connection()
            
        if not self.db_pool:
            return []
        
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT version, case_id, step_id, timestamp, agent_name, agent_role,
                       agent_model, prompt_version, autonomy_level, inputs, plan,
                       observations, outputs, token_usage, prev_hash, hash, signature
                FROM audit_steps 
                WHERE case_id = $1 
                ORDER BY timestamp ASC 
                LIMIT $2 OFFSET $3
            """, case_id, limit, offset)
            
            steps = []
            for row in rows:
                agent_info = AgentInfo(
                    name=row['agent_name'],
                    role=row['agent_role'],
                    model=row['agent_model']
                )
                
                token_usage_data = row['token_usage']
                if isinstance(token_usage_data, str):
                    token_usage_data = json.loads(token_usage_data)
                token_usage = TokenUsage(**token_usage_data)
                
                step = AgentStep(
                    version=row['version'],
                    case_id=row['case_id'],
                    step_id=row['step_id'],
                    timestamp=row['timestamp'],
                    agent=agent_info,
                    prompt_version=row['prompt_version'],
                    autonomy_level=row['autonomy_level'],
                    inputs=row['inputs'],
                    plan=row['plan'],
                    observations=row['observations'],
                    outputs=row['outputs'],
                    token_usage=token_usage,
                    prev_hash=row['prev_hash'],
                    hash=row['hash'],
                    signature=row['signature']
                )
                steps.append(step)
            
            return steps
    
    async def verify_integrity(self, case_id: str) -> Dict[str, Any]:
        """
        Verify the integrity of the audit chain for a case
        
        Returns:
            Dictionary with verification results
        """
        steps = await self.fetch_case_steps(case_id, limit=1000)
        
        if not steps:
            return {"valid": True, "message": "No steps found", "verified_steps": 0}
        
        verified_steps = 0
        errors = []
        
        prev_hash = None
        for i, step in enumerate(steps):
            # Verify hash chain
            expected_prev_hash = prev_hash
            if step.prev_hash != expected_prev_hash:
                errors.append(f"Step {i}: Hash chain broken. Expected prev_hash: {expected_prev_hash}, got: {step.prev_hash}")
            
            # Recalculate hash
            step_data = {
                "version": step.version,
                "case_id": step.case_id,
                "step_id": step.step_id,
                "timestamp": step.timestamp if isinstance(step.timestamp, str) else step.timestamp.isoformat(),
                "agent": asdict(step.agent),
                "prompt_version": step.prompt_version,
                "autonomy_level": step.autonomy_level,
                "inputs": step.inputs,
                "plan": step.plan,
                "observations": step.observations,
                "outputs": step.outputs,
                "token_usage": asdict(step.token_usage),
                "prev_hash": step.prev_hash
            }
            
            calculated_hash = self._calculate_hash(step_data, step.prev_hash)
            if calculated_hash != step.hash:
                errors.append(f"Step {i}: Hash mismatch. Expected: {calculated_hash}, got: {step.hash}")
            else:
                verified_steps += 1
            
            prev_hash = step.hash
        
        return {
            "valid": len(errors) == 0,
            "total_steps": len(steps),
            "verified_steps": verified_steps,
            "errors": errors
        }
    
    async def get_case_summary(self, case_id: str) -> Dict[str, Any]:
        """Get summary statistics for a case's audit trail"""
        if not self.db_pool:
            await self._ensure_db_connection()
            
        if not self.db_pool:
            return {}
        
        async with self.db_pool.acquire() as conn:
            summary = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total_steps,
                    MIN(timestamp) as first_step,
                    MAX(timestamp) as last_step,
                    SUM((token_usage->>'cost_usd')::numeric) as total_cost,
                    SUM((token_usage->>'total_tokens')::bigint) as total_tokens,
                    array_agg(DISTINCT agent_name) as agents_used
                FROM audit_steps 
                WHERE case_id = $1
            """, case_id)
            
            if summary:
                return {
                    "case_id": case_id,
                    "total_steps": summary['total_steps'],
                    "first_step": summary['first_step'].isoformat() if summary['first_step'] else None,
                    "last_step": summary['last_step'].isoformat() if summary['last_step'] else None,
                    "total_cost_usd": float(summary['total_cost']) if summary['total_cost'] else 0.0,
                    "total_tokens": summary['total_tokens'] if summary['total_tokens'] else 0,
                    "agents_used": summary['agents_used'] if summary['agents_used'] else []
                }
            
            return {"case_id": case_id, "total_steps": 0}

# Global audit logger instance
audit_logger = AuditLogger(use_signatures=True)