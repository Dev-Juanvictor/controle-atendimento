"""Tabelas do banco de dados (modelos SQLAlchemy).

Este arquivo é a ÚNICA fonte da estrutura do banco: o script scripts/gerar_sql.py
lê estes modelos e gera o database/schema.sql para o MySQL.
"""
import enum
from datetime import date, datetime

from sqlalchemy import (
    Boolean, Date, DateTime, Enum, ForeignKey, Index, Integer, String, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# ---------- Enumerações ----------

class Perfil(str, enum.Enum):
    ATENDENTE = "ATENDENTE"
    GESTOR = "GESTOR"  # o gestor também é atendente (requisito: "um único AA com perfil adicional de gestor")


class TipoSenha(str, enum.Enum):
    SP = "SP"  # prioritária
    SG = "SG"  # geral
    SE = "SE"  # retirada de exames


class EstadoSenha(str, enum.Enum):
    EMITIDA = "EMITIDA"
    AGUARDANDO = "AGUARDANDO"
    CHAMADA = "CHAMADA"
    CHAMADA_NOVAMENTE = "CHAMADA_NOVAMENTE"
    EM_ATENDIMENTO = "EM_ATENDIMENTO"
    ATENDIDA = "ATENDIDA"
    NAO_COMPARECEU = "NAO_COMPARECEU"


def _enum(tipo_enum, nome: str):
    # native_enum=False -> coluna VARCHAR + CHECK (funciona igual no MySQL e no SQLite)
    return Enum(tipo_enum, native_enum=False, length=20, create_constraint=True, name=nome)


# ---------- Tabelas ----------

class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(100))
    login: Mapped[str] = mapped_column(String(50), unique=True)
    senha_hash: Mapped[str] = mapped_column(String(100))  # nunca a senha em texto puro
    perfil: Mapped[Perfil] = mapped_column(_enum(Perfil, "ck_usuarios_perfil"))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)


class Guiche(Base):
    __tablename__ = "guiches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    numero: Mapped[int] = mapped_column(Integer, unique=True)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)


class Senha(Base):
    __tablename__ = "senhas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    numero: Mapped[str] = mapped_column(String(12), unique=True)  # YYMMDD-PPSQ, ex.: 261127-SP001
    tipo: Mapped[TipoSenha] = mapped_column(_enum(TipoSenha, "ck_senhas_tipo"))
    sequencial: Mapped[int] = mapped_column(Integer)
    data_emissao: Mapped[date] = mapped_column(Date)
    estado: Mapped[EstadoSenha] = mapped_column(_enum(EstadoSenha, "ck_senhas_estado"))

    # Horários usados nos relatórios e na auditoria
    emitida_em: Mapped[datetime] = mapped_column(DateTime)
    primeira_chamada_em: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    segunda_chamada_em: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    inicio_atendimento_em: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    fim_atendimento_em: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Quem chamou / atendeu (vazio enquanto não for chamada)
    guiche_id: Mapped[int | None] = mapped_column(ForeignKey("guiches.id"), nullable=True)
    atendente_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)

    # Por que terminou sem atendimento: NAO_COMPARECEU_APOS_2_CHAMADAS ou DESCARTADA_FIM_EXPEDIENTE
    motivo_encerramento: Mapped[str | None] = mapped_column(String(40), nullable=True)

    guiche: Mapped[Guiche | None] = relationship()
    atendente: Mapped[Usuario | None] = relationship()

    __table_args__ = (
        # Não pode existir duas senhas "SP 001" no mesmo dia
        UniqueConstraint("data_emissao", "tipo", "sequencial", name="uq_senhas_dia_tipo_seq"),
        # Índice para a consulta mais usada: "próxima senha AGUARDANDO do tipo X, hoje"
        Index("ix_senhas_fila", "data_emissao", "estado", "tipo", "sequencial"),
        # Índice para achar rápido a senha que está no guichê
        Index("ix_senhas_guiche_estado", "guiche_id", "estado"),
    )


class HistoricoEstado(Base):
    """Cada mudança de estado de uma senha vira uma linha aqui (histórico/auditoria)."""
    __tablename__ = "historico_estados"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    senha_id: Mapped[int] = mapped_column(ForeignKey("senhas.id"))
    estado_anterior: Mapped[EstadoSenha | None] = mapped_column(_enum(EstadoSenha, "ck_hist_anterior"), nullable=True)
    estado_novo: Mapped[EstadoSenha] = mapped_column(_enum(EstadoSenha, "ck_hist_novo"))
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    guiche_id: Mapped[int | None] = mapped_column(ForeignKey("guiches.id"), nullable=True)
    ocorrido_em: Mapped[datetime] = mapped_column(DateTime)

    senha: Mapped[Senha] = relationship()
    guiche: Mapped[Guiche | None] = relationship()

    __table_args__ = (
        Index("ix_hist_senha", "senha_id"),
        Index("ix_hist_estado_data", "estado_novo", "ocorrido_em"),
    )


class SequenciaDiaria(Base):
    """Último número emitido por tipo em cada dia (garante o SQ com reinício diário)."""
    __tablename__ = "sequencias_diarias"

    data: Mapped[date] = mapped_column(Date, primary_key=True)
    tipo: Mapped[TipoSenha] = mapped_column(_enum(TipoSenha, "ck_seq_tipo"), primary_key=True)
    ultimo_numero: Mapped[int] = mapped_column(Integer)


class ControleFila(Base):
    """Tabela com UMA linha só (id=1). Guarda o tipo da última senha chamada.

    Ela também é a "trava" da concorrência: quem vai chamar a próxima senha
    precisa primeiro travar esta linha. Ver services/atendimento_service.py.
    """
    __tablename__ = "controle_fila"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ultimo_tipo_chamado: Mapped[TipoSenha | None] = mapped_column(_enum(TipoSenha, "ck_controle_tipo"), nullable=True)
    data_referencia: Mapped[date | None] = mapped_column(Date, nullable=True)
    atualizado_em: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class RegistroAcesso(Base):
    """Registro de acesso (LGPD): quem fez login, quem viu relatório, quem cadastrou.

    Guarda só o necessário: o usuário, o evento e a hora. Nunca guarda senha.
    """
    __tablename__ = "registros_acesso"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    evento: Mapped[str] = mapped_column(String(40))  # ex.: LOGIN, LOGIN_RECUSADO, RELATORIO
    detalhe: Mapped[str | None] = mapped_column(String(200), nullable=True)
    ocorrido_em: Mapped[datetime] = mapped_column(DateTime)

    usuario: Mapped[Usuario | None] = relationship()

    __table_args__ = (Index("ix_acesso_data", "ocorrido_em"),)
