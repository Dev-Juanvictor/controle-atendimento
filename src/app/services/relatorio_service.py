"""Relatórios diário e mensal, auditoria e indicadores de desempenho.

Todos os números saem das colunas que a senha já guarda (os 5 horários, guichê e
atendente). Não existe tabela de relatório: ele é calculado na hora, a partir das senhas.
"""
import calendar
from collections import defaultdict
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import EstadoSenha, Senha, TipoSenha

E = EstadoSenha
TIPOS = [TipoSenha.SP, TipoSenha.SE, TipoSenha.SG]


def periodo_do_mes(ano: int, mes: int) -> tuple[date, date]:
    ultimo_dia = calendar.monthrange(ano, mes)[1]
    return date(ano, mes, 1), date(ano, mes, ultimo_dia)


def _minutos(inicio: datetime | None, fim: datetime | None) -> float | None:
    if inicio is None or fim is None:
        return None
    return (fim - inicio).total_seconds() / 60


def _media(valores: list[float]) -> float | None:
    return round(sum(valores) / len(valores), 1) if valores else None


def _percentual(parte: int, total: int) -> float:
    return round(100 * parte / total, 1) if total else 0.0


def gerar(db: Session, inicio: date, fim: date) -> dict:
    senhas = list(db.scalars(
        select(Senha)
        .options(joinedload(Senha.guiche), joinedload(Senha.atendente))
        .where(Senha.data_emissao >= inicio, Senha.data_emissao <= fim)
        .order_by(Senha.emitida_em, Senha.id)
    ))

    atendidas = [s for s in senhas if s.estado == E.ATENDIDA]
    nao_compareceu = [s for s in senhas if s.motivo_encerramento == "NAO_COMPARECEU_APOS_2_CHAMADAS"]
    descartadas = [s for s in senhas if s.motivo_encerramento == "DESCARTADA_FIM_EXPEDIENTE"]

    # ---------- Quantitativo e TM por tipo ----------
    por_tipo = []
    for tipo in TIPOS:
        do_tipo = [s for s in senhas if s.tipo == tipo]
        atendidas_tipo = [s for s in atendidas if s.tipo == tipo]
        por_tipo.append({
            "tipo": tipo,
            "emitidas": len(do_tipo),
            "atendidas": len(atendidas_tipo),
            "tm_minutos": _media([_minutos(s.inicio_atendimento_em, s.fim_atendimento_em) for s in atendidas_tipo]),
        })

    # ---------- Indicadores de desempenho ----------
    esperas = [_minutos(s.emitida_em, s.primeira_chamada_em) for s in senhas if s.primeira_chamada_em]
    duracoes = [_minutos(s.inicio_atendimento_em, s.fim_atendimento_em) for s in atendidas]

    por_guiche: dict[int, list[float]] = defaultdict(list)
    por_atendente: dict[str, list[float]] = defaultdict(list)
    for s in atendidas:
        duracao = _minutos(s.inicio_atendimento_em, s.fim_atendimento_em)
        if s.guiche:
            por_guiche[s.guiche.numero].append(duracao)
        if s.atendente:
            por_atendente[s.atendente.nome].append(duracao)

    indicadores = {
        "tempo_medio_espera_minutos": _media(esperas),
        "tempo_medio_atendimento_minutos": _media(duracoes),
        "taxa_atendimento_percentual": _percentual(len(atendidas), len(senhas)),
        "taxa_nao_comparecimento_percentual": _percentual(len(nao_compareceu), len(senhas)),
        "por_guiche": [
            {"nome": f"Guichê {numero}", "atendimentos": len(lista), "tm_minutos": _media(lista)}
            for numero, lista in sorted(por_guiche.items())
        ],
        "por_atendente": [
            {"nome": nome, "atendimentos": len(lista), "tm_minutos": _media(lista)}
            for nome, lista in sorted(por_atendente.items())
        ],
    }

    # ---------- Relatório detalhado (uma linha por senha) ----------
    # Se não foi atendida, data/hora do atendimento e guichê ficam em branco (requisito).
    detalhado = [
        {
            "numero": s.numero,
            "tipo": s.tipo,
            "emitida_em": s.emitida_em,
            "atendida_em": s.inicio_atendimento_em if s.estado == E.ATENDIDA else None,
            "guiche": s.guiche.numero if s.guiche and s.estado == E.ATENDIDA else None,
            "situacao": s.estado,
        }
        for s in senhas
    ]

    # ---------- Auditoria (só senhas que chegaram a ser chamadas) ----------
    auditoria = [
        {
            "numero": s.numero,
            "atendente": s.atendente.nome if s.atendente else None,
            "guiche": s.guiche.numero if s.guiche else None,
            "primeira_chamada": s.primeira_chamada_em,
            "segunda_chamada": s.segunda_chamada_em,
            "inicio_atendimento": s.inicio_atendimento_em,
            "fim_atendimento": s.fim_atendimento_em,
        }
        for s in senhas if s.primeira_chamada_em
    ]

    return {
        "inicio": inicio,
        "fim": fim,
        "emitidas": len(senhas),
        "atendidas": len(atendidas),
        "nao_compareceram": len(nao_compareceu),
        "descartadas_fim_expediente": len(descartadas),
        "por_tipo": por_tipo,
        "indicadores": indicadores,
        "senhas": detalhado,
        "auditoria": auditoria,
    }
