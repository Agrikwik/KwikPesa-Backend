import uuid
from fastapi import APIRouter, Depends, HTTPException, Header, Request, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import text
from decimal import Decimal

from app.api.deps import get_db, SessionLocal
from app.services.checkout_service import CheckoutService
from app.services.security_services import SecurityService
from app.services.router_services import RouterService

router = APIRouter()

async def run_background_orchestrator(tx_id: str, provider: str, destination: str, amount: Decimal):
    with SessionLocal() as db:
        service = CheckoutService(db)
        await service.process_with_retry(tx_id, provider, destination, amount)

@router.post("")
async def create_checkout(
    request: Request,
    background_tasks: BackgroundTasks, 
    db: Session = Depends(get_db),
    x_signature: str = Header(...)
):
    body = await request.json()
    merchant_id = body.get("merchant_id")
    amount = Decimal(str(body.get("amount", 0)))

    if not merchant_id:
        raise HTTPException(status_code=400, detail="merchant_id is required")

    merchant = db.execute(text(
        "SELECT secret_key_hashed FROM ledger.merchants WHERE id = :id"
    ), {"id": merchant_id}).fetchone()

    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")

    SecurityService.verify_signature(
        secret_key=merchant.secret_key_hashed,
        signature=x_signature,
        payload=body
    )

    provider_type, destination = RouterService.route_request(body)

    tx_id = f"KP-{uuid.uuid4().hex[:8].upper()}"
    try:
        db.execute(text("""
            INSERT INTO ledger.transactions (id, merchant_id, amount, provider, status, destination)
            VALUES (:id, :m_id, :amount, :provider, 'PENDING', :dest)
        """), {
            "id": tx_id, "m_id": merchant_id, "amount": amount,
            "provider": provider_type, "dest": destination
        })
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Database Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to initialize transaction")

    background_tasks.add_task(
        run_background_orchestrator, 
        tx_id, 
        provider_type, 
        destination, 
        amount
    )

    return {
        "status": "processing",
        "tx_ref": tx_id,
        "provider": provider_type,
        "message": "Payment request received and is being processed"
    }