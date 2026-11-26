"""Relógio da aplicação.

Por que não usar datetime.now() direto no código? Porque:
1. O servidor pode estar em outro fuso; aqui sempre usamos o horário do laboratório.
2. Nos testes conseguimos "fingir" que são 18h para testar o fim do expediente
   (substituindo esta função), sem esperar o relógio de verdade.

Guardamos a data/hora no banco SEM fuso (DATETIME do MySQL), sempre no horário local
do laboratório. Recife não tem horário de verão, então isso não gera ambiguidade.
"""
from datetime import datetime
from zoneinfo import ZoneInfo

from app.config import get_settings


def agora() -> datetime:
    fuso = ZoneInfo(get_settings().FUSO_HORARIO)
    return datetime.now(fuso).replace(tzinfo=None, microsecond=0)
