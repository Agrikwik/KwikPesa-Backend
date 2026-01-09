import hmac
import hashlib
import json
from fastapi import HTTPException, Request

class SecurityService:
    @staticmethod
    def generate_signature(secret_key: str, payload: dict) -> str:
        payload_string = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        return hmac.new(
            secret_key.encode(),
            payload_string.encode(),
            hashlib.sha256
        ).hexdigest()

    @staticmethod
    def verify_signature(secret_key: str, signature: str, payload: dict):
        expected = SecurityService.generate_signature(secret_key, payload)
        if not hmac.compare_digest(expected, signature):
            raise HTTPException(status_code=401, detail="Invalid HMAC signature")