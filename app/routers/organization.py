from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app import schemas
from app.services.org_service import get_all_organizations, create_organization, register_user

router = APIRouter(tags=["Organization"])


@router.get("/organizations", response_model=List[schemas.OrganizationResponse])
def list_organizations(db: Session = Depends(get_db)):
    return get_all_organizations(db)


@router.post("/organizations", response_model=schemas.OrganizationResponse)
def create_org(org: schemas.OrganizationCreate, db: Session = Depends(get_db)):
    return create_organization(org, db)


@router.post("/register", response_model=schemas.UserResponse)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    return register_user(user, db)