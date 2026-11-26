"""Ponto de entrada da API.

Rodar (na raiz do projeto):  uvicorn app.main:app --reload --app-dir src
Documentação (Swagger):      http://localhost:8000/docs
"""
import json
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from sqlalchemy.exc import OperationalError

from app import models  # noqa: F401  (registra as tabelas no Base)
from app.api.routes import atendimento, auth, gestor, health, totem
from app.core.erros import registrar_tratadores_de_erro
from app.database import Base, engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log_requisicoes = logging.getLogger("requisicoes")


@asynccontextmanager
async def ciclo_de_vida(_app: FastAPI):
    """Ao iniciar, cria as tabelas que ainda não existem.

    Não mexe nas que já existem. Serve para um banco criado com uma versão anterior
    do schema.sql (ex.: a tabela registros_acesso, que veio depois).
    """
    try:
        Base.metadata.create_all(engine)
    except OperationalError:
        logging.getLogger("controle_atendimento").warning("Banco indisponível ao iniciar a API.")
    yield


app = FastAPI(
    lifespan=ciclo_de_vida,
    title="Controle de Atendimento - Laboratório de Análises Clínicas",
    description="API de senhas e filas (SP, SG, SE). Projeto final de Back End Frameworks - UNINASSAU.",
    version="1.0.0",
)

registrar_tratadores_de_erro(app)


@app.middleware("http")
async def registrar_requisicao(request: Request, call_next):
    """Log estruturado (JSON) de cada requisição: rota, resposta e tempo.

    Não registra corpo, token nem dados pessoais (LGPD). Serve para acompanhar
    erros e lentidão (observabilidade).
    """
    inicio = time.perf_counter()
    resposta = await call_next(request)
    log_requisicoes.info(json.dumps({
        "metodo": request.method,
        "rota": request.url.path,
        "status": resposta.status_code,
        "duracao_ms": round((time.perf_counter() - inicio) * 1000, 1),
    }))
    return resposta

# /api/v1 = versão 1 da API. Se um dia mudar algo incompatível, cria-se /api/v2
# sem quebrar o front que já usa a v1.
API_V1 = "/api/v1"
app.include_router(totem.router, prefix=API_V1)
app.include_router(auth.router, prefix=API_V1)
app.include_router(atendimento.router, prefix=API_V1)
app.include_router(atendimento.expediente_router, prefix=API_V1)
app.include_router(gestor.relatorios, prefix=API_V1)
app.include_router(gestor.simulacao, prefix=API_V1)
app.include_router(gestor.usuarios, prefix=API_V1)
app.include_router(gestor.guiches, prefix=API_V1)
app.include_router(gestor.acessos, prefix=API_V1)
app.include_router(health.router)
