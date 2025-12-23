import sqlite3
from datetime import datetime, timedelta

DB_NAME = "fraud_detection.db"

def get_connection():
    # check_same_thread=False is crucial for async frameworks like FastAPI/NiceGUI
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    c = conn.cursor()
    
    # Transactions Table
    c.execute('''CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME,
        sender TEXT,
        receiver TEXT,
        amount REAL,
        segment TEXT,
        risk_score REAL,
        status TEXT,
        reason TEXT
    )''')
    
    # Blacklist/Watchlist Table
    c.execute('''CREATE TABLE IF NOT EXISTS restricted_lists (
        entity_id TEXT PRIMARY KEY,
        list_type TEXT, -- 'BLACKLIST' or 'WATCHLIST'
        added_on DATETIME
    )''')

    # Check if 'reason' column exists (migration for existing db)
    c.execute("PRAGMA table_info(restricted_lists)")
    cols = [info[1] for info in c.fetchall()]
    if 'reason' not in cols:
        c.execute("ALTER TABLE restricted_lists ADD COLUMN reason TEXT")
    
    # Segment Rules Table (Default Limits)
    c.execute('''CREATE TABLE IF NOT EXISTS segment_rules (
        segment TEXT PRIMARY KEY,
        min_amount REAL,
        max_amount REAL,
        daily_limit INTEGER,
        monthly_limit INTEGER
    )''')
    
    # Seed default rules if empty
    c.execute("SELECT count(*) FROM segment_rules")
    if c.fetchone()[0] == 0:
        default_rules = [
            ('Individual', 10, 10000, 10, 100),
            ('Corporate', 100, 500000, 50, 1000),
            ('Student', 5, 2000, 15, 150)
        ]
        c.executemany("INSERT INTO segment_rules VALUES (?,?,?,?,?)", default_rules)

    # System Config Table (Global Cap etc.)
    c.execute('''CREATE TABLE IF NOT EXISTS system_config (
        key TEXT PRIMARY KEY,
        value TEXT
    )''')
    c.execute("INSERT OR IGNORE INTO system_config (key, value) VALUES ('global_cap', '10000000')")
    c.execute("INSERT OR IGNORE INTO system_config (key, value) VALUES ('night_start', '0')")
    c.execute("INSERT OR IGNORE INTO system_config (key, value) VALUES ('night_end', '6')")
    c.execute("INSERT OR IGNORE INTO system_config (key, value) VALUES ('night_ratio', '0.8')")
    c.execute("INSERT OR IGNORE INTO system_config (key, value) VALUES ('hist_multiplier', '5.0')")
        
    conn.commit()
    conn.close()

def add_transaction(data):
    conn = get_connection()
    c = conn.cursor()
    ts = data.get('timestamp', datetime.now())
    c.execute('''INSERT INTO transactions 
                 (timestamp, sender, receiver, amount, segment, risk_score, status, reason)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
              (ts, data['sender'], data['receiver'], data['amount'], 
               data['segment'], data['risk_score'], data['status'], data['reason']))
    conn.commit()
    conn.close()

def get_history(limit=50):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM transactions ORDER BY id DESC LIMIT ?", (limit,))
    rows = [dict(row) for row in c.fetchall()]
    conn.close()
    return rows

def get_user_stats(sender):
    """Calculates daily, monthly stats and historical average for a user."""
    conn = get_connection()
    c = conn.cursor()
    now = datetime.now()
    
    # Daily Count
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    c.execute("SELECT count(*) FROM transactions WHERE sender = ? AND timestamp >= ?", (sender, start_of_day))
    daily_count = c.fetchone()[0]
    
    # Monthly Count
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    c.execute("SELECT count(*) FROM transactions WHERE sender = ? AND timestamp >= ?", (sender, start_of_month))
    monthly_count = c.fetchone()[0]
    
    # Historical Average Amount
    c.execute("SELECT avg(amount) FROM transactions WHERE sender = ?", (sender,))
    res = c.fetchone()[0]
    avg_amount = res if res else 0.0
    
    conn.close()
    return {
        "daily_count": daily_count,
        "monthly_count": monthly_count,
        "avg_amount": avg_amount
    }

def manage_list(action, list_type, entity_id, reason=None):
    conn = get_connection()
    c = conn.cursor()
    if action == "add":
        try:
            c.execute("INSERT OR REPLACE INTO restricted_lists (entity_id, list_type, added_on, reason) VALUES (?, ?, ?, ?)",
                      (entity_id, list_type, datetime.now(), reason))
        except sqlite3.IntegrityError:
            pass # Already exists
    elif action == "remove":
        c.execute("DELETE FROM restricted_lists WHERE entity_id = ? AND list_type = ?", (entity_id, list_type))
    conn.commit()
    conn.close()

def get_list(list_type):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT entity_id FROM restricted_lists WHERE list_type = ?", (list_type,))
    items = [row[0] for row in c.fetchall()]
    conn.close()
    return items

def get_list_details(list_type):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT entity_id, reason, added_on FROM restricted_lists WHERE list_type = ?", (list_type,))
    rows = [dict(row) for row in c.fetchall()]
    conn.close()
    return rows

def get_segment_rules(segment):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM segment_rules WHERE segment = ?", (segment,))
    row = c.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def get_dashboard_stats():
    conn = get_connection()
    c = conn.cursor()
    now = datetime.now()
    
    stats = {}
    
    # Time ranges
    start_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    start_year = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Helper for sums
    def get_sum_count(query, params=()):
        c.execute(query, params)
        row = c.fetchone()
        return (row[0] if row[0] else 0.0, row[1] if row[1] else 0)

    # Totals
    stats['day_total_amt'], stats['day_total_cnt'] = get_sum_count("SELECT sum(amount), count(*) FROM transactions WHERE timestamp >= ? AND status = 'APPROVED'", (start_day,))
    stats['month_total_amt'], stats['month_total_cnt'] = get_sum_count("SELECT sum(amount), count(*) FROM transactions WHERE timestamp >= ? AND status = 'APPROVED'", (start_month,))
    stats['year_total_amt'], stats['year_total_cnt'] = get_sum_count("SELECT sum(amount), count(*) FROM transactions WHERE timestamp >= ? AND status = 'APPROVED'", (start_year,))
    
    # Status based
    stats['suspicious_amt'], stats['suspicious_cnt'] = get_sum_count("SELECT sum(amount), count(*) FROM transactions WHERE status = 'REJECT'")
    stats['monitor_amt'], stats['monitor_cnt'] = get_sum_count("SELECT sum(amount), count(*) FROM transactions WHERE status = 'MONITOR'")
    stats['queued_cnt'] = get_sum_count("SELECT sum(amount), count(*) FROM transactions WHERE status = 'QUEUED'")[1]

    conn.close()
    return stats

def get_queued_transactions():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM transactions WHERE status = 'QUEUED'")
    # Convert row to dict and parse timestamp string back to datetime object if needed
    # SQLite stores datetime as string usually
    rows = []
    for row in c.fetchall():
        r = dict(row)
        rows.append(r)
    conn.close()
    return rows

def update_transaction_status(txn_id, risk_score, status, reason):
    conn = get_connection()
    conn.execute("UPDATE transactions SET risk_score = ?, status = ?, reason = ? WHERE id = ?", (risk_score, status, reason, txn_id))
    conn.commit()
    conn.close()

def update_segment_rules(segment, min_amount, max_amount, daily_limit, monthly_limit):
    conn = get_connection()
    c = conn.cursor()
    # Upsert logic (Insert or Replace)
    c.execute('''INSERT OR REPLACE INTO segment_rules 
                 (segment, min_amount, max_amount, daily_limit, monthly_limit)
                 VALUES (?, ?, ?, ?, ?)''', 
              (segment, min_amount, max_amount, daily_limit, monthly_limit))
    conn.commit()
    conn.close()

def get_all_segments():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT segment FROM segment_rules")
    rows = [row[0] for row in c.fetchall()]
    conn.close()
    return rows

def add_segment(segment):
    # Add with default values
    update_segment_rules(segment, 0, 10000, 10, 100)

def delete_segment(segment):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM segment_rules WHERE segment = ?", (segment,))
    conn.commit()
    conn.close()

def get_global_cap():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT value FROM system_config WHERE key = 'global_cap'")
    row = c.fetchone()
    conn.close()
    return float(row[0]) if row else 10000000.0

def set_global_cap(value):
    conn = get_connection()
    conn.execute("INSERT OR REPLACE INTO system_config (key, value) VALUES ('global_cap', ?)", (str(value),))
    conn.commit()
    conn.close()

def get_config(key, default_val):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT value FROM system_config WHERE key = ?", (key,))
    row = c.fetchone()
    conn.close()
    return type(default_val)(row[0]) if row else default_val

def set_config(key, value):
    conn = get_connection()
    conn.execute("INSERT OR REPLACE INTO system_config (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()

def get_recent_transactions_by_status(status, limit=50):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM transactions WHERE status = ? ORDER BY id DESC LIMIT ?", (status, limit))
    rows = [dict(row) for row in c.fetchall()]
    conn.close()
    return rows