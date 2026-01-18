from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from app.api import deps
from app.models.app_models import User
import uuid
from fpdf import FPDF

router = APIRouter(prefix="/api/invoices", tags=["Invoice"])

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

    result = db.execute("""
        SELECT 
            id, 
            invoice_number, 
            client_name, 
            total_amount, 
            status, 
            issue_date 
        FROM ledger.invoices 
        WHERE merchant_id = :mid 
        ORDER BY created_at DESC
    """, {"mid": current_user.id}).fetchall()
    
    invoices_list = [
        {
            "id": str(row.id),
            "invoice_number": row.invoice_number,
            "client_name": row.client_name,
            "total_amount": float(row.total_amount),
            "status": row.status,
            "issue_date": str(row.issue_date)
        } for row in result
    ]
    return {
        "stats": {
            "total_invoiced": float(stats.total_invoiced),
            "paid_count": stats.paid_count,
            "paid_amount": float(stats.paid_amount),
            "pending_count": stats.pending_count,
            "pending_amount": float(stats.pending_amount)
        },
        "invoices": invoices_list
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

@router.patch("/{invoice_id}/pay")
def mark_invoice_as_paid(invoice_id: str, db: Session = Depends(deps.get_db), current_user: User = Depends(deps.get_current_user)):
    db.execute(
        "UPDATE ledger.invoices SET status = 'paid' WHERE id = :id AND merchant_id = :mid",
        {"id": invoice_id, "mid": current_user.id}
    )
    db.commit()
    return {"message": "Invoice marked as paid"}

@router.get("/{invoice_id}/download")
def download_invoice(invoice_id: str, db: Session = Depends(deps.get_db), current_user: User = Depends(deps.get_current_user)):
    invoice = db.execute(
        "SELECT * FROM ledger.invoices WHERE id = :id AND merchant_id = :mid",
        {"id": invoice_id, "mid": current_user.id}
    ).fetchone()
    
    items = db.execute(
        "SELECT * FROM ledger.invoice_items WHERE invoice_id = :id",
        {"id": invoice_id}
    ).fetchall()

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    
    pdf.cell(0, 10, f"INVOICE: {invoice.invoice_number}", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 10, f"Date: {invoice.issue_date} | Due: {invoice.due_date}", ln=True)
    pdf.ln(10)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 10, "Bill To:", ln=True)
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 10, f"{invoice.client_name}", ln=True)
    pdf.cell(0, 10, f"Email: {invoice.client_email or 'N/A'}", ln=True)
    pdf.ln(10)

    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(100, 10, "Description", border=1, fill=True)
    pdf.cell(30, 10, "Qty", border=1, fill=True)
    pdf.cell(30, 10, "Rate", border=1, fill=True)
    pdf.cell(30, 10, "Total", border=1, fill=True, ln=True)

    pdf.set_font("Helvetica", "", 10)
    for item in items:
        pdf.cell(100, 10, item.description, border=1)
        pdf.cell(30, 10, str(item.quantity), border=1)
        pdf.cell(30, 10, f"{item.rate:,.2f}", border=1)
        pdf.cell(30, 10, f"{item.amount:,.2f}", border=1, ln=True)

    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(160, 10, "GRAND TOTAL (MWK):", align="R")
    pdf.cell(30, 10, f"{invoice.total_amount:,.2f}", align="R", ln=True)

    return Response(
        content=pdf.output(),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=Invoice_{invoice.invoice_number}.pdf"}
    )
