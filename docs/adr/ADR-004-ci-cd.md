# ADR-004: CI/CD

## Título

Pipeline de **CI/CD no GitHub Actions** com ruff, mypy, import-linter, pytest, testes E2E com Docker Compose e publicação da imagem Docker no **GHCR**, apoiado por **uv**, **pre-commit** e **branch protection**.

## Status

Aprovada

## Data

02/11/2026

## Versão

1.3

## Proprietário ADR

Luis Henrique S. Carvalho

## Contexto

O RNF-03 exige CI no GitHub Actions com lint, testes e build Docker, todos verdes. O RNF-02 define as metas de cobertura, o RNF-04 exige que o ambiente completo suba com `docker compose up` sem passo manual, o RNF-05 exige commits no padrão Conventional Commits e o ADR-003 determina que as fronteiras da arquitetura hexagonal sejam verificadas automaticamente no CI. O ADR-002 exige que os testes de integração rodem contra PostgreSQL.

A plataforma de CI já está definida pelo RNF-03. As decisões em aberto eram as ferramentas e o formato do pipeline:

- **Lint e formatação:** ruff (lint e formatação em uma única ferramenta) ou flake8, black e isort combinados.
- **Checagem de tipos:** mypy, pyright ou nenhuma.
- **Gerenciamento de dependências:** uv, poetry ou pip.
- **Formato do pipeline:** um job sequencial ou jobs paralelos.
- **Entrega (CD):** nenhuma, publicação da imagem em um registry ou deploy em nuvem.
- **Fluxo de Git:** push direto na branch principal ou Pull Request com checks obrigatórios.
- **Checagens locais:** nenhuma ou pre-commit.

O responsável pelo projeto não tinha experiência prévia com CI/CD.

## Decisão

Foi decidido adotar o seguinte pipeline e ferramentas:

**Pipeline no GitHub Actions, com quatro jobs:**

- **quality:** `ruff check`, `ruff format --check`, `mypy` e `import-linter`.
- **test:** `pytest` (testes unitários e de integração) com PostgreSQL e Redis em service containers (Redis incluído pelo ADR-006). A API alvo é iniciada pelos próprios testes, por uma fixture que a sobe com uvicorn em subprocesso. O pipeline falha se a cobertura total ficar abaixo de 85% ou se a cobertura de branches de `domain/` e `application/` ficar abaixo de 100%. A cobertura é medida somente sobre o pacote `app/`, sem contar a `target_api/`.
- **build:** build da imagem Docker do hub. No push para `main`, a imagem é publicada no GitHub Container Registry (GHCR).
- **e2e:** depende do `build`. Sobe o ambiente completo com `docker compose up` usando a imagem construída no `build` e executa os testes marcados como `e2e`, conforme o Plano de Testes.

Os jobs `quality`, `test` e `build` rodam em paralelo. O `e2e` roda após o `build`.

**Ferramentas:**

- **ruff** para lint e formatação, substituindo flake8, black e isort com uma única ferramenta mais rápida.
- **mypy** para checagem estática de tipos. Na arquitetura hexagonal, garante que cada adapter implementa corretamente a porta correspondente.
- **uv** para gerenciar dependências, com lockfile versionado, garantindo as mesmas versões localmente e no CI.

**Fluxo de trabalho:**

- Todo código entra na `main` via Pull Request, com **branch protection** exigindo os quatro jobs verdes.
- **pre-commit** local executa ruff e valida a mensagem de commit no padrão Conventional Commits antes de cada commit.

**CD na v1** se limita à publicação da imagem no GHCR. Deploy em servidor ou nuvem está fora do escopo da v1 (RN-08).

Alternativas descartadas:

- **flake8, black e isort:** três ferramentas para o que o ruff faz sozinho.
- **pyright:** equivalente ao mypy para este uso. A escolha do mypy foi por ser a referência mais difundida em projetos Python.
- **Sem checagem de tipos:** perderia a verificação de que adapters implementam as portas.
- **poetry e pip:** poetry é mais lento e pip não oferece lockfile nativo.
- **Job sequencial único:** pipeline mais lento e falhas menos claras de identificar.
- **Deploy em nuvem:** fora do escopo da v1 e com custo.
- **Push direto na `main`:** permite que código quebrado chegue à branch principal.
- **E2E apenas local:** deixaria o RNF-04 sem verificação automática.

## Consequências

### Positivas

- Nenhum código chega à `main` sem lint, tipos, fronteiras de arquitetura, testes, build e verificação do ambiente completo.
- As regras do ADR-002 (testes contra PostgreSQL) e do ADR-003 (fronteiras da hexagonal) passam a ser cobradas automaticamente.
- O RNF-04 é verificado a cada Pull Request pelo job `e2e`.
- Erros simples são pegos localmente pelo pre-commit, antes do push.
- Imagem Docker publicada e versionada a cada merge, pronta para ser executada por qualquer pessoa.
- Histórico de commits padronizado e legível.

### Negativas

- Curva de aprendizado, pois o responsável não tinha experiência com CI/CD, GitHub Actions ou pre-commit.
- Fluxo com PR e branch protection é mais lento do que push direto em um projeto com um único desenvolvedor.
- mypy pode gerar atrito com SQLModel e outras bibliotecas com tipagem dinâmica, exigindo ajustes de configuração.
- Testes com PostgreSQL em service container deixam o job de testes mais lento.
- O job `e2e` sobe o ambiente completo e acrescenta alguns minutos ao pipeline, além de depender do `build`.
- A meta de 100% de branches no domínio exige teste para cada caminho das regras de negócio, o que aumenta o esforço da v1.

## Conformidade

- O arquivo de workflow deve ficar em `.github/workflows/` e conter os jobs `quality`, `test`, `build` e `e2e`.
- O job `e2e` deve declarar dependência do `build` e usar a imagem construída nele.
- A branch `main` deve ter branch protection exigindo os quatro jobs verdes para merge.
- As duas metas de cobertura (85% total e 100% de branches em `domain/` e `application/`) devem ser aplicadas como `fail-under`, não apenas reportadas, e medidas somente sobre `app/`.
- A API alvo usada no job `test` deve ser iniciada pela fixture dos testes, sem service container próprio.
- O mypy deve rodar em todo o código, com modo estrito no mínimo nos pacotes `domain` e `application`.
- As regras de importação do ADR-003 devem estar declaradas na configuração do import-linter e rodar no job `quality`.
- O lockfile do uv deve ser versionado e o CI deve instalar dependências a partir dele.
- O `.pre-commit-config.yaml` deve estar na raiz do repositório com ruff e validação de Conventional Commits.
- Qualquer etapa removida ou desativada do pipeline deve ser registrada em nova ADR.

## Observações

- Branch protection é gratuita para repositórios públicos no GitHub. O repositório do Test Hub deve ser público.
- Se o mypy estrito gerar atrito excessivo com o SQLModel, o modo estrito pode ficar restrito a `domain` e `application`, como já previsto na Conformidade.
- Deploy em nuvem pode ser avaliado em versões futuras, em ADR própria.
- O detalhamento dos testes de cada job (níveis, marcadores e matriz de rastreabilidade) fica no Plano de Testes.

## Direcionadores

- **f5/f6: Velocidade e confiabilidade de implantação.** Imagem publicada automaticamente a cada merge, sempre a partir de código verificado.
- **f7: Confiabilidade.** Branch protection impede que código quebrado chegue à `main`.
- **f44: Redução da dívida técnica.** Lint, tipos e fronteiras de arquitetura verificados a cada mudança.
- **f38: Economizar tempo.** pre-commit e jobs paralelos encurtam o ciclo de feedback.
- **f39: Reduzir custos.** GitHub Actions, GHCR e as ferramentas escolhidas são gratuitos para repositórios públicos.

## Histórico de versões

| Versão | Data | Alteração |
| --- | --- | --- |
| 1.0 | 02/11/2026 | Criação. |
| 1.1 | 07/11/2026 | Redis incluído no job de testes, conforme o ADR-006. |
| 1.2 | 08/11/2026 | Inclusão do job `e2e` e da meta de 100% de branches em `domain/` e `application/`, conforme o Plano de Testes. |
| 1.3 | 08/11/2026 | API alvo iniciada por fixture no job `test` e cobertura medida somente sobre `app/`. |

## Registro de uso de IA

- **O que a IA sugeriu:** o pacote completo, com ruff, mypy, uv, três jobs paralelos, publicação no GHCR, PR com branch protection e pre-commit. Também explicou cada termo e ferramenta, já que eu não tinha experiência com CI/CD. Na elaboração do Plano de Testes, propôs o job `e2e` e a meta de 100% de branches no domínio, mas não atualizou este ADR na mesma hora, o que deixou os documentos inconsistentes.
- **O que aceitei:** a recomendação inteira, depois de entender o papel de cada peça. Na v1.2, aceitei manter o job `e2e` no CI em vez de rodar os testes E2E apenas localmente.
- **O que decidi diferente:** nada. Por não ter experiência na área, segui a recomendação, e este ADR registra isso. A inconsistência entre o Plano de Testes e este ADR foi identificada por mim na revisão.
- **v1.3:** em uma revisão cruzada dos documentos, a IA apontou que o Plano de Testes exige a API alvo real, mas o job `test` não a disponibilizava, e recomendou a fixture com uvicorn e a medição de cobertura somente sobre `app/`. Aceitei.
