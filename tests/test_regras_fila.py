"""Testes unitários das regras puras (sem banco, sem API)."""
from datetime import date, datetime

import pytest

from app.core.erros import ErroNegocio
from app.domain.regras_fila import dentro_do_expediente, formatar_numero, ordem_de_busca, validar_transicao
from app.models import EstadoSenha as E
from app.models import TipoSenha as T


def test_numeracao_no_formato_yymmdd_ppsq():
    assert formatar_numero(date(2026, 11, 27), T.SP, 1) == "261127-SP001"
    assert formatar_numero(date(2026, 1, 5), T.SE, 42) == "260105-SE042"


def test_numeracao_nao_passa_de_999():
    with pytest.raises(ErroNegocio):
        formatar_numero(date(2026, 11, 27), T.SG, 1000)


def test_alternancia_modo_diagrama():
    assert ordem_de_busca(None) == [T.SP, T.SE, T.SG]       # começo do dia: SP
    assert ordem_de_busca(T.SP) == [T.SE, T.SG, T.SP]       # depois de SP: SE ou SG
    assert ordem_de_busca(T.SE) == [T.SP, T.SE, T.SG]       # depois de SE: SP
    assert ordem_de_busca(T.SG) == [T.SP, T.SE, T.SG]       # depois de SG: SP


def test_alternancia_modo_ciclo():
    assert ordem_de_busca(T.SP, "CICLO") == [T.SE, T.SG, T.SP]
    assert ordem_de_busca(T.SE, "CICLO") == [T.SG, T.SP, T.SE]
    assert ordem_de_busca(T.SG, "CICLO") == [T.SP, T.SE, T.SG]


@pytest.mark.parametrize("atual,novo", [
    (E.EMITIDA, E.AGUARDANDO),
    (E.AGUARDANDO, E.CHAMADA),
    (E.CHAMADA, E.CHAMADA_NOVAMENTE),
    (E.CHAMADA, E.EM_ATENDIMENTO),
    (E.CHAMADA_NOVAMENTE, E.EM_ATENDIMENTO),
    (E.CHAMADA_NOVAMENTE, E.NAO_COMPARECEU),
    (E.EM_ATENDIMENTO, E.ATENDIDA),
])
def test_transicoes_permitidas(atual, novo):
    validar_transicao(atual, novo)  # não pode lançar erro


@pytest.mark.parametrize("atual,novo", [
    (E.AGUARDANDO, E.ATENDIDA),          # pular etapas
    (E.CHAMADA, E.ATENDIDA),
    (E.ATENDIDA, E.AGUARDANDO),          # voltar de estado final
    (E.NAO_COMPARECEU, E.CHAMADA),
    (E.CHAMADA_NOVAMENTE, E.CHAMADA_NOVAMENTE),  # 3ª chamada não existe
])
def test_transicoes_invalidas_sao_rejeitadas(atual, novo):
    with pytest.raises(ErroNegocio) as erro:
        validar_transicao(atual, novo)
    assert erro.value.codigo == "TRANSICAO_INVALIDA"


def test_expediente_das_7_as_17():
    dia = (2026, 11, 27)
    assert not dentro_do_expediente(datetime(*dia, 6, 59), 7, 17)
    assert dentro_do_expediente(datetime(*dia, 7, 0), 7, 17)
    assert dentro_do_expediente(datetime(*dia, 16, 59), 7, 17)
    assert not dentro_do_expediente(datetime(*dia, 17, 0), 7, 17)
