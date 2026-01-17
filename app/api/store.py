import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import List, Optional

from app.api.deps import get_db, get_current_user
from app.models.app_models import User

router = APIRouter()

class ProductCreate(BaseModel):
    name: str
    price: float
    stock: int
    description: Optional[str] = None

class ProductResponse(ProductCreate):
    id: uuid.UUID
    sales_count: int = 0
    revenue: float = 0.0

class StoreDashboardResponse(BaseModel):
    summary: dict
    products: List[ProductResponse]

@router.post("/api/store/add-product")
async def add_product(
    item: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Creates a new product in the store."""
    try:
        query = text("""
            INSERT INTO ledger.products (merchant_id, name, price, stock, description)
            VALUES (:mid, :name, :price, :stock, :desc)
            RETURNING id
        """)
        result = db.execute(query, {
            "mid": current_user.id,
            "name": item.name,
            "price": item.price,
            "stock": item.stock,
            "desc": item.description
        }).fetchone()
        db.commit()
        return {"status": "success", "product_id": result.id}
    except Exception as e:
        db.rollback()
        print(f"Store Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to add product")

@router.get("/api/store/dashboard", response_model=StoreDashboardResponse)
async def get_store_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    products_query = text("""
        SELECT 
            p.id, p.name, p.price, p.stock, p.description,
            COALESCE(SUM(t.amount), 0) as revenue,
            COUNT(t.id) as sales_count
        FROM ledger.products p
        LEFT JOIN ledger.transactions t 
            ON t.metadata->>'product_id' = CAST(p.id AS TEXT) 
            AND t.status = 'SUCCESS'
        WHERE p.merchant_id = :mid AND p.is_active = TRUE
        GROUP BY p.id
        ORDER BY p.created_at DESC
    """)
    
    products = db.execute(products_query, {"mid": current_user.id}).fetchall()
    total_products = len(products)
    total_revenue = sum(p.revenue for p in products)
    total_orders = sum(p.sales_count for p in products)

    product_list = [
        {
            "id": p.id,
            "name": p.name,
            "price": float(p.price),
            "stock": p.stock,
            "description": p.description,
            "sales_count": p.sales_count,
            "revenue": float(p.revenue)
        }
        for p in products
    ]

    return {
        "summary": {
            "total_products": total_products,
            "total_revenue": total_revenue,
            "total_orders": total_orders
        },
        "products": product_list
    }