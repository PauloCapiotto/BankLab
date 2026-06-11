# BankLab Fase 4 — Qualidade: Plano De Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fechar a v1 do BankLab: verificação de infraestrutura automatizada, README completo, revisão visual contra a direção aprovada e validação final de todos os critérios de pronto do PRD.

**Architecture:** Sem código de produto novo — esta fase adiciona um script de verificação de infraestrutura, completa a documentação e executa a validação de aceite ponta a ponta.

**Tech Stack:** Bash, curl, Docker Compose.

**Pré-requisito:** Fases 1, 2 e 3 concluídas.

**Regras de commit (obrigatórias, do CLAUDE.md):** Conventional Commits em português. NUNCA adicionar `Co-Authored-By: Claude`, "Generated with Claude" ou qualquer referência à Anthropic.

---

### Task 1: Script de verificação de infraestrutura

**Files:**
- Create: `scripts/check-infra.sh`

- [ ] **Step 1: Criar `scripts/check-infra.sh`**

Cobre as verificações de infraestrutura da seção 16 da spec (containers, healthchecks, API e frontend respondendo):

```bash
#!/usr/bin/env bash
set -u

PASS=0
FAIL=0

check() {
  local label="$1"
  shift
  if "$@" > /dev/null 2>&1; then
    echo "OK   - $label"
    PASS=$((PASS + 1))
  else
    echo "FALHA - $label"
    FAIL=$((FAIL + 1))
  fi
}

check "postgres healthy" \
  sh -c 'docker compose ps postgres | grep -q "(healthy)"'

check "redis healthy" \
  sh -c 'docker compose ps redis | grep -q "(healthy)"'

check "api respondendo em /health" \
  sh -c 'curl -sf http://localhost:8000/health | grep -q "ok"'

check "api docs (OpenAPI) acessivel" \
  curl -sf -o /dev/null http://localhost:8000/docs

check "frontend respondendo na porta 3000" \
  curl -sf -o /dev/null http://localhost:3000

check "worker rodando" \
  sh -c 'docker compose ps worker | grep -q "Up"'

echo ""
echo "Resultado: $PASS ok, $FAIL falha(s)."
[ "$FAIL" -eq 0 ]
```

- [ ] **Step 2: Tornar executável e rodar**

```bash
chmod +x scripts/check-infra.sh
docker compose up -d --build
./scripts/check-infra.sh
```

Expected:

```text
OK   - postgres healthy
OK   - redis healthy
OK   - api respondendo em /health
OK   - api docs (OpenAPI) acessivel
OK   - frontend respondendo na porta 3000
OK   - worker rodando

Resultado: 6 ok, 0 falha(s).
```

- [ ] **Step 3: Commit**

```bash
git add scripts/check-infra.sh
git commit -m "test: adiciona script de verificacao de infraestrutura"
```

---

### Task 2: README completo

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Substituir `README.md` pelo conteúdo final**

Cobre todos os itens obrigatórios da seção 17 da spec (visão geral, stack, pré-requisitos, `.env`, subida, migrations, seed, clientes, portas, testes, troubleshooting):

````markdown
# BankLab

Aplicação local de internet banking para portfólio. Simula fluxos bancários
realistas: autenticação, contas, depósitos, transferências, extrato,
notificações geradas por eventos e auditoria.

## Stack

- **Frontend:** Next.js (App Router), TypeScript, Tailwind CSS
- **Backend:** FastAPI, Python 3.12, SQLAlchemy 2 (async), Alembic
- **Banco:** PostgreSQL 16
- **Eventos:** Redis Streams (worker de notificações com consumer group)
- **Orquestração:** Docker Compose

## Arquitetura

```text
Browser → Next.js (web) → FastAPI (api) → PostgreSQL
                              └→ Redis Streams → worker → PostgreSQL
```

Depósitos e transferências são atômicos e idempotentes (header
`Idempotency-Key`), publicam eventos no stream `banklab.transactions` e o
worker persiste notificações com deduplicação.

## Pré-requisitos

- Docker e Docker Compose
- (Opcional, para desenvolvimento) Python 3.12 e Node 20

## Configuração

```bash
cp .env.example .env
```

Nenhum segredo real é necessário para uso local; os valores padrão funcionam.

## Como subir

```bash
docker compose up -d --build
```

As migrations rodam automaticamente quando o container da API sobe.

## Seed (dados iniciais)

```bash
docker compose exec api python -m app.seed
```

O seed é idempotente: rodar de novo não duplica dados.

## Clientes iniciais

| Cliente     | E-mail               | Senha        | Conta            |
| ----------- | -------------------- | ------------ | ---------------- |
| Maria Silva | `maria@banklab.local` | `BankLab@123` | ag. 0001, 0042-0 |
| João Souza  | `joao@banklab.local`  | `BankLab@123` | ag. 0001, 0188-3 |

## Portas

| Serviço  | Porta | URL                        |
| -------- | ----- | -------------------------- |
| web      | 3000  | http://localhost:3000      |
| api      | 8000  | http://localhost:8000      |
| api docs | 8000  | http://localhost:8000/docs |
| postgres | 5432  | -                          |
| redis    | 6379  | -                          |

## Migrations (manual, se necessário)

```bash
docker compose exec api alembic upgrade head
```

## Testes

Backend (requer `docker compose up -d postgres`; usa o banco `banklab_test`):

```bash
cd apps/api
python3.12 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/pytest -v
```

Frontend:

```bash
cd apps/web
npm install
npm test
```

Infraestrutura (com tudo no ar):

```bash
./scripts/check-infra.sh
```

## Troubleshooting

- **`api` não sobe / erro de conexão com o banco:** confira se o postgres está
  `healthy` com `docker compose ps`; veja logs com `docker compose logs api`.
- **Login falha com credenciais corretas:** o seed foi executado?
  (`docker compose exec api python -m app.seed`)
- **Notificação de depósito/transferência não aparece:** verifique o worker
  com `docker compose logs worker`; o evento fica no stream
  `banklab.transactions` e é reprocessável com segurança.
- **Testes do backend falham com erro de conexão:** o banco `banklab_test` é
  criado pelo init script do postgres; se o volume é antigo, recrie com
  `docker compose down -v && docker compose up -d`.
- **Porta em uso:** ajuste o mapeamento de portas no `docker-compose.yml`.
- **Resetar tudo:** `docker compose down -v` apaga o volume do banco; suba de
  novo e rode o seed.
````

- [ ] **Step 2: Validar instruções do zero (simulando um avaliador)**

```bash
docker compose down -v
cp .env.example .env
docker compose up -d --build
docker compose exec api python -m app.seed
./scripts/check-infra.sh
```

Expected: tudo sobe, seed roda, 6 verificações ok. Fazer login manual em `http://localhost:3000` com a Maria.

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "docs: completa readme com instrucoes, clientes e troubleshooting"
```

---

### Task 3: Revisão visual contra a direção aprovada

**Files:**
- Modify: arquivos de UI conforme achados (apenas ajustes, sem funcionalidades novas)

- [ ] **Step 1: Percorrer todas as telas e conferir contra o checklist da spec (seções 9 do PRD e da spec)**

Checklist de conferência manual em `http://localhost:3000`:

- [ ] Fundo bege/pêssego (`#fff8f1`) com gradientes radiais sutis.
- [ ] Títulos em Bricolage Grotesque; corpo em Plus Jakarta Sans.
- [ ] Ações primárias em coral (`#ef6a3a`), hover em laranja queimado.
- [ ] Card de saldo em marrom/cobre com bom contraste.
- [ ] Entradas em verde, saídas em laranja/vermelho quente — em `Início` e `Extrato`.
- [ ] Sidebar fixa à esquerda com ícones e item ativo destacado.
- [ ] Página inicial rotulada `Início` (nunca "Dashboard").
- [ ] Cards arredondados (`rounded-card`).
- [ ] Indicador de notificações no topo sem emoji de sino.
- [ ] Badges e textos de listas legíveis (contraste adequado).
- [ ] Layout desktop-first íntegro em 1280px e 1440px.

- [ ] **Step 2: Corrigir desvios encontrados**

Aplicar ajustes pontuais de classe Tailwind nos componentes afetados. Não adicionar funcionalidades.

- [ ] **Step 3: Rodar a suíte de frontend após ajustes**

Run: `cd apps/web && npm test && npm run build`
Expected: tudo verde.

- [ ] **Step 4: Commit (se houver ajustes)**

```bash
git add apps/web
git commit -m "refactor: ajustes visuais conforme direcao aprovada"
```

---

### Task 4: Validação final dos critérios de pronto da v1

- [ ] **Step 1: Subida limpa do zero**

```bash
docker compose down -v
docker compose up -d --build
docker compose exec api python -m app.seed
./scripts/check-infra.sh
```

Expected: 6 verificações ok.

- [ ] **Step 2: Suítes completas**

```bash
cd apps/api && .venv/bin/pytest -v && cd ../..
cd apps/web && npm test && cd ../..
```

Expected: todos os testes passam.

- [ ] **Step 3: Conferir cada critério de pronto da v1 (PRD seção 17 / spec seção 18)**

- [ ] `docker compose up` sobe todos os serviços.
- [ ] Login funciona com usuário seedado (Maria e João).
- [ ] `Início` exibe dados agregados (saldo, entradas, saídas, movimentações, contador).
- [ ] Contas são listadas com agência, número, tipo, status e saldo.
- [ ] Depósito atualiza saldo e gera notificação (via worker).
- [ ] Transferência atualiza os dois saldos e gera notificações para remetente e destinatário.
- [ ] Extrato lista e filtra movimentações (período, tipo, status, busca) com estado vazio.
- [ ] Notificações podem ser marcadas como lidas.
- [ ] Retentativa de depósito/transferência com a mesma `Idempotency-Key` não duplica (testes das Tasks 7–8 da Fase 2).
- [ ] Valores financeiros mantêm precisão decimal (testes de precisão da Fase 2).
- [ ] README permite rodar o projeto do zero (validado na Task 2).
- [ ] UI segue a direção visual aprovada (validado na Task 3).
- [ ] Não existe projeto Playwright dentro do repositório: `! grep -ri playwright apps package*.json 2>/dev/null` não retorna nada.

- [ ] **Step 4: Atualizar a seção "Status" do README**

Remover a seção `## Status` provisória da Fase 1 (a v1 está completa; o README final da Task 2 já não deve contê-la — conferir).

- [ ] **Step 5: Commit final**

```bash
git add -A
git commit -m "chore: validacao final da v1"
```

(Se não houver mudanças pendentes, pular.)

---

## Critérios de conclusão da Fase 4 (= v1 pronta)

- Script `scripts/check-infra.sh` passa com tudo no ar.
- README cobre todos os itens da seção 17 da spec.
- Checklist visual da direção aprovada conferido.
- Todos os critérios de pronto do PRD (seção 17) marcados.
- Suítes de backend e frontend verdes.
