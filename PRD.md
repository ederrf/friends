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
- Evernote e obrigatorio no escopo
- Google Calendar continua no escopo
- o MVP sera local-first
- a fonte principal de verdade dos dados sera o proprio Friends
- o Evernote sera inicialmente um destino sincronizado para notas e historico
- nao vamos perseguir sync bidirecional completo com Evernote no inicio

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

### 7.4 Papel do Evernote

- manter uma nota por amigo
- registrar metadados relevantes do contato
- manter uma secao de notas livres
- appendar entradas de historico sempre que houver nova interacao no Friends

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
- `last_contact_at`
- `evernote_note_id`
- `created_at`
- `updated_at`

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

- `POST /api/integrations/evernote/friends/{friend_id}/sync`
- `POST /api/integrations/calendar/friends/{friend_id}/sync`
- `POST /api/integrations/calendar/review-sync`

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

## 11. Integracao com Evernote

Estrategia inicial:

- o backend cria ou localiza uma nota do Evernote para cada amigo
- a nota deve conter um bloco de metadados do contato
- a nota deve conter uma secao `Notas`
- a nota deve conter uma secao `Historico`
- ao registrar uma nova interacao, o backend deve appendar a nova entrada na secao `Historico`
- falhas na sync devem gerar registro em `sync_events`
- falhas na sync nao podem impedir gravacao local da interacao

Formato minimo desejado da nota:

```text
# Nome do amigo
Telefone | Aniversario
Tags
Categoria | Cadencia

## Notas
...

## Historico
- data: descricao da interacao
```

## 12. Integracao com Google Calendar

Estrategia inicial a ser implementada:

- comecar com uma sincronizacao simples de lembretes por contato
- cada sincronizacao deve considerar a cadencia configurada e a data do ultimo contato
- o backend deve conseguir criar ou atualizar o lembrete vinculado ao amigo
- o mapeamento local x evento externo deve ser persistido em `calendar_links`

Decisao tecnica aberta dentro do escopo:

- validar se a primeira versao cria um evento por contato ou uma rotina central de revisao

Essa decisao ainda nao esta fechada, entao continua como atividade tecnica.

## 13. Atividades tecnicas

### 13.1 Setup do repositorio

Atividade: criar estrutura `frontend/` e `backend/` espelhando o projeto `money`
Feito: Nao

Atividade: criar `frontend/package.json`, `vite.config.ts`, `tsconfig.json` e `src/`
Feito: Nao

Atividade: criar `backend/pyproject.toml`, `app/`, `tests/`, `alembic/` e `alembic.ini`
Feito: Nao

Atividade: criar `Makefile` com comandos de `dev`, `backend`, `frontend`, `lint`, `test`, `migrate`
Feito: Nao

Atividade: criar `.env.example` com variaveis de app, banco e integracoes
Feito: Nao

### 13.2 Backend base

Atividade: implementar `backend/app/config.py` com `pydantic-settings`
Feito: Nao

Atividade: implementar `backend/app/database.py` com engine async SQLite e session factory
Feito: Nao

Atividade: implementar `backend/app/main.py` com FastAPI, lifespan e healthcheck
Feito: Nao

Atividade: configurar CORS para frontend local
Feito: Nao

Atividade: criar pacote `backend/app/models/`
Feito: Nao

Atividade: criar pacote `backend/app/schemas/`
Feito: Nao

Atividade: criar pacote `backend/app/routers/`
Feito: Nao

Atividade: criar pacote `backend/app/services/`
Feito: Nao

### 13.3 Banco e migrations

Atividade: modelar ORM de `Friend`
Feito: Nao

Atividade: modelar ORM de `FriendTag`
Feito: Nao

Atividade: modelar ORM de `Interaction`
Feito: Nao

Atividade: modelar ORM de `SyncEvent`
Feito: Nao

Atividade: modelar ORM de `CalendarLink`
Feito: Nao

Atividade: criar migration inicial com tabelas principais
Feito: Nao

Atividade: validar criacao de schema em SQLite local
Feito: Nao

### 13.4 Schemas e validacao

Atividade: criar schema de criacao de amigo
Feito: Nao

Atividade: criar schema de atualizacao parcial de amigo
Feito: Nao

Atividade: criar schema de resposta de amigo
Feito: Nao

Atividade: criar schema de criacao de interacao
Feito: Nao

Atividade: criar schema de resposta de dashboard
Feito: Nao

Atividade: criar schema de preview de importacao
Feito: Nao

### 13.5 Regras de dominio

Atividade: implementar calculo de temperatura em servico dedicado
Feito: Nao

Atividade: implementar calculo de `days_since_last_contact`
Feito: Nao

Atividade: implementar calculo de `days_until_next_ping`
Feito: Nao

Atividade: implementar agregacao de clusters por interesse
Feito: Nao

Atividade: implementar geracao de ganchos de conversa a partir de tags compartilhadas
Feito: Nao

### 13.6 API de amigos

Atividade: implementar router `GET /api/friends`
Feito: Nao

Atividade: implementar router `POST /api/friends`
Feito: Nao

Atividade: implementar router `GET /api/friends/{friend_id}`
Feito: Nao

Atividade: implementar router `PATCH /api/friends/{friend_id}`
Feito: Nao

Atividade: implementar router `DELETE /api/friends/{friend_id}`
Feito: Nao

### 13.7 API de interacoes

Atividade: implementar router `POST /api/friends/{friend_id}/interactions`
Feito: Nao

Atividade: implementar persistencia local de nova interacao
Feito: Nao

Atividade: atualizar `last_contact_at` ao registrar interacao
Feito: Nao

Atividade: implementar router `GET /api/friends/{friend_id}/interactions`
Feito: Nao

### 13.8 API de dashboard

Atividade: implementar router `GET /api/dashboard/summary`
Feito: Nao

Atividade: implementar router `GET /api/dashboard/overdue`
Feito: Nao

Atividade: implementar router `GET /api/dashboard/clusters`
Feito: Nao

### 13.9 API de interesses

Atividade: implementar router `GET /api/interests`
Feito: Nao

Atividade: implementar router `POST /api/friends/{friend_id}/tags`
Feito: Nao

Atividade: implementar router `DELETE /api/friends/{friend_id}/tags/{tag}`
Feito: Nao

### 13.10 Importacao CSV

Atividade: implementar parser de CSV em servico dedicado
Feito: Nao

Atividade: implementar autodeteccao de colunas
Feito: Nao

Atividade: implementar preview de importacao de CSV
Feito: Nao

Atividade: implementar confirmacao de importacao de CSV
Feito: Nao

Atividade: cobrir parser de CSV com testes
Feito: Nao

### 13.11 Importacao VCF

Atividade: implementar parser basico de VCF
Feito: Nao

Atividade: implementar preview de importacao de VCF
Feito: Nao

Atividade: implementar confirmacao de importacao de VCF
Feito: Nao

Atividade: cobrir parser de VCF com testes
Feito: Nao

### 13.12 Integracao Evernote

Atividade: definir variaveis de ambiente para credenciais do Evernote
Feito: Nao

Atividade: implementar cliente de integracao do Evernote em `services/`
Feito: Nao

Atividade: implementar criacao ou localizacao de nota por amigo
Feito: Nao

Atividade: implementar renderizacao do corpo padrao da nota
Feito: Nao

Atividade: implementar append de nova interacao na secao `Historico`
Feito: Nao

Atividade: persistir `evernote_note_id` localmente
Feito: Nao

Atividade: registrar falhas de sync em `sync_events`
Feito: Nao

Atividade: cobrir fluxo de sync com testes de servico
Feito: Nao

### 13.13 Integracao Google Calendar

Atividade: definir variaveis de ambiente para credenciais do Google Calendar
Feito: Nao

Atividade: decidir estrategia inicial de lembrete no Calendar
Feito: Nao

Atividade: implementar cliente de integracao do Google Calendar em `services/`
Feito: Nao

Atividade: implementar criacao de lembrete vinculado a amigo
Feito: Nao

Atividade: implementar atualizacao de lembrete apos nova interacao
Feito: Nao

Atividade: persistir `external_event_id` em `calendar_links`
Feito: Nao

### 13.14 Frontend base

Atividade: criar app React com TypeScript e Vite em `frontend/`
Feito: Nao

Atividade: configurar React Router em `src/App.tsx`
Feito: Nao

Atividade: configurar Tailwind CSS
Feito: Nao

Atividade: criar `src/services/api.ts`
Feito: Nao

Atividade: criar `src/types/`
Feito: Nao

Atividade: criar layout base da aplicacao
Feito: Nao

### 13.15 Frontend dashboard

Atividade: criar `DashboardPage`
Feito: Nao

Atividade: criar componente de resumo estatistico
Feito: Nao

Atividade: criar lista de temperatura das amizades
Feito: Nao

Atividade: criar bloco de contatos atrasados
Feito: Nao

Atividade: criar bloco de clusters por interesse
Feito: Nao

### 13.16 Frontend contatos

Atividade: criar `FriendsPage`
Feito: Nao

Atividade: criar lista de cards de amigos
Feito: Nao

Atividade: criar filtros por categoria
Feito: Nao

Atividade: criar filtros por tag
Feito: Nao

Atividade: criar modal ou formulario de novo contato
Feito: Nao

Atividade: criar fluxo de edicao de contato
Feito: Nao

### 13.17 Frontend detalhe do contato

Atividade: criar `FriendDetailPage`
Feito: Nao

Atividade: criar header com categoria, cadencia e temperatura
Feito: Nao

Atividade: criar secao de notas do contato
Feito: Nao

Atividade: criar secao de tags com adicao e remocao
Feito: Nao

Atividade: criar formulario rapido de interacao
Feito: Nao

Atividade: criar timeline de historico
Feito: Nao

Atividade: criar bloco de ganchos de conversa
Feito: Nao

### 13.18 Frontend interesses

Atividade: criar `InterestsPage`
Feito: Nao

Atividade: criar lista de interesses com contagem
Feito: Nao

Atividade: criar lista de clusters por interesse
Feito: Nao

Atividade: criar bloco de interesses unicos
Feito: Nao

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
Feito: Nao

Atividade: criar `conftest.py` inicial
Feito: Nao

Atividade: testar calculo de temperatura
Feito: Nao

Atividade: testar CRUD de amigos
Feito: Nao

Atividade: testar registro de interacao
Feito: Nao

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
