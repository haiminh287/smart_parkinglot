import uuid
from datetime import datetime
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user_id
from app.models.payment import Payment
from app.schemas.payment import (
    PaymentInitiateRequest,
    PaymentResponse,
    PaymentVerifyRequest,
    PaymentListResponse,
)

router = APIRouter(prefix="/api/payments", tags=["payments"])


@router.post("/initiate/", response_model=PaymentResponse, status_code=201)
async def initiate_payment(
    payload: PaymentInitiateRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Initiate a payment for a booking."""
    valid_methods = ("momo", "vnpay", "zalopay", "cash")
    if payload.payment_method not in valid_methods:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid payment method. Must be one of: {', '.join(valid_methods)}",
        )

    existing = (
        db.query(Payment)
        .filter(
            Payment.booking_id == payload.booking_id,
            Payment.user_id == user_id,
            Payment.status.in_(["pending", "processing"]),
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=400, detail="An active payment already exists for this booking"
        )

    payment = Payment(
        id=str(uuid.uuid4()),
        booking_id=payload.booking_id,
        user_id=user_id,
        payment_method=payload.payment_method,
        amount=payload.amount,
        status="pending",
        initiated_at=datetime.utcnow(),
    )

    if payload.payment_method == "cash":
        payment.status = "completed"
        payment.completed_at = datetime.utcnow()
        payment.transaction_id = f"CASH-{uuid.uuid4().hex[:12].upper()}"
    else:
        payment.transaction_id = f"{payload.payment_method.upper()}-{uuid.uuid4().hex[:12].upper()}"
        payment.status = "processing"
        payment.payment_url = f"https://payment-gateway.example.com/pay/{payment.transaction_id}"
        payment.qr_code_url = f"https://payment-gateway.example.com/qr/{payment.transaction_id}"

    db.add(payment)
    db.commit()
    db.refresh(payment)

    # Notify booking service about payment status
    try:
        async with httpx.AsyncClient() as client:
            await client.patch(
                f"{settings.BOOKING_SERVICE_URL}/api/bookings/{payload.booking_id}/payment-status/",
                json={"payment_status": payment.status},
                headers={"X-Gateway-Secret": settings.GATEWAY_SECRET},
                timeout=5.0,
            )
    except Exception:
        pass  # Non-critical: booking service will reconcile

    return payment


@router.post("/verify/{payment_id}/", response_model=PaymentResponse)
async def verify_payment(
    payment_id: str,
    payload: PaymentVerifyRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Verify / confirm a payment after gateway callback."""
    payment = (
        db.query(Payment)
        .filter(Payment.id == payment_id, Payment.user_id == user_id)
        .first()
    )
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    if payment.status not in ("pending", "processing"):
        raise HTTPException(
            status_code=400, detail=f"Cannot verify payment with status: {payment.status}"
        )

    payment.transaction_id = payload.transaction_id or payment.transaction_id
    payment.gateway_response = payload.gateway_response
    payment.status = "completed"
    payment.completed_at = datetime.utcnow()
    db.commit()
    db.refresh(payment)

    # Notify booking service
    try:
        async with httpx.AsyncClient() as client:
            await client.patch(
                f"{settings.BOOKING_SERVICE_URL}/api/bookings/{payment.booking_id}/payment-status/",
                json={"payment_status": "completed"},
                headers={"X-Gateway-Secret": settings.GATEWAY_SECRET},
                timeout=5.0,
            )
    except Exception:
        pass

    # Broadcast via realtime service
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{settings.REALTIME_SERVICE_URL}/api/broadcast/notification/",
                json={
                    "user_id": user_id,
                    "type": "payment_completed",
                    "message": f"Payment of {payment.amount} completed successfully",
                    "data": {"payment_id": payment.id, "booking_id": payment.booking_id},
                },
                headers={"X-Gateway-Secret": settings.GATEWAY_SECRET},
                timeout=5.0,
            )
    except Exception:
        pass

    return payment


@router.get("/", response_model=PaymentListResponse)
async def list_payments(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """List payments for the current user."""
    query = db.query(Payment).filter(Payment.user_id == user_id)

    if status:
        query = query.filter(Payment.status == status)

    total = query.count()
    payments = (
        query.order_by(Payment.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return PaymentListResponse(
        count=total,
        next=f"?page={page + 1}&page_size={page_size}" if page * page_size < total else None,
        previous=f"?page={page - 1}&page_size={page_size}" if page > 1 else None,
        results=payments,
    )


@router.get("/{payment_id}/", response_model=PaymentResponse)
async def get_payment(
    payment_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Get payment detail."""
    payment = (
        db.query(Payment)
        .filter(Payment.id == payment_id, Payment.user_id == user_id)
        .first()
    )
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment


@router.get("/booking/{booking_id}/", response_model=list[PaymentResponse])
async def get_booking_payments(
    booking_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
):
    """Get all payments for a specific booking."""
    payments = (
        db.query(Payment)
        .filter(Payment.booking_id == booking_id, Payment.user_id == user_id)
        .order_by(Payment.created_at.desc())
        .all()
    )
    return payments
