"""Cadastros feitos pelo gestor: atendentes (usuários) e guichês."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.erros import ErroNegocio
from app.core.seguranca import gerar_hash
from app.models import Guiche, Perfil, Usuario

# ---------- Usuários ----------


def listar_usuarios(db: Session) -> list[Usuario]:
    return list(db.scalars(select(Usuario).order_by(Usuario.nome)))


def criar_usuario(db: Session, nome: str, login: str, senha: str, perfil: Perfil) -> Usuario:
    if db.scalar(select(Usuario).where(Usuario.login == login)):
        raise ErroNegocio("LOGIN_EM_USO", f"Já existe um usuário com o login '{login}'.")
    usuario = Usuario(nome=nome, login=login, senha_hash=gerar_hash(senha), perfil=perfil, ativo=True)
    db.add(usuario)
    db.commit()
    return usuario


def alterar_usuario(db: Session, usuario_id: int, ativo: bool, quem_alterou: int) -> Usuario:
    usuario = db.get(Usuario, usuario_id)
    if usuario is None:
        raise ErroNegocio("NAO_ENCONTRADO", "Usuário não encontrado.", 404)
    if usuario.id == quem_alterou and not ativo:
        raise ErroNegocio("NAO_PERMITIDO", "Você não pode desativar o seu próprio usuário.")
    usuario.ativo = ativo
    db.commit()
    return usuario


# ---------- Guichês ----------


def listar_guiches(db: Session) -> list[Guiche]:
    return list(db.scalars(select(Guiche).order_by(Guiche.numero)))


def criar_guiche(db: Session, numero: int) -> Guiche:
    if db.scalar(select(Guiche).where(Guiche.numero == numero)):
        raise ErroNegocio("GUICHE_EXISTE", f"O guichê {numero} já existe.")
    guiche = Guiche(numero=numero, ativo=True)
    db.add(guiche)
    db.commit()
    return guiche


def alterar_guiche(db: Session, guiche_id: int, ativo: bool) -> Guiche:
    guiche = db.get(Guiche, guiche_id)
    if guiche is None:
        raise ErroNegocio("NAO_ENCONTRADO", "Guichê não encontrado.", 404)
    guiche.ativo = ativo
    db.commit()
    return guiche
