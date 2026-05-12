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
    if not ok:
        return {"success": False, "path_mapping": None}

    # On a successful test, try to auto-detect the path mapping so imports
    # work out of the box without the user ever touching Remote Path Mappings.
    path_mapping = None
    get_dir = getattr(client, "get_complete_dir", None)
    if get_dir is not None:
        path_mapping = await _setup_path_mapping(session, client)

    return {"success": True, "path_mapping": path_mapping}


async def _setup_path_mapping(session: AsyncSession, client) -> dict | None:
    """Query the download client for its complete_dir and auto-create a
    PathMapping if Fightarr can't see that path directly.

    Returns a dict describing the mapping that was created (or already existed),
    or None if the path is already visible / no mapping needed.
    """
    from app.services.importer import _auto_discover_path, _persist_auto_mapping

    complete_dir: str | None = await client.get_complete_dir()
    if not complete_dir:
        return None

    from pathlib import Path

    # Great — the path is already visible, no mapping needed.
    if Path(complete_dir).exists():
        return {"remote_path": complete_dir, "local_path": complete_dir, "auto_created": False}

    # Path not visible — run the same sliding-suffix discovery used at import
    # time, but do it NOW so it's ready before the first download finishes.
    discovery = await _auto_discover_path(complete_dir)
    if discovery is None:
        return None

    resolved, remote_prefix, local_prefix = discovery
    await _persist_auto_mapping(session, remote_prefix, local_prefix)
    await session.commit()
    return {"remote_path": remote_prefix, "local_path": local_prefix, "auto_created": True}
