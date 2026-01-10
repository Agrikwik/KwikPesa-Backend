from app.core.database import SessionLocal
from app.models.app_models import User
from app.models.auth_utils import hash_password
import uuid

def create_initial_admin():
    db = SessionLocal()
    if db.query(User).filter(User.email == "admin@kwikpesa.com").first():
        print("Admin already exists.")
        return

    admin = User(
        id=uuid.uuid4(),
        email="admin@kwikpesa.com",
        password_hash=hash_password("Systemadministrator@415"),
        full_name="KwikPesa Admin",
        role="admin",
        is_verified=True
    )
    db.add(admin)
    db.commit()
    print("System Admin created successfully.")

if __name__ == "__main__":
    create_initial_admin()