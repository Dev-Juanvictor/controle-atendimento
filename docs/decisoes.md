# Decisões de arquitetura (ADR)

Registro curto de cada decisão importante: **o que** escolhemos e **por quê**.
Na arguição, qualquer integrante deve conseguir explicar estes pontos.

---

## ADR-01 · Stack: Python + FastAPI + MySQL 8

- **Decisão:** Python 3.14, FastAPI, SQLAlchemy 2, MySQL 8.0 (opções aceitas pelo edital).
- **Por quê:** o FastAPI gera a documentação Swagger (`/docs`) e valida os dados de entrada
  automaticamente (Pydantic), dois itens cobrados na rubrica. O MySQL é o banco citado no
  requisito e na rubrica, e tem lock de linha (InnoDB), que usamos na concorrência.
- **Testes:** rodam em SQLite temporário, para qualquer um rodar `pytest` sem subir o MySQL.

## ADR-02 · Organização em camadas

```
api/routes   -> recebe a requisição HTTP e devolve a resposta (sem regra de negócio)
services     -> orquestra o caso de uso (abre/fecha transação, chama as regras)
domain       -> regras puras (numeração, alternância, máquina de estados, expediente)
models       -> tabelas do banco
```
- **Por quê:** a rubrica penaliza "lógica de negócio nos controllers". As regras puras ficam
  isoladas e são testadas sem banco (`tests/test_regras_fila.py`).

## ADR-03 · Concorrência: lock pessimista na linha de controle

- **Problema:** dois atendentes clicam em "chamar próxima" ao mesmo tempo.
- **Decisão:** toda chamada começa com `UPDATE controle_fila SET ... WHERE id = 1`. O InnoDB
  trava essa linha até o `COMMIT`; a segunda chamada espera a primeira terminar.
- **Por que não `SELECT ... FOR UPDATE SKIP LOCKED` nas senhas?** A alternância depende do
  "tipo da última senha chamada", que é um dado único para o laboratório inteiro. Com SKIP LOCKED,
  dois atendentes poderiam ler "a última foi SP" ao mesmo tempo e os dois chamarem SE/SG,
  quebrando a regra. Serializando pela linha de controle, cada chamada enxerga a anterior.
- **Custo:** as chamadas são processadas uma de cada vez. Cada uma leva milissegundos e o
  laboratório tem poucos guichês, então o impacto é imperceptível.
- **Prova:** `tests/test_concorrencia.py` dispara 4 atendentes ao mesmo tempo (com barreira de
  threads) e verifica que (1) nenhuma senha vai para dois guichês e (2) a alternância SP/SE
  se mantém. Se a trava for removida, os dois testes falham.
- **Emissão no totem:** a sequência do dia usa `UPDATE ... SET ultimo_numero = ultimo_numero + 1`,
  que também trava a linha; mais a constraint `UNIQUE (data_emissao, tipo, sequencial)`.

## ADR-04 · Interpretação da alternância (PERGUNTAR AO PROFESSOR)

O requisito tem duas leituras possíveis:

| Modo | Fonte no requisito | Sequência |
|---|---|---|
| `DIAGRAMA` (padrão) | diagrama `[SP] -> [SE\|SG] -> [SP] -> [SE\|SG]` | depois de SP vem SE (ou SG se não houver SE); depois de SE/SG vem SP |
| `CICLO` | texto "uma SP, em seguida uma SE, para enfim uma SG" | SP -> SE -> SG -> SP -> SE -> SG |

- **Decisão:** implementamos os dois; o padrão é `DIAGRAMA`. Troca-se no `.env`
  (`MODO_ALTERNANCIA`). Em ambos, fila vazia é pulada seguindo a prioridade SP > SE > SG.
- A alternância recomeça (por SP) a cada novo dia.

## ADR-05 · Máquina de estados e descartes

Transições permitidas (qualquer outra é rejeitada com `409 TRANSICAO_INVALIDA`):

```
EMITIDA -> AGUARDANDO                   (automático ao emitir)
AGUARDANDO -> CHAMADA                   (chamar próxima)
CHAMADA -> CHAMADA_NOVAMENTE            (chamar novamente)
CHAMADA | CHAMADA_NOVAMENTE -> EM_ATENDIMENTO
CHAMADA_NOVAMENTE -> NAO_COMPARECEU     (2 chamadas sem o cliente: ao chamar a próxima)
EM_ATENDIMENTO -> ATENDIDA
AGUARDANDO | CHAMADA | CHAMADA_NOVAMENTE -> NAO_COMPARECEU   (descarte no fim do expediente)
```

- O requisito lista só 7 estados e não tem "DESCARTADA". Para não inventar um 8º estado,
  senhas descartadas no fim do expediente vão para `NAO_COMPARECEU` com
  `motivo_encerramento = 'DESCARTADA_FIM_EXPEDIENTE'`. Assim os relatórios distinguem os casos.
- Toda mudança passa por uma única função (`senha_service.mudar_estado`), que valida e grava
  em `historico_estados`.
- Para desistir de um cliente, o atendente precisa ter chamado **duas** vezes.

## ADR-06 · Horário e expediente

- Datas/horas são gravadas no horário local do laboratório (`America/Recife`, sem horário de verão).
- Expediente: 07:00 até 16:59:59. Fora dele não se emite nem se chama; encerrar atendimento
  em curso continua permitido.
- Como a aula é à noite, para a **demonstração** usa-se `IGNORAR_EXPEDIENTE=true` no `.env`.
  A regra continua provada pelos testes automatizados (relógio falso).

## ADR-07 · Uma única fonte para o banco

- `src/app/models.py` define as tabelas; `scripts/gerar_sql.py` gera `database/schema.sql`
  e `database/seed.sql` (MySQL). O Docker executa esses scripts na primeira subida.

## ADR-08 · LGPD (minimização)

- O cliente é anônimo: o totem não pede nenhum dado pessoal; a senha não identifica ninguém.
- Dados pessoais existem só para os funcionários (nome e login) e a senha deles é guardada
  com hash bcrypt.
- O histórico de estados registra quem (usuário) fez cada ação e quando (registro de acesso).
