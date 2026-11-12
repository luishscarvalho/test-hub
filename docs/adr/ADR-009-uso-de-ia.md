# ADR-009: Uso de IA no projeto

## Título

Divisão de trabalho entre desenvolvedor e **IA** no **Test Hub**: o desenvolvedor especifica (ERS, ADRs e matriz do Plano de Testes), revisa e aprova; a IA escreve todo o código, inclusive o domínio, com toda mudança aprovada pelo desenvolvedor em comentário no Pull Request.

## Status

Aprovada

## Data

07/11/2026

## Versão

1.2

## Proprietário ADR

Luis Henrique S. Carvalho

## Contexto

O Test Hub é um projeto de portfólio cujo objetivo inclui demonstrar uso responsável de IA no desenvolvimento: usar IA para ganhar velocidade, mantendo controle e entendimento total do que é entregue. A Definição de Pronto da v1 exige um `CLAUDE.md` na raiz e uma seção "Como usei IA neste projeto" no README, e o RNF-05 exige commits pequenos.

Os principais riscos do uso de IA identificados foram:

- **Código que o autor não sabe explicar**, o que invalida o projeto como portfólio.
- **Testes que passam pelo motivo errado**, escritos para confirmar o código em vez de verificar o comportamento.
- **Revisão superficial**, quando grandes volumes de código pronto são aprovados sem leitura atenta.
- **Decisões tomadas implicitamente pela IA**, sem registro.

As opções avaliadas foram:

- **IA implementa e desenvolvedor revisa:** rápido, mas sujeito a revisão superficial.
- **Teste primeiro (TDD em dupla):** testes definidos e aprovados pelo desenvolvedor antes da implementação feita pela IA.
- **IA faz tudo e desenvolvedor ajusta no fim:** o mais rápido, mas inviabiliza explicar o código.
- **Divisão por tipo de trabalho:** a IA escreve o código mecânico e o desenvolvedor escreve a lógica de negócio, com revisão mútua.

## Decisão

Na v1.0, foi decidido adotar a **divisão por tipo de trabalho**, aproveitando a separação já definida pela arquitetura hexagonal (ADR-003): a IA escrevia o código mecânico e o desenvolvedor escrevia `domain/` e `application/`. A v1.1 passou os casos de uso para a IA, e a v1.2 passou também o domínio (ver as revisões abaixo). A divisão em vigor é:

| Quem faz | O quê | Onde fica |
| --- | --- | --- |
| **Desenvolvedor** | Especificação: escopo e regras (ERS), decisões de arquitetura (ADRs) e critérios de teste (matriz do Plano de Testes). Revisão e aprovação de todo PR, por comentário | `docs/` e PRs |
| **IA**, com aprovação do desenvolvedor em PR (v1.2) | Todo o código: domínio, portas, casos de uso, adapters, bootstrap, API alvo, configuração, CI e migrações | `app/`, `target_api/` e raiz |
| **IA**, com conferência do desenvolvedor | Testes, derivados dos IDs da matriz. O desenvolvedor confere se cada teste verifica o que o nome diz | `tests/` |

**Regras permanentes:**

- Decisões de arquitetura e de escopo são tomadas pelo desenvolvedor e registradas em ADR. A IA levanta alternativas e recomenda, mas não decide.
- Nenhum código entra no repositório sem leitura do desenvolvedor, inclusive o mecânico.
- Nada é integrado à `main` se o desenvolvedor não souber explicar o que o código faz e por quê.
- Commits pequenos, no padrão Conventional Commits, com a IA registrada como coautora nos commits em que ela escreveu código.
- O `CLAUDE.md` registra esta divisão, para que a IA trabalhe dentro do papel definido.
- Toda decisão que a ERS, os ADRs e o Plano de Testes não cobrem é listada na descrição do PR, para o desenvolvedor confirmar ou reverter.
- Todo documento do projeto tem a seção "Registro de uso de IA", fiel ao que aconteceu.

Na v1.0, a escolha foi motivada por:

- **Aprendizado real:** o desenvolvedor escreve a parte que define o comportamento do sistema e domina o núcleo do projeto.
- **Velocidade no que é repetitivo:** configuração, infraestrutura e código de integração ficam com a IA.
- **Encaixe na arquitetura:** a fronteira entre lógica e mecânica coincide com a fronteira entre `domain`/`application` e `adapters`.
- **Defesa em entrevista:** todo o núcleo foi escrito pelo autor, e o restante foi lido e compreendido.

Alternativas descartadas:

- **IA implementa e desenvolvedor revisa:** risco de revisão superficial de grandes volumes de código.
- **Teste primeiro com implementação da IA:** recomendada pela IA. Descartada porque o desenvolvedor não escreveria a lógica de negócio, perdendo o aprendizado do núcleo.
- **IA faz tudo:** incompatível com o objetivo do portfólio.

### Revisão da v1.1

A partir do PR #5, os casos de uso de `application/` passaram a ser implementados pela IA. A mudança foi aplicada na prática antes deste registro; esta versão formaliza o que já acontecia e alinha os documentos ao código.

Motivo: com o domínio e as portas prontos, o que restava em `application/` era majoritariamente orquestração. A exceção é `spec_normalizada.py`, com a regra de normalização e hash do ADR-007, coberta por teste de propriedade com Hypothesis, que encontrou um defeito real (número 1e+17 lido como texto). O comportamento já estava fixado em três lugares escritos ou aprovados pelo desenvolvedor: as regras do domínio, as RN da ERS e a matriz de rastreabilidade do Plano de Testes. Escrever essa orquestração à mão custava prazo sem aumentar o controle sobre o comportamento do sistema. O controle passou da autoria para a especificação e a revisão:

- **Especificação antes do código:** as regras do domínio, as RN e os critérios de teste continuam sendo do desenvolvedor. As portas iniciais também; extensões feitas pela IA entram no PR e são revisadas.
- **Revisão por PR:** nenhum caso de uso entra na `main` sem os quatro jobs do CI verdes, 100% de branches em `application/` e aprovação do desenvolvedor.
- **Decisões explícitas:** toda decisão que os documentos não cobrem é listada na descrição do PR para o desenvolvedor confirmar ou reverter, em vez de ficar implícita no código. O desenvolvedor registra o OK num comentário no PR antes do merge, já que o GitHub não permite ao autor aprovar o próprio PR. Nos PRs #5 e #6, as decisões foram listadas só no relatório do agente e confirmadas fora do GitHub.

Na v1.1, o `domain/` continuou escrito pelo desenvolvedor e bloqueado para escrita da IA.

### Revisão da v1.2

A partir desta versão, a IA escreve todo o código, inclusive `domain/`. O desenvolvedor especifica na ERS, nos ADRs e na matriz do Plano de Testes, revisa e aprova cada PR por comentário, com as decisões não cobertas pelos documentos listadas na descrição.

Motivo: no modelo da v1.1, os defeitos foram encontrados na revisão e nos testes, não pela autoria, e escrever o domínio à mão passou a custar prazo sem aumentar o controle.

Na prática, a v1.2 adota a alternativa "IA implementa e desenvolvedor revisa", descartada na v1.0 pelo risco de revisão superficial de grandes volumes de código. O que mudou desde então são as regras de revisão da v1.1, que passam a valer para todo o código: especificação antes do código, PRs pequenos, decisões listadas na descrição e OK do desenvolvedor em comentário antes do merge.

## Consequências

### Positivas

- O desenvolvedor domina e consegue explicar o núcleo do sistema.
- Trabalho repetitivo e de configuração é acelerado pela IA.
- Processo transparente: commits, ADRs e README mostram o que foi feito por quem.
- Regras explícitas no `CLAUDE.md` mantêm a IA dentro do papel definido.

### Negativas

- Desenvolvimento mais lento do que delegar tudo à IA, estendendo o prazo da v1.
- A fronteira entre mecânico e lógica pode ser ambígua em alguns trechos, como mapeamentos com regras implícitas.
- Exige disciplina para ler de fato o código mecânico, que é volumoso.
- A partir da v1.1, os casos de uso não foram digitados pelo desenvolvedor, e a partir da v1.2 nenhum código é. A capacidade de explicá-lo depende da qualidade da revisão, e não da autoria.

## Conformidade

- O `CLAUDE.md` na raiz deve conter a tabela de divisão deste ADR e as regras permanentes.
- Todo código escrito pela IA, inclusive em `domain/` e `application/`, entra somente por Pull Request, com as decisões não cobertas pelos documentos listadas na descrição do PR e o OK do desenvolvedor registrado em comentário no PR antes do merge.
- Commits com código escrito pela IA devem incluir a IA como coautora na mensagem.
- O README deve ter a seção "Como usei IA neste projeto", resumindo esta divisão e apontando para os ADRs.

## Observações

- A divisão pode ser revisada se o prazo se tornar inviável, com a mudança registrada em nova versão deste ADR. A v1.1 e a v1.2 são essas revisões.
- O plano de testes, feito à parte, deve seguir a divisão definida aqui para os testes.

## Direcionadores

- **f44: Redução da dívida técnica.** Código compreendido pelo autor é código que ele consegue manter.
- **f7: Confiabilidade.** Lógica de negócio escrita e testada com intenção clara reduz testes que passam pelo motivo errado.
- **f4: Velocidade de desenvolvimento.** Trabalho mecânico delegado à IA.
- **f38: Economizar tempo.** Configuração e integração geradas pela IA em vez de escritas manualmente.

## Histórico de versões

| Versão | Data | Alteração |
| --- | --- | --- |
| 1.0 | 07/11/2026 | Criação. |
| 1.1 | 11/11/2026 | Casos de uso de `application/` passam a ser implementados pela IA, com revisão e aprovação por PR. Portas e `domain/` continuam com o desenvolvedor. |
| 1.2 | 11/11/2026 | A IA passa a escrever todo o código, inclusive `domain/`. O desenvolvedor especifica, revisa e aprova por comentário no PR. |

## Registro de uso de IA

- **O que a IA sugeriu:** comparou três fluxos (IA implementa e eu reviso, teste primeiro com implementação da IA, IA faz tudo) e recomendou o teste primeiro, com regras fixas de leitura, commits e documentação. Quando propus outro modelo, montou a tabela de divisão usando as camadas da hexagonal e apontou o custo no prazo.
- **O que aceitei:** as regras fixas e a tabela de divisão baseada na arquitetura.
- **O que decidi diferente:** propus um modelo próprio, diferente dos três apresentados: a IA escreve o trabalho mecânico e eu escrevo a lógica de negócio, revisando com a IA.
- **v1.1:** no fechamento da v1, a IA apontou que este ADR, o `CLAUDE.md`, o RNF-08 da ERS e a seção 5 do Plano de Testes ainda descreviam a divisão antiga, enquanto o código de `application/` já era escrito por ela desde o PR #5. A decisão de mudar a divisão foi minha, tomada na prática antes deste registro. A IA redigiu o texto desta revisão a partir do motivo que dei, e eu aprovei. Na revisão do PR #8, a IA apontou quatro pontos em que o texto não batia com os PRs #5 a #7; concordei e defini as correções.
- **v1.2:** a decisão de a IA escrever também o `domain/` foi minha. Pouco antes, ao conferir a matriz no fechamento da v1, a IA apontou que a US06-C2 não tinha teste e que `consolidar_casos` aceitava caso que falhou sem mensagem, e sugeriu a correção, que ficou para depois desta revisão. A IA redigiu o texto desta revisão a partir do motivo que dei, e eu aprovei. Até a v1.1, o `domain/` foi escrito por mim, com exemplos e trechos da IA. Nem todos os commits com trechos dela têm o trailer de coautoria.
