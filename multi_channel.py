import httpx
import asyncio

async def simulate_payment(provider, amount, webhook_path, payload_generator):
    async with httpx.AsyncClient() as client:
        res = await client.post("http://localhost:8000/v1/checkout", json={
            "merchant_id": "d405e9d9-71c5-4aec-8f3b-c8d4f288d054",
            "amount": amount,
            "phone": "0888000111",
            "provider": provider
        })
        tx_id = res.json()["tx_ref"]
        print(f"Created {provider} TX: {tx_id}")

        webhook_payload = payload_generator(tx_id, amount)
        await client.post(f"http://localhost:8000/v1/webhooks/{webhook_path}", json=webhook_payload)
        print(f"💰 Confirmed {provider} payment!")

# Run all 3
async def main():
    tasks = [
        simulate_payment("airtel", 500, "airtel", lambda id, amt: {"transaction": {"id": id, "status": "SUCCESS"}}),
        simulate_payment("tnm", 1200, "tnm", lambda id, amt: {"reference": id, "status": "SUCCESS", "amount": amt}),
        simulate_payment("bank", 5000, "bank", lambda id, amt: {"ext_ref": id, "payment_status": "COMPLETED", "amount_cents": int(amt*100)})
    ]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())