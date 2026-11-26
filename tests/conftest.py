"""Configuração dos testes.

Os testes usam um SQLite temporário (não precisa de MySQL ligado para rodar),
e um relógio falso, para testar horários sem depender da hora real.
"""
import os
import tempfile
from datetime import datetime, timedelta

# As variáveis precisam existir ANTES de importar a aplicação
_pasta = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_pasta}/teste.db"
os.environ["JWT_SECRET"] = "chave-somente-para-os-testes-automatizados-0001"
os.environ["IGNORAR_EXPEDIENTE"] = "false"
os.environ["MODO_ALTERNANCIA"] = "DIAGRAMA"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core import relogio  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.seed import popular  # noqa: E402


class RelogioFalso:
    """Começa num horário fixo e avança 1 segundo a cada consulta."""

    def __init__(self, inicio: datetime):
        self.atual = inicio

    def __call__(self) -> datetime:
        self.atual += timedelta(seconds=1)
        return self.atual

    def ir_para(self, momento: datetime) -> None:
        self.atual = momento


@pytest.fixture(autouse=True)
def banco_limpo():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        popular(db)
    yield


@pytest.fixture(autouse=True)
def relogio_falso(monkeypatch):
    falso = RelogioFalso(datetime(2026, 11, 27, 10, 0, 0))  # dentro do expediente
    monkeypatch.setattr(relogio, "agora", falso)
    return falso


@pytest.fixture
def client():
    return TestClient(app)


def login(client, usuario="atendente1", senha="atendente123", guiche_id=1) -> dict:
    """Faz login e devolve o cabeçalho de autorização pronto para usar."""
    resp = client.post("/api/v1/auth/login", json={"login": usuario, "senha": senha, "guiche_id": guiche_id})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def emitir(client, *tipos: str) -> list[str]:
    numeros = []
    for tipo in tipos:
        resp = client.post("/api/v1/senhas", json={"tipo": tipo})
        assert resp.status_code == 201, resp.text
        numeros.append(resp.json()["numero"])
    return numeros
