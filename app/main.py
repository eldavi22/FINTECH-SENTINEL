from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# 1. Configuración de Base de Datos SQLite
SQLALCHEMY_DATABASE_URL = "sqlite:///./fintech.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 2. Modelo de Transacción
class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    txn_id = Column(String, unique=True, index=True)
    timestamp = Column(String)
    amount = Column(Float)
    risk_score = Column(Integer)
    risk_level = Column(String)
    status = Column(String)

# Crea las tablas en la BD si no existen
Base.metadata.create_all(bind=engine)

# 3. Inicialización de FastAPI
app = FastAPI(title="FINTECH SENTINEL API", version="1.0")

# Dependencia para inyectar la BD en las rutas
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 4. Rutas Estáticas y Frontend
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/")
def serve_dashboard():
    return FileResponse("app/static/index.html")

# 5. Endpoints de la API REST
@app.get("/api/transactions")
def get_transactions(db: Session = Depends(get_db)):
    return db.query(Transaction).order_by(Transaction.id.desc()).limit(5).all()

@app.get("/api/seed")
def seed_database(db: Session = Depends(get_db)):
    """Ruta temporal para inyectar datos de prueba en SQLite"""
    if db.query(Transaction).count() == 0:
        txns = [
            Transaction(txn_id="TXN-8F3A2K9L", timestamp="Sep 07, 10:24:31", amount=125430.00, risk_score=89, risk_level="CRITICAL", status="Blocked"),
            Transaction(txn_id="TXN-7D2B1M8P", timestamp="Sep 07, 10:21:18", amount=85200.00, risk_score=75, risk_level="HIGH", status="Under Review"),
            Transaction(txn_id="TXN-9G3C4N7Q", timestamp="Sep 07, 10:18:45", amount=45980.00, risk_score=62, risk_level="HIGH", status="Approved"),
            Transaction(txn_id="TXN-1K9L8P2R", timestamp="Sep 07, 10:15:12", amount=12300.00, risk_score=45, risk_level="MEDIUM", status="Approved"),
            Transaction(txn_id="TXN-3M7N5Q1T", timestamp="Sep 07, 10:11:02", amount=8750.00, risk_score=28, risk_level="LOW", status="Approved")
        ]
        db.bulk_save_objects(txns)
        db.commit()
        return {"msg": "Base de datos poblada con éxito."}
    return {"msg": "La base de datos ya contiene registros."}