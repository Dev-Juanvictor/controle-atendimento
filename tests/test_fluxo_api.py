"""Testes de integração: chamam a API de verdade (com banco de teste)."""
from datetime import datetime

from sqlalchemy import select

from app.database import SessionLocal
from app.models import EstadoSenha, Senha
from conftest import emitir, login

API = "/api/v1"


def chamar_e_atender(client, headers) -> str:
    """Chama a próxima, inicia e encerra. Devolve o número da senha atendida."""
    resp = client.post(f"{API}/atendimentos/chamar-proxima", headers=headers)
    assert resp.status_code == 200, resp.text
    numero = resp.json()["numero"]
    assert client.post(f"{API}/atendimentos/iniciar", headers=headers).status_code == 200
    assert client.post(f"{API}/atendimentos/encerrar", headers=headers).status_code == 200
    return numero


def estado_no_banco(numero: str) -> EstadoSenha:
    with SessionLocal() as db:
        return db.scalar(select(Senha.estado).where(Senha.numero == numero))


# ---------- Emissão ----------

def test_emissao_numera_por_tipo(client):
    assert emitir(client, "SP", "SP", "SG", "SE") == [
        "261127-SP001", "261127-SP002", "261127-SG001", "261127-SE001",
    ]


def test_sequencia_reinicia_no_dia_seguinte(client, relogio_falso):
    emitir(client, "SP", "SP")
    relogio_falso.ir_para(datetime(2026, 11, 28, 9, 0))
    assert emitir(client, "SP") == ["261128-SP001"]


def test_senha_emitida_entra_aguardando(client):
    (numero,) = emitir(client, "SG")
    assert estado_no_banco(numero) == EstadoSenha.AGUARDANDO


def test_tipo_invalido_retorna_erro_padronizado(client):
    resp = client.post(f"{API}/senhas", json={"tipo": "XX"})
    assert resp.status_code == 422
    assert resp.json()["erro"]["codigo"] == "DADOS_INVALIDOS"


# ---------- Alternância ----------

def test_alternancia_sp_se_sg_com_filas_vazias(client):
    emitir(client, "SG", "SG", "SE", "SP", "SP")
    h = login(client)
    ordem = [chamar_e_atender(client, h) for _ in range(5)]
    assert ordem == [
        "261127-SP001",  # começo do dia: SP
        "261127-SE001",  # depois de SP: SE (tem prioridade sobre SG)
        "261127-SP002",  # volta para SP
        "261127-SG001",  # depois de SP: não há SE -> SG
        "261127-SG002",  # não há SP nem SE -> segue com SG
    ]


def test_fila_vazia(client):
    resp = client.post(f"{API}/atendimentos/chamar-proxima", headers=login(client))
    assert resp.status_code == 404
    assert resp.json() == {"erro": {"codigo": "FILA_VAZIA", "mensagem": "Nenhuma senha aguardando atendimento."}}


# ---------- Fluxo, painel e estados ----------

def test_fluxo_completo_e_painel(client):
    emitir(client, "SP")
    h = login(client, guiche_id=3)

    chamada = client.post(f"{API}/atendimentos/chamar-proxima", headers=h).json()
    assert chamada["estado"] == "CHAMADA"
    assert chamada["guiche"] == 3
    assert chamada["ultima_chamada"] is False

    painel = client.get(f"{API}/painel").json()["ultimas_chamadas"]
    assert painel[0]["numero"] == "261127-SP001" and painel[0]["guiche"] == 3

    de_novo = client.post(f"{API}/atendimentos/chamar-novamente", headers=h).json()
    assert de_novo["ultima_chamada"] is True  # front deve tocar "Última chamada"
    painel = client.get(f"{API}/painel").json()["ultimas_chamadas"]
    assert len(painel) == 1  # a mesma senha não aparece duas vezes
    assert painel[0]["ultima_chamada"] is True

    assert client.post(f"{API}/atendimentos/iniciar", headers=h).json()["estado"] == "EM_ATENDIMENTO"
    assert client.post(f"{API}/atendimentos/encerrar", headers=h).json()["estado"] == "ATENDIDA"


def test_painel_mostra_so_as_5_ultimas(client):
    emitir(client, *["SG"] * 7)
    h = login(client)
    for _ in range(7):
        chamar_e_atender(client, h)
    painel = client.get(f"{API}/painel").json()["ultimas_chamadas"]
    assert [p["numero"] for p in painel] == [f"261127-SG00{i}" for i in (7, 6, 5, 4, 3)]


def test_encerrar_sem_iniciar_e_transicao_invalida(client):
    emitir(client, "SG")
    h = login(client)
    client.post(f"{API}/atendimentos/chamar-proxima", headers=h)
    resp = client.post(f"{API}/atendimentos/encerrar", headers=h)
    assert resp.status_code == 409
    assert resp.json()["erro"]["codigo"] == "TRANSICAO_INVALIDA"


def test_duas_chamadas_sem_comparecimento(client):
    emitir(client, "SG", "SG")
    h = login(client)
    client.post(f"{API}/atendimentos/chamar-proxima", headers=h)  # SG001, 1ª chamada

    # Só chamou uma vez: ainda não pode desistir do cliente
    resp = client.post(f"{API}/atendimentos/chamar-proxima", headers=h)
    assert resp.json()["erro"]["codigo"] == "CHAME_NOVAMENTE"

    client.post(f"{API}/atendimentos/chamar-novamente", headers=h)  # 2ª chamada
    proxima = client.post(f"{API}/atendimentos/chamar-proxima", headers=h).json()

    assert proxima["numero"] == "261127-SG002"
    assert estado_no_banco("261127-SG001") == EstadoSenha.NAO_COMPARECEU


def test_nao_chama_outra_com_atendimento_em_andamento(client):
    emitir(client, "SG", "SG")
    h = login(client)
    client.post(f"{API}/atendimentos/chamar-proxima", headers=h)
    client.post(f"{API}/atendimentos/iniciar", headers=h)
    resp = client.post(f"{API}/atendimentos/chamar-proxima", headers=h)
    assert resp.json()["erro"]["codigo"] == "ATENDIMENTO_EM_ANDAMENTO"


# ---------- Expediente ----------

def test_fora_do_expediente_nao_emite_nem_chama(client, relogio_falso):
    h = login(client)
    relogio_falso.ir_para(datetime(2026, 11, 27, 17, 30))
    assert client.post(f"{API}/senhas", json={"tipo": "SG"}).json()["erro"]["codigo"] == "FORA_DO_EXPEDIENTE"
    assert client.post(f"{API}/atendimentos/chamar-proxima", headers=h).json()["erro"]["codigo"] == "FORA_DO_EXPEDIENTE"


def test_atendimento_em_curso_pode_terminar_depois_das_17h(client, relogio_falso):
    relogio_falso.ir_para(datetime(2026, 11, 27, 16, 55))
    emitir(client, "SP")
    h = login(client)
    client.post(f"{API}/atendimentos/chamar-proxima", headers=h)
    client.post(f"{API}/atendimentos/iniciar", headers=h)
    relogio_falso.ir_para(datetime(2026, 11, 27, 17, 10))
    assert client.post(f"{API}/atendimentos/encerrar", headers=h).status_code == 200


def test_gestor_encerra_expediente_e_descarta_sobras(client):
    emitir(client, "SP", "SG", "SG")
    h = login(client)
    client.post(f"{API}/atendimentos/chamar-proxima", headers=h)  # SP001
    client.post(f"{API}/atendimentos/iniciar", headers=h)

    resp = client.post(f"{API}/expediente/encerrar", headers=login(client, "gestor", "gestor123", None))
    assert resp.json() == {"senhas_descartadas": 2}
    assert estado_no_banco("261127-SG001") == EstadoSenha.NAO_COMPARECEU
    assert estado_no_banco("261127-SP001") == EstadoSenha.EM_ATENDIMENTO  # este continua


# ---------- Segurança ----------

def test_sem_login_nao_acessa(client):
    resp = client.post(f"{API}/atendimentos/chamar-proxima")
    assert resp.status_code == 401
    assert resp.json()["erro"]["codigo"] == "NAO_AUTENTICADO"


def test_senha_errada(client):
    resp = client.post(f"{API}/auth/login", json={"login": "atendente1", "senha": "errada"})
    assert resp.status_code == 401
    assert resp.json()["erro"]["codigo"] == "LOGIN_INVALIDO"


def test_atendente_nao_pode_acao_de_gestor(client):
    resp = client.post(f"{API}/expediente/encerrar", headers=login(client))
    assert resp.status_code == 403


def test_atender_exige_guiche_no_login(client):
    h = login(client, guiche_id=None)
    assert client.post(f"{API}/atendimentos/chamar-proxima", headers=h).status_code == 403


def test_health(client):
    assert client.get("/health").json() == {"status": "ok", "banco": "ok"}
