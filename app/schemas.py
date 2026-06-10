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
    category_id: UUID
    vehicle_id: Optional[UUID] = None
    unit: int = 1
    transaction_date: str
    note: Optional[str] = None

    @field_validator("unit")
    @classmethod
    def validate_unit(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Jumlah unit minimal 1")
        return v

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v):
        if not isinstance(v, int):
            raise ValueError("Jumlah transaksi harus berupa angka bulat positif")
        if v <= 0:
            raise ValueError("Jumlah transaksi harus positif")
        return v

    @field_validator("transaction_date")
    @classmethod
    def validate_transaction_date(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("Tanggal tidak boleh kosong dan harus format YYYY-MM-DD")
        try:
            dt = datetime.strptime(v, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError("Format tanggal tidak valid, gunakan YYYY-MM-DD")
        if dt > date.today():
            raise ValueError("Tanggal tidak boleh lebih besar dari hari ini")
        return v

class TransactionResponse(BaseModel):
    id: UUID
    amount: int
    category: str
    category_id: Optional[UUID] = None
    transaction_date: date
    note: Optional[str]
    vehicle_id: Optional[UUID] = None
    unit: int = 1
    bukti_path: Optional[str] = None
    bukti_url: Optional[str] = None
    organization_id: UUID
    created_at: datetime

    @field_validator("amount", mode="before")
    @classmethod
    def coerce_amount_to_int(cls, v):
        if isinstance(v, Decimal):
            return int(v)
        return int(v)

    @field_validator("category", mode="before")
    @classmethod
    def convert_enum_to_str(cls, v):
        return v.value if hasattr(v, "value") else str(v)

    @field_validator("bukti_url", mode="before")
    @classmethod
    def build_bukti_url(cls, v):
        return v

    class Config:
        from_attributes = True

    def model_post_init(self, __context):
        if self.bukti_path and not self.bukti_url:
            self.bukti_url = f"/uploads/{self.bukti_path}"

class PaginatedTransactionResponse(BaseModel):
    items: List[TransactionResponse]
    total: int
    page: int
    limit: int

class TransactionUpdate(BaseModel):
    amount: Optional[int] = None
    category: Optional[str] = None
    category_id: Optional[UUID] = None
    transaction_date: Optional[date] = None
    note: Optional[str] = None

    @field_validator("transaction_date", mode="before")
    @classmethod
    def validate_transaction_date(cls, v):
        if v is None:
            return v
        if isinstance(v, date):
            return v
        if not isinstance(v, str):
            raise ValueError("transaction_date harus berupa string")
        try:
            return datetime.strptime(v, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError("Format transaction_date tidak valid, gunakan YYYY-MM-DD")
        
    @field_validator("amount", mode="before")
    @classmethod
    def validate_amount(cls, v):
        if v is None:
            return v
        if type(v) is not int:
            raise ValueError("Amount harus berupa integer")
        if v <= 0:
            raise ValueError("Amount harus lebih dari 0")
        return v
        
    @field_validator("category")
    @classmethod
    def validate_category(cls, v:str) -> str:
        if v is None:
            return v
        v = v.strip().lower()
        if v not in {"in", "out"}:
            raise ValueError("Kategori harus 'in' atau 'out'")
        return v
        
class TransactionDeleteResponse(BaseModel):
    message: str
    deleted_at: datetime

class MonthlyProfitItem(BaseModel):
    month: str
    year: int
    month_number: int
    total_income: float
    total_expense: float
    profit: float

class MonthlyProfitResponse(BaseModel):
    items: list[MonthlyProfitItem]
    total_income: float
    total_expense: float
    profit: float

class DailyProfitItem(BaseModel):
    date: str
    total_income: float
    total_expense: float
    profit: float

class DailyProfitResponse(BaseModel):
    items: list[DailyProfitItem]
    total_income: float
    total_expense: float
    profit: float

class WeeklyProfitItem(BaseModel):
    week: str
    total_income: float
    total_expense: float
    profit: float

class WeeklyProfitResponse(BaseModel):
    items: list[WeeklyProfitItem]
    total_income: float
    total_expense: float
    profit: float

class IncomePredictionResponse(BaseModel):
    months: list[str] = []
    income_per_month: list[float] = []
    next_month: Optional[str] = None
    predicted_next_month_income: Optional[float] = None
    trend_up: Optional[bool] = None
    percentage_change: Optional[float] = None
    predict_available: bool = False
    ai_recommendation: Optional[str] = None
    error: Optional[str] = None

# --- Vehicle ---

VALID_VEHICLE_STATUS = {"aktif", "tidak_aktif", "dalam_perawatan"}

class VehicleCreate(BaseModel):
    plat_nomor: str
    merek: str
    model: str
    tahun: int
    tarif_sewa: int
    status: Optional[str] = "aktif"

    @field_validator("plat_nomor")
    @classmethod
    def validate_plat_nomor(cls, v: str) -> str:
        v = v.strip().upper()
        if len(v) < 4 or len(v) > 15:
            raise ValueError("Plat nomor harus antara 4 sampai 15 karakter")
        return v

    @field_validator("merek")
    @classmethod
    def validate_merek(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Merek kendaraan minimal 2 karakter")
        return v

    @field_validator("model")
    @classmethod
    def validate_model(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Model kendaraan minimal 2 karakter")
        return v

    @field_validator("tahun")
    @classmethod
    def validate_tahun(cls, v: int) -> int:
        current_year = date.today().year
        if v < 1990 or v > current_year:
            raise ValueError(f"Tahun kendaraan harus antara 1990 dan {current_year}")
        return v

    @field_validator("tarif_sewa")
    @classmethod
    def validate_tarif_sewa(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Tarif sewa harus lebih dari 0")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in VALID_VEHICLE_STATUS:
            raise ValueError(f"Status tidak valid. Pilihan: {', '.join(sorted(VALID_VEHICLE_STATUS))}")
        return v

class VehicleUpdate(BaseModel):
    merek: Optional[str] = None
    model: Optional[str] = None
    tahun: Optional[int] = None
    tarif_sewa: Optional[int] = None
    status: Optional[str] = None

    @field_validator("tahun", mode="before")
    @classmethod
    def validate_tahun(cls, v):
        if v is None:
            return v
        current_year = date.today().year
        if v < 1990 or v > current_year:
            raise ValueError(f"Tahun kendaraan harus antara 1990 dan {current_year}")
        return v

    @field_validator("tarif_sewa", mode="before")
    @classmethod
    def validate_tarif_sewa(cls, v):
        if v is None:
            return v
        if v <= 0:
            raise ValueError("Tarif sewa harus lebih dari 0")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        if v is None:
            return v
        v = v.strip().lower()
        if v not in VALID_VEHICLE_STATUS:
            raise ValueError(f"Status tidak valid. Pilihan: {', '.join(sorted(VALID_VEHICLE_STATUS))}")
        return v

class VehicleResponse(BaseModel):
    id: UUID
    plat_nomor: str
    merek: str
    model: str
    tahun: int
    tarif_sewa: int
    status: str
    organization_id: UUID
    created_at: datetime

    @field_validator("tarif_sewa", mode="before")
    @classmethod
    def coerce_tarif_sewa(cls, v):
        return int(v)

    @field_validator("status", mode="before")
    @classmethod
    def convert_status_enum(cls, v):
        return v.value if hasattr(v, "value") else str(v)

    class Config:
        from_attributes = True

class PaginatedVehicleResponse(BaseModel):
    items: List[VehicleResponse]
    total: int
    page: int
    limit: int

class VehicleDeleteResponse(BaseModel):
    message: str
    deleted_at: datetime

# --- Transaction Category Master ---

class TransactionCategoryMasterCreate(BaseModel):
    name: str
    type: str

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2 or len(v) > 100:
            raise ValueError("Nama kategori harus antara 2 sampai 100 karakter")
        return v

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in {"in", "out"}:
            raise ValueError("Tipe kategori harus 'in' atau 'out'")
        return v

class TransactionCategoryMasterResponse(BaseModel):
    id: UUID
    name: str
    type: str
    is_default: bool
    organization_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True