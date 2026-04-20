from datetime import datetime, timedelta
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from jose import JWTError

from app.db import models
from app.core.security import (
    verify_password,
    create_access_token,
    decode_access_token,
    validate_session,
    SESSION_TIMEOUT_MINUTES,
)


def login(email: str, password: str, db: Session) -> dict:
    user = db.query(models.User).filter(models.User.email == email).first()

    if not user:
        raise HTTPException(status_code=401, detail="Email atau Password salah")

    if not verify_password(password, user.password):
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


def get_current_user(token: str, db: Session) -> models.User:
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


def logout(token: str, db: Session) -> models.Authentication:
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

    return auth_record