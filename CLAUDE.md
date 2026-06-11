# CLAUDE.md

## Projeto

BankLab é uma aplicação de internet banking para portfólio.

O objetivo principal é construir uma aplicação bancária realista, funcional e bem estruturada utilizando:

* Next.js
* TypeScript
* Tailwind CSS
* FastAPI
* PostgreSQL
* Redis Streams
* Docker Compose

O produto vem antes da automação.

A aplicação deve parecer um sistema bancário real e não um laboratório de QA.

---

# Fonte Da Verdade

Antes de implementar qualquer funcionalidade:

1. Ler o PRD.
2. Ler a Spec.
3. Seguir os critérios definidos nesses documentos.

Não criar requisitos novos.

Não reinterpretar regras de negócio sem justificativa.

---

# Escopo

Funcionalidades da v1:

* Autenticação
* Início
* Contas
* Depósitos
* Transferências
* Extrato
* Notificações
* Auditoria

Não implementar:

* Pix
* Boletos
* Cartões
* Investimentos
* Empréstimos
* RBAC
* Área administrativa
* Feature Flags
* Integrações externas

Qualquer funcionalidade fora da lista deve ser aprovada antes da implementação.

---

# Filosofia De Desenvolvimento

Priorizar:

* simplicidade;
* clareza;
* manutenção;
* previsibilidade.

Evitar:

* overengineering;
* abstrações prematuras;
* padrões complexos sem necessidade;
* dependências desnecessárias.

Preferir a solução mais simples que atenda aos requisitos.

---

# Backend

Regras obrigatórias:

* FastAPI
* Pydantic
* SQLAlchemy
* PostgreSQL

Toda regra de negócio deve ficar no backend.

Não implementar lógica financeira no frontend.

---

# Operações Financeiras

Depósitos e transferências devem:

* ser atômicos;
* registrar auditoria;
* publicar eventos;
* respeitar idempotência.

Operações parciais não são aceitáveis.

---

# Valores Monetários

Todos os valores monetários devem utilizar Decimal.

Não utilizar float para cálculos financeiros.

Banco:

* numeric(12,2)

Backend:

* Decimal

---

# Redis Streams

Redis Streams deve ser utilizado apenas para eventos internos.

Exemplos:

* DEPOSIT_COMPLETED
* TRANSFER_COMPLETED

Não utilizar Redis como banco de dados principal.

---

# Frontend

Regras obrigatórias:

* Next.js App Router
* TypeScript strict
* Tailwind CSS

Priorizar:

* acessibilidade;
* semântica HTML;
* clareza visual;
* feedback ao usuário.

---

# Estados De Interface

Telas que realizam carregamento devem possuir:

* loading state

Telas sem conteúdo devem possuir:

* empty state

Falhas devem possuir:

* error state

Mensagens devem ser claras e orientadas ao usuário.

---

# Seed

O seed existe para permitir uso imediato da aplicação.

Os dados iniciais representam clientes comuns do BankLab.

Não criar usuários especiais.

Não criar perfis administrativos.

Não criar cenários artificiais.

---

# Testes

Este repositório contém apenas testes da aplicação.

Não adicionar:

* Playwright
* Pact
* k6
* Visual Regression

Essas iniciativas pertencem a projetos futuros e separados.

Manter:

* testes unitários
* testes de integração
* validações de infraestrutura

---

# Git

Conventional Commits:

* feat:
* fix:
* refactor:
* test:
* docs:
* chore:

Nunca adicionar:

* Generated with Claude
* Co-Authored-By: Claude
* referências à Anthropic

Todos os commits devem conter apenas autoria do usuário.

---

# Antes De Finalizar Uma Task

Verificar:

* código compila;
* migrations executam;
* Docker sobe corretamente;
* testes existentes continuam passando.

Não declarar uma tarefa concluída sem validação.
