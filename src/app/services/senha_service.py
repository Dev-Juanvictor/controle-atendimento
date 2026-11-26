"""Emissão de senhas (totem) e mudança de estado com histórico."""
from datetime import date, datetime

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core import relogio
from app.core.erros import ErroNegocio
from app.domain import regras_fila
from app.models import EstadoSenha, HistoricoEstado, Senha, SequenciaDiaria, TipoSenha


def verificar_expediente(momento: datetime) -> None:
    s = get_settings()
    if s.IGNORAR_EXPEDIENTE:
        return
    if not regras_fila.dentro_do_expediente(momento, s.HORA_INICIO_EXPEDIENTE, s.HORA_FIM_EXPEDIENTE):
        raise ErroNegocio(
            "FORA_DO_EXPEDIENTE",
            f"Fora do expediente ({s.HORA_INICIO_EXPEDIENTE}h às {s.HORA_FIM_EXPEDIENTE}h).",
        )


def mudar_estado(
    db: Session,
    senha: Senha,
    novo: EstadoSenha,
    momento: datetime,
    usuario_id: int | None = None,
    guiche_id: int | None = None,
) -> None:
    """ÚNICO lugar do sistema que muda o estado de uma senha.

    Valida a transição (máquina de estados) e grava o histórico.
    """
    regras_fila.validar_transicao(senha.estado, novo)
    db.add(HistoricoEstado(
        senha_id=senha.id,
        estado_anterior=senha.estado,
        estado_novo=novo,
        usuario_id=usuario_id,
        guiche_id=guiche_id,
        ocorrido_em=momento,
    ))
    senha.estado = novo


def _proximo_sequencial(db: Session, dia: date, tipo: TipoSenha) -> int:
    """Pega o próximo número da sequência do dia, sem repetir mesmo com 2 totens ao mesmo tempo.

    O UPDATE "ultimo_numero = ultimo_numero + 1" é feito pelo próprio banco, e trava a
    linha até o commit: um segundo totem emitindo o mesmo tipo espera o primeiro terminar.
    """
    for _ in range(3):
        resultado = db.execute(
            update(SequenciaDiaria)
            .where(SequenciaDiaria.data == dia, SequenciaDiaria.tipo == tipo)
            .values(ultimo_numero=SequenciaDiaria.ultimo_numero + 1)
        )
        if resultado.rowcount == 1:
            return db.scalar(
                select(SequenciaDiaria.ultimo_numero)
                .where(SequenciaDiaria.data == dia, SequenciaDiaria.tipo == tipo)
            )
        # Primeira senha deste tipo no dia: cria a linha da sequência.
        try:
            with db.begin_nested():  # SAVEPOINT: se der conflito, desfaz só este pedaço
                db.add(SequenciaDiaria(data=dia, tipo=tipo, ultimo_numero=1))
            return 1
        except IntegrityError:
            continue  # outro totem criou a linha no mesmo instante; tenta o UPDATE de novo
    raise ErroNegocio("ERRO_SEQUENCIA", "Não foi possível gerar a senha. Tente novamente.", 503)


def emitir_senha(db: Session, tipo: TipoSenha) -> Senha:
    momento = relogio.agora()
    verificar_expediente(momento)

    hoje = momento.date()
    sequencial = _proximo_sequencial(db, hoje, tipo)

    senha = Senha(
        numero=regras_fila.formatar_numero(hoje, tipo, sequencial),
        tipo=tipo,
        sequencial=sequencial,
        data_emissao=hoje,
        estado=EstadoSenha.EMITIDA,
        emitida_em=momento,
    )
    db.add(senha)
    db.flush()  # gera o id da senha para usar no histórico

    db.add(HistoricoEstado(senha_id=senha.id, estado_anterior=None,
                           estado_novo=EstadoSenha.EMITIDA, ocorrido_em=momento))
    # Assim que é impressa, a senha entra na fila
    mudar_estado(db, senha, EstadoSenha.AGUARDANDO, momento)

    db.commit()
    return senha
