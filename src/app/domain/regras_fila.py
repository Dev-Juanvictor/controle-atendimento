"""Regras de negócio da fila em funções "puras".

Puras = não acessam banco nem relógio; recebem valores e devolvem valores.
Vantagem: são fáceis de testar e de explicar na arguição.
"""
from datetime import date, datetime

from app.core.erros import ErroNegocio
from app.models import EstadoSenha, TipoSenha

E = EstadoSenha

# ---------- Máquina de estados ----------
# Para cada estado, quais são os próximos estados permitidos.
TRANSICOES_PERMITIDAS: dict[EstadoSenha, set[EstadoSenha]] = {
    E.EMITIDA: {E.AGUARDANDO},
    E.AGUARDANDO: {E.CHAMADA, E.NAO_COMPARECEU},          # NAO_COMPARECEU = descarte no fim do expediente
    E.CHAMADA: {E.CHAMADA_NOVAMENTE, E.EM_ATENDIMENTO, E.NAO_COMPARECEU},
    E.CHAMADA_NOVAMENTE: {E.EM_ATENDIMENTO, E.NAO_COMPARECEU},
    E.EM_ATENDIMENTO: {E.ATENDIDA},
    E.ATENDIDA: set(),        # estado final
    E.NAO_COMPARECEU: set(),  # estado final
}


def validar_transicao(atual: EstadoSenha, novo: EstadoSenha) -> None:
    if novo not in TRANSICOES_PERMITIDAS[atual]:
        raise ErroNegocio(
            "TRANSICAO_INVALIDA",
            f"Não é permitido passar a senha de {atual.value} para {novo.value}.",
        )


# ---------- Numeração YYMMDD-PPSQ ----------

def formatar_numero(data: date, tipo: TipoSenha, sequencial: int) -> str:
    """Ex.: 27/11/2026, SP, 1 -> '261127-SP001'."""
    if not 1 <= sequencial <= 999:
        raise ErroNegocio("LIMITE_DE_SENHAS", f"Limite diário de senhas {tipo.value} atingido (999).")
    return f"{data:%y%m%d}-{tipo.value}{sequencial:03d}"


# ---------- Alternância das chamadas ----------

def ordem_de_busca(ultimo_tipo: TipoSenha | None, modo: str = "DIAGRAMA") -> list[TipoSenha]:
    """Em que ordem procurar nas filas para escolher a próxima senha.

    O sistema percorre a lista e chama a primeira fila que tiver senha esperando.
    Assim, fila vazia é tratada naturalmente: se não tem SE, cai para SG, e assim por diante.

    modo DIAGRAMA (padrão) segue o diagrama do requisito: [SP] -> [SE|SG] -> [SP] -> [SE|SG]
      - depois de uma SP, a vez é de SE (ou SG, se não houver SE);
      - depois de SE ou SG (ou no começo do dia), a vez é de SP.

    modo CICLO segue a leitura literal do texto: SP -> SE -> SG -> SP -> SE -> SG

    O requisito tem as duas leituras; ver docs/decisoes.md.
    """
    SP, SE, SG = TipoSenha.SP, TipoSenha.SE, TipoSenha.SG

    if modo == "CICLO":
        if ultimo_tipo == SP:
            return [SE, SG, SP]
        if ultimo_tipo == SE:
            return [SG, SP, SE]
        return [SP, SE, SG]  # depois de SG, ou começo do dia

    # modo DIAGRAMA
    if ultimo_tipo == SP:
        return [SE, SG, SP]
    return [SP, SE, SG]


# ---------- Expediente ----------

def dentro_do_expediente(momento: datetime, hora_inicio: int, hora_fim: int) -> bool:
    """07:00:00 até 16:59:59 está dentro; 17:00 em diante está fora."""
    return hora_inicio <= momento.hour < hora_fim
