"""Conexão com o banco de dados (SQLAlchemy)."""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings

settings = get_settings()

if settings.DATABASE_URL.startswith("sqlite"):
    # SQLite é usado só nos testes automatizados.
    # timeout=30: se outra conexão estiver escrevendo, espera em vez de dar erro.
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False, "timeout": 30},
    )
else:
    # MySQL (uso normal).
    # pool_pre_ping: testa a conexão antes de usar; se o MySQL reiniciou, reconecta.
    # READ COMMITTED: cada consulta enxerga o que já foi confirmado por outros atendentes.
    engine = create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
        isolation_level="READ COMMITTED",
    )

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    """Dependência do FastAPI: abre uma sessão por requisição e fecha no final."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
