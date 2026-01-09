import enum
import uuid
from datetime import datetime, timedelta
from sqlalchemy import Column, String, Boolean, Enum, DateTime, Numeric, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    MERCHANT = "merchant"

class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "ledger"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    personal_phone = Column(String, nullable=False)

    business_name = Column(String, nullable=True)
    business_phone = Column(String, nullable=True)
    business_category = Column(String, nullable=True)
    business_address = Column(Text, nullable=True)
    
    role = Column(Enum(UserRole), default=UserRole.MERCHANT)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


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