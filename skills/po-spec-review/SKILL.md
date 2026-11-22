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

Depois da resposta, gere um PDF com as histórias quebradas para o Azure DevOps. Cada história tem exatamente quatro blocos, nesta ordem: **Título**, **Descrição**, **Critérios de aceite** e **Tasks**.

1. Monte um JSON no scratchpad: `{"document": "<nome da especificação>", "stories": [{"title": "...", "description": "Como ..., quero ..., para ...", "acceptance_criteria": ["Cenário: ...\n  Dado ...\n  Quando ...\n  Então ...", "..."], "tasks": [{"title": "...", "description": "..."}]}]}`.
2. Título curto e no imperativo (vira o Title do work item). Descrição no formato Como/Quero/Para (vira a Description). Cada critério é um cenário Gherkin completo, um comportamento por cenário (vira o Acceptance Criteria). Cada task é um trabalho concreto (construir, testar, configurar, documentar) com título no infinitivo e uma descrição curta dizendo qual cenário entrega.
3. Inclua **todas** as histórias da tabela, cada uma com de 2 a 6 tasks. **Sem horas, dias ou estimativas** nas tasks, e só com o que o texto sustenta. Nas histórias bloqueadas, escreva os critérios que o texto já sustenta, as tasks que não dependem do ponto em aberto e marque cada ponto em aberto como `[A DEFINIR] <a pergunta>`. Nunca preencha o vazio com suposição.
4. Rode `python "<pasta desta skill>/scripts/stories_pdf.py" <json> "<saida.pdf>"` (precisa de `pip install pymupdf`).
5. Salve na **mesma pasta do documento analisado**, com o nome `Historias - <nome do documento>.pdf`. Se o documento não for um arquivo, pergunte a pasta. Nunca salve dentro de um repositório público.
6. Informe o caminho completo do PDF e **mantenha o JSON** até o usuário decidir sobre o envio ao Azure DevOps (seção abaixo). Depois da decisão, apague o JSON.

## Subir para o Azure DevOps (opcional, só com confirmação)

Pergunte ao usuário se quer enviar as histórias e tasks ao Azure DevOps. Só histórias e tasks são enviadas (sem épicos nem features). Se ele aceitar:

1. Peça o nome da **organização** e do **projeto**. Se for a primeira vez, recomende um projeto de sandbox.
2. O token (PAT com permissão de leitura e escrita em Work Items) fica na variável de ambiente `AZDO_PAT`. Diga ao usuário para defini-la **no próprio terminal** (PowerShell: `$env:AZDO_PAT = "<token>"` na mesma janela em que o comando vai rodar). **Nunca peça, leia nem repita o token no chat.**
3. Leia o caminho do repositório em `repo-path.txt` (nesta pasta da skill). Rode a **prévia**, que não envia nada: `cd "<repositório>"` e `python -m scripts.azure_push "<json>" --org <organização> --project <projeto>`. Use o Python onde as dependências do repositório estão instaladas (`pip install -r requirements.txt`). Mostre a prévia ao usuário (histórias, tasks, avisos).
4. Pergunte: "Confirma o envio?". Só com um **sim explícito**, rode o mesmo comando com `--yes`. A prévia e o envio usam um arquivo de controle (`<json>.azdo-ledger.json`, ao lado do JSON): repetir o comando não duplica nada. Para guardá-lo junto do PDF, passe `--ledger "<pasta do PDF>/Historias - <documento>.azdo-ledger.json"`.
5. Informe o resumo e os links dos work items. Se der erro, mostre a mensagem (ela nunca traz o token) e diga o que já foi criado.
6. Apague o JSON temporário. Deixe o arquivo de controle ao lado do PDF.

## Modo converter

Se o usuário pedir para "converter", "padronizar" ou "reescrever": produza a especificação completa no padrão, preservando o conteúdo do original, marcando como `[A DEFINIR]` tudo que for lacuna e **sem preencher** com suposição. Salve no caminho que o usuário indicar, nunca dentro de um repositório público.

## Pipeline do repositório

Quando o usuário quiser rodar o pipeline automatizado (app Streamlit ou `python -m scripts.generate_examples`), lembre que o texto é enviado ao provedor de IA escolhido. Para documentos confidenciais, prefira esta revisão feita aqui.
