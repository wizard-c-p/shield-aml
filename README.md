# 🛡️ Shield AML - Fraud Detection System (v2.0)

Shield AML is a modern MVP application developed to detect fraud in financial transactions, combining **Hybrid AI (XGBoost + Isolation Forest)** and **Rule-Based** engines.

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![NiceGUI](https://img.shields.io/badge/UI-NiceGUI-orange)
![AI](https://img.shields.io/badge/AI-XGBoost%20%7C%20Isolation%20Forest-green)

## 🚀 Features (v2.0 Updates)

### 🧠 Hybrid Detection Engine
*   **XGBoost (Supervised):** Learns and catches known fraud patterns (high amount, segment violation, etc.).
*   **Isolation Forest (Unsupervised):** Detects previously unseen anomalies and deviations.
*   **Rule Engine:** Global limits, Blacklist, and segment-based rules.

### 🎨 Modern Interface & UX
*   **Dark Mode:** Dark theme to reduce operational fatigue.
*   **Multi-Language Support:** Fully Turkish and English (TR/EN) interface.
*   **Dynamic Configuration:** Update limits and rules via the interface without changing code.

### 🛠️ Operational Tools
*   **Maintenance Mode & Queue:** Queues transactions instead of rejecting them when the system is under maintenance.
*   **Simulation:** Real-time transaction simulation and instant risk analysis.
*   **Watchlists:** Watchlist and Blacklist management for suspicious entities.

## 📦 Installation

1.  Clone the repo:
    ```bash
    git clone https://github.com/wizard-c-p/shield-aml.git
    cd shield-aml
    ```

2.  Create and activate virtual environment:
    ```bash
    python -m venv venv
    source venv/bin/activate  # Windows: venv\Scripts\activate
    ```

3.  Install required packages:
    ```bash
    pip install -r requirements.txt
    ```
    *(If requirements.txt is missing: `pip install nicegui pandas numpy scikit-learn xgboost`)*

4.  Start the application:
    ```bash
    python main.py
    ```

## 🖥️ Usage

*   **Dashboard:** Monitor daily transaction volumes and risky transactions.
*   **Simulation:** Manually enter transaction data and see the AI engine's decision (Approve/Reject/Monitor).
*   **Settings:**
    *   Change language option (TR/EN).
    *   Update segment limits (Student, Corporate, etc.).
    *   Set night mode restrictions.

## 🏗️ Technology Stack

*   **Frontend/Backend:** Python (NiceGUI)
*   **Database:** SQLite
*   **ML Engine:** XGBoost, Isolation Forest, Scikit-Learn
*   **Data Processing:** Pandas, NumPy

## 🤝 Contribution

1.  Fork it
2.  Create your feature branch (`git checkout -b feature/new-feature`)
3.  Commit your changes (`git commit -m 'Add new feature'`)
4.  Push to the branch (`git push origin feature/new-feature`)
5.  Open a Pull Request

---
*Developer: Ghost*