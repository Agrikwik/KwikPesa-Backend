import uuid
from fastapi import APIRouter, Depends, HTTPException, Header, Request, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import text
from decimal import Decimal

from app.core.database import SessionLocal
from app.api.deps import get_db
from app.services.checkout_service import CheckoutService
from app.services.security_services import SecurityService
from app.services.router_services import RouterService
from app.models.app_models import User

router = APIRouter()

async def run_background_orchestrator(tx_id: str, provider: str, destination: str, amount: Decimal):
    # Isolated session for background tasks to avoid thread-safety issues
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

    # 1. Look for the merchant in the UNIFIED 'users' table
    # We check for role='merchant' to ensure an admin isn't accidentally used as a merchant
    merchant = db.query(User).filter(
        User.id == merchant_id, 
        User.role == "merchant"
    ).first()

    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found or invalid role")

    # 2. Verify Signature using the unified table's hashed key
    # Ensure your SecurityService.verify_signature handles the hashed comparison correctly
    SecurityService.verify_signature(
        secret_key=merchant.api_key_hashed, # Matches our unified model column name
        signature=x_signature,
        payload=body
    )

    # 3. Route the request (Airtel/TNM/etc)
    provider_type, destination = RouterService.route_request(body)

    # 4. Initialize Transaction
    tx_id = f"KP-{uuid.uuid4().hex[:8].upper()}"
    try:
        # Note: Ensure ledger.transactions table has a foreign key pointing to ledger.users(id)
        db.execute(text("""
            INSERT INTO ledger.transactions (id, merchant_id, amount, provider, status, destination)
            VALUES (:id, :m_id, :amount, :provider, 'PENDING', :dest)
        """), {
            "id": tx_id, 
            "m_id": merchant.id, 
            "amount": amount,
            "provider": provider_type, 
            "dest": destination
        })
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"CRITICAL: Transaction Init Failed: {e}")
        raise HTTPException(status_code=500, detail="Internal processing error")

    # 5. Offload to background orchestrator
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
        "message": "Payment request received"
    }