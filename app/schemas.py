from pydantic import BaseModel, EmailStr, field_validator
from uuid import UUID
from datetime import datetime
import re

VALID_ROLES = {"admin", "staff", "viewer"}

class OrganizationCreate(BaseModel):
    organization_name: str
    organization_code: str

    @field_validator("organization_name")
    @classmethod
    def validate_organization_name(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Nama organisasi minimal 2 karakter")
        if len(v) > 100:
            raise ValueError("Nama organisasi maksimal 100 karakter")
        return v

    @field_validator("organization_code")
    @classmethod
    def validate_organization_code(cls, v: str) -> str:
        v = v.strip().upper()
        if not re.fullmatch(r"[A-Z0-9_\-]{2,20}", v):
            raise ValueError(
                "Kode organisasi hanya boleh huruf, angka, underscore, atau dash (2–20 karakter)"
            )
        return v

class OrganizationResponse(BaseModel):
    id: UUID
    organization_name: str
    organization_code: str
    created_at: datetime

    class Config:
        from_attributes = True

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: str
    organization_id: UUID

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        v = v.strip()
        if not re.fullmatch(r"[a-zA-Z0-9_]{3,50}", v):
            raise ValueError(
                "Username hanya boleh huruf, angka, dan underscore (3–50 karakter)"
            )
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password minimal 8 karakter")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password harus mengandung minimal 1 huruf kapital")
        if not re.search(r"[0-9]", v):
            raise ValueError("Password harus mengandung minimal 1 angka")
        return v

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in VALID_ROLES:
            raise ValueError(f"Role tidak valid. Pilihan: {', '.join(sorted(VALID_ROLES))}")
        return v

class UserResponse(BaseModel):
    id: UUID
    username: str
    email: EmailStr
    role: str
    organization_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True