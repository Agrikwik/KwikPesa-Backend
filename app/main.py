import os
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text

# Internal Imports
from app.api.deps import get_db
from app.api.webhooks import router as webhook_router
from app.api.checkout import router as checkout_router
from app.api.dashboard import router as dashboard_router
from app.auth.router import router as auth_router
from app.core.database import engine, Base
from app.api import links, store
from app.api import invoices

def init_db():
    with engine.connect() as connection:
        connection.execute(text("CREATE SCHEMA IF NOT EXISTS ledger"))
        connection.commit()
    Base.metadata.create_all(bind=engine)

init_db()

app = FastAPI(title="KwikPesa Payment Gateway", version="1.0.0")

# --- CORS CONFIGURATION ---
# Replace the first URL with your actual live React URL from Render
origins = [
    "https://kwikpesa-k3vi.onrender.com",  
    "http://localhost:5173",               # Standard Vite dev port
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API ROUTERS ---
app.include_router(auth_router, tags=["Authentication"])
app.include_router(checkout_router, prefix="/v1/checkout", tags=["Checkout"])
app.include_router(webhook_router, prefix="/v1/webhooks", tags=["Webhooks"])
app.include_router(dashboard_router, prefix="/api/merchant", tags=["Merchant Dashboard"])
app.include_router(
    links.router, 
    tags=["Payments"]
)
app.include_router(
    store.router, 
    tags=["Store"]
)
app.include_router(
    invoices.router,
    tags=["Invoice"]
)

# --- ROOT REDIRECT ---
@app.get("/")
async def root():
    """Redirects API visitors to the main React frontend."""
    return RedirectResponse(url="https://kwikpesa-k3vi.onrender.com")

# --- PUBLIC CHECKOUT PAGE ---
from fastapi.templating import Jinja2Templates
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

@app.get("/pay/{short_code}", response_class=HTMLResponse)
async def public_checkout_page(short_code: str, request: Request, db: Session = Depends(get_db)):
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

# --- GLOBAL ERROR HANDLER ---
@app.exception_handler(404)
async def not_found_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=404, 
        content={"message": "API endpoint not found. Visit /docs for documentation."}
    )
