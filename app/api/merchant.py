from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.api.deps import get_db
from app.auth.router import get_current_user
from app.models.app_models import User
from app.schemas.merchant import MerchantStatsResponse # Import the schema above

router = APIRouter()

@router.get("/api/merchant/stats", response_model=MerchantStatsResponse)
async def get_merchant_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Fetches real-time statistics for the logged-in merchant.
    """
    try:
        # 1. Get Balance (Ensure it's a float for JSON)
        balance = float(current_user.balance) if current_user.balance else 0.0

        # 2. Today's Sales (Strictly for this merchant and today)
        # We use DATE(created_at) to ensure we only get today's data
        sales_query = text("""
            SELECT SUM(amount) FROM ledger.transactions 
            WHERE merchant_id = :mid 
            AND status = 'SUCCESS' 
            AND DATE(created_at) = CURRENT_DATE
        """)
        sales_result = db.execute(sales_query, {"mid": current_user.id}).scalar()
        sales = float(sales_result) if sales_result else 0.0

        # 3. Success Rate Calculation
        rate_query = text("""
            SELECT 
                COUNT(*) FILTER (WHERE status = 'SUCCESS')::float / 
                NULLIF(COUNT(*), 0) * 100
            FROM ledger.transactions 
            WHERE merchant_id = :mid
        """)
        rate_result = db.execute(rate_query, {"mid": current_user.id}).scalar()
        success_rate = round(float(rate_result), 1) if rate_result else 0.0

        # 4. Provider Split (Real distribution from transaction history)
        # This replaces the hardcoded 70/30 with actual data
        split_query = text("""
            SELECT provider, 
                   (COUNT(*)::float / SUM(COUNT(*)) OVER ()) * 100 as percentage
            FROM ledger.transactions 
            WHERE merchant_id = :mid AND status = 'SUCCESS'
            GROUP BY provider
        """)
        split_results = db.execute(split_query, {"mid": current_user.id}).fetchall()
        
        # Convert DB rows to a clean Dictionary
        # Default to empty split if no transactions exist
        provider_split = {row[0]: round(row[1], 1) for row in split_results} if split_results else {"Airtel": 0, "TNM": 0}

        return {
            "id": current_user.id,
            "business_name": current_user.business_name or "KwikPesa Merchant",
            "balance": balance,
            "sales": sales,
            "success_rate": success_rate,
            "provider_split": provider_split,
            "role": current_user.role
        }

    except Exception as e:
        # Log the error in production logs
        print(f"Error in merchant stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error fetching statistics")


from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

# Schema for a single transaction row
class TransactionSchema(BaseModel):
    id: str
    amount: float
    currency: str
    status: str
    provider: str
    customer_phone: str
    created_at: datetime

@router.get("/api/merchant/transactions", response_model=Dict)
async def get_merchant_transactions(
    page: int = 1,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    offset = (page - 1) * limit
    
    # 1. Fetch total count for pagination math
    count_query = text("SELECT COUNT(*) FROM ledger.transactions WHERE merchant_id = :mid")
    total_count = db.execute(count_query, {"mid": current_user.id}).scalar()

    # 2. Fetch the specific page of transactions
    tx_query = text("""
        SELECT id, amount, currency, status, provider, customer_phone, created_at 
        FROM ledger.transactions 
        WHERE merchant_id = :mid 
        ORDER BY created_at DESC 
        LIMIT :limit OFFSET :offset
    """)
    
    results = db.execute(tx_query, {
        "mid": current_user.id, 
        "limit": limit, 
        "offset": offset
    }).fetchall()

    # Map to list of dicts
    transactions = [
        {
            "id": row.id,
            "amount": float(row.amount),
            "currency": row.currency,
            "status": row.status,
            "provider": row.provider,
            "customer_phone": row.customer_phone,
            "created_at": row.created_at
        } for row in results
    ]

    return {
        "transactions": transactions,
        "total_pages": (total_count + limit - 1) // limit,
        "current_page": page
    }