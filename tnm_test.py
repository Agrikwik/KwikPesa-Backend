import httpx
import asyncio
import uuid
import json
import hmac
import hashlib

MERCHANT_ID = "d405e9d9-71c5-4aec-8f3b-c8d4f288d054" 
SECRET_KEY = "sk_test_secret_7722"
BASE_URL = "http://localhost:8000"

def generate_signature(secret, payload):
    """Calculates the HMAC SHA256 signature"""
    payload_str = json.dumps(payload, sort_keys=True, separators=(',', ':'))
    return hmac.new(
        secret.encode(),
        payload_str.encode(),
        hashlib.sha256
    ).hexdigest()

async def run_simulation():
    async with httpx.AsyncClient() as client:
        print("--- Starting Secure Full Loop Simulation ---")

        print(f"Creating Payment for Merchant: {MERCHANT_ID}")
        checkout_payload = {
            "merchant_id": MERCHANT_ID,
            "amount": 10000.00,
            "phone": "0888997766",
            "provider": "tnm"
        }
        
        signature = generate_signature(SECRET_KEY, checkout_payload)
        #signature = "fake-code-123" --- uncommeent this line and comment the ubove line to test the functionality of HMAC ---
        headers = {"x-signature": signature}


        
        res1 = await client.post(
            f"{BASE_URL}/v1/checkout", 
            json=checkout_payload, 
            headers=headers
        )

        if res1.status_code != 200:
            print(f"Checkout Failed: {res1.text}")
            return
        
        data = res1.json()
        tx_id = data["tx_ref"]
        print(f"Transaction Created: {tx_id}")

        print("\n" + "-"*30 + "\n")

        print(f"Sending Mock Webhook for {tx_id}...")
        webhook_payload = {
            "transaction": {
                "id": tx_id,
                "status": "SUCCESS",
                "tnm_mpamba_id": f"AM-{uuid.uuid4().hex[:10].upper()}"
            }
        }
        
        res2 = await client.post(f"{BASE_URL}/v1/webhooks/tnm", json=webhook_payload)
        
        if res2.status_code == 200:
            print(f"Webhook Processed: {res2.json()['status']}")
        else:
            print(f"Webhook Failed: {res2.text}")

        print("\n--- Simulation Complete ---")
        print(f"Check your database for TX {tx_id} and Merchant {MERCHANT_ID} balance!")

if __name__ == "__main__":
    asyncio.run(run_simulation())