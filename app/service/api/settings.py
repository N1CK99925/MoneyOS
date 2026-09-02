"""Settings API — GET /api/settings, PUT /api/settings/:key."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db import SystemSetting, get_db
from ..runtime_settings import get_all_settings, set_setting
from ..settings import settings as _static_settings

router = APIRouter(prefix="/api", tags=["settings"])


class SettingResponse(BaseModel):
    key: str
    value: str
    default: str
    description: str
    updated_at: str


class UpdateSettingRequest(BaseModel):
    value: str = Field(..., description="New value for the setting")


class UpdateSettingResponse(BaseModel):
    key: str
    value: str
    message: str


@router.get("/settings", response_model=list[SettingResponse])
def list_settings(db: Session = Depends(get_db)):
    """Return all system settings."""
    return get_all_settings(db)


@router.get("/settings/{key}", response_model=SettingResponse)
def get_single_setting(key: str, db: Session = Depends(get_db)):
    """Return a single setting by key."""
    row = db.query(SystemSetting).filter_by(key=key).first()
    if not row:
        raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")
    default = getattr(_static_settings, key, None)
    return SettingResponse(
        key=row.key,
        value=row.value,
        default=str(default) if default is not None else "",
        description=row.description or "",
        updated_at=row.updated_at,
    )


@router.put("/settings/{key}", response_model=UpdateSettingResponse)
def update_setting(key: str, body: UpdateSettingRequest, db: Session = Depends(get_db)):
    """Update a setting by key. Creates it if it doesn't exist."""
    existing = db.query(SystemSetting).filter_by(key=key).first()
    if not existing:
        raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")

    set_setting(db, key, body.value, description=existing.description)
    return UpdateSettingResponse(
        key=key,
        value=body.value,
        message=f"Setting '{key}' updated successfully",
    )
