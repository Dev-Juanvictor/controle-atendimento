"""Health check: o front e o Docker usam para saber se a API e o banco estão no ar."""
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.database import engine

router = APIRouter(tags=["Saúde do sistema"])


@router.get("/health", summary="API e banco estão funcionando?")
def health():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "banco": "ok"}
    except Exception:
        return JSONResponse(status_code=503, content={"status": "degradado", "banco": "indisponivel"})
