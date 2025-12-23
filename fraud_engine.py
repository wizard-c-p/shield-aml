import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings("ignore", message=".*glibc.*")
from xgboost import XGBClassifier
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import LabelEncoder
import database

# Global Model Storage
_MODELS = {}

def generate_synthetic_data(n=10000):
    """
    Generates robust synthetic data with specific fraud scenarios
    to teach the AI model.
    """
    np.random.seed(42)
    
    data = pd.DataFrame({
        'amount': np.random.lognormal(mean=4, sigma=1.5, size=n), # Normal distribution
        'hour': np.random.randint(0, 24, size=n),
        'minute': np.random.randint(0, 60, size=n),
        'segment': np.random.choice(['Individual', 'Corporate', 'Student'], size=n, p=[0.6, 0.3, 0.1]),
        'is_international': np.random.choice([0, 1], size=n, p=[0.8, 0.2]),
        'daily_txn_count': np.random.poisson(lam=2, size=n), # New feature: Frequency
        'hist_avg_diff': np.random.normal(0, 0.2, size=n), # New feature: Deviation %
        'is_fraud': 0
    })
    
    # --- Scenario Injection (The "Teacher") ---
    
    # 1. The "Whale" Anomaly: Amount > 1,000,000 is Fraud (unless Corporate)
    mask_whale = (data['amount'] > 1000000) & (data['segment'] != 'Corporate')
    data.loc[mask_whale, 'is_fraud'] = 1
    
    # 2. The "Night Owl": High amounts (>20k) between 02:00-05:00 AM
    mask_night = (data['hour'].between(2, 5)) & (data['amount'] > 20000)
    data.loc[mask_night, 'is_fraud'] = 1
    
    # 3. The "Segment Violation": Student sending > 50,000
    mask_student = (data['segment'] == 'Student') & (data['amount'] > 50000)
    data.loc[mask_student, 'is_fraud'] = 1
    
    # 4. Smurfing: Repeated ~9900
    smurf_indices = np.random.choice(data.index, size=int(n*0.02))
    data.loc[smurf_indices, 'amount'] = np.random.uniform(9800, 9999, size=len(smurf_indices))
    data.loc[smurf_indices, 'is_fraud'] = 1
    
    # 5. High Frequency Fraud
    mask_freq = (data['daily_txn_count'] > 15)
    data.loc[mask_freq, 'is_fraud'] = 1
    
    return data

def train_models():
    """
    Trains XGBoost and Isolation Forest with Feature Scaling.
    """
    print("Training Fraud Models...")
    df = generate_synthetic_data()
    
    # --- Preprocessing ---
    # 1. Feature Scaling: Log Transform for Amount (Crucial for "Trillion" fix)
    df['log_amount'] = np.log1p(df['amount'])
    
    # 2. Encoding
    le_segment = LabelEncoder()
    df['segment_code'] = le_segment.fit_transform(df['segment'])
    
    # Added new features to model
    X = df[['log_amount', 'hour', 'minute', 'segment_code', 'is_international', 'daily_txn_count', 'hist_avg_diff']]
    y = df['is_fraud']
    
    # --- Model 1: XGBoost (Supervised) ---
    # Optimized: scale_pos_weight for imbalance, deeper trees for complex patterns
    xgb = XGBClassifier(n_estimators=200, max_depth=6, learning_rate=0.05, scale_pos_weight=5, eval_metric='logloss')
    xgb.fit(X, y)
    
    # --- Model 2: Isolation Forest (Unsupervised Anomaly) ---
    iso = IsolationForest(contamination=0.05, random_state=42)
    iso.fit(X)
    
    _MODELS['xgb'] = xgb
    _MODELS['iso'] = iso
    _MODELS['le_segment'] = le_segment
    print("Training Complete.")

def analyze_transaction(sender, receiver, amount, hour, minute, segment, is_intl):
    """
    Hybrid Analysis: Hard Rules -> Blacklist -> AI
    """
    # Ensure models are trained
    if not _MODELS:
        train_models()
        
    # Input Sanitization (Fix for potential NoneType errors)
    if amount is None: amount = 0.0
    if hour is None: hour = 0; minute = 0
    if segment is None: segment = "Individual"

    result = {
        "status": "APPROVED",
        "risk_score": 0.0,
        "reason": "Normal",
        "reason_key": "rule_ai_safe"
    }
    
    # --- FETCH CONTEXT DATA (DB) ---
    user_stats = database.get_user_stats(sender)
    seg_rules = database.get_segment_rules(segment)
    
    # --- LAYER 1: HARD RULES (Global Cap) ---
    global_cap = database.get_global_cap()
    
    if amount > global_cap:
        return {
            "status": "REJECT",
            "risk_score": 1.0,
            "reason": f"HARD RULE: Global Cap Exceeded (>{global_cap:,.0f})",
            "reason_key": "rule_hard"
        }
        
    # --- LAYER 2: BLACKLIST ---
    blacklist = database.get_list('BLACKLIST')
    if sender in blacklist or receiver in blacklist:
        return {
            "status": "REJECT",
            "risk_score": 1.0,
            "reason": "BLACKLIST: Sender or Receiver ID Match",
            "reason_key": "rule_black"
        }
        
    # --- LAYER 2.5: WATCHLIST ---
    watchlist = database.get_list('WATCHLIST')
    if sender in watchlist or receiver in watchlist:
        return {
            "status": "MONITOR",
            "risk_score": 0.8,
            "reason": "WATCHLIST: Entity on Watchlist",
            "reason_key": "rule_watch"
        }
    
    # --- LAYER 3: SEGMENT & FREQUENCY RULES (Non-ML) ---
    if seg_rules:
        # Amount Limits
        if amount < seg_rules['min_amount'] or amount > seg_rules['max_amount']:
             return {
                "status": "REJECT",
                "risk_score": 0.9,
                "reason": f"RULE: Amount {amount} outside segment limits ({seg_rules['min_amount']}-{seg_rules['max_amount']})",
                "reason_key": "rule_seg_limit"
            }
        
        # Frequency Limits
        if user_stats['daily_count'] >= seg_rules['daily_limit']:
             return {
                "status": "MONITOR",
                "risk_score": 0.7,
                "reason": f"RULE: Daily transaction limit ({seg_rules['daily_limit']}) reached",
                "reason_key": "rule_freq"
            }
        
        # Night Time Rule (00:00 - 06:00) & Near Limit (within 20% of max)
        # Dynamic Config
        night_start = database.get_config('night_start', 0)
        night_end = database.get_config('night_end', 6)
        night_ratio = database.get_config('night_ratio', 0.8)
        
        if (night_start <= hour < night_end) and (amount >= seg_rules['max_amount'] * night_ratio):
            return {
                "status": "MONITOR",
                "risk_score": 0.75,
                "reason": f"RULE: Night time transaction close to limit ({amount} / {seg_rules['max_amount']})",
                "reason_key": "rule_night_limit"
            }
            
    # --- LAYER 4: HISTORICAL PROFILING ---
    # Calculate deviation from historical average
    hist_avg = user_stats['avg_amount']
    deviation = 0.0
    if hist_avg > 0:
        deviation = (amount - hist_avg) / hist_avg
        
    hist_mult = database.get_config('hist_multiplier', 5.0)
    
    if hist_avg > 0 and amount > (hist_avg * hist_mult) and amount > 1000:
         return {
            "status": "MONITOR",
            "risk_score": 0.65,
            "reason": f"RULE: Abnormal spike ({deviation:.1%} increase) vs History",
            "reason_key": "rule_hist"
        }

    # --- LAYER 3: AI ANALYSIS ---
    # Preprocess Input
    try:
        # Handle dynamic segments (map unknown to 'Individual' or similar safe default)
        if segment in _MODELS['le_segment'].classes_:
            seg_code = _MODELS['le_segment'].transform([segment])[0]
        else:
            seg_code = 0 # Default to 0 if unknown
            
        # Feature Scaling
        log_amt = np.log1p(amount)
        daily_cnt = user_stats['daily_count']
        
        input_vector = pd.DataFrame([[log_amt, hour, minute, seg_code, int(is_intl), daily_cnt, deviation]], 
                                    columns=['log_amount', 'hour', 'minute', 'segment_code', 'is_international', 'daily_txn_count', 'hist_avg_diff'])
        
        # Predict
        fraud_prob = _MODELS['xgb'].predict_proba(input_vector)[0][1]
        anomaly = _MODELS['iso'].predict(input_vector)[0] # -1 is anomaly
        
        result['risk_score'] = float(fraud_prob)
        
        # Decision Logic
        if fraud_prob > 0.85:
            result['status'] = "REJECT"
            result['reason'] = f"AI: High Fraud Probability ({fraud_prob:.2%}) - Pattern Match"
            result['reason_key'] = "rule_ai_reject"
        elif fraud_prob > 0.50 or anomaly == -1:
            result['status'] = "MONITOR"
            result['reason'] = f"AI: Anomaly Detected (Score: {fraud_prob:.2%})"
            result['reason_key'] = "rule_ai_monitor"
        else:
            result['status'] = "APPROVED"
            result['reason'] = "AI: Normal Behavior"
            result['reason_key'] = "rule_ai_safe"
            
    except Exception as e:
        print(f"AI Error: {e}")
        result['status'] = "MONITOR"
        result['reason'] = "System Error: Defaulting to Monitor"
        
    return result
0