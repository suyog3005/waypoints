"""Master-data read endpoints (departments, users).

These back the block-request form's dropdowns. They are served from the
Command Service (which owns the Operational DB) so the form can resolve
structured identifiers (SR-003) instead of free text. Tracks are already
served by the Query Service at ``/tracks`` (no conflict).
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from db.models import Department, User

router = APIRouter(tags=["master-data"])


class DepartmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    code: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    full_name: str
    email: str
    department_id: str | None = None


@router.get("/departments", response_model=list[DepartmentOut])
def list_departments(db: Session = Depends(get_db)) -> list[Department]:
    return list(db.scalars(select(Department).where(Department.is_active.is_(True))).all())


@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db)) -> list[User]:
    return list(db.scalars(select(User).where(User.is_active.is_(True))).all())
