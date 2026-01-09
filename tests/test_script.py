import random
import uuid
from decimal import Decimal
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

DATABASE_URL = "postgresql://postgres:kwachapoint415@localhost:5432/postgres"
engine = create_engine(DATABASE_URL)

def generate_test_data():
    print("Starting KwachaPoint Stress Test...")
    
    merchants = [uuid.uuid4() for _ in range(10)]
    treasury_id = uuid.uuid4()
    
    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO accounts (id, owner_id, type, balance, currency) 
            VALUES (:id, :owner, 'TREASURY', 1000000, 'MWK')
        """), {"id": treasury_id, "owner": uuid.uuid4()})
        
        for m_id in merchants:
            conn.execute(text("INSERT INTO accounts (id, owner_id, type, balance) VALUES (:id, :owner, 'MERCHANT', 0)"), 
                         {"id": m_id, "owner": uuid.uuid4()})
        conn.commit()

    success_count = 0
    duplicate_prevented = 0
    used_keys = []

    for i in range(1000):
        if i > 10 and i % 10 == 0:
            ikey = random.choice(used_keys)
            is_dup_attempt = True
        else:
            ikey = str(uuid.uuid4())
            used_keys.append(ikey)
            is_dup_attempt = False
        
        amount = Decimal(random.uniform(10.00, 500.00)).quantize(Decimal('0.0001'))
        m_id = random.choice(merchants)

        try:
            with engine.begin() as conn:
                tx_res = conn.execute(text("""
                    INSERT INTO transactions (idempotency_key, amount, description, status) 
                    VALUES (:ik, :amt, 'Test Payment', 'SUCCESS') RETURNING id
                """), {"ik": ikey, "amt": amount})
                tx_id = tx_res.fetchone()[0]

                conn.execute(text("""
                    INSERT INTO ledger_entries (transaction_id, account_id, debit, credit)
                    VALUES (:tx, :acc, :amt, 0), (:tx, :m_acc, 0, :amt)
                """), {"tx": tx_id, "acc": treasury_id, "m_acc": m_id, "amt": amount})
                
                success_count += 1
        except IntegrityError:
            if is_dup_attempt:
                duplicate_prevented += 1
            continue

    with engine.connect() as conn:
        audit = conn.execute(text("SELECT SUM(credit) - SUM(debit) FROM ledger_entries")).fetchone()[0]
        print(f"--- RESULTS ---")
        print(f"Success Transactions: {success_count}")
        print(f"Duplicates Blocked: {duplicate_prevented}")
        print(f"Final Ledger Balance: {audit}")

if __name__ == "__main__":
    generate_test_data()