from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.db import models
from app.db.database import get_db
from app import schemas
from app.services.auth_service import login, logout, get_current_user

router = APIRouter(tags=["Authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")


def authenticated_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    return get_current_user(token, db)


@router.post("/login")
def login_user(credentials: schemas.LoginRequest, db: Session = Depends(get_db)):
    return login(credentials.email, credentials.password, db)


@router.post("/logout", response_model=schemas.LogoutResponse)
def logout_user(
    token: str = Depends(oauth2_scheme),
    current_user: models.User = Depends(authenticated_user),
    db: Session = Depends(get_db),
):
    auth_record = logout(token, db)
    return schemas.LogoutResponse(
        message="Logout berhasil.",
        logged_out_at=auth_record.logged_out_at,
    )
