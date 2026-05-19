from sqlalchemy import Column, String, Numeric, Date, Text, ForeignKey, DateTime, Enum, Integer, Boolean, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
import enum
from .database import Base

class TransactionCategory(enum.Enum):
    IN = "in"
    OUT = "out"

class Organization(Base):
    __tablename__ = 'organizations'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_name = Column(String, nullable=False)
    organization_code = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)

class User(Base):
    __tablename__ = 'users'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String, unique=True, nullable=False)
    role = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False) 
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id'))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)

class Transaction(Base):
    __tablename__ = 'transactions'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    amount = Column(Numeric, nullable=False) 
    category = Column(Enum(TransactionCategory), nullable=False)
    transaction_date = Column(Date, nullable=False) 
    note = Column(Text)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id'))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)

class VehicleStatus(enum.Enum):
    AKTIF = "aktif"
    TIDAK_AKTIF = "tidak_aktif"
    DALAM_PERAWATAN = "dalam_perawatan"

class Vehicle(Base):
    __tablename__ = 'vehicles'
    __table_args__ = (
        UniqueConstraint('plat_nomor', 'organization_id', name='uq_vehicle_plat_org'),
    )
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plat_nomor = Column(String, nullable=False)
    merek = Column(String, nullable=False)
    model = Column(String, nullable=False)
    tahun = Column(Integer, nullable=False)
    tarif_sewa = Column(Numeric, nullable=False)
    status = Column(Enum(VehicleStatus), nullable=False, default=VehicleStatus.AKTIF)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)

class TransactionCategoryMaster(Base):
    __tablename__ = 'transaction_category_masters'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)  # "in" atau "out"
    is_default = Column(Boolean, nullable=False, default=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)

class Authentication(Base):
    __tablename__ = "authentications"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    session_timeout = Column(Integer, nullable=False, default=30)  # dalam menit
    token = Column(Text, nullable=False, unique=True, index=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expired_at = Column(DateTime, nullable=False)      # created_at + session_timeout
    logged_out_at = Column(DateTime, nullable=True)    # diisi saat logout()
 
    def validate_session(self) -> bool:
        return self.is_active and not self.check_timeout()
 
    def check_timeout(self) -> bool:
        return datetime.utcnow() > self.expired_at