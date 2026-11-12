# Plano de Testes

| **Projeto** | Test Hub | **Versão do produto** | v1 |
| --- | --- | --- | --- |
| **Versão do documento** | 1.4 | **Data** | 11/11/2026 |
| **Autor** | Luís Henrique Souza Carvalho | **Status** | Aprovado |

## 1. Objetivos

Assegurar que o Test Hub entregue comportamento correto, reproduzível e estável, validando as regras de negócio, os critérios de aceitação das estórias de usuário e as decisões registradas nos ADRs por meio de testes automatizados executados a cada Pull Request.

A estratégia privilegia o domínio (consolidação de resultados, status da run, imutabilidade e versionamento da spec), a integração dos adapters com a infraestrutura real (PostgreSQL, Redis, Schemathesis e HTTP) e a verificação do ambiente completo subindo via Docker Compose.

Como o Test Hub é um serviço sem interface gráfica, não há testes de UI. O "usuário" do sistema é quem consome a API do hub.

## 2. Escopo e Níveis de Teste

### 2.1 Testes Unitários

- **O que cobrem:** `domain/` e `application/` (ADR-003). Entidades, regras de negócio (RN-03 a RN-07 e RN-11 a RN-16) e casos de uso.
- **Como:** casos de uso exercitados com adapters falsos em memória para todas as portas (`GeradorDeTestes`, `ExecutorDeRun`, repositórios, carregador de spec). Sem banco, sem rede, sem FastAPI.
- **Também entram:** normalização da spec e cálculo do hash (ADR-007), que são lógica pura.
- **Marcador:** `@pytest.mark.unit`. Rodam em segundos, sem Docker.

### 2.2 Testes de Integração

Cada adapter de saída tem testes próprios contra a dependência real (ADR-003, Conformidade).

- **Persistência:** repositórios SQLModel contra PostgreSQL, com o esquema criado pelas migrações do Alembic (ADR-002). Inclui unicidade de (API alvo, hash) e bloqueio de alteração de run finalizada.
- **Gerador:** adapter do Schemathesis contra a API alvo real, cobrindo os cinco cenários exigidos no ADR-005: todos os casos passando, um caso falhando, endpoint sem schema de resposta, reprodutibilidade com a mesma seed e API alvo inacessível.
- **API alvo nos testes:** uma fixture sobe a API alvo com uvicorn em subprocesso, inclusive no job `test` do CI (ADR-004). O cenário de caso falhando usa uma instância com `MODO_FALHA` ligado.
- **Fila:** adapter RQ e worker contra Redis real. Ao menos um teste executa uma run completa com Redis e worker reais (ADR-006). Também cobre as três causas de run `interrompida`: worker reiniciado, tempo máximo excedido (com tempo máximo reduzido no teste) e erro interno do hub.
- **Carregador de spec:** download e validação de spec por URL, incluindo falha de download e spec inválida (ADR-007).
- **Rotas HTTP:** endpoints do hub exercitados via `TestClient`, com banco real, validando status, corpo e mensagens de erro. São os testes que verificam a maior parte dos critérios de aceitação das estórias.
- **Marcador:** `@pytest.mark.integration`. Exigem PostgreSQL e Redis no ar.

### 2.3 Testes End-to-End (E2E)

- **O que cobrem:** o ambiente completo subindo com `docker compose up` (hub, worker, Redis, PostgreSQL e API alvo), sem passo manual (RNF-04).
- **Cenários:** poucos e focados em fluxo completo: cadastrar a API alvo, disparar a run, acompanhar até o status final e consultar o detalhe. Uma vez com `MODO_FALHA` desligado (espera `passou`) e uma vez ligado (espera `falhou`), conforme o ADR-008. Entre os cenários, o serviço da API alvo é recriado com o novo valor da variável.
- **Como:** cliente HTTP externo ao Compose, com polling da run até status final e tempo limite definido. Sem `sleep` fixo.
- **Marcador:** `@pytest.mark.e2e`. Rodam no job `e2e` do CI (ADR-004).

### 2.4 Testes Estáticos e de Arquitetura

Não executam o código, mas fazem parte da suíte e quebram o build:

- **import-linter:** fronteiras da hexagonal (ADR-003), isolamento do Schemathesis (ADR-005), do RQ/Redis (ADR-006) e separação entre hub e API alvo (ADR-008).
- **mypy:** modo estrito em `domain/` e `application/` (ADR-004).
- **ruff:** lint e formatação (ADR-004).

### 2.5 Testes de Regressão

A suíte inteira roda a cada Pull Request, e a branch protection impede merge com qualquer job vermelho (ADR-004). Não há execução noturna na v1: o projeto não tem dependência externa que mude sem commit, então a execução por PR já cobre a regressão.

Todo defeito corrigido ganha um teste que reproduz o cenário (seção 7).

### 2.6 Fora do escopo da v1

- Testes de carga e desempenho.
- Testes de segurança (não há autenticação na v1).
- Mutation testing.
- Detecção de flaky (v2).
- O hub testando a própria spec (ADR-001, Observações).
- Suíte própria para a API alvo: ela é exercitada pelos testes de integração e E2E do hub. A exceção é a verificação de conformidade descrita no NF-05.

## 3. Ferramentas

| Ferramenta | Uso | Nível |
| --- | --- | --- |
| **pytest** | Runner, fixtures, parametrização e marcadores (ADR-001). | Todos |
| **pytest-cov** | Medição de cobertura e `fail-under` (RNF-02), somente sobre `app/`. | Todos |
| **FastAPI TestClient (httpx)** | Chamadas às rotas do hub sem subir servidor. | Integração |
| **respx** | Simulação de respostas HTTP no teste do carregador de spec (spec fora do ar, conteúdo inválido). | Integração |
| **Hypothesis** | Propriedades da normalização da spec: ordem de chaves e formato (YAML ou JSON) não alteram o hash. Já vem como dependência do Schemathesis. | Unitário |
| **time-machine** | Controle do relógio para validar início, fim e duração (RN-07) de forma determinística. | Unitário |
| **RQ (modo imediato)** | Execução síncrona no próprio processo, dispensando o worker nos testes do adapter que não precisam dele. Continua usando Redis real (ADR-006). | Integração |
| **PostgreSQL e Redis** | Service containers no CI (ADR-004) e serviços do Compose localmente. Nada de SQLite (ADR-002). | Integração |
| **Docker Compose** | Ambiente completo dos testes E2E. | E2E |
| **import-linter, mypy, ruff** | Verificações estáticas e de arquitetura (ADR-003 e ADR-004). | Estático |

**Justificativa resumida:** todas as ferramentas são do ecossistema pytest ou já estão definidas nos ADRs. As únicas adições de fora são o respx, escolhido por simular erros HTTP de forma declarativa, e o time-machine, por tornar testes com tempo determinísticos sem alterar o código de produção.

## 4. Modelo Estratégico de Testes

O Test Hub adota a **Pirâmide de Testes**. A arquitetura hexagonal (ADR-003) isola as regras de negócio em código puro, o que permite uma base larga de testes unitários rápidos e sem instabilidade. Os testes de integração validam cada adapter contra a infraestrutura real, e os E2E ficam restritos aos fluxos completos que provam que o ambiente funciona de ponta a ponta.

| Nível | Volume esperado | Tempo de execução | Instabilidade |
| --- | --- | --- | --- |
| **Unitário** | Maior parte da suíte | Segundos | Nenhuma (sem I/O) |
| **Integração** | Um conjunto por adapter e por rota | Dezenas de segundos | Baixa (infraestrutura em container) |
| **E2E** | 2 cenários principais | Minutos | Média (ambiente completo) |

**Regras de determinismo:**

- Seed fixa do gerador em todos os testes (ADR-005).
- API alvo sempre sobe no mesmo estado (ADR-008).
- Tempo controlado com time-machine nos testes que medem duração.
- Esperas sempre por condição com tempo limite, nunca por `sleep` fixo.
- Cada teste de integração limpa os próprios dados. Testes que envolvem o worker em outro processo usam limpeza por truncamento, já que transação com rollback não é visível entre processos.

## 5. Responsabilidades

Segue a divisão definida no ADR-009:

| Testes | Quem define os casos | Quem escreve | Revisão |
| --- | --- | --- | --- |
| **Domínio e casos de uso** (`tests/unit/`) | IA, a partir dos IDs da matriz (ADR-009 v1.2) | IA | Desenvolvedor confere se cada teste verifica o que o nome diz |
| **Adapters e rotas** (`tests/integration/`) | IA, a partir dos critérios de aceitação e da Conformidade dos ADRs | IA | Desenvolvedor lê todo o código |
| **E2E** (`tests/e2e/`) | Desenvolvedor | IA | Desenvolvedor |
| **Configuração** (pytest, cobertura, CI) | IA | IA | Desenvolvedor |

Nenhum teste é integrado sem que o desenvolvedor saiba explicar o que ele verifica e por que ele falharia (ADR-009). Teste que passa pelo motivo errado é tratado como defeito.

## 6. Critérios de Aceitação

- Nenhuma estória é considerada "Finalizada" sem os testes listados para ela na matriz de rastreabilidade (seção 8), todos verdes.
- Toda regra de negócio implementada no domínio (RN-03 a RN-07 e RN-11 a RN-16) tem teste unitário, incluindo os casos de borda.
- Todo endpoint do hub tem teste de integração para o caminho de sucesso e para cada erro documentado.
- Todo item de Conformidade dos ADRs que exige teste tem ao menos um teste correspondente.
- **Cobertura:** mínimo de 85% de linhas no projeto inteiro e 100% de branches em `domain/` e `application/` (RNF-02 e ADR-004), medidas somente sobre `app/`. As duas metas são aplicadas como `fail-under` no CI, não apenas reportadas.
- Os quatro jobs do CI (`quality`, `test`, `build` e `e2e`) precisam estar verdes na `main` (RNF-03 e ADR-004).

## 7. Registro de Defeitos

- Os defeitos são registrados em **GitHub Issues** e acompanhados no **GitHub Projects**.
- Cada issue de defeito contém: título claro, passos para reproduzir, resultado obtido, resultado esperado e evidências (log, resposta HTTP ou saída do teste). Um template de issue fica em `.github/ISSUE_TEMPLATE/`.
- Classificação por labels:
  - **Severidade:** Crítica, Alta, Média e Baixa.
  - **Prioridade:** Urgente, Alta, Média e Baixa (mesma escala da ERS).
- A issue é vinculada à estória ou à RN afetada e ao Pull Request da correção (`Fixes #n`).
- Um defeito só é fechado quando existe um teste automatizado que reproduz o cenário, falha antes da correção e passa depois. O teste referencia a issue no nome (ex.: `test_issue_12_run_finalizada_aceita_novo_resultado`).

## 8. Matriz de Rastreabilidade

Os critérios de aceitação são verificados diretamente pelos testes automatizados, sem documento separado de casos de teste. O relatório do pytest no CI serve como evidência de execução de cada item.

**Regras dos IDs:**

- **USxx-Cn:** critério `n` da estória `US-xx`, com a **mesma numeração da ERS**. Ex.: o critério 4 da US-04 é `US04-C4`.
- **RNxx-Tn:** teste `n` de uma regra de negócio que não está coberta por nenhum critério de estória.
- **NF-n e E2E-n:** verificações não funcionais e cenários ponta a ponta.
- O ID vai no início do nome da função de teste, em minúsculas: `test_us04_c4_disparo_responde_202`. Um ID pode ter mais de um teste (ex.: casos parametrizados ou caminhos diferentes da mesma regra).

### 8.1 Critérios de aceitação das estórias

| ID | Critério | Nível | Origem |
| --- | --- | --- | --- |
| **US01-C1** | Nome, base URL e spec são obrigatórios (422 indicando o campo faltante). | Integração | US-01 |
| **US01-C2** | Spec aceita por URL e por arquivo. | Integração | US-01 |
| **US01-C3** | Cadastro retorna 201 com o identificador da API. | Integração | US-01 |
| **US02-C1** | Spec inválida é rejeitada e nada é gravado (nem API, nem versão). | Unitário, Integração | US-02, RN-01 |
| **US02-C2** | Mensagem de erro informa o motivo da rejeição. | Integração | US-02, RN-02 |
| **US02-C3** | Spec válida é aceita e associada à API. | Integração | US-02 |
| **US02-C4** | Spec válida é salva como versão, com hash. | Integração | US-02, RN-13 |
| **US02-C5** | A mesma validação do cadastro é aplicada no início de cada run de spec por URL. | Unitário | US-02, RN-02 |
| **US03-C1** | Um resultado consolidado por par endpoint e método: "passou" só se todos os casos passaram, mensagem do primeiro caso que falhou e duração igual à soma dos casos. | Unitário | US-03, RN-03 |
| **US03-C2** | Apenas as verificações de status e de schema da resposta estão ativas. | Integração | US-03, RN-04 |
| **US03-C3** | Endpoint sem schema de resposta verifica apenas o status. | Integração | US-03 |
| **US03-C4** | Mesma spec e mesma seed geram os mesmos casos. | Integração | US-03, RN-14 |
| **US04-C1** | Run para API inexistente retorna 404 e nada é enfileirado. | Integração | US-04 |
| **US04-C2** | Todos os testes gerados são executados pelo worker contra a base URL, com Redis e worker reais. | Integração | US-04, ADR-006 |
| **US04-C3** | Ao final, a run possui status geral `passou` ou `falhou`. | Unitário, Integração | US-04, RN-06 |
| **US04-C4** | O disparo responde 202 com o identificador e status `na_fila`, sem aguardar a execução. | Integração | US-04, RN-11 |
| **US04-C5** | Spec por URL inacessível ou inválida no início da run resulta em `falhou`, com motivo, sem resultados de teste e sem `spec_versao`. | Unitário, Integração | US-04, RN-06, RN-13 |
| **US04-C6** | Com a fila indisponível, o disparo responde 503 e a run não permanece registrada. | Unitário, Integração | US-04, RN-16, ADR-006 |
| **US05-C1** | Início e fim são gravados para toda run em status final, inclusive `interrompida` (por reinício do worker, por tempo excedido e por erro interno). | Unitário, Integração | US-05, RN-07, RN-12 |
| **US05-C2** | Status geral "passou" somente se todos os testes passaram. | Unitário | US-05, RN-06 |
| **US05-C3** | Totais de passou e falhou conferem com os resultados individuais. | Unitário | US-05 |
| **US05-C4** | Transições de status seguem a RN-11; transições fora dela são rejeitadas. | Unitário | US-05, RN-11 |
| **US06-C1** | Endpoint, método, status, duração e mensagem são gravados para cada teste. | Integração | US-06, RN-07 |
| **US06-C2** | Teste que falhou traz mensagem de erro. | Unitário | US-06 |
| **US06-C3** | Resultados não são alterados depois que a run termina. | Unitário, Integração | US-06, RN-05 |
| **US06-C4** | Endpoint com vários casos grava um único resultado consolidado. | Integração | US-06, RN-03 |
| **US07-C1** | Lista em ordem decrescente por data de criação. | Integração | US-07 |
| **US07-C2** | Cada item traz data, status geral e totais. | Integração | US-07 |
| **US07-C3** | API sem runs retorna lista vazia. | Integração | US-07 |
| **US07-C4** | Runs não finalizadas aparecem com o status atual; totais só para runs em status final. | Integração | US-07, RN-11 |
| **US08-C1** | Detalhe traz os dados da run e o resultado de cada teste. | Integração | US-08 |
| **US08-C2** | Testes que falharam trazem a mensagem de erro. | Integração | US-08 |
| **US08-C3** | Run inexistente retorna 404. | Integração | US-08 |
| **US08-C4** | Run não finalizada retorna seu status atual, sem resultados. | Integração | US-08, RN-11 |
| **US08-C5** | Resposta inclui a seed e, quando houver, a versão da spec usada (nula quando a run terminou antes de resolver a spec). | Integração | US-08, RN-13, RN-14 |

### 8.2 Regras de negócio sem critério de estória

| ID | Verificação | Nível | Origem |
| --- | --- | --- | --- |
| **RN02-T1** | Spec sem nenhum endpoint é rejeitada no cadastro e, se baixada no início da run, resulta em `falhou`. | Unitário, Integração | RN-02, ADR-007 |
| **RN03-T1** | API alvo inacessível durante a run: cada endpoint termina `falhou` com a mensagem do erro, e a run termina `falhou`. | Integração | RN-03, ADR-005 |
| **RN05-T1** | Run em status final não aceita mudança de status. | Unitário, Integração | RN-05, ADR-006 |
| **RN11-T1** | Nenhuma rota do hub permite alterar o status de uma run; só o caso de uso executado pelo worker muda o status a partir de `na_fila`. | Unitário, Integração | RN-11, ADR-006 |
| **RN12-T1** | Ao iniciar, o worker marca como `interrompida` toda run presa em `em_execucao`, com fim e motivo registrados. | Integração | RN-12, ADR-006 |
| **RN12-T2** | Run que excede o tempo máximo configurado termina como `interrompida`, com fim registrado e motivo de tempo excedido. | Integração | RN-12, ADR-006 |
| **RN12-T3** | Exceção inesperada do hub durante a execução termina a run como `interrompida`, com fim e motivo registrados, nunca como `falhou`. | Unitário, Integração | RN-12, ADR-006 |
| **RN13-T1** | Run com resultados de teste sempre tem `spec_versao` preenchida. | Unitário, Integração | RN-13, ADR-007 |
| **RN13-T2** | Spec por URL: hash novo cria nova versão; hash existente reutiliza a versão. | Unitário, Integração | RN-13, ADR-007 |
| **RN13-T3** | Spec por arquivo usa a versão mais recente. | Unitário | RN-13, ADR-007 |
| **RN13-T4** | Mesma spec em YAML e em JSON, com chaves em qualquer ordem, gera o mesmo hash. | Unitário | RN-13, ADR-007 |
| **RN13-T5** | Versão de spec não pode ser alterada, e versão referenciada por run não pode ser removida. | Integração | RN-13, ADR-007 |
| **RN14-T1** | A seed é configurável e cada run registra a seed com que foi executada. | Unitário, Integração | RN-14, ADR-005 |
| **RN15-T1** | Resultados e totais são gravados na mesma transação que finaliza a run; run interrompida no meio da execução não tem resultados e tem totais zerados. | Integração | RN-15, ADR-006 |

### 8.3 Requisitos não funcionais e cenários E2E

| ID | Verificação | Nível | Origem |
| --- | --- | --- | --- |
| **NF-01** | Fronteiras de importação da arquitetura respeitadas. | Estático | RNF-07, ADR-003, 005, 006, 008 |
| **NF-02** | mypy estrito sem erros em `domain/` e `application/`. | Estático | ADR-004 |
| **NF-03** | Cobertura de 85% no total e 100% de branches em `domain/` e `application/`. | CI | RNF-02, ADR-004 |
| **NF-04** | Migrações do Alembic criam o esquema do zero em banco vazio. | Integração | ADR-002 |
| **NF-05** | Spec da API alvo declara as respostas de erro esperadas (404), `MODO_FALHA` vem desligado por padrão, `GET /saude` não é afetado por ele e, com ele ligado, `GET /tarefas/{id}` responde com tipos errados para qualquer `id`. | Integração | ADR-008 |
| **NF-06** | `GET /saude` do hub responde 200. | Integração | RNF-04 |
| **E2E-01** | `docker compose up` sobe o ambiente sem passo manual, com o worker iniciando após o hub saudável, e uma run com `MODO_FALHA` desligado termina `passou`. | E2E | RNF-04, ADR-006, ADR-008 |
| **E2E-02** | Com `MODO_FALHA` ligado, a run termina `falhou` e o detalhe aponta os endpoints com erro. | E2E | ADR-008 |

## 9. Ambiente e Execução

**Estrutura de pastas:**

```
tests/
  unit/
    domain/
    application/
  integration/
    persistence/
    generator/
    queue/
    spec_loader/
    http/
  e2e/
  conftest.py
```

**Execução local:**

- `uv run pytest -m unit`: sem Docker, para o ciclo rápido de desenvolvimento.
- `docker compose up -d postgres redis` e `uv run pytest -m "unit or integration"`: suíte do job de testes. A API alvo é iniciada pela fixture.
- `uv run pytest -m e2e`: com o ambiente completo no ar via `docker compose up`.

**Execução no CI (GitHub Actions):**

- Job `test` (ADR-004): unitários e integração, com PostgreSQL e Redis em service containers, API alvo iniciada pela fixture, cobertura com `fail-under` e relatório em JUnit XML publicado como artefato.
- Job `e2e` (ADR-004): após o `build`, sobe o Compose com a imagem gerada e roda os cenários E2E.

## 10. Observações

- Este plano pode ser atualizado a qualquer momento para refletir mudanças de escopo ou de arquitetura, com registro no histórico de versões.
- **Dependência da ERS v0.6:** este plano considera a meta de cobertura do RNF-02, os quatro jobs do RNF-03, a RN-12 com as três causas de run `interrompida`, a RN-15 (gravação dos resultados ao final), a RN-16 (fila indisponível no disparo), o contrato da API do hub e a referência a este plano na Definição de Pronto.
- **Regra de sincronia:** os IDs da matriz seguem a numeração da ERS. Qualquer mudança de numeração ou redação de critério na ERS exige atualizar a matriz antes de renomear ou escrever testes.

## 11. Histórico de versões

| Versão | Data | Alteração |
| --- | --- | --- |
| 1.0 | 07/11/2026 | Criação. |
| 1.1 | 08/11/2026 | Matriz alinhada à numeração da ERS v0.2, com IDs próprios para regras de negócio (RNxx-Tn). Inclusão dos testes de run interrompida por tempo excedido, da gravação dos resultados ao final, da obrigatoriedade de `spec_versao` em run com resultados (ADR-007 v1.1) e dos critérios US05-C1 e US08-C5. Job `e2e` e meta de cobertura alinhados ao ADR-004 v1.2. |
| 1.2 | 08/11/2026 | Alinhamento à ERS v0.4 e aos ADRs revisados: novos testes US04-C6, RN02-T1, RN03-T1, RN12-T3 e NF-06, API alvo iniciada por fixture, cobertura somente sobre `app/`, correção do modo imediato do RQ e status Aprovado. |
| 1.3 | 11/11/2026 | Seção 5 alinhada ao ADR-009 v1.1: testes dos casos de uso escritos pela IA a partir da matriz, conferidos pelo desenvolvedor, e dependência atualizada para a ERS v0.5. |
| 1.4 | 11/11/2026 | Seção 5 alinhada ao ADR-009 v1.2: testes do domínio também escritos pela IA a partir da matriz, conferidos pelo desenvolvedor, e dependência atualizada para a ERS v0.6. |

## 12. Registro de uso de IA

- **O que a IA sugeriu:** adaptar a estrutura de um plano de testes de projeto anterior para um serviço sem interface, trocando testes de UI por E2E com Docker Compose; organizar os níveis de teste seguindo as camadas da hexagonal; adotar a Pirâmide de Testes; cobertura de 85% global com 100% de branches no domínio; registrar as ferramentas dentro do plano em vez de documentos separados; e manter casos de teste detalhados em um documento próprio. Também propôs as ferramentas complementares (respx, Hypothesis e time-machine), o job `e2e` no CI e a matriz de rastreabilidade com os ajustes dos ADRs 005 a 008.
- **O que aceitei:** a Pirâmide, as metas de cobertura, as ferramentas dentro do plano e a adaptação geral da estrutura.
- **O que decidi diferente:** questionei a necessidade de um documento de casos de teste detalhados. Ficou decidido que a matriz de rastreabilidade, com o ID do critério no nome de cada teste automatizado, substitui esse documento.
- **v1.1:** na revisão, identifiquei que o plano criava o job `e2e` e a meta de 100% sem atualizar o ADR-004 e a ERS, que a matriz tinha numeração diferente da ERS, que faltavam critérios da ERS v0.2 e o teste exigido pelo ADR-007 v1.1, e que ninguém definia o status final de uma run que excede o tempo máximo. A IA recomendou `interrompida` com motivo para o timeout, descartar resultados parciais (gravação apenas ao final), manter o job `e2e` no CI e separar os IDs de regras de negócio (RNxx-Tn) dos IDs de critérios de estória. Aceitei as recomendações e decidi atualizar a ERS eu mesmo.
- **v1.2:** em uma revisão cruzada dos documentos, a IA apontou lacunas de regra (erro interno do worker, fila indisponível, API alvo fora do ar e spec sem endpoints), a falta da API alvo no job `test` e divergências sobre o modo imediato do RQ, e recomendou os ajustes desta versão. Aceitei.
- **v1.3:** a IA apontou que a seção 5 descrevia a divisão antiga do ADR-009 e redigiu o ajuste. A mudança da divisão foi decisão minha (ADR-009 v1.1).
- **v1.4:** a IA redigiu o ajuste da seção 5 a partir do ADR-009 v1.2. A mudança da divisão foi decisão minha.
