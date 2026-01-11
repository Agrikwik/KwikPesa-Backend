import os
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text

# Internal Imports
from app.api.deps import get_db
from app.api.webhooks import router as webhook_router
from app.api.checkout import router as checkout_router
from app.api.dashboard import router as dashboard_router
from app.auth.router import router as auth_router
from app.core.database import engine, Base

# --- DATABASE INITIALIZATION ---
def init_db():
    with engine.connect() as connection:
        # Create the schema first!
        connection.execute(text("CREATE SCHEMA IF NOT EXISTS ledger"))
        connection.commit()
    # Now it is safe to create the tables
    Base.metadata.create_all(bind=engine)

# Run the initialization BEFORE creating the FastAPI app instance
init_db()

app = FastAPI(title="KwachaPoint Payment Gateway", version="1.0.0")

# Setup Static Files & Templates
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Ensure your static and templates folders are in the root directory
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# Include Routers
app.include_router(auth_router, tags=["Authentication"])
app.include_router(checkout_router, prefix="/v1/checkout", tags=["Checkout"])
app.include_router(webhook_router, prefix="/v1/webhooks", tags=["Webhooks"])
app.include_router(dashboard_router, tags=["Admin"])
app.include_router(dashboard_router, prefix="/api/merchant", tags=["Dashboard"])



@app.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    return templates.TemplateResponse("auth.html", {"request": request})

@app.get("/admin", response_class=HTMLResponse)
async def read_dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("auth.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    return templates.TemplateResponse("merchant_dashboard.html", {"request": request})

@app.get("/redirect")
async def auth_redirect_handler():
    return JSONResponse(content={"redirect_url": "/dashboard"})

# --- PAYMENT LINK HANDLER ---

@app.get("/pay/{short_code}", response_class=HTMLResponse)
async def public_checkout_page(short_code: str, request: Request, db: Session = Depends(get_db)):
    # Using a robust query to fetch link details
    query = text("""
        SELECT l.amount, l.description, l.status, m.business_name as merchant_name
        FROM ledger.payment_links l
        JOIN ledger.users m ON l.merchant_id = m.id
        WHERE l.short_code = :code
    """)
    link = db.execute(query, {"code": short_code}).fetchone()

    if not link:
        raise HTTPException(status_code=404, detail="Payment link not found")
    
    if link.status == 'PAID':
        return templates.TemplateResponse("error_paid.html", {"request": request})

    return templates.TemplateResponse("checkout_page.html", {
        "request": request,
        "merchant_name": link.merchant_name,
        "amount": f"{link.amount:,.2f}",
        "description": link.description,
        "short_code": short_code
    })

# --- ERROR HANDLERS ---
@app.exception_handler(404)
async def not_found_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=404, 
        content={"message": "The page or endpoint you are looking for does not exist."}
    )