import json
from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.security import OAuth2PasswordBearer
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from jose import JWTError

from app.db import models
from app.db.database import engine, get_db
from app import schemas
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    decode_access_token,
    validate_session,
    SESSION_TIMEOUT_MINUTES,
)
models.Base.metadata.create_all(bind=engine)


from typing import List

app = FastAPI(title="Fin-Management API", version="1.0.0")

# ── Global Response Formatter ────────────────────────────────────
class StandardResponseMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        content_type = response.headers.get("content-type", "")
        if "application/json" not in content_type:
            return response

        body = b"".join([chunk async for chunk in response.body_iterator])

        if 200 <= response.status_code < 300:
            try:
                data = json.loads(body)
                wrapped = {
                    "success": True,
                    "server_message": "OK",
                    **(data if isinstance(data, dict) else {"data": data}),
                }
                return JSONResponse(content=wrapped, status_code=response.status_code)
            except Exception:
                pass

        return StarletteResponse(
            content=body,
            status_code=response.status_code,
            headers=dict(response.headers),
        )

app.add_middleware(StandardResponseMiddleware)

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "server_message": exc.detail},
        headers=exc.headers,
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    raw_msg = errors[0]["msg"] if errors else "Validasi gagal"
    message = raw_msg.replace("Value error, ", "")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"success": False, "server_message": message},
    )
# ─────────────────────────────────────────────────────────────────

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login/")

@app.get("/")
def read_root():
    return {"test"}



# GET: List all organizations
@app.get("/organizations", response_model=List[schemas.OrganizationResponse])
def list_organizations(db: Session = Depends(get_db)):
    return db.query(models.Organization).all()

# POST: Create new organization
@app.post("/organizations", response_model=schemas.OrganizationResponse)
def create_organization(org: schemas.OrganizationCreate, db: Session = Depends(get_db)):
    db_org = (
        db.query(models.Organization)
        .filter(models.Organization.organization_code == org.organization_code)
        .first()
    )
    if db_org:
        raise HTTPException(status_code=400, detail="kode organisasi sudah ada")

    new_org = models.Organization(
        organization_name=org.organization_name, organization_code=org.organization_code
    )

    db.add(new_org)
    db.commit()
    db.refresh(new_org)

    return new_org


@app.post("/register", response_model=schemas.UserResponse)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = (
        db.query(models.User)
        .filter(
            (models.User.email == user.email) | (models.User.username == user.username)
        )
        .first()
    )

    if db_user:
        raise HTTPException(
            status_code=400, detail="Email atau Username sudah terdaftar"
        )

    db_org = (
        db.query(models.Organization)
        .filter(models.Organization.id == user.organization_id)
        .first()
    )
    if not db_org:
        raise HTTPException(status_code=404, detail="Organisasi tidak ditemukan")

    hashed_password = get_password_hash(user.password)

    new_user = models.User(
        username=user.username,
        email=user.email,
        password=hashed_password,
        role=user.role,
        organization_id=user.organization_id,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


@app.post("/login")
def login_user(credentials: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == credentials.email).first()

    if not user:
        raise HTTPException(status_code=401, detail="Email atau Password salah")

    if not verify_password(credentials.password, user.password):
        raise HTTPException(status_code=401, detail="Email atau Password salah")

    token = create_access_token(
        {"sub": user.email, "user_id": str(user.id), "role": user.role}
    )

    auth_session = models.Authentication(
        user_id=user.id,
        session_timeout=SESSION_TIMEOUT_MINUTES,
        token=token,
        is_active=True,
        expired_at=datetime.utcnow() + timedelta(minutes=SESSION_TIMEOUT_MINUTES),
    )
    db.add(auth_session)
    db.commit()

    return {
        "message": "Login berhasil",
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "role": user.role,
        },
    }

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token tidak valid atau sesi sudah berakhir. Silakan login kembali.",
        headers={"WWW-Authenticate": "Bearer"},
    )
 
    try:
        payload = decode_access_token(token)
        user_id: str = payload.get("user_id")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
 
    auth_record = (
        db.query(models.Authentication)
        .filter(models.Authentication.token == token)
        .first()
    )
 
    if not validate_session(auth_record, db):
        raise credentials_exception
 
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise credentials_exception
 
    return user

@app.post("/logout", response_model=schemas.LogoutResponse)
def logout_user(
    token: str = Depends(oauth2_scheme),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    auth_record = (
        db.query(models.Authentication)
        .filter(
            models.Authentication.token == token,
            models.Authentication.is_active == True,
        )
        .first()
    )
 
    if not auth_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesi tidak ditemukan atau sudah tidak aktif.",
        )
 
    auth_record.is_active = False
    auth_record.logged_out_at = datetime.utcnow()
    db.commit()
 
    return schemas.LogoutResponse(
        message="Logout berhasil.",
        logged_out_at=auth_record.logged_out_at,
    )