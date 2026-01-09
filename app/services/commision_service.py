from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import text
from sqlalchemy.orm import Session

class CommissionService:
    # 1. Your markup (What you charge the merchant)
    MERCHANT_FEE_RATE = Decimal("0.02")

    # 2. Third-party costs (What you pay the provider)
    # These are standard estimates for Malawi; adjust based on your contracts.
    PROVIDER_RATES = {
        "AIRTEL": Decimal("0.012"),   # 1.2%
        "TNM": Decimal("0.012"),      # 1.2%
        "BANK_NBM": Decimal("0.005"), # 0.5% (Banks are usually cheaper)
        "BANK_STD": Decimal("0.005"),
    }

    @staticmethod

    @staticmethod
    def apply_commission(db: Session, transaction_id: str, merchant_id: str, provider: str, total_amount: Decimal):
        # Math remains the same
        gross_commission = (total_amount * CommissionService.MERCHANT_FEE_RATE).quantize(Decimal("0.01"))
        net_to_merchant = total_amount - gross_commission
        rate = CommissionService.PROVIDER_RATES.get(provider, Decimal("0.01"))
        external_fee = (total_amount * rate).quantize(Decimal("0.01"))

        # --- UPDATED LEDGER ENTRIES ---

        # 1. Credit Merchant (+98%)
        db.execute(text("""
            INSERT INTO ledger.ledger_entries (transaction_id, account_id, credit, debit)
            VALUES (:tx_id, :m_id, :amt, 0)
        """), {"tx_id": transaction_id, "m_id": merchant_id, "amt": net_to_merchant})

        # 2. Credit KP Gross Revenue (+2%)
        db.execute(text("""
            INSERT INTO ledger.ledger_entries (transaction_id, account_id, credit, debit)
            VALUES (:tx_id, '00000000-0000-0000-0000-000000000001', :amt, 0) -- Use a valid UUID for your revenue account
        """), {"tx_id": transaction_id, "amt": gross_commission})

        # 3. Debit External Fees (The 'Loss')
        # In accounting, an expense is usually recorded as a DEBIT to an expense account
        db.execute(text("""
            INSERT INTO ledger.ledger_entries (transaction_id, account_id, credit, debit)
            VALUES (:tx_id, '00000000-0000-0000-0000-000000000002', 0, :amt) -- Use a valid UUID for provider expense
        """), {"tx_id": transaction_id, "amt": external_fee})

        # Finalize
        db.execute(text("""
            UPDATE ledger.transactions SET status = 'SUCCESS' WHERE id = :id
        """), {"id": transaction_id})
        
        db.commit()
        print(f"📊 Reconciled: Merchant (+{net_to_merchant}) | KP Gross (+{gross_commission}) | Provider Cost (-{external_fee})")