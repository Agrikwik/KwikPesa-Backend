import logging
from fastapi import APIRouter, Request, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.services.ledger_service import LedgerService
from decimal import Decimal


router = APIRouter()
logger = logging.getLogger("KwachaPoint.Webhooks")

@router.post("/airtel")
async def airtel_webhook(
    request: Request, 
    db: Session = Depends(get_db)
):
    payload = await request.json()
    tx_id = payload.get("transaction", {}).get("id")
    status = payload.get("transaction", {}).get("status")
    
    if not tx_id:
        logger.error("Webhook received with no Transaction ID")
        raise HTTPException(status_code=400, detail="Missing transaction ID")

    logger.info(f"Received Webhook for TX: {tx_id} - Status: {status}")

    if status != "SUCCESS":
        from sqlalchemy import text
        db.execute(text("UPDATE ledger.transactions SET status = 'FAILED' WHERE id = :id"), {"id": tx_id})
        db.commit()
        return {"status": "FAILED_ACKNOWLEDGED"}

    try:
        from sqlalchemy import text
        tx_data = db.execute(text(
            "SELECT amount FROM ledger.transactions WHERE id = :id AND status = 'PENDING'"
        ), {"id": tx_id}).fetchone()

        if not tx_data:
            logger.warning(f"TX {tx_id} already processed or not found.")
            return {"status": "ALREADY_PROCESSED"}

        LedgerService.record_successful_payment(
            db=db,
            transaction_id=tx_id,
            amount=tx_data.amount
        )
        
        return {"status": "SUCCESS_ACKNOWLEDGED"}

    except Exception as e:
        logger.error(f"Webhook Processing Failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal processing error")



@router.post("/tnm")
async def tnm_webhook(
    request: Request, 
    db: Session = Depends(get_db)
):
    payload = await request.json()
    tx_id = payload.get("transaction", {}).get("id")
    status = payload.get("transaction", {}).get("status")
    
    if not tx_id:
        logger.error("Webhook received with no Transaction ID")
        raise HTTPException(status_code=400, detail="Missing transaction ID")

    logger.info(f"Received Webhook for TX: {tx_id} - Status: {status}")

    if status != "SUCCESS":
        from sqlalchemy import text
        db.execute(text("UPDATE ledger.transactions SET status = 'FAILED' WHERE id = :id"), {"id": tx_id})
        db.commit()
        return {"status": "FAILED_ACKNOWLEDGED"}

    try:
        from sqlalchemy import text
        tx_data = db.execute(text(
            "SELECT amount FROM ledger.transactions WHERE id = :id AND status = 'PENDING'"
        ), {"id": tx_id}).fetchone()

        if not tx_data:
            logger.warning(f"TX {tx_id} already processed or not found.")
            return {"status": "ALREADY_PROCESSED"}

        LedgerService.record_successful_payment(
            db=db,
            transaction_id=tx_id,
            amount=tx_data.amount
        )
        
        return {"status": "SUCCESS_ACKNOWLEDGED"}

    except Exception as e:
        logger.error(f"Webhook Processing Failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal processing error")


@router.post("/bank")
async def bank_webhook(data: dict, db: Session = Depends(get_db)):
    """Simulates Bank Transfer (Standard/National/NBS)"""
    tx_id = data.get("ext_ref")
    amount = Decimal(data.get("amount_cents", 0)) / 100 
    
    if data.get("payment_status") == "COMPLETED":
        LedgerService.record_successful_payment(db, tx_id, amount)
    return {"message": "Bank Received"}