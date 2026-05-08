"""Indexer management endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.indexer import Indexer, IndexerType

router = APIRouter()


class IndexerIn(BaseModel):
    name: str
    indexer_type: IndexerType = IndexerType.NEWZNAB
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


@router.put("/indexer/{indexer_id}", response_model=IndexerOut)
async def update_indexer(
    indexer_id: int,
    data: IndexerIn,
    session: AsyncSession = Depends(get_session),
) -> Indexer:
    obj = await session.get(Indexer, indexer_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Indexer not found")
    for field, val in data.model_dump().items():
        setattr(obj, field, val)
    await session.commit()
    await session.refresh(obj)
    return obj


@router.post("/indexer/{indexer_id}/test")
async def test_indexer(indexer_id: int, session: AsyncSession = Depends(get_session)) -> dict:
    """Test connectivity to an indexer by calling t=caps."""
    from app.services.newznab import NewznabClient

    obj = await session.get(Indexer, indexer_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Indexer not found")

    client = NewznabClient(obj.name, obj.url, obj.api_key)
    ok, message = await client.test_connection()
    return {"ok": ok, "message": message}


@router.delete("/indexer/{indexer_id}", status_code=204)
async def delete_indexer(indexer_id: int, session: AsyncSession = Depends(get_session)) -> None:
    obj = await session.get(Indexer, indexer_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Indexer not found")
    await session.delete(obj)
    await session.commit()


class ReorderItem(BaseModel):
    id: int
    priority: int


@router.put("/indexer/reorder", response_model=list[IndexerOut])
async def reorder_indexers(
    items: list[ReorderItem],
    session: AsyncSession = Depends(get_session),
) -> list[Indexer]:
    """Bulk-update indexer priorities in a single transaction.

    Accepts an ordered list of {id, priority} pairs and updates all rows
    atomically, preventing the race condition of two concurrent PUTs.
    """
    result = await session.execute(select(Indexer))
    index_map = {obj.id: obj for obj in result.scalars().all()}

    for item in items:
        if item.id in index_map:
            index_map[item.id].priority = item.priority

    await session.commit()
    result2 = await session.execute(select(Indexer).order_by(Indexer.priority.asc()))
    return list(result2.scalars().all())
