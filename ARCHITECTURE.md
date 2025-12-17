# 🏛️ ShieldAML System Architecture

## 1. Overview
ShieldAML is a distributed, event-driven risk engine designed to detect financial fraud in real-time. It adheres to Microservices principles (separation of concerns) and uses an Asynchronous Processing model to ensure high throughput.

## 2. High-Level Architecture Diagram
[Client (Web/Mobile)] --> [FastAPI Gateway] --> [Transactions DB (SQLite)]
                                 |
                          (Message Queue)
                                 |
                                 v
                        [Background Worker]
                        /       |        \
              [Rules Engine] [AI Model] [Lists DB]

## 3. Core Components

### A. API Layer (FastAPI)
- **Role:** Entry point for all requests.
- **Responsibilities:** Validation (Pydantic), Authentication stub, Pushing tasks to Queue.
- **Resilience:** Implements "Maintenance Mode" to accept transactions without processing them during downtimes.

### B. Service Layer (Business Logic)
- **Hybrid Decision Engine:**
    1.  **Deterministic:** Checks against Blacklist/Watchlist and dynamic Thresholds (Config).
    2.  **Probabilistic:** Uses `IsolationForest` (Scikit-Learn) for anomaly detection.
- **Dual AI Models:** Separate models for `INDIVIDUAL` and `COMMERCIAL` segments to reduce false positives.

### C. Data Persistence (SQLAlchemy)
- **Schema:** Relational model linking Users, Transactions, and Risk Lists.
- **Config Driven:** System parameters (Limits, AI Sensitivity) are stored in DB, allowing runtime updates without code redeployment.

## 4. Key Workflows

### Transaction Processing Flow
1.  **Ingest:** API receives `POST /transfer`.
2.  **Persist & Queue:** Transaction saved as `PENDING`, ID pushed to `task_queue`.
3.  **Process:** Worker picks ID, runs checks (Blacklist -> Rules -> AI).
4.  **Update:** Status updated to `APPROVED` / `REJECTED`.

### Resilience Flow (Maintenance Mode)
1.  **Ingest:** API receives `POST /transfer`.
2.  **Check:** System Config `MAINTENANCE_MODE` is `TRUE`.
3.  **Save:** Transaction saved as `SAVED_FOR_LATER`.
4.  **Replay:** Admin triggers `POST /replay`, system moves saved items to Queue.
