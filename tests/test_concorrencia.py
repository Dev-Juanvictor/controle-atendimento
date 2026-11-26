"""Teste de concorrência: vários atendentes chamando ao MESMO tempo.

Cada atendente roda numa thread separada, com sua própria conexão ao banco.
A "barreira" faz todos esperarem e dispararem o clique juntos.
"""
import threading
from collections import Counter

from sqlalchemy import select

from app.database import SessionLocal
from app.models import EstadoSenha, HistoricoEstado, Senha, TipoSenha
from app.services import atendimento_service, senha_service

ATENDENTES = [(2, 1), (3, 2), (4, 3), (1, 4)]  # (usuario_id, guiche_id)
RODADAS = 3


def _emitir(tipo: TipoSenha, quantidade: int):
    with SessionLocal() as db:
        for _ in range(quantidade):
            senha_service.emitir_senha(db, tipo)


def _rodar_atendentes_em_paralelo() -> list[str]:
    chamadas: list[str] = []
    erros: list[Exception] = []
    trava_lista = threading.Lock()
    barreira = threading.Barrier(len(ATENDENTES))

    def atendente(usuario_id: int, guiche_id: int):
        try:
            for _ in range(RODADAS):
                barreira.wait()  # todos clicam "chamar próxima" juntos
                with SessionLocal() as db:
                    senha = atendimento_service.chamar_proxima(db, usuario_id, guiche_id)
                    with trava_lista:
                        chamadas.append(senha.numero)
                    atendimento_service.iniciar_atendimento(db, usuario_id, guiche_id)
                    atendimento_service.encerrar_atendimento(db, usuario_id, guiche_id)
        except Exception as exc:  # noqa: BLE001
            erros.append(exc)
            barreira.abort()

    threads = [threading.Thread(target=atendente, args=a) for a in ATENDENTES]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not erros, erros
    return chamadas


def test_nenhuma_senha_vai_para_dois_guiches():
    _emitir(TipoSenha.SG, len(ATENDENTES) * RODADAS)

    chamadas = _rodar_atendentes_em_paralelo()

    repetidas = [n for n, qtd in Counter(chamadas).items() if qtd > 1]
    assert repetidas == [], f"Senhas entregues a mais de um guichê: {repetidas}"
    assert len(chamadas) == len(ATENDENTES) * RODADAS

    with SessionLocal() as db:
        # cada senha foi CHAMADA uma única vez no histórico
        eventos = db.scalars(
            select(HistoricoEstado.senha_id).where(HistoricoEstado.estado_novo == EstadoSenha.CHAMADA)
        ).all()
        assert len(eventos) == len(set(eventos))
        assert all(s.estado == EstadoSenha.ATENDIDA for s in db.scalars(select(Senha)))


def test_alternancia_se_mantem_com_chamadas_simultaneas():
    total = len(ATENDENTES) * RODADAS
    _emitir(TipoSenha.SP, total // 2)
    _emitir(TipoSenha.SE, total // 2)

    _rodar_atendentes_em_paralelo()

    with SessionLocal() as db:
        # ordem real das chamadas = ordem de gravação no histórico
        tipos = db.scalars(
            select(Senha.tipo)
            .join(HistoricoEstado, HistoricoEstado.senha_id == Senha.id)
            .where(HistoricoEstado.estado_novo == EstadoSenha.CHAMADA)
            .order_by(HistoricoEstado.id)
        ).all()
    esperado = [TipoSenha.SP, TipoSenha.SE] * (total // 2)
    assert tipos == esperado
