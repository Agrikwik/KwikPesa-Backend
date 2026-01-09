import hmac
import hashlib
import json
import httpx
import asyncio

SECRET_KEY = "sk_test_secret_7722"
URL = "http://localhost:8000/v1/checkout"

def sign_payload(payload):
    payload_str = json.dumps(payload, sort_keys=True, separators=(',', ':'))
    return hmac.new(SECRET_KEY.encode(), payload_str.encode(), hashlib.sha256).hexdigest()

async def run_security_test():
    payload = {
        "merchant_id": "d405e9d9-71c5-4aec-8f3b-c8d4f288d054",
        "amount": 500.0,
        "phone": "0999123456",
        "provider": "airtel"
    }

    async with httpx.AsyncClient() as client:
        sig = sign_payload(payload)
        res1 = await client.post(URL, json=payload, headers={"X-Signature": sig})
        print(f"Honest Request: {res1.status_code} (Expect 200)")

        payload["amount"] = 50000.0
        res2 = await client.post(URL, json=payload, headers={"X-Signature": sig}) 
        print(f"Tampered Request: {res2.status_code} (Expect 401)")

if __name__ == "__main__":
    asyncio.run(run_security_test())