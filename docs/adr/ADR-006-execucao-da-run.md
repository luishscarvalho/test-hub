# ADR-006: Execução da run

## Título

Execução das runs em **segundo plano por fila**, usando **Redis** e **RQ**, com worker dedicado.

## Status

Aprovada

## Data

07/11/2026

## Versão

1.2

## Proprietário ADR

Luis Henrique S. Carvalho

## Contexto

Uma run executa os smoke tests gerados para todos os endpoints de uma API alvo. Com o Schemathesis (ADR-005) gerando vários casos por endpoint, a duração de uma run cresce com o número de endpoints, de casos e com a latência da API alvo. Executar tudo dentro do request que dispara a run (US-04) arrisca timeouts e deixa o cliente bloqueado.

Restrições relevantes:

- **RN-05:** o resultado de uma run finalizada não pode ser alterado.
- **RN-06 e RN-07:** status geral derivado dos testes, início, fim e duração registrados.
- **RNF-04:** `docker compose up` sobe todo o ambiente sem passo manual.
- **ADR-002:** acesso ao banco síncrono.
- **ADR-003:** dependências externas ficam atrás de portas.

As opções avaliadas foram:

- **Execução síncrona no request:** simples, mas sujeita a timeout e com cliente bloqueado.
- **BackgroundTasks do FastAPI:** o request responde na hora e a run executa no mesmo processo, sem infraestrutura nova. Se o processo cair, a run se perde.
- **Fila com Redis e worker dedicado:** a run é enfileirada e executada por um processo separado. Mais robusta e escalável, com mais infraestrutura. Bibliotecas consideradas: RQ (simples e síncrona), arq (assíncrona) e Celery (completa e mais pesada).
- **Postgres como fila com worker próprio:** robusto sem Redis, mas exige implementar manualmente a lógica de concorrência da fila.

## Decisão

Foi decidido executar as runs em **segundo plano por meio de fila**, usando **Redis** como broker e **RQ** como biblioteca de fila, com um **worker dedicado**.

**Fluxo:**

1. `POST /runs` cria a run com status `na_fila`, confirma a gravação, enfileira a execução e responde imediatamente com `202 Accepted` e o identificador da run. Se o enfileiramento falhar, a run recém-criada é removida e a rota responde `503 Service Unavailable`.
2. O worker pega a tarefa, muda a run para `em_execucao`, executa os testes e grava os resultados.
3. Ao terminar, a run passa para `passou` ou `falhou` (RN-06) e se torna imutável (RN-05).
4. O cliente acompanha o andamento consultando a run (US-08).

**Status da run:** `na_fila`, `em_execucao`, `passou`, `falhou` e `interrompida`. Os três últimos são finais e imutáveis.

**Run interrompida:** a run termina como `interrompida` em três casos, sempre com fim registrado e o motivo em `mensagem_erro`:

- **Queda do worker:** ao iniciar, o worker encontra a run presa em `em_execucao`.
- **Tempo máximo excedido:** a execução ultrapassa o tempo máximo configurado no job do RQ.
- **Erro interno do hub:** uma exceção inesperada do próprio hub encerra a execução.

O status `falhou` continua reservado para quando a API alvo não cumpre a spec (inclusive por estar inacessível durante a run, ADR-005) ou a spec está inacessível ou inválida. Uma run que não terminou por problema do próprio hub nunca é registrada como `falhou`, para não misturar falha da API com falha de execução (relevante para a detecção de flaky da v2).

**Gravação dos resultados:** os resultados de teste e os totais são gravados de uma só vez, na mesma transação que move a run para `passou` ou `falhou`. Uma run `interrompida` nunca tem resultados de teste, e seus totais ficam zerados.

**Worker único na v1:** o ambiente sobe exatamente um worker, e as runs são executadas uma por vez. A recuperação na inicialização marca como `interrompida` toda run em `em_execucao`, o que, com dois workers, interromperia runs ainda ativas no outro.

**Na arquitetura (ADR-003):** a aplicação usa a porta `ExecutorDeRun` para enfileirar a execução. O adapter RQ implementa essa porta. O worker chama o caso de uso de execução montado em `bootstrap`, sem lógica de negócio própria.

**No ambiente (RNF-04):** o Docker Compose passa a ter os serviços `redis` e `worker`. O worker usa a mesma imagem do hub, com outro comando de inicialização, e só inicia depois que o hub está saudável (`GET /saude`), o que garante que as migrações já rodaram.

A escolha da fila foi motivada por:

- **Robustez:** uma queda do processo da API não perde runs enfileiradas.
- **Base para escalar:** a separação entre API e worker permite adicionar workers em versão futura, desde que a recuperação na inicialização seja ajustada.
- **Separação de responsabilidades:** a API só recebe e consulta, o worker só executa.
- **Relevância profissional:** filas e workers são padrão em sistemas reais.

A escolha do **RQ** foi motivada por ser síncrono como o restante da stack (ADR-002 e ADR-005), simples de configurar e por ter um modo de execução imediata, que dispensa o worker nos testes do adapter que não precisam dele.

Alternativas descartadas:

- **Execução síncrona:** risco de timeout com o volume de casos do Schemathesis.
- **BackgroundTasks:** recomendada inicialmente pela IA pelo menor custo na v1. Descartada por perder runs em caso de queda e não separar API e execução.
- **Postgres como fila:** exigiria implementar a lógica de fila manualmente.
- **arq:** obrigaria tornar o acesso a banco e o gerador assíncronos.
- **Celery:** mais configuração do que o necessário para a v1.
- **Timeout como `falhou`:** misturaria falha da API alvo com falha de execução do hub.
- **Status próprio para timeout:** exigiria mais um valor no enum e nas consultas, sem ganho sobre `interrompida` com motivo.
- **Manter resultados parciais em run interrompida:** totais parciais e regra de status mais complexa, sem uso claro na v1.

## Consequências

### Positivas

- O cliente não fica bloqueado e não há risco de timeout no disparo da run.
- Runs enfileiradas sobrevivem a reinícios da API.
- Caminho aberto para múltiplos workers em versão futura.
- API e execução isoladas em processos distintos, facilitando diagnóstico.
- Toda run pega pelo worker chega a um status final, com motivo quando não terminou normalmente. Se o worker cair, isso acontece quando ele reiniciar.
- Resultados e totais sempre consistentes entre si, já que são gravados juntos.

### Negativas

- **Mais infraestrutura:** dois serviços novos no Compose e no CI (Redis e worker).
- **Mais estados:** a run deixa de ser apenas finalizada e passa a ter estados intermediários, exigindo tratamento nas consultas.
- **Consistência eventual:** logo após o disparo, a run ainda não tem resultados.
- **Prazo:** aumenta o esforço da v1.
- **Mudança no ERS:** novos status e comportamento assíncrono precisam ser refletidos.
- **Perda de trabalho parcial:** uma run interrompida descarta os resultados já obtidos, e uma nova run precisa ser disparada do zero.
- **Perda da fila:** se o Redis perder os dados com runs ainda em `na_fila`, elas permanecem nesse status. A v1 não reconcilia esse caso, e uma nova run deve ser disparada.
- **Worker único:** runs disparadas ao mesmo tempo aguardam na fila.

## Conformidade

- O RQ e o Redis só podem ser importados no adapter da porta `ExecutorDeRun` e no ponto de entrada do worker (verificado pelo import-linter, conforme o ADR-004).
- `POST /runs` deve responder `202 Accepted` com o identificador da run, sem aguardar a execução.
- Se a execução não puder ser enfileirada, `POST /runs` deve responder `503` e a run não pode permanecer registrada, e essa regra deve ter teste próprio.
- Apenas o worker pode mover a run para `em_execucao`, `passou`, `falhou` ou `interrompida`.
- O Docker Compose deve declarar uma única réplica do worker.
- Run em status final não pode ter status nem resultados alterados (RN-05), e essa regra deve ter teste próprio.
- Na inicialização do worker, runs presas em `em_execucao` devem ser marcadas como `interrompida`, com fim e motivo registrados.
- O tempo máximo de execução de uma run deve ser configurado no job do RQ. Ao ser excedido, a run deve ser marcada como `interrompida`, com fim e motivo registrados, e essa regra deve ter teste próprio.
- Exceção inesperada do hub durante a execução deve marcar a run como `interrompida`, com fim e motivo registrados, e essa regra deve ter teste próprio.
- Resultados de teste e totais devem ser gravados na mesma transação que move a run para status final. Run `interrompida` não pode ter resultados de teste.
- Não há retry automático na v1: run interrompida permanece no histórico e uma nova run deve ser disparada.
- Testes unitários usam um adapter falso da porta `ExecutorDeRun`, sem RQ. O adapter RQ é testado contra Redis real, e ao menos um teste de integração deve rodar com worker real.

## Observações

- Ajustes no ERS: inclusão dos status da run, resposta `202` na US-04, exibição de runs em andamento nas US-07 e US-08 e definição de run `interrompida`. Na v1.1 deste ADR: timeout como causa de `interrompida` e gravação dos resultados apenas ao final. Na v1.2: erro interno como causa de `interrompida` e resposta `503` no disparo.
- O tratamento do tempo excedido e do erro interno pode usar o callback de falha do RQ, que roda no worker quando o job é encerrado. A forma exata fica para a implementação, dentro do adapter e do ponto de entrada do worker.
- Como o worker roda em outro processo, a run precisa estar confirmada no banco antes de ser enfileirada. Por isso a remoção em caso de falha acontece depois da confirmação, quando nenhum worker conhece a run.
- Retry automático, múltiplos workers e reconciliação de runs perdidas na fila podem ser avaliados na v2. Múltiplos workers exigem que a recuperação na inicialização identifique o dono de cada run.
- O job de testes do CI (ADR-004) passa a incluir Redis como service container para os testes de integração.

## Direcionadores

- **f7: Confiabilidade.** Runs não se perdem com quedas da API e, depois de pegas pelo worker, sempre chegam a um status final.
- **f22: Melhor experiência do usuário.** O disparo responde na hora, sem cliente bloqueado.
- **f5/f6: Velocidade e confiabilidade de implantação.** API e worker podem ser reiniciados de forma independente.
- **f11: Testabilidade.** A porta `ExecutorDeRun` permite testar o fluxo sem infraestrutura.

## Histórico de versões

| Versão | Data | Alteração |
| --- | --- | --- |
| 1.0 | 07/11/2026 | Criação. |
| 1.1 | 08/11/2026 | Definição do status final por tempo excedido (`interrompida` com motivo) e gravação dos resultados somente ao final da run. |
| 1.2 | 08/11/2026 | Erro interno como causa de `interrompida`, resposta `503` quando a fila está indisponível, worker único na v1, limitação de perda da fila, ordem de subida e correção sobre o modo imediato do RQ. |

## Registro de uso de IA

- **O que a IA sugeriu:** comparou execução síncrona, BackgroundTasks, fila com Redis e Postgres como fila, recomendando BackgroundTasks com porta `ExecutorDeRun` e status intermediários. Explicou os conceitos e ferramentas envolvidos (fila, worker, polling, Redis, RQ, arq, Celery). Depois da minha escolha pela fila, comparou RQ, arq e Celery e recomendou RQ. Na v1.1, recomendou tratar o timeout como `interrompida` com motivo (em vez de `falhou` ou de um status novo) e gravar os resultados somente ao final, descartando parciais. Também apontou que o destino dos resultados parciais em run interrompida não estava definido em nenhum documento.
- **O que aceitei:** a porta `ExecutorDeRun`, os status intermediários com tratamento de runs interrompidas e o RQ como biblioteca de fila. Na v1.1, aceitei as duas recomendações.
- **O que decidi diferente:** escolhi a fila com Redis em vez das BackgroundTasks recomendadas pela IA, priorizando robustez, escalabilidade e a experiência com filas e workers. A lacuna sobre o status final por timeout foi identificada por mim na revisão do Plano de Testes.
- **v1.2:** em uma revisão cruzada dos documentos, a IA apontou que um erro inesperado no worker não tinha status final, que o Redis fora do ar deixava a run presa em `na_fila`, que a recuperação na inicialização não funciona com vários workers e que o modo imediato do RQ não dispensa Redis, e recomendou as correções desta versão. Aceitei.
