# Test Hub

Hub que lê a spec OpenAPI de uma API, gera smoke tests (status e schema) com Schemathesis, executa em fila e guarda o histórico. Peça de portfólio QA/SDET: o objetivo é mostrar uso de IA com controle e entregar a v1 fechada.

## Fontes de verdade

Leia o documento antes de implementar algo que ele cobre. Em conflito entre código e documento, pare e avise.

| O quê | Onde |
| --- | --- |
| Escopo, regras (RN), estórias (US), contrato da API | `docs/ers/Test-Hub-ERS-v0.4.md` |
| Decisões de arquitetura | `docs/adr/` |
| Modelo de dados | `docs/der/der-test-hub.dbml` |
| Níveis de teste, matriz de rastreabilidade, IDs | `docs/plano-de-testes/plano-de-testes-v1.2.md` |

## Divisão de trabalho (ADR-009)

| Quem escreve | O quê | Onde fica |
| --- | --- | --- |
| **Desenvolvedor**, com revisão da IA | Regras de negócio e casos de uso: consolidação de resultados, status da run, imutabilidade, versionamento da spec | `domain/` e `application/` |
| **IA**, com leitura do desenvolvedor | Estrutura do projeto, Dockerfile, Docker Compose, CI, configurações, migrações, rotas FastAPI, DTOs, mapeamentos, adapters (Schemathesis, RQ, banco, HTTP) e API alvo | `adapters/`, `bootstrap/`, `target_api/` e raiz |
| **Em conjunto** | Testes do domínio e dos casos de uso: o desenvolvedor define os casos, a IA ajuda a escrever | `tests/` |

Regras permanentes:

- **Nunca escreva em `app/domain/` nem em `app/application/`.** Lá a IA só sugere na conversa, em forma de revisão. O `.claude/settings.json` bloqueia essa escrita.
- Trecho ambíguo entre mecânico e lógica é lógica: pergunte.
- Decisão de arquitetura ou de escopo é do desenvolvedor e vira ADR. A IA levanta alternativas e recomenda, não decide.
- Nada entra na `main` sem o desenvolvedor ler e saber explicar. Entregue em pedaços pequenos que dê para ler.
- Teste que passa pelo motivo errado é defeito. Testes seguem as responsabilidades da seção 5 do Plano de Testes.

## Escopo (RN-08)

Só o que está na lista da v1 na ERS. Fora dela, não implemente: avise e cite a RN-08. Sem funcionalidade "de brinde".

## Arquitetura (ADR-003)

```
app/
  domain/          entidades e regras puras
  application/     casos de uso e portas
  adapters/
    inbound/http/          rotas FastAPI e DTOs, sem regra de negócio
    inbound/worker/        entrada do worker, sem regra de negócio
    outbound/persistence/  tabelas SQLModel, repositórios, mapeamento
    outbound/queue/        RQ e Redis (porta ExecutorDeRun)
    outbound/spec_loader/  download e validação da spec
    outbound/generator/    Schemathesis (porta GeradorDeTestes)
  bootstrap/       única camada que liga portas e adapters
target_api/        API cobaia (ADR-008), não importa nada do hub e vice-versa
```

As fronteiras estão no `import-linter` (`pyproject.toml`). Violação quebra o CI. Não relaxe um contrato para fazer passar: se o contrato estiver errado, avise.

Acesso a banco é síncrono (ADR-002). Modelos `table=True` ficam separados dos DTOs. Mudança de esquema só por migração do Alembic.

## Comandos

```bash
make help                                # lista tudo
uv run pytest -m unit                    # rápido, sem Docker
docker compose up -d postgres redis      # dependências dos testes de integração
uv run pytest -m "unit or integration"
make check                               # ruff, mypy, import-linter
make cov                                 # testes + as duas metas de cobertura
docker compose up -d --build --wait      # ambiente completo
uv run pytest -m e2e
```

Antes de dizer que terminou, rode `make check` e os testes do que mudou, e informe o resultado real.

## Testes

- Nome começa com o ID da matriz, em minúsculas: `test_us04_c4_disparo_responde_202`.
- Marcador obrigatório: `unit`, `integration` ou `e2e`.
- Nada de `sleep` fixo: espere por condição com tempo limite. Seed fixa. Nada de SQLite.
- Cobertura: 85% no total e 100% de branches em `domain/` e `application/`, medidas só sobre `app/`.
- Mudou a matriz ou a numeração da ERS? Sincronize antes de renomear testes.

## Git

- Todo código entra por Pull Request, com os jobs `quality`, `test`, `build` e `e2e` verdes.
- Commits pequenos em Conventional Commits, em português: `feat(api-alvo): adiciona rota de tarefas`.
- Um commit por unidade lógica, com escopo e mensagem dizendo exatamente o que mudou. Proibido commit genérico como 'initial setup' ou 'update files'.
- Commit com código escrito pela IA leva o trailer: `Co-Authored-By: Claude <noreply@anthropic.com>`.
- Só faça commit ou push quando o desenvolvedor pedir.

## Documentos

- Alterou documento já feito: atualize o campo Versão e a tabela Histórico de versões.
- Todo documento tem a seção "Registro de uso de IA" (o que a IA sugeriu, o que aceitei, o que decidi diferente), fiel ao que aconteceu. Não fabrique discordância.
- Texto em português do Brasil, sem travessão.

## Ambiente

Desenvolvimento em WSL, com o repositório no filesystem Linux (`~/`), nunca em `/mnt/c`.
