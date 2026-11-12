# Test Hub

Hub que lê a spec OpenAPI de uma API, gera smoke tests (status e schema da resposta) com Schemathesis, executa as runs em fila e guarda o histórico de cada execução.

Escopo da v1 na [ERS](docs/ers/Test-Hub-ERS-v0.6.md): cadastro da API alvo com validação da spec, geração dos testes, execução assíncrona com worker e consulta do histórico. A API alvo é uma API de tarefas do próprio projeto ([ADR-008](docs/adr/ADR-008-api-alvo.md)).

## Como rodar

Pré-requisito: Docker com Compose.

```bash
cp .env.example .env              # opcional: muda portas e padrões
docker compose up -d --build --wait
```

Sobem o hub, um worker, PostgreSQL, Redis e a API alvo, com as migrações aplicadas na subida do hub.

| Serviço | URL |
| --- | --- |
| Hub (Swagger) | http://localhost:8000/docs |
| API alvo | http://localhost:8001/docs |

### Exemplo de uso

```bash
# Cadastra a API alvo. Dentro do Compose, o hub a encontra em target-api:8000.
curl -F nome=tarefas \
     -F base_url=http://target-api:8000 \
     -F spec_url=http://target-api:8000/openapi.json \
     http://localhost:8000/apis
# {"id":1}

# Dispara uma run. Responde na hora, com a run na fila.
curl -H 'Content-Type: application/json' -d '{"api_alvo_id": 1}' http://localhost:8000/runs
# {"id":1,"status":"na_fila"}

# Acompanha a run até passou, falhou ou interrompida, com o resultado por endpoint.
curl http://localhost:8000/runs/1

# Histórico da API, da run mais recente para a mais antiga.
curl http://localhost:8000/apis/1/runs
```

A spec também pode ser enviada como arquivo (`-F spec_arquivo=@openapi.yaml`). Para ver o hub apontando falhas, suba a API alvo com `MODO_FALHA=true`:

```bash
MODO_FALHA=true docker compose up -d --force-recreate --wait target-api
```

### Contrato da API do hub

| Endpoint | Sucesso | Erros |
| --- | --- | --- |
| `POST /apis` | 201 com o id da API | 422 para campo faltante ou spec inválida ou inacessível |
| `POST /runs` | 202 com o id da run e status `na_fila` | 404 para API inexistente, 503 para fila indisponível |
| `GET /apis/{id}/runs` | 200 com a lista de runs | 404 para API inexistente |
| `GET /runs/{id}` | 200 com a run e os resultados | 404 para run inexistente |
| `GET /saude` | 200 | |

Os padrões de execução (seed, casos por endpoint, timeouts e tempo máximo da run) estão no [`.env.example`](.env.example).

## Testes

```bash
make help                                   # lista os comandos
uv run pytest -m unit                       # domínio e casos de uso, sem Docker
docker compose up -d postgres redis
make cov                                    # unitários e integração, com as metas de cobertura
make check                                  # ruff, mypy e import-linter
docker compose up -d --build --wait
uv run pytest -m e2e                        # fluxo completo no Compose
```

Cada teste começa com o ID da [matriz de rastreabilidade](docs/plano-de-testes/plano-de-testes-v1.4.md) (ex.: `test_us04_c4_...`). O CI roda os jobs `quality`, `test`, `build` e `e2e` em todo Pull Request ([ADR-004](docs/adr/ADR-004-ci-cd.md)). A meta de cobertura é 85% no total e 100% de branches em `domain/` e `application/`.

## Arquitetura

Hexagonal ([ADR-003](docs/adr/ADR-003-arquitetura-do-hub.md)), com as fronteiras verificadas pelo import-linter no CI.

```
app/
  domain/          entidades e regras: status da run, consolidação de resultados
  application/     casos de uso e portas
  adapters/
    inbound/http/          rotas FastAPI e DTOs
    inbound/worker/        entrada do worker (RQ)
    outbound/persistence/  PostgreSQL com SQLModel
    outbound/queue/        fila com Redis e RQ
    outbound/spec_loader/  download e validação da spec
    outbound/generator/    Schemathesis
  bootstrap/       configuração e montagem dos casos de uso
target_api/        API alvo, independente do hub
```

Fluxo de uma run ([ADR-006](docs/adr/ADR-006-execucao-da-run.md)):

1. `POST /runs` grava a run em `na_fila`, enfileira no Redis e responde 202.
2. O worker muda a run para `em_execucao`, resolve a versão da spec ([ADR-007](docs/adr/ADR-007-armazenamento-da-spec.md)) e gera e executa os casos com seed fixa ([ADR-005](docs/adr/ADR-005-gerador-de-testes.md)).
3. Cada endpoint vira um resultado consolidado. A run termina `passou` ou `falhou`, com resultados e totais gravados na mesma transação.
4. Tempo máximo excedido, erro interno do hub ou worker reiniciado no meio da run terminam a run como `interrompida`, com o motivo.

## Documentação

- [ERS](docs/ers/Test-Hub-ERS-v0.6.md): escopo, regras de negócio, estórias e contrato da API
- [ADRs](docs/adr/): decisões de arquitetura
- [Modelo de dados](docs/der/der-test-hub.dbml)
- [Plano de Testes](docs/plano-de-testes/plano-de-testes-v1.4.md): níveis de teste e matriz de rastreabilidade

## Como usei IA neste projeto

O projeto foi feito com o Claude Code. O uso de IA está registrado em:

- **Divisão de trabalho e regras de uso:** [ADR-009](docs/adr/ADR-009-uso-de-ia.md). Desde a v1.2, eu especifico (ERS, ADRs e matriz do Plano de Testes), reviso e aprovo cada PR por comentário, e a IA escreve todo o código, inclusive o domínio.
- **Instruções dadas à IA:** [`CLAUDE.md`](CLAUDE.md), com as fontes de verdade, o escopo e as regras de commit e de teste.
- **Decisões:** as alternativas levantadas pela IA e a escolha final ficam nos [ADRs](docs/adr/). Cada documento tem a seção "Registro de uso de IA", com o que a IA sugeriu, o que aceitei e o que decidi diferente.
- **Autoria do código:** os commits com código escrito pela IA levam o trailer `Co-Authored-By: Claude`. A exceção é o `domain/` até a v1.1 do ADR-009: escrito por mim, com trechos da IA, nem todos os commits com trechos dela têm o trailer.

```bash
git log --grep "Co-Authored-By: Claude" --oneline    # commits com código escrito pela IA
```
