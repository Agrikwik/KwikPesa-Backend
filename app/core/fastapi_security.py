import secrets
import hashlib
from fastapi import Security, HTTPException, status, Depends
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session
from app.db.session import SessionLocal

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

async def validate_api_key(
    api_key: str = Security(api_key_header),
    db: Session = Depends(get_db)
):
    if not api_key:
        raise HTTPException(status_code=401, detail="API Key missing")

    hashed_input = hashlib.sha256(api_key.encode()).hexdigest()

    merchant = db.execute(
        text("SELECT id, name FROM ledger.merchants WHERE api_key_hashed = :h AND is_active = TRUE"),
        {"h": hashed_input}
    ).mappings().first()

    if not merchant:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive API Key"
        )

    return merchant