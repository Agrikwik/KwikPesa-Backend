import uuid
import asyncio
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.intergrations.airtel import AirtelMoneyProvider
from app.intergrations.tnm import TNMMpambaProvider
from app.intergrations.bank import BankDirectProvider
from app.services.commision_service import CommissionService

class CheckoutService:
    def __init__(self, db: Session):
        self.db = db
        self.providers = {
            "airtel": AirtelMoneyProvider(),
            "tnm": TNMMpambaProvider(),
            "bank": BankDirectProvider()
        }

    async def create_local_record(self, merchant_id: str, amount: Decimal, destination: str, provider_name: str) -> str:
        """Saves the initial intent. Returns tx_id immediately."""
        tx_ref = f"KP-{uuid.uuid4().hex[:8].upper()}"
        idem_key = f"IDEM-{uuid.uuid4().hex[:12].upper()}"

        self.db.execute(text("""
            INSERT INTO ledger.transactions (id, merchant_id, amount, destination, provider, status, idempotency_key)
            VALUES (:id, :m_id, :amt, :dest, :prov, 'PENDING', :idem)
        """), {
            "id": tx_ref, "m_id": merchant_id, "amt": amount, 
            "dest": destination, "prov": provider_name.upper(), "idem": idem_key
        })
        self.db.commit()
        return tx_ref

    async def process_with_retry(self, tx_id: str, provider_name: str, destination: str, amount: Decimal, attempt: int = 1):
        MAX_RETRIES = 3
        provider = self.providers.get(provider_name.lower())

        if not provider:
            print(f"Error: Unsupported provider {provider_name}")
            return

        try:
            print(f"[Attempt {attempt}] Calling {provider_name} for {tx_id}...")
            
            # 1. Trigger the actual USSD/Bank API
            result = await provider.trigger_ussd_push(destination, amount, tx_id)

            # 2. Check Result
            if result.get("status") == "SUCCESS":
                # Get merchant info to apply commission
                tx_record = self.db.execute(
                    text("SELECT merchant_id FROM ledger.transactions WHERE id = :id"), 
                    {"id": tx_id}
                ).fetchone()

                CommissionService.apply_commission(
                    self.db, 
                    transaction_id=tx_id, 
                    merchant_id=tx_record.merchant_id, 
                    provider=provider_name.upper(), 
                    total_amount=amount
                )
                print(f"{tx_id} fully processed and split.")
            
            else:
                # API responded but transaction is waiting for User PIN
                self.db.execute(text(
                    "UPDATE ledger.transactions SET status = 'PROCESSING' WHERE id = :id"
                ), {"id": tx_id})
                self.db.commit()
                print(f"{tx_id} waiting for user PIN.")

        except Exception as e:
            if attempt < MAX_RETRIES:
                # Exponential Backoff: 30s, 60s, 90s
                wait_time = 30 * attempt 
                print(f"{tx_id} API failure: {str(e)}. Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
                await self.process_with_retry(tx_id, provider_name, destination, amount, attempt + 1)
            else:
                print(f"{tx_id} failed after {MAX_RETRIES} attempts.")
                self.db.execute(text(
                    "UPDATE ledger.transactions SET status = 'FAILED' WHERE id = :id"
                ), {"id": tx_id})
                self.db.commit()