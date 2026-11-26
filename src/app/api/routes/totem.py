"""Rotas públicas: totem (emissão) e painel. O cliente é anônimo, sem login."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import EmitirSenhaRequest, PainelResponse, SenhaEmitidaResponse
from app.services import painel_service, senha_service

router = APIRouter(tags=["Totem e painel (público)"])


@router.post("/senhas", response_model=SenhaEmitidaResponse, status_code=201,
             summary="Emitir senha (totem)")
def emitir_senha(dados: EmitirSenhaRequest, db: Session = Depends(get_db)):
    return senha_service.emitir_senha(db, dados.tipo)


@router.get("/painel", response_model=PainelResponse, summary="Últimas 5 senhas chamadas")
def painel(db: Session = Depends(get_db)):
    return PainelResponse(ultimas_chamadas=painel_service.ultimas_chamadas(db))
