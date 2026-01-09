import uuid
from decimal import Decimal
from sqlalchemy import text
from app.db.session import SessionLocal
from app.services.ledger_service import LedgerService

def run_ultimate_test():
    db = SessionLocal()
    print("Starting Ultimate Stage 1 Test...")

    db.execute(text("SET search_path TO ledger, public"))

    tx_id = uuid.uuid4()
    m_id = uuid.uuid4()
    t_id = uuid.uuid4()
    f_id = uuid.uuid4()
    p_id = uuid.uuid4()
    
    amount = Decimal("10000.00")

    try:
        print("Setting up test accounts...")
        db.execute(text("""
            INSERT INTO accounts (id, owner_id, type, currency) 
            VALUES (:id, :owner, 'MERCHANT', 'MWK')
        """), {"id": m_id, "owner": uuid.uuid4()})
        
        db.execute(text("""
            INSERT INTO accounts (id, owner_id, type, currency) 
            VALUES (:id, :owner, 'TREASURY', 'MWK')
        """), {"id": t_id, "owner": uuid.uuid4()})
        
        db.execute(text("""
            INSERT INTO accounts (id, owner_id, type, currency) 
            VALUES (:id, :owner, 'FEE_COLLECTION', 'MWK')
        """), {"id": f_id, "owner": uuid.uuid4()})
        
        db.execute(text("""
            INSERT INTO accounts (id, owner_id, type, currency) 
            VALUES (:id, :owner, 'PROVIDER_SETTLEMENT', 'MWK')
        """), {"id": p_id, "owner": uuid.uuid4()})
        
        db.commit()

        print("Processing 10,000 MWK Payment...")
        LedgerService.record_successful_payment(
            db, tx_id, m_id, t_id, f_id, p_id, amount, "AIRTEL"
        )
        
        m_balance = db.execute(text(
            "SELECT SUM(credit) - SUM(debit) FROM ledger_entries WHERE account_id = :id"
        ), {"id": m_id}).scalar()
        print(f"Merchant Balance: {m_balance} MWK (Expected: 9850.00)")

        print("Processing Refund...")
        LedgerService.process_refund(db, tx_id, m_id, t_id)
        
        total_audit = db.execute(text(
            "SELECT SUM(credit) - SUM(debit) FROM ledger_entries"
        )).scalar()
        
        total_audit = Decimal(str(total_audit)).quantize(Decimal("0.0001"))
        
        print(f"Final Global Ledger Balance: {total_audit}")
        
        if total_audit == Decimal("0.0000"):
            print("STAGE 1 VERIFIED: System is mathematically perfect.")
        else:
            print(f"AUDIT FAILED: Difference of {total_audit} detected!")

    except Exception as e:
        print(f"Test crashed with error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    run_ultimate_test()