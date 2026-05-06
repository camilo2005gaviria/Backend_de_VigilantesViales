"""
database.py
Configuración de la conexión a MySQL usando SQLAlchemy.
Modifica las variables de DB_* para apuntar a tu instancia.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# ─────────────────────────────────────────────
# PARÁMETROS DE CONEXIÓN — ajusta aquí
# ─────────────────────────────────────────────
DB_HOST     = "localhost"
DB_PORT     = 3308          # Puerto mapeado en docker-compose.yaml
DB_USER     = "root"
DB_PASSWORD = "rootpassword"
DB_NAME     = "accidentes"

DATABASE_URL = (
    f"mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
)

# ─────────────────────────────────────────────
# MOTOR Y SESIÓN
# ─────────────────────────────────────────────
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,      # Valida conexiones antes de usarlas
    pool_recycle=3600,       # Recicla conexiones cada hora
    echo=False,              # Cambia a True para ver SQL en consola (debug)
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


# ─────────────────────────────────────────────
# BASE DECLARATIVA (compartida por todos los modelos)
# ─────────────────────────────────────────────
class Base(DeclarativeBase):
    pass


# ─────────────────────────────────────────────
# DEPENDENCIA FastAPI — inyecta la sesión DB
# ─────────────────────────────────────────────
def get_db():
    """
    Generador que abre una sesión por request y la cierra al terminar.
    Uso: db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
