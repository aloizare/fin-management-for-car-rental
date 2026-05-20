from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.db import models
from app.db.database import get_db
from app import schemas
from app.services.auth_service import login, logout, get_current_user

router = APIRouter(tags=["Authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")


def authenticated_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> models.User:
    return get_current_user(token, db)


@router.post("/login")
def login_user(credentials: schemas.LoginRequest, db: Session = Depends(get_db)):
    return login(credentials.email, credentials.password, db)


@router.post("/token", include_in_schema=False)
def login_form(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    result = login(form_data.username, form_data.password, db)
    return {"access_token": result["access_token"], "token_type": "bearer"}


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
