import httpx
import asyncio
import uuid

MERCHANT_ID = "d405e9d9-71c5-4aec-8f3b-c8d4f288d054" 
BASE_URL = "http://localhost:8000"

async def run_simulation():
    async with httpx.AsyncClient() as client:
        print("--- Starting Full Loop Simulation ---")

        print(f"[Step 1] Creating Payment for Merchant: {MERCHANT_ID}")
        checkout_payload = {
            "merchant_id": MERCHANT_ID,
            "amount": 1000.00,
            "phone": "0999887766",
            "provider": "airtel"
        }
        
        res1 = await client.post(f"{BASE_URL}/v1/checkout", json=checkout_payload)
        if res1.status_code != 200:
            print(f"Checkout Failed: {res1.text}")
            return
        
        data = res1.json()
        tx_id = data["tx_ref"]
        print(f"Transaction Created: {tx_id}")

        print("\n" + "-"*30 + "\n")

        print(f"[Step 2] Sending Mock Webhook for {tx_id}...")
        webhook_payload = {
            "transaction": {
                "id": tx_id,
                "status": "SUCCESS",
                "airtel_money_id": f"AM-{uuid.uuid4().hex[:10].upper()}"
            }
        }
        
        res2 = await client.post(f"{BASE_URL}/v1/webhooks/airtel", json=webhook_payload)
        
        if res2.status_code == 200:
            print(f"Webhook Processed: {res2.json()['status']}")
        else:
            print(f"Webhook Failed: {res2.text}")

        print("\n--- Simulation Complete ---")
        print(f"Check your database for TX {tx_id} and Merchant {MERCHANT_ID} balance!")

if __name__ == "__main__":
    asyncio.run(run_simulation())