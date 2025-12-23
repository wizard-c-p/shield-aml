import random

# --- Mock User Database ---
# Simulates a database of users with their segment and historical average transaction amount.
MOCK_USERS = {
    "101": {"segment": "Retail", "avg_amount": 100.0},
    "102": {"segment": "Corporate", "avg_amount": 5000.0},
    "103": {"segment": "Retail", "avg_amount": 250.0},
    "104": {"segment": "High Net Worth", "avg_amount": 15000.0},
    "105": {"segment": "Corporate", "avg_amount": 8000.0},
    "106": {"segment": "Retail", "avg_amount": 80.0},
}

def get_random_user():
    """Selects a random user from the mock database."""
    user_id = random.choice(list(MOCK_USERS.keys()))
    return user_id, MOCK_USERS[user_id]

def generate_mock_transaction(user_profile):
    """
    Generates a transaction amount based on the user's history.
    Intentionally injects anomalies to test the dashboard rules.
    """
    avg = user_profile["avg_amount"]
    
    # Determine the scenario for this transaction
    # 70% Normal, 20% Suspicious Spike, 10% Severe Anomaly
    scenario = random.choices(
        ["normal", "spike_mild", "spike_severe"], 
        weights=[0.7, 0.2, 0.1]
    )[0]
    
    if scenario == "normal":
        # Amount varies by +/- 10%
        amount = avg * random.uniform(0.9, 1.1)
    elif scenario == "spike_mild":
        # Amount is 20% to 45% higher (Should trigger Monitoring)
        amount = avg * random.uniform(1.2, 1.45)
    else: # spike_severe
        # Amount is 55% to 100% higher (Should trigger Rejection)
        amount = avg * random.uniform(1.55, 2.0)
        
    return round(amount, 2)
