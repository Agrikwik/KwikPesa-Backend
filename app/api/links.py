import string
import secrets
from app.api.deps import get_db
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

router = APIRouter()

@router.post("/api/merchant/create-link")
async def create_link(amount: float, description: str, db: Session = Depends(get_db)):
    code = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(10))
    
    # 2. Save to DB
    new_link = text("""
        INSERT INTO ledger.payment_links (short_code, merchant_id, amount, description)
        VALUES (:code, :mid, :amount, :desc)
        RETURNING short_code
    """)
    db.execute(new_link, {
        "code": code, 
        "mid": "00000000-0000-0000-0000-000000000000", 
        "amount": amount, 
        "desc": description
    })
    db.commit()
    
    return {"url": f"https://kwikpesa.onrender.com/{code}"}