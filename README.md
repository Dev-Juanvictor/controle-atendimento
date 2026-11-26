# Controle de Atendimento: Laboratório de Análises Clínicas (Back End)

Projeto final da disciplina **Back End Frameworks** (UNINASSAU, 2026.2, Prof. Eduardo Hernandes).
API REST de senhas e filas (SP, SG e SE) para um laboratório, conforme o documento
"Sistema para controle de atendimento" v06 (Prof. João Ferreira), que está em [`docs/`](docs/).

Front end (React): repositório `controle-atendimento-front` _(colocar o link)_.

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
Se o banco foi criado com uma versão anterior do projeto, a API cria sozinha as tabelas que
faltarem ao iniciar.

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

Guichês cadastrados: 1 a 5. O gestor pode cadastrar outros atendentes e guichês.

**Para ter dados nos relatórios:** entre como `gestor`, vá em **Relatórios → Simular um dia**
(ou `POST /api/v1/simulacao` com `{"dia": "2026-11-25", "quantidade": 150}`) e depois gere o
relatório daquele dia.

**Testando pelo Swagger:**
1. `POST /api/v1/senhas` com `{"tipo": "SP"}` (repita com SG e SE).
2. `POST /api/v1/auth/login` com `{"login": "atendente1", "senha": "atendente123", "guiche_id": 1}`.
3. Copie o `access_token`, clique em **Authorize** (cadeado) e cole.
4. `POST /api/v1/atendimentos/chamar-proxima`, depois `iniciar` e `encerrar`.
5. `GET /api/v1/painel` mostra as 5 últimas chamadas.
6. Entre como `gestor` (sem `guiche_id`) e chame `GET /api/v1/relatorios/diario`.

## Como rodar os testes

```powershell
pytest -v
```
Não precisa do MySQL ligado: os testes criam um banco SQLite temporário. São 47 testes:
regras puras da fila, fluxo completo pela API, concorrência com threads, relatórios,
simulação, cadastros e registro de acesso.

O GitHub roda os mesmos testes a cada `push` (aba **Actions**, arquivo `.github/workflows/ci.yml`).

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
| GET | `/api/v1/relatorios/diario?data=AAAA-MM-DD` | Gestor | Relatório do dia: quantitativos, TM, detalhado, auditoria, indicadores |
| GET | `/api/v1/relatorios/mensal?ano=AAAA&mes=MM` | Gestor | O mesmo relatório para o mês inteiro |
| POST | `/api/v1/simulacao` | Gestor | Simula um dia passado (TM sorteado, ~5% não atendidas) |
| GET/POST | `/api/v1/usuarios` | Gestor | Lista / cadastra atendentes |
| PATCH | `/api/v1/usuarios/{id}` | Gestor | Ativa ou desativa um usuário |
| GET | `/api/v1/guiches` | Público | Lista os guichês (usado na tela de login) |
| POST/PATCH | `/api/v1/guiches` | Gestor | Cadastra / ativa ou desativa guichê |
| GET | `/api/v1/acessos` | Gestor | Registro de acesso (LGPD) |
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
├── domain/
│   ├── regras_fila.py   # regras puras: numeração, alternância, estados, expediente
│   └── simulacao.py     # regras puras da simulação: TM sorteado e 5% de desistência
├── services/            # casos de uso: emitir, chamar, atender, login, painel,
│                        #   relatórios, simulação, cadastros, registro de acesso
└── api/                 # rotas HTTP (sem regra de negócio) e dependências de login
```

- **Concorrência:** lock pessimista em uma linha de controle (`controle_fila`). Quem chama a
  próxima senha trava essa linha até o commit; os outros esperam. Isso impede senha duplicada
  **e** mantém a alternância correta. Provado em `tests/test_concorrencia.py`.
- **Alternância:** padrão `[SP] -> [SE|SG] -> [SP]` (diagrama do requisito). O modo
  `SP -> SE -> SG` também está pronto (`MODO_ALTERNANCIA=CICLO`).
- **Erros padronizados:** toda resposta de erro tem o formato
  `{"erro": {"codigo": "...", "mensagem": "..."}}`.
- **Relatórios:** calculados na hora a partir das senhas, que já guardam os 5 horários,
  o guichê e o atendente (ADR-09).
- **Simulação:** o TM e os 5% de desistência são sorteados por funções puras e o dia é "rodado"
  com a mesma alternância e a mesma máquina de estados do sistema real (ADR-10).

Requisitos funcionais, não funcionais e regras de negócio, cada um com o lugar do código que o
atende: [`docs/requisitos.md`](docs/requisitos.md). LGPD e acessibilidade:
[`docs/lgpd-e-acessibilidade.md`](docs/lgpd-e-acessibilidade.md).

## Diagramas

### Casos de uso
```mermaid
flowchart LR
    AC((Cliente))
    AA((Atendente))
    G((Gestor))
    subgraph SIS [Sistema de Controle de Atendimento]
        UC01([Emitir senha no totem])
        UC02([Acompanhar o painel])
        UC03([Entrar no guichê])
        UC04([Chamar próxima / chamar novamente])
        UC05([Iniciar e encerrar atendimento])
        UC06([Encerrar expediente])
        UC07([Ver relatórios, auditoria e indicadores])
        UC08([Simular dia de atendimento])
        UC09([Cadastrar atendentes e guichês])
        UC10([Consultar registro de acesso])
    end
    AC --- UC01
    AC --- UC02
    AA --- UC03
    AA --- UC04
    AA --- UC05
    G --- UC06
    G --- UC07
    G --- UC08
    G --- UC09
    G --- UC10
    G -. também atende .-> AA
```
Descrição de cada caso de uso: [`docs/requisitos.md`](docs/requisitos.md#casos-de-uso).

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
    USUARIOS ||--o{ REGISTROS_ACESSO : gera
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
    REGISTROS_ACESSO {
        int id PK
        int usuario_id FK
        string evento
        string detalhe
        datetime ocorrido_em
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
- [x] Relatórios diário e mensal: emitidas e atendidas (geral e por tipo), detalhado por senha, TM
- [x] Relatório de auditoria (atendente, guichê, senha, 1ª e 2ª chamada, início e fim)
- [x] Indicadores: espera média, duração média, taxa de atendimento e de não comparecimento, por guichê e por atendente
- [x] Simulação do TM (SP 15±5, SG 5±3, SE 1/5 min) e dos ~5% de senhas não atendidas
- [x] Cadastro de atendentes e guichês pelo gestor (criar, ativar, desativar)
- [x] Registro de acesso (LGPD) e logs estruturados em JSON
- [x] Erros padronizados, health check, banco fora do ar (503), reconexão automática
- [x] Backup e restauração do banco por script
- [x] Swagger automático, 47 testes automatizados, CI no GitHub Actions, Docker Compose
- [x] Front end em React integrado (repositório `controle-atendimento-front`)

**Não implementadas (melhorias futuras)**
- [ ] Encerramento automático do expediente às 17h (hoje o gestor clica em "Encerrar expediente")
- [ ] Exportar relatórios em PDF ou planilha (hoje: tela, impressão pelo navegador e JSON da API)
- [ ] Troca de senha pelo próprio atendente
- [ ] Publicação em servidor com HTTPS

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

## Disponibilidade e recuperação de falhas

| Falha | O que acontece | O que o front mostra |
|---|---|---|
| MySQL cai | A API responde `503 BANCO_INDISPONIVEL`; `/health` mostra `degradado` | Painel: "Sistema fora do ar" e continua com as últimas senhas. Totem e guichê: mensagem de indisponível |
| MySQL volta | A API reconecta sozinha (`pool_pre_ping`) | Tudo volta em poucos segundos, sem recarregar a página |
| API cai | Nada responde | Painel: "Sistema fora do ar" com as últimas senhas; demais telas: "Sem conexão com o sistema" |
| Perda de dados | Restaurar o último backup | — |

**Backup** (com o MySQL no Docker):
```powershell
.\scripts\backup.ps1                                     # cria backups\backup-AAAAMMDD-HHMM.sql
.\scripts\restaurar.ps1 backups\backup-20261127-1700.sql  # volta um backup
```
Rotina sugerida: um backup por dia, no fim do expediente. A pasta `backups/` não vai para o GitHub.

**Logs:** cada requisição gera uma linha JSON no terminal da API (método, rota, status, tempo),
sem dados pessoais.

---

## Uso de IA generativa

Usamos o Claude (Anthropic) como ferramenta de apoio na estrutura do projeto, no código,
nos testes e na documentação. Todo o código foi revisado e testado pela equipe, e cada
integrante sabe explicar as partes do projeto.
