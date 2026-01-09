from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from decimal import Decimal
from typing import Optional
import uuid

from app.core.fastapi_security import validate_api_key
from app.db.session import SessionLocal
from app.services.checkout_service import CheckoutService

router = APIRouter(prefix="/v1/payments", tags=["Payments"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class PaymentInitiateRequest(BaseModel):
    amount: Decimal = Field(..., gt=0, description="Amount must be greater than 0")
    phone: str = Field(..., pattern=r"^(?:\+265|0)[89]\d{8}$", description="Valid Malawian Phone")
    currency: str = "MWK"
    callback_url: Optional[str] = None
    metadata: Optional[dict] = None

@router.post("/initiate", status_code=status.HTTP_201_CREATED)
async def initiate_payment(
    payload: PaymentInitiateRequest,
    db: Session = Depends(get_db),
    merchant_data: any = Depends(validate_api_key)
):
    try:
        result = await CheckoutService.create_payment(
            db=db,
            amount=payload.amount,
            phone=payload.phone,
            merchant_id=merchant_data.id, 
            currency=payload.currency
        )
        
        if result.get("status") == "ERROR" or result.get("status") == "FAILED":
            raise HTTPException(status_code=400, detail=result.get("message", "Payment failed"))
            
        return result

    except HTTPException:
        raise
    except Exception as e:
        print(f"Gateway Error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Gateway processing error"
        )