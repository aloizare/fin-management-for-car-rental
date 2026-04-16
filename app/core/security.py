from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from jose import jwt

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = "admin123"  # nanti diganti
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
SESSION_TIMEOUT_MINUTES = 30

def get_password_hash(password: str):
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

def validate_session(auth_record, db) -> bool:
    if not auth_record or not auth_record.is_active:
        return False

    if auth_record.check_timeout():
        auth_record.is_active = False
        auth_record.logged_out_at = datetime.utcnow()
        db.commit()
        return False
 
    return True