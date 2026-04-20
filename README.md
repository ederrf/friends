# Friends

App pessoal para manter e aprofundar amizades. Lista contatos, registra
interações, calcula quem está "esfriando" e sugere ganchos de conversa a
partir de interesses compartilhados.

Stack: **FastAPI + SQLite (SQLAlchemy async)** no backend, **React 19 +
Vite + Tailwind v4** no frontend. Tudo roda localmente.

Visão de produto e arquitetura completas em [`PRD.md`](./PRD.md). Histórico
operacional em [`progress.txt`](./progress.txt).

## Funcionalidades

- cadastro de amigos com tags, cadência e notas
- registro rápido de interações (mensagem, call, presencial, email, outro)
- dashboard com temperatura média, contatos atrasados, clusters por tag
- ganchos de conversa derivados de tags compartilhadas
- importação em massa a partir de **CSV** (Google Contacts, Outlook,
  planilha) ou **VCF** (vCard 2.1/3.0) com mapeamento editável

## Requisitos

- Python 3.11+
- Node.js 20.19+ ou 22.12+
- `make` (opcional, só para atalhos)

## Setup rápido

```bash
# 1. instalar dependências (backend + frontend)
make install

# 2. rodar migrações
make migrate

# 3. subir backend e frontend em paralelo
make dev
```

Backend em http://localhost:8000 (Swagger em `/docs`), frontend em
http://localhost:5173 (proxy `/api` aponta pro backend).

## Comandos disponíveis

```bash
make dev         # backend + frontend concorrentes
make backend     # só backend (uvicorn com reload)
make frontend    # só frontend (vite dev)

make install     # instala dependências dos dois lados
make migrate     # alembic upgrade head
make migration MSG="titulo"  # nova revisão autogen

make test        # pytest no backend
make lint        # ruff + eslint
make format      # ruff format

make help        # lista todos os targets
```

## Estrutura

```
friends/
├── backend/            # FastAPI + SQLAlchemy async
│   ├── app/
│   │   ├── models/     # ORM (Friend, FriendTag, Interaction)
│   │   ├── schemas/    # Pydantic v2 (friend, interaction, dashboard, import)
│   │   ├── services/   # regra de domínio (friendship, import, dashboard, ...)
│   │   └── routers/    # adaptadores HTTP (friends, interactions, dashboard, import, ...)
│   ├── alembic/        # migrations
│   └── tests/          # pytest-asyncio + httpx ASGITransport
├── frontend/           # React 19 + Vite + Tailwind v4
│   └── src/
│       ├── pages/      # Dashboard / Friends / FriendDetail / Interests
│       ├── components/ # Modal, TagsEditor, ImportModal, ...
│       ├── services/   # clientes HTTP tipados (friendsApi, importApi, ...)
│       ├── hooks/      # useFetch (data/error/loading/reload)
│       └── types/      # espelho dos schemas Pydantic
├── legacy/             # mockup original (referência visual)
├── Makefile
├── PRD.md              # escopo e arquitetura
└── progress.txt        # histórico de iterações
```

## Formato de erro da API

Toda resposta de erro segue o padrão (PRD §9.7):

```json
{
  "error": {
    "code": "STRING_CODE",
    "message": "mensagem legível",
    "details": {}
  }
}
```

## Testes

```bash
make test
```

Cobertura atual: 137 testes em 6 arquivos (friendship, friends CRUD,
interações, dashboard, interesses, import CSV+VCF).

## Importação

Modal na página de Amigos em 4 etapas:

1. **Upload** — arrasta ou clica pra selecionar `.csv`, `.vcf` ou `.vcard`
2. **Mapeamento** (CSV) — revisa o mapping sugerido (autodeteção cobre
   Google/Outlook em pt-BR e en)
3. **Seleção** — marca quais contatos importar, define categoria e cadência padrão
4. **Resultado** — mostra `imported`/`skipped` e até 10 erros por linha

Backend é stateless: o arquivo é re-parseado entre preview e commit.

## Escopo não implementado (adiado)

- integração com Evernote via IFTTT (PRD §13.12)
- integração com Google Calendar (PRD §13.13)

Ambas são plumbing externo e não bloqueiam o fluxo principal — o app
continua útil sem elas.
