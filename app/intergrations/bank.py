import httpx
from .base import BasePaymentProvider, PaymentError
from app.config import settings
from decimal import Decimal

class BankDirectProvider(BasePaymentProvider):
    async def trigger_ussd_push(self, phone: str, amount: Decimal, tx_ref: str):
        self.logger.info(f"[BANK] Initiating transfer request for {tx_ref}")
        
        url = f"{settings.MOCK_GATEWAY_URL}/bank/initiate"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json={"ref": tx_ref, "amount": str(amount)})
                data = response.json()
                
                return {
                    "status": "SUCCESS",
                    "instructions": data.get("instructions", "Transfer to Standard Bank Acct: 12345"),
                    "provider_ref": data.get("provider_ref", "BANK_MOCK_999")
                }
            except Exception as e:
                raise PaymentError("Bank Gateway Unavailable", "BANK")

    async def verify_webhook(self, payload: dict, signature: str) -> bool:
        return True

    async def get_transaction_status(self, tx_ref: str) -> str:
        return "PENDING"