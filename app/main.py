import datetime
import html
import random
import uuid
from decimal import Decimal

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    DateTime,
    Numeric,
    Text,
    inspect,
    text,
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError


# ============================================================
# CONFIGURATION
# ============================================================

APP_NAME = "FINTECH SENTINEL API"
APP_VERSION = "1.0.0"

DATABASE_URL = "sqlite:///./fintech.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def utc_timestamp():
    """Return a SQLite-safe timestamp string compatible with legacy data."""
    return datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")


# ============================================================
# DATABASE MODELS
# ============================================================

class TransactionModel(Base):
    __tablename__ = "transactions"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    txn_id = Column(
        String(80),
        unique=True,
        nullable=False,
        index=True,
    )

    # Stored as text to remain compatible with legacy SQLite records
    # that use values such as "Sep 07, 10:11:02".
    timestamp = Column(
        String(40),
        nullable=False,
        default=utc_timestamp,
    )

    amount = Column(
        Numeric(18, 2),
        nullable=False,
        default=0,
    )

    transaction_type = Column(
        String(30),
        nullable=True,
    )

    customer_risk = Column(
        String(20),
        nullable=True,
    )

    country_risk = Column(
        String(20),
        nullable=True,
    )

    previous_alerts = Column(
        Integer,
        nullable=False,
        default=0,
    )

    description = Column(
        Text,
        nullable=True,
    )

    risk_score = Column(
        Integer,
        nullable=False,
        default=0,
    )

    risk_level = Column(
        String(20),
        nullable=False,
        default="LOW",
    )

    status = Column(
        String(30),
        nullable=False,
        default="Approved",
    )

    assessment = Column(
        Text,
        nullable=True,
    )

    recommendation = Column(
        Text,
        nullable=True,
    )

    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.datetime.utcnow,
    )


class RiskAssessmentModel(Base):
    __tablename__ = "risk_assessments"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    assessment_id = Column(
        String(80),
        unique=True,
        nullable=False,
        index=True,
    )

    txn_id = Column(
        String(80),
        nullable=False,
        index=True,
    )

    risk_score = Column(
        Integer,
        nullable=False,
    )

    risk_level = Column(
        String(20),
        nullable=False,
    )

    status = Column(
        String(30),
        nullable=False,
    )

    assessment = Column(
        Text,
        nullable=False,
    )

    risk_factors = Column(
        Text,
        nullable=False,
    )

    recommendation = Column(
        Text,
        nullable=False,
    )

    report = Column(
        Text,
        nullable=False,
    )

    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.datetime.utcnow,
    )


# ============================================================
# DATABASE INITIALIZATION / MIGRATION
# ============================================================

Base.metadata.create_all(bind=engine)


def migrate_transactions_table():
    """
    Mantiene la fintech.db existente y agrega las columnas
    nuevas que necesita FINTECH SENTINEL.
    """

    inspector = inspect(engine)

    if "transactions" not in inspector.get_table_names():
        return

    existing_columns = {
        column["name"]
        for column in inspector.get_columns("transactions")
    }

    migrations = {
        "transaction_type": "VARCHAR(30)",
        "customer_risk": "VARCHAR(20)",
        "country_risk": "VARCHAR(20)",
        "previous_alerts": "INTEGER DEFAULT 0",
        "description": "TEXT",
        "assessment": "TEXT",
        "recommendation": "TEXT",
        "created_at": "DATETIME",
    }

    with engine.begin() as connection:

        for column_name, column_definition in migrations.items():

            if column_name not in existing_columns:

                connection.execute(
                    text(
                        f"ALTER TABLE transactions "
                        f"ADD COLUMN {column_name} "
                        f"{column_definition}"
                    )
                )


migrate_transactions_table()


# ============================================================
# FASTAPI
# ============================================================

app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description=(
        "Financial Risk, Fraud & Intelligence "
        "Analysis Platform"
    ),
)


# ============================================================
# DATABASE DEPENDENCY
# ============================================================

def get_db():

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()


# ============================================================
# PYDANTIC SCHEMAS
# ============================================================

class TransactionResponse(BaseModel):

    model_config = ConfigDict(
        from_attributes=True
    )

    id: int
    txn_id: str
    timestamp: str
    amount: Decimal

    transaction_type: str | None = None
    customer_risk: str | None = None
    country_risk: str | None = None

    previous_alerts: int = 0
    description: str | None = None

    risk_score: int
    risk_level: str
    status: str

    assessment: str | None = None
    recommendation: str | None = None

    created_at: datetime.datetime | None = None


class RiskAnalysisRequest(BaseModel):

    txn_id: str = Field(
        ...,
        min_length=1,
        max_length=80,
    )

    amount: Decimal = Field(
        ...,
        ge=0,
    )

    transaction_type: str = Field(
        default="TRANSFER",
        max_length=30,
    )

    customer_risk: str = Field(
        default="LOW",
        max_length=20,
    )

    country_risk: str = Field(
        default="LOW",
        max_length=20,
    )

    previous_alerts: int = Field(
        default=0,
        ge=0,
    )

    description: str | None = None


class RiskAnalysisResponse(BaseModel):

    assessment_id: str
    txn_id: str
    risk_score: int
    risk_level: str
    status: str
    assessment: str
    risk_factors: list[str]
    recommendation: str
    report: str


# ============================================================
# API ROOT
# ============================================================

@app.get("/api")
def api_root():

    return {
        "application": APP_NAME,
        "version": APP_VERSION,
        "status": "operational",
        "database": "sqlite",
    }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/api/health")
def health_check(
    db: Session = Depends(get_db),
):

    try:

        db.execute(text("SELECT 1"))

        return {
            "status": "ok",
            "api": "operational",
            "database": "connected",
        }

    except Exception:

        raise HTTPException(
            status_code=503,
            detail="Database unavailable",
        )


# ============================================================
# RISK ENGINE
# ============================================================

def calculate_risk(
    amount: Decimal,
    transaction_type: str,
    customer_risk: str,
    country_risk: str,
    previous_alerts: int,
    description: str | None,
):

    score = 0
    factors = []

    # --------------------------------------------------------
    # AMOUNT
    # --------------------------------------------------------

    if amount >= Decimal("100000"):

        score += 30

        factors.append(
            "Transaction amount is exceptionally high."
        )

    elif amount >= Decimal("50000"):

        score += 22

        factors.append(
            "Transaction amount exceeds the high-value threshold."
        )

    elif amount >= Decimal("25000"):

        score += 14

        factors.append(
            "Transaction amount is above the standard monitoring threshold."
        )

    elif amount >= Decimal("10000"):

        score += 7


    # --------------------------------------------------------
    # CUSTOMER RISK
    # --------------------------------------------------------

    customer_risk = customer_risk.upper()

    customer_points = {
        "LOW": 0,
        "MEDIUM": 12,
        "HIGH": 22,
        "CRITICAL": 30,
    }

    score += customer_points.get(
        customer_risk,
        0,
    )

    if customer_risk in (
        "HIGH",
        "CRITICAL",
    ):

        factors.append(
            f"Customer risk classification: {customer_risk}."
        )


    # --------------------------------------------------------
    # COUNTRY RISK
    # --------------------------------------------------------

    country_risk = country_risk.upper()

    country_points = {
        "LOW": 0,
        "MEDIUM": 10,
        "HIGH": 20,
        "CRITICAL": 28,
    }

    score += country_points.get(
        country_risk,
        0,
    )

    if country_risk in (
        "HIGH",
        "CRITICAL",
    ):

        factors.append(
            f"Country risk classification: {country_risk}."
        )


    # --------------------------------------------------------
    # PREVIOUS ALERTS
    # --------------------------------------------------------

    if previous_alerts >= 5:

        score += 25

        factors.append(
            "Multiple previous alerts detected."
        )

    elif previous_alerts >= 3:

        score += 18

        factors.append(
            "Several previous alerts are associated with the operation."
        )

    elif previous_alerts >= 1:

        score += 8

        factors.append(
            "Previous alert history detected."
        )


    # --------------------------------------------------------
    # TRANSACTION TYPE
    # --------------------------------------------------------

    transaction_type = transaction_type.upper()

    if transaction_type == "WITHDRAWAL":

        score += 5

    elif transaction_type == "TRANSFER":

        score += 4

    elif transaction_type == "PAYMENT":

        score += 2


    # --------------------------------------------------------
    # DESCRIPTION
    # --------------------------------------------------------

    if description:

        description_lower = description.lower()

        suspicious_terms = [
            "fraud",
            "fraude",
            "anonymous",
            "anomalia",
            "anomaly",
            "urgent",
            "urgente",
            "suspicious",
            "sospechosa",
            "chargeback",
            "lavado",
            "money laundering",
        ]

        detected_terms = [
            term
            for term in suspicious_terms
            if term in description_lower
        ]

        if detected_terms:

            score += min(
                20,
                len(detected_terms) * 5,
            )

            factors.append(
                "Suspicious indicators detected in "
                "the transaction description."
            )


    # --------------------------------------------------------
    # NORMALIZE SCORE
    # --------------------------------------------------------

    score = min(
        100,
        max(
            0,
            score,
        ),
    )


    # --------------------------------------------------------
    # CLASSIFICATION
    # --------------------------------------------------------

    if score >= 80:

        level = "CRITICAL"
        status = "Blocked"

    elif score >= 61:

        level = "HIGH"
        status = "Under Review"

    elif score >= 41:

        level = "MEDIUM"
        status = "Under Review"

    else:

        level = "LOW"
        status = "Approved"


    # --------------------------------------------------------
    # DEFAULT FACTOR
    # --------------------------------------------------------

    if not factors:

        factors.append(
            "No significant risk indicators were detected."
        )


    # --------------------------------------------------------
    # ASSESSMENT / RECOMMENDATION
    # --------------------------------------------------------

    if level == "CRITICAL":

        assessment = (
            "The transaction presents a critical level "
            "of financial risk and requires immediate "
            "investigation."
        )

        recommendation = (
            "Block the transaction and initiate enhanced "
            "review according to the organization's fraud, "
            "AML and financial risk procedures."
        )

    elif level == "HIGH":

        assessment = (
            "The transaction presents a high level of risk "
            "and should not be treated as a routine operation."
        )

        recommendation = (
            "Place the transaction under enhanced review "
            "and validate the relevant customer, geographic "
            "and transactional risk factors."
        )

    elif level == "MEDIUM":

        assessment = (
            "The transaction presents a moderate level "
            "of risk and should remain under monitoring."
        )

        recommendation = (
            "Perform enhanced monitoring and verify the "
            "relevant risk indicators before final approval."
        )

    else:

        assessment = (
            "The transaction presents a low level of "
            "identified risk based on the available information."
        )

        recommendation = (
            "Approve under normal controls while maintaining "
            "standard transaction monitoring."
        )


    return (
        score,
        level,
        status,
        assessment,
        factors,
        recommendation,
    )


# ============================================================
# REPORT GENERATOR
# ============================================================

def generate_report(
    assessment_id: str,
    txn_id: str,
    amount: Decimal,
    transaction_type: str,
    customer_risk: str,
    country_risk: str,
    previous_alerts: int,
    score: int,
    level: str,
    status: str,
    assessment: str,
    factors: list[str],
    recommendation: str,
):

    generated_at = datetime.datetime.utcnow().strftime(
        "%Y-%m-%d %H:%M:%S UTC"
    )

    safe_txn_id = html.escape(txn_id)
    safe_type = html.escape(transaction_type)
    safe_customer = html.escape(customer_risk)
    safe_country = html.escape(country_risk)
    safe_assessment = html.escape(assessment)
    safe_recommendation = html.escape(recommendation)

    factors_html = "".join(
        f"<li>{html.escape(factor)}</li>"
        for factor in factors
    )

    report = f"""
    <div class="sentinel-report">

        <h1>FINTECH SENTINEL</h1>

        <h2>
            Financial Risk Intelligence Report
        </h2>

        <hr>

        <p>
            <strong>Assessment ID:</strong>
            {assessment_id}
        </p>

        <p>
            <strong>Transaction ID:</strong>
            {safe_txn_id}
        </p>

        <p>
            <strong>Generated:</strong>
            {generated_at}
        </p>

        <h3>Transaction Profile</h3>

        <ul>

            <li>
                <strong>Amount:</strong>
                ${amount:,.2f}
            </li>

            <li>
                <strong>Transaction Type:</strong>
                {safe_type}
            </li>

            <li>
                <strong>Customer Risk:</strong>
                {safe_customer}
            </li>

            <li>
                <strong>Country Risk:</strong>
                {safe_country}
            </li>

            <li>
                <strong>Previous Alerts:</strong>
                {previous_alerts}
            </li>

        </ul>

        <h3>Risk Assessment</h3>

        <p>
            <strong>Risk Score:</strong>
            {score}/100
        </p>

        <p>
            <strong>Risk Level:</strong>
            {level}
        </p>

        <p>
            <strong>Status:</strong>
            {status}
        </p>

        <p>
            {safe_assessment}
        </p>

        <h3>Risk Factors</h3>

        <ul>
            {factors_html}
        </ul>

        <h3>Recommendation</h3>

        <p>
            {safe_recommendation}
        </p>

        <hr>

        <p>
            <strong>FINTECH SENTINEL</strong><br>
            Enterprise Financial Risk & Intelligence Platform
        </p>

    </div>
    """

    return report


# ============================================================
# ANALYZE TRANSACTION
# ============================================================

@app.post(
    "/api/risk/analyze",
    response_model=RiskAnalysisResponse,
)
def analyze_transaction(
    data: RiskAnalysisRequest,
    db: Session = Depends(get_db),
):

    # --------------------------------------------------------
    # CHECK DUPLICATE
    # --------------------------------------------------------

    existing = (
        db.query(TransactionModel)
        .filter(
            TransactionModel.txn_id == data.txn_id
        )
        .first()
    )

    if existing:

        raise HTTPException(
            status_code=409,
            detail="Transaction ID already exists.",
        )


    # --------------------------------------------------------
    # CALCULATE
    # --------------------------------------------------------

    (
        score,
        level,
        status,
        assessment,
        factors,
        recommendation,
    ) = calculate_risk(

        amount=data.amount,

        transaction_type=data.transaction_type,

        customer_risk=data.customer_risk,

        country_risk=data.country_risk,

        previous_alerts=data.previous_alerts,

        description=data.description,
    )


    # --------------------------------------------------------
    # ASSESSMENT ID
    # --------------------------------------------------------

    assessment_id = (
        "RISK-"
        + uuid.uuid4().hex[:12].upper()
    )


    # --------------------------------------------------------
    # REPORT
    # --------------------------------------------------------

    report = generate_report(

        assessment_id=assessment_id,

        txn_id=data.txn_id,

        amount=data.amount,

        transaction_type=data.transaction_type,

        customer_risk=data.customer_risk,

        country_risk=data.country_risk,

        previous_alerts=data.previous_alerts,

        score=score,

        level=level,

        status=status,

        assessment=assessment,

        factors=factors,

        recommendation=recommendation,
    )


    # --------------------------------------------------------
    # TRANSACTION
    # --------------------------------------------------------

    transaction = TransactionModel(

        txn_id=data.txn_id,

        timestamp=utc_timestamp(),

        amount=data.amount,

        transaction_type=data.transaction_type.upper(),

        customer_risk=data.customer_risk.upper(),

        country_risk=data.country_risk.upper(),

        previous_alerts=data.previous_alerts,

        description=data.description,

        risk_score=score,

        risk_level=level,

        status=status,

        assessment=assessment,

        recommendation=recommendation,

        created_at=datetime.datetime.utcnow(),
    )


    # --------------------------------------------------------
    # RISK ASSESSMENT
    # --------------------------------------------------------

    risk_assessment = RiskAssessmentModel(

        assessment_id=assessment_id,

        txn_id=data.txn_id,

        risk_score=score,

        risk_level=level,

        status=status,

        assessment=assessment,

        risk_factors="|".join(factors),

        recommendation=recommendation,

        report=report,

        created_at=datetime.datetime.utcnow(),
    )


    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    try:

        db.add(transaction)

        db.add(risk_assessment)

        db.commit()

    except SQLAlchemyError:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Unable to save risk assessment.",
        )


    # --------------------------------------------------------
    # RESPONSE
    # --------------------------------------------------------

    return {
        "assessment_id": assessment_id,
        "txn_id": data.txn_id,
        "risk_score": score,
        "risk_level": level,
        "status": status,
        "assessment": assessment,
        "risk_factors": factors,
        "recommendation": recommendation,
        "report": report,
    }


# ============================================================
# GET TRANSACTIONS
# ============================================================

@app.get(
    "/api/transactions",
    response_model=list[TransactionResponse],
)
def get_transactions(
    q: str | None = Query(
        default=None,
        description="Search transaction ID",
    ),
    db: Session = Depends(get_db),
):

    query = db.query(
        TransactionModel
    )

    if q:

        query = query.filter(
            TransactionModel.txn_id.ilike(
                f"%{q}%"
            )
        )

    return (
        query
        .order_by(
            TransactionModel.id.desc()
        )
        .limit(500)
        .all()
    )


# ============================================================
# GET SINGLE TRANSACTION
# ============================================================

@app.get(
    "/api/transactions/{txn_id}",
    response_model=TransactionResponse,
)
def get_transaction(
    txn_id: str,
    db: Session = Depends(get_db),
):

    transaction = (
        db.query(TransactionModel)
        .filter(
            TransactionModel.txn_id == txn_id
        )
        .first()
    )

    if not transaction:

        raise HTTPException(
            status_code=404,
            detail="Transaction not found.",
        )

    return transaction


# ============================================================
# GET RISK ASSESSMENT
# ============================================================

@app.get(
    "/api/risk/assessments/{assessment_id}"
)
def get_risk_assessment(
    assessment_id: str,
    db: Session = Depends(get_db),
):

    assessment = (
        db.query(RiskAssessmentModel)
        .filter(
            RiskAssessmentModel.assessment_id
            == assessment_id
        )
        .first()
    )

    if not assessment:

        raise HTTPException(
            status_code=404,
            detail="Risk assessment not found.",
        )

    factors = []

    if assessment.risk_factors is not None:

        factors = [
            factor
            for factor
            in assessment.risk_factors.split("|")
            if factor
        ]

    return {

        "assessment_id":
            assessment.assessment_id,

        "txn_id":
            assessment.txn_id,

        "risk_score":
            assessment.risk_score,

        "risk_level":
            assessment.risk_level,

        "status":
            assessment.status,

        "assessment":
            assessment.assessment,

        "risk_factors":
            factors,

        "recommendation":
            assessment.recommendation,

        "report":
            assessment.report,

        "created_at":
            assessment.created_at,
    }


# ============================================================
# SIMULATE TRANSACTION
# ============================================================

@app.post(
    "/api/transactions/simulate",
    response_model=TransactionResponse,
)
def simulate_transaction(
    db: Session = Depends(get_db),
):

    txn_id = (
        "TXN-"
        + uuid.uuid4().hex[:10].upper()
    )

    amount = Decimal(
        str(
            round(
                random.uniform(
                    500,
                    95000,
                ),
                2,
            )
        )
    )

    score = random.randint(
        10,
        99,
    )

    if score >= 80:

        level = "CRITICAL"
        status = "Blocked"

    elif score >= 61:

        level = "HIGH"
        status = "Under Review"

    elif score >= 41:

        level = "MEDIUM"
        status = "Under Review"

    else:

        level = "LOW"
        status = "Approved"


    transaction = TransactionModel(

        txn_id=txn_id,

        timestamp=utc_timestamp(),

        amount=amount,

        transaction_type="TRANSFER",

        customer_risk="MEDIUM",

        country_risk="MEDIUM",

        previous_alerts=0,

        description="Simulated transaction",

        risk_score=score,

        risk_level=level,

        status=status,

        assessment=(
            "Simulated transaction generated "
            "for system testing."
        ),

        recommendation=(
            "Review simulated transaction."
        ),

        created_at=datetime.datetime.utcnow(),
    )


    try:

        db.add(transaction)

        db.commit()

        db.refresh(transaction)

        return transaction

    except SQLAlchemyError:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Unable to create simulated transaction.",
        )


# ============================================================
# SEED DATABASE
# ============================================================

@app.post("/api/seed")
def seed_database(
    db: Session = Depends(get_db),
):

    sample_data = [

        (
            "TXN-31314X",
            Decimal("57422.20"),
            77,
            "HIGH",
            "Under Review",
        ),

        (
            "TXN-86450X",
            Decimal("28017.94"),
            94,
            "CRITICAL",
            "Blocked",
        ),

        (
            "TXN-82615X",
            Decimal("85669.28"),
            24,
            "LOW",
            "Approved",
        ),

        (
            "TXN-83785X",
            Decimal("77606.73"),
            98,
            "CRITICAL",
            "Blocked",
        ),

        (
            "TXN-63269X",
            Decimal("86466.18"),
            71,
            "HIGH",
            "Under Review",
        ),
    ]


    inserted = 0


    try:

        for (
            txn_id,
            amount,
            score,
            level,
            status,
        ) in sample_data:

            exists = (
                db.query(TransactionModel)
                .filter(
                    TransactionModel.txn_id
                    == txn_id
                )
                .first()
            )

            if exists:
                continue


            transaction = TransactionModel(

                txn_id=txn_id,

                timestamp=utc_timestamp(),

                amount=amount,

                transaction_type="TRANSFER",

                customer_risk=(
                    "HIGH"
                    if level
                    in (
                        "HIGH",
                        "CRITICAL",
                    )
                    else "LOW"
                ),

                country_risk="MEDIUM",

                previous_alerts=0,

                description="Seed transaction",

                risk_score=score,

                risk_level=level,

                status=status,

                assessment=(
                    "Seed transaction "
                    "for system initialization."
                ),

                recommendation=(
                    "Review according to "
                    "standard controls."
                ),

                created_at=datetime.datetime.utcnow(),
            )

            db.add(transaction)

            inserted += 1


        db.commit()


        return {
            "message":
                "Database seeded successfully.",

            "inserted":
                inserted,
        }


    except SQLAlchemyError:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Unable to seed database.",
        )


# ============================================================
# STATIC FRONTEND
# ============================================================

app.mount(
    "/",
    StaticFiles(
        directory="app/static",
        html=True,
    ),
    name="static",
)