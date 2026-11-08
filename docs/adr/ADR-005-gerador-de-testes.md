# ADR-005: Gerador de testes

## Título

Uso do **Schemathesis** como gerador de smoke tests do **Test Hub**, com resultados consolidados por endpoint e **seed fixa**.

## Status

Aprovada

## Data

07/11/2026

## Versão

1.1

## Proprietário ADR

Luis Henrique S. Carvalho

## Contexto

O gerador é o núcleo do Test Hub: a partir da spec OpenAPI de uma API alvo, ele produz os smoke tests que verificam status e schema da resposta de cada endpoint (RN-04). Pelo ADR-003, o gerador fica atrás de uma porta (`GeradorDeTestes`), então a escolha da implementação não afeta o domínio.

Restrições relevantes:

- **RN-03:** cada par endpoint e método gera exatamente um smoke test.
- **RN-07:** todo teste registra sua duração.
- **US-03, critério 3:** endpoint sem schema de resposta verifica apenas o status.
- **v2:** detecção de testes flaky, que depende de resultados comparáveis entre runs.

O ponto mais difícil da geração não é validar a resposta, e sim montar entradas válidas: parâmetros de caminho, query e corpos de requisição.

As opções avaliadas foram:

- **Schemathesis:** ferramenta open source em Python que gera testes a partir da spec OpenAPI usando testes baseados em propriedades (Hypothesis). Gera entradas válidas automaticamente e já possui verificações de conformidade de status e schema. Porém, gera vários casos por endpoint e usa dados aleatórios.
- **Gerador próprio simples:** uma requisição por endpoint montada a partir dos exemplos da spec, com validação da resposta via JSON Schema. Aderente ao ERS e com pouco código, mas dependente de a spec trazer exemplos.
- **Híbrido:** Schemathesis apenas para leitura da spec, com geração própria. Dependência pesada para pouco uso.

## Decisão

Foi decidido utilizar o **Schemathesis** como implementação do gerador de testes, encapsulado em um adapter de saída que implementa a porta `GeradorDeTestes`.

Para compatibilizar a ferramenta com o ERS e com a v2:

- **Geração e execução juntas:** o Schemathesis gera os casos e também faz as chamadas à API alvo. A porta `GeradorDeTestes` recebe a spec, a base URL e a seed e devolve os resultados consolidados, sem cliente HTTP separado.
- **Consolidação por endpoint:** o Schemathesis pode gerar vários casos por endpoint, mas o hub registra **um resultado por par endpoint e método**. O resultado é "passou" somente se todos os casos passaram. Em caso de falha, a mensagem registrada é a do primeiro caso que falhou. A duração do resultado é a soma da duração dos casos.
- **API alvo inacessível:** erro de conexão ou tempo esgotado ao chamar a API alvo conta como caso que falhou, com a mensagem do erro. Assim, a queda da API alvo durante a run resulta em endpoints e run com status `falhou`.
- **Seed fixa:** a geração usa seed fixa, para que runs sobre a mesma spec produzam os mesmos dados de entrada. Assim, uma variação de resultado entre runs reflete mudança na API, não no dado gerado, o que é pré-requisito para a detecção de flaky da v2.
- **Verificações restritas:** apenas as verificações de conformidade de status e de schema da resposta ficam ativas, respeitando a RN-04.
- **Limite de casos:** o número máximo de casos por endpoint é configurável, com valor padrão baixo, mantendo as runs rápidas.

A escolha foi motivada por:

- **Geração de dados resolvida:** a ferramenta monta entradas válidas a partir dos schemas, sem depender de exemplos na spec.
- **Preparação para a v3:** APIs públicas raramente trazem exemplos completos, cenário em que um gerador próprio teria dificuldade.
- **Relevância profissional:** Schemathesis é uma ferramenta reconhecida em QA de APIs.
- **Encaixe na arquitetura:** por estar atrás de uma porta, a ferramenta pode ser substituída sem impacto no domínio.

Alternativas descartadas:

- **Gerador próprio:** recomendado inicialmente pela IA, por aderir ao ERS sem adaptação. Descartado por depender de exemplos na spec e exigir resolver a geração de dados manualmente, especialmente na v3.
- **Híbrido:** dependência pesada para usar apenas a leitura da spec.

## Consequências

### Positivas

- Geração de entradas válidas sem esforço manual e sem exigir exemplos na spec.
- Mais de um caso por endpoint aumenta a chance de encontrar falhas que um único request não pegaria.
- Seed fixa torna as runs reproduzíveis e prepara o terreno para a v2.
- Adapter isolado permite trocar ou complementar o gerador no futuro.

### Negativas

- **Curva de aprendizado:** a API Python do Schemathesis mudou de forma relevante entre versões recentes, exigindo estudo da versão adotada.
- **Camada de adaptação:** consolidar vários casos em um resultado é código adicional e precisa de testes próprios.
- **Perda de detalhe:** o resultado consolidado registra apenas a primeira falha, não todas.
- **Dependência externa crítica:** mudanças incompatíveis na ferramenta afetam o núcleo do produto.
- **Mudança no ERS:** a RN-03 e a US-03 precisam ser ajustadas para refletir a consolidação.

## Conformidade

- O Schemathesis só pode ser importado dentro do adapter do gerador. Domínio e aplicação usam apenas a porta `GeradorDeTestes` (verificado pelo import-linter, conforme o ADR-004).
- O hub deve registrar exatamente um resultado por par endpoint e método em cada run.
- A seed usada deve ser fixa e configurável, e cada run deve registrar a seed com que foi executada.
- Apenas verificações de status e de schema da resposta podem estar ativas.
- A versão do Schemathesis deve ser fixada no lockfile, e atualizações de versão maior devem ser feitas em PR próprio com os testes do adapter verdes.
- O adapter deve ter testes que cubram: todos os casos passando, um caso falhando, endpoint sem schema de resposta, reprodutibilidade com a mesma seed e API alvo inacessível.

## Observações

- A forma de integração (API Python ou linha de comando) será definida na implementação, priorizando a API Python por permitir capturar o resultado de cada caso diretamente.
- Se a consolidação esconder informação importante para a investigação de falhas, o registro dos casos individuais pode ser avaliado na v2.
- Ajustes no ERS: RN-03 passa a falar em um resultado consolidado por endpoint e método. US-03, critério 1, idem. A seção de decisões pendentes deve ser atualizada com a numeração atual dos ADRs.

## Direcionadores

- **f4: Velocidade de desenvolvimento.** A geração de dados vem pronta, sem implementação manual.
- **f7: Confiabilidade.** Seed fixa garante runs reproduzíveis e comparáveis.
- **f11: Testabilidade.** Vários casos por endpoint ampliam a cobertura dos testes gerados sobre a API alvo.
- **f44: Redução da dívida técnica.** Ferramenta mantida pela comunidade, isolada atrás de uma porta, em vez de um gerador próprio a ser mantido.

## Histórico de versões

| Versão | Data | Alteração |
| --- | --- | --- |
| 1.0 | 07/11/2026 | Criação. |
| 1.1 | 08/11/2026 | Registro de que a porta gera e executa os testes e definição do comportamento com a API alvo inacessível. |

## Registro de uso de IA

- **O que a IA sugeriu:** comparou Schemathesis, gerador próprio e híbrido, e recomendou o gerador próprio por aderir ao ERS sem adaptação. Quando escolhi o Schemathesis, apontou dois conflitos: a RN-03 (um teste por endpoint) e o risco de falso flaky na v2 por dados aleatórios. Propôs consolidar os casos em um resultado por endpoint e usar seed fixa.
- **O que aceitei:** a consolidação por endpoint, a seed fixa e a sugestão de ajustar o ERS.
- **O que decidi diferente:** escolhi o Schemathesis em vez do gerador próprio recomendado pela IA, priorizando a geração automática de dados, a preparação para a v3 e a relevância da ferramenta no mercado de QA.
- **v1.1:** em uma revisão cruzada dos documentos, a IA apontou que a porta também executa os testes e que a queda da API alvo durante a run não estava definida, e recomendou tratá-la como falha de cada endpoint. Aceitei.
