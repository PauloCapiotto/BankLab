# BankLab Fase 1 — Fundação: Plano De Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Criar o monorepo BankLab com Docker Compose, frontend Next.js mínimo, backend FastAPI mínimo e healthchecks funcionando.

**Architecture:** Monorepo com `apps/web` (Next.js) e `apps/api` (FastAPI), orquestrado por `docker-compose.yml` na raiz com Postgres 16 e Redis 7. Nesta fase só existe o esqueleto: API responde `/health`, web responde na porta 3000, bancos sobem com healthcheck.

**Tech Stack:** Next.js 14 (App Router), TypeScript strict, Tailwind CSS 3.4, FastAPI, Python 3.12, PostgreSQL 16, Redis 7, Docker Compose.

**Regras de commit (obrigatórias, do CLAUDE.md):** Conventional Commits em português. NUNCA adicionar `Co-Authored-By: Claude`, "Generated with Claude" ou qualquer referência à Anthropic. Autoria apenas de Paulo Capiotto.

**Referências:** `docs/PRD.md` e `docs/superpowers/specs/2026-06-10-banklab-design.md`.

---

### Task 1: Arquivos raiz e serviços de dados (Postgres + Redis)

**Files:**
- Create: `.env.example`
- Create: `infra/docker/postgres-init.sql`
- Create: `docker-compose.yml`

- [ ] **Step 1: Criar `.env.example`**

```env
POSTGRES_DB=banklab
POSTGRES_USER=banklab
POSTGRES_PASSWORD=banklab
DATABASE_URL=postgresql+asyncpg://banklab:banklab@postgres:5432/banklab
REDIS_URL=redis://redis:6379/0
JWT_SECRET=change-me-local-secret
JWT_EXPIRES_IN_MINUTES=60
API_PORT=8000
WEB_PORT=3000
NEXT_PUBLIC_API_URL=http://localhost:8000
```

- [ ] **Step 2: Criar `infra/docker/postgres-init.sql`**

Cria o banco de testes usado pelos testes de integração do backend (Fase 2):

```sql
CREATE DATABASE banklab_test OWNER banklab;
```

- [ ] **Step 3: Criar `docker-compose.yml` com postgres e redis**

```yaml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-banklab}
      POSTGRES_USER: ${POSTGRES_USER:-banklab}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-banklab}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./infra/docker/postgres-init.sql:/docker-entrypoint-initdb.d/init.sql:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U banklab -d banklab"]
      interval: 5s
      timeout: 3s
      retries: 10

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 10

volumes:
  postgres_data:
```

- [ ] **Step 4: Criar `.env` local e subir os serviços**

```bash
cp .env.example .env
docker compose up -d postgres redis
```

- [ ] **Step 5: Verificar healthchecks**

Run: `docker compose ps`
Expected: `postgres` e `redis` com status `Up (healthy)` (aguarde alguns segundos se aparecer `health: starting`).

Run: `docker compose exec postgres psql -U banklab -c '\l' | grep banklab_test`
Expected: linha contendo `banklab_test`.

- [ ] **Step 6: Commit**

```bash
git add .env.example infra/docker/postgres-init.sql docker-compose.yml
git commit -m "feat: adiciona docker compose com postgres e redis"
```

---

### Task 2: Backend FastAPI mínimo com `/health`

**Files:**
- Create: `apps/api/pyproject.toml`
- Create: `apps/api/app/__init__.py`
- Create: `apps/api/app/core/__init__.py`
- Create: `apps/api/app/core/config.py`
- Create: `apps/api/app/main.py`
- Create: `apps/api/tests/__init__.py`
- Create: `apps/api/tests/test_health.py`
- Create: `apps/api/Dockerfile`
- Create: `apps/api/.dockerignore`
- Modify: `docker-compose.yml` (adicionar serviço `api`)

- [ ] **Step 1: Criar `apps/api/pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "banklab-api"
version = "1.0.0"
description = "API do BankLab"
requires-python = ">=3.12"
dependencies = [
    "fastapi==0.115.6",
    "uvicorn[standard]==0.32.1",
    "sqlalchemy[asyncio]==2.0.36",
    "asyncpg==0.30.0",
    "alembic==1.14.0",
    "pydantic==2.10.3",
    "pydantic-settings==2.6.1",
    "PyJWT==2.10.1",
    "bcrypt==4.2.1",
    "redis==5.2.1",
]

[project.optional-dependencies]
dev = [
    "pytest==8.3.4",
    "pytest-asyncio==0.24.0",
    "httpx==0.28.1",
]

[tool.setuptools.packages.find]
include = ["app*"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
```

- [ ] **Step 2: Criar `apps/api/app/__init__.py` e `apps/api/app/core/__init__.py`**

Ambos vazios:

```python
```

- [ ] **Step 3: Criar `apps/api/app/core/config.py`**

Os nomes dos campos mapeiam automaticamente para as variáveis de ambiente em maiúsculas (`DATABASE_URL`, `REDIS_URL`, etc.):

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://banklab:banklab@localhost:5432/banklab"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "change-me-local-secret"
    jwt_expires_in_minutes: int = 60
    testing: bool = False


settings = Settings()
```

- [ ] **Step 4: Criar `apps/api/app/main.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="BankLab API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
```

- [ ] **Step 5: Escrever o teste de health (falhando primeiro só se preferir; aqui o app já existe, então o teste valida o harness)**

`apps/api/tests/__init__.py` vazio.

`apps/api/tests/test_health.py`:

```python
import httpx

from app.main import app


async def test_health_retorna_ok():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 6: Criar venv local, instalar e rodar o teste**

```bash
cd apps/api
python3.12 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/pytest tests/test_health.py -v
```

Expected: `1 passed`.

- [ ] **Step 7: Criar `apps/api/Dockerfile`**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml ./
COPY app ./app

RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 8: Criar `apps/api/.dockerignore`**

```text
.venv
__pycache__
.pytest_cache
tests
```

- [ ] **Step 9: Adicionar serviço `api` ao `docker-compose.yml`**

Adicionar dentro de `services:` (manter postgres e redis como estão):

```yaml
  api:
    build: ./apps/api
    environment:
      DATABASE_URL: postgresql+asyncpg://banklab:banklab@postgres:5432/banklab
      REDIS_URL: redis://redis:6379/0
      JWT_SECRET: ${JWT_SECRET:-change-me-local-secret}
      JWT_EXPIRES_IN_MINUTES: ${JWT_EXPIRES_IN_MINUTES:-60}
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
```

- [ ] **Step 10: Subir e verificar**

```bash
docker compose up -d --build api
```

Run: `curl -s http://localhost:8000/health`
Expected: `{"status":"ok"}`

Run: `curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/docs`
Expected: `200` (documentação OpenAPI acessível).

- [ ] **Step 11: Commit**

```bash
git add apps/api docker-compose.yml
git commit -m "feat: adiciona backend fastapi minimo com health e docs"
```

---

### Task 3: Frontend Next.js mínimo

**Files:**
- Create: `apps/web/package.json`
- Create: `apps/web/tsconfig.json`
- Create: `apps/web/next.config.mjs`
- Create: `apps/web/postcss.config.mjs`
- Create: `apps/web/tailwind.config.ts`
- Create: `apps/web/app/layout.tsx`
- Create: `apps/web/app/globals.css`
- Create: `apps/web/app/page.tsx`
- Create: `apps/web/next-env.d.ts`
- Create: `apps/web/Dockerfile`
- Create: `apps/web/.dockerignore`
- Modify: `docker-compose.yml` (adicionar serviço `web`)

- [ ] **Step 1: Criar `apps/web/package.json`**

Todas as dependências da v1 já entram aqui para evitar retrabalho nas fases seguintes:

```json
{
  "name": "banklab-web",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "test": "vitest run"
  },
  "dependencies": {
    "next": "14.2.20",
    "react": "18.3.1",
    "react-dom": "18.3.1",
    "react-hook-form": "7.54.2",
    "@hookform/resolvers": "3.9.1",
    "zod": "3.24.1",
    "lucide-react": "0.468.0"
  },
  "devDependencies": {
    "typescript": "5.7.2",
    "@types/node": "22.10.2",
    "@types/react": "18.3.12",
    "@types/react-dom": "18.3.1",
    "tailwindcss": "3.4.17",
    "postcss": "8.4.49",
    "autoprefixer": "10.4.20",
    "vitest": "2.1.8",
    "@vitejs/plugin-react": "4.3.4",
    "jsdom": "25.0.1",
    "@testing-library/react": "16.1.0",
    "@testing-library/user-event": "14.5.2",
    "@testing-library/jest-dom": "6.6.3"
  }
}
```

- [ ] **Step 2: Criar `apps/web/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": false,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

- [ ] **Step 3: Criar `apps/web/next.config.mjs`, `apps/web/postcss.config.mjs` e `apps/web/next-env.d.ts`**

`next.config.mjs`:

```js
/** @type {import('next').NextConfig} */
const nextConfig = {};

export default nextConfig;
```

`postcss.config.mjs`:

```js
/** @type {import('postcss-load-config').Config} */
const config = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};

export default config;
```

`next-env.d.ts`:

```ts
/// <reference types="next" />
/// <reference types="next/image-types/global" />
```

- [ ] **Step 4: Criar `apps/web/tailwind.config.ts` com os tokens da direção visual aprovada**

Tokens vêm da seção 9 da spec (`text` vira `ink` e `border` vira `border-warm` para não colidir com utilitários do Tailwind):

```ts
import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "#fff8f1",
        surface: "#ffffff",
        "surface-warm": "#fff4ec",
        primary: { DEFAULT: "#ef6a3a", dark: "#b94f2d" },
        copper: "#74311f",
        brown: "#4a2117",
        success: { DEFAULT: "#237a4b", soft: "#dcfce7" },
        danger: { DEFAULT: "#b94122", soft: "#ffdfd2" },
        ink: "#22130f",
        muted: "#7f6a60",
        "border-warm": "#f1d8c8",
      },
      fontFamily: {
        display: ["var(--font-bricolage)", "sans-serif"],
        sans: ["var(--font-jakarta)", "sans-serif"],
      },
      borderRadius: {
        card: "1.25rem",
      },
    },
  },
  plugins: [],
};

export default config;
```

- [ ] **Step 5: Criar `apps/web/app/globals.css`**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

body {
  background-color: #fff8f1;
  background-image:
    radial-gradient(at 0% 0%, rgba(239, 106, 58, 0.06) 0px, transparent 50%),
    radial-gradient(at 100% 100%, rgba(116, 49, 31, 0.05) 0px, transparent 50%);
  color: #22130f;
}
```

- [ ] **Step 6: Criar `apps/web/app/layout.tsx` com as fontes aprovadas**

```tsx
import type { Metadata } from "next";
import { Bricolage_Grotesque, Plus_Jakarta_Sans } from "next/font/google";
import "./globals.css";

const bricolage = Bricolage_Grotesque({
  subsets: ["latin"],
  variable: "--font-bricolage",
});

const jakarta = Plus_Jakarta_Sans({
  subsets: ["latin"],
  variable: "--font-jakarta",
});

export const metadata: Metadata = {
  title: "BankLab",
  description: "Internet banking BankLab",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="pt-BR">
      <body className={`${bricolage.variable} ${jakarta.variable} font-sans antialiased`}>
        {children}
      </body>
    </html>
  );
}
```

- [ ] **Step 7: Criar `apps/web/app/page.tsx` (placeholder; na Fase 3 vira redirect para `/login`)**

```tsx
export default function HomePage() {
  return (
    <main className="flex min-h-screen items-center justify-center">
      <h1 className="font-display text-4xl font-bold text-primary">BankLab</h1>
    </main>
  );
}
```

- [ ] **Step 8: Instalar dependências e validar o build local**

```bash
cd apps/web
npm install
npm run build
```

Expected: build conclui sem erros (`✓ Compiled successfully`).

- [ ] **Step 9: Criar `apps/web/Dockerfile` e `apps/web/.dockerignore`**

`Dockerfile`:

```dockerfile
FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

ENV NEXT_PUBLIC_API_URL=http://localhost:8000
RUN npm run build

EXPOSE 3000

CMD ["npm", "run", "start"]
```

`.dockerignore`:

```text
node_modules
.next
```

- [ ] **Step 10: Adicionar serviço `web` ao `docker-compose.yml`**

Adicionar dentro de `services:`:

```yaml
  web:
    build: ./apps/web
    ports:
      - "3000:3000"
    depends_on:
      - api
```

- [ ] **Step 11: Subir e verificar**

```bash
docker compose up -d --build web
```

Run: `curl -s -o /dev/null -w "%{http_code}" http://localhost:3000`
Expected: `200`

- [ ] **Step 12: Commit**

```bash
git add apps/web docker-compose.yml
git commit -m "feat: adiciona frontend nextjs minimo com tema visual"
```

---

### Task 4: README inicial

**Files:**
- Create: `README.md`

- [ ] **Step 1: Criar `README.md`**

````markdown
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
````

- [ ] **Step 2: Verificar subida completa do zero**

```bash
docker compose down
docker compose up -d --build
docker compose ps
```

Expected: `postgres` e `redis` com `Up (healthy)`; `api` e `web` com `Up`.

Run: `curl -s http://localhost:8000/health && curl -s -o /dev/null -w "%{http_code}\n" http://localhost:3000`
Expected: `{"status":"ok"}200`

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: adiciona readme inicial com instrucoes de uso"
```

---

## Critérios de conclusão da Fase 1

- `docker compose up -d --build` sobe os 4 serviços.
- Postgres e Redis ficam `healthy`.
- `GET /health` responde `{"status":"ok"}`.
- `GET /docs` responde 200.
- Frontend responde 200 na porta 3000.
- `pytest` passa no backend.
- Nenhum segredo real versionado (`.env` está no `.gitignore`).
