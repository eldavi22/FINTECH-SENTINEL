from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from typing import Optional
import random
from datetime import datetime

# Configuración de Base de Datos SQLite
SQLALCHEMY_DATABASE_URL = "sqlite:///./fintech.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Modelo de Transacción
class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    txn_id = Column(String, unique=True, index=True)
    timestamp = Column(String)
    amount = Column(Float)
    risk_score = Column(Integer)
    risk_level = Column(String)
    status = Column(String)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="FINTECH SENTINEL API", version="2.0")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/")
def serve_dashboard():
    return FileResponse("app/static/index.html")

# ENDPOINT: Leer y buscar transacciones
@app.get("/api/transactions")
def get_transactions(q: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Transaction)
    if q:
        query = query.filter(Transaction.txn_id.contains(q.upper()))
    return query.order_by(Transaction.id.desc()).limit(15).all()

# ENDPOINT: Inyectar fraude simulado
@app.post("/api/transactions/simulate")
def simulate_transaction(db: Session = Depends(get_db)):
    riesgos = [
        ("CRITICAL", "Blocked", random.randint(85, 99)), 
        ("HIGH", "Under Review", random.randint(60, 84)), 
        ("LOW", "Approved", random.randint(10, 30))
    ]
    seleccion = random.choice(riesgos)
    
    nuevo_id = f"TXN-{random.randint(10000, 99999)}X"
    nueva_txn = Transaction(
        txn_id=nuevo_id,
        timestamp=datetime.now().strftime("%b %d, %H:%M:%S"),
        amount=round(random.uniform(500.0, 95000.0), 2),
        risk_score=seleccion[2],
        risk_level=seleccion[0],
        status=seleccion[1]
    )
    db.add(nueva_txn)
    db.commit()
    return {"msg": "Alerta generada", "txn_id": nuevo_id}

@app.get("/api/seed")
def seed_database(db: Session = Depends(get_db)):
    if db.query(Transaction).count() == 0:
        txns = [
            Transaction(txn_id="TXN-8F3A2K9L", timestamp="Sep 07, 10:24:31", amount=125430.00, risk_score=89, risk_level="CRITICAL", status="Blocked"),
            Transaction(txn_id="TXN-7D2B1M8P", timestamp="Sep 07, 10:21:18", amount=85200.00, risk_score=75, risk_level="HIGH", status="Under Review")
        ]
        db.bulk_save_objects(txns)
        db.commit()
        return {"msg": "Base de datos poblada."}
    return {"msg": "Base ya contiene datos."}