from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
import secrets
import hashlib
from app.api.deps import get_db
from app.auth.router import get_current_user
from app.models.app_models import User

router = APIRouter()

# --- MERCHANT SECURE ROUTES ---

@router.get("/api/merchant/stats")
async def get_merchant_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user) # Now returns a User object
):
    # 1. Available Balance (Now directly on the User object!)
    balance = current_user.balance or 0

    # 2. Today's Sales (Querying transactions table)
    sales_query = text("""
        SELECT SUM(amount) FROM ledger.transactions 
        WHERE merchant_id = :mid AND status = 'SUCCESS' 
        AND created_at >= CURRENT_DATE
    """)
    sales = db.execute(sales_query, {"mid": current_user.id}).scalar() or 0

    # 3. Success Rate
    rate_query = text("""
        SELECT 
            COUNT(*) FILTER (WHERE status = 'SUCCESS')::float / 
            NULLIF(COUNT(*), 0) * 100
        FROM ledger.transactions WHERE merchant_id = :mid
    """)
    rates = db.execute(rate_query, {"mid": current_user.id}).scalar() or 0

    return {
        "business_name": current_user.business_name,
        "balance": float(balance),
        "sales": float(sales),
        "success_rate": round(rates, 1) if rates else 0,
        "provider_split": {"Airtel": 70, "TNM": 30}
    }

@router.post("/api/merchant/generate-keys")
async def generate_keys(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    new_public_key = f"pk_live_{secrets.token_hex(12)}"
    new_secret_key = f"sk_live_{secrets.token_hex(24)}"
    hashed_secret = hashlib.sha256(new_secret_key.encode()).hexdigest()
    
    # Update the Unified Table
    current_user.public_key = new_public_key
    current_user.api_key_hashed = hashed_secret # Fixed column name
    
    db.commit()
    
    return {
        "public_key": new_public_key,
        "secret_key": new_secret_key
    }

# --- ADMIN ROUTES (NOW SECURED) ---

@router.get("/api/admin/stats")
async def get_admin_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Forbidden")

    # 1. Total Volume (Sum of all successful transactions)
    volume = db.execute(text(
        "SELECT SUM(amount) FROM ledger.transactions WHERE status = 'SUCCESS'"
    )).scalar() or 0

    # 2. System Health (Check if any transactions failed in the last hour)
    recent_fails = db.execute(text("""
        SELECT COUNT(*) FROM ledger.transactions 
        WHERE status = 'FAILED' AND created_at > NOW() - INTERVAL '1 hour'
    """)).scalar() or 0
    
    health_status = "Optimal" if recent_fails < 5 else "Degraded"

    return {
        "total_platform_volume": float(volume),
        "system_health": health_status
    }


@router.post("/api/merchant/create-link")
async def create_payment_link(
    data: dict, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    short_code = secrets.token_urlsafe(6)
    
    # Ensure merchant can only create links if verified
    if not current_user.is_verified:
        raise HTTPException(status_code=403, detail="Account must be verified to create links")

    db.execute(text("""
        INSERT INTO ledger.payment_links (merchant_id, amount, description, short_code, status)
        VALUES (:mid, :amt, :desc, :code, 'PENDING')
    """), {
        "mid": current_user.id,
        "amt": data['amount'],
        "desc": data['description'],
        "code": short_code
    })
    db.commit()
    
    return {"url": f"https://kwikpesa.onrender.com/pay/{short_code}"}

@router.get("/pay/{short_code}", response_class=HTMLResponse)
async def checkout_page(short_code: str, db: Session = Depends(get_db)):
    # 1. Look up the link details from the DB
    link = db.execute(text("SELECT * FROM ledger.payment_links WHERE short_code = :c"), {"c": short_code}).fetchone()
    
    if not link:
        return "<h1>Link Not Found</h1>"

    # 2. Return a simple, mobile-friendly HTML page
    return f"""
    <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{ font-family: sans-serif; text-align: center; padding: 20px; }}
                .card {{ border: 1px solid #ddd; padding: 20px; border-radius: 10px; }}
                button {{ background: #2ecc71; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; }}
            </style>
        </head>
        <body>
            <div class="card">
                <h2>KwikPesa Checkout</h2>
                <p>Paying: <b>MK {link.amount}</b></p>
                <p>For: {link.description}</p>
                <input type="tel" id="phone" placeholder="099... or 088..." style="padding:10px; width:100%; margin-bottom:10px;"><br>
                <button onclick="payNow()">Pay Now</button>
            </div>

            <script>
                async function payNow() {{
                    const phone = document.getElementById('phone').value;
                    // Trigger your existing STK Push endpoint
                    const res = await fetch('/api/v1/payments/initiate-push', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify({{ phone: phone, amount: {link.amount} }})
                    }});
                    
                    if (res.ok) {{
                        alert('Check your phone for the PIN prompt!');
                        // Tell the marketplace we are done (Optional: use window.postMessage)
                        window.parent.postMessage('payment_initiated', '*');
                    }}
                }}
            </script>
        </body>
    </html>
    """