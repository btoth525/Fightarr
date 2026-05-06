"""Download client CRUD + connection test endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.download_client import DownloadClient, DownloadClientType
from app.services.download_clients.factory import build_client

router = APIRouter()


class DownloadClientIn(BaseModel):
    name: str
    client_type: DownloadClientType
    host: str
    api_key: str | None = None
    username: str | None = None
    password: str | None = None
    category: str = "ufc"
    enabled: bool = True
    priority: int = 25


class DownloadClientOut(DownloadClientIn):
    id: int
    model_config = {"from_attributes": True}


@router.get("/downloadclient", response_model=list[DownloadClientOut])
async def list_download_clients(
    session: AsyncSession = Depends(get_session),
) -> list[DownloadClient]:
    result = await session.execute(select(DownloadClient).order_by(DownloadClient.priority.asc()))
    return list(result.scalars().all())


@router.post("/downloadclient", response_model=DownloadClientOut, status_code=201)
async def create_download_client(
    body: DownloadClientIn, session: AsyncSession = Depends(get_session)
) -> DownloadClient:
    obj = DownloadClient(**body.model_dump())
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return obj


@router.put("/downloadclient/{client_id}", response_model=DownloadClientOut)
async def update_download_client(
    client_id: int,
    body: DownloadClientIn,
    session: AsyncSession = Depends(get_session),
) -> DownloadClient:
    obj = await session.get(DownloadClient, client_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Download client not found")
    for field, value in body.model_dump().items():
        setattr(obj, field, value)
    await session.commit()
    await session.refresh(obj)
    return obj


@router.delete("/downloadclient/{client_id}", status_code=204)
async def delete_download_client(
    client_id: int, session: AsyncSession = Depends(get_session)
) -> None:
    obj = await session.get(DownloadClient, client_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Download client not found")
    await session.delete(obj)
    await session.commit()


@router.post("/downloadclient/{client_id}/test")
async def test_download_client(
    client_id: int, session: AsyncSession = Depends(get_session)
) -> dict:
    obj = await session.get(DownloadClient, client_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Download client not found")
    client = build_client(obj)
    ok = await client.test_connection()
    return {"success": ok}
