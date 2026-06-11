# PRD Do BankLab

## 1. Visão Geral

BankLab é uma aplicação local de internet banking criada para simular um produto bancário realista, com qualidade visual e arquitetural suficiente para portfólio e com fluxos adequados para prática futura de testes automatizados.

A primeira versão entrega a aplicação principal, sem criar ainda o projeto separado de automação com Playwright. A aplicação deve rodar localmente com Docker Compose e usar uma stack moderna: Next.js, TypeScript, Tailwind, FastAPI, Python, PostgreSQL e Redis Streams.

## 2. Problema

Treinar automação end-to-end em aplicações muito simples cria uma lacuna entre estudo e mercado. Projetos didáticos normalmente não têm autenticação realista, estados de erro, dados transacionais, tabelas filtráveis, validações de negócio, eventos assíncronos ou arquitetura parecida com aplicações profissionais.

BankLab resolve isso oferecendo uma aplicação bancária local com fluxos completos e previsíveis, sem depender de serviços externos, APIs de terceiros ou infraestrutura pesada.

## 3. Objetivos Do Produto

- Criar uma aplicação bancária realista para uso local.
- Servir como base de portfólio técnico.
- Permitir prática futura de automação com Playwright em um projeto separado.
- Demonstrar arquitetura full-stack moderna com frontend, backend, banco relacional e mensageria.
- Fornecer dados determinísticos para uso manual, testes automatizados futuros e demonstrações.
- Rodar em MacBook M4 com 16 GB de RAM sem sobrecarga excessiva.

## 4. Não Objetivos

- Não criar o projeto Playwright nesta fase.
- Não implementar Pix realista.
- Não implementar boletos.
- Não implementar cartão de crédito.
- Não implementar cadastro público de usuário.
- Não integrar com serviços bancários reais.
- Não criar deploy em nuvem.
- Não criar microsserviços separados.
- Não criar mensageria complexa além de eventos leves com Redis Streams.

## 5. Público-Alvo

### Público Principal

Pessoa desenvolvedora ou QA que quer estudar automação e arquitetura usando uma aplicação mais próxima de um produto real.

### Público Secundário

Recrutadores, tech leads ou avaliadores técnicos que podem acessar o projeto como evidência de domínio em produto, backend, frontend, testes e infraestrutura local.

## 6. Personas

### Paulo, QA/Desenvolvedor Em Evolução

Quer uma aplicação com fluxos reais para depois criar testes automatizados em Playwright. Precisa de dados estáveis, cenários positivos e negativos, boa UI e backend com regras de negócio.

### Avaliador Técnico

Quer entender rapidamente a arquitetura, subir o projeto localmente, navegar pelos fluxos e ver organização de código, documentação e testes.

## 7. Proposta De Valor

BankLab entrega uma experiência de internet banking local, visualmente amigável e tecnicamente robusta, permitindo demonstrar domínio em:

- frontend moderno;
- backend com regras de negócio;
- banco relacional;
- eventos com Redis Streams;
- Docker Compose;
- testes internos de aplicação;
- preparação para automação end-to-end futura.

## 8. Escopo Da V1

### Incluído

- Login com usuário seedado.
- Logout.
- Sessão autenticada com JWT.
- Shell autenticado com navegação lateral.
- Página `Início`.
- Listagem de contas.
- Depósito simulado.
- Transferência entre contas internas.
- Extrato com filtros.
- Notificações geradas por eventos de transação.
- Logs de auditoria para ações importantes.
- API documentada via OpenAPI.
- Banco PostgreSQL com migrations.
- Redis Streams para eventos internos.
- Docker Compose para rodar a aplicação completa.
- README com instruções de uso.
- Testes internos de frontend e backend.

### Excluído

- Projeto Playwright.
- Integração bancária real.
- Autocadastro.
- Recuperação de senha por e-mail.
- Upload de documentos.
- Autorização por múltiplos fatores.
- Tema escuro.

## 9. Experiência Do Usuário

### Tom Visual

A aplicação deve ser amigável, quente e humana, evitando o visual frio de sistemas bancários corporativos genéricos.

Direção aprovada:

- fundo bege/pêssego suave;
- gradientes radiais discretos;
- coral e laranja queimado como cores principais;
- marrom e cobre em cards financeiros de destaque;
- verde para entradas;
- laranja/vermelho quente para saídas.

### Tipografia

- Bricolage Grotesque para títulos e números em destaque.
- Plus Jakarta Sans para corpo, formulários, tabelas e navegação.

### Layout

- Desktop-first.
- Sidebar fixa à esquerda.
- Página inicial chamada `Início`, não `Dashboard`.
- Cards arredondados.
- Ícones no menu, cards financeiros, ações rápidas e lista de movimentações.
- Notificação no topo sem emoji de sino.
- Contraste adequado em listas e valores financeiros.

## 10. Jornada Principal

1. Usuário acessa a aplicação local.
2. Usuário faz login com credenciais seedadas.
3. Usuário cai na página `Início`.
4. Usuário visualiza saldo, entradas, saídas, últimas movimentações e notificações.
5. Usuário simula um depósito.
6. Sistema atualiza saldo, cria transação, publica evento e gera notificação.
7. Usuário faz uma transferência interna.
8. Sistema valida saldo e destino, atualiza contas, cria transações e notifica.
9. Usuário consulta o extrato com filtros.
10. Usuário revisa notificações e encerra a sessão.

## 11. Requisitos Funcionais

### RF01 - Login

O usuário deve conseguir autenticar usando e-mail e senha previamente cadastrados no seed.

Critérios de aceite:

- login válido redireciona para `Início`;
- login inválido exibe mensagem clara;
- usuário inativo não autentica;
- token expirado exige novo login;
- sessão expirada redireciona para login;
- rotas autenticadas não devem ser acessíveis sem token válido.

### RF02 - Logout

O usuário deve conseguir encerrar a sessão.

Critérios de aceite:

- token local é removido;
- usuário é redirecionado para login;
- tentativa de voltar para área autenticada exige novo login.

### RF03 - Início

O usuário deve visualizar um resumo financeiro.

Critérios de aceite:

- mostra saldo total;
- mostra entradas do mês;
- mostra saídas do mês;
- mostra últimas movimentações;
- mostra ações rápidas;
- mostra contador de notificações;
- usa o rótulo `Início`.

### RF04 - Contas

O usuário deve visualizar suas contas.

Critérios de aceite:

- lista contas vinculadas ao usuário autenticado;
- mostra agência, número, tipo, status e saldo;
- não mostra contas de outros usuários.

### RF05 - Depósito

O usuário deve simular depósito em uma conta própria.

Critérios de aceite:

- valor deve ser maior que zero;
- valor deve ser tratado com precisão decimal;
- retentativa com a mesma chave de idempotência não duplica o depósito;
- depósito válido cria transação `deposit`;
- saldo da conta aumenta;
- evento é publicado no Redis Streams;
- notificação é criada;
- erro de validação aparece no formulário.

### RF06 - Transferência

O usuário deve transferir dinheiro entre contas internas.

Critérios de aceite:

- conta de origem deve pertencer ao usuário;
- conta destino deve existir;
- valor deve ser maior que zero;
- valor deve ser tratado com precisão decimal;
- saldo insuficiente deve bloquear a operação;
- retentativa com a mesma chave de idempotência não duplica débito ou crédito;
- transferência válida cria transação de saída e entrada;
- saldos são atualizados de forma atômica;
- comprovante/resultado é exibido;
- evento é publicado no Redis Streams.

### RF07 - Extrato

O usuário deve consultar movimentações.

Critérios de aceite:

- lista transações paginadas;
- permite filtro por período;
- permite filtro por tipo;
- permite filtro por status;
- permite busca textual por descrição;
- mostra estado vazio quando não houver resultados.

### RF08 - Notificações

O usuário deve visualizar notificações geradas por eventos.

Critérios de aceite:

- lista notificações do usuário autenticado;
- mostra contador de não lidas;
- permite marcar como lida;
- notificação é persistida após evento de depósito ou transferência.
- reprocessamento do mesmo evento não cria notificação duplicada.

### RF09 - Auditoria

O sistema deve registrar ações relevantes.

Critérios de aceite:

- login bem-sucedido pode gerar log;
- depósito gera log;
- transferência gera log;
- falhas importantes de regra de negócio podem gerar log técnico.

## 12. Requisitos Não Funcionais

### RNF01 - Execução Local

A aplicação deve rodar com Docker Compose.

Critérios:

- `docker compose up` sobe todos os serviços necessários;
- Postgres e Redis devem ter healthcheck;
- frontend e backend devem ficar acessíveis em portas documentadas.

### RNF02 - Performance Local

A aplicação deve ser leve para uso em MacBook M4 com 16 GB de RAM.

Critérios:

- evitar serviços desnecessários;
- evitar workers pesados;
- manter Redis Streams com uso simples;
- usar volumes locais e imagens comuns.

### RNF03 - Segurança Básica

Mesmo local, a aplicação deve seguir boas práticas.

Critérios:

- senhas armazenadas com hash;
- JWT com expiração;
- sem refresh token na v1;
- variáveis sensíveis em `.env`;
- `.env.example` sem segredos reais;
- backend valida todas as regras críticas.

### RNF04 - Observabilidade Local

O desenvolvedor deve conseguir entender falhas.

Critérios:

- logs claros no backend;
- mensagens úteis no frontend;
- healthchecks;
- documentação de troubleshooting.

### RNF05 - Testabilidade

A aplicação deve ser preparada para automação futura.

Critérios:

- dados seedados previsíveis;
- rotas estáveis;
- estados claros de sucesso e erro;
- labels acessíveis;
- textos consistentes;
- sem dependência de dados externos aleatórios.

### RNF06 - Consistência Financeira

Operações financeiras devem ser previsíveis e seguras contra duplicidade.

Critérios:

- valores monetários devem usar precisão decimal;
- depósitos e transferências devem ser idempotentes;
- saldos não podem ser alterados parcialmente;
- worker de notificações deve aceitar reprocessamento seguro de eventos.

## 13. Dados Iniciais

O seed da v1 existe para permitir o uso imediato da aplicação após a instalação local. Esses dados representam clientes comuns do BankLab e servem para demonstrar os principais fluxos do produto sem configuração manual.

O seed deve criar:

- usuários;
- contas;
- algumas transações;
- algumas notificações;
- saldos coerentes com as movimentações exibidas.

Clientes iniciais:

### Maria Silva

- Cliente comum do BankLab.
- E-mail: `maria@banklab.local`
- Senha: `BankLab@123`
- Deve possuir ao menos uma conta ativa.

### João Souza

- Cliente comum do BankLab.
- E-mail: `joao@banklab.local`
- Senha: `BankLab@123`
- Deve possuir ao menos uma conta ativa.

As transações e notificações iniciais devem existir apenas para que as telas `Início`, `Extrato` e `Notificações` tenham conteúdo útil logo após a primeira execução local.

## 14. Métricas De Sucesso

- Aplicação sobe localmente com um comando documentado.
- Login, depósito, transferência, extrato e notificações funcionam manualmente.
- Testes internos passam.
- API possui documentação OpenAPI acessível.
- Seed permite repetir os principais cenários.
- UI segue o estilo visual aprovado.
- Repositório tem documentação suficiente para outro avaliador rodar o projeto.

## 15. Riscos

- Docker Compose com todos os serviços pode consumir mais recursos que o necessário.
- Redis Streams pode aumentar complexidade se for usado além do necessário.
- Next.js e FastAPI exigem cuidado para manter contratos de API consistentes.
- UI muito polida antes da base funcional pode atrasar a entrega.
- Falta de dados seedados bem planejados pode prejudicar a automação futura.
- Uso incorreto de tipos numéricos pode causar divergência em saldos.
- Retentativas sem idempotência podem duplicar depósitos ou transferências.

## 16. Estratégia De Entrega

### Fase 1 - Fundação

- Estrutura do monorepo.
- Docker Compose.
- Frontend e backend mínimos.
- Healthchecks.
- README inicial.

### Fase 2 - Backend E Dados

- Modelos.
- Migrations.
- Seed.
- Auth.
- Regras de depósito e transferência.
- Eventos e notificações.

### Fase 3 - Frontend Funcional

- Login.
- Shell autenticado.
- Início.
- Contas.
- Depósitos.
- Transferências.
- Extrato.
- Notificações.

### Fase 4 - Qualidade

- Testes de backend.
- Testes de frontend.
- Ajustes visuais.
- Documentação final.
- Validação local completa.

## 17. Critérios De Pronto Da V1

A v1 estará pronta quando:

- todos os serviços subirem com Docker Compose;
- usuário seedado conseguir fazer login;
- usuário conseguir consultar contas;
- usuário conseguir simular depósito;
- usuário conseguir transferir para conta interna;
- extrato refletir as operações;
- notificações forem geradas por eventos;
- retentativas de depósito e transferência não duplicarem operações;
- valores financeiros manterem precisão decimal;
- testes internos passarem;
- README permitir rodar o projeto do zero;
- UI seguir a direção visual aprovada;
- não houver projeto Playwright dentro deste repositório.
