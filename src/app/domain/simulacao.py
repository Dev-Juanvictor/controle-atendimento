"""Regras da simulação do atendimento, em funções "puras" (sem banco).

O requisito pede que o tempo de atendimento (TM) seja simulado:
- SP: 15 min, variando 5 min para baixo ou para cima (distribuição igual) -> entre 10 e 20 min
- SG: 5 min, variando 3 min para baixo ou para cima                      -> entre 2 e 8 min
- SE: 1 min em 95% dos atendimentos e 5 min nos outros 5%
E que cerca de 5% das senhas emitidas não sejam atendidas (o cliente vai embora).

O "rng" (gerador de números aleatórios) vem de fora: nos testes usamos uma semente
fixa, e o resultado sai sempre igual.
"""
import random

from app.models import TipoSenha

CHANCE_CLIENTE_DESISTIR = 0.05

# Proporção de cada tipo nas senhas simuladas (o requisito não define; ver docs/decisoes.md)
PROPORCAO_TIPOS = {TipoSenha.SP: 0.2, TipoSenha.SE: 0.3, TipoSenha.SG: 0.5}


def sortear_tm_minutos(tipo: TipoSenha, rng: random.Random) -> float:
    """Sorteia quanto tempo (em minutos) vai durar um atendimento deste tipo."""
    if tipo == TipoSenha.SP:
        return rng.uniform(15 - 5, 15 + 5)
    if tipo == TipoSenha.SG:
        return rng.uniform(5 - 3, 5 + 3)
    # SE
    return 5.0 if rng.random() < 0.05 else 1.0


def cliente_desiste(rng: random.Random) -> bool:
    """True em ~5% das senhas: o cliente foi embora e não aparece quando é chamado."""
    return rng.random() < CHANCE_CLIENTE_DESISTIR


def sortear_tipo(rng: random.Random) -> TipoSenha:
    tipos = list(PROPORCAO_TIPOS)
    return rng.choices(tipos, weights=[PROPORCAO_TIPOS[t] for t in tipos])[0]
