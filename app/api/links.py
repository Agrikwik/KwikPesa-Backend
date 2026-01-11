import string
import secrets
from app.api.deps import get_db
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user
from app.models.app_models import User
from pydantic import BaseModel

router = APIRouter()


class PaymentLinkRequest(BaseModel):
    amount: float
    description: str

@router.post("/api/merchant/create-link")
async def create_link(
    data: PaymentLinkRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    code = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(10))

    query = text("""
        INSERT INTO ledger.payment_links (short_code, merchant_id, amount, description)
        VALUES (:code, :mid, :amount, :desc)
    """)

    db.execute(query, {
        "code": code, 
        "mid": current_user.id, 
        "amount": data.amount, 
        "desc": data.description
    })
    db.commit()
    
    return {"url": f"https://kwikpesa.onrender.com/pay/{code}"}