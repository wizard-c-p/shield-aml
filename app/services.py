import logging
import queue
import threading
import numpy as np
from sklearn.ensemble import IsolationForest
from .database import SessionLocal
from .models import Transaction, User, Blacklist, Watchlist, SystemConfig

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ShieldAML")

class DualMLEngine:
    """
    Dual-Engine AI for Segment-Based Anomaly Detection.
    Uses Isolation Forest algorithm (Unsupervised Learning).
    """
    model_individual = IsolationForest(contamination=0.01, random_state=42)
    model_commercial = IsolationForest(contamination=0.01, random_state=42)
    is_trained = False

    @classmethod
    def train_models(cls):
        """Trains separate models for Individual and Commercial segments."""
        # 1. Individual Data (Normal: 1k - 20k)
        ind_data = np.abs(np.random.normal(5000, 2000, (500, 1)))
        cls.model_individual.fit(ind_data)

        # 2. Commercial Data (Normal: 50k - 500k)
        com_data = np.abs(np.random.normal(200000, 50000, (500, 1)))
        cls.model_commercial.fit(com_data)

        cls.is_trained = True
        logger.info("🧠 Dual AI Models Trained Successfully.")

    @classmethod
    def predict_anomaly(cls, amount: float, segment: str) -> int:
        """Returns risk points if anomaly is detected."""
        if not cls.is_trained: return 0
        
        if segment == "COMMERCIAL":
            prediction = cls.model_commercial.predict([[amount]])
            return 35 if prediction[0] == -1 else 0
        else:
            prediction = cls.model_individual.predict([[amount]])
            return 50 if prediction[0] == -1 else 0

# In-Memory Queue for Asynchronous Processing
# NOTE: For Production, replace this with RabbitMQ or Kafka.
task_queue = queue.Queue()

def get_config_value(db, key, default):
    """Helper to fetch dynamic configuration from DB."""
    cfg = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    return float(cfg.value) if cfg else default

def background_worker():
    """
    Consumer thread that processes transactions from the queue.
    Checks Blacklists, Watchlists, Dynamic Limits, and AI Anomalies.
    """
    logger.info("👷 Background Worker Active.")
    while True:
        task = task_queue.get()
        if task is None: break
        
        tx_id = task
        db = SessionLocal()
        try:
            tx = db.query(Transaction).filter(Transaction.id == tx_id).first()
            sender = db.query(User).filter(User.id == tx.sender_id).first()
            
            score = 0
            rules = []

            # 1. Blacklist Check (Strict Block)
            blk = db.query(Blacklist).filter(Blacklist.identity_no == tx.target_identity_no).first()
            if blk:
                score += 100
                rules.append(f"BLACKLIST HIT: {blk.reason}")

            # 2. Watchlist Check (Monitoring)
            wlist = db.query(Watchlist).filter(Watchlist.identity_no == tx.target_identity_no).first()
            if wlist:
                points = 60 if wlist.risk_level == "HIGH" else 30
                score += points
                rules.append(f"WATCHLIST MATCH: {wlist.risk_level} Risk")

            # 3. Dynamic Limits (Fetched from DB)
            if sender.segment == "COMMERCIAL":
                limit = get_config_value(db, "LIMIT_COMMERCIAL", 500000.0)
                if tx.amount > limit:
                    score += 20
                    rules.append(f"RULE: Commercial Limit Exceeded (> {limit})")
            else:
                limit = get_config_value(db, "LIMIT_INDIVIDUAL", 20000.0)
                if tx.amount > limit:
                    score += 25
                    rules.append(f"RULE: Individual Limit Exceeded (> {limit})")

            # 4. AI Analysis
            ai_score = DualMLEngine.predict_anomaly(tx.amount, sender.segment)
            if ai_score > 0:
                score += ai_score
                rules.append(f"AI: Anomaly Detected for {sender.segment} (+{ai_score})")

            # Final Decision Logic
            tx.risk_score = min(score, 100)
            tx.triggered_rules = ", ".join(rules) if rules else "Clean Transaction"
            
            if score >= 80: tx.status = "REJECTED"
            elif score >= 30: tx.status = "UNDER_REVIEW"
            else: tx.status = "APPROVED"
            
            db.commit()

        except Exception as e:
            logger.error(f"❌ Worker Error: {e}")
        finally:
            db.close()
            task_queue.task_done()

# Start the worker thread
threading.Thread(target=background_worker, daemon=True).start()