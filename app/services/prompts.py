"""
Prompt management system with versioning
"""
import asyncpg
import logging
import os
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import uuid

logger = logging.getLogger(__name__)

@dataclass
class AgentPrompt:
    id: str
    agent_name: str
    version: str
    created_at: str
    content: str
    modified_by: str

class PromptManager:
    def __init__(self, db_url: str = None):
        """
        Initialize prompt manager with database connection
        
        Args:
            db_url: PostgreSQL connection URL, defaults to in-memory if None
        """
        self.db_url = db_url or os.getenv("POSTGRES_URL", "postgresql://soc_user:soc_password@localhost:5432/soc_platform")
        self.db_pool = None
        self._default_prompts = self._get_default_prompts()
    
    async def _ensure_db_connection(self):
        """Ensure database connection pool is established"""
        if self.db_pool is None:
            try:
                self.db_pool = await asyncpg.create_pool(self.db_url)
                await self._create_tables()
                await self._seed_default_prompts()
                logger.info("Connected to prompts database")
            except Exception as e:
                logger.error(f"Failed to connect to prompts database: {e}")
                # Continue with default prompts only
    
    async def _create_tables(self):
        """Create prompt tables if they don't exist"""
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_prompts (
                    id TEXT PRIMARY KEY,
                    agent_name TEXT NOT NULL,
                    version TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL,
                    content TEXT NOT NULL,
                    modified_by TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT true,
                    UNIQUE(agent_name, version)
                );
                
                CREATE INDEX IF NOT EXISTS idx_prompts_agent ON agent_prompts(agent_name);
                CREATE INDEX IF NOT EXISTS idx_prompts_active ON agent_prompts(agent_name, is_active);
            """)
    
    def _get_default_prompts(self) -> Dict[str, str]:
        """Define default prompts for all agents"""
        return {
            "TriageAgent": """You are a SOC Triage Agent specialized in initial security alert assessment.

Your role:
- Normalize and parse security alerts/cases
- Extract entities (IPs, domains, users, files, etc.)
- Set initial severity and confidence
- Generate investigation hypotheses

Given a case summary, you must:
1. Extract all security-relevant entities
2. Assess severity (LOW, MEDIUM, HIGH, CRITICAL)
3. Provide initial hypotheses for investigation
4. Format output as structured JSON

Be precise and thorough. Focus on actionable intelligence.""",

            "EnrichmentAgent": """You are a SOC Enrichment Agent specialized in contextual data gathering.

Your role:
- Find similar cases/alerts in historical data
- Fetch raw case data from security platforms
- Apply rule-based filtering for SIEM queries
- Correlate related security events

Key responsibilities:
1. Search Redis for similar cases using entity matching
2. Retrieve raw cases from Exabeam
3. Apply rule gating (only fact* and profile* rules proceed to SIEM)
4. Aggregate related security data

Output structured enrichment data with clear provenance.""",

            "InvestigationAgent": """You are a SOC Investigation Agent specialized in deep security analysis.

Your role:
- Execute SIEM queries for qualified rules
- Build comprehensive security timelines
- Extract Indicators of Compromise (IOCs)
- Analyze attack patterns and techniques

Investigation process:
1. Execute search queries against SIEM for fact*/profile* rules
2. Construct detailed timeline of security events
3. Extract and validate IOCs
4. Map to MITRE ATT&CK framework
5. Assess threat actor techniques

Provide detailed technical analysis with evidence citations.""",

            "CorrelationAgent": """You are a SOC Correlation Agent specialized in cross-case analysis.

Your role:
- Correlate security events across multiple cases
- Build comprehensive attack narratives
- Map attack chains to MITRE ATT&CK
- Identify campaign patterns

Correlation focus:
1. Link related security incidents
2. Identify attack progression and lateral movement
3. Map techniques to MITRE ATT&CK framework
4. Assess threat actor attribution
5. Build attack story narrative

Provide strategic threat intelligence with high confidence assessments.""",

            "ResponseAgent": """You are a SOC Response Agent specialized in incident response planning.

Your role:
- Propose containment and mitigation actions
- Assess business impact and urgency
- Plan coordinated response activities
- Generate action recommendations

Response planning:
1. Evaluate containment options
2. Assess business impact and risk
3. Prioritize response actions
4. Coordinate with stakeholders
5. Plan recovery activities

Focus on practical, actionable responses with clear risk/benefit analysis.""",

            "ReportingAgent": """You are a SOC Reporting Agent specialized in incident documentation.

Your role:
- Generate comprehensive incident reports
- Provide executive summaries
- Document lessons learned
- Create actionable recommendations

Report structure:
1. Executive Summary
2. Incident Timeline
3. Technical Analysis
4. Impact Assessment
5. Response Actions
6. Recommendations
7. IOCs and Evidence

Ensure reports are clear, accurate, and actionable for all stakeholder levels.""",

            "KnowledgeAgent": """You are a SOC Knowledge Agent specialized in information management.

Your role:
- Manage SOC knowledge base and procedures
- Retrieve relevant historical investigations
- Maintain security playbooks and SOPs
- Provide contextual security intelligence

Knowledge management:
1. Store and index security knowledge
2. Retrieve similar past incidents
3. Maintain procedure documentation
4. Provide security intelligence context
5. Update knowledge base with learnings

Focus on providing relevant, accurate historical context and procedural guidance."""
        }
    
    async def _seed_default_prompts(self):
        """Seed database with default prompts if empty"""
        if not self.db_pool:
            return
        
        async with self.db_pool.acquire() as conn:
            for agent_name, content in self._default_prompts.items():
                # Check if prompt already exists
                existing = await conn.fetchrow(
                    "SELECT id FROM agent_prompts WHERE agent_name = $1 AND version = 'v1.0'",
                    agent_name
                )
                
                if not existing:
                    await conn.execute("""
                        INSERT INTO agent_prompts (id, agent_name, version, created_at, content, modified_by)
                        VALUES ($1, $2, $3, $4, $5, $6)
                    """,
                        f"prompt_{uuid.uuid4().hex[:12]}",
                        agent_name,
                        "v1.0",
                        datetime.now(timezone.utc),
                        content,
                        "system"
                    )
                    logger.info(f"Seeded default prompt for {agent_name}")
    
    async def get(self, agent_name: str, version: Optional[str] = None) -> str:
        """
        Get prompt content for an agent
        
        Args:
            agent_name: Name of the agent
            version: Specific version to retrieve, None for latest
            
        Returns:
            Prompt content string
        """
        if not self.db_pool:
            await self._ensure_db_connection()
        
        if self.db_pool:
            async with self.db_pool.acquire() as conn:
                if version:
                    # Get specific version
                    row = await conn.fetchrow(
                        "SELECT content FROM agent_prompts WHERE agent_name = $1 AND version = $2",
                        agent_name, version
                    )
                else:
                    # Get latest version
                    row = await conn.fetchrow(
                        """SELECT content FROM agent_prompts 
                           WHERE agent_name = $1 AND is_active = true
                           ORDER BY created_at DESC LIMIT 1""",
                        agent_name
                    )
                
                if row:
                    return row['content']
        
        # Fallback to default prompts
        return self._default_prompts.get(agent_name, "You are a helpful AI assistant.")
    
    async def put(self, agent_name: str, content: str, author: str) -> str:
        """
        Store a new prompt version
        
        Args:
            agent_name: Name of the agent
            content: Prompt content
            author: Who is creating this prompt
            
        Returns:
            Version string of the new prompt
        """
        if not self.db_pool:
            await self._ensure_db_connection()
        
        # Generate version number
        version_num = 1
        if self.db_pool:
            async with self.db_pool.acquire() as conn:
                # Get highest version number
                row = await conn.fetchrow(
                    """SELECT version FROM agent_prompts WHERE agent_name = $1 
                       ORDER BY created_at DESC LIMIT 1""",
                    agent_name
                )
                if row:
                    current_version = row['version']
                    if current_version.startswith('v'):
                        try:
                            version_num = int(float(current_version[1:])) + 1
                        except:
                            version_num = 1
        
        new_version = f"v{version_num}.0"
        
        if self.db_pool:
            async with self.db_pool.acquire() as conn:
                prompt_id = f"prompt_{uuid.uuid4().hex[:12]}"
                await conn.execute("""
                    INSERT INTO agent_prompts (id, agent_name, version, created_at, content, modified_by)
                    VALUES ($1, $2, $3, $4, $5, $6)
                """,
                    prompt_id,
                    agent_name,
                    new_version,
                    datetime.now(timezone.utc),
                    content,
                    author
                )
                logger.info(f"Created new prompt version {new_version} for {agent_name}")
        
        return new_version
    
    async def latest(self, agent_name: str) -> str:
        """Get the latest prompt version for an agent"""
        return await self.get(agent_name)
    
    async def list_versions(self, agent_name: str) -> List[AgentPrompt]:
        """List all prompt versions for an agent"""
        if not self.db_pool:
            await self._ensure_db_connection()
        
        if not self.db_pool:
            # Return default if no database
            return [AgentPrompt(
                id="default",
                agent_name=agent_name,
                version="v1.0",
                created_at=datetime.now(timezone.utc).isoformat(),
                content=self._default_prompts.get(agent_name, ""),
                modified_by="system"
            )]
        
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT id, agent_name, version, created_at, content, modified_by
                   FROM agent_prompts 
                   WHERE agent_name = $1 
                   ORDER BY created_at DESC""",
                agent_name
            )
            
            prompts = []
            for row in rows:
                prompt = AgentPrompt(
                    id=row['id'],
                    agent_name=row['agent_name'],
                    version=row['version'],
                    created_at=row['created_at'].isoformat(),
                    content=row['content'],
                    modified_by=row['modified_by']
                )
                prompts.append(prompt)
            
            return prompts
    
    async def get_info(self, agent_name: str, version: Optional[str] = None) -> Dict[str, Any]:
        """
        Get prompt metadata information
        
        Args:
            agent_name: Name of the agent
            version: Specific version to retrieve, None for latest
            
        Returns:
            Dictionary with version, created_at, modified_by info
        """
        if not self.db_pool:
            await self._ensure_db_connection()
        
        if self.db_pool:
            async with self.db_pool.acquire() as conn:
                if version:
                    # Get specific version info
                    row = await conn.fetchrow(
                        "SELECT version, created_at, modified_by FROM agent_prompts WHERE agent_name = $1 AND version = $2",
                        agent_name, version
                    )
                else:
                    # Get latest version info
                    row = await conn.fetchrow(
                        """SELECT version, created_at, modified_by FROM agent_prompts 
                           WHERE agent_name = $1 AND is_active = true
                           ORDER BY created_at DESC LIMIT 1""",
                        agent_name
                    )
                
                if row:
                    return {
                        "version": row["version"],
                        "created_at": row["created_at"].isoformat(),
                        "modified_by": row["modified_by"]
                    }
        
        # Fallback to default
        return {
            "version": "v1.0",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "modified_by": "system"
        }
    
    async def get_latest(self, agent_name: str) -> str:
        """
        Get latest prompt content for an agent
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            Latest prompt content string
        """
        return await self.get(agent_name, version=None)
    
    async def update(self, agent_name: str, content: str, modified_by: str) -> str:
        """
        Update prompt for an agent (creates new version)
        
        Args:
            agent_name: Name of the agent
            content: New prompt content
            modified_by: Who is making the update
            
        Returns:
            New version string
        """
        if not self.db_pool:
            await self._ensure_db_connection()
        
        if not self.db_pool:
            raise Exception("Database not available")
        
        # Generate new version
        current_info = await self.get_info(agent_name)
        current_version = current_info.get("version", "v1.0")
        
        # Parse version and increment
        if current_version.startswith("v"):
            try:
                version_num = float(current_version[1:])
                new_version = f"v{version_num + 0.1:.1f}"
            except:
                new_version = "v1.1"
        else:
            new_version = "v1.1"
        
        # Insert new version
        async with self.db_pool.acquire() as conn:
            prompt_id = f"pmt_{uuid.uuid4().hex[:8]}"
            await conn.execute(
                """INSERT INTO agent_prompts (id, agent_name, version, created_at, content, modified_by, is_active)
                   VALUES ($1, $2, $3, $4, $5, $6, true)""",
                prompt_id, agent_name, new_version, datetime.now(timezone.utc), content, modified_by
            )
        
        logger.info(f"Updated prompt for {agent_name} to version {new_version}")
        return new_version

    async def get_all_agents(self) -> List[str]:
        """Get list of all agents with prompts"""
        if not self.db_pool:
            await self._ensure_db_connection()
        
        if self.db_pool:
            async with self.db_pool.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT DISTINCT agent_name FROM agent_prompts ORDER BY agent_name"
                )
                return [row['agent_name'] for row in rows]
        
        # Return default agents
        return list(self._default_prompts.keys())

# Global prompt manager instance
prompt_manager = PromptManager()