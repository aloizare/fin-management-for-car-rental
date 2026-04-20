from pydantic import BaseModel, EmailStr, Field ,field_validator
from uuid import UUID
from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional
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


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)

class LogoutResponse(BaseModel):
    message: str
    logged_out_at: datetime

class TransactionCreate(BaseModel):
    amount: int
    category: str
    transaction_date: date
    note: Optional[str] = None

    @field_validator("transaction_date", mode="before")
    @classmethod
    def validate_transaction_date(cls, v):
        if not isinstance(v, str):
            raise ValueError("transaction_date harus berupa string")
        try:
            return datetime.strptime(v, "%d-%m-%Y").date()
        except ValueError:
            raise ValueError("Format transaction_date tidak valid, harus DD-MM-YYYY (contoh: 09-09-2000)")

    @field_validator("amount", mode="before")
    @classmethod
    def validate_amount(cls, v):
        if type(v) is not int:
            raise ValueError("Amount harus berupa integer")
        return v

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in {"in", "out"}:
            raise ValueError("Kategori harus 'in' atau 'out'")
        return v

class TransactionResponse(BaseModel):
    id: UUID
    amount: Decimal
    category: str
    transaction_date: date
    note: Optional[str]
    organization_id: UUID
    created_at: datetime

    @field_validator("category", mode="before")
    @classmethod
    def convert_enum_to_str(cls, v):
        return v.value if hasattr(v, "value") else str(v)

    class Config:
        from_attributes = True

class PaginatedTransactionResponse(BaseModel):
    items: List[TransactionResponse]
    total: int
    page: int
    limit: int