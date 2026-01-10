import enum
import uuid
from datetime import datetime, timedelta
from sqlalchemy import Column, String, Boolean, Enum, DateTime, Numeric, Text, ForeignKey
from decimal import Decimal
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    MERCHANT = "merchant"

class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "ledger"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(String, default="merchant")
    
    is_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    business_name = Column(String)
    business_phone = Column(String)
    business_category = Column(String)
    balance = Column(Decimal(20, 4), default=0.0)
    
    api_key_hashed = Column(String, unique=True)
    public_key = Column(String, unique=True)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class OTP(Base):
    __tablename__ = "otps"
    __table_args__ = {"schema": "ledger"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, index=True, nullable=False)
    code = Column(String(6), nullable=False)
    purpose = Column(String, default="registration") 
    expires_at = Column(DateTime, default=lambda: datetime.utcnow() + timedelta(minutes=10))
    is_used = Column(Boolean, default=False)

class PaymentLink(Base):
    __tablename__ = "payment_links"
    __table_args__ = {"schema": "ledger"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    short_code = Column(String(20), unique=True, nullable=False)
    merchant_id = Column(UUID(as_uuid=True), ForeignKey("ledger.users.id"))
    amount = Column(Numeric(12, 2), nullable=False)
    description = Column(Text)
    status = Column(String(20), default="ACTIVE")
    created_at = Column(DateTime, default=datetime.utcnow)