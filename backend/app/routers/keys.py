from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import ApiKeyCreate, ApiKeyUpdate, ApiKeyResponse, ApiKeyVerifyResponse
from app.services import key_service

router = APIRouter(prefix="/api/keys", tags=["keys"])


@router.post("", response_model=ApiKeyResponse)
async def create_key(data: ApiKeyCreate, db: AsyncSession = Depends(get_db)):
    key = await key_service.create_key(db, data)
    return key


@router.get("", response_model=list[ApiKeyResponse])
async def list_keys(db: AsyncSession = Depends(get_db)):
    return await key_service.list_keys(db)


@router.put("/{key_id}", response_model=ApiKeyResponse)
async def update_key(key_id: int, data: ApiKeyUpdate, db: AsyncSession = Depends(get_db)):
    key = await key_service.update_key(db, key_id, data)
    if not key:
        raise HTTPException(status_code=404, detail="Key not found")
    return key


@router.delete("/{key_id}")
async def delete_key(key_id: int, db: AsyncSession = Depends(get_db)):
    success = await key_service.delete_key(db, key_id)
    if not success:
        raise HTTPException(status_code=404, detail="Key not found")
    return {"message": "deleted"}


@router.post("/{key_id}/verify", response_model=ApiKeyVerifyResponse)
async def verify_key(key_id: int, db: AsyncSession = Depends(get_db)):
    is_valid, message = await key_service.verify_key(db, key_id)
    return ApiKeyVerifyResponse(is_valid=is_valid, message=message)


@router.post("/{key_id}/activate", response_model=ApiKeyResponse)
async def activate_key(key_id: int, db: AsyncSession = Depends(get_db)):
    key = await key_service.activate_key(db, key_id)
    if not key:
        raise HTTPException(status_code=404, detail="Key not found")
    return key
