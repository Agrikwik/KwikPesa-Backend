from app.intergrations.airtel import AirtelMoneyProvider
from app.config import settings

class ProviderRouter:
    @staticmethod
    def get_provider(method: str = None, phone: str = None):
        
        if method == "AIRTEL":
            return AirtelMoneyProvider(
                client_id=settings.AIRTEL_CLIENT_ID, 
                client_secret=settings.AIRTEL_CLIENT_SECRET,
                env=settings.ENVIRONMENT
            )
        
        if method in ["TNM", "BANK"]:
            raise ValueError(f"{method} integration is coming soon. Please use Airtel Money.")

        if phone:
            clean_phone = phone.replace("+265", "").lstrip("0")
            
            if clean_phone.startswith(("99", "98")):
                return AirtelMoneyProvider(
                    client_id=settings.AIRTEL_CLIENT_ID, 
                    client_secret=settings.AIRTEL_CLIENT_SECRET,
                    env=settings.ENVIRONMENT
                )
            
            elif clean_phone.startswith(("88", "89")):
                raise ValueError("TNM Mpamba is not yet enabled. Please use an Airtel number.")
            
            raise ValueError(f"Unknown or unsupported network prefix: {clean_phone[:2]}")

        raise ValueError("A valid Airtel phone number or 'AIRTEL' method is required.")