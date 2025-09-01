"""
Database models for SOC Agent Platform
"""
from sqlalchemy import create_engine, Column, String, DateTime, Integer, Text, Boolean, Float, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
from datetime import datetime
import os

Base = declarative_base()

class Case(Base):
    __tablename__ = "cases"
    
    id = Column(String(36), primary_key=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    severity = Column(String(20), default="medium")
    status = Column(String(20), default="pending")  # pending, analyzing, completed, failed
    current_step = Column(String(50))  # triage, enrichment, investigation, etc.
    autonomy_level = Column(String(20), default="supervised")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    completed_at = Column(DateTime, nullable=True)
    
    # Case metadata
    entities = Column(JSON)  # {type: [values]}
    threat_classification = Column(String(50))
    confidence_score = Column(Float, default=0.0)
    estimated_cost = Column(Float, default=0.0)
    actual_cost = Column(Float, default=0.0)
    
    # Relationships
    approvals = relationship("Approval", back_populates="case")
    reports = relationship("Report", back_populates="case")
    agents = relationship("Agent", back_populates="case")

class Approval(Base):
    __tablename__ = "approvals"
    
    id = Column(String(36), primary_key=True)
    case_id = Column(String(36), ForeignKey("cases.id"), nullable=False)
    agent_name = Column(String(50), nullable=False)
    action_type = Column(String(50), nullable=False)  # query_siem, isolate_host, etc.
    action_description = Column(Text, nullable=False)
    justification = Column(Text, nullable=False)
    
    # Request data
    request_data = Column(JSON)  # Full action parameters
    artifacts = Column(JSON)  # Supporting evidence
    
    # Approval state
    status = Column(String(20), default="pending")  # pending, approved, denied, expired
    requested_at = Column(DateTime, server_default=func.now())
    decided_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    
    # Decision info
    decided_by = Column(String(100), nullable=True)  # User/role who decided
    decision_reason = Column(Text, nullable=True)
    
    # Relationships
    case = relationship("Case", back_populates="approvals")

class Report(Base):
    __tablename__ = "reports"
    
    id = Column(String(36), primary_key=True)
    case_id = Column(String(36), ForeignKey("cases.id"), nullable=False)
    
    # Report content
    title = Column(String(255), nullable=False)
    content_markdown = Column(Text)
    content_html = Column(Text)
    
    # File paths
    pdf_path = Column(String(500))
    markdown_path = Column(String(500))
    html_path = Column(String(500))
    audit_path = Column(String(500))
    signature_path = Column(String(500))
    
    # Metadata
    generated_at = Column(DateTime, server_default=func.now())
    file_size = Column(Integer, default=0)
    is_verified = Column(Boolean, default=False)
    
    # Relationships
    case = relationship("Case", back_populates="reports")

class Agent(Base):
    __tablename__ = "agents"
    
    id = Column(String(36), primary_key=True)
    case_id = Column(String(36), ForeignKey("cases.id"), nullable=True)
    
    # Agent info
    name = Column(String(50), nullable=False)
    agent_type = Column(String(50), nullable=False)  # TriageAgent, etc.
    model = Column(String(50), default="gemini-2.5-flash")
    status = Column(String(20), default="idle")  # idle, running, paused, completed, failed
    
    # Execution tracking
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    step_number = Column(Integer, default=0)
    
    # Performance metrics
    tokens_used = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)
    execution_time_ms = Column(Integer, default=0)
    
    # Configuration
    autonomy_level = Column(String(20), default="supervised")
    max_steps = Column(Integer, default=10)
    budget_usd = Column(Float, default=1.0)
    
    # Relationships
    case = relationship("Case", back_populates="agents")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(String(36), primary_key=True)
    case_id = Column(String(36), nullable=True)
    
    # Event info
    event_type = Column(String(50), nullable=False)  # agent_start, approval_request, etc.
    agent_name = Column(String(50))
    action = Column(String(100))
    
    # Event data
    event_data = Column(JSON)
    previous_hash = Column(String(64))  # For audit chain integrity
    event_hash = Column(String(64))
    
    # Timestamps
    timestamp = Column(DateTime, server_default=func.now())
    
    # Signature for integrity
    signature = Column(Text, nullable=True)

# Database connection
DATABASE_URL = os.getenv("POSTGRES_URL", "postgresql://soc_user:soc_password@localhost:5432/soc_platform")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    """Create all tables"""
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    create_tables()
    print("Database tables created successfully!")