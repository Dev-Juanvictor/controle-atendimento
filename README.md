# Controle de Atendimento: Laboratório de Análises Clínicas (Back End)

Projeto final da disciplina **Back End Frameworks** (UNINASSAU, 2026.2, Prof. Eduardo Hernandes).
API REST de senhas e filas (SP, SG e SE) para um laboratório, conforme o documento
"Sistema para controle de atendimento" v06 (Prof. João Ferreira), que está em [`docs/`](docs/).

**Equipe:** _(preencher: nome e matrícula de cada integrante)_

---

## Tecnologias

| Item | Versão |
|---|---|
| Python | 3.14 (funciona a partir do 3.12) |
| FastAPI | 0.165 |
| SQLAlchemy | 2.1 |
| MySQL | 8.0 |
| Testes | pytest 9 + httpx (banco SQLite temporário) |
| Segurança | bcrypt (hash de senha), JWT (login) |

Todas as dependências estão em [`requirements.txt`](requirements.txt).

## Pré-requisitos

- **Python 3.14** (ou 3.12+) e **Git**
- **Docker Desktop** (recomendado, para o MySQL) **ou** MySQL 8.0 instalado na máquina

---

## Como rodar (Windows / PowerShell)

### 1. Baixar o projeto e instalar as dependências

```powershell
git clone <url-do-repositorio>
cd controle-atendimento
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

> Se o PowerShell bloquear o `Activate.ps1`, rode uma vez:
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`
>
> No Linux/macOS: `source .venv/bin/activate`.

### 2. Criar o arquivo `.env`

```powershell
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_hex(32))"
```
Cole a chave gerada em `JWT_SECRET=` dentro do `.env`.

> **Demonstração à noite:** o expediente é das 7h às 17h. Para demonstrar fora desse horário,
> coloque `IGNORAR_EXPEDIENTE=true` no `.env`.

### 3. Subir o banco de dados

**Opção A: com Docker (recomendado)**
```powershell
docker compose up -d mysql
```
Na primeira vez, o MySQL cria as tabelas (`database/schema.sql`) e os dados de teste
(`database/seed.sql`) sozinho. Para zerar tudo: `docker compose down -v`.

**Opção B: MySQL instalado na máquina**
```powershell
Get-Content database\schema.sql | mysql -u root -p
Get-Content database\seed.sql | mysql -u root -p
```
E ajuste o `.env`: `DATABASE_URL=mysql+pymysql://root:SUA_SENHA@localhost:3306/controle_atendimento`

### 4. Subir a API

```powershell
uvicorn app.main:app --reload --app-dir src
```

- Documentação (Swagger): **http://localhost:8000/docs**
- Health check: http://localhost:8000/health

### Alternativa: tudo no Docker (banco + API)

```powershell
docker compose up -d --build
```

---

## Usuários de teste (seed)

| Login | Senha | Perfil |
|---|---|---|
| `gestor` | `gestor123` | GESTOR (também pode atender) |
| `atendente1` | `atendente123` | ATENDENTE |
| `atendente2` | `atendente123` | ATENDENTE |
| `atendente3` | `atendente123` | ATENDENTE |

Guichês cadastrados: 1 a 5.

**Testando pelo Swagger:**
1. `POST /api/v1/senhas` com `{"tipo": "SP"}` (repita com SG e SE).
2. `POST /api/v1/auth/login` com `{"login": "atendente1", "senha": "atendente123", "guiche_id": 1}`.
3. Copie o `access_token`, clique em **Authorize** (cadeado) e cole.
4. `POST /api/v1/atendimentos/chamar-proxima`, depois `iniciar` e `encerrar`.
5. `GET /api/v1/painel` mostra as 5 últimas chamadas.

## Como rodar os testes

```powershell
pytest -v
```
Não precisa do MySQL ligado: os testes criam um banco SQLite temporário.

---

## Endpoints

| Método | Rota | Quem usa | O que faz |
|---|---|---|---|
| POST | `/api/v1/senhas` | Totem (anônimo) | Emite senha `{"tipo": "SP"\|"SG"\|"SE"}` |
| GET | `/api/v1/painel` | Painel (público) | 5 últimas chamadas |
| POST | `/api/v1/auth/login` | Atendente/gestor | Login, retorna token |
| GET | `/api/v1/auth/me` | Logado | Dados do usuário logado |
| GET | `/api/v1/atendimentos/atual` | Atendente | Senha que está no meu guichê |
| POST | `/api/v1/atendimentos/chamar-proxima` | Atendente | Chama a próxima pela alternância |
| POST | `/api/v1/atendimentos/chamar-novamente` | Atendente | 2ª chamada ("última chamada") |
| POST | `/api/v1/atendimentos/iniciar` | Atendente | Cliente chegou |
| POST | `/api/v1/atendimentos/encerrar` | Atendente | Fim do atendimento |
| POST | `/api/v1/expediente/encerrar` | Gestor | Descarta as senhas que sobraram |
| GET | `/health` | Front/Docker | API e banco estão no ar? |

---

## Arquitetura e decisões (resumo)

Detalhes e justificativas em [`docs/decisoes.md`](docs/decisoes.md).

```
src/app/
├── main.py              # cria a API e registra as rotas
├── config.py            # lê o .env
├── database.py          # conexão com o banco
├── models.py            # tabelas
├── schemas.py           # formato de entrada/saída da API
├── seed.py              # dados de teste
├── core/                # erros padronizados, segurança (bcrypt/JWT), relógio
├── domain/regras_fila.py# regras puras: numeração, alternância, estados, expediente
├── services/            # casos de uso: emitir, chamar, atender, login, painel
└── api/                 # rotas HTTP (sem regra de negócio) e dependências de login
```

- **Concorrência:** lock pessimista em uma linha de controle (`controle_fila`). Quem chama a
  próxima senha trava essa linha até o commit; os outros esperam. Isso impede senha duplicada
  **e** mantém a alternância correta. Provado em `tests/test_concorrencia.py`.
- **Alternância:** padrão `[SP] -> [SE|SG] -> [SP]` (diagrama do requisito). O modo
  `SP -> SE -> SG` também está pronto (`MODO_ALTERNANCIA=CICLO`).
- **Erros padronizados:** toda resposta de erro tem o formato
  `{"erro": {"codigo": "...", "mensagem": "..."}}`.

## Diagramas

### Máquina de estados da senha
```mermaid
stateDiagram-v2
    [*] --> EMITIDA: totem
    EMITIDA --> AGUARDANDO: automático
    AGUARDANDO --> CHAMADA: chamar próxima
    CHAMADA --> CHAMADA_NOVAMENTE: chamar novamente
    CHAMADA --> EM_ATENDIMENTO: iniciar
    CHAMADA_NOVAMENTE --> EM_ATENDIMENTO: iniciar
    CHAMADA_NOVAMENTE --> NAO_COMPARECEU: 2 chamadas sem cliente
    EM_ATENDIMENTO --> ATENDIDA: encerrar
    AGUARDANDO --> NAO_COMPARECEU: fim do expediente
    CHAMADA --> NAO_COMPARECEU: fim do expediente
    ATENDIDA --> [*]
    NAO_COMPARECEU --> [*]
```

### Modelo do banco (entidade-relacionamento)
```mermaid
erDiagram
    USUARIOS ||--o{ SENHAS : atende
    GUICHES ||--o{ SENHAS : "é chamada em"
    SENHAS ||--o{ HISTORICO_ESTADOS : registra
    USUARIOS ||--o{ HISTORICO_ESTADOS : executa
    GUICHES ||--o{ HISTORICO_ESTADOS : em
    USUARIOS {
        int id PK
        string login UK
        string senha_hash
        string perfil
    }
    GUICHES {
        int id PK
        int numero UK
        bool ativo
    }
    SENHAS {
        int id PK
        string numero UK
        string tipo
        int sequencial
        date data_emissao
        string estado
        datetime emitida_em
        datetime primeira_chamada_em
        datetime segunda_chamada_em
        datetime inicio_atendimento_em
        datetime fim_atendimento_em
        string motivo_encerramento
    }
    HISTORICO_ESTADOS {
        int id PK
        int senha_id FK
        string estado_anterior
        string estado_novo
        datetime ocorrido_em
    }
    SEQUENCIAS_DIARIAS {
        date data PK
        string tipo PK
        int ultimo_numero
    }
    CONTROLE_FILA {
        int id PK
        string ultimo_tipo_chamado
        date data_referencia
    }
```

### Sequência: chamar próxima (com concorrência)
```mermaid
sequenceDiagram
    participant A1 as Atendente 1
    participant A2 as Atendente 2
    participant API
    participant DB as MySQL
    A1->>API: POST /chamar-proxima
    A2->>API: POST /chamar-proxima
    API->>DB: UPDATE controle_fila (trava linha) [A1]
    API->>DB: UPDATE controle_fila [A2 fica esperando]
    API->>DB: escolhe senha pela alternância, marca CHAMADA [A1]
    API->>DB: COMMIT [A1] (libera a trava)
    API-->>A1: 261127-SP001, guichê 1
    API->>DB: escolhe a PRÓXIMA senha, marca CHAMADA [A2]
    API->>DB: COMMIT [A2]
    API-->>A2: 261127-SE001, guichê 2
```

_(Falta: diagrama de casos de uso; ver lista abaixo.)_

---

## Funcionalidades

**Implementadas**
- [x] Emissão de SP, SG e SE sem login, numeração `YYMMDD-PPSQ` com reinício diário
- [x] Alternância `[SP] -> [SE|SG]` com prioridades e filas vazias (e modo `CICLO` opcional)
- [x] Chamar próxima, chamar novamente, iniciar e encerrar atendimento
- [x] Não comparecimento após 2 chamadas
- [x] Máquina de 7 estados com validação e histórico
- [x] Expediente 7h–17h (bloqueia emissão e chamada; atendimento em curso pode terminar)
- [x] Encerramento do expediente com descarte das senhas restantes (gestor)
- [x] Painel com as 5 últimas chamadas (com indicação de "última chamada" para o áudio)
- [x] Concorrência sem senha duplicada (testada com threads)
- [x] Login com bcrypt + JWT, perfis ATENDENTE e GESTOR
- [x] Erros padronizados, health check, tratamento de banco fora do ar (503)
- [x] Swagger automático, testes automatizados, Docker Compose

**Pendentes**
- [ ] Relatórios diários e mensais (emitidas/atendidas, por tipo, detalhado, TM)
- [ ] Relatório de auditoria
- [ ] Indicadores de desempenho (tempo de espera, taxa de não comparecimento, por guichê)
- [ ] Simulação do TM (SP 15±5, SG 5±3, SE 1/5 min) e dos 5% de senhas não atendidas
- [ ] Cadastro de atendentes e guichês pelo gestor
- [ ] Documento de LGPD e acessibilidade
- [ ] Diagrama de casos de uso
- [ ] CORS para o front end, logs estruturados, CI

---

## Integração com o front end

- O front fica no projeto `controle-atendimento-front` (ver o README dele para rodar tudo junto).
  Ele acessa a API pelo proxy do Vite, por isso não precisa de CORS.
- Base da API: `http://localhost:8000/api/v1`
- Autenticação: header `Authorization: Bearer <token>` (obtido em `/auth/login`).
- **Painel:** consultar `GET /painel` a cada 2–3 segundos.
- **Áudio:** as respostas de chamada trazem `tipo`, `sequencial`, `guiche` e `ultima_chamada`.
  Quando `ultima_chamada` for `true`, o áudio começa com "Última chamada".
- **Erros:** sempre `{"erro": {"codigo", "mensagem"}}`. Se vier `503` / `BANCO_INDISPONIVEL`
  (ou `/health` falhar), o painel deve mostrar "Sistema temporariamente indisponível" e
  continuar exibindo as últimas senhas que já tinha.

---

## Uso de IA generativa

_(O edital exige declarar.)_ Usamos o Claude (Anthropic) como apoio para montar a estrutura
inicial do projeto, as regras da fila e os testes. Todo o código foi revisado pela equipe, e
cada integrante sabe explicar as partes do projeto. _(Ajustar este texto com o que o grupo
realmente fez.)_
