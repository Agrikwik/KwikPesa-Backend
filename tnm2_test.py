import httpx
import asyncio
import uuid
import json
import hmac
import hashlib
import time

MERCHANT_ID = "d405e9d9-71c5-4aec-8f3b-c8d4f288d054" 
SECRET_KEY = "sk_test_secret_7722"
BASE_URL = "http://localhost:8000"

def generate_signature(secret, payload):
    payload_str = json.dumps(payload, sort_keys=True, separators=(',', ':'))
    return hmac.new(secret.encode(), payload_str.encode(), hashlib.sha256).hexdigest()

async def run_simulation():
    async with httpx.AsyncClient() as client:
        print("--- Orchestration & Commission Test ---")

        checkout_payload = {
            "merchant_id": MERCHANT_ID,
            "amount": 9850.00,
            "phone": "0889997766",
            "provider": "tnm"
        }
        
        signature = generate_signature(SECRET_KEY, checkout_payload)
        headers = {"x-signature": signature}

        print(f"Sending Checkout Request...")
        res1 = await client.post(f"{BASE_URL}/v1/checkout", json=checkout_payload, headers=headers)

        if res1.status_code not in [200, 202]:
            print(f"Initial Request Failed: {res1.text}")
            return
        
        data = res1.json()
        tx_id = data["tx_ref"]
        print(f"API Accepted Request. TX_REF: {tx_id}")
        print(f"Status: {data['status']} - {data['message']}")

        print(f"\nWaiting for Background Orchestration (Retries/Commissions)...")
        await asyncio.sleep(5) 

        print(f"Verifying Triple-Entry Ledger for {tx_id}...")
        

        print(f"   Expected Split:")
        print(f"   -> Merchant Account:  +980.00 MWK")
        print(f"   -> KP Gross Revenue:  +20.00  MWK")
        print(f"   -> Provider Expense:  -12.00  MWK (TNM 1.2%)")
        print(f"   -> YOUR NET PROFIT:   +8.00   MWK")

        print(f"\n[*] Sending Mock Webhook to finalize...")
        webhook_payload = {
            "transaction": {
                "id": tx_id,
                "status": "SUCCESS",
                "provider_id": f"EXT-{uuid.uuid4().hex[:6].upper()}"
            }
        }
        await client.post(f"{BASE_URL}/v1/webhooks/tnm", json=webhook_payload)

        print("\nSimulation Complete. Run the 'Audit Query' in your DB to confirm balances.")

if __name__ == "__main__":
    asyncio.run(run_simulation())