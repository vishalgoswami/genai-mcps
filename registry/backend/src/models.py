"""SQLAlchemy ORM models."""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
from src.database import Base


class MCPServer(Base):
    __tablename__ = "mcp_servers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    description = Column(Text, default="")
    url = Column(String(500), nullable=False)
    tags = Column(String(500), default="")          # comma-separated
    owner = Column(String(100), default="")
    auth_type = Column(String(50), default="none")  # none | api_key | oauth
    is_public = Column(Boolean, default=True)

    # Status (updated by background checker)
    status = Column(String(20), default="unknown")  # online | offline | unknown
    last_checked = Column(DateTime, nullable=True)
    tools_count = Column(Integer, default=0)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
