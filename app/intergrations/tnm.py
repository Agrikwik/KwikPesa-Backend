import httpx
from .base import BasePaymentProvider, PaymentError
from app.config import settings
from decimal import Decimal

class TNMMpambaProvider(BasePaymentProvider):
    async def trigger_ussd_push(self, phone: str, amount: Decimal, tx_ref: str):
        self.logger.info(f"[TNM] Initiating Mpamba Push for {phone}")
        
        url = f"{settings.MOCK_GATEWAY_URL}/tnm/push"
        payload = {
            "msisdn": self.normalize_phone(phone),
            "amount": str(amount),
            "trans_id": tx_ref,
            "remarks": f"Payment for {tx_ref}"
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, timeout=10.0)
                data = response.json()
                
                if response.status_code != 200:
                    raise PaymentError("TNM Gateway rejected request", "TNM", data)
                
                return {
                    "status": "SUCCESS",
                    "provider_ref": data.get("provider_ref", f"TNM_{tx_ref[:6]}"),
                    "message": "Mpamba PIN prompt sent"
                }
            except Exception as e:
                self.logger.error(f"TNM Connection Failed: {e}")
                raise PaymentError("Could not connect to TNM Mpamba", "TNM")

    async def verify_webhook(self, payload: dict, signature: str) -> bool:
        return True

    async def get_transaction_status(self, tx_ref: str) -> str:
        return "PENDING"