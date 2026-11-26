"""Tratamento de erros padronizado.

Toda resposta de erro da API tem o MESMO formato, para o front end tratar fácil:

    {"erro": {"codigo": "FILA_VAZIA", "mensagem": "Nenhuma senha aguardando atendimento."}}

O "codigo" é fixo (o front pode usar num if/switch); a "mensagem" é para exibir.
"""
import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError

logger = logging.getLogger("controle_atendimento")


class ErroNegocio(Exception):
    """Erro de regra de negócio (ex.: transição de estado inválida, fila vazia)."""

    def __init__(self, codigo: str, mensagem: str, status_code: int = 409):
        self.codigo = codigo
        self.mensagem = mensagem
        self.status_code = status_code
        super().__init__(mensagem)


def _resposta(status_code: int, codigo: str, mensagem: str, detalhes=None) -> JSONResponse:
    corpo = {"erro": {"codigo": codigo, "mensagem": mensagem}}
    if detalhes is not None:
        corpo["erro"]["detalhes"] = detalhes
    return JSONResponse(status_code=status_code, content=corpo)


def registrar_tratadores_de_erro(app: FastAPI) -> None:
    @app.exception_handler(ErroNegocio)
    async def _erro_negocio(request: Request, exc: ErroNegocio):
        return _resposta(exc.status_code, exc.codigo, exc.mensagem)

    @app.exception_handler(HTTPException)
    async def _erro_http(request: Request, exc: HTTPException):
        codigos = {401: "NAO_AUTENTICADO", 403: "SEM_PERMISSAO", 404: "NAO_ENCONTRADO"}
        return _resposta(exc.status_code, codigos.get(exc.status_code, "ERRO_HTTP"), str(exc.detail))

    @app.exception_handler(RequestValidationError)
    async def _erro_validacao(request: Request, exc: RequestValidationError):
        detalhes = [{"campo": ".".join(str(p) for p in e["loc"][1:]), "problema": e["msg"]} for e in exc.errors()]
        return _resposta(422, "DADOS_INVALIDOS", "Os dados enviados são inválidos.", detalhes)

    @app.exception_handler(OperationalError)
    async def _banco_fora(request: Request, exc: OperationalError):
        # Recuperação de desastres: se o MySQL cair, a API não "explode";
        # devolve 503 e o front sabe que deve mostrar "sistema temporariamente indisponível".
        logger.error("Banco de dados indisponível: %s", exc)
        return _resposta(
            503, "BANCO_INDISPONIVEL", "Sistema temporariamente indisponível. Tente novamente em instantes."
        )

    @app.exception_handler(Exception)
    async def _erro_inesperado(request: Request, exc: Exception):
        # Nunca devolvemos o stack trace para o cliente (segurança/OWASP); só registramos no log.
        logger.exception("Erro inesperado")
        return _resposta(500, "ERRO_INTERNO", "Ocorreu um erro inesperado.")
