import uuid
from datetime import datetime

from sqlalchemy import Column, String, DECIMAL, DateTime, Text, JSON
from sqlalchemy.dialects.mysql import CHAR

from app.database import Base


class Payment(Base):
    __tablename__ = "payments_payment"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    booking_id = Column(CHAR(36), nullable=False, index=True)
    user_id = Column(CHAR(36), nullable=False, index=True)
    payment_method = Column(String(20), nullable=False)  # momo, vnpay, zalopay, cash
    amount = Column(DECIMAL(12, 2), nullable=False)
    transaction_id = Column(String(255), nullable=True, unique=True)
    payment_url = Column(Text, nullable=True)
    qr_code_url = Column(Text, nullable=True)
    status = Column(String(20), default="pending", index=True)
    # pending, processing, completed, failed, refunded, cancelled
    initiated_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    gateway_response = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
