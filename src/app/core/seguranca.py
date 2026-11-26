"""Hash de senha (bcrypt) e token de login (JWT)."""
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.config import get_settings


def gerar_hash(senha: str) -> str:
    # bcrypt já gera um "sal" aleatório e é lento de propósito (dificulta ataque de força bruta)
    return bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verificar_senha(senha: str, senha_hash: str) -> bool:
    return bcrypt.checkpw(senha.encode("utf-8"), senha_hash.encode("utf-8"))


def criar_token(usuario_id: int, perfil: str, guiche_id: int | None) -> str:
    s = get_settings()
    expira = datetime.now(timezone.utc) + timedelta(minutes=s.JWT_EXPIRA_MINUTOS)
    dados = {"sub": str(usuario_id), "perfil": perfil, "guiche_id": guiche_id, "exp": expira}
    return jwt.encode(dados, s.JWT_SECRET, algorithm="HS256")


def ler_token(token: str) -> dict:
    """Lança jwt.InvalidTokenError se o token for inválido ou estiver vencido."""
    return jwt.decode(token, get_settings().JWT_SECRET, algorithms=["HS256"])
