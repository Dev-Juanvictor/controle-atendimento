"""Registro de acesso (LGPD): grava quem fez o quê e quando."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import relogio
from app.models import RegistroAcesso


def registrar(db: Session, usuario_id: int | None, evento: str, detalhe: str | None = None) -> None:
    """Grava um registro de acesso e confirma (commit) na hora.

    Confirma na hora de propósito: um login recusado também precisa ficar registrado,
    mesmo que a requisição termine em erro logo depois.
    """
    db.add(RegistroAcesso(usuario_id=usuario_id, evento=evento, detalhe=detalhe, ocorrido_em=relogio.agora()))
    db.commit()


def ultimos(db: Session, limite: int) -> list[RegistroAcesso]:
    return list(db.scalars(select(RegistroAcesso).order_by(RegistroAcesso.id.desc()).limit(limite)))
