"""Dependências das rotas: quem está logado, qual perfil, qual guichê."""
from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.seguranca import ler_token
from app.database import get_db
from app.models import Perfil, Usuario

bearer = HTTPBearer(auto_error=False)


@dataclass
class Sessao:
    usuario: Usuario
    guiche_id: int | None


def sessao_atual(
    credenciais: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> Sessao:
    if credenciais is None:
        raise HTTPException(401, "Faça login para continuar.")
    try:
        dados = ler_token(credenciais.credentials)
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Sessão inválida ou expirada. Faça login novamente.") from None

    usuario = db.get(Usuario, int(dados["sub"]))
    if usuario is None or not usuario.ativo:
        raise HTTPException(401, "Usuário inativo.")
    return Sessao(usuario=usuario, guiche_id=dados.get("guiche_id"))


def sessao_com_guiche(sessao: Sessao = Depends(sessao_atual)) -> Sessao:
    """Para as ações de atendimento: precisa ter feito login informando o guichê."""
    if sessao.guiche_id is None:
        raise HTTPException(403, "Faça login informando o guichê para atender.")
    return sessao


def somente_gestor(sessao: Sessao = Depends(sessao_atual)) -> Sessao:
    if sessao.usuario.perfil != Perfil.GESTOR:
        raise HTTPException(403, "Apenas o gestor pode fazer esta ação.")
    return sessao
