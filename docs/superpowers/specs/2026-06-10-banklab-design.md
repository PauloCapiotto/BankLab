# Especificação De Design Do BankLab

## Contexto

BankLab é uma aplicação local de internet banking criada do zero para desenvolvimento com qualidade de portfólio e prática futura de testes automatizados. A primeira entrega foca somente na aplicação. Um projeto separado de automação com Playwright + TypeScript pode ser criado depois, mas está fora do escopo desta versão.

A aplicação deve parecer um produto bancário real, com foco em desktop, e não um sandbox didático de QA. Ao mesmo tempo, precisa continuar prática para rodar localmente em um MacBook M4 com 16 GB de RAM.

## Objetivos

- Construir uma aplicação realista de internet banking com autenticação, contas, depósitos, transferências, extrato e notificações.
- Usar uma stack moderna e valorizada: Next.js, TypeScript, Tailwind, FastAPI, Python, PostgreSQL, Redis Streams e Docker Compose.
- Rodar todo o ambiente localmente com Docker Compose.
- Manter a arquitetura adequada para portfólio e para automação end-to-end futura.
- Fornecer dados iniciais previsíveis e documentação clara de execução local.

## Fora De Escopo

- Nenhum projeto Playwright nesta primeira entrega.
- Nenhuma implementação de Pix.
- Nenhum pagamento de boletos.
- Nenhum módulo de cartão de crédito.
- Nenhum cadastro público de usuário.
- Nenhum deploy em produção.
- Nenhum processamento em background complexo além do uso leve de Redis Streams.

## Stack Técnica

### Frontend

- Next.js
- TypeScript
- Tailwind CSS
- Layout responsivo com foco em desktop

### Backend

- FastAPI
- Python
- Validação com Pydantic
- Autenticação com JWT
- Documentação OpenAPI gerada pelo FastAPI

### Dados

- PostgreSQL
- Migrations versionadas
- Dados iniciais para desenvolvimento local

### Mensageria

- Redis Streams
- Eventos de transações
- Criação de notificações a partir de eventos de transação

### Infraestrutura

- Docker Compose para todos os serviços:
  - `web`
  - `api`
  - `postgres`
  - `redis`
  - worker leve opcional de notificações

## Arquitetura

O diretório principal do projeto deve se chamar `BankLab`.

O repositório será um monorepo:

```text
apps/
  web/
  api/
infra/
  docker/
docs/
```

O frontend se comunica com o backend FastAPI por endpoints REST. O backend concentra regras de negócio, autenticação, validação, persistência e publicação de eventos.

O PostgreSQL armazena usuários, contas, transações, notificações e logs de auditoria. O Redis Streams é usado para eventos internos de transação. Um consumidor leve cria notificações persistidas a partir desses eventos.

O Docker Compose executa a aplicação inteira localmente. O uso de recursos deve ser conservador: sem workers pesados, sem serviços desnecessários e com comandos simples para iniciar, parar, resetar e popular dados.

## Módulos Do Produto

### Autenticação

- Login com usuários previamente cadastrados via seed.
- Logout.
- Sessão baseada em JWT.
- Rotas protegidas no frontend.
- Tratamento de sessão expirada.

### Início

A rota principal autenticada se chama `Início`, não `Dashboard`.

Ela inclui:

- saldo total disponível;
- entradas e saídas do mês;
- últimas movimentações;
- ações rápidas;
- contador de notificações;
- resumo do usuário atual.

### Contas

- Listar contas do usuário.
- Mostrar número da conta, saldo e status.
- Exibir dados úteis para transferências e extrato.

### Depósitos

- Simular entrada de dinheiro em uma conta.
- Validar valor.
- Criar uma transação de entrada.
- Atualizar saldo da conta.
- Publicar evento de transação no Redis Streams.
- Gerar uma notificação.

### Transferências

- Transferir dinheiro entre contas internas.
- Validar valor, conta de destino e saldo disponível.
- Criar registros de transação de saída e entrada.
- Atualizar os saldos das duas contas de forma atômica.
- Publicar eventos de transação.
- Exibir confirmação com aparência de comprovante.

### Extrato

- Tabela densa de transações.
- Filtros por período, tipo de transação, status e busca textual.
- Estados vazios claros.
- Estados de carregamento e erro claros.

### Notificações

- Listar notificações geradas por eventos de transação.
- Marcar notificações como lidas.
- Exibir contador de não lidas no shell autenticado.

## Modelo De Dados

### User

- id
- name
- email
- password_hash
- status
- created_at
- updated_at

### Account

- id
- user_id
- branch
- number
- type
- balance
- status
- created_at
- updated_at

### Transaction

- id
- account_id
- related_account_id
- type: deposit, transfer_in, transfer_out
- status: pending, completed, failed
- amount
- description
- created_at
- completed_at

### Notification

- id
- user_id
- type
- title
- message
- read_at
- created_at

### AuditLog

- id
- actor_user_id
- action
- entity_type
- entity_id
- metadata
- created_at

## Fluxos Principais

### Login

O usuário envia suas credenciais. A API valida o usuário, retorna um JWT e o frontend mantém a sessão de forma controlada. Rotas protegidas redirecionam usuários não autenticados para a tela de login.

### Depósito

O usuário escolhe uma conta e informa um valor. A API valida o valor, cria uma transação de depósito concluída, atualiza o saldo, publica um evento no Redis Streams e retorna o novo estado.

### Transferência

O usuário escolhe uma conta de origem, informa a conta de destino e o valor, revisa os dados e confirma. A API valida todas as regras, atualiza os saldos em uma transação de banco de dados, cria os registros de transação, publica eventos e retorna uma confirmação.

### Extrato

O frontend solicita transações paginadas com filtros. A API retorna as transações correspondentes e metadados de paginação e estados vazios.

### Notificações

O backend consome eventos de transação e cria registros de notificação. O frontend mostra o contador de não lidas e os detalhes das notificações.

## Tratamento De Erros

A aplicação deve tratar:

- login inválido;
- sessão expirada;
- saldo insuficiente;
- valor inválido;
- campos obrigatórios ausentes;
- conta de destino inexistente;
- requisição de transferência duplicada ou malformada;
- erros de validação do backend;
- falha temporária da API;
- ausência de resultados no extrato.

Os erros devem ser visíveis, específicos e úteis, sem expor detalhes internos de implementação.

## Direção Visual

A direção visual aprovada é amigável, quente e com foco em desktop.

Tipografia:

- Bricolage Grotesque para títulos e textos de destaque.
- Plus Jakarta Sans para textos de corpo e interface.

Tom e cor:

- fundos suaves em bege e pêssego;
- gradientes radiais sutis;
- coral e laranja queimado como cores principais de ação;
- marrom e cobre em cards financeiros de maior destaque;
- verde para movimentações positivas;
- laranja/vermelho quente para saídas de dinheiro.

Layout:

- navegação lateral esquerda;
- `Início` como rótulo ativo da página inicial;
- cards arredondados;
- iconografia clara na sidebar, nos cards financeiros, nas ações rápidas e na lista de transações;
- sem emoji de sino no pill de notificação do topo;
- contraste acessível nos textos e valores da lista de transações.

## Testes Dentro Deste Projeto

Este projeto inclui testes da própria aplicação, mas não inclui Playwright.

Testes de frontend:

- helpers de formatação;
- validação de formulários;
- estados de componentes;
- comportamento de proteção de rotas;
- principais componentes de interface.

Testes de backend:

- autenticação;
- depósitos;
- transferências;
- saldo insuficiente;
- filtros do extrato;
- criação de notificações;
- erros de validação.

Verificações de infraestrutura:

- migrations executam com sucesso;
- comando de seed cria os usuários e contas locais esperados;
- serviços do Docker Compose ficam saudáveis.

## Operação Local

O README deve documentar:

- pré-requisitos;
- variáveis de ambiente;
- inicialização com Docker Compose;
- comando de migration;
- comando de seed/reset;
- portas dos serviços;
- usuários de teste;
- URL útil da documentação da API;
- passos comuns de troubleshooting.

O fluxo local padrão deve ser simples:

```text
docker compose up
```

Comandos adicionais podem ser fornecidos para reset, seed e testes.

## Preparação Para Automação Futura

A primeira versão não inclui Playwright, mas deve evitar escolhas que dificultem a automação futura:

- nomes de rotas estáveis;
- dados iniciais previsíveis;
- estados claros de sucesso e erro;
- labels acessíveis;
- títulos de página consistentes;
- ambiente local determinístico;
- nenhuma dependência de dados externos aleatórios.

Seletores dedicados para Playwright podem ser adicionados depois, quando o projeto de automação for desenhado.

## Decisões Resolvidas

- Domínio: banco e finanças pessoais.
- Estilo do produto: aplicação realista para portfólio.
- Nível de backend: arquitetura robusta.
- Estilo de UI: internet banking com foco em desktop.
- Primeira entrega: somente a aplicação, sem projeto Playwright separado.
- Pasta principal do projeto: `BankLab`.
- Stack: Next.js, TypeScript, Tailwind, FastAPI, PostgreSQL, Redis Streams e Docker Compose.
- Modo de infraestrutura: todos os serviços rodam com Docker Compose.
- Estilo visual: direção quente em bege, pêssego e coral baseada no mockup aprovado.
