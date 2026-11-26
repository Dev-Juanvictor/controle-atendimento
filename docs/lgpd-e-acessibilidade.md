# LGPD e acessibilidade

## LGPD (Lei 13.709/2018)

### Que dados pessoais o sistema trata

| Quem | Dado | Para quê (finalidade) | Onde fica |
|---|---|---|---|
| Cliente | **Nenhum** | O totem não pede nome, CPF nem telefone. A senha (`261127-SP001`) não identifica ninguém | — |
| Funcionário | Nome e login | Identificar quem atendeu (auditoria exigida pelo laboratório) | `usuarios` |
| Funcionário | Senha de acesso | Entrar no sistema | `usuarios.senha_hash`: só o **hash bcrypt**, nunca a senha |
| Funcionário | Ações no sistema | Auditoria e segurança | `historico_estados` e `registros_acesso` |

### Princípios aplicados

- **Minimização:** só guardamos o mínimo para o atendimento e a auditoria. O cliente é anônimo.
- **Finalidade:** os dados dos funcionários são usados só para login, auditoria e relatórios.
- **Segurança:**
  - senha com hash bcrypt;
  - token de login (JWT) que expira em 8 horas;
  - acesso por perfil (só o gestor vê relatórios e cadastros);
  - segredos no `.env`, fora do GitHub;
  - o login recusado tem a mesma mensagem para "usuário não existe" e "senha errada", para não revelar quais logins existem.
- **Registro de acesso:** a tabela `registros_acesso` grava logins (aceitos e recusados), relatórios
  gerados, simulações, cadastros e encerramentos de expediente, com usuário e horário.
  **A senha digitada nunca é gravada.** O gestor consulta em `GET /api/v1/acessos`.
- **Logs sem dados pessoais:** o log de cada requisição guarda só método, rota, status e tempo
  (sem corpo, token ou nome).
- **Direitos do titular:** o gestor pode desativar um funcionário que saiu. O usuário não é
  apagado porque os registros de auditoria precisam continuar apontando para quem atendeu.
- **Retenção (proposta):** registros de acesso guardados por 6 meses, como o Marco Civil da
  Internet pede para registros de acesso a aplicações; depois disso, podem ser apagados.

## Acessibilidade (Lei Brasileira de Inclusão, 13.146/2015)

O que depende da API e o que o front faz:

| Necessidade | Como foi atendida |
|---|---|
| Pessoa com deficiência visual na sala de espera | Áudio da chamada no painel: tipo, número e guichê. Na 2ª chamada, "Última chamada" antes. A API envia `tipo`, `sequencial`, `guiche` e `ultima_chamada` para isso |
| Pessoa com deficiência auditiva | O painel mostra a senha e o guichê em letras grandes |
| Baixa visão | Fonte Atkinson Hyperlegible (diferencia 0 e O, 1 e l), números grandes, alto contraste |
| Daltonismo | A cor do tipo (roxa, dourada, azul) sempre vem com o nome escrito: a cor nunca é a única informação |
| Leitor de tela | Avisos com `aria-live` (a nova senha é lida), botões e campos com rótulo |
| Atendente que usa só teclado | Atalhos P, N, I e E no guichê; foco visível em todos os botões |
| Sensibilidade a movimento | Sem animações quando o sistema pede "reduzir movimento" |
| Atendimento prioritário (idosos, gestantes, PcD) | Senha SP, com prioridade na alternância |
