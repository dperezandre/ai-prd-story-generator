# Padrão de especificação funcional

Este é o padrão que o pipeline gera e que a skill [`po-spec-review`](../skills/po-spec-review/SKILL.md) usa para revisar documentos escritos por áreas de negócio. Ele nasceu da comparação de duas especificações reais de uma operação de saúde, das quais só a estrutura foi aproveitada: nenhum conteúdo desses documentos está neste repositório.

## Estrutura

● obrigatória, ○ opcional.

| # | Seção | | O que precisa conter |
|---|---|---|---|
| 0 | Controle do documento | ● | Registro de alterações (data, autor, versão, referência), colaboradores (nome e função), nota de confidencialidade |
| 1 | Identificação da feature | ● | Nome, versão, data |
| 2.1 | Objetivo | ● | O que a mudança permite, em 2 a 4 frases |
| 2.2 | Justificativa | ● | Por que agora; o problema que ela resolve |
| 2.3 | Situação atual (AS IS) | ● | Fatos sobre como funciona hoje |
| 2.4 | Situação futura (TO BE) | ● | Comportamento futuro em termos observáveis, por ator |
| 2.5 | Sistemas e módulos | ● | Cada sistema com seu módulo |
| 3.1 | User Story | ● | Como / Quero / Para, com um único papel e um valor (não uma solução) |
| 3.2 | Regras de negócio | ● | Numeradas (`RN01`...), atômicas, testáveis, sem sobreposição com os requisitos |
| 3.3 | Especificação detalhada | ● | Para cada campo: tipo, valores permitidos, unidade, obrigatório, o que acontece quando vazio, origem e momento da leitura |
| 3.4 | Critérios de aceite | ● | Gherkin: cenário nomeado, um comportamento por cenário, ao menos um caminho feliz, um alternativo e um de erro; cada cenário aponta a `RN` que cobre |
| 3.5 | Protótipo | ○ | Imagem ou link |
| 3.6 | Cenários de teste | ○ | Casos além do Gherkin |
| 4 | Retornos esperados | ● | Tipo (assistencial, operacional, financeiro, experiência), indicador, linha de base e hipótese de ROI. Preenchido: texto de instrução do modelo não conta |
| 5 | Fora do escopo | ● | Pelo menos um item explícito, além da nota padrão sobre novas versões |
| 6 | Premissas e perguntas em aberto | ● | O que foi assumido e o que falta decidir |
| 7 | Aprovações | ● | Nome, papel e data |

A seção 6 não existia nos dois documentos analisados. Sem ela, lacunas viram suposições silenciosas.

## Como o pipeline mapeia

| Seção do padrão | Campo gerado |
|---|---|
| 2.1, 2.2 | `problem`, `goals` |
| 2.3 / 2.4 | `as_is` / `to_be` |
| 2.5 | `systems` |
| 3.1 | histórias (`as_a`, `i_want`, `so_that`) |
| 3.2 | `business_rules` (histórias apontam para elas em `rule_refs`) |
| 3.4 | `scenarios` (Gherkin) |
| 4 | `expected_returns` |
| 5 | `scope_out` |
| 6 | `assumptions`, `open_questions` |

Fora do pipeline: controle do documento, protótipo, cenários de teste e aprovações, que são do processo da empresa.

## Lista de verificação da revisão

**A. Estrutura**
- Todas as seções obrigatórias existem e estão preenchidas.
- Nenhum texto de instrução do modelo ficou no lugar do conteúdo.
- O sumário bate com o corpo (ordem e numeração).

**B. História**
- Um papel, um valor, sem descrever implementação.
- Cabe em uma sprint (acima de 8 pontos, dividir). Se há várias telas, atores ou integrações, é épico.
- O "Para" não contradiz as regras (ex.: "sem alterações manuais" onde há campos editáveis).

**C. Regras de negócio**
- Numeradas, atômicas e testáveis.
- Sem quantificadores vagos ("todos", "mesma estrutura já existente", "quando permitido").
- Sem contradição entre regras, critérios de aceite e especificação de tela.

**D. Campos e dados**
- Tipo, domínio, unidade, obrigatoriedade e comportamento quando vazio definidos por campo.
- Origem do dado e momento da leitura (admissão, evolução, valor mais recente?).

**E. Gherkin**
- Cenário nomeado, um comportamento por cenário, com caminho de erro e alternativo.
- Cada cenário rastreável a uma `RN`.

**F. Consistência**
- Título, objetivo, história, regras, protótipo e critérios descrevem a mesma coisa.
- O que está fora do escopo não reaparece na especificação.

**G. Integrações e falhas**
- Dependências externas e o que acontece quando indisponíveis.
- Registros já existentes (migração ou compatibilidade).
- Perfis e permissões. O que é persistido e para quê.

**H. Retornos**
- Tipo, indicador e linha de base. Sem número inventado.

**I. Domínio regulado ou clínico**
- Quem valida limites e parâmetros clínicos.
- O que acontece com dados ausentes, fora de faixa ou desatualizados quando uma regra age sozinha.
