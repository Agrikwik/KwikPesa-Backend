import httpx
import uuid
import asyncio
from fastapi import APIRouter, Background_Tasks, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.api.deps import get_db

router = APIRouter()

# --- CONFIGURATION ---
MNO_STK_ENDPOINT = "https://kwachapoint.free.beeceptor.com/v1/stk/push"

# --- HELPER FUNCTIONS ---

async def notify_merchant_webhook(webhook_url: str, payload: dict, retries=3):
    """Smart Webhook with exponential backoff retries."""
    if not webhook_url:
        return False
    async with httpx.AsyncClient() as client:
        for i in range(retries):
            try:
                response = await client.post(webhook_url, json=payload, timeout=10.0)
                if response.status_code == 200:
                    return True
            except Exception as e:
                print(f"Webhook attempt {i+1} failed: {e}")
                await asyncio.sleep(60 * (i + 1))
    return False

async def send_customer_sms(phone: str, message: str):
    """Log SMS intent (Integrate with Buru/Africa's Talking here)."""
    print(f"📡 [SMS SENT] To: {phone} | Message: {message}")

async def send_to_mno(phone: str, amount: float, ref: str):
    """Actual handshake with the Mobile Network."""
    async with httpx.AsyncClient() as client:
        data = {
            "msisdn": phone,
            "amount": amount,
            "external_id": ref,
            "callback_url": "https://kwachapoint.onrender.com/api/webhook"
        }
        headers = {"Authorization": "Bearer MNO_ACCESS_TOKEN"}
        try:
            await client.post(MNO_STK_ENDPOINT, json=data, headers=headers)
        except Exception as e:
            print(f"MNO Network Error: {e}")

# --- API ENDPOINTS ---

@router.post("/v1/checkout/initiate-stk")
async def initiate_stk_push(payload: dict, background_tasks: Background_Tasks, db: Session = Depends(get_db)):
    customer_phone = payload.get("phone")
    amount = payload.get("amount")
    merchant_id = payload.get("merchant_id", "00000000-0000-0000-0000-000000000000") # Default for testing
    
    if not customer_phone or not amount:
        raise HTTPException(status_code=400, detail="Missing phone or amount")

    # 1. Create a "Pending" Transaction in our DB
    tx_ref = str(uuid.uuid4())
    
    try:
        db.execute(text("""
            INSERT INTO ledger.transactions (id, amount, destination, merchant_id, status, created_at)
            VALUES (:id, :amount, :phone, :mid, 'PENDING', CURRENT_TIMESTAMP)
        """), {
            "id": tx_ref,
            "amount": amount,
            "phone": customer_phone,
            "mid": merchant_id
        })
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Database Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to save transaction")

    # 2. Trigger the network request in the background
    background_tasks.add_task(send_to_mno, customer_phone, amount, tx_ref)

    return {
        "status": "initiated",
        "message": "PIN prompt sent to customer",
        "tx_ref": tx_ref
    }

@router.post("/api/webhooks/mno")
async def mno_callback(data: dict, background_tasks: Background_Tasks, db: Session = Depends(get_db)):
    """The master brain that receives MNO results and triggers notifications."""
    ref = data.get("external_id")
    status = data.get("status")

    if status == "SUCCESS":
        # 1. Update Ledger status
        db.execute(text("UPDATE ledger.transactions SET status = 'SUCCESS' WHERE id = :id"), {"id": ref})
        db.commit()

        # 2. Fetch Merchant & Transaction details for notifications
        query = text("""
            SELECT m.webhook_url, t.amount, t.destination 
            FROM ledger.merchants m 
            JOIN ledger.transactions t ON m.id = t.merchant_id 
            WHERE t.id = :id
        """)
        result = db.execute(query, {"id": ref}).fetchone()

        if result:
            payload = {
                "tx_ref": ref,
                "status": "PAID",
                "amount": float(result.amount),
                "phone": result.destination
            }
            
            # 3. Queue Smart Notifications
            background_tasks.add_task(notify_merchant_webhook, result.webhook_url, payload)
            background_tasks.add_task(send_customer_sms, result.destination, f"KwachaPoint: Paid {result.amount} MWK. Ref: {ref}")

    return {"status": "ok"}