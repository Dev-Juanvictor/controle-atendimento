"""Configurações da aplicação, lidas das variáveis de ambiente / arquivo .env.

Por que assim? O edital exige "segredos fora do código". Nada de senha de banco
ou chave de token escrita no .py: tudo vem do .env (que não vai para o GitHub).
"""
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

# .env na raiz do projeto (duas pastas acima deste arquivo), não importa de onde se roda o comando
ARQUIVO_ENV = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ARQUIVO_ENV, env_file_encoding="utf-8", extra="ignore")

    DATABASE_URL: str
    JWT_SECRET: str  # obrigatório: sem ele a aplicação nem sobe
    JWT_EXPIRA_MINUTOS: int = 480

    FUSO_HORARIO: str = "America/Recife"
    HORA_INICIO_EXPEDIENTE: int = 7
    HORA_FIM_EXPEDIENTE: int = 17
    IGNORAR_EXPEDIENTE: bool = False

    MODO_ALTERNANCIA: Literal["DIAGRAMA", "CICLO"] = "DIAGRAMA"


@lru_cache
def get_settings() -> Settings:
    return Settings()
