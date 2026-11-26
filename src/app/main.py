"""Ponto de entrada da API.

Rodar (na raiz do projeto):  uvicorn app.main:app --reload --app-dir src
Documentação (Swagger):      http://localhost:8000/docs
"""
import logging

from fastapi import FastAPI

from app.api.routes import atendimento, auth, health, totem
from app.core.erros import registrar_tratadores_de_erro

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(
    title="Controle de Atendimento - Laboratório de Análises Clínicas",
    description="API de senhas e filas (SP, SG, SE). Projeto final de Back End Frameworks - UNINASSAU.",
    version="1.0.0",
)

registrar_tratadores_de_erro(app)

# /api/v1 = versão 1 da API. Se um dia mudar algo incompatível, cria-se /api/v2
# sem quebrar o front que já usa a v1.
API_V1 = "/api/v1"
app.include_router(totem.router, prefix=API_V1)
app.include_router(auth.router, prefix=API_V1)
app.include_router(atendimento.router, prefix=API_V1)
app.include_router(atendimento.expediente_router, prefix=API_V1)
app.include_router(health.router)
