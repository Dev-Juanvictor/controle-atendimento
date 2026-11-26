"""Ações do atendente: chamar próxima, chamar novamente, iniciar e encerrar atendimento.

CONCORRÊNCIA (o que explicar na apresentação)
----------------------------------------------
Problema: dois atendentes clicam em "chamar próxima" no mesmo instante.
Sem cuidado, os dois leriam a mesma senha como "a próxima" e ela iria para dois guichês.

Estratégia escolhida: lock pessimista em uma linha de controle (tabela controle_fila).
- Antes de escolher a senha, a transação faz um UPDATE na linha id=1 de controle_fila.
- O banco trava essa linha até o COMMIT. O segundo atendente fica esperando na fila do banco.
- Quando o primeiro termina (commit), a senha dele já está CHAMADA; o segundo então
  escolhe a próxima, que é outra senha.

Por que não só "SELECT ... FOR UPDATE SKIP LOCKED" nas senhas?
Porque a ALTERNÂNCIA depende do "tipo da última senha chamada", que é um dado global.
Com SKIP LOCKED, dois atendentes poderiam ler "última foi SP" ao mesmo tempo e os dois
chamarem SE/SG, quebrando a regra [SP] -> [SE|SG] -> [SP]. Travando a linha de controle,
cada chamada vê o resultado da anterior. O custo (chamadas em fila, uma por vez) é
irrelevante: cada chamada leva milissegundos e o laboratório tem poucos guichês.
"""
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core import relogio
from app.core.erros import ErroNegocio
from app.domain import regras_fila
from app.models import ControleFila, EstadoSenha, Senha
from app.services.senha_service import mudar_estado, verificar_expediente

E = EstadoSenha
ESTADOS_NO_GUICHE = (E.CHAMADA, E.CHAMADA_NOVAMENTE, E.EM_ATENDIMENTO)


def senha_atual_do_guiche(db: Session, guiche_id: int) -> Senha | None:
    """A senha que está "ocupando" o guichê (chamada ou em atendimento), se houver."""
    return db.scalar(
        select(Senha).where(Senha.guiche_id == guiche_id, Senha.estado.in_(ESTADOS_NO_GUICHE))
    )


def _travar_controle(db: Session, momento) -> ControleFila:
    # Este UPDATE é a trava (equivale a um SELECT ... FOR UPDATE na linha id=1).
    resultado = db.execute(update(ControleFila).where(ControleFila.id == 1).values(atualizado_em=momento))
    if resultado.rowcount == 0:
        raise ErroNegocio("CONTROLE_AUSENTE", "Banco sem a linha de controle da fila. Rode o seed.", 500)
    return db.get(ControleFila, 1)


def chamar_proxima(db: Session, usuario_id: int, guiche_id: int) -> Senha:
    momento = relogio.agora()
    verificar_expediente(momento)
    hoje = momento.date()

    controle = _travar_controle(db, momento)

    # O que o guichê está fazendo agora?
    atual = senha_atual_do_guiche(db, guiche_id)
    if atual is not None:
        if atual.estado == E.EM_ATENDIMENTO:
            raise ErroNegocio(
                "ATENDIMENTO_EM_ANDAMENTO",
                f"Encerre o atendimento da senha {atual.numero} antes de chamar outra.",
            )
        if atual.estado == E.CHAMADA:
            raise ErroNegocio(
                "CHAME_NOVAMENTE",
                f"A senha {atual.numero} foi chamada só uma vez. Use 'chamar novamente' ou inicie o atendimento.",
            )
        # CHAMADA_NOVAMENTE: já foram 2 chamadas e o cliente não veio -> não compareceu
        mudar_estado(db, atual, E.NAO_COMPARECEU, momento, usuario_id, guiche_id)
        atual.motivo_encerramento = "NAO_COMPARECEU_APOS_2_CHAMADAS"

    # Na virada do dia, a alternância recomeça (começa por SP)
    ultimo_tipo = controle.ultimo_tipo_chamado if controle.data_referencia == hoje else None

    proxima = None
    for tipo in regras_fila.ordem_de_busca(ultimo_tipo, get_settings().MODO_ALTERNANCIA):
        proxima = db.scalar(
            select(Senha)
            .where(Senha.data_emissao == hoje, Senha.estado == E.AGUARDANDO, Senha.tipo == tipo)
            .order_by(Senha.sequencial)
            .limit(1)
        )
        if proxima is not None:
            break

    if proxima is None:
        db.commit()  # grava o NAO_COMPARECEU, se houve
        raise ErroNegocio("FILA_VAZIA", "Nenhuma senha aguardando atendimento.", 404)

    mudar_estado(db, proxima, E.CHAMADA, momento, usuario_id, guiche_id)
    proxima.guiche_id = guiche_id
    proxima.atendente_id = usuario_id
    proxima.primeira_chamada_em = momento

    controle.ultimo_tipo_chamado = proxima.tipo
    controle.data_referencia = hoje

    db.commit()  # libera a trava
    return proxima


def _senha_do_guiche_ou_erro(db: Session, guiche_id: int) -> Senha:
    senha = senha_atual_do_guiche(db, guiche_id)
    if senha is None:
        raise ErroNegocio("GUICHE_LIVRE", "Não há senha chamada neste guichê.", 404)
    return senha


def chamar_novamente(db: Session, usuario_id: int, guiche_id: int) -> Senha:
    momento = relogio.agora()
    senha = _senha_do_guiche_ou_erro(db, guiche_id)
    mudar_estado(db, senha, E.CHAMADA_NOVAMENTE, momento, usuario_id, guiche_id)
    senha.segunda_chamada_em = momento
    db.commit()
    return senha


def iniciar_atendimento(db: Session, usuario_id: int, guiche_id: int) -> Senha:
    momento = relogio.agora()
    senha = _senha_do_guiche_ou_erro(db, guiche_id)
    mudar_estado(db, senha, E.EM_ATENDIMENTO, momento, usuario_id, guiche_id)
    senha.inicio_atendimento_em = momento
    senha.atendente_id = usuario_id
    db.commit()
    return senha


def encerrar_atendimento(db: Session, usuario_id: int, guiche_id: int) -> Senha:
    # Sem verificar expediente: atendimento em curso pode terminar depois das 17h
    momento = relogio.agora()
    senha = _senha_do_guiche_ou_erro(db, guiche_id)
    mudar_estado(db, senha, E.ATENDIDA, momento, usuario_id, guiche_id)
    senha.fim_atendimento_em = momento
    db.commit()
    return senha


def encerrar_expediente(db: Session, usuario_id: int) -> int:
    """Fim do dia: descarta as senhas que sobraram (aguardando ou chamadas sem atendimento).

    Senhas EM_ATENDIMENTO não são tocadas: o atendente ainda vai encerrá-las.
    Retorna quantas senhas foram descartadas.
    """
    momento = relogio.agora()
    _travar_controle(db, momento)  # ninguém chama senha enquanto descartamos
    sobras = db.scalars(
        select(Senha).where(Senha.estado.in_((E.AGUARDANDO, E.CHAMADA, E.CHAMADA_NOVAMENTE)))
    ).all()
    for senha in sobras:
        mudar_estado(db, senha, E.NAO_COMPARECEU, momento, usuario_id, senha.guiche_id)
        senha.motivo_encerramento = "DESCARTADA_FIM_EXPEDIENTE"
    db.commit()
    return len(sobras)
