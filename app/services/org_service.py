from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.db import models
from app import schemas
from app.core.security import get_password_hash


def get_all_organizations(db: Session):
    return db.query(models.Organization).all()


def create_organization(org: schemas.OrganizationCreate, db: Session) -> models.Organization:
    db_org = (
        db.query(models.Organization)
        .filter(models.Organization.organization_code == org.organization_code)
        .first()
    )
    if db_org:
        raise HTTPException(status_code=400, detail="kode organisasi sudah ada")

    new_org = models.Organization(
        organization_name=org.organization_name,
        organization_code=org.organization_code,
    )
    db.add(new_org)
    db.commit()
    db.refresh(new_org)

    return new_org


def register_user(user: schemas.UserCreate, db: Session) -> models.User:
    db_user = (
        db.query(models.User)
        .filter(
            (models.User.email == user.email) | (models.User.username == user.username)
        )
        .first()
    )
    if db_user:
        raise HTTPException(status_code=400, detail="Email atau Username sudah terdaftar")

    db_org = (
        db.query(models.Organization)
        .filter(models.Organization.id == user.organization_id)
        .first()
    )
    if not db_org:
        raise HTTPException(status_code=404, detail="Organisasi tidak ditemukan")

    new_user = models.User(
        username=user.username,
        email=user.email,
        password=get_password_hash(user.password),
        role=user.role,
        organization_id=user.organization_id,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user