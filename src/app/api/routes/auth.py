"""Rotas de login."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import Sessao, sessao_atual
from app.database import get_db
from app.schemas import LoginRequest, LoginResponse, UsuarioResponse
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Login"])


@router.post("/login", response_model=LoginResponse, summary="Login do atendente ou gestor")
def login(dados: LoginRequest, db: Session = Depends(get_db)):
    token, usuario = auth_service.autenticar(db, dados.login, dados.senha, dados.guiche_id)
    return LoginResponse(access_token=token, usuario=usuario, guiche_id=dados.guiche_id)


@router.get("/me", response_model=UsuarioResponse, summary="Quem está logado")
def eu(s: Sessao = Depends(sessao_atual)):
    return s.usuario
