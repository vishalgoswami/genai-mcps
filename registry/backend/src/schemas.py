"""Pydantic schemas for request/response validation."""
from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, HttpUrl


class MCPServerCreate(BaseModel):
    name: str
    description: str = ""
    url: str
    tags: str = ""
    owner: str = ""
    auth_type: str = "none"
    is_public: bool = True


class MCPServerUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    tags: Optional[str] = None
    owner: Optional[str] = None
    auth_type: Optional[str] = None
    is_public: Optional[bool] = None


class MCPServerRead(BaseModel):
    id: int
    name: str
    description: str
    url: str
    tags: str
    owner: str
    auth_type: str
    is_public: bool
    status: str
    last_checked: Optional[datetime]
    tools_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
