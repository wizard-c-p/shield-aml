# 🛡️ ShieldAML Enterprise v1.0

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104-009688?style=for-the-badge&logo=fastapi)
![AI](https://img.shields.io/badge/AI-ScikitLearn-orange?style=for-the-badge&logo=scikit-learn)
![License](https://img.shields.io/badge/License-MIT-lightgrey?style=for-the-badge)

> **A Business Analyst's journey into the architecture of Financial Crime detection.**

---

## 📖 About The Project

Hi! I am a Business Analyst with 4+ years of experience in the Fintech domain. In my daily work, I define **"what"** needs to be done. The **"how"**—the complex architecture, the microservices, the database integrity—is the art of my brilliant developer colleagues.

I built **ShieldAML** not to replace developers, but to understand their world better. I wanted to feel the weight of architectural decisions, experience the challenges of asynchronous processing, and see how AI integrates into business logic.

**ShieldAML** is a fully functional, event-driven **Risk Engine** simulation designed to detect money laundering patterns in real-time.

*⚠️ **Disclaimer:** This project is a Proof of Concept (PoC) for educational purposes. While the architecture and workflows are my design, the coding process was accelerated using AI Assistants as "Pair Programmers".*

---

## 🚀 Key Features

### 1. 🧠 Hybrid Decision Engine
The system doesn't rely on just one method. It uses a **Hybrid Approach**:
* **Deterministic Rules:** Checks against Blacklists, Watchlists, and Dynamic Limits.
* **Probabilistic AI:** Uses **Isolation Forest** (Unsupervised Learning) to detect anomalies.

### 2. 👥 Segment-Based AI Models
A \$50,000 transaction might be fraud for an individual but normal for a corporation.
* **Dual-Engine:** The system trains separate AI models for `INDIVIDUAL` and `COMMERCIAL` segments to reduce false positives.

### 3. 🛡️ System Resilience & Maintenance Mode
What happens when the system goes down?
* **Graceful Degradation:** When `MAINTENANCE_MODE` is active, the API doesn't crash. It accepts transactions and saves them as `SAVED_FOR_LATER`.
* **Event Replay:** An admin can trigger a "Replay" to process all saved transactions once the system is healthy.

### 4. 🎛️ Operational Dashboard
A modern, Dark-Mode enabled UI for Compliance Teams:
* **Live Simulator:** Test transactions in real-time.
* **Dynamic Config:** Update limits and AI sensitivity without re-deploying code.
* **List Management:** Add/Edit/Delete Blacklist and Watchlist entries via UI.

---

## 🛠️ Tech Stack

* **Core:** Python 3.11+
* **API Framework:** FastAPI (Async/Await)
* **Database:** SQLite (SQLAlchemy ORM) - *Designed to be easily swappable with PostgreSQL*
* **ML Engine:** Scikit-Learn (Isolation Forest)
* **Frontend:** Jinja2 Templates + Bootstrap 5.3
* **Concurrency:** Python `threading` & `queue` (Simulating a Message Broker like RabbitMQ)

---

## 📦 Installation & Setup

You can run this project locally in minutes.

### 1. Clone the Repository
```bash
git clone (https://github.com/wizard-c-p/shield-aml.git)
cd shield-aml
