# Especificação Completa Do BankLab

## 1. Resumo

BankLab é uma aplicação local de internet banking com frontend Next.js, backend FastAPI, PostgreSQL, Redis Streams e Docker Compose. A aplicação simula fluxos bancários realistas para portfólio e preparação futura para automação end-to-end em um projeto separado.

Esta especificação detalha arquitetura, módulos, dados, API, UI, eventos, testes e operação local da v1.

## 2. Decisões Aprovadas

- Nome do projeto: BankLab.
- Pasta principal: `BankLab`.
- Idioma dos documentos e commits: português.
- Autor dos commits: Paulo Capiotto `<ph.capiotto@gmail.com>`.
- Domínio: banco e finanças pessoais.
- Produto: internet banking realista para portfólio.
- UI: desktop-first, amigável, quente e moderna.
- Stack: Next.js, TypeScript, Tailwind, FastAPI, Python, PostgreSQL, Redis Streams e Docker Compose.
- Infra: todos os serviços rodam com Docker Compose.
- Automação: sem Playwright na v1; projeto Playwright será separado futuramente.

## 3. Estrutura Do Repositório

Estrutura alvo:

```text
BankLab/
  apps/
    web/
    api/
  infra/
    docker/
  docs/
    PRD.md
    superpowers/
      specs/
        2026-06-10-banklab-design.md
      plans/
  docker-compose.yml
  .env.example
  .gitignore
  README.md
```

Responsabilidades:

- `apps/web`: frontend Next.js.
- `apps/api`: backend FastAPI.
- `infra/docker`: arquivos auxiliares de Docker, se necessário.
- `docs`: documentação de produto, especificação e planos.
- `docker-compose.yml`: orquestração local.
- `.env.example`: contrato de variáveis de ambiente.
- `README.md`: guia de uso local.

## 4. Arquitetura De Alto Nível

```text
Browser
  |
  v
Next.js web
  |
  v
FastAPI api
  |              |
  v              v
PostgreSQL    Redis Streams
                 |
                 v
          Worker de notificações
                 |
                 v
            PostgreSQL
```

O frontend consome a API REST do backend. O backend concentra autenticação, validação, regras bancárias e persistência. Operações financeiras publicam eventos no Redis Streams. Um worker leve consome eventos e cria notificações persistidas no PostgreSQL.

## 5. Serviços Docker

### `web`

- Executa o frontend Next.js.
- Porta local sugerida: `3000`.
- Depende de `api`.

### `api`

- Executa FastAPI.
- Porta local sugerida: `8000`.
- Expõe documentação em `/docs`.
- Depende de `postgres` e `redis`.

### `postgres`

- Banco relacional principal.
- Porta local sugerida: `5432`.
- Usa volume persistente.
- Deve ter healthcheck.

### `redis`

- Mensageria com Redis Streams.
- Porta local sugerida: `6379`.
- Deve ter healthcheck.

### `worker`

- Consumidor leve de eventos.
- Pode usar o mesmo código base do backend.
- Depende de `postgres` e `redis`.
- Pode ser incluído na v1 se não aumentar demais a complexidade.

## 6. Variáveis De Ambiente

`.env.example` deve conter:

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

Nenhum segredo real deve ser versionado.

## 7. Backend

### Stack

- Python.
- FastAPI.
- Pydantic.
- SQLAlchemy ou SQLModel.
- Alembic para migrations.
- Pytest para testes.
- Passlib ou biblioteca equivalente para hash de senha.
- PyJWT ou python-jose para JWT.
- Redis client assíncrono.

### Organização Sugerida

```text
apps/api/
  app/
    main.py
    core/
      config.py
      security.py
      database.py
      redis.py
    modules/
      auth/
      accounts/
      transactions/
      notifications/
      audit/
    workers/
      notifications_worker.py
  tests/
  alembic/
  pyproject.toml
  Dockerfile
```

### Regras Gerais

- Toda regra financeira crítica deve ficar no backend.
- O frontend não deve ser fonte de verdade para saldo.
- Operações de transferência devem ser transacionais.
- Erros devem retornar estrutura previsível.
- Todos os endpoints autenticados devem validar usuário pelo JWT.
- Valores monetários devem ser tratados no backend com `Decimal`, nunca com `float`.
- Depósitos e transferências devem exigir chave de idempotência para evitar duplicidade em retentativas.
- A v1 usa JWT simples com expiração; refresh token, múltiplos fatores e recuperação de senha ficam fora do escopo.

## 8. Frontend

### Stack

- Next.js.
- TypeScript.
- Tailwind CSS.
- React Hook Form ou solução equivalente para formulários.
- Zod ou validação equivalente no frontend.
- Biblioteca de ícones: preferencialmente `lucide-react`.
- Testes com Vitest e Testing Library.

### Organização Sugerida

```text
apps/web/
  app/
    login/
    inicio/
    contas/
    depositos/
    transferencias/
    extrato/
    notificacoes/
  src/
    components/
    features/
    lib/
    styles/
    types/
  tests/
  package.json
  Dockerfile
```

### Rotas

- `/login`
- `/inicio`
- `/contas`
- `/depositos/novo`
- `/transferencias/nova`
- `/extrato`
- `/notificacoes`

Rotas autenticadas devem redirecionar para `/login` quando não houver sessão válida.

## 9. Direção Visual

### Tipografia

- Títulos: Bricolage Grotesque.
- Corpo: Plus Jakarta Sans.

### Paleta

Tokens sugeridos:

```text
background: #fff8f1
surface: #ffffff
surface-warm: #fff4ec
primary: #ef6a3a
primary-dark: #b94f2d
copper: #74311f
brown: #4a2117
success: #237a4b
success-soft: #dcfce7
danger: #b94122
danger-soft: #ffdfd2
text: #22130f
muted: #7f6a60
border: #f1d8c8
```

### Layout

- Sidebar fixa à esquerda.
- Item ativo: `Início`.
- Cards com raio arredondado.
- Fundo bege/pêssego com gradientes radiais sutis.
- Ações primárias em coral/laranja queimado.
- Cards financeiros com boa hierarquia e contraste.
- Lista de movimentações com texto escuro e badges legíveis.
- Notificação no topo sem emoji de sino.

## 10. Modelo De Dados

### `users`

| Campo | Tipo | Regras |
| --- | --- | --- |
| id | uuid | chave primária |
| name | varchar | obrigatório |
| email | varchar | único, obrigatório |
| password_hash | varchar | obrigatório |
| status | varchar | active, inactive |
| created_at | timestamp | obrigatório |
| updated_at | timestamp | obrigatório |

### `accounts`

| Campo | Tipo | Regras |
| --- | --- | --- |
| id | uuid | chave primária |
| user_id | uuid | FK users |
| branch | varchar | obrigatório |
| number | varchar | único, obrigatório |
| type | varchar | checking, savings |
| balance | numeric(12,2) | não negativo |
| status | varchar | active, blocked, closed |
| created_at | timestamp | obrigatório |
| updated_at | timestamp | obrigatório |

### `transactions`

| Campo | Tipo | Regras |
| --- | --- | --- |
| id | uuid | chave primária |
| account_id | uuid | FK accounts |
| related_account_id | uuid | opcional |
| type | varchar | deposit, transfer_in, transfer_out |
| status | varchar | pending, completed, failed |
| amount | numeric(12,2) | maior que zero |
| description | varchar | opcional |
| idempotency_key | varchar | obrigatório para comandos financeiros; único por usuário/operação |
| created_at | timestamp | obrigatório |
| completed_at | timestamp | opcional |

### `notifications`

| Campo | Tipo | Regras |
| --- | --- | --- |
| id | uuid | chave primária |
| user_id | uuid | FK users |
| type | varchar | transaction, system |
| title | varchar | obrigatório |
| message | text | obrigatório |
| read_at | timestamp | opcional |
| created_at | timestamp | obrigatório |

### `audit_logs`

| Campo | Tipo | Regras |
| --- | --- | --- |
| id | uuid | chave primária |
| actor_user_id | uuid | FK users, opcional |
| action | varchar | obrigatório |
| entity_type | varchar | obrigatório |
| entity_id | uuid | opcional |
| metadata | jsonb | opcional |
| created_at | timestamp | obrigatório |

## 11. Dados Iniciais

O seed da v1 existe para permitir o uso imediato da aplicação após a instalação local. Esses dados representam apenas clientes comuns do BankLab.

O seed deve criar:

- dois usuários clientes;
- contas ativas para os dois clientes;
- algumas transações de entrada e saída;
- algumas notificações;
- saldos coerentes com as transações criadas.

### Maria Silva

- Cliente comum do BankLab.
- E-mail: `maria@banklab.local`
- Senha: `BankLab@123`
- Conta sugerida: agência `0001`, conta `0042-0`.

### João Souza

- Cliente comum do BankLab.
- E-mail: `joao@banklab.local`
- Senha: `BankLab@123`
- Conta sugerida: agência `0001`, conta `0188-3`.

### Movimentações E Notificações

- As transações iniciais devem ser compatíveis com os saldos das contas.
- As notificações iniciais devem estar vinculadas aos clientes e às movimentações criadas.
- Os dados devem popular `Início`, `Extrato` e `Notificações` imediatamente após a primeira execução local.

## 12. API

Todas as respostas de erro devem seguir formato consistente:

```json
{
  "code": "INSUFFICIENT_BALANCE",
  "message": "Saldo insuficiente para concluir a transferência.",
  "details": {}
}
```

Endpoints mutáveis de operação financeira devem receber o header `Idempotency-Key`. A chave deve ser única por usuário e por operação. Se a mesma requisição for repetida com a mesma chave, a API deve retornar o mesmo resultado já persistido, sem criar nova transação ou alterar saldo novamente.

### Autenticação

#### `POST /auth/login`

Request:

```json
{
  "email": "maria@banklab.local",
  "password": "BankLab@123"
}
```

Response:

```json
{
  "access_token": "jwt",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": "uuid",
    "name": "Maria Silva",
    "email": "maria@banklab.local"
  }
}
```

#### `GET /auth/me`

Retorna o usuário autenticado.

Regras de autenticação:

- o token JWT deve conter, no mínimo, `sub`, `exp` e identificador do usuário;
- senhas devem ser armazenadas somente como hash;
- tokens expirados devem retornar erro `401`;
- usuários inativos não devem autenticar;
- refresh token não faz parte da v1.

### Contas

#### `GET /accounts`

Lista contas do usuário autenticado.

#### `GET /accounts/{account_id}`

Retorna detalhe de uma conta do usuário autenticado.

### Início

#### `GET /summary`

Retorna dados agregados para a página `Início`:

```json
{
  "total_balance": 12840.55,
  "monthly_inflow": 4200.00,
  "monthly_outflow": 1380.25,
  "unread_notifications": 3,
  "latest_transactions": []
}
```

### Depósitos

#### `POST /deposits`

Headers:

```http
Idempotency-Key: deposit-unique-client-key
```

Request:

```json
{
  "account_id": "uuid",
  "amount": 1500.00,
  "description": "Depósito simulado"
}
```

Response:

```json
{
  "transaction_id": "uuid",
  "status": "completed",
  "new_balance": 14340.55
}
```

### Transferências

#### `POST /transfers`

Headers:

```http
Idempotency-Key: transfer-unique-client-key
```

Request:

```json
{
  "source_account_id": "uuid",
  "destination_account_number": "0188-3",
  "amount": 250.00,
  "description": "Transferência para João"
}
```

Response:

```json
{
  "transfer_id": "uuid",
  "status": "completed",
  "source_transaction_id": "uuid",
  "destination_transaction_id": "uuid",
  "new_balance": 12590.55
}
```

### Extrato

#### `GET /transactions`

Query params:

- `account_id`
- `from`
- `to`
- `type`
- `status`
- `search`
- `page`
- `page_size`

Response:

```json
{
  "items": [],
  "page": 1,
  "page_size": 20,
  "total": 0
}
```

### Notificações

#### `GET /notifications`

Lista notificações do usuário autenticado.

#### `PATCH /notifications/{notification_id}/read`

Marca uma notificação como lida.

## 13. Eventos Redis Streams

Stream principal:

```text
banklab.transactions
```

O worker de notificações deve usar consumer group, registrar o último processamento no Redis e ser idempotente no banco. Reprocessar o mesmo evento não pode criar notificação duplicada. A chave natural para deduplicação deve considerar `event_type` e identificadores de transação do payload.

Evento de depósito:

```json
{
  "event_type": "transaction.deposit.completed",
  "transaction_id": "uuid",
  "account_id": "uuid",
  "user_id": "uuid",
  "amount": "1500.00",
  "occurred_at": "2026-06-10T12:00:00Z"
}
```

Evento de transferência:

```json
{
  "event_type": "transaction.transfer.completed",
  "source_transaction_id": "uuid",
  "destination_transaction_id": "uuid",
  "source_account_id": "uuid",
  "destination_account_id": "uuid",
  "source_user_id": "uuid",
  "destination_user_id": "uuid",
  "amount": "250.00",
  "occurred_at": "2026-06-10T12:00:00Z"
}
```

## 14. Regras De Negócio

### Depósitos

- Valor deve ser maior que zero.
- Conta deve existir e pertencer ao usuário autenticado.
- Conta deve estar ativa.
- Valor deve ser recebido e processado como `Decimal` com duas casas decimais.
- A operação deve exigir `Idempotency-Key`.
- Repetir a mesma chave de idempotência deve retornar o resultado original sem alterar saldo novamente.
- Operação válida cria transação `deposit` com status `completed`.
- Saldo deve ser atualizado no backend.
- Evento deve ser publicado após persistência bem-sucedida.

### Transferências

- Valor deve ser maior que zero.
- Valor deve ser recebido e processado como `Decimal` com duas casas decimais.
- Conta origem deve pertencer ao usuário autenticado.
- Conta origem deve estar ativa.
- Conta destino deve existir e estar ativa.
- Conta origem e destino não devem ser a mesma.
- Saldo da conta origem deve ser suficiente.
- A operação deve exigir `Idempotency-Key`.
- Repetir a mesma chave de idempotência deve retornar o resultado original sem debitar ou creditar novamente.
- Atualização de saldos e criação das transações devem ocorrer de forma atômica.
- Se qualquer etapa falhar, nenhuma alteração financeira parcial deve permanecer.

### Notificações

- Depósito concluído gera notificação para o dono da conta.
- Transferência enviada gera notificação para remetente.
- Transferência recebida gera notificação para destinatário.
- Notificações devem iniciar como não lidas.
- O worker deve ser idempotente: o mesmo evento processado mais de uma vez não deve gerar notificações duplicadas.
- Falha no worker não deve desfazer a transação financeira já concluída.
- Eventos pendentes devem poder ser reprocessados com segurança.

## 15. Estados De UI

Cada tela relevante deve tratar:

- carregando;
- vazio;
- erro;
- sucesso;
- validação de formulário;
- sessão expirada.

Mensagens devem ser claras e em português.

## 16. Testes

### Backend

Cobertura mínima:

- login válido;
- login inválido;
- login de usuário inativo;
- token expirado;
- rota protegida sem token;
- listagem de contas;
- depósito válido;
- depósito com valor inválido;
- depósito repetido com mesma chave de idempotência;
- transferência válida;
- transferência com saldo insuficiente;
- transferência para conta inexistente;
- transferência repetida com mesma chave de idempotência;
- precisão monetária com `Decimal`;
- filtros de extrato;
- criação de notificação a partir de evento;
- reprocessamento de evento sem duplicar notificação;
- marcação de notificação como lida.

### Frontend

Cobertura mínima:

- renderização do login;
- validação de campos obrigatórios;
- estado de erro de login;
- renderização do shell autenticado;
- exibição de saldo e cards da página `Início`;
- formulário de depósito;
- formulário de transferência;
- filtros de extrato;
- lista de notificações;
- helpers de moeda e data.

### Infraestrutura

Verificações:

- containers sobem;
- healthcheck do Postgres passa;
- healthcheck do Redis passa;
- API responde `/health`;
- frontend responde na porta documentada.

## 17. Documentação Obrigatória

### README

Deve conter:

- visão geral;
- stack;
- pré-requisitos;
- como configurar `.env`;
- como subir;
- como rodar migrations;
- como rodar seed;
- clientes iniciais;
- portas;
- comandos de teste;
- troubleshooting.

### PRD

O arquivo `docs/PRD.md` deve ser a referência de produto.

### Spec

Este arquivo deve ser a referência técnica e funcional para o plano de implementação.

## 18. Critérios De Aceite Da V1

- `docker compose up` sobe a aplicação.
- Login funciona com usuário seedado.
- `Início` exibe dados agregados.
- Contas são listadas.
- Depósito atualiza saldo e gera notificação.
- Transferência atualiza saldos e gera notificações.
- Extrato lista e filtra movimentações.
- Notificações podem ser lidas.
- Testes internos passam.
- README permite que outra pessoa rode o projeto.
- Não existe projeto Playwright dentro do repositório.
