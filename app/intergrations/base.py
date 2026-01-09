from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Dict, Any, Optional
import logging

class PaymentError(Exception):
    def __init__(self, message: str, provider_code: str, raw_response: Any = None):
        self.message = message
        self.provider_code = provider_code
        self.raw_response = raw_response
        super().__init__(self.message)

class BasePaymentProvider(ABC):
    def __init__(self):
        self.logger = logging.getLogger(f"KwachaPoint.Provider.{self.__class__.__name__}")

    @abstractmethod
    async def trigger_ussd_push(self, phone: str, amount: Decimal, tx_ref: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def verify_webhook(self, payload: Dict[str, Any], signature: str) -> bool:
        pass

    @abstractmethod
    async def get_transaction_status(self, tx_ref: str) -> str:
        pass

    def normalize_phone(self, phone: str) -> str:
        clean = phone.replace("+265", "").replace(" ", "").lstrip("0")
        return f"265{clean}"