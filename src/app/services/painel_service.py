"""Dados do painel de chamadas."""
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core import relogio
from app.models import EstadoSenha, HistoricoEstado
from app.schemas import ChamadaPainel


def ultimas_chamadas(db: Session, limite: int = 5) -> list[ChamadaPainel]:
    """As 5 últimas senhas chamadas no dia (sem repetir a mesma senha).

    Se uma senha foi chamada de novo, ela aparece uma vez só, no topo, marcada como
    "ultima_chamada". Nunca mostra a PRÓXIMA senha: o requisito explica que uma senha
    nova pode ser emitida a qualquer momento e mudar a ordem; a próxima só é decidida no clique.
    """
    inicio_do_dia = relogio.agora().replace(hour=0, minute=0, second=0)
    eventos = db.scalars(
        select(HistoricoEstado)
        .options(joinedload(HistoricoEstado.senha), joinedload(HistoricoEstado.guiche))
        .where(
            HistoricoEstado.estado_novo.in_((EstadoSenha.CHAMADA, EstadoSenha.CHAMADA_NOVAMENTE)),
            HistoricoEstado.ocorrido_em >= inicio_do_dia,
        )
        .order_by(HistoricoEstado.ocorrido_em.desc(), HistoricoEstado.id.desc())
        .limit(limite * 2)  # cada senha tem no máximo 2 chamadas
    ).all()

    painel: list[ChamadaPainel] = []
    ja_listadas: set[int] = set()
    for e in eventos:
        if e.senha_id in ja_listadas:
            continue  # já está no painel pela chamada mais recente
        ja_listadas.add(e.senha_id)
        painel.append(ChamadaPainel(
            numero=e.senha.numero,
            tipo=e.senha.tipo,
            sequencial=e.senha.sequencial,
            guiche=e.guiche.numero,
            ultima_chamada=e.estado_novo == EstadoSenha.CHAMADA_NOVAMENTE,
            chamada_em=e.ocorrido_em,
        ))
        if len(painel) == limite:
            break
    return painel
