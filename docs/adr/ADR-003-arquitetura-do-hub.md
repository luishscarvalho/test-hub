# ADR-003: Arquitetura do hub

## Título

Adoção da **Arquitetura Hexagonal (Ports & Adapters)** para o back-end do **Test Hub**.

## Status

Aprovada

## Data

02/11/2026

## Versão

1.2

## Proprietário ADR

Luis Henrique S. Carvalho

## Contexto

O Test Hub tem quatro subdomínios: cadastro de APIs alvo, geração de testes, execução e histórico. A v1 tem prazo de 3 a 5 dias, mas o roadmap já prevê crescimento: detecção de flaky e dashboard na v2, e suporte a APIs públicas externas na v3. Na v3 é provável a troca ou a combinação do gerador de testes com uma ferramenta externa (como Schemathesis), já que APIs públicas nem sempre trazem exemplos na spec.

A arquitetura precisava equilibrar:

- **Testabilidade:** a lógica central (gerar casos de teste a partir da spec e avaliar a resposta contra o schema) deve ser testável sem banco e sem rede (RNF-02).
- **Abertura a crescimento:** novas versões não devem exigir reestruturação do código existente.
- **Prazo da v1:** o custo inicial da estrutura não pode inviabilizar a entrega.
- **Compatibilidade com o ADR-002:** o SQLModel une modelo de tabela e modelo Pydantic, o que impacta o isolamento do domínio.

As opções avaliadas foram:

- **Modular por subdomínio com camadas leves:** módulos com router, service e repository, lógica central em funções puras. Baixo custo inicial e boa testabilidade, mas com isolamento dependente de disciplina.
- **Hexagonal (Ports & Adapters):** domínio e casos de uso isolados de frameworks e infraestrutura por meio de portas (interfaces) e adaptadores. Maior isolamento e facilidade de troca de tecnologia, com mais artefatos no início.
- **Estrutura plana (routers, services, models):** início mais rápido, mas tende à desorganização com quatro subdomínios.
- **Vertical slice:** uma pasta por funcionalidade. Cresce bem por versão, mas a lógica de geração e execução é compartilhada entre funcionalidades e exigiria um núcleo comum de qualquer forma.
- **Modular com uma porta apenas no gerador:** variação da primeira opção, isolando somente o ponto de troca mais provável.

## Decisão

Foi decidido adotar a **Arquitetura Hexagonal (Ports & Adapters)** no back-end do Test Hub, com um único hexágono para o serviço na v1.

A estrutura será:

```
app/
  domain/          entidades e regras de negócio puras
  application/     casos de uso e portas (interfaces de saída)
  adapters/
    inbound/http/          rotas FastAPI e DTOs
    inbound/worker/        ponto de entrada do worker (ver ADR-006)
    outbound/persistence/  tabelas SQLModel, repositórios e mapeamento
    outbound/queue/        fila com RQ e Redis (ver ADR-006)
    outbound/spec_loader/  leitura e validação da spec
    outbound/generator/    geração e execução dos testes (ver ADR-005)
  bootstrap/       composição das dependências
```

A escolha foi motivada por:

- **Abertura a crescimento:** entre as opções avaliadas, é a que melhor suporta a evolução prevista para v2 e v3 sem reestruturação.
- **Troca de tecnologia sem impacto no domínio:** o gerador de testes, a fila, o carregador de spec e a persistência ficam atrás de portas. Substituir a implementação do gerador de testes, por exemplo, exige apenas um novo adapter.
- **Testabilidade máxima:** domínio e casos de uso são testados com adapters falsos em memória, sem banco, rede ou framework.
- **Regras de negócio explícitas:** RN-03 a RN-07 e RN-11 a RN-16 ficam no domínio e nos casos de uso, em código puro, e não espalhadas por rotas e consultas.

**Relação com o ADR-002:** o SQLModel fica restrito ao adapter de persistência. O domínio usa entidades próprias, sem dependência de SQLModel, e o mapeamento entre entidade e tabela é responsabilidade do repositório.

**Chamadas à API alvo:** não há adapter próprio de cliente HTTP. Como o Schemathesis gera e executa os casos (ADR-005), as chamadas à API alvo ficam dentro do adapter do gerador.

Alternativas descartadas:

- **Modular com camadas leves:** recomendada inicialmente pela IA pelo menor custo na v1, mas com isolamento dependente apenas de disciplina e menor abertura a crescimento.
- **Modular com porta apenas no gerador:** resolveria a troca mais provável, mas deixaria a persistência e as demais integrações acopladas.
- **Estrutura plana:** não comporta bem quatro subdomínios.
- **Vertical slice:** exigiria um núcleo compartilhado de qualquer forma, perdendo sua principal vantagem neste cenário.

## Consequências

### Positivas

- Domínio e casos de uso testáveis de forma unitária, rápida e sem I/O.
- Troca de gerador, banco, fila ou carregador de spec sem alterar regras de negócio.
- Fronteiras claras entre o que é regra do produto e o que é detalhe técnico, facilitando a leitura do código por terceiros.
- Base preparada para v2 e v3 sem reestruturação.

### Negativas

- **Mais artefatos e mapeamentos:** entidades de domínio, tabelas SQLModel e DTOs da API são estruturas distintas, com conversão entre elas.
- **Redução do ganho do SQLModel:** a principal vantagem considerada no ADR-002 (menos código por unir tabela e Pydantic) diminui, pois o domínio não usa os modelos SQLModel.
- **Risco ao prazo da v1:** a estrutura inicial consome mais tempo do que as alternativas mais simples.
- **Risco de sobreengenharia:** portas criadas sem necessidade real de troca adicionam abstração sem retorno.

## Conformidade

- O pacote `domain` não pode importar FastAPI, SQLModel, SQLAlchemy, bibliotecas HTTP nem qualquer código de `adapters`.
- O pacote `application` pode importar apenas `domain` e as próprias portas.
- As regras de importação acima devem ser verificadas automaticamente no CI (por exemplo, com import-linter). Violação quebra o build.
- Toda dependência externa usada por um caso de uso deve ser acessada por uma porta definida em `application`.
- Rotas FastAPI apenas convertem DTO para chamada de caso de uso e o resultado para DTO de resposta, sem regra de negócio.
- O ponto de entrada do worker apenas chama o caso de uso montado em `bootstrap`, sem regra de negócio.
- A ligação entre portas e adapters acontece somente em `bootstrap`.
- Testes de domínio e de casos de uso devem usar adapters falsos em memória. Adapters de saída têm testes de integração próprios.
- Nova porta só deve ser criada quando houver dependência externa real a isolar.

## Observações

- Na v1 o hub terá um único hexágono. Se os subdomínios crescerem a ponto de justificar, a divisão em módulos internos pode ser registrada em nova ADR.
- Com o SQLModel restrito à persistência, a escolha de ORM do ADR-002 pode ser revisada caso o SQLAlchemy puro passe a fazer mais sentido.
- Se a estrutura comprometer o prazo da v1, a simplificação deve ser registrada em ADR que substitua esta, em vez de abandonada silenciosamente.

## Direcionadores

- **f11: Testabilidade.** Domínio e casos de uso testados sem I/O, com adapters falsos.
- **f44: Redução da dívida técnica.** Fronteiras verificadas no CI impedem acoplamento indevido ao longo das versões.
- **f7: Confiabilidade.** Regras de negócio centralizadas no domínio reduzem divergências de comportamento.
- **f5/f6: Velocidade e confiabilidade de implantação.** Mudanças em infraestrutura ficam restritas aos adapters, reduzindo o risco de regressão em releases.

## Histórico de versões

| Versão | Data | Alteração |
| --- | --- | --- |
| 1.0 | 02/11/2026 | Criação. |
| 1.1 | 07/11/2026 | Referências ao gerador de testes atualizadas após o ADR-005. |
| 1.2 | 08/11/2026 | Estrutura alinhada aos ADR-005 e ADR-006: inclusão da fila e do ponto de entrada do worker, remoção do adapter de cliente HTTP e regras de negócio atualizadas. |

## Registro de uso de IA

- **O que a IA sugeriu:** comparou modular com camadas leves, hexagonal, estrutura plana e vertical slice, recomendando modular com camadas leves pelo prazo da v1 e pela compatibilidade com o SQLModel. Quando questionada sobre escalabilidade, explicou que a arquitetura de código não afeta escala de carga, apontou hexagonal e vertical slice como as mais abertas a crescimento de código e sugeriu um meio-termo: modular com uma porta apenas no gerador.
- **O que aceitei:** a análise das opções e o alerta sobre o conflito com o SQLModel, resolvido restringindo o SQLModel ao adapter de persistência.
- **O que decidi diferente:** escolhi a hexagonal completa em vez da modular recomendada e do meio-termo sugerido, priorizando a abertura a crescimento do software.
- **v1.2:** em uma revisão cruzada dos documentos, a IA apontou que a estrutura não refletia a fila e o worker do ADR-006 e que o adapter de cliente HTTP ficou sem uso com o Schemathesis, e propôs os ajustes desta versão. Aceitei.
