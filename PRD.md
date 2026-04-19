# Friends - PRD

Status do documento: ativo
Nome oficial do app: Friends
Tipo de projeto: app pessoal para uso individual
Modo de desenvolvimento: iterativo, incremental e orientado por handoff

## 1. Como manter o `progress.txt`

O arquivo `progress.txt` e obrigatorio e deve ser atualizado ao final de toda iteracao relevante.

Regras:

- qualquer IA que fizer analise, implementacao, refatoracao, definicao de arquitetura ou mudanca de escopo deve atualizar o `progress.txt` antes de encerrar o passo
- a entrada mais recente deve ficar no topo do arquivo, acima das entradas antigas
- o arquivo deve registrar decisoes, mudancas realizadas, estado atual e proximo passo sugerido
- se uma decisao de produto ou arquitetura mudar, a IA deve atualizar `PRD.md` e `progress.txt` no mesmo passo
- o `progress.txt` nao deve ser apagado ou reiniciado; ele e o historico operacional do projeto
- atividades concluidas continuam no `progress.txt`, mas nao precisam continuar listadas como tarefas no `PRD.md`

Formato obrigatorio para novas entradas:

```text
Data: YYYY-MM-DD
Iteracao: nome curto da iteracao
Resumo: 1 a 3 linhas sobre o que aconteceu
Decisoes:
- decisao 1
- decisao 2
Arquivos alterados:
- arquivo 1
- arquivo 2
Pendencias:
- item 1
- item 2
Proximo passo sugerido:
- item 1
- item 2
```

## 2. Resumo executivo

Friends e um app pessoal para ajudar o usuario a manter, reavivar e aprofundar amizades de forma intencional. O sistema deve funcionar como uma combinacao de:

- memoria relacional
- historico estruturado de interacoes
- painel de acompanhamento de cadencia
- base de interesses compartilhados
- ponte para Evernote
- camada de lembretes via Google Calendar

O app nao sera tratado como produto comercial. As decisoes devem priorizar:

- velocidade de uso
- baixo atrito para registrar interacoes
- confiabilidade local
- simplicidade de manutencao
- utilidade pessoal acima de generalizacao de produto

## 3. Decisoes de produto e escopo ja definidas

As decisoes abaixo ja estao fechadas e nao entram como atividades pendentes:

- o nome oficial do app e `Friends`
- o projeto e para uso pessoal, nao para venda
- Todoist saiu do escopo
- Evernote e obrigatorio no escopo, mas via IFTTT (nao via API nativa)
- Google Calendar continua no escopo via API oficial
- o MVP sera local-first
- a fonte principal de verdade dos dados sera o proprio Friends
- o Evernote sera inicialmente um destino one-way de append de historico
- nao vamos perseguir sync bidirecional completo com Evernote no inicio
- integracao com Google Calendar sera um evento por contato, nao rotina central

## 4. Objetivo do produto

O Friends deve reduzir o custo mental de cuidar das amizades. O usuario deve conseguir:

- saber rapidamente quem precisa de contato
- abrir um contato e recuperar contexto suficiente para agir
- registrar interacoes em poucos segundos
- manter historico local confiavel
- refletir o historico relevante no Evernote
- receber lembretes praticos no Google Calendar

## 5. Principios de produto

- o app deve apoiar, nao cobrar
- o registro de interacoes deve ser mais rapido do que abrir o Evernote manualmente
- a tela principal deve orientar para acao, nao apenas exibicao
- a integracao com Evernote deve falhar sem comprometer os dados locais
- a arquitetura deve ser simples o suficiente para iterar com seguranca

## 6. Arquitetura definida

O Friends vai seguir a mesma linha tecnica usada em `/Users/eder/Projects/money`, adaptada ao dominio deste projeto.

### 6.1 Stack principal

Frontend:

- React 19
- TypeScript
- Vite
- React Router
- Tailwind CSS

Backend:

- Python 3.12+
- FastAPI
- Pydantic / pydantic-settings
- SQLAlchemy 2 async
- aiosqlite
- Alembic

Qualidade e operacao:

- pytest
- Ruff
- Makefile
- docker-compose opcional para ambiente local

### 6.2 Estrutura de repositorio alvo

```text
friends/
  PRD.md
  progress.txt
  Makefile
  docker-compose.yml
  .env.example
  frontend/
    package.json
    vite.config.ts
    tsconfig.json
    src/
      main.tsx
      App.tsx
      index.css
      pages/
      components/
      hooks/
      services/
      types/
  backend/
    pyproject.toml
    alembic.ini
    app/
      main.py
      config.py
      database.py
      models/
      schemas/
      routers/
      services/
      tasks/
    alembic/
      env.py
      versions/
    tests/
```

### 6.3 Diretrizes arquiteturais

- frontend e backend devem ficar separados, como no projeto `money`
- frontend conversa com backend via API HTTP
- backend concentra regras de negocio, persistencia e integracoes externas
- SQLite sera o banco oficial da v1
- migrations devem ser feitas com Alembic, mesmo usando SQLite
- testes do backend devem cobrir regras de dominio, parsers e integracoes adaptadas
- o frontend deve ser organizado por `pages`, `components`, `hooks`, `services` e `types`

## 7. Dominio funcional

### 7.1 Categorias

- `rekindle`: amizades antigas que precisam ser reacendidas
- `upgrade`: conhecidos ou colegas com potencial de amizade real
- `maintain`: amizades importantes que precisam de constancia

### 7.2 Cadencias

- `weekly`: 7 dias
- `biweekly`: 14 dias
- `monthly`: 30 dias
- `quarterly`: 90 dias

### 7.3 Temperatura da amizade

Formula base:

`temperatura = max(0, min(100, (1 - dias_sem_contato / (cadencia_dias * 2.5)) * 100))`

Faixas:

- 75 a 100: Quente
- 50 a 74: Morna
- 25 a 49: Esfriando
- 0 a 24: Fria

Casos de borda:

- se `last_contact_at` for nulo (amigo recem-criado), usar `created_at` como referencia para `dias_sem_contato`
- se `created_at` tambem nao estiver disponivel, tratar temperatura como 100 (neutro, sem alarme)
- calculo deve usar timezone fixo `America/Sao_Paulo` para evitar oscilacao na fronteira do dia

### 7.4 Papel do Evernote

- manter uma nota por amigo, identificada pela convencao de titulo `Friends: {nome}`
- appendar entradas de historico sempre que houver nova interacao no Friends
- integracao feita via webhook do IFTTT, sem uso direto da API do Evernote
- o Friends nao le notas do Evernote; a integracao e one-way (so escrita)
- se a primeira nota de um amigo for criada pelo IFTTT, o bloco de metadados vai na primeira entrada; atualizacoes de metadados depois nao se refletem retroativamente

### 7.5 Papel do Google Calendar

- gerar lembretes coerentes com a cadencia das amizades
- ajudar o usuario a agir no momento certo
- nao servir como fonte de verdade do historico

## 8. Modelo de dados inicial

### 8.1 Tabela `friends`

Campos previstos:

- `id`
- `name`
- `phone`
- `email`
- `birthday`
- `category`
- `cadence`
- `notes`
- `last_contact_at` (nullable; amigos recem-criados podem nao ter contato registrado)
- `created_at`
- `updated_at`

Observacao: nao ha campo `evernote_note_id` porque a integracao via IFTTT nao retorna id da nota. A nota e identificada pela convencao de titulo.

### 8.2 Tabela `friend_tags`

Campos previstos:

- `id`
- `friend_id`
- `tag`
- `created_at`

### 8.3 Tabela `interactions`

Campos previstos:

- `id`
- `friend_id`
- `occurred_at`
- `note`
- `interaction_type`
- `created_at`

### 8.4 Tabela `sync_events`

Campos previstos:

- `id`
- `provider`
- `entity_type`
- `entity_id`
- `action`
- `status`
- `external_id`
- `payload_json`
- `error_message`
- `created_at`
- `updated_at`

### 8.5 Tabela `calendar_links`

Campos previstos:

- `id`
- `friend_id`
- `provider`
- `external_event_id`
- `last_synced_at`
- `created_at`
- `updated_at`

## 9. API inicial desejada

### 9.1 Friends

- `GET /api/friends`
- `POST /api/friends`
- `GET /api/friends/{friend_id}`
- `PATCH /api/friends/{friend_id}`
- `DELETE /api/friends/{friend_id}`

### 9.2 Interactions

- `POST /api/friends/{friend_id}/interactions`
- `GET /api/friends/{friend_id}/interactions`

### 9.3 Tags e interesses

- `POST /api/friends/{friend_id}/tags`
- `DELETE /api/friends/{friend_id}/tags/{tag}`
- `GET /api/interests`

### 9.4 Dashboard

- `GET /api/dashboard/summary`
- `GET /api/dashboard/overdue`
- `GET /api/dashboard/clusters`

### 9.5 Importacao

- `POST /api/import/csv/preview`
- `POST /api/import/csv/commit`
- `POST /api/import/vcf/preview`
- `POST /api/import/vcf/commit`

### 9.6 Integracoes

- `POST /api/integrations/evernote/friends/{friend_id}/sync` (dispara webhook IFTTT)
- `POST /api/integrations/calendar/friends/{friend_id}/sync`

### 9.7 Formato de erro padrao

Toda resposta de erro deve seguir o formato:

```json
{
  "error": {
    "code": "STRING_CODE",
    "message": "mensagem legivel",
    "details": {}
  }
}
```

Codigos HTTP esperados:

- `400` validacao de payload
- `404` entidade nao encontrada
- `409` conflito (ex: tag duplicada)
- `422` payload valido mas regra de negocio falhou
- `502` falha em integracao externa (IFTTT, Google Calendar)
- `500` erro interno nao esperado

## 10. Telas do frontend

### 10.1 DashboardPage

Deve exibir:

- temperatura media
- total de amigos
- contatos atrasados
- total de interesses
- lista ordenada dos contatos por temperatura
- bloco de atencao imediata
- grupos por interesse

### 10.2 FriendsPage

Deve exibir:

- lista de contatos
- filtros por categoria
- filtros por tag
- acao de novo contato
- acao de importacao

### 10.3 FriendDetailPage

Deve exibir:

- cabecalho do contato
- estatisticas basicas
- tags e interesses
- ganchos de conversa
- notas
- formulario de nova interacao
- historico de interacoes

### 10.4 InterestsPage

Deve exibir:

- lista de interesses com contagem
- clusters de amigos por interesse
- interesses unicos

## 11. Integracao com Evernote (via IFTTT)

A integracao com Evernote sera feita via webhook do IFTTT. O Friends nao fala com a API do Evernote diretamente, o que elimina a necessidade de OAuth, tokens de refresh e biblioteca oficial.

Estrategia:

- o usuario configura um applet IFTTT do tipo `Webhooks (Receive a web request) -> Evernote (Append to note)`
- o applet deve usar o evento `friends_log` (nome sugerido, configuravel)
- o applet usa `{{Value1}}` como titulo da nota e `{{Value2}}` como corpo a ser appendado
- o backend dispara POST para `https://maker.ifttt.com/trigger/{event}/with/key/{IFTTT_WEBHOOK_KEY}` com `value1`, `value2` e opcionalmente `value3`
- convencao de titulo de nota: `Friends: {nome do amigo}`
- falhas de webhook devem gerar registro em `sync_events`
- falhas nao podem impedir gravacao local da interacao

Limitacoes aceitas:

- integracao e one-way (so escrita); o Friends nao le nem busca notas do Evernote
- nao ha captura de id da nota; a nota e identificada pela convencao de titulo
- metadados de cabecalho (telefone, aniversario, tags) entram so na primeira entrada, nao sao atualizados retroativamente
- IFTTT limita a 3 valores por trigger (value1, value2, value3)
- upgrade para API nativa do Evernote fica como fase 2 opcional, caso IFTTT vire limitacao

Formato minimo de cada append (corpo enviado em `value2`):

```text
[YYYY-MM-DD HH:MM] {tipo de interacao}
{nota da interacao}
```

Formato do cabecalho inicial (enviado junto da primeira interacao, em `value2`):

```text
Friends: {nome}
Telefone: {phone} | Aniversario: {birthday}
Categoria: {category} | Cadencia: {cadence}
Tags: {tags separadas por virgula}

---

[YYYY-MM-DD HH:MM] {tipo de interacao}
{nota da interacao}
```

## 12. Integracao com Google Calendar

Estrategia definida:

- sera criado um evento por contato, nao uma rotina central de revisao
- cada sincronizacao considera a cadencia configurada e a data do ultimo contato
- o backend cria ou atualiza o evento vinculado ao amigo
- o mapeamento local x evento externo e persistido em `calendar_links`
- falhas nao podem impedir gravacao local da interacao
- apos registrar nova interacao, o evento correspondente deve ser reagendado para `last_contact_at + cadencia`

Autenticacao:

- usar API oficial do Google Calendar com OAuth 2.0
- `GOOGLE_CLIENT_ID` e `GOOGLE_CLIENT_SECRET` ficam em `.env`
- `refresh_token` do usuario fica em arquivo local fora do repo (ex: `~/.friends/google_token.json`) ou em tabela dedicada no SQLite
- fluxo OAuth inicial pode ser CLI (copiar codigo do navegador) dado que o app e pessoal

## 13. Atividades tecnicas

### 13.1 Setup do repositorio

Atividade: avaliar `friends-dashboard.jsx` e extrair parsers de CSV/VCF, lista de tags sugeridas, paleta de cores e logica de temperatura para reaproveitamento na nova estrutura
Feito: Nao

Atividade: arquivar `friends-dashboard.jsx` movendo para `legacy/`
Feito: Sim

Atividade: criar estrutura `frontend/` e `backend/` espelhando o projeto `money`
Feito: Sim

Atividade: criar `frontend/package.json`, `vite.config.ts`, `tsconfig.json` e `src/`
Feito: Sim

Atividade: criar `backend/pyproject.toml`, `app/`, `tests/`, `alembic/` e `alembic.ini`
Feito: Sim

Atividade: criar `Makefile` com comandos de `dev`, `backend`, `frontend`, `lint`, `test`, `migrate`
Feito: Sim

Atividade: criar `.env.example` com variaveis de app, banco e integracoes
Feito: Sim

Atividade: criar `.gitignore` cobrindo `.env`, `.venv`, `node_modules`, `*.db` e `.friends/`
Feito: Sim

### 13.2 Backend base

Atividade: implementar `backend/app/config.py` com `pydantic-settings`
Feito: Sim

Atividade: implementar `backend/app/database.py` com engine async SQLite e session factory
Feito: Sim

Atividade: implementar `backend/app/main.py` com FastAPI, lifespan e healthcheck
Feito: Sim

Atividade: configurar CORS para frontend local
Feito: Sim

Atividade: criar pacote `backend/app/models/`
Feito: Sim

Atividade: criar pacote `backend/app/schemas/`
Feito: Sim

Atividade: criar pacote `backend/app/routers/`
Feito: Sim

Atividade: criar pacote `backend/app/services/`
Feito: Sim

### 13.3 Banco e migrations

Atividade: modelar ORM de `Friend`
Feito: Sim

Atividade: modelar ORM de `FriendTag`
Feito: Sim

Atividade: modelar ORM de `Interaction`
Feito: Sim

Atividade: modelar ORM de `SyncEvent`
Feito: Sim

Atividade: modelar ORM de `CalendarLink`
Feito: Sim

Atividade: criar migration inicial com tabelas principais
Feito: Sim

Atividade: validar criacao de schema em SQLite local
Feito: Sim

### 13.4 Schemas e validacao

Atividade: criar schema de criacao de amigo
Feito: Sim

Atividade: criar schema de atualizacao parcial de amigo
Feito: Sim

Atividade: criar schema de resposta de amigo
Feito: Sim

Atividade: criar schema de criacao de interacao
Feito: Sim

Atividade: criar schema de resposta de dashboard
Feito: Sim

Atividade: criar schema de preview de importacao
Feito: Sim

### 13.5 Regras de dominio

Atividade: implementar calculo de temperatura em servico dedicado
Feito: Sim

Atividade: implementar calculo de `days_since_last_contact`
Feito: Sim

Atividade: implementar calculo de `days_until_next_ping`
Feito: Sim

Atividade: implementar agregacao de clusters por interesse
Feito: Sim

Atividade: implementar geracao de ganchos de conversa a partir de tags compartilhadas
Feito: Sim

### 13.6 API de amigos

Atividade: implementar router `GET /api/friends`
Feito: Sim

Atividade: implementar router `POST /api/friends`
Feito: Sim

Atividade: implementar router `GET /api/friends/{friend_id}`
Feito: Sim

Atividade: implementar router `PATCH /api/friends/{friend_id}`
Feito: Sim

Atividade: implementar router `DELETE /api/friends/{friend_id}`
Feito: Sim

### 13.7 API de interacoes

Atividade: implementar router `POST /api/friends/{friend_id}/interactions`
Feito: Sim

Atividade: implementar persistencia local de nova interacao
Feito: Sim

Atividade: atualizar `last_contact_at` ao registrar interacao
Feito: Sim

Atividade: implementar router `GET /api/friends/{friend_id}/interactions`
Feito: Sim

### 13.8 API de dashboard

Atividade: implementar router `GET /api/dashboard/summary`
Feito: Sim

Atividade: implementar router `GET /api/dashboard/overdue`
Feito: Sim

Atividade: implementar router `GET /api/dashboard/clusters`
Feito: Sim

### 13.9 API de interesses

Atividade: implementar router `GET /api/interests`
Feito: Sim

Atividade: implementar router `POST /api/friends/{friend_id}/tags`
Feito: Sim

Atividade: implementar router `DELETE /api/friends/{friend_id}/tags/{tag}`
Feito: Sim

### 13.10 Importacao CSV

Atividade: implementar parser de CSV em servico dedicado
Feito: Sim

Atividade: implementar autodeteccao de colunas
Feito: Sim

Atividade: implementar preview de importacao de CSV
Feito: Sim

Atividade: implementar confirmacao de importacao de CSV
Feito: Sim

Atividade: cobrir parser de CSV com testes
Feito: Sim

### 13.11 Importacao VCF

Atividade: implementar parser basico de VCF
Feito: Sim

Atividade: implementar preview de importacao de VCF
Feito: Sim

Atividade: implementar confirmacao de importacao de VCF
Feito: Sim

Atividade: cobrir parser de VCF com testes
Feito: Sim

### 13.12 Integracao Evernote via IFTTT

Atividade: definir variaveis `IFTTT_WEBHOOK_KEY` e `IFTTT_EVENT_NAME` no `.env.example`
Feito: Nao

Atividade: implementar cliente IFTTT em `services/ifttt_client.py` com POST para webhook
Feito: Nao

Atividade: implementar servico de sync de interacao (monta titulo `Friends: {nome}` e corpo padrao)
Feito: Nao

Atividade: registrar falhas de sync em `sync_events` sem impedir gravacao local
Feito: Nao

Atividade: cobrir cliente IFTTT e servico de sync com testes (mockando webhook)
Feito: Nao

### 13.13 Integracao Google Calendar

Atividade: definir `GOOGLE_CLIENT_ID` e `GOOGLE_CLIENT_SECRET` no `.env.example`
Feito: Nao

Atividade: implementar fluxo OAuth inicial via CLI e salvar `refresh_token` em arquivo local fora do repo
Feito: Nao

Atividade: implementar cliente de Google Calendar em `services/calendar_client.py`
Feito: Nao

Atividade: implementar criacao de evento por contato vinculado a amigo
Feito: Nao

Atividade: implementar reagendamento de evento apos nova interacao (last_contact_at + cadencia)
Feito: Nao

Atividade: persistir `external_event_id` em `calendar_links`
Feito: Nao

Atividade: cobrir cliente de Calendar com testes mockando API externa
Feito: Nao

### 13.14 Frontend base

Atividade: criar app React com TypeScript e Vite em `frontend/`
Feito: Sim

Atividade: configurar React Router em `src/App.tsx`
Feito: Sim

Atividade: configurar Tailwind CSS
Feito: Sim

Atividade: criar `src/services/api.ts`
Feito: Sim

Atividade: criar `src/types/`
Feito: Sim

Atividade: criar layout base da aplicacao
Feito: Sim

### 13.15 Frontend dashboard

Atividade: criar `DashboardPage`
Feito: Sim

Atividade: criar componente de resumo estatistico
Feito: Sim

Atividade: criar lista de temperatura das amizades
Feito: Sim

Atividade: criar bloco de contatos atrasados
Feito: Sim

Atividade: criar bloco de clusters por interesse
Feito: Sim

### 13.16 Frontend contatos

Atividade: criar `FriendsPage`
Feito: Sim

Atividade: criar lista de cards de amigos
Feito: Sim

Atividade: criar filtros por categoria
Feito: Sim

Atividade: criar filtros por tag
Feito: Sim

Atividade: criar modal ou formulario de novo contato
Feito: Sim

Atividade: criar fluxo de edicao de contato
Feito: Sim

### 13.17 Frontend detalhe do contato

Atividade: criar `FriendDetailPage`
Feito: Sim

Atividade: criar header com categoria, cadencia e temperatura
Feito: Sim

Atividade: criar secao de notas do contato
Feito: Sim

Atividade: criar secao de tags com adicao e remocao
Feito: Sim

Atividade: criar formulario rapido de interacao
Feito: Sim

Atividade: criar timeline de historico
Feito: Sim

Atividade: criar bloco de ganchos de conversa
Feito: Sim

### 13.18 Frontend interesses

Atividade: criar `InterestsPage`
Feito: Sim

Atividade: criar lista de interesses com contagem
Feito: Sim

Atividade: criar lista de clusters por interesse
Feito: Sim

Atividade: criar bloco de interesses unicos
Feito: Sim

### 13.19 Frontend importacao

Atividade: criar modal de importacao
Feito: Nao

Atividade: criar etapa de upload
Feito: Nao

Atividade: criar etapa de mapeamento de CSV
Feito: Nao

Atividade: criar etapa de selecao de contatos
Feito: Nao

Atividade: criar etapa de confirmacao
Feito: Nao

### 13.20 Testes

Atividade: configurar pytest no backend
Feito: Sim

Atividade: criar `conftest.py` inicial
Feito: Sim

Atividade: testar calculo de temperatura
Feito: Sim

Atividade: testar CRUD de amigos
Feito: Sim

Atividade: testar registro de interacao
Feito: Sim

Atividade: testar parser de CSV
Feito: Nao

Atividade: testar parser de VCF
Feito: Nao

Atividade: testar fluxo de append no Evernote com mocks
Feito: Nao

### 13.21 Operacao e DX

Atividade: criar script de inicializacao local via `Makefile`
Feito: Nao

Atividade: criar comando de migration
Feito: Nao

Atividade: criar comando de testes
Feito: Nao

Atividade: criar comando de lint
Feito: Nao

Atividade: documentar setup local minimo no `README` quando o app real existir
Feito: Nao

## 14. Ordem recomendada de implementacao

1. Estruturar repositorio real com frontend e backend.
2. Subir backend FastAPI com SQLite e migration inicial.
3. Implementar modelos, schemas e CRUD de amigos.
4. Implementar registro de interacoes e calculos de dashboard.
5. Subir frontend com rotas e consumir API real.
6. Implementar importacao CSV e VCF.
7. Integrar Evernote com append de historico.
8. Integrar Google Calendar.
9. Refinar UX e cobertura de testes.

## 15. Criterios de sucesso do MVP

- o usuario consegue cadastrar, editar e remover amigos
- o usuario consegue registrar interacoes rapidamente
- o dashboard mostra quem precisa de atencao
- o app persiste tudo em SQLite local
- o app consegue sincronizar historico de interacoes com Evernote
- o app consegue criar ou atualizar lembretes no Google Calendar
- o fluxo inteiro continua util mesmo quando integracoes externas falham
