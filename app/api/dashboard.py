from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
import secrets
import hashlib
from app.api.deps import get_db
from app.auth.router import get_current_user

router = APIRouter()

# --- MERCHANT SECURE ROUTES ---

@router.get("/api/merchant/stats")
async def get_merchant_stats(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user) # PROTECTED
):
    # Use the real ID from the logged-in user's token
    merchant_id = current_user.get("user_id")

    # 1. Available Balance
    balance = db.execute(text(
        "SELECT balance FROM ledger.merchants WHERE id = :mid"
    ), {"mid": merchant_id}).scalar() or 0

    # 2. Today's Sales
    sales = db.execute(text("""
        SELECT SUM(amount) FROM ledger.transactions 
        WHERE merchant_id = :mid AND status = 'SUCCESS' 
        AND created_at >= CURRENT_DATE
    """), {"mid": merchant_id}).scalar() or 0

    # 3. Success Rate
    rates = db.execute(text("""
        SELECT 
            COUNT(*) FILTER (WHERE status = 'SUCCESS')::float / 
            NULLIF(COUNT(*), 0) * 100
        FROM ledger.transactions WHERE merchant_id = :mid
    """), {"mid": merchant_id}).scalar() or 0

    return {
        "balance": float(balance),
        "sales": float(sales),
        "success_rate": round(rates, 1) if rates else 0,
        "provider_split": {"Airtel": 70, "TNM": 30}
    }

@router.post("/api/merchant/generate-keys")
async def generate_keys(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user) # PROTECTED
):
    merchant_id = current_user.get("user_id")
    
    new_public_key = f"pk_live_{secrets.token_hex(12)}"
    new_secret_key = f"sk_live_{secrets.token_hex(24)}"
    hashed_secret = hashlib.sha256(new_secret_key.encode()).hexdigest()
    
    db.execute(text("""
        UPDATE ledger.merchants 
        SET public_key = :pk, secret_key_hashed = :sk 
        WHERE id = :mid
    """), {"pk": new_public_key, "sk": hashed_secret, "mid": merchant_id})
    db.commit()
    
    return {
        "public_key": new_public_key,
        "secret_key": new_secret_key
    }

# --- ADMIN ROUTES (PUBLIC FOR NOW) ---

@router.get("/api/stats")
async def get_dashboard_stats(db: Session = Depends(get_db)):
    # Keep as is for now - you mentioned we'll secure Admin later
    volume = db.execute(text("SELECT SUM(credit) FROM ledger.ledger_entries WHERE account_id = '00000000-0000-0000-0000-000000000001'")).scalar() or 0
    # ... rest of admin logic ...
    return {"volume": float(volume), "profit": 0, "health": "98.5%"}

@router.get("/api/transactions")
async def get_recent_transactions(q: str = None, db: Session = Depends(get_db)):
    # ... admin transaction view ...
    return []

@router.post("/api/merchant/create-link")
async def create_payment_link(
    data: dict, 
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    merchant_id = current_user.get("user_id")
    short_code = secrets.token_urlsafe(6)
    
    db.execute(text("""
        INSERT INTO ledger.payment_links (merchant_id, amount, description, short_code, status)
        VALUES (:mid, :amt, :desc, :code, 'PENDING')
    """), {
        "mid": merchant_id,
        "amt": data['amount'],
        "desc": data['description'],
        "code": short_code
    })
    db.commit()
    
    return {"url": f"http://yourdomain.com/pay/{short_code}"}