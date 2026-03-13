from datetime import datetime
from decimal import Decimal
from typing import Optional, Any
from pydantic import BaseModel
from app.schemas.base import CamelModel


class PaymentInitiateRequest(CamelModel):
    booking_id: str
    payment_method: str  # momo, vnpay, zalopay, cash
    amount: Decimal


class PaymentResponse(CamelModel):
    id: str
    booking_id: str
    user_id: str
    payment_method: str
    amount: Decimal
    transaction_id: Optional[str] = None
    payment_url: Optional[str] = None
    qr_code_url: Optional[str] = None
    status: str
    initiated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class PaymentVerifyRequest(CamelModel):
    transaction_id: str
    gateway_response: Optional[dict[str, Any]] = None


class PaymentListResponse(CamelModel):
    count: int
    next: Optional[str] = None
    previous: Optional[str] = None
    results: list[PaymentResponse]
