---
name: po-spec-review
description: Revisa e padroniza especificações funcionais escritas por áreas de negócio (PDF, Word ou texto): confere a estrutura padrão, aponta contradições e lacunas, quebra em histórias INVEST com critérios de aceite em Gherkin e reescreve no padrão. Use quando o usuário anexar uma especificação ou PRD e pedir "validar", "revisar", "quebrar em histórias", "padronizar" ou "converter para o padrão".
---

# po-spec-review

Revisa uma especificação funcional como um PO crítico e a leva ao padrão descrito em `standard.pt-BR.md` (mesma pasta). Leia esse arquivo antes de começar: a estrutura obrigatória e a lista de verificação A a I vêm dele.

## Regras que valem sempre

1. **Confidencialidade.** O documento é do usuário e costuma ser confidencial. Não grave trechos dele em repositório, não envie a serviço externo, não cole em arquivo versionado. Arquivos temporários (texto extraído, imagens das páginas) ficam no scratchpad e são apagados ao final. Nomes de pessoas do documento não entram na análise, só papéis.
2. **Fiel ao texto.** Aponte o que está escrito; não invente regra, campo, valor ou número. O que faltar vira pergunta, não suposição.
3. **Separe o que é fato do que é inferência.** Diga qual página ou seção sustenta cada achado.

## Fluxo

1. **Ler.** PDF com texto: extraia o texto. Páginas sem texto (imagens): renderize em PNG (PyMuPDF `fitz`, 100 dpi) e leia as imagens, inclusive protótipos e tabelas. Ignore as páginas de certificado de assinatura. Se o documento for longo, leia tudo antes de concluir.
2. **Conferir a estrutura** (lista A do padrão): seção por seção, presente, ausente ou com texto de instrução do modelo no lugar do conteúdo.
3. **Achar contradições e lacunas** (listas B a I). Numere os achados e classifique cada um:
   - **Contradição**: duas partes do documento dizem coisas incompatíveis. Cite as duas.
   - **Lacuna**: falta algo para construir ou testar. Diga o que falta.
   - **Qualidade**: texto vago, história grande, Gherkin fraco.
4. **Quebrar em histórias.** Tabela: id, história (Como/Quero/Para), MoSCoW, pontos, regras `RN` cobertas, veredito INVEST (ok, dividir, bloqueada por qual achado). Histórias acima de 8 pontos são divididas. Habilitadoras técnicas são marcadas como tal.
5. **Escrever o Gherkin** das histórias não bloqueadas: cenário nomeado, um comportamento por cenário, ao menos feliz, alternativo e erro, cada um apontando a `RN`. Histórias bloqueadas só recebem a pergunta que as desbloqueia.
6. **Entregar.** Responda em português do Brasil, nesta ordem: resumo em 3 linhas; conformidade com o padrão; contradições; lacunas; qualidade; quebra em histórias; perguntas para a área de negócio, agrupadas por quem deve responder (negócio, médico/consultor, tecnologia); por fim, o PDF das histórias (seção abaixo).

## PDF das histórias (sempre, no final)

Depois da resposta, gere um PDF com as histórias quebradas para o Azure DevOps. Cada história tem exatamente três blocos, nesta ordem: **Título**, **Descrição** e **Critérios de aceite**.

1. Monte um JSON no scratchpad: `{"document": "<nome da especificação>", "stories": [{"title": "...", "description": "Como ..., quero ..., para ...", "acceptance_criteria": ["Cenário: ...\n  Dado ...\n  Quando ...\n  Então ...", "..."]}]}`.
2. Título curto e no imperativo (vira o Title do work item). Descrição no formato Como/Quero/Para (vira a Description). Cada critério é um cenário Gherkin completo, um comportamento por cenário (vira o Acceptance Criteria).
3. Inclua **todas** as histórias da tabela. Nas bloqueadas, escreva os critérios que o texto já sustenta e marque cada ponto em aberto como `[A DEFINIR] <a pergunta>`. Nunca preencha o vazio com suposição.
4. Rode `python "<pasta desta skill>/scripts/stories_pdf.py" <json> "<saida.pdf>"` (precisa de `pip install pymupdf`).
5. Salve na **mesma pasta do documento analisado**, com o nome `Historias - <nome do documento>.pdf`. Se o documento não for um arquivo, pergunte a pasta. Nunca salve dentro de um repositório público.
6. Apague o JSON temporário e informe o caminho completo do PDF.

## Modo converter

Se o usuário pedir para "converter", "padronizar" ou "reescrever": produza a especificação completa no padrão, preservando o conteúdo do original, marcando como `[A DEFINIR]` tudo que for lacuna e **sem preencher** com suposição. Salve no caminho que o usuário indicar, nunca dentro de um repositório público.

## Pipeline do repositório

Quando o usuário quiser rodar o pipeline automatizado (app Streamlit ou `python -m scripts.generate_examples`), lembre que o texto é enviado ao provedor de IA escolhido. Para documentos confidenciais, prefira esta revisão feita aqui.
