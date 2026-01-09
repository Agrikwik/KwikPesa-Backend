import httpx
import asyncio


async def test_payment():
    print("Step 1: Triggering Payment...")
    async with httpx.AsyncClient() as client:
        payload = {
            "merchant_id": "d405e9d9-71c5-4aec-8f3b-c8d4f288d054",
            "amount": 500,
            "phone": "0999123456",
            "provider": "airtel"
        }
        
        response = await client.post("http://localhost:8000/v1/checkout", json=payload)
        
        if response.status_code != 200:
            print(f"Server Error ({response.status_code}): {response.text}")
            return

        data = response.json()
        
        if 'tx_ref' not in data:
            print(f"Missing 'tx_ref'. Full Response: {data}")
            return
            
        tx_ref = data['tx_ref']
        print(f"Created TX: {tx_ref}")


if __name__ == "__main__":
    asyncio.run(test_payment())