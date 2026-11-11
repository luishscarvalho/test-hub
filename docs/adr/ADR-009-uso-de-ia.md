# ADR-009: Uso de IA no projeto

## Título

Divisão de trabalho entre desenvolvedor e **IA** no **Test Hub**: o desenvolvedor escreve o domínio e define as portas, as regras e os critérios de teste; a IA escreve o código mecânico e implementa os casos de uso, com toda mudança revisada e aprovada pelo desenvolvedor em Pull Request.

## Status

Aprovada

## Data

07/11/2026

## Versão

1.1

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

Foi decidido adotar a **divisão por tipo de trabalho**, aproveitando a separação já definida pela arquitetura hexagonal (ADR-003):

| Quem escreve | O quê | Onde fica |
| --- | --- | --- |
| **Desenvolvedor**, com revisão da IA | Regras de negócio: consolidação de resultados, status da run, imutabilidade. Portas dos casos de uso | `domain/` e `application/portas.py` |
| **IA**, com revisão e aprovação do desenvolvedor em PR (v1.1) | Casos de uso, implementados a partir das portas, das RN da ERS e da matriz do Plano de Testes | `application/` |
| **IA**, com leitura do desenvolvedor | Estrutura do projeto, Dockerfile, Docker Compose, CI, configurações, migrações, rotas FastAPI, DTOs, mapeamentos, adapters (Schemathesis, RQ, banco, HTTP) e API alvo | `adapters/`, `bootstrap/`, `target_api/` e raiz |
| **Em conjunto** | Testes do domínio: o desenvolvedor define os casos, a IA ajuda a escrever. Testes dos casos de uso: a IA deriva os casos dos IDs da matriz e o desenvolvedor confere se cada um testa o que o nome diz | `tests/` |

**Regras permanentes:**

- Decisões de arquitetura e de escopo são tomadas pelo desenvolvedor e registradas em ADR. A IA levanta alternativas e recomenda, mas não decide.
- Nenhum código entra no repositório sem leitura do desenvolvedor, inclusive o mecânico.
- Nada é integrado à `main` se o desenvolvedor não souber explicar o que o código faz e por quê.
- Commits pequenos, no padrão Conventional Commits, com a IA registrada como coautora nos commits em que ela escreveu código.
- O `CLAUDE.md` registra esta divisão, para que a IA não escreva lógica de negócio por conta própria.
- Todo documento do projeto tem a seção "Registro de uso de IA", fiel ao que aconteceu.

A escolha foi motivada por:

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

Motivo: com o domínio e as portas prontos, o que restava em `application/` era orquestração. O comportamento já estava fixado em três lugares escritos ou aprovados pelo desenvolvedor: as regras do domínio, as RN da ERS e a matriz de rastreabilidade do Plano de Testes. Escrever essa orquestração à mão custava prazo sem aumentar o controle sobre o comportamento do sistema. O controle passou da autoria para a especificação e a revisão:

- **Especificação antes do código:** portas, regras e critérios de teste continuam sendo do desenvolvedor.
- **Revisão por PR:** nenhum caso de uso entra na `main` sem os quatro jobs do CI verdes, 100% de branches em `application/` e aprovação do desenvolvedor.
- **Decisões explícitas:** toda decisão que os documentos não cobrem é listada na descrição do PR para o desenvolvedor confirmar ou reverter, em vez de ficar implícita no código.

O `domain/` continua escrito pelo desenvolvedor e bloqueado para escrita da IA.

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
- A partir da v1.1, os casos de uso não foram digitados pelo desenvolvedor. A capacidade de explicá-los depende da qualidade da revisão, e não da autoria.

## Conformidade

- O `CLAUDE.md` na raiz deve conter a tabela de divisão deste ADR e as regras permanentes.
- Alterações em `domain/` escritas pela IA só são aceitas como sugestão de revisão, nunca como código integrado diretamente. O `.claude/settings.json` bloqueia essa escrita.
- Alterações em `application/` escritas pela IA entram somente por Pull Request aprovado pelo desenvolvedor, com as decisões não cobertas pelos documentos listadas na descrição do PR.
- Commits com código escrito pela IA devem incluir a IA como coautora na mensagem.
- Trechos ambíguos entre mecânico e lógica são tratados como lógica.
- O README deve ter a seção "Como usei IA neste projeto", resumindo esta divisão e apontando para os ADRs.

## Observações

- A divisão pode ser revisada se o prazo se tornar inviável, com a mudança registrada em nova versão deste ADR. A v1.1 é essa revisão.
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

## Registro de uso de IA

- **O que a IA sugeriu:** comparou três fluxos (IA implementa e eu reviso, teste primeiro com implementação da IA, IA faz tudo) e recomendou o teste primeiro, com regras fixas de leitura, commits e documentação. Quando propus outro modelo, montou a tabela de divisão usando as camadas da hexagonal e apontou o custo no prazo.
- **O que aceitei:** as regras fixas e a tabela de divisão baseada na arquitetura.
- **O que decidi diferente:** propus um modelo próprio, diferente dos três apresentados: a IA escreve o trabalho mecânico e eu escrevo a lógica de negócio, revisando com a IA.
- **v1.1:** no fechamento da v1, a IA apontou que este ADR, o `CLAUDE.md`, o RNF-08 da ERS e a seção 5 do Plano de Testes ainda descreviam a divisão antiga, enquanto o código de `application/` já era escrito por ela desde o PR #5. A decisão de mudar a divisão foi minha, tomada na prática antes deste registro. A IA redigiu o texto desta revisão a partir do motivo que dei, e eu aprovei.
