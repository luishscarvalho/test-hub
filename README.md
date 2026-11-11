# Test Hub

Lê a spec OpenAPI de uma API, gera smoke tests (status e schema) com Schemathesis, executa em fila e guarda o histórico de cada execução.

> Em construção. Escopo da v1 na [ERS](docs/ers/Test-Hub-ERS-v0.5.md).

## Como rodar

```bash
docker compose up -d --build --wait
```

| Serviço | URL |
| --- | --- |
| Hub (Swagger) | http://localhost:8000/docs |
| API alvo | http://localhost:8001/docs |

## Documentação

- [ERS](docs/ers/Test-Hub-ERS-v0.5.md)
- [ADRs](docs/adr/)
- [Modelo de dados](docs/der/der-test-hub.dbml)
- [Plano de Testes](docs/plano-de-testes/plano-de-testes-v1.3.md)

## Como usei IA neste projeto

Divisão definida no [ADR-009](docs/adr/ADR-009-uso-de-ia.md): a IA escreve o código mecânico, eu escrevo a lógica de negócio, e todo documento registra o que a IA sugeriu e o que decidi diferente.
