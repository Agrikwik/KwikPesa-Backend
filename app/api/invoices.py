from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api import deps
from app.models.models import User
import uuid

router = APIRouter(prefix="/api/invoices", tags=["Invoices"])

@router.get("/dashboard-stats")
def get_invoice_stats(db: Session = Depends(deps.get_db), current_user: User = Depends(deps.get_current_user)):
    stats = db.execute("""
        SELECT 
            COALESCE(SUM(total_amount), 0) as total_invoiced,
            COUNT(CASE WHEN status = 'paid' THEN 1 END) as paid_count,
            COALESCE(SUM(CASE WHEN status = 'paid' THEN total_amount ELSE 0 END), 0) as paid_amount,
            COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_count,
            COALESCE(SUM(CASE WHEN status = 'pending' THEN total_amount ELSE 0 END), 0) as pending_amount
        FROM ledger.invoices 
        WHERE merchant_id = :mid
    """, {"mid": current_user.id}).fetchone()
    
    invoices = db.execute("""
        SELECT id, invoice_number, client_name, total_amount, status, issue_date 
        FROM ledger.invoices 
        WHERE merchant_id = :mid 
        ORDER BY created_at DESC
    """, {"mid": current_user.id}).fetchall()
    
    return {
        "stats": stats,
        "invoices": invoices
    }

@router.post("/create")
def create_invoice(data: dict, db: Session = Depends(deps.get_db), current_user: User = Depends(deps.get_current_user)):
    try:
        inv_query = """
            INSERT INTO ledger.invoices (merchant_id, invoice_number, client_name, client_email, client_phone, issue_date, due_date, notes, total_amount)
            VALUES (:mid, :num, :name, :email, :phone, :issue, :due, :notes, :total)
            RETURNING id
        """
        inv_id = db.execute(inv_query, {
            "mid": current_user.id,
            "num": data['invoiceNumber'],
            "name": data['clientName'],
            "email": data['clientEmail'],
            "phone": data['clientPhone'],
            "issue": data['issueDate'],
            "due": data['dueDate'],
            "notes": data['notes'],
            "total": sum(item['quantity'] * item['rate'] for item in data['items'])
        }).fetchone()[0]

        for item in data['items']:
            db.execute("""
                INSERT INTO ledger.invoice_items (invoice_id, description, quantity, rate, amount)
                VALUES (:inv_id, :desc, :qty, :rate, :amt)
            """, {
                "inv_id": inv_id,
                "desc": item['description'],
                "qty": item['quantity'],
                "rate": item['rate'],
                "amt": item['quantity'] * item['rate']
            })
        
        db.commit()
        return {"status": "success", "message": "Invoice Created"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
