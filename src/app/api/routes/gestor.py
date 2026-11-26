"""Rotas do gestor: relatórios, simulação, cadastros e registro de acesso.

Todas exigem login com perfil GESTOR (dependência somente_gestor),
exceto a lista de guichês, que a tela de login usa antes de alguém entrar.
"""
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import Sessao, somente_gestor
from app.core import relogio
from app.database import get_db
from app.schemas import (
    AtivoRequest, GuicheResponse, NovoGuicheRequest, NovoUsuarioRequest, RegistroAcessoResponse,
    RelatorioResponse, SimulacaoRequest, SimulacaoResponse, UsuarioCadastro,
)
from app.services import acesso_service, cadastro_service, relatorio_service, simulacao_service

# ---------- Relatórios ----------

relatorios = APIRouter(prefix="/relatorios", tags=["Relatórios (gestor)"])


@relatorios.get("/diario", response_model=RelatorioResponse, summary="Relatório de um dia")
def relatorio_diario(
    data: date | None = Query(default=None, description="Padrão: hoje"),
    s: Sessao = Depends(somente_gestor),
    db: Session = Depends(get_db),
):
    dia = data or relogio.agora().date()
    acesso_service.registrar(db, s.usuario.id, "RELATORIO", f"diário {dia:%d/%m/%Y}")
    return relatorio_service.gerar(db, dia, dia)


@relatorios.get("/mensal", response_model=RelatorioResponse, summary="Relatório de um mês")
def relatorio_mensal(
    ano: int | None = Query(default=None, ge=2000, le=2100, description="Padrão: ano atual"),
    mes: int | None = Query(default=None, ge=1, le=12, description="Padrão: mês atual"),
    s: Sessao = Depends(somente_gestor),
    db: Session = Depends(get_db),
):
    hoje = relogio.agora().date()
    inicio, fim = relatorio_service.periodo_do_mes(ano or hoje.year, mes or hoje.month)
    acesso_service.registrar(db, s.usuario.id, "RELATORIO", f"mensal {inicio:%m/%Y}")
    return relatorio_service.gerar(db, inicio, fim)


# ---------- Simulação ----------

simulacao = APIRouter(prefix="/simulacao", tags=["Relatórios (gestor)"])


@simulacao.post("", response_model=SimulacaoResponse, status_code=201,
                summary="Simular um dia de atendimento (TM e 5% de não atendidas)")
def simular(dados: SimulacaoRequest, s: Sessao = Depends(somente_gestor), db: Session = Depends(get_db)):
    resultado = simulacao_service.simular_dia(db, dados.dia, dados.quantidade, dados.semente)
    acesso_service.registrar(db, s.usuario.id, "SIMULACAO", f"{dados.quantidade} senhas em {dados.dia:%d/%m/%Y}")
    return resultado


# ---------- Cadastros ----------

usuarios = APIRouter(prefix="/usuarios", tags=["Cadastros (gestor)"])


@usuarios.get("", response_model=list[UsuarioCadastro], summary="Listar atendentes e gestores")
def listar_usuarios(s: Sessao = Depends(somente_gestor), db: Session = Depends(get_db)):
    return cadastro_service.listar_usuarios(db)


@usuarios.post("", response_model=UsuarioCadastro, status_code=201, summary="Cadastrar atendente")
def criar_usuario(dados: NovoUsuarioRequest, s: Sessao = Depends(somente_gestor), db: Session = Depends(get_db)):
    usuario = cadastro_service.criar_usuario(db, dados.nome, dados.login, dados.senha, dados.perfil)
    acesso_service.registrar(db, s.usuario.id, "CADASTRO", f"criou o usuário {usuario.login}")
    return usuario


@usuarios.patch("/{usuario_id}", response_model=UsuarioCadastro, summary="Ativar ou desativar usuário")
def alterar_usuario(usuario_id: int, dados: AtivoRequest, s: Sessao = Depends(somente_gestor),
                    db: Session = Depends(get_db)):
    usuario = cadastro_service.alterar_usuario(db, usuario_id, dados.ativo, s.usuario.id)
    situacao = "ativou" if dados.ativo else "desativou"
    acesso_service.registrar(db, s.usuario.id, "CADASTRO", f"{situacao} o usuário {usuario.login}")
    return usuario


guiches = APIRouter(prefix="/guiches", tags=["Cadastros (gestor)"])


@guiches.get("", response_model=list[GuicheResponse], summary="Listar guichês (público: usado no login)")
def listar_guiches(db: Session = Depends(get_db)):
    return cadastro_service.listar_guiches(db)


@guiches.post("", response_model=GuicheResponse, status_code=201, summary="Cadastrar guichê")
def criar_guiche(dados: NovoGuicheRequest, s: Sessao = Depends(somente_gestor), db: Session = Depends(get_db)):
    guiche = cadastro_service.criar_guiche(db, dados.numero)
    acesso_service.registrar(db, s.usuario.id, "CADASTRO", f"criou o guichê {guiche.numero}")
    return guiche


@guiches.patch("/{guiche_id}", response_model=GuicheResponse, summary="Ativar ou desativar guichê")
def alterar_guiche(guiche_id: int, dados: AtivoRequest, s: Sessao = Depends(somente_gestor),
                   db: Session = Depends(get_db)):
    guiche = cadastro_service.alterar_guiche(db, guiche_id, dados.ativo)
    situacao = "ativou" if dados.ativo else "desativou"
    acesso_service.registrar(db, s.usuario.id, "CADASTRO", f"{situacao} o guichê {guiche.numero}")
    return guiche


# ---------- Registro de acesso (LGPD) ----------

acessos = APIRouter(prefix="/acessos", tags=["Cadastros (gestor)"])


@acessos.get("", response_model=list[RegistroAcessoResponse], summary="Últimos registros de acesso")
def listar_acessos(limite: int = Query(default=50, ge=1, le=500), s: Sessao = Depends(somente_gestor),
                   db: Session = Depends(get_db)):
    return [
        RegistroAcessoResponse(
            usuario=r.usuario.nome if r.usuario else None,
            evento=r.evento, detalhe=r.detalhe, ocorrido_em=r.ocorrido_em,
        )
        for r in acesso_service.ultimos(db, limite)
    ]
