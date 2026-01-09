import hmac
import hashlib
import json
from fastapi import Request, HTTPException, Header

SHARED_SECRET = b"kwacha_point_ultra_secret_key_415"

def verify_hmac_signature(payload: bytes, received_signature: str):
    expected_signature = hmac.new(
        SHARED_SECRET,
        msg=payload,
        digestmod=hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected_signature, received_signature):
        raise HTTPException(status_code=403, detail="Invalid Security Signature")
    
    return True

    