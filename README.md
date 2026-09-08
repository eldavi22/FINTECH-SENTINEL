FINTECH SENTINEL

Enterprise Risk & Financial Intelligence Platform

FINTECH SENTINEL is a full-stack FinTech risk analysis platform focused on transaction risk assessment, scoring, classification and explainable decision support.

It was developed as an independent project to explore how software, financial risk, fraud signals, controls and operational decision-making can be brought together in a single web application.

🌐 Live Demo: https://fintech-sentinel.onrender.com/

What it does

FINTECH SENTINEL analyzes a financial transaction and produces a structured risk assessment based on multiple signals, including:

Transaction amount

Customer risk level

Country risk level

Previous alerts

Transaction type

Suspicious terms or information contained in the transaction context

The result includes:

Risk Score

Risk Level

Transaction Status

Risk Factors

Assessment

Recommendation

Report

The dashboard also presents transaction metrics, risk trends, risk distribution, high-risk activity and risk events.

Architecture — high level

                    ┌──────────────────────────────┐
                    │          USER / ANALYST       │
                    └──────────────┬───────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────────┐
                    │       WEB DASHBOARD          │
                    │      HTML / CSS / JS         │
                    └──────────────┬───────────────┘
                                   │
                           HTTP / JSON API
                                   │
                                   ▼
                    ┌──────────────────────────────┐
                    │          FASTAPI             │
                    │       API / APPLICATION      │
                    └──────────────┬───────────────┘
                                   │
                 ┌─────────────────┼─────────────────┐
                 │                 │                 │
                 ▼                 ▼                 ▼
        ┌────────────────┐  ┌────────────────┐  ┌────────────────┐
        │ Risk Analysis  │  │ Transactions   │  │ Assessments    │
        │ Engine         │  │ Management     │  │ & Reports      │
        └───────┬────────┘  └───────┬────────┘  └───────┬────────┘
                │                   │                   │
                └───────────────────┼───────────────────┘
                                    │
                                    ▼
                         ┌────────────────────┐
                         │     SQLAlchemy     │
                         │   Persistence ORM   │
                         └─────────┬──────────┘
                                   │
                                   ▼
                         ┌────────────────────┐
                         │      SQLite DB     │
                         │   fintech.db       │
                         └────────────────────┘

Risk analysis flow

The main processing path can be summarized as:

Transaction submitted
        │
        ▼
Input validation
        │
        ▼
Risk signal extraction
        │
        ├── Amount
        ├── Customer risk
        ├── Country risk
        ├── Previous alerts
        ├── Transaction type
        └── Suspicious context
        │
        ▼
Risk score calculation
        │
        ▼
Risk classification
        │
        ├── CRITICAL  → Blocked
        ├── HIGH      → Under Review
        ├── MEDIUM    → Under Review
        └── LOW       → Approved
        │
        ▼
Persist transaction + assessment
        │
        ▼
Generate assessment / recommendation / report
        │
        ▼
Display result in dashboard

Core components

Frontend

A lightweight web dashboard provides:

KPI cards

Risk trend visualization

Risk distribution

Transaction risk monitoring

Risk events

Transaction risk assessment form

Assessment result panel

The frontend communicates with the backend through JSON APIs and renders the dashboard without requiring an external charting dependency.

Backend

Built with Python + FastAPI.

The backend provides the application API, risk analysis workflow, persistence and report generation.

Data layer

Built with SQLAlchemy + SQLite.

The local database stores transaction and risk assessment information. The SQLite file fintech.db is intentionally kept outside Git version control.

API surface

Current application endpoints include:

GET  /api
GET  /api/health
POST /api/risk/analyze
GET  /api/transactions
GET  /api/transactions/{txn_id}
GET  /api/risk/assessments/{assessment_id}
POST /api/transactions/simulate
POST /api/seed

The main endpoint is:

POST /api/risk/analyze

It receives transaction information, executes the risk analysis workflow and returns the resulting assessment.

Example decision model

The current risk engine combines several transaction signals into a single score.

The resulting classification follows this model:

Score

Risk Level

Status

80+

CRITICAL

Blocked

61–79

HIGH

Under Review

41–60

MEDIUM

Under Review

0–40

LOW

Approved

The objective is not simply to assign a number, but to provide an interpretable assessment with the factors that influenced the decision.

Technology stack

Backend

Python

FastAPI

SQLAlchemy

SQLite

Frontend

HTML5

CSS3

JavaScript

Canvas-based visualizations

Development & delivery

Git / GitHub

VS Code

Uvicorn

Render

Project structure

FINTECH SENTINEL/
│
├── app/
│   ├── main.py
│   │
│   └── static/
│       └── index.html
│
├── .venv/
├── .gitignore
├── requirements.txt
└── fintech.db        # local database, not versioned

Local execution

1. Create and activate the virtual environment

python -m venv .venv

Windows:

.venv\Scripts\activate

2. Install dependencies

pip install -r requirements.txt

3. Start the application

uvicorn app.main:app --reload

The application will then be available locally through the URL shown by Uvicorn.

Deployment

FINTECH SENTINEL is deployed as a public web application on Render.

Local development
       │
       ▼
   Git commit
       │
       ▼
     GitHub
       │
       ▼
     Render
       │
       ▼
  Public application
       │
       ▼
https://fintech-sentinel.onrender.com/

The same project can therefore be inspected from the repository and tested directly through the deployed application.

Design goals

FINTECH SENTINEL was built around a few practical ideas:

Explainability — A risk result should expose the factors behind the decision.

Operational usefulness — The result should support an analyst or decision-maker, not just display a score.

Traceability — Transactions and assessments are persisted so that the analysis can be revisited.

Separation of concerns — Frontend, API/application logic and persistence remain separated within the project structure.

Deployable product mindset — The project was taken beyond local development into version control and a public cloud deployment.

Project scope

FINTECH SENTINEL is an independent portfolio and product-development project. Its current implementation focuses on the Risk Analysis Core and demonstrates an end-to-end workflow from transaction input to risk assessment and public deployment.

It should not be interpreted as a complete banking, payments or regulatory platform. Real financial production environments would require additional controls such as hardened authentication and authorization, secure secrets management, observability, audit architecture, infrastructure controls, compliance processes, fraud models and extensive security testing.

Author

David Giacone

Full-Stack Developer with a background in security, risk management, controls and operational analysis.

This project reflects an approach of combining software engineering with domain knowledge in financial risk, cybersecurity, GRC and operational decision-making.

Live project

🚀 Try FINTECH SENTINEL:

https://fintech-sentinel.onrender.com/
