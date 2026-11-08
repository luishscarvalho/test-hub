# ADR-008: API alvo

## Título

Criação de uma **API alvo de tarefas** em **FastAPI**, com dados em memória e **modo de falha controlada**, mantida no mesmo repositório do **Test Hub**.

## Status

Aprovada

## Data

07/11/2026

## Versão

1.1

## Proprietário ADR

Luis Henrique S. Carvalho

## Contexto

Na v1, a única API testada pelo hub é uma API criada pelo próprio projeto (RN-10). Ela funciona como cobaia: existe apenas para que o hub tenha uma spec OpenAPI para ler, testes para gerar e respostas para validar. O ambiente completo deve subir com `docker compose up` (RNF-04).

A API alvo precisava:

- Cobrir os tipos de endpoint que o hub deve suportar: listagem, parâmetro no caminho, corpo na requisição e resposta sem corpo (US-03, critério 3).
- Ser previsível, para que runs repetidas sejam comparáveis.
- Permitir demonstrar que o hub detecta falhas, e não apenas que tudo passa.
- Não virar um projeto paralelo (RN-08).

Decisões avaliadas:

- **Stack:** FastAPI ou outra stack (Node, por exemplo) para demonstrar que o hub é agnóstico.
- **Domínio:** tarefas ou domínios com mais entidades (biblioteca, loja).
- **Persistência:** memória, SQLite ou PostgreSQL.
- **Localização:** mesmo repositório do hub ou repositório separado.
- **Falhas:** nenhuma ou falha controlada por variável de ambiente.

## Decisão

Foi decidido criar a API alvo com as seguintes características:

**Stack: FastAPI.** Gera a spec OpenAPI automaticamente a partir do código e não exige aprendizado novo. Demonstrar que o hub testa APIs de outras stacks fica a cargo da v3, com APIs públicas.

**Domínio: tarefas.** Uma única entidade (`Tarefa`) já permite todos os tipos de endpoint necessários. Domínios maiores só adicionariam código repetido, sem ganho para o hub.

**Endpoints:**

| Endpoint | Função | O que exercita no hub |
| --- | --- | --- |
| `GET /tarefas` | Listar tarefas | Resposta em lista |
| `GET /tarefas/{id}` | Buscar uma tarefa | Parâmetro no caminho e resposta `404` |
| `POST /tarefas` | Criar tarefa | Corpo na requisição e resposta `201` |
| `PUT /tarefas/{id}` | Editar tarefa | Parâmetro no caminho e corpo juntos |
| `DELETE /tarefas/{id}` | Apagar tarefa | Resposta `204` sem corpo (US-03, critério 3) |
| `GET /saude` | Health check | Endpoint sem parâmetros. Também usado pelo Compose para saber quando a API subiu |

O identificador da tarefa é gerado pela API. O corpo de criação e edição usa um modelo de entrada sem `id`, separado do modelo de resposta.

**Persistência: memória, com dados fixos na subida.** As tarefas ficam em uma estrutura em memória, carregada com tarefas iniciais (seed) a cada inicialização. A API sempre sobe no mesmo estado, e os caminhos de sucesso (como buscar uma tarefa existente) podem ser testados.

**Localização: mesmo repositório**, na pasta `target_api/`, com serviço próprio no Docker Compose e no CI.

**Falha controlada: variável de ambiente `MODO_FALHA`.**

- Desligada (padrão): a API cumpre a spec e os testes do hub passam.
- Ligada: `GET /tarefas/{id}` responde `200` para qualquer `id`, existente ou não, com tipos diferentes dos prometidos na spec (por exemplo, `id` como texto), e `GET /tarefas` responde `500`. Como o Schemathesis gera identificadores aleatórios, responder a qualquer `id` garante que a falha seja detectada em vez de cair em um `404` documentado. As respostas incorretas são devolvidas diretamente, sem passar pela validação do FastAPI.
- `GET /saude` nunca falha, para não impedir a subida do ambiente.

Alternativas descartadas:

- **Outra stack:** o objetivo de provar que o hub é agnóstico pertence à v3.
- **Domínio maior:** mais código sem ganho para o hub.
- **SQLite ou PostgreSQL:** mais um serviço ou arquivo para gerenciar, sem necessidade de guardar dados de verdade.
- **Repositório separado:** exigiria coordenar dois repositórios e dois pipelines para um componente que só existe em função do hub.
- **Sem falha controlada:** não haveria como demonstrar que o hub detecta erros.

## Consequências

### Positivas

- O hub é exercitado em todos os tipos de endpoint previstos na v1.
- Ambiente previsível: toda inicialização parte do mesmo estado.
- Demonstração clara de verde e vermelho alternando apenas a variável `MODO_FALHA`.
- Quem clonar o repositório sobe hub e API alvo com um único comando.

### Negativas

- **Estado muda durante a run:** requests gerados pelo Schemathesis podem criar, editar e apagar tarefas, inclusive as iniciais. As respostas continuam válidas (um `404` documentado é conforme), mas o estado só volta ao inicial quando a API reinicia.
- **Spec sempre fiel ao código:** sem o `MODO_FALHA`, a API nunca falha, então o modo de falha precisa ser mantido junto com a API.
- Mais um serviço no Compose e no CI.

## Conformidade

- O código da API alvo fica em `target_api/` e não pode importar nada do hub, nem o hub da API alvo (verificado pelo import-linter, conforme o ADR-004).
- Toda resposta de erro esperada (como `404`) deve ser declarada explicitamente na rota, para constar na spec. O FastAPI documenta automaticamente apenas o `422` de validação.
- `MODO_FALHA` deve ser desligado por padrão.
- Deve existir um teste E2E do hub que executa uma run com `MODO_FALHA` ligado e exige status `falhou`, e outro com o modo desligado que exige `passou`.
- `GET /saude` não pode ser afetado pelo `MODO_FALHA` e deve ser usado no healthcheck do serviço no Docker Compose.
- Novos endpoints só podem ser adicionados se exercitarem um comportamento do hub ainda não coberto.

## Observações

- Na v3, o hub passará a testar APIs externas de qualquer stack. A API alvo continua útil como ambiente controlado para os testes do próprio hub.
- Se a mudança de estado durante a run atrapalhar a detecção de flaky na v2, um mecanismo de reinício do estado pode ser avaliado. Um endpoint que falha de forma intermitente, útil para demonstrar flaky, também pertence à v2 (RN-08).

## Direcionadores

- **f4: Velocidade de desenvolvimento.** Mesma stack do hub, uma entidade e persistência em memória.
- **f11: Testabilidade.** Cobre todos os tipos de endpoint da v1 e permite testes E2E de verde e vermelho.
- **f7: Confiabilidade.** Estado inicial fixo torna as runs comparáveis.
- **f38: Economizar tempo.** Um único repositório e um único comando para subir tudo.

## Histórico de versões

| Versão | Data | Alteração |
| --- | --- | --- |
| 1.0 | 07/11/2026 | Criação. |
| 1.1 | 08/11/2026 | `MODO_FALHA` passa a responder com erro para qualquer `id`, e os testes de verde e vermelho passam a ser E2E, conforme o Plano de Testes. |

## Registro de uso de IA

- **O que a IA sugeriu:** o pacote completo: FastAPI, domínio de tarefas, seis endpoints, persistência em memória com dados fixos, mesmo repositório e falha controlada por `MODO_FALHA`. Como eu não estava entendendo a proposta, passou ponto a ponto com exemplos de código, até ficar claro que este ADR trata da API cobaia, e não do hub.
- **O que aceitei:** todas as recomendações, depois de entender cada uma.
- **O que decidi diferente:** nada. Registrei apenas que FastAPI é escolha da v1, e que a intenção é o hub suportar o máximo possível de APIs nas versões seguintes.
- **v1.1:** em uma revisão cruzada dos documentos, a IA apontou que, com identificadores aleatórios, o `MODO_FALHA` poderia cair sempre em `404` e não ser detectado, e que este ADR divergia do Plano de Testes sobre o nível do teste. Aceitei as correções.
