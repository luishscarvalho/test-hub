# ADR-007: Armazenamento da spec

## Título

Armazenamento da spec OpenAPI em **tabela de versões** no PostgreSQL (JSONB + hash), com **novo download a cada run** para specs cadastradas por URL.

## Status

Aprovada

## Data

07/11/2026

## Versão

1.2

## Proprietário ADR

Luis Henrique S. Carvalho

## Contexto

Toda API alvo tem uma spec OpenAPI, informada por URL ou por arquivo no cadastro (US-01) e validada antes de ser aceita (US-02). A spec é a entrada do gerador de testes (ADR-005), que usa seed fixa para tornar as runs reproduzíveis.

A seed só garante reprodutibilidade se a spec usada também for conhecida. Specs mudam ao longo do tempo, e o histórico nunca pode ser sobrescrito (RN-05). Portanto, cada run precisa saber exatamente contra qual spec foi executada.

As opções avaliadas foram:

- **JSONB na tabela da API:** simples, mas uma spec nova sobrescreve a anterior e runs antigas perdem a referência.
- **Tabela de versões da spec:** cada versão guarda conteúdo em JSONB e um hash do conteúdo. A run referencia a versão usada. Histórico completo, sem duplicar specs iguais.
- **Arquivo em volume do Docker:** spec fora do banco, com backup e consistência separados e risco de arquivo removido com runs ainda apontando para ele.
- **Somente a URL:** não reproduz runs antigas e não atende specs enviadas como arquivo.

Também foi avaliado se, para specs cadastradas por URL, o hub deve baixar a spec novamente a cada run ou mantê-la congelada desde o cadastro.

## Decisão

Foi decidido armazenar as specs em uma **tabela de versões** no PostgreSQL e, para specs cadastradas por URL, **baixar a spec novamente a cada run**.

**Modelo:**

- Tabela `spec_versao` com: identificador, API alvo, conteúdo em JSONB, hash SHA-256 do conteúdo, origem (URL ou arquivo) e data de criação.
- Restrição de unicidade em (API alvo, hash): a mesma spec nunca é gravada duas vezes para a mesma API.
- Toda run que chegou a resolver a spec referencia a `spec_versao` usada. A referência é preenchida pelo worker quando a spec é resolvida.
- Versões de spec são imutáveis.

**Normalização:** specs em YAML são convertidas para JSON. O hash é calculado sobre o JSON normalizado (chaves ordenadas), para que diferenças só de formatação não gerem versões novas.

**Fluxo por run:**

1. O worker (ADR-006) inicia a run.
2. Se a spec da API foi cadastrada por URL, o worker baixa a spec, valida e calcula o hash.
3. Se o hash já existe para aquela API, a run usa a versão existente. Se não existe, uma nova versão é criada.
4. Se a spec foi cadastrada por arquivo, a run usa a versão mais recente.
5. Se o download falhar ou a spec baixada for inválida, a run termina como `falhou`, com mensagem de erro no nível da run e sem resultados de teste. Nesse caso, a run fica sem `spec_versao`.

A escolha foi motivada por:

- **Reprodutibilidade:** run + seed + versão da spec permitem repetir exatamente a mesma execução.
- **Rastreabilidade do contrato:** o histórico mostra quando a spec da API mudou, o que ajuda a investigar falhas que aparecem de uma run para outra.
- **Histórico íntegro:** nenhuma run perde a referência da spec usada (RN-05).
- **Tudo no banco:** spec e runs ficam na mesma transação e no mesmo backup.

Alternativas descartadas:

- **JSONB na tabela da API:** perde a referência das runs antigas.
- **Arquivo em volume:** separa spec e histórico, com risco de inconsistência.
- **Somente a URL:** não reproduz runs e não atende upload de arquivo.
- **Spec congelada no cadastro:** esconde mudanças de contrato da API alvo.

## Consequências

### Positivas

- Qualquer run pode ser reproduzida com a mesma spec e a mesma seed.
- Mudanças de contrato da API alvo ficam registradas e datadas automaticamente.
- Specs iguais não ocupam espaço duplicado.
- Base útil para a v2: separar falhas causadas por mudança de spec de falhas intermitentes.

### Negativas

- Uma tabela e um relacionamento a mais no modelo de dados.
- Toda run de API cadastrada por URL depende de a spec estar acessível naquele momento.
- O texto original da spec (formatação e comentários do YAML) não é preservado, apenas o conteúdo normalizado.
- O volume de dados cresce a cada mudança de spec, sem limpeza automática na v1.

## Conformidade

- A chave estrangeira `spec_versao_id` da run é opcional no banco. Run com resultados de teste deve ter `spec_versao` preenchida, e essa regra deve ter teste próprio.
- Registros de `spec_versao` nunca podem ser alterados, e não podem ser removidos enquanto houver run que os referencie.
- O hash deve ser calculado sobre o JSON normalizado, e essa normalização deve ter teste próprio (mesma spec em YAML e JSON gera o mesmo hash).
- O download e a validação da spec devem passar pela porta de carregamento de spec definida no ADR-003, sem acesso HTTP direto no domínio.
- Falha de download ou spec inválida durante a run devem resultar em run `falhou` com mensagem explicando o motivo, coberta por teste.
- A validação aplicada no cadastro (US-02) e a aplicada a cada run devem ser a mesma.
- Spec sem nenhum endpoint é considerada inválida, e essa regra deve ter teste próprio.

## Observações

- Ajustes no ERS: a US-02 passa a valer também no início de cada run de spec por URL, a run passa a registrar a versão da spec usada, e a run pode falhar por spec inacessível ou inválida.
- Atualização manual de spec cadastrada por arquivo não está prevista na v1.
- Política de limpeza de versões antigas sem runs associadas pode ser avaliada em versões futuras.

## Direcionadores

- **f7: Confiabilidade.** Runs reproduzíveis e histórico que nunca perde referência.
- **f44: Redução da dívida técnica.** Versionamento definido desde o início evita migração de dados quando o histórico já estiver grande.
- **f11: Testabilidade.** Normalização e hash são lógica pura, testável sem I/O.
- **f22: Melhor experiência do usuário.** Quem investiga uma falha vê se a spec mudou entre as runs.

## Histórico de versões

| Versão | Data | Alteração |
| --- | --- | --- |
| 1.0 | 07/11/2026 | Criação. |
| 1.1 | 08/11/2026 | Referência da run para spec_versao passa a ser opcional até o worker resolver a spec. |
| 1.2 | 08/11/2026 | Texto alinhado à RN-13 (imutabilidade e momento da referência) e spec sem endpoints tratada como inválida. |

## Registro de uso de IA

- **O que a IA sugeriu:** comparou JSONB na tabela da API, tabela de versões, arquivo em volume e somente URL, recomendando a tabela de versões com hash. Recomendou também baixar a spec novamente a cada run para specs por URL. Na redação deste ADR, definiu a normalização antes do hash e o comportamento de run `falhou` quando a spec está inacessível ou inválida. Durante a modelagem do banco, apontou que a referência obrigatória para `spec_versao` conflitava com o fluxo da run (run criada em `na_fila` antes de a spec ser resolvida, e runs que falham ou são interrompidas sem versão) e propôs tornar a chave estrangeira opcional.
- **O que aceitei:** a tabela de versões, o novo download a cada run e a chave estrangeira opcional para `spec_versao`.
- **O que decidi diferente:** nada.
- **v1.2:** em uma revisão cruzada dos documentos, a IA apontou divergências de texto com a RN-13 e que uma spec sem endpoints passaria com zero testes, e recomendou tratá-la como inválida. Aceitei.
