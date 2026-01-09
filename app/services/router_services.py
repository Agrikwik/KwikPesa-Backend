import re
from fastapi import HTTPException

class RouterService:
    TELCO_PREFIXES = {
        "AIRTEL": ["99", "98"],
        "TNM": ["88", "89"],
    }

    SUPPORTED_BANKS = {
        "NBM": {"name": "National Bank of Malawi", "sort_code": "050015"},
        "STD": {"name": "Standard Bank", "sort_code": "010000"},
        "NBS": {"name": "NBS Bank", "sort_code": "100100"},
        "FCB": {"name": "First Capital Bank", "sort_code": "030006"},
        "ECO": {"name": "Ecobank", "sort_code": "040000"},
    }

    @staticmethod
    def clean_phone(phone: str) -> str:
        digits = re.sub(r'\D', '', phone)
        if digits.startswith('265') and len(digits) > 9:
            digits = digits[3:]
        if digits.startswith('0'):
            digits = digits[1:]
        
        if len(digits) != 9:
            raise HTTPException(status_code=400, detail="Invalid phone number")
        return digits

    @staticmethod
    def route_request(payload: dict):
        provider_key = payload.get("provider", "").upper()

        if provider_key in RouterService.SUPPORTED_BANKS:
            account_no = payload.get("account_number")
            if not account_no or len(account_no) < 5:
                raise HTTPException(status_code=400, detail="Valid Account Number required for Bank transfers")
            
            return f"BANK_{provider_key}", account_no

        elif provider_key in ["AIRTEL", "TNM", "MOBILE_MONEY"]:
            phone = payload.get("phone")
            if not phone:
                 raise HTTPException(status_code=400, detail="Phone number required for Mobile Money")
            
            clean_num = RouterService.clean_phone(phone)
            prefix = clean_num[:2]

            for telco, prefixes in RouterService.TELCO_PREFIXES.items():
                if prefix in prefixes:
                    return telco, clean_num
            
            raise HTTPException(status_code=400, detail="Phone number does not match any Malawi Telco")

        else:
            raise HTTPException(status_code=400, detail=f"Provider '{provider_key}' is not supported yet")