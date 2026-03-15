"""CRUD router for MCP server registry entries."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from src.database import get_db
from src import models, schemas

router = APIRouter(prefix="/servers", tags=["servers"])


@router.get("/", response_model=list[schemas.MCPServerRead])
def list_servers(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(models.MCPServer).offset(skip).limit(limit).all()


@router.get("/{server_id}", response_model=schemas.MCPServerRead)
def get_server(server_id: int, db: Session = Depends(get_db)):
    server = db.query(models.MCPServer).filter(models.MCPServer.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    return server


@router.post("/", response_model=schemas.MCPServerRead, status_code=201)
def register_server(payload: schemas.MCPServerCreate, db: Session = Depends(get_db)):
    existing = db.query(models.MCPServer).filter(models.MCPServer.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Server '{payload.name}' already registered")
    server = models.MCPServer(**payload.model_dump())
    db.add(server)
    db.commit()
    db.refresh(server)
    return server


@router.patch("/{server_id}", response_model=schemas.MCPServerRead)
def update_server(server_id: int, payload: schemas.MCPServerUpdate, db: Session = Depends(get_db)):
    server = db.query(models.MCPServer).filter(models.MCPServer.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(server, field, value)
    db.commit()
    db.refresh(server)
    return server


@router.delete("/{server_id}", status_code=204)
def delete_server(server_id: int, db: Session = Depends(get_db)):
    server = db.query(models.MCPServer).filter(models.MCPServer.id == server_id).first()
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    db.delete(server)
    db.commit()
