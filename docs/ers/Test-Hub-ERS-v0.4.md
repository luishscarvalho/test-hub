**Test Hub**

Especificação de Requisitos de Software

|   |   |   |   |
|---|---|---|---|
| **Versão do documento** | 0.4 | **Versão do produto** | v1 |
| **Data** | 08/11/2026 | **Prazo estimado da v1** | 3 a 5 dias após a definição de todos os documentos |
| **Autor** | Luís Henrique Souza Carvalho | **Status** | Aprovado |

# **1. Introdução**

Este documento registra os requisitos da versão 1 do Test Hub por meio de épicos, regras de negócio, requisitos funcionais (estórias de usuário) e não funcionais. O objetivo é fixar o escopo antes da implementação, evitando que o projeto cresça sem controle, e servir de referência para as decisões registradas em ADRs ao longo do desenvolvimento.

# **2. Definição de Conceitos**

Conceitos de maior relevância para o domínio do sistema.

1.  **ADR (Architecture Decision Record):** Registro curto de uma decisão arquitetural, com contexto, alternativas consideradas e consequências.

2.  **API alvo:** API HTTP cadastrada no hub para ser testada. Na v1 é uma API pequena criada pelo próprio projeto.

3.  **Caso de teste:** Cada requisição gerada pelo Schemathesis para um endpoint. Um endpoint pode ter vários casos, consolidados em um único resultado.

4.  **Endpoint:** Combinação de caminho e método HTTP exposta por uma API (ex.: GET /tarefas/{id}).

5.  **Fila e worker:** A run é colocada numa fila (Redis) e executada por um processo separado (worker), fora do request.

6.  **Flaky:** Teste que alterna entre passar e falhar sem mudança no código. Detecção prevista apenas para a v2.

7.  **Health check:** Endpoint que informa se o serviço está de pé.

8.  **OpenAPI:** Padrão para descrever APIs HTTP em JSON ou YAML: caminhos, métodos, parâmetros e schemas de resposta.

9.  **Run (execução):** Rodada completa dos smoke tests de uma API alvo, com início, fim e resultado de cada teste executado. Uma run pode terminar sem resultados de teste (RN-06).

10. **Schema:** Descrição da estrutura esperada de um corpo de resposta (campos, tipos e obrigatoriedade).

11. **Schemathesis:** Ferramenta open source que gera testes a partir de uma spec OpenAPI. Ferramenta adotada como gerador de testes (ADR-005).

12. **Seed:** Valor fixo usado na geração dos casos, que faz runs sobre a mesma spec gerarem os mesmos dados.

13. **Smoke test:** Teste básico que verifica se um endpoint responde com o status esperado e com corpo conforme o schema. Não valida regra de negócio.

14. **Spec:** Documento OpenAPI que descreve uma API.

15. **Versão da spec:** Registro imutável do conteúdo de uma spec, identificado por hash. Toda run que resolveu a spec aponta para a versão que usou (RN-13).

# **3. Contexto**

Testar uma API manualmente, ou escrever cada teste à mão, é repetitivo e fácil de deixar desatualizado quando a API muda. Como uma API bem documentada já descreve seus endpoints e respostas em uma spec OpenAPI, essa spec pode ser a fonte para gerar testes básicos automaticamente.

Além disso, o histórico dessas execuções costuma se perder em logs de CI, o que dificulta comparar uma rodada com a anterior. O Test Hub também serve como projeto de portfólio de QA/SDET, demonstrando testes automatizados, CI, containers e decisões documentadas.

# **4. Objetivos**

1.  **Gerar testes básicos automaticamente** a partir da spec OpenAPI.

2.  **Guardar um histórico consultável** de cada execução.

3.  **Entregar a v1 fechada** em 3 a 5 dias após a definição de todos os documentos, com CI verde e README.

4.  **Demonstrar boas práticas** de engenharia: ADRs, cobertura, Docker e CI.

# **5. Visão do Produto**

O **Test Hub** é um serviço (API) em Python e FastAPI, com arquitetura hexagonal (ADR-003), que recebe o cadastro de uma API alvo, lê sua spec OpenAPI, gera smoke tests por endpoint via Schemathesis (ADR-005), executa as runs em segundo plano por uma fila com Redis e RQ, processada por um worker dedicado (ADR-006), e persiste o histórico no PostgreSQL. A v1 foca em uma única API alvo pequena, criada no próprio projeto, com todo o ambiente subindo via Docker Compose.

## **5.1 Versões planejadas**

| **Versão** | **Escopo** | **Situação** |
|---|---|---|
| **v1** | Smoke tests gerados da spec, execução e histórico, com API alvo própria. | Em especificação |
| **v2** | Detecção de flaky e dashboard. | Futura |
| **v3** | APIs públicas externas. | Futura |

## **5.2 Principais funcionalidades da v1**

- Cadastro de API alvo com spec OpenAPI.

- Leitura e validação da spec.

- Geração de smoke tests (status e schema) por endpoint.

- Execução dos testes contra a API alvo.

- Persistência do histórico no PostgreSQL.

- API do hub para consultar execuções e resultados.

- Ambiente completo via Docker Compose, CI verde, cobertura alta e README.

- Versionamento da spec, com novo download a cada run para specs cadastradas por URL.

- Execução assíncrona das runs por fila.

## **5.3 API alvo**

API de tarefas em FastAPI (ADR-008), na pasta target_api/ do mesmo repositório, com dados em memória e seed carregada na inicialização. Endpoints:

- GET /tarefas

- GET /tarefas/{id}

- POST /tarefas

- PUT /tarefas/{id}

- DELETE /tarefas/{id} (204 sem corpo)

- GET /saude (health check)

A variável **MODO_FALHA** fica desligada por padrão. Quando ligada, GET /tarefas/{id} devolve, para qualquer id, tipos diferentes dos da spec e GET /tarefas devolve 500, para demonstrar que o hub detecta falhas. GET /saude nunca falha.

# **6. Classes de Usuários**

O sistema será utilizado por:

- **Dev/QA:** pessoa que cadastra APIs, dispara runs e consulta resultados.

Não há autenticação na v1, então não existe diferença entre papéis. Desenvolvedor, QA e usuário são sinônimos no contexto do projeto.

# **7. Fora do Escopo da v1**

- Detecção de flaky (v2).

- Dashboard (v2).

- APIs públicas externas (v3).

- Autenticação e multiusuário.

- Testes de regra de negócio (a v1 faz apenas smoke).

- APIs sem spec OpenAPI (fora do escopo do projeto inteiro).

- Retry automático de runs.

- Múltiplos workers e reconciliação de runs perdidas na fila.

- Deploy em nuvem.

- Endpoint de falha intermitente na API alvo (v2).

- Atualização manual de spec cadastrada por arquivo.

- Limpeza de versões antigas de spec.

- Listagem, edição e remoção de APIs alvo.

# **8. Regras de Negócio**

Regras que restringem ou definem o comportamento do sistema, com base na condição considerada em seu escopo.

*Prioridade: "Urgente", "Alta", "Média" e "Baixa". Tipo: "Restritivo", "Derivada" e "Factivo".*

| **ID** | **Regra de Negócio** | **Prioridade** | **Tipo** |
|---|---|---|---|
| **RN-01** | Toda API alvo deve ter uma spec OpenAPI válida para ser cadastrada. | Urgente | Restritivo |
| **RN-02** | Spec inválida deve ser rejeitada com mensagem que indique o motivo. Spec sem nenhum endpoint também é inválida. A mesma validação vale no início de cada run para specs cadastradas por URL. | Alta | Restritivo |
| **RN-03** | Cada par endpoint e método da spec gera exatamente um resultado de smoke test por run. Os vários casos gerados para o endpoint são consolidados: o resultado é "passou" somente se todos os casos passaram; em falha, registra a mensagem do primeiro caso que falhou; a duração é a soma da duração dos casos. Erro de conexão ou tempo esgotado ao chamar a API alvo conta como caso que falhou. | Alta | Derivada |
| **RN-04** | O smoke test verifica apenas o status esperado e o schema da resposta. Testes de regra de negócio estão fora do escopo. | Alta | Restritivo |
| **RN-05** | Uma run em status final (passou, falhou ou interrompida) não pode ter status nem resultados alterados. O histórico nunca é sobrescrito. | Alta | Factivo |
| **RN-06** | O status geral da run é "passou" somente se todos os testes passaram. A run também termina como "falhou" se a spec estiver inacessível ou inválida no início da execução, com o motivo registrado e sem resultados de teste. | Urgente | Derivada |
| **RN-07** | Toda run em status final (passou, falhou ou interrompida) registra início e fim, mesmo sem resultados de teste. Todo teste registra sua duração. | Média | Factivo |
| **RN-08** | Nenhuma funcionalidade fora da lista da v1 pode ser implementada antes de a v1 ser fechada. | Urgente | Restritivo |
| **RN-09** | Toda decisão arquitetural relevante deve ser registrada em um ADR. | Média | Restritivo |
| **RN-10** | Na v1, a única API alvo é a criada pelo próprio projeto. | Média | Factivo |
| **RN-11** | Status da run: na_fila, em_execucao, passou, falhou e interrompida. Os três últimos são finais. Só o worker muda o status a partir de na_fila. | Urgente | Restritivo |
| **RN-12** | Uma run é marcada como interrompida, com fim e motivo registrados, quando: (a) ao iniciar, o worker a encontra presa em em_execucao; (b) a execução excede o tempo máximo configurado; ou (c) ocorre um erro inesperado do próprio hub durante a execução. Não há retry automático. Uma run interrompida fica no histórico e uma nova run deve ser disparada. | Alta | Restritivo |
| **RN-13** | Toda run que chegou a resolver a spec referencia a versão usada. O campo fica vazio quando a run termina antes dessa etapa (download falhou, spec inválida ou run interrompida antes de resolver a spec). Toda run com resultados de teste tem a versão preenchida. Versões são imutáveis e identificadas por hash SHA-256 do JSON normalizado. Specs por URL são baixadas de novo a cada run: se o hash for novo, cria nova versão; se já existir, reusa. Specs por arquivo usam a versão mais recente. | Alta | Factivo |
| **RN-14** | A geração de casos usa seed fixa e configurável, e cada run registra a seed com que foi executada. | Média | Factivo |
| **RN-15** | Resultados de teste e totais são gravados de uma só vez, na mesma transação que finaliza a run. Run interrompida não tem resultados de teste e tem totais zerados. | Alta | Restritivo |
| **RN-16** | Se a execução não puder ser enfileirada, o disparo responde 503 e a run não permanece registrada. | Alta | Restritivo |

# **9. Épicos**

Um épico representa uma funcionalidade macro do sistema, agrupando estórias de usuário relacionadas que, juntas, entregam valor.

|   |   |   |
|---|---|---|
| **EPIC - 01** | **Cadastro e Validação de APIs** | **Status: Não iniciada** |
| **Descrição** | *Registrar APIs alvo no hub e garantir que a spec OpenAPI é válida.* |   |
| **Estórias de usuário relacionadas** | **Cadastrar API alvo** | **US-01** |
|   | **Validar spec OpenAPI** | **US-02** |
| **Regras de negócio relacionadas** | Toda API alvo deve ter uma spec OpenAPI válida para ser cadastrada. | **RN-01** |
|   | Spec inválida deve ser rejeitada com mensagem que indique o motivo. Spec sem nenhum endpoint também é inválida. A mesma validação vale no início de cada run para specs cadastradas por URL. | **RN-02** |
|   | Toda run que chegou a resolver a spec referencia a versão usada. O campo fica vazio quando a run termina antes dessa etapa (download falhou, spec inválida ou run interrompida antes de resolver a spec). Toda run com resultados de teste tem a versão preenchida. Versões são imutáveis e identificadas por hash SHA-256 do JSON normalizado. Specs por URL são baixadas de novo a cada run: se o hash for novo, cria nova versão; se já existir, reusa. Specs por arquivo usam a versão mais recente. | **RN-13** |
| **Valor de Negócio** | *Garantir que somente APIs testáveis entrem no hub.* |   |

|   |   |   |
|---|---|---|
| **EPIC - 02** | **Geração de Testes** | **Status: Não iniciada** |
| **Descrição** | *Gerar smoke tests automaticamente a partir da spec.* |   |
| **Estórias de usuário relacionadas** | **Gerar smoke tests** | **US-03** |
| **Regras de negócio relacionadas** | Cada par endpoint e método da spec gera exatamente um resultado de smoke test por run. Os vários casos gerados para o endpoint são consolidados: o resultado é "passou" somente se todos os casos passaram; em falha, registra a mensagem do primeiro caso que falhou; a duração é a soma da duração dos casos. Erro de conexão ou tempo esgotado ao chamar a API alvo conta como caso que falhou. | **RN-03** |
|   | O smoke test verifica apenas o status esperado e o schema da resposta. Testes de regra de negócio estão fora do escopo. | **RN-04** |
|   | A geração de casos usa seed fixa e configurável, e cada run registra a seed com que foi executada. | **RN-14** |
| **Valor de Negócio** | *Eliminar a escrita manual de testes básicos.* |   |

|   |   |   |
|---|---|---|
| **EPIC - 03** | **Execução e Registro** | **Status: Não iniciada** |
| **Descrição** | *Executar os testes contra a API alvo e registrar os resultados.* |   |
| **Estórias de usuário relacionadas** | **Disparar execução** | **US-04** |
|   | **Registrar resultado da run** | **US-05** |
|   | **Registrar resultado por teste** | **US-06** |
| **Regras de negócio relacionadas** | Uma run em status final (passou, falhou ou interrompida) não pode ter status nem resultados alterados. O histórico nunca é sobrescrito. | **RN-05** |
|   | O status geral da run é "passou" somente se todos os testes passaram. A run também termina como "falhou" se a spec estiver inacessível ou inválida no início da execução, com o motivo registrado e sem resultados de teste. | **RN-06** |
|   | Toda run em status final (passou, falhou ou interrompida) registra início e fim, mesmo sem resultados de teste. Todo teste registra sua duração. | **RN-07** |
|   | Status da run: na_fila, em_execucao, passou, falhou e interrompida. Os três últimos são finais. Só o worker muda o status a partir de na_fila. | **RN-11** |
|   | Uma run é marcada como interrompida, com fim e motivo registrados, quando: (a) ao iniciar, o worker a encontra presa em em_execucao; (b) a execução excede o tempo máximo configurado; ou (c) ocorre um erro inesperado do próprio hub durante a execução. Não há retry automático. Uma run interrompida fica no histórico e uma nova run deve ser disparada. | **RN-12** |
|   | A geração de casos usa seed fixa e configurável, e cada run registra a seed com que foi executada. | **RN-14** |
|   | Resultados de teste e totais são gravados de uma só vez, na mesma transação que finaliza a run. Run interrompida não tem resultados de teste e tem totais zerados. | **RN-15** |
|   | Se a execução não puder ser enfileirada, o disparo responde 503 e a run não permanece registrada. | **RN-16** |
| **Valor de Negócio** | *Produzir evidência confiável do estado da API.* |   |

|   |   |   |
|---|---|---|
| **EPIC - 04** | **Consulta de Histórico** | **Status: Não iniciada** |
| **Descrição** | *Consultar execuções passadas e seus resultados.* |   |
| **Estórias de usuário relacionadas** | **Listar runs de uma API** | **US-07** |
|   | **Consultar detalhe da run** | **US-08** |
| **Regras de negócio relacionadas** | Uma run em status final (passou, falhou ou interrompida) não pode ter status nem resultados alterados. O histórico nunca é sobrescrito. | **RN-05** |
|   | Status da run: na_fila, em_execucao, passou, falhou e interrompida. Os três últimos são finais. Só o worker muda o status a partir de na_fila. | **RN-11** |
|   | Toda run que chegou a resolver a spec referencia a versão usada. O campo fica vazio quando a run termina antes dessa etapa (download falhou, spec inválida ou run interrompida antes de resolver a spec). Toda run com resultados de teste tem a versão preenchida. Versões são imutáveis e identificadas por hash SHA-256 do JSON normalizado. Specs por URL são baixadas de novo a cada run: se o hash for novo, cria nova versão; se já existir, reusa. Specs por arquivo usam a versão mais recente. | **RN-13** |
| **Valor de Negócio** | *Permitir comparar execuções e investigar falhas.* |   |

*Status possíveis: "Não iniciada", "Com bug", "Em progresso", "Em teste", "Parcialmente feita" e "Finalizada". RN-08, RN-09 e RN-10 são transversais e não pertencem a um épico específico.*

# **10. Requisitos de Software**

## **10.1 Requisitos Funcionais**

<table class="us"><colgroup><col style="width: 19%" /><col style="width: 58%" /><col style="width: 23%" /></colgroup><tbody>
<tr><td><strong>US - 01</strong></td><td><strong>Cadastrar API alvo</strong></td><td><strong>Status: Não iniciada</strong></td></tr>
<tr><td><strong>Cartão</strong></td><td colspan="2"><p><strong>COMO</strong> dev/QA,</p><p><strong>QUERO</strong> cadastrar uma API alvo informando nome, base URL e spec OpenAPI (URL ou arquivo),</p><p><strong>PARA</strong> que o hub possa testá-la.</p></td></tr>
<tr><td><strong>Critérios de Aceitação</strong></td><td colspan="2"><ul><li><p>Critério 1: Nome, base URL e spec são obrigatórios.</p></li><li><p>Critério 2: A spec pode ser informada por URL ou por arquivo.</p></li><li><p>Critério 3: O cadastro retorna o identificador da API criada.</p></li></ul></td></tr>
<tr><td><strong>Relacionada</strong></td><td><strong>Épico - 01 Cadastro e Validação de APIs</strong></td><td><strong>RN-01, RN-10</strong></td></tr>
</tbody></table>

<table class="us"><colgroup><col style="width: 19%" /><col style="width: 58%" /><col style="width: 23%" /></colgroup><tbody>
<tr><td><strong>US - 02</strong></td><td><strong>Validar spec OpenAPI</strong></td><td><strong>Status: Não iniciada</strong></td></tr>
<tr><td><strong>Cartão</strong></td><td colspan="2"><p><strong>COMO</strong> dev/QA,</p><p><strong>QUERO</strong> que o hub baixe e valide a spec no cadastro,</p><p><strong>PARA</strong> descobrir cedo se a API não pode ser testada.</p></td></tr>
<tr><td><strong>Critérios de Aceitação</strong></td><td colspan="2"><ul><li><p>Critério 1: Spec inválida é rejeitada e não é salva.</p></li><li><p>Critério 2: A mensagem de erro informa o motivo da rejeição.</p></li><li><p>Critério 3: Spec válida é aceita e associada à API.</p></li><li><p>Critério 4: A spec válida é salva como versão, com hash.</p></li><li><p>Critério 5: A mesma validação é aplicada no início de cada run de spec cadastrada por URL.</p></li></ul></td></tr>
<tr><td><strong>Relacionada</strong></td><td><strong>Épico - 01 Cadastro e Validação de APIs</strong></td><td><strong>RN-01, RN-02, RN-13</strong></td></tr>
</tbody></table>

<table class="us"><colgroup><col style="width: 19%" /><col style="width: 58%" /><col style="width: 23%" /></colgroup><tbody>
<tr><td><strong>US - 03</strong></td><td><strong>Gerar smoke tests</strong></td><td><strong>Status: Não iniciada</strong></td></tr>
<tr><td><strong>Cartão</strong></td><td colspan="2"><p><strong>COMO</strong> dev/QA,</p><p><strong>QUERO</strong> que o hub gere um smoke test para cada endpoint e método da spec,</p><p><strong>PARA</strong> testar a API sem escrever testes à mão.</p></td></tr>
<tr><td><strong>Critérios de Aceitação</strong></td><td colspan="2"><ul><li><p>Critério 1: Existe exatamente um resultado por par endpoint e método, consolidando os casos gerados.</p></li><li><p>Critério 2: Cada teste verifica o status esperado e o schema da resposta.</p></li><li><p>Critério 3: Endpoint sem schema de resposta na spec verifica apenas o status.</p></li><li><p>Critério 4: Com a mesma spec e a mesma seed, os casos gerados são os mesmos.</p></li></ul></td></tr>
<tr><td><strong>Relacionada</strong></td><td><strong>Épico - 02 Geração de Testes</strong></td><td><strong>RN-03, RN-04, RN-14</strong></td></tr>
</tbody></table>

<table class="us"><colgroup><col style="width: 19%" /><col style="width: 58%" /><col style="width: 23%" /></colgroup><tbody>
<tr><td><strong>US - 04</strong></td><td><strong>Disparar execução</strong></td><td><strong>Status: Não iniciada</strong></td></tr>
<tr><td><strong>Cartão</strong></td><td colspan="2"><p><strong>COMO</strong> dev/QA,</p><p><strong>QUERO</strong> disparar uma run dos testes de uma API cadastrada,</p><p><strong>PARA</strong> saber se ela responde conforme a spec.</p></td></tr>
<tr><td><strong>Critérios de Aceitação</strong></td><td colspan="2"><ul><li><p>Critério 1: A run só pode ser disparada para uma API cadastrada.</p></li><li><p>Critério 2: Todos os testes gerados são executados pelo worker contra a base URL.</p></li><li><p>Critério 3: Ao final, a run possui um status geral.</p></li><li><p>Critério 4: O disparo responde 202 com o identificador da run e status na_fila, sem aguardar a execução.</p></li><li><p>Critério 5: Se a spec estiver inacessível ou inválida, a run termina como falhou com o motivo.</p></li><li><p>Critério 6: Se a execução não puder ser enfileirada, o disparo responde 503 e a run não permanece registrada.</p></li></ul></td></tr>
<tr><td><strong>Relacionada</strong></td><td><strong>Épico - 03 Execução e Registro</strong></td><td><strong>RN-06, RN-11, RN-13, RN-16</strong></td></tr>
</tbody></table>

<table class="us"><colgroup><col style="width: 19%" /><col style="width: 58%" /><col style="width: 23%" /></colgroup><tbody>
<tr><td><strong>US - 05</strong></td><td><strong>Registrar resultado da run</strong></td><td><strong>Status: Não iniciada</strong></td></tr>
<tr><td><strong>Cartão</strong></td><td colspan="2"><p><strong>COMO</strong> dev/QA,</p><p><strong>QUERO</strong> que cada run registre início, fim, status geral, totais de testes que passaram e falharam, e a seed e a versão da spec usadas,</p><p><strong>PARA</strong> acompanhar a saúde da API ao longo do tempo.</p></td></tr>
<tr><td><strong>Critérios de Aceitação</strong></td><td colspan="2"><ul><li><p>Critério 1: Início e fim são gravados para toda run em status final, inclusive interrompida.</p></li><li><p>Critério 2: O status geral é "passou" somente se todos os testes passaram.</p></li><li><p>Critério 3: Os totais conferem com os resultados individuais.</p></li><li><p>Critério 4: O status geral segue os estados definidos na RN-11.</p></li></ul></td></tr>
<tr><td><strong>Relacionada</strong></td><td><strong>Épico - 03 Execução e Registro</strong></td><td><strong>RN-05, RN-06, RN-07, RN-11, RN-12, RN-13, RN-14, RN-15</strong></td></tr>
</tbody></table>

<table class="us"><colgroup><col style="width: 19%" /><col style="width: 58%" /><col style="width: 23%" /></colgroup><tbody>
<tr><td><strong>US - 06</strong></td><td><strong>Registrar resultado por teste</strong></td><td><strong>Status: Não iniciada</strong></td></tr>
<tr><td><strong>Cartão</strong></td><td colspan="2"><p><strong>COMO</strong> dev/QA,</p><p><strong>QUERO</strong> que cada teste da run registre endpoint, método, status, duração e mensagem de erro,</p><p><strong>PARA</strong> entender exatamente o que falhou.</p></td></tr>
<tr><td><strong>Critérios de Aceitação</strong></td><td colspan="2"><ul><li><p>Critério 1: Todos os campos são gravados para cada teste.</p></li><li><p>Critério 2: Teste que falhou traz mensagem de erro.</p></li><li><p>Critério 3: O resultado não é alterado depois que a run termina.</p></li><li><p>Critério 4: Endpoint com vários casos registra um único resultado consolidado (RN-03).</p></li></ul></td></tr>
<tr><td><strong>Relacionada</strong></td><td><strong>Épico - 03 Execução e Registro</strong></td><td><strong>RN-03, RN-05, RN-07</strong></td></tr>
</tbody></table>

<table class="us"><colgroup><col style="width: 19%" /><col style="width: 58%" /><col style="width: 23%" /></colgroup><tbody>
<tr><td><strong>US - 07</strong></td><td><strong>Listar runs de uma API</strong></td><td><strong>Status: Não iniciada</strong></td></tr>
<tr><td><strong>Cartão</strong></td><td colspan="2"><p><strong>COMO</strong> dev/QA,</p><p><strong>QUERO</strong> listar as runs de uma API da mais recente para a mais antiga,</p><p><strong>PARA</strong> ver o histórico de execuções.</p></td></tr>
<tr><td><strong>Critérios de Aceitação</strong></td><td colspan="2"><ul><li><p>Critério 1: A ordem é decrescente por data de criação.</p></li><li><p>Critério 2: Cada item mostra data, status geral e totais.</p></li><li><p>Critério 3: API sem runs retorna lista vazia.</p></li><li><p>Critério 4: Runs não finalizadas aparecem com o status atual. Totais só para runs em status final.</p></li></ul></td></tr>
<tr><td><strong>Relacionada</strong></td><td><strong>Épico - 04 Consulta de Histórico</strong></td><td><strong>RN-05</strong></td></tr>
</tbody></table>

<table class="us"><colgroup><col style="width: 19%" /><col style="width: 58%" /><col style="width: 23%" /></colgroup><tbody>
<tr><td><strong>US - 08</strong></td><td><strong>Consultar detalhe da run</strong></td><td><strong>Status: Não iniciada</strong></td></tr>
<tr><td><strong>Cartão</strong></td><td colspan="2"><p><strong>COMO</strong> dev/QA,</p><p><strong>QUERO</strong> consultar uma run com todos os resultados dos testes,</p><p><strong>PARA</strong> investigar falhas.</p></td></tr>
<tr><td><strong>Critérios de Aceitação</strong></td><td colspan="2"><ul><li><p>Critério 1: Retorna os dados da run e o resultado de cada teste.</p></li><li><p>Critério 2: Testes que falharam trazem a mensagem de erro.</p></li><li><p>Critério 3: Run inexistente retorna erro claro (404).</p></li><li><p>Critério 4: Run não finalizada retorna seu status atual.</p></li><li><p>Critério 5: A resposta inclui a seed e, quando houver, a versão da spec usada.</p></li></ul></td></tr>
<tr><td><strong>Relacionada</strong></td><td><strong>Épico - 04 Consulta de Histórico</strong></td><td><strong>RN-05</strong></td></tr>
</tbody></table>

## **10.2 Requisitos Não Funcionais**

| **ID** | **Requisito** | **Categoria** | **Prioridade** |
|---|---|---|---|
| **RNF-01** | Stack: Python, FastAPI, PostgreSQL, SQLModel + Alembic, Redis + RQ, Schemathesis, Docker e pytest. | Tecnologia | Alta |
| **RNF-02** | Cobertura mínima de 85% no total e 100% de branches em domain/ e application/, medidas sobre o pacote app/ e verificadas no CI (falha abaixo disso). | Qualidade | Alta |
| **RNF-03** | GitHub Actions com 4 jobs: quality (ruff, mypy, import-linter), test (pytest com PostgreSQL e Redis em service containers e API alvo iniciada pelos testes) e build (imagem Docker, publicada no GHCR no push para main) em paralelo, e e2e (docker compose com a imagem do build) após o build. Branch protection exigindo os 4 verdes. | Qualidade | Urgente |
| **RNF-04** | docker compose up sobe hub, um único worker, Redis, PostgreSQL e API alvo sem passo manual, com migrações automáticas na subida do hub. Hub e API alvo expõem healthcheck via GET /saude, e o worker só inicia depois que o hub está saudável. | Operação | Urgente |
| **RNF-05** | Commits pequenos, com mensagens no padrão Conventional Commits. Pre-commit valida ruff e Conventional Commits. A IA aparece como coautora nos commits em que escreveu código. | Processo | Média |
| **RNF-06** | Decisões relevantes registradas em docs/adr/. | Processo | Média |
| **RNF-07** | Arquitetura hexagonal, com fronteiras de importação verificadas pelo import-linter no CI. | Arquitetura | Alta |
| **RNF-08** | Divisão de trabalho com IA conforme ADR-009 (IA escreve código mecânico, desenvolvedor escreve domínio e casos de uso), registrada no CLAUDE.md. | Processo | Média |

## **10.3 Contrato da API do Hub**

Campos inválidos ou ausentes respondem 422, com o motivo na mensagem de erro.

| **Endpoint** | **Entrada** | **Sucesso** | **Erros** | **Origem** |
|---|---|---|---|---|
| **POST /apis** | Formulário multipart com nome, base_url e exatamente um entre spec_url e spec_arquivo. | 201 com o identificador da API. | 422 para campo faltante e para spec inválida ou inacessível. | US-01, US-02 |
| **POST /runs** | JSON com api_alvo_id. | 202 com o identificador da run e status na_fila. | 404 para API inexistente. 503 para fila indisponível. | US-04 |
| **GET /apis/{id}/runs** | Identificador da API. | 200 com a lista de runs, vazia se não houver. | 404 para API inexistente. | US-07 |
| **GET /runs/{id}** | Identificador da run. | 200 com os dados da run e os resultados dos testes. | 404 para run inexistente. | US-08 |
| **GET /saude** | Nenhuma. | 200 quando o hub está de pé. | Nenhum documentado. | RNF-04 |

# **11. Decisões Arquiteturais (ADR)**

| **ID** | **Decisão** | **Situação** |
|---|---|---|
| **ADR-001** | Escolha das tecnologias (Python, FastAPI, pytest) | Aprovada |
| **ADR-002** | Banco de dados e ORM (PostgreSQL, SQLModel, Alembic) | Aprovada |
| **ADR-003** | Arquitetura do hub (Hexagonal) | Aprovada |
| **ADR-004** | CI/CD (GitHub Actions, ruff, mypy, uv, GHCR, job e2e) | Aprovada |
| **ADR-005** | Gerador de testes (Schemathesis, consolidação, seed fixa) | Aprovada |
| **ADR-006** | Execução da run (fila com Redis e RQ, worker único, status interrompida) | Aprovada |
| **ADR-007** | Armazenamento da spec (tabela de versões com hash) | Aprovada |
| **ADR-008** | API alvo (tarefas, memória, MODO_FALHA) | Aprovada |
| **ADR-009** | Uso de IA no projeto | Aprovada |

# **12. Riscos**

| **Risco** | **Mitigação** |
|---|---|
| **Crescimento de escopo (scope creep)** | Regra das versões (RN-08): nada fora da lista da v1 entra antes de ela fechar. |
| **Perfeccionismo no gerador de testes** | Somente smoke (status e schema), sem testes de lógica (RN-04). |
| **Projeto pausado ou encerrado antes da v1 por mudança de prioridades** | v1 fechada em 3 a 5 dias após a definição dos documentos. Se o projeto for pausado ou encerrado, a decisão e o estado em que ele parou são registrados no repositório. Ao fim da v1, decidir se segue para a v2. |
| **Prazo da v1 estendido pela arquitetura hexagonal, fila e divisão de trabalho com IA** | Simplificações registradas em ADR, nunca abandonadas silenciosamente. |
| **Mudanças incompatíveis na API do Schemathesis** | Versão fixada no lockfile, atualizações em PR próprio com testes do adapter. |
| **Estado da API alvo muda durante a run (requests do Schemathesis criam e apagam tarefas)** | Reinício restaura o estado; reavaliar na v2 por causa do flaky. |
| **Redis perde a fila com runs ainda em na_fila** | Limitação aceita na v1: a run permanece em na_fila e uma nova run deve ser disparada. Reconciliação avaliada na v2 (ADR-006). |

# **13. Definição de Pronto da v1**

☐ US-01 a US-08 implementadas e testadas.

☐ CI verde na branch principal.

☐ Cobertura de testes atingida (RNF-02).

☐ README com: o que é, como rodar, arquitetura resumida e seção "Como usei IA neste projeto".

☐ CLAUDE.md na raiz com as regras do projeto.

☑ ADR-001 a ADR-009 aprovados.

☐ Fronteiras da arquitetura verificadas pelo import-linter no CI.

☐ Testes E2E com MODO_FALHA ligado (run falhou) e desligado (run passou).

☐ Todos os itens da matriz de rastreabilidade do Plano de Testes cobertos por testes automatizados verdes.

# **14. Registro de Uso de IA**

## **Versão 0.2**

| **Item** | **Registro** |
|---|---|
| **O que a IA sugeriu** | Consolidar nesta versão as mudanças decorrentes dos ADR-001 a ADR-009, sugerir prioridade e tipo das RN-11 a RN-14 e prioridade das RNF-07 e RNF-08, e apontar trechos do documento que conflitam com as mudanças (RN-07, conceito de Run, US-05 e US-07) e lacunas de rastreabilidade (US-05 e US-06). A partir da modelagem do banco (DER), sugeriu a redação dos ajustes na RN-13, no conceito de Versão da spec e no critério 5 da US-08. |
| **O que aceitei** | A atualização consolidada pela IA a partir dos ADRs, após minha revisão. Resolvi os conflitos apontados: run interrompida tem fim, uma run pode terminar sem resultados de teste e as runs são listadas por data de criação. Defini que o prazo da v1 conta a partir da definição de todos os documentos. Aceitei incluir RN-03 na US-06 e RN-13 na US-05. Pela modelagem do banco (DER), defini que a versão da spec da run pode ficar vazia quando a run termina antes de resolver a spec, e aprovei a redação sugerida. |
| **O que decidi diferente** | Nenhuma divergência nesta versão. |

## **Versão 0.3**

| **Item** | **Registro** |
|---|---|
| **O que a IA sugeriu** | A lista de ajustes desta versão, a redação da RN-12 e da RN-15 e o tratamento do timeout como run interrompida com resultados descartados. |
| **O que aceitei** | As redações sugeridas, depois de revisar. |
| **O que decidi diferente** | Identifiquei na revisão do Plano de Testes as inconsistências com o ADR-004 e a ERS e a falta de status final para o timeout, e decidi conduzir eu mesmo a atualização da ERS, definindo os ajustes desta versão. A IA aplicou os ajustes no documento. |

## **Versão 0.4**

| **Item** | **Registro** |
|---|---|
| **O que a IA sugeriu** | Em uma revisão cruzada dos documentos, apontou lacunas de regra (erro interno do worker, fila indisponível no disparo, API alvo fora do ar durante a run e spec sem endpoints), a impossibilidade de usar vários workers com a recuperação atual e a falta de um contrato da API do hub, e recomendou as correções desta versão. |
| **O que aceitei** | Todas as correções recomendadas. |
| **O que decidi diferente** | Nenhuma divergência nesta versão. |

# **15. Histórico de Versões**

| **Versão** | **Data** | **Alteração** |
|---|---|---|
| **0.1** | 31/10/2026 | Criação. |
| **0.2** | 08/11/2026 | Atualização conforme ADR-001 a ADR-009 e modelagem do banco (DER). |
| **0.3** | 08/11/2026 | Ajustes conforme Plano de Testes v1.1, ADR-004 v1.2 e ADR-006 v1.1: metas de cobertura, job e2e, timeout como run interrompida (RN-12), gravação dos resultados ao final (RN-15) e referência ao Plano na Definição de Pronto. |
| **0.4** | 08/11/2026 | Revisão cruzada dos documentos: erro interno como causa de run interrompida (RN-12), fila indisponível no disparo (RN-16), API alvo inacessível (RN-03), spec sem endpoints (RN-02), worker único, ordem de subida (RNF-04), contrato da API do hub (seção 10.3), MODO_FALHA para qualquer id, risco de perda da fila e status Aprovado. |
