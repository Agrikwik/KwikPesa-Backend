import httpx
import asyncio
import uuid

BASE_URL = "http://127.0.0.1:8000/v1/payments/initiate"
VALID_KEY = "kp_test_123456"

async def run_security_suite():
    print("Starting KwachaPoint Security Integration Test...\n")

    async with httpx.AsyncClient(timeout=10.0) as client: 
        
        print("Test 1: Requesting without API Key...")
        res1 = await client.post(BASE_URL, json={})
        print(f"Result: {res1.status_code} (Expected: 401) {'OK' if res1.status_code == 401 else 'WRONG'}")

        print("\nTest 2: Requesting with Fake API Key...")
        res2 = await client.post(BASE_URL, headers={"X-API-Key": "wrong_key"}, json={})
        print(f"Result: {res2.status_code} (Expected: 401) {'OK' if res2.status_code == 401 else 'WRONG'}")

        print("\nTest 3: Valid Key with Bad Phone Number...")
        payload_bad = {
            "amount": 1000,
            "phone": "invalid_number"
        }
        res3 = await client.post(BASE_URL, headers={"X-API-Key": VALID_KEY}, json=payload_bad)
        print(f"Result: {res3.status_code} (Expected: 422 Unprocessable Content) {'OK' if res3.status_code == 422 else 'WRONG'}")

        print("\nTest 4: Authorized Successful Request...")
        payload_ok = {
            "amount": 500.50,
            "phone": "0991234567",
            "currency": "MWK"
        }
        res4 = await client.post(BASE_URL, headers={"X-API-Key": VALID_KEY}, json=payload_ok)
        print(f"Result: {res4.status_code} (Expected: 201) {'OK' if res4.status_code == 201 else 'WRONG'}")
        if res4.status_code == 201:
            print(f"Response Body: {res4.json()}")

if __name__ == "__main__":
    asyncio.run(run_security_suite())