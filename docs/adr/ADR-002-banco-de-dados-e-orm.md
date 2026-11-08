# ADR-002: Banco de dados e ORM

## Título

Escolha de **PostgreSQL** como banco de dados e **SQLModel** com **Alembic** para acesso a dados e migrações do **Test Hub**.

## Status

Aprovada

## Data

02/11/2026

## Versão

1.1

## Proprietário ADR

Luis Henrique S. Carvalho

## Contexto

O Test Hub precisa persistir as APIs alvo cadastradas, suas specs OpenAPI e o histórico de execuções (runs) com o resultado de cada teste. O histórico nunca é sobrescrito (RN-05) e tende a crescer a cada run. A v2 prevê detecção de testes flaky, o que depende de consultas sobre esse histórico.

O ambiente inteiro deve subir com `docker compose up`, sem passo manual (RNF-04), e o CI deve rodar os testes de forma reproduzível (RNF-03). A stack já definida no ADR-001 é Python com FastAPI.

**Banco de dados, opções avaliadas:**

- **PostgreSQL:** sobe como serviço no Docker Compose e como service container no CI, oferece JSONB (útil para guardar a spec), lida bem com acesso concorrente e suporta as consultas de histórico da v2.
- **SQLite:** zero configuração e testes rápidos, mas com concorrência e tipos limitados, e provável migração forçada na v2.

**ORM e migrações, opções avaliadas:**

- **SQLAlchemy 2.x sync + Alembic:** padrão de mercado em Python, porém com modelos do ORM separados dos schemas Pydantic, o que gera mais código.
- **SQLAlchemy async + Alembic:** combina com rotas async, mas complica setup e testes sem ganho para o volume da v1.
- **SQLModel + Alembic:** criado pelo autor do FastAPI, une modelo de tabela e modelo Pydantic na mesma base, reduzindo código repetido. Por baixo usa SQLAlchemy.
- **SQL puro (psycopg) + migrações manuais:** controle total, mas reescreve o que um ORM já oferece.

## Decisão

Foi decidido utilizar **PostgreSQL** como banco de dados e **SQLModel** como camada de acesso a dados, com **Alembic** para migrações.

A escolha do **banco** foi motivada por:

- **Contexto de serviço:** o hub roda em container e pode receber runs simultâneas, cenário em que o PostgreSQL é adequado e o SQLite não.
- **JSONB:** permite armazenar a spec OpenAPI de forma estruturada (o formato exato fica para ADR própria).
- **Continuidade para a v2:** as consultas de histórico para detecção de flaky não exigirão troca de banco.
- **Integração com o ambiente:** sobe no Docker Compose e no CI sem instalação local.

A escolha do **SQLModel** foi motivada por:

- **Integração com FastAPI e Pydantic:** o mesmo ecossistema da stack do ADR-001, com modelos que servem tanto ao banco quanto à validação.
- **Menos código repetido:** evita manter duas hierarquias paralelas (ORM e Pydantic) para entidades simples, o que favorece o prazo da v1.
- **Base em SQLAlchemy:** quando o SQLModel não cobrir um caso, é possível usar SQLAlchemy diretamente, sem trocar de ferramenta.

O **Alembic** foi escolhido por ser a ferramenta de migração padrão do ecossistema SQLAlchemy, compatível com o SQLModel.

O acesso ao banco será **síncrono** na v1. A eventual necessidade de acesso assíncrono será avaliada no ADR de execução dos testes.

Alternativas descartadas:

- **SQLite:** adequado a apps locais de um único usuário, mas não ao cenário de serviço e histórico crescente do Test Hub.
- **SQLAlchemy puro (sync ou async):** mais maduro e mais comum em vagas, porém com mais código para o escopo da v1.
- **SQL puro:** custo de implementação incompatível com o prazo.

## Consequências

### Positivas

- Ambiente de desenvolvimento, CI e execução usam o mesmo banco, reduzindo diferenças de comportamento.
- Menos código de modelagem graças à integração do SQLModel com Pydantic.
- Esquema do banco versionado e reproduzível via migrações do Alembic.
- Base preparada para as consultas de histórico da v2.

### Negativas

- SQLModel é menos maduro que o SQLAlchemy puro, com documentação menos completa. Casos mais complexos exigirão recorrer ao SQLAlchemy diretamente.
- Usar a mesma classe como tabela e como schema da API pode vazar campos internos se não houver disciplina na separação dos modelos.
- Testes de integração com PostgreSQL são mais lentos e exigem um banco rodando no CI.
- SQLModel aparece menos em vagas do que SQLAlchemy.

## Conformidade

- Todo acesso ao banco deve passar pelo SQLModel (ou SQLAlchemy, quando necessário), sem SQL montado por concatenação de strings.
- Modelos de tabela (`table=True`) devem ser separados dos modelos de entrada e saída da API, para que campos internos não sejam expostos.
- Toda mudança de esquema deve ser feita por migração do Alembic versionada no repositório. É proibido alterar o banco manualmente.
- As migrações devem rodar automaticamente na subida do container do hub, atendendo ao RNF-04.
- O template de migração do Alembic deve importar `sqlmodel`, para que migrações geradas automaticamente com tipos do SQLModel funcionem.
- Os testes de integração devem rodar contra PostgreSQL, não contra SQLite.
- Qualquer troca de banco ou de ORM deve ser formalizada em nova ADR que substitua esta.

## Observações

- O formato de armazenamento da spec (JSONB na tabela da API, tabela de versões ou outro) será decidido em ADR própria.
- Se o ADR de execução dos testes exigir acesso assíncrono ao banco, esta decisão deve ser revisitada.
- Se o SQLModel se mostrar limitante durante a v1, a migração para SQLAlchemy puro é de baixo custo, pois ele já é a base do SQLModel.

## Direcionadores

- **f4: Velocidade de desenvolvimento.** SQLModel reduz o código de modelagem e o Alembic automatiza a evolução do esquema.
- **f7: Confiabilidade.** PostgreSQL garante consistência transacional e suporta acesso concorrente às runs.
- **f44: Redução da dívida técnica.** Migrações versionadas e um único banco em todos os ambientes evitam divergências.
- **f39: Reduzir custos.** Todas as tecnologias são open source e rodam em container, sem infraestrutura dedicada.
- **f11: Testabilidade.** O banco sobe em container tanto localmente quanto no CI, permitindo testes de integração reais.

## Histórico de versões

| Versão | Data | Alteração |
| --- | --- | --- |
| 1.0 | 02/11/2026 | Criação. |
| 1.1 | 02/11/2026 | Remoção de referências a projeto anterior. |

## Registro de uso de IA

- **O que a IA sugeriu:** comparou PostgreSQL e SQLite, recomendando PostgreSQL. Para ORM, comparou SQLAlchemy sync, SQLAlchemy async, SQLModel e SQL puro, e recomendou SQLAlchemy 2.x sync com Alembic, citando maturidade e presença em vagas.
- **O que aceitei:** PostgreSQL como banco, Alembic para migrações e acesso síncrono na v1.
- **O que decidi diferente:** escolhi SQLModel em vez do SQLAlchemy puro recomendado pela IA, priorizando a integração com FastAPI e Pydantic e a redução de código no prazo da v1.
