# Enviar histórias e tasks para o Azure DevOps

Em vez de importar um CSV, o projeto pode criar os work items para você pela API REST do Azure DevOps: uma **User Story** por história e as **Tasks** dela como filhas. Não há épicos nem features.

> **Situação.** O código é testado com respostas HTTP simuladas, e os endpoints foram conferidos na documentação oficial do Azure DevOps (REST 7.1). Ele **ainda não rodou contra uma organização real**. Faça o primeiro envio em um projeto de sandbox.

## 1. Crie um token de acesso pessoal (PAT)

No Azure DevOps: **User settings → Personal access tokens → New token**. Dê uma validade curta e o escopo **Work Items: Read & write**. Copie o token uma vez; o Azure não o mostra de novo.

Nunca cole o token em um chat, em um arquivo ou no repositório.

## 2. Deixe o token disponível

PowerShell, na mesma janela em que vai rodar o comando:

```powershell
$env:AZDO_PAT = "<seu token>"
```

O app tem um campo de senha no lugar; o token fica só naquela sessão do navegador e nunca é armazenado.

## 3. Sempre veja a prévia primeiro

```bash
python -m scripts.azure_push historias.json --org <organização> --project <projeto>
```

Sem `--yes`, o comando só mostra o que criaria, marcado como `[new]`, `[already sent]` ou `[partly sent]`, e não envia nada. A prévia não precisa do token.

A entrada é um resultado gerado (JSON de `PipelineResult`) ou o JSON da skill `po-spec-review` (histórias com `title`, `description`, `acceptance_criteria` e `tasks`).

## 4. Envie

```bash
python -m scripts.azure_push historias.json --org <organização> --project <projeto> --yes
```

Opções: `--area` e `--iteration` definem os caminhos de área e iteração (padrão: a raiz do projeto); `--ledger CAMINHO` escolhe onde o arquivo de controle fica.

O que acontece: o tipo de história do projeto é detectado (User Story, Product Backlog Item, Requirement ou Issue), depois cada história é criada, e então suas tasks com vínculo de pai. Os campos opcionais (critérios de aceite, story points ou effort, prioridade) só vão se o processo do projeto os tiver. Se o processo não tem o campo Acceptance Criteria (por exemplo, Basic), os critérios são acrescentados à descrição da história, sob um título, em vez de serem descartados.

## O que o arquivo de controle faz

A cada work item criado, o comando grava um arquivo pequeno ao lado da entrada (`<nome>.azdo-ledger.json`). Se você rodar de novo, as histórias terminadas são puladas, e uma história que perdeu tasks por causa de um erro recebe só as que faltam. O que o arquivo registrou não é criado de novo. Ainda é possível haver duplicatas se uma requisição der timeout depois de o Azure já ter criado o item, ou se você regenerar as histórias com texto diferente (elas contam como histórias novas). Duas histórias idênticas na mesma entrada são rejeitadas. `--force` ignora o arquivo e cria tudo de novo.

## Pelo app e pela skill

- **App:** no modo real, abra a aba **Exportar** → **Link com Azure DevOps**, preencha organização, projeto e token, clique em **Ver prévia** e depois em **Enviar ao Azure DevOps**. Fica oculto no modo demo.
- **Skill:** depois do PDF, a `po-spec-review` oferece o envio. Ela mostra a prévia e pede um sim claro antes de enviar, e nunca lê o token. Instale com `python -m scripts.install_skill`.

## Se algo falhar

| Mensagem | Causa provável |
|---|---|
| "rejected the token (it answered with a sign-in page)" | Token errado ou expirado, ou sem o escopo de Work Items |
| "Organization or project not found" | Confira os nomes; a organização é o trecho depois de `dev.azure.com/` |
| "none of the supported story types" | O processo do projeto não tem User Story, PBI, Requirement nem Issue |
| "refused the request (...)" | Uma regra do projeto, por exemplo um campo obrigatório; o detalhe do Azure aparece |
| "rate limiting" | Espere e rode de novo; o arquivo de controle guarda o que já foi criado |
