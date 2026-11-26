"""Rotas do atendente (precisa de login com guichê)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import Sessao, sessao_com_guiche, somente_gestor
from app.database import get_db
from app.schemas import EncerrarExpedienteResponse, SenhaGuicheResponse
from app.services import acesso_service
from app.services import atendimento_service as servico

router = APIRouter(prefix="/atendimentos", tags=["Atendimento (atendente)"])


@router.get("/atual", response_model=SenhaGuicheResponse, summary="Senha que está no meu guichê")
def senha_atual(s: Sessao = Depends(sessao_com_guiche), db: Session = Depends(get_db)):
    senha = servico.senha_atual_do_guiche(db, s.guiche_id)
    if senha is None:
        raise HTTPException(404, "Não há senha chamada neste guichê.")
    return SenhaGuicheResponse.de(senha)


@router.post("/chamar-proxima", response_model=SenhaGuicheResponse, summary="Chamar a próxima senha")
def chamar_proxima(s: Sessao = Depends(sessao_com_guiche), db: Session = Depends(get_db)):
    return SenhaGuicheResponse.de(servico.chamar_proxima(db, s.usuario.id, s.guiche_id))


@router.post("/chamar-novamente", response_model=SenhaGuicheResponse,
             summary="Chamar novamente (última chamada)")
def chamar_novamente(s: Sessao = Depends(sessao_com_guiche), db: Session = Depends(get_db)):
    return SenhaGuicheResponse.de(servico.chamar_novamente(db, s.usuario.id, s.guiche_id))


@router.post("/iniciar", response_model=SenhaGuicheResponse, summary="Cliente chegou: iniciar atendimento")
def iniciar(s: Sessao = Depends(sessao_com_guiche), db: Session = Depends(get_db)):
    return SenhaGuicheResponse.de(servico.iniciar_atendimento(db, s.usuario.id, s.guiche_id))


@router.post("/encerrar", response_model=SenhaGuicheResponse, summary="Encerrar atendimento")
def encerrar(s: Sessao = Depends(sessao_com_guiche), db: Session = Depends(get_db)):
    return SenhaGuicheResponse.de(servico.encerrar_atendimento(db, s.usuario.id, s.guiche_id))


expediente_router = APIRouter(prefix="/expediente", tags=["Gestor"])


@expediente_router.post("/encerrar", response_model=EncerrarExpedienteResponse,
                        summary="Encerrar expediente e descartar senhas restantes")
def encerrar_expediente(s: Sessao = Depends(somente_gestor), db: Session = Depends(get_db)):
    descartadas = servico.encerrar_expediente(db, s.usuario.id)
    acesso_service.registrar(db, s.usuario.id, "ENCERRAR_EXPEDIENTE", f"{descartadas} senha(s) descartada(s)")
    return EncerrarExpedienteResponse(senhas_descartadas=descartadas)
