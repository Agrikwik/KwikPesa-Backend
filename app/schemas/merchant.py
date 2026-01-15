from pydantic import BaseModel
from typing import Dict

class MerchantStatsResponse(BaseModel):
    business_name: str
    balance: float
    sales: float
    success_rate: float
    provider_split: Dict[str, float]
    role: str
    id: int