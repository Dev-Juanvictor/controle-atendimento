"""Formato dos dados que entram e saem da API (validação automática pelo Pydantic)."""
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import EstadoSenha, Perfil, Senha, TipoSenha


# ---------- Totem ----------

class EmitirSenhaRequest(BaseModel):
    tipo: TipoSenha = Field(description="SP (prioritária), SG (geral) ou SE (retirada de exames)")


class SenhaEmitidaResponse(BaseModel):
    """O que o totem imprime. Sem nenhum dado pessoal do cliente (LGPD: minimização)."""
    model_config = ConfigDict(from_attributes=True)

    numero: str = Field(examples=["261127-SP001"])
    tipo: TipoSenha
    emitida_em: datetime


# ---------- Atendimento ----------

class SenhaGuicheResponse(BaseModel):
    """Senha que está no guichê. Traz o que o front precisa para o painel e o áudio."""
    numero: str
    tipo: TipoSenha
    sequencial: int
    estado: EstadoSenha
    guiche: int | None = Field(description="Número do guichê (o que aparece no painel)")
    ultima_chamada: bool = Field(description="true na 2ª chamada: o áudio deve dizer 'Última chamada'")

    @classmethod
    def de(cls, senha: Senha) -> "SenhaGuicheResponse":
        return cls(
            numero=senha.numero,
            tipo=senha.tipo,
            sequencial=senha.sequencial,
            estado=senha.estado,
            guiche=senha.guiche.numero if senha.guiche else None,
            ultima_chamada=senha.estado == EstadoSenha.CHAMADA_NOVAMENTE,
        )


class ChamadaPainel(BaseModel):
    numero: str
    tipo: TipoSenha
    sequencial: int
    guiche: int
    ultima_chamada: bool
    chamada_em: datetime


class PainelResponse(BaseModel):
    ultimas_chamadas: list[ChamadaPainel] = Field(
        description="As 5 últimas chamadas, da mais recente para a mais antiga"
    )


class EncerrarExpedienteResponse(BaseModel):
    senhas_descartadas: int


# ---------- Login ----------

class LoginRequest(BaseModel):
    login: str = Field(min_length=1, max_length=50)
    senha: str = Field(min_length=1, max_length=100)
    guiche_id: int | None = Field(
        default=None, description="Guichê em que o atendente vai trabalhar (opcional para o gestor)"
    )


class UsuarioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nome: str
    login: str
    perfil: Perfil


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: UsuarioResponse
    guiche_id: int | None


# ---------- Cadastros (gestor) ----------

class UsuarioCadastro(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nome: str
    login: str
    perfil: Perfil
    ativo: bool


class NovoUsuarioRequest(BaseModel):
    nome: str = Field(min_length=3, max_length=100)
    login: str = Field(min_length=3, max_length=50, pattern=r"^[a-z0-9._-]+$",
                       description="Só letras minúsculas, números, ponto, hífen e sublinhado")
    senha: str = Field(min_length=6, max_length=100)
    perfil: Perfil = Perfil.ATENDENTE


class AtivoRequest(BaseModel):
    ativo: bool


class GuicheResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    numero: int
    ativo: bool


class NovoGuicheRequest(BaseModel):
    numero: int = Field(ge=1, le=99)


class RegistroAcessoResponse(BaseModel):
    usuario: str | None
    evento: str
    detalhe: str | None
    ocorrido_em: datetime


# ---------- Relatórios ----------

class QuantidadePorTipo(BaseModel):
    tipo: TipoSenha
    emitidas: int
    atendidas: int
    tm_minutos: float | None = Field(description="Tempo médio de atendimento (TM) deste tipo, em minutos")


class DesempenhoItem(BaseModel):
    nome: str
    atendimentos: int
    tm_minutos: float | None


class Indicadores(BaseModel):
    tempo_medio_espera_minutos: float | None = Field(description="Da emissão até a 1ª chamada")
    tempo_medio_atendimento_minutos: float | None = Field(description="Do início ao fim do atendimento")
    taxa_atendimento_percentual: float
    taxa_nao_comparecimento_percentual: float
    por_guiche: list[DesempenhoItem]
    por_atendente: list[DesempenhoItem]


class SenhaDetalhada(BaseModel):
    numero: str
    tipo: TipoSenha
    emitida_em: datetime
    atendida_em: datetime | None = Field(description="Em branco se a senha não foi atendida")
    guiche: int | None = Field(description="Em branco se a senha não foi atendida")
    situacao: EstadoSenha


class LinhaAuditoria(BaseModel):
    numero: str
    atendente: str | None
    guiche: int | None
    primeira_chamada: datetime | None
    segunda_chamada: datetime | None
    inicio_atendimento: datetime | None
    fim_atendimento: datetime | None


class RelatorioResponse(BaseModel):
    inicio: date
    fim: date
    emitidas: int
    atendidas: int
    nao_compareceram: int = Field(description="Chamadas 2 vezes e o cliente não veio")
    descartadas_fim_expediente: int
    por_tipo: list[QuantidadePorTipo]
    indicadores: Indicadores
    senhas: list[SenhaDetalhada] = Field(description="Relatório detalhado, uma linha por senha")
    auditoria: list[LinhaAuditoria]


# ---------- Simulação ----------

class SimulacaoRequest(BaseModel):
    dia: date = Field(description="Um dia que já passou e ainda não tem senhas")
    quantidade: int = Field(default=150, ge=1, le=600, description="Quantas senhas emitir no dia")
    semente: int | None = Field(default=None, description="Opcional: mesma semente = mesmo resultado")


class SimulacaoResponse(BaseModel):
    dia: date
    emitidas: int
    atendidas: int
    nao_compareceram: int
    descartadas_fim_expediente: int
