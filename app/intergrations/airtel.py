import httpx
from .base import BasePaymentProvider, PaymentError
from app.config import settings
from decimal import Decimal

class AirtelMoneyProvider(BasePaymentProvider):
    async def trigger_ussd_push(self, phone: str, amount: Decimal, tx_ref: str):
        self.logger.info(f"Initiating push for {phone} - Ref: {tx_ref}")
        
        url = f"{settings.MOCK_GATEWAY_URL}/airtel/push"
        payload = {
            "msisdn": self.normalize_phone(phone),
            "amount": float(amount),
            "reference": tx_ref
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, timeout=10.0)
                data = response.json()
                
                if response.status_code != 200:
                    raise PaymentError("Airtel Gateway rejected request", "AIRTEL", data)
                
                return {
                    "status": "SUCCESS",
                    "provider_ref": data.get("provider_ref"),
                    "message": "PIN prompt initiated"
                }
            except Exception as e:
                self.logger.error(f"Airtel Connection Failed: {e}")
                raise PaymentError("Could not connect to Airtel", "AIRTEL")

    async def verify_webhook(self, payload: dict, signature: str) -> bool:
        return True

    async def get_transaction_status(self, tx_ref: str) -> str:
        return "PENDING"