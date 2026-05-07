"""Path mapping CRUD endpoints — Settings → Download Clients → Remote Path Mappings."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.path_mapping import PathMapping

router = APIRouter()


class PathMappingIn(BaseModel):
    host: str = ""
    remote_path: str
    local_path: str


class PathMappingOut(PathMappingIn):
    id: int
    created_at: datetime


@router.get("/pathmapping", response_model=list[PathMappingOut])
async def list_mappings(session: AsyncSession = Depends(get_session)) -> list[PathMappingOut]:
    result = await session.execute(select(PathMapping).order_by(PathMapping.id))
    return [
        PathMappingOut(
            id=m.id,
            host=m.host,
            remote_path=m.remote_path,
            local_path=m.local_path,
            created_at=m.created_at,
        )
        for m in result.scalars().all()
    ]


@router.post("/pathmapping", response_model=PathMappingOut, status_code=201)
async def create_mapping(
    body: PathMappingIn, session: AsyncSession = Depends(get_session)
) -> PathMappingOut:
    obj = PathMapping(**body.model_dump())
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return PathMappingOut(
        id=obj.id,
        host=obj.host,
        remote_path=obj.remote_path,
        local_path=obj.local_path,
        created_at=obj.created_at,
    )


@router.delete("/pathmapping/{mapping_id}", status_code=204)
async def delete_mapping(mapping_id: int, session: AsyncSession = Depends(get_session)) -> None:
    obj = await session.get(PathMapping, mapping_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Path mapping not found")
    await session.delete(obj)
    await session.commit()
