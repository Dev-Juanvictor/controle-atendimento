"""Testes dos relatórios, da simulação, dos cadastros e do registro de acesso."""
import random
from datetime import date

from app.domain import simulacao
from app.models import TipoSenha

from conftest import emitir, login

GESTOR = {"usuario": "gestor", "senha": "gestor123", "guiche_id": None}


def _atender(client, cabecalho):
    for acao in ("chamar-proxima", "iniciar", "encerrar"):
        resp = client.post(f"/api/v1/atendimentos/{acao}", headers=cabecalho)
        assert resp.status_code == 200, resp.text


# ---------- Regras da simulação (funções puras) ----------

def test_tm_sorteado_fica_dentro_da_faixa_do_requisito():
    rng = random.Random(1)
    for _ in range(500):
        assert 10 <= simulacao.sortear_tm_minutos(TipoSenha.SP, rng) <= 20
        assert 2 <= simulacao.sortear_tm_minutos(TipoSenha.SG, rng) <= 8
        assert simulacao.sortear_tm_minutos(TipoSenha.SE, rng) in (1.0, 5.0)


def test_cerca_de_5_por_cento_dos_clientes_desistem():
    rng = random.Random(2)
    desistencias = sum(simulacao.cliente_desiste(rng) for _ in range(10_000))
    assert 400 <= desistencias <= 600  # ~5% de 10.000


# ---------- Relatórios ----------

def test_relatorio_diario_conta_emitidas_atendidas_e_auditoria(client):
    emitir(client, "SG", "SP", "SE")
    atendente = login(client)
    _atender(client, atendente)  # SP
    _atender(client, atendente)  # SE

    gestor = login(client, **GESTOR)
    resp = client.get("/api/v1/relatorios/diario", params={"data": "2026-11-27"}, headers=gestor)
    assert resp.status_code == 200, resp.text
    r = resp.json()

    assert r["emitidas"] == 3
    assert r["atendidas"] == 2
    por_tipo = {linha["tipo"]: linha for linha in r["por_tipo"]}
    assert por_tipo["SP"]["atendidas"] == 1 and por_tipo["SG"]["atendidas"] == 0
    # Detalhado: senha não atendida fica com atendimento e guichê em branco
    sg = next(s for s in r["senhas"] if s["tipo"] == "SG")
    assert sg["atendida_em"] is None and sg["guiche"] is None
    # Auditoria: só as 2 que foram chamadas, com atendente e guichê
    assert len(r["auditoria"]) == 2
    assert r["auditoria"][0]["atendente"] == "Atendente Um" and r["auditoria"][0]["guiche"] == 1
    assert r["indicadores"]["por_guiche"][0]["atendimentos"] == 2


def test_relatorio_e_so_para_o_gestor(client):
    atendente = login(client)
    assert client.get("/api/v1/relatorios/diario", headers=atendente).status_code == 403
    assert client.get("/api/v1/relatorios/diario").status_code == 401


def test_simulacao_de_um_dia_alimenta_o_relatorio_mensal(client):
    gestor = login(client, **GESTOR)
    resp = client.post("/api/v1/simulacao", json={"dia": "2026-11-20", "quantidade": 120, "semente": 7},
                       headers=gestor)
    assert resp.status_code == 201, resp.text
    sim = resp.json()
    assert sim["emitidas"] == 120
    assert sim["atendidas"] + sim["nao_compareceram"] + sim["descartadas_fim_expediente"] == 120

    r = client.get("/api/v1/relatorios/mensal", params={"ano": 2026, "mes": 11}, headers=gestor).json()
    assert r["emitidas"] == 120
    tm = {linha["tipo"]: linha["tm_minutos"] for linha in r["por_tipo"]}
    assert 10 <= tm["SP"] <= 20 and 2 <= tm["SG"] <= 8 and 1 <= tm["SE"] <= 5

    # Não deixa simular de novo o mesmo dia, nem hoje
    de_novo = client.post("/api/v1/simulacao", json={"dia": "2026-11-20"}, headers=gestor)
    assert de_novo.json()["erro"]["codigo"] == "DIA_JA_TEM_SENHAS"
    hoje = client.post("/api/v1/simulacao", json={"dia": "2026-11-27"}, headers=gestor)
    assert hoje.json()["erro"]["codigo"] == "DIA_INVALIDO"


def test_simulacao_respeita_a_alternancia_e_a_numeracao(client):
    from app.database import SessionLocal
    from app.services.simulacao_service import simular_dia

    with SessionLocal() as db:
        simular_dia(db, date(2026, 11, 19), 60, semente=3)
    r = client.get("/api/v1/relatorios/diario", params={"data": "2026-11-19"},
                   headers=login(client, **GESTOR)).json()
    numeros = [s["numero"] for s in r["senhas"]]
    assert len(numeros) == len(set(numeros))
    assert all(n.startswith("261119-") for n in numeros)


# ---------- Cadastros ----------

def test_gestor_cadastra_atendente_que_consegue_entrar(client):
    gestor = login(client, **GESTOR)
    novo = {"nome": "Maria Souza", "login": "maria", "senha": "maria123", "perfil": "ATENDENTE"}
    resp = client.post("/api/v1/usuarios", json=novo, headers=gestor)
    assert resp.status_code == 201, resp.text
    assert "senha" not in resp.json() and "senha_hash" not in resp.json()

    assert client.post("/api/v1/usuarios", json=novo, headers=gestor).json()["erro"]["codigo"] == "LOGIN_EM_USO"
    login(client, "maria", "maria123", 2)

    # Desativado, não entra mais
    client.patch(f"/api/v1/usuarios/{resp.json()['id']}", json={"ativo": False}, headers=gestor)
    recusado = client.post("/api/v1/auth/login", json={"login": "maria", "senha": "maria123", "guiche_id": 2})
    assert recusado.status_code == 401


def test_gestor_cadastra_guiche_e_atendente_nao(client):
    gestor = login(client, **GESTOR)
    resp = client.post("/api/v1/guiches", json={"numero": 6}, headers=gestor)
    assert resp.status_code == 201 and resp.json()["numero"] == 6
    assert len(client.get("/api/v1/guiches").json()) == 6  # lista pública, usada no login
    assert client.post("/api/v1/guiches", json={"numero": 7}, headers=login(client)).status_code == 403


def test_registro_de_acesso_guarda_logins_sem_a_senha(client):
    client.post("/api/v1/auth/login", json={"login": "atendente1", "senha": "errada", "guiche_id": 1})
    gestor = login(client, **GESTOR)
    registros = client.get("/api/v1/acessos", headers=gestor).json()
    eventos = [r["evento"] for r in registros]
    assert "LOGIN_RECUSADO" in eventos and "LOGIN" in eventos
    assert all("errada" not in (r["detalhe"] or "") for r in registros)
