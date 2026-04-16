from pydantic import BaseModel, EmailStr, Field
from uuid import UUID
from datetime import datetime


class OrganizationCreate(BaseModel):
    organization_name: str
    organization_code: str


class OrganizationResponse(BaseModel):
    id: UUID
    organization_name: str
    organization_code: str
    created_at: datetime


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: str
    organization_id: UUID


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