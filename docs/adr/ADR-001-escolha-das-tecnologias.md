# ADR-001: Escolha das tecnologias

## Título

Escolha de **Python** como linguagem, **FastAPI** como framework web e **pytest** como framework de testes do **Test Hub**.

## Status

Aprovada

## Data

31/10/2026

## Versão

1.1

## Proprietário ADR

Luis Henrique S. Carvalho

## Contexto

O Test Hub é um serviço que lê a spec OpenAPI de uma API alvo, gera smoke tests (status e schema da resposta), executa e guarda o histórico. A v1 tem prazo de 3 a 5 dias e precisa sair com CI verde, cobertura alta e ambiente subindo via Docker Compose (RNF-02, RNF-03, RNF-04).

A escolha da stack precisava considerar:

- **Afinidade com o domínio:** o projeto gira em torno de OpenAPI e JSON Schema, então o ecossistema da linguagem para esses padrões pesa.
- **Prazo curto:** a stack não pode exigir aprendizado do zero.
- **Testabilidade:** o projeto é peça de portfolio de QA/SDET, testes são o produto e a vitrine.
- **Mercado:** a stack deve ser relevante para vagas de backend e QA/SDET.

As opções avaliadas foram:

- **Python + FastAPI + pytest:** OpenAPI gerada automaticamente pelo framework, validação de dados nativa via Pydantic, ecossistema forte de bibliotecas de OpenAPI e JSON Schema, e familiaridade prévia com a stack.
- **Python + Flask:** mesma linguagem, mas sem OpenAPI nem validação nativas, exigindo plugins para atender ao básico.
- **Java + Spring Boot + JUnit + RestAssured:** stack muito presente em vagas de QA/SDET no Brasil, porém exigiria aprendizado durante o desenvolvimento, incompatível com o prazo da v1.
- **TypeScript + Node (Fastify ou NestJS) + Vitest:** viável, mas sem ganho claro sobre Python para este problema e com ecossistema de ferramentas OpenAPI menor.

## Decisão

Foi decidido utilizar **Python** com **FastAPI** para o serviço e **pytest** para os testes do próprio hub.

A escolha foi motivada por:

- **OpenAPI nativa no FastAPI:** o hub expõe a própria spec sem esforço extra, o que documenta a API do hub e mantém o projeto coerente com o que ele testa.
- **Validação com Pydantic:** entradas e saídas da API do hub são validadas e tipadas na borda, reduzindo código manual de validação.
- **Ecossistema Python para OpenAPI e JSON Schema:** as bibliotecas candidatas para leitura de spec e validação de schema estão em Python (a escolha específica fica para ADR própria).
- **pytest:** fixtures, parametrização e plugins de cobertura atendem ao RNF-02 e ao CI. O detalhamento de como os testes são organizados fica no plano de testes.
- **Familiaridade prévia:** experiência anterior com Python e FastAPI reduz o risco de não cumprir o prazo da v1.

Alternativas descartadas:

- **Flask:** descartado por demandar plugins para entregar o que o FastAPI já oferece nativamente.
- **Java + Spring Boot:** descartado para a v1 por causa da curva de aprendizado dentro do prazo. Continua sendo opção relevante para projetos futuros de portfolio.
- **TypeScript + Node:** descartado por não trazer vantagem sobre Python neste domínio.

Banco de dados e ORM ficam fora deste ADR e serão decididos em ADR própria.

## Consequências

### Positivas

- Entrega mais rápida da v1, pela familiaridade com a stack e pelos recursos nativos do FastAPI.
- API do hub documentada automaticamente via OpenAPI (Swagger), facilitando uso e testes manuais.
- Validação de entrada padronizada pelo Pydantic, com erros consistentes para o usuário.
- Base de testes com pytest bem suportada no CI e com medição de cobertura direta.

### Negativas

- Tipagem do Python é verificada só em tempo de execução, a menos que se adote checagem estática (decisão do ADR de CI/CD).
- Código assíncrono no FastAPI exige disciplina para não misturar chamadas bloqueantes em rotas async.
- A stack não demonstra Java, que é frequente em vagas de QA/SDET no mercado brasileiro.

## Conformidade

- O serviço do hub deve ser implementado em Python com FastAPI, sem outro framework web.
- Toda rota do hub deve ter modelos Pydantic de entrada e saída, para que a spec OpenAPI gerada seja completa.
- Os testes do hub devem ser escritos com pytest e executados no CI.
- Versões de Python e dependências devem ser fixadas no projeto.
- Substituir qualquer tecnologia deste ADR exige uma nova ADR que substitua esta, total ou parcialmente.

## Observações

- Este ADR pode ser revisitado se a v3 (APIs públicas externas) trouxer requisitos que a stack não atenda bem.
- A spec OpenAPI do próprio hub poderá servir futuramente como alvo de teste, mas isso está fora do escopo da v1 (RN-08, RN-10).
- Banco de dados e ORM, arquitetura e CI/CD serão registrados em ADRs separadas.

## Direcionadores

- **f4: Velocidade de desenvolvimento.** Stack conhecida e recursos nativos do FastAPI (OpenAPI, validação) encurtam a entrega da v1.
- **f11: Testabilidade.** pytest e a injeção de dependências do FastAPI facilitam testes isolados das rotas e serviços.
- **f44: Redução da dívida técnica.** Modelos Pydantic e spec gerada automaticamente evitam documentação desatualizada.
- **f39: Reduzir custos.** Todas as tecnologias são open source.
- **f38: Economizar tempo.** Swagger gerado automaticamente reduz o esforço de documentar e testar manualmente a API do hub.

## Histórico de versões

| Versão | Data | Alteração |
| --- | --- | --- |
| 1.0 | 31/10/2026 | Criação. |
| 1.1 | 02/11/2026 | Remoção de referências a projeto anterior. |

## Registro de uso de IA

- **O que a IA sugeriu:** comparou quatro stacks (Python + FastAPI, Python + Flask, Java + Spring Boot, TypeScript + Node) e recomendou Python + FastAPI + pytest. Também apontou Java como relevante para o mercado de QA/SDET e sugeriu manter CI/CD em ADR separada.
- **O que aceitei:** a recomendação de stack e a separação do CI/CD em ADR própria.
- **O que decidi diferente:** cheguei a propor incluir o banco neste ADR e a IA concordou, mas depois mudei de ideia e decidi tirar banco e ORM daqui e registrá-los juntos em ADR própria. Também decidi manter pytest neste ADR em vez de criar um ADR só para o framework de testes, deixando o detalhamento para o plano de testes.
