"""Simulação de um dia inteiro de atendimento.

Para que serve: o requisito pede o TM simulado e os 5% de senhas não atendidas.
O gestor escolhe um dia que já passou e a quantidade de senhas; o sistema "roda" o dia:
- as senhas chegam espalhadas entre 7h e 16h30;
- cada guichê chama a próxima pela MESMA regra de alternância do sistema real
  (regras_fila.ordem_de_busca);
- o tempo de cada atendimento é sorteado pela regra do TM (domain/simulacao.py);
- ~5% dos clientes vão embora: são chamados duas vezes e ficam NAO_COMPARECEU;
- às 17h ninguém mais é chamado e o que sobrou é descartado.

Toda mudança de estado passa por mudar_estado(), então a máquina de estados e o
histórico (auditoria) valem também para os dados simulados.
"""
import random
from datetime import date, datetime, time, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core import relogio
from app.core.erros import ErroNegocio
from app.domain import regras_fila, simulacao
from app.models import EstadoSenha, Guiche, HistoricoEstado, Perfil, Senha, SequenciaDiaria, Usuario
from app.services.senha_service import mudar_estado

E = EstadoSenha
MINUTOS_ATE_O_CLIENTE_CHEGAR = 1   # do painel até o guichê
MINUTOS_ENTRE_CHAMADAS = 2          # espera antes de chamar novamente


def simular_dia(db: Session, dia: date, quantidade: int, semente: int | None = None) -> dict:
    if dia >= relogio.agora().date():
        raise ErroNegocio("DIA_INVALIDO", "Escolha um dia que já passou para a simulação.", 422)
    if db.scalar(select(func.count()).select_from(Senha).where(Senha.data_emissao == dia)):
        raise ErroNegocio("DIA_JA_TEM_SENHAS", f"O dia {dia:%d/%m/%Y} já tem senhas registradas.")

    guiches = list(db.scalars(select(Guiche).where(Guiche.ativo).order_by(Guiche.numero)))
    atendentes = list(db.scalars(
        select(Usuario).where(Usuario.ativo, Usuario.perfil == Perfil.ATENDENTE).order_by(Usuario.id)
    ))
    if not guiches or not atendentes:
        raise ErroNegocio("SEM_GUICHE_OU_ATENDENTE", "Cadastre pelo menos um guichê e um atendente ativos.")

    rng = random.Random(semente)
    s = get_settings()
    abertura = datetime.combine(dia, time(s.HORA_INICIO_EXPEDIENTE))
    fechamento = datetime.combine(dia, time(s.HORA_FIM_EXPEDIENTE))
    ultima_emissao = fechamento - timedelta(minutes=30)

    # 1) Emissão: horários de chegada espalhados pelo dia, numeração por tipo
    chegadas = sorted(abertura + (ultima_emissao - abertura) * rng.random() for _ in range(quantidade))
    sequencial = {tipo: 0 for tipo in simulacao.PROPORCAO_TIPOS}
    senhas = []
    for momento in chegadas:
        momento = momento.replace(microsecond=0)
        tipo = simulacao.sortear_tipo(rng)
        sequencial[tipo] += 1
        senha = Senha(
            numero=regras_fila.formatar_numero(dia, tipo, sequencial[tipo]),
            tipo=tipo, sequencial=sequencial[tipo], data_emissao=dia,
            estado=E.EMITIDA, emitida_em=momento,
        )
        db.add(senha)
        db.flush()
        db.add(HistoricoEstado(senha_id=senha.id, estado_anterior=None, estado_novo=E.EMITIDA, ocorrido_em=momento))
        mudar_estado(db, senha, E.AGUARDANDO, momento)
        senhas.append(senha)

    for tipo, ultimo in sequencial.items():
        if ultimo:
            db.add(SequenciaDiaria(data=dia, tipo=tipo, ultimo_numero=ultimo))

    # 2) Atendimento: cada guichê fica livre num horário; o mais cedo chama a próxima
    livre_em = {g.id: abertura for g in guiches}
    atendente_do_guiche = {g.id: atendentes[i % len(atendentes)].id for i, g in enumerate(guiches)}
    fila = list(senhas)  # em ordem de chegada
    ultimo_tipo = None

    while fila:
        guiche_id = min(livre_em, key=livre_em.get)  # o guichê que fica livre primeiro
        agora = livre_em[guiche_id]
        if fila[0].emitida_em > agora:  # ninguém esperando: o guichê aguarda o próximo cliente chegar
            agora = fila[0].emitida_em
        if agora >= fechamento:
            break

        esperando = [x for x in fila if x.emitida_em <= agora]
        senha = None
        for tipo in regras_fila.ordem_de_busca(ultimo_tipo, s.MODO_ALTERNANCIA):
            senha = next((x for x in esperando if x.tipo == tipo), None)
            if senha:
                break
        fila.remove(senha)
        ultimo_tipo = senha.tipo
        usuario_id = atendente_do_guiche[guiche_id]

        mudar_estado(db, senha, E.CHAMADA, agora, usuario_id, guiche_id)
        senha.guiche_id, senha.atendente_id, senha.primeira_chamada_em = guiche_id, usuario_id, agora

        if simulacao.cliente_desiste(rng):
            segunda = agora + timedelta(minutes=MINUTOS_ENTRE_CHAMADAS)
            mudar_estado(db, senha, E.CHAMADA_NOVAMENTE, segunda, usuario_id, guiche_id)
            senha.segunda_chamada_em = segunda
            desistencia = segunda + timedelta(minutes=MINUTOS_ENTRE_CHAMADAS)
            mudar_estado(db, senha, E.NAO_COMPARECEU, desistencia, usuario_id, guiche_id)
            senha.motivo_encerramento = "NAO_COMPARECEU_APOS_2_CHAMADAS"
            livre_em[guiche_id] = desistencia
            continue

        inicio = agora + timedelta(minutes=MINUTOS_ATE_O_CLIENTE_CHEGAR)
        fim = inicio + timedelta(minutes=simulacao.sortear_tm_minutos(senha.tipo, rng))
        fim = fim.replace(microsecond=0)
        mudar_estado(db, senha, E.EM_ATENDIMENTO, inicio, usuario_id, guiche_id)
        senha.inicio_atendimento_em = inicio
        mudar_estado(db, senha, E.ATENDIDA, fim, usuario_id, guiche_id)
        senha.fim_atendimento_em = fim
        livre_em[guiche_id] = fim

    # 3) Fim do expediente: quem não foi chamado até as 17h é descartado
    for senha in fila:
        mudar_estado(db, senha, E.NAO_COMPARECEU, fechamento)
        senha.motivo_encerramento = "DESCARTADA_FIM_EXPEDIENTE"

    db.commit()
    return {
        "dia": dia,
        "emitidas": len(senhas),
        "atendidas": sum(1 for x in senhas if x.estado == E.ATENDIDA),
        "nao_compareceram": sum(1 for x in senhas if x.motivo_encerramento == "NAO_COMPARECEU_APOS_2_CHAMADAS"),
        "descartadas_fim_expediente": len(fila),
    }
