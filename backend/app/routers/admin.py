from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import hash_password
from app.deps import get_db, require_admin
from app.models.audit_log import AuditLog
from app.models.config import AllowedCountry, AllowedUnit, AppSetting
from app.models.user import User
from app.schemas.config import (
    AllowedCountryCreate,
    AllowedCountryOut,
    AllowedUnitCreate,
    AllowedUnitOut,
)
from app.schemas.user import UserCreate, UserOut, UserUpdate

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])


def _log(
    db: Session,
    actor: User,
    entity_type: str,
    entity_id: int,
    change_type: str,
    field_name: Optional[str] = None,
    old_value: Optional[object] = None,
    new_value: Optional[object] = None,
) -> None:
    db.add(
        AuditLog(
            entity_type=entity_type,
            entity_id=entity_id,
            change_type=change_type,
            field_name=field_name,
            old_value=str(old_value) if old_value is not None else None,
            new_value=str(new_value) if new_value is not None else None,
            source="system",
            user_id=actor.id,
        )
    )


# --- User management -------------------------------------------------------


@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db)) -> list[User]:
    return db.query(User).order_by(User.username).all()


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate, db: Session = Depends(get_db), admin: User = Depends(require_admin)
) -> User:
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")

    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        is_admin=payload.is_admin,
        is_active=payload.is_active,
    )
    db.add(user)
    db.flush()
    _log(db, admin, "user", user.id, "create", new_value=user.username)
    db.commit()
    db.refresh(user)
    return user


@router.put("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if payload.password is not None:
        user.password_hash = hash_password(payload.password)
        _log(db, admin, "user", user.id, "update", field_name="password")
    if payload.is_admin is not None:
        _log(db, admin, "user", user.id, "update", "is_admin", user.is_admin, payload.is_admin)
        user.is_admin = payload.is_admin
    if payload.is_active is not None:
        _log(db, admin, "user", user.id, "update", "is_active", user.is_active, payload.is_active)
        user.is_active = payload.is_active

    db.commit()
    db.refresh(user)
    return user


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)
) -> None:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete your own account"
        )

    _log(db, admin, "user", user.id, "delete", old_value=user.username)
    db.delete(user)
    db.commit()


# --- Config: allowed units & countries --------------------------------------


@router.get("/units", response_model=list[AllowedUnitOut])
def list_units(db: Session = Depends(get_db)) -> list[AllowedUnit]:
    return db.query(AllowedUnit).order_by(AllowedUnit.code).all()


@router.post("/units", response_model=AllowedUnitOut, status_code=status.HTTP_201_CREATED)
def create_unit(
    payload: AllowedUnitCreate, db: Session = Depends(get_db), admin: User = Depends(require_admin)
) -> AllowedUnit:
    if db.query(AllowedUnit).filter(AllowedUnit.code == payload.code).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Unit already exists")

    unit = AllowedUnit(**payload.model_dump())
    db.add(unit)
    db.flush()
    _log(db, admin, "allowed_unit", unit.id, "create", new_value=unit.code)
    db.commit()
    db.refresh(unit)
    return unit


@router.get("/countries", response_model=list[AllowedCountryOut])
def list_countries(db: Session = Depends(get_db)) -> list[AllowedCountry]:
    return db.query(AllowedCountry).order_by(AllowedCountry.code).all()


@router.post("/countries", response_model=AllowedCountryOut, status_code=status.HTTP_201_CREATED)
def create_country(
    payload: AllowedCountryCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> AllowedCountry:
    if db.query(AllowedCountry).filter(AllowedCountry.code == payload.code).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Country already exists")

    country = AllowedCountry(**payload.model_dump())
    db.add(country)
    db.flush()
    _log(db, admin, "allowed_country", country.id, "create", new_value=country.code)
    db.commit()
    db.refresh(country)
    return country


# --- Settings (API key) -------------------------------------------------------


@router.get("/settings")
def get_settings(db: Session = Depends(get_db)):
    """Get app settings (masks API key for security)."""
    settings = db.query(AppSetting).all()
    result = {}
    for s in settings:
        if "key" in s.key.lower() or "secret" in s.key.lower():
            # Mask sensitive values - show only last 8 chars
            result[s.key] = {
                "value": "***" + s.value[-8:] if len(s.value) > 8 else "***",
                "updated_at": s.updated_at.isoformat() if s.updated_at else None,
            }
        else:
            result[s.key] = {
                "value": s.value,
                "updated_at": s.updated_at.isoformat() if s.updated_at else None,
            }
    return result


@router.put("/settings/{key}")
def update_setting(
    key: str,
    payload: dict,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Update an app setting. Admin only."""
    value = payload.get("value", "")
    setting = db.query(AppSetting).filter(AppSetting.key == key).first()
    if setting:
        old_masked = "***" + setting.value[-8:] if len(setting.value) > 8 else "***"
        setting.value = value
        _log(
            db,
            admin,
            "app_setting",
            setting.id,
            "update",
            field_name=key,
            old_value=old_masked,
            new_value="***" + value[-8:] if len(value) > 8 else "***",
        )
    else:
        setting = AppSetting(key=key, value=value)
        db.add(setting)
        db.flush()
        _log(
            db,
            admin,
            "app_setting",
            setting.id,
            "create",
            field_name=key,
            new_value="(set)",
        )
    db.commit()
    return {"status": "ok"}
