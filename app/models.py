import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from .database import Base

class SystemConfig(Base):
    """
    Stores dynamic system configurations like transaction limits, 
    AI sensitivity, and maintenance mode status.
    """
    __tablename__ = "system_configs"
    key = Column(String, primary_key=True, index=True) # e.g., 'MAINTENANCE_MODE'
    value = Column(String) # e.g., 'TRUE'
    description = Column(String) # Tooltip description for UI

class User(Base):
    """Represents bank customers."""
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String)
    identity_no = Column(String, unique=True, index=True)
    segment = Column(String) # 'INDIVIDUAL' or 'COMMERCIAL'
    sector = Column(String, nullable=True) # e.g., 'RETAIL', 'TECH'

class Blacklist(Base):
    """Identities strictly prohibited from transacting (Sanctions, Fraud)."""
    __tablename__ = "blacklist"
    id = Column(Integer, primary_key=True)
    identity_no = Column(String, unique=True, index=True)
    reason = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Watchlist(Base):
    """Identities under monitoring (PEPs, High Risk)."""
    __tablename__ = "watchlist"
    id = Column(Integer, primary_key=True)
    identity_no = Column(String, unique=True, index=True)
    risk_level = Column(String) # 'HIGH' or 'MEDIUM'
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Transaction(Base):
    """Stores all financial transaction records and their risk analysis results."""
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True)
    sender_id = Column(Integer, ForeignKey("users.id"))
    target_identity_no = Column(String)
    amount = Column(Float)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Analysis Results
    status = Column(String, default="PENDING") # PENDING, APPROVED, REJECTED, SAVED_FOR_LATER
    risk_score = Column(Integer, default=0)
    triggered_rules = Column(String, nullable=True)