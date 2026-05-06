"""Indexer management endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.indexer import Indexer

router = APIRouter()


class IndexerIn(BaseModel):
    name: str
    url: str
    api_key: str
    enabled: bool = True
    priority: int = 25
    categories: str = "5070,5080"


class IndexerOut(IndexerIn):
    id: int

    model_config = {"from_attributes": True}


@router.get("/indexer", response_model=list[IndexerOut])
async def list_indexers(session: AsyncSession = Depends(get_session)) -> list[Indexer]:
    result = await session.execute(select(Indexer).order_by(Indexer.priority.asc()))
    return list(result.scalars().all())


@router.post("/indexer", response_model=IndexerOut, status_code=201)
async def create_indexer(
    indexer: IndexerIn, session: AsyncSession = Depends(get_session)
) -> Indexer:
    obj = Indexer(**indexer.model_dump())
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return obj


@router.delete("/indexer/{indexer_id}", status_code=204)
async def delete_indexer(
    indexer_id: int, session: AsyncSession = Depends(get_session)
) -> None:
    obj = await session.get(Indexer, indexer_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Indexer not found")
    await session.delete(obj)
    await session.commit()
