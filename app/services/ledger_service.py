from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import text
import uuid

class FeeService:
    @staticmethod
    def calculate_fees(amount: Decimal):
        # 1.5% Total Fee
        total_fee = (amount * Decimal("0.015")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        # 0.5% Provider Cost (what Airtel/TNM charges)
        provider_cost = (amount * Decimal("0.005")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        
        merchant_credit = amount - total_fee
        our_revenue = total_fee - provider_cost
        
        return {
            "merchant_credit": merchant_credit,
            "our_commission": our_revenue,
            "provider_expense": provider_cost
        }

class LedgerService:
    @staticmethod
    def record_successful_payment(db, transaction_id: str, amount: Decimal):
        fees = FeeService.calculate_fees(amount)
        REVENUE_ACC_ID = '00000000-0000-0000-0000-000000000000'
        
        try:
            db.execute(text("""
                UPDATE ledger.transactions 
                SET status = 'SUCCESS', 
                    completed_at = CURRENT_TIMESTAMP
                WHERE id = :id AND status = 'PENDING'
            """), {"id": transaction_id})

            result = db.execute(text(
                "SELECT merchant_id FROM ledger.transactions WHERE id = :id"
            ), {"id": transaction_id}).fetchone()
            
            if not result:
                raise ValueError(f"Transaction {transaction_id} not found")
            
            merchant_id = result.merchant_id

            db.execute(text("""
                UPDATE ledger.merchants 
                SET balance = balance + :amt 
                WHERE id = :m_id
            """), {"amt": fees['merchant_credit'], "m_id": merchant_id})

            db.execute(text("""
                UPDATE ledger.merchants 
                SET balance = balance + :rev_amt 
                WHERE id = :rev_id
            """), {"rev_amt": fees['our_commission'], "rev_id": REVENUE_ACC_ID})

            db.execute(text("""
                INSERT INTO ledger.ledger_entries (transaction_id, account_id, credit, debit)
                VALUES (:tx_id, :acc_id, :amt, 0)
            """), {"tx_id": transaction_id, "acc_id": merchant_id, "amt": fees['merchant_credit']})

            db.execute(text("""
                INSERT INTO ledger.ledger_entries (transaction_id, account_id, credit, debit)
                VALUES (:tx_id, :acc_id, :amt, 0)
            """), {
                "tx_id": transaction_id, 
                "acc_id": REVENUE_ACC_ID,
                "amt": fees['our_commission']
            })

            db.commit()
            print(f"Balances Synced: Merchant +{fees['merchant_credit']}, Revenue +{fees['our_commission']}")
            return True
            
        except Exception as e:
            db.rollback()
            print(f"Ledger Error: {e}")
            raise e