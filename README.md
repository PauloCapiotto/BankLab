# BankLab

Aplicação local de internet banking para portfólio. Simula fluxos bancários
realistas: autenticação, contas, depósitos, transferências, extrato,
notificações e auditoria.

## Stack

- Frontend: Next.js, TypeScript, Tailwind CSS
- Backend: FastAPI, Python, SQLAlchemy, Alembic
- Banco: PostgreSQL
- Eventos: Redis Streams
- Orquestração: Docker Compose

## Pré-requisitos

- Docker e Docker Compose
- (Opcional, para desenvolvimento) Python 3.12 e Node 20

## Como subir

```bash
cp .env.example .env
docker compose up -d --build
```

## Portas

| Serviço  | Porta | URL                        |
| -------- | ----- | -------------------------- |
| web      | 3000  | http://localhost:3000      |
| api      | 8000  | http://localhost:8000      |
| api docs | 8000  | http://localhost:8000/docs |
| postgres | 5432  | -                          |
| redis    | 6379  | -                          |

## Status

Fase 1 (fundação) concluída. Funcionalidades bancárias nas próximas fases.
