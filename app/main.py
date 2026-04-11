from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

# Perubahan ada di 3 baris ini (menggunakan 'app.' di depannya)
from app.db import models
from app.db.database import engine, get_db
from app import schemas
from app.core.security import get_password_hash
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Fin-Management API", version="1.0.0")

@app.get("/")
def read_root():
    return {"test"}

@app.post("/organizations/", response_model=schemas.OrganizationResponse)
def create_organization(org: schemas.OrganizationCreate, db: Session = Depends(get_db)):
    db_org = db.query(models.Organization).filter(models.Organization.organization_code == org.organization_code).first()
    if db_org:
        raise HTTPException(status_code=400, detail="kode organisasi sudah ada")
    
    new_org = models.Organization(
        organization_name=org.organization_name,
        organization_code=org.organization_code
    )

    db.add(new_org)
    db.commit()
    db.refresh(new_org)
    
    return new_org

@app.post("/register/", response_model=schemas.UserResponse)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(
        (models.User.email == user.email) | (models.User.username == user.username)
    ).first()
    
    if db_user:
        raise HTTPException(status_code=400, detail="Email atau Username sudah terdaftar")

    db_org = db.query(models.Organization).filter(models.Organization.id == user.organization_id).first()
    if not db_org:
        raise HTTPException(status_code=404, detail="Organisasi tidak ditemukan")

    hashed_password = get_password_hash(user.password)

    new_user = models.User(
        username=user.username,
        email=user.email,
        password=hashed_password,
        role=user.role,
        organization_id=user.organization_id
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user