"""Login dos atendentes e do gestor."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.erros import ErroNegocio
from app.core.seguranca import criar_token, verificar_senha
from app.models import Guiche, Usuario


def autenticar(db: Session, login: str, senha: str, guiche_id: int | None) -> tuple[str, Usuario]:
    usuario = db.scalar(select(Usuario).where(Usuario.login == login))

    # Mesma mensagem para "usuário não existe" e "senha errada":
    # assim ninguém descobre quais logins existem testando (boa prática OWASP).
    if usuario is None or not usuario.ativo or not verificar_senha(senha, usuario.senha_hash):
        raise ErroNegocio("LOGIN_INVALIDO", "Login ou senha incorretos.", 401)

    if guiche_id is not None:
        guiche = db.get(Guiche, guiche_id)
        if guiche is None or not guiche.ativo:
            raise ErroNegocio("GUICHE_INVALIDO", "Guichê inexistente ou inativo.", 422)

    token = criar_token(usuario.id, usuario.perfil.value, guiche_id)
    return token, usuario
