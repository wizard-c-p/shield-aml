import os
import math
from pathlib import Path
from fastapi import FastAPI, Depends, HTTPException, Request, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import desc
from .database import engine, Base, get_db, SessionLocal
from .models import User, Blacklist, Watchlist, Transaction, SystemConfig
from .services import DualMLEngine, task_queue
from pydantic import BaseModel

# Initialize Tables
Base.metadata.create_all(bind=engine)

# Initialize App
app = FastAPI(
    title="ShieldAML Enterprise v1.0",
    description="Hybrid AI Risk Engine for Anti-Money Laundering",
    version="1.0.0"
)

# Template Configuration
BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

@app.on_event("startup")
def startup_event():
    """Initializes AI models and seeds default data."""
    DualMLEngine.train_models()
    db = SessionLocal()
    
    # Seed Default Configs
    configs = [
        ("LIMIT_INDIVIDUAL", "50000", "Daily limit for Individual customers"),
        ("LIMIT_COMMERCIAL", "500000", "Daily limit for Commercial entities"),
        ("AI_SENSITIVITY", "0.01", "AI Anomaly Sensitivity (0.01 - 0.1)"),
        ("MAINTENANCE_MODE", "FALSE", "If TRUE, transactions are saved but not processed"),
        ("CURRENCY_SYMBOL", "₺", "Currency symbol for UI")
    ]
    for k, v, d in configs:
        if not db.query(SystemConfig).filter(SystemConfig.key == k).first():
            db.add(SystemConfig(key=k, value=v, description=d))
    
    # Seed Users
    if not db.query(User).first():
        db.add(User(full_name="Atlas Nova Ind.", identity_no="10001", segment="INDIVIDUAL"))
        db.add(User(full_name="Zenith Corp", identity_no="20002", segment="COMMERCIAL"))

    db.commit()
    db.close()

# --- Data Transfer Objects (DTOs) ---
class TransferRequest(BaseModel):
    sender_id: int
    target_identity_no: str
    amount: float

class ListRequest(BaseModel):
    identity_no: str
    reason_or_level: str 

# --- API ENDPOINTS ---

@app.post("/api/v1/transfer", tags=["Transaction"])
def create_transfer(req: TransferRequest, db: Session = Depends(get_db)):
    """Initiates a financial transfer. Checks for Maintenance Mode."""
    mode = db.query(SystemConfig).filter(SystemConfig.key == "MAINTENANCE_MODE").first()
    
    tx = Transaction(
        sender_id=req.sender_id, 
        target_identity_no=req.target_identity_no, 
        amount=req.amount
    )
    
    if mode and mode.value == "TRUE":
        # Resilience Pattern: Save but don't process
        tx.status = "SAVED_FOR_LATER"
        tx.risk_score = 0
        tx.triggered_rules = "System in Maintenance. Saved for replay."
        db.add(tx); db.commit(); db.refresh(tx)
        return {"tx_id": tx.id, "status": "SAVED", "message": "System Maintenance. Transaction saved."}
    else:
        # Standard Flow
        tx.status = "PENDING"
        db.add(tx); db.commit(); db.refresh(tx)
        task_queue.put(tx.id)
        return {"tx_id": tx.id, "status": "QUEUED"}

@app.post("/api/v1/maintenance/replay", tags=["Admin"])
def replay_saved_transactions(db: Session = Depends(get_db)):
    """Re-queues saved transactions after maintenance is over."""
    saved_txs = db.query(Transaction).filter(Transaction.status == "SAVED_FOR_LATER").all()
    count = 0
    for tx in saved_txs:
        tx.status = "QUEUED"
        task_queue.put(tx.id)
        count += 1
    db.commit()
    return {"status": "SUCCESS", "message": f"{count} transactions re-queued."}

@app.get("/api/v1/status/{tx_id}", tags=["Transaction"])
def get_status(tx_id: int, db: Session = Depends(get_db)):
    tx = db.query(Transaction).filter(Transaction.id == tx_id).first()
    return tx if tx else {}

@app.get("/api/v1/transactions/recent", tags=["Reporting"])
def get_recent_transactions(db: Session = Depends(get_db)):
    return db.query(Transaction).order_by(desc(Transaction.timestamp)).limit(5).all()

# --- LIST MANAGEMENT ENDPOINTS ---

@app.post("/api/v1/blacklist", tags=["Lists"])
def upsert_blacklist(req: ListRequest, db: Session = Depends(get_db)):
    """Add or Update Blacklist entry."""
    if db.query(Watchlist).filter(Watchlist.identity_no == req.identity_no).first():
        raise HTTPException(400, "Error: Identity is in Watchlist. Remove it first.")

    existing = db.query(Blacklist).filter(Blacklist.identity_no == req.identity_no).first()
    if existing:
        existing.reason = req.reason_or_level
        msg = "Updated"
    else:
        db.add(Blacklist(identity_no=req.identity_no, reason=req.reason_or_level))
        msg = "Added"
    db.commit()
    return {"status": msg}

@app.delete("/api/v1/blacklist/{identity_no}", tags=["Lists"])
def del_blacklist(identity_no: str, db: Session = Depends(get_db)):
    db.query(Blacklist).filter(Blacklist.identity_no == identity_no).delete()
    db.commit()
    return {"status": "Deleted"}

@app.post("/api/v1/watchlist", tags=["Lists"])
def upsert_watchlist(req: ListRequest, db: Session = Depends(get_db)):
    """Add or Update Watchlist entry."""
    if db.query(Blacklist).filter(Blacklist.identity_no == req.identity_no).first():
        raise HTTPException(400, "Error: Identity is Blacklisted.")
        
    existing = db.query(Watchlist).filter(Watchlist.identity_no == req.identity_no).first()
    if existing:
        existing.risk_level = req.reason_or_level.upper()
        msg = "Updated"
    else:
        db.add(Watchlist(identity_no=req.identity_no, risk_level=req.reason_or_level.upper()))
        msg = "Added"
    db.commit()
    return {"status": msg}

@app.delete("/api/v1/watchlist/{identity_no}", tags=["Lists"])
def del_watchlist(identity_no: str, db: Session = Depends(get_db)):
    db.query(Watchlist).filter(Watchlist.identity_no == identity_no).delete()
    db.commit()
    return {"status": "Deleted"}

@app.post("/api/v1/config/update", tags=["Config"])
async def update_config_ui(request: Request, key: str = Form(...), value: str = Form(...), db: Session = Depends(get_db)):
    cfg = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    if cfg:
        cfg.value = value
        db.commit()
    return RedirectResponse(url="/config", status_code=303)

# --- FRONTEND ROUTERS ---

@app.get("/", response_class=HTMLResponse)
async def dashboard_page(request: Request, db: Session = Depends(get_db)):
    recent_txs = db.query(Transaction).order_by(desc(Transaction.timestamp)).limit(5).all()
    users = db.query(User).all()
    return templates.TemplateResponse("dashboard.html", {"request": request, "recent_txs": recent_txs, "users": users})

@app.get("/history", response_class=HTMLResponse)
async def history_page(request: Request, page: int = Query(1, ge=1), db: Session = Depends(get_db)):
    page_size = 15
    total_txs = db.query(Transaction).count()
    total_pages = math.ceil(total_txs / page_size)
    offset = (page - 1) * page_size
    transactions = db.query(Transaction).order_by(desc(Transaction.timestamp)).offset(offset).limit(page_size).all()
    
    return templates.TemplateResponse("history.html", {
        "request": request, "transactions": transactions, "page": page, "total_pages": total_pages
    })

@app.get("/lists", response_class=HTMLResponse)
async def lists_page(request: Request, db: Session = Depends(get_db)):
    blacklist = db.query(Blacklist).all()
    watchlist = db.query(Watchlist).all()
    return templates.TemplateResponse("lists.html", {"request": request, "blacklist": blacklist, "watchlist": watchlist})

@app.get("/config", response_class=HTMLResponse)
async def config_page(request: Request, db: Session = Depends(get_db)):
    configs = db.query(SystemConfig).all()
    return templates.TemplateResponse("config.html", {"request": request, "configs": configs})