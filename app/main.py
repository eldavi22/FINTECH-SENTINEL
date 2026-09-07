from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import datetime
import random

SQLALCHEMY_DATABASE_URL = "sqlite:///./fintech.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class TransactionModel(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    txn_id = Column(String, unique=True, index=True)
    timestamp = Column(String)
    amount = Column(Float)
    risk_score = Column(Integer)
    risk_level = Column(String)
    status = Column(String)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Fintech Sentinel API")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/api/transactions")
def get_transactions(q: str | None = None, db: Session = Depends(get_db)):
    query = db.query(TransactionModel)
    if q:
        query = query.filter(TransactionModel.txn_id.contains(q))
    return query.order_by(TransactionModel.id.desc()).all()

@app.post("/api/transactions/simulate")
def simulate_transaction(db: Session = Depends(get_db)):
    txn_id = f"TXN-{random.randint(1000, 9999)}X"
    amount = round(random.uniform(500, 95000), 2)
    score = random.randint(10, 99)
    level = "CRITICAL" if score > 80 else ("HIGH" if score > 60 else ("MEDIUM" if score > 40 else "LOW"))
    status = "Blocked" if level == "CRITICAL" else ("Under Review" if level == "HIGH" else "Approved")
    
    new_txn = TransactionModel(
        txn_id=txn_id,
        timestamp=datetime.datetime.now().strftime("%b %d, %H:%M:%S"),
        amount=amount,
        risk_score=score,
        risk_level=level,
        status=status
    )
    db.add(new_txn)
    db.commit()
    db.refresh(new_txn)
    return new_txn

@app.get("/api/seed")
def seed_database(db: Session = Depends(get_db)):
    sample_data = [
        ("TXN-31314X", "Sep 07, 20:47:19", 57422.20, 77, "HIGH", "Under Review"),
        ("TXN-86450X", "Sep 07, 20:47:48", 28017.94, 94, "CRITICAL", "Blocked"),
        ("TXN-82615X", "Sep 07, 20:43:42", 85669.28, 24, "LOW", "Approved"),
        ("TXN-83785X", "Sep 07, 20:43:48", 77606.73, 98, "CRITICAL", "Blocked"),
        ("TXN-63269X", "Sep 07, 20:44:18", 86466.18, 71, "HIGH", "Under Review"),
    ]
    for t in sample_data:
        exists = db.query(TransactionModel).filter_by(txn_id=t[0]).first()
        if not exists:
            db.add(TransactionModel(txn_id=t[0], timestamp=t[1], amount=t[2], risk_score=t[3], risk_level=t[4], status=t[5]))
    db.commit()
    return {"message": "Database seeded successfully!"}

app.mount("/", StaticFiles(directory="app/static", html=True), name="static")