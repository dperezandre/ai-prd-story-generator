# Como importar os CSVs gerados no Azure DevOps e no Jira

O app exporta dois arquivos: `azure_devops.csv` e `jira.csv`. Os dois trazem uma linha de **Épico** por épico, seguida de suas **histórias de usuário**, com prioridade MoSCoW, pontos e os critérios de aceite em Gherkin.

> **Situação deste guia.** Os passos e os nomes de colunas foram conferidos na documentação oficial da Microsoft Learn e da Atlassian (links no final). Eles **ainda não foram testados em uma organização real do Azure DevOps nem em um site Jira**. Importe sempre um primeiro arquivo de teste em um projeto de sandbox.

## O que há em cada arquivo

**`azure_devops.csv`**

| Coluna | Conteúdo |
|---|---|
| Work Item Type | `Epic` ou `User Story` |
| Title 1 / Title 2 | O nome do épico vai em `Title 1`; o título da história vai em `Title 2`. Esse recuo cria o vínculo pai/filho. |
| Description | "Como ... quero ... para ..." em HTML |
| Acceptance Criteria | Cenários Gherkin em HTML |
| Priority | MoSCoW mapeado para 1-4 (Must=1, Should=2, Could=3, Won't=4) |
| Story Points | Estimativa |
| Tags | `MoSCoW-Must`, `MoSCoW-Should`, `MoSCoW-Could`, `MoSCoW-Wont` |

**`jira.csv`**

| Coluna | Conteúdo |
|---|---|
| Issue Id | Número único por linha (épicos primeiro) |
| Issue Type | `Epic` ou `Story` |
| Summary | Nome do épico ou título da história |
| Description | "Como ... quero ... para ..." mais os critérios de aceite em Gherkin |
| Priority | MoSCoW mapeado para Highest/High/Medium/Low |
| Parent | Na história, o `Issue Id` do seu épico |
| Labels | `moscow-must`, `moscow-should`, `moscow-could`, `moscow-wont` |

## Azure DevOps

### Antes de começar
- Para importar work items, você precisa ser membro de **Project Administrators** ou **Team Foundation Administrators**.
- O CSV usa `User Story`, que existe no processo **Agile**. No **Scrum** use `Product Backlog Item`; no **CMMI** use `Requirement`. Troque o valor da coluna `Work Item Type` antes de importar. Use um editor de texto ou, no Excel, abra o arquivo por **Dados → De Texto/CSV** com origem **UTF-8**; um clique duplo simples pode quebrar os acentos e, em algumas configurações regionais, jogar tudo em uma única coluna.
- A coluna `Story Points` corresponde ao nome do campo no Agile. No Scrum o campo é `Effort`; renomeie o cabeçalho da coluna.
- O processo **Basic** tem `Epic` e `Issue`, mas não tem os campos `Story Points` nem `Acceptance Criteria`: use `Issue` como tipo e apague essas duas colunas.
- Exporte dois ou três work items existentes do seu projeto antes. O cabeçalho exportado mostra os nomes exatos dos campos do seu processo.

### Passos
1. No app, baixe o **CSV do Azure DevOps**.
2. No projeto, abra **Boards → Queries → Import work items**.
3. Selecione **Choose file**, escolha `azure_devops.csv` e depois **Import**.
4. Os itens carregam na visão de consulta **sem salvar** e sem IDs. Confira o resultado.
5. Corrija as linhas destacadas em vermelho (valor inválido) e selecione **Save items**.

### Bom saber
- Textos que começam com `=`, `+`, `-` ou `@` saem com um apóstrofo no início para que a planilha não os execute como fórmula. O apóstrofo é importado como parte do texto; remova-o à mão se incomodar.
- A hierarquia vem de `Title 1` (épico) e `Title 2` (história): cada história vira filha do épico que está acima dela.
- Até 1.000 work items por importação.
- Os itens novos nascem no estado **New**, e Area/Iteration ficam na raiz do projeto. Adicione as colunas `Area Path` e `Iteration Path` se precisar de outros valores.
- Deixe a coluna `ID` de fora. Informar um ID em item novo gera erro.

### Solução de problemas
| Sintoma | Causa provável | Correção |
|---|---|---|
| Linha em vermelho, "invalid work item type" | O processo não tem `User Story` | Use o tipo do seu processo (veja acima) |
| Erro de campo desconhecido | O nome da coluna não existe no seu processo | Renomeie para o nome exato do campo, conforme uma exportação |
| Acentos quebrados | Arquivo aberto e salvo em editor que não usa UTF-8 | Exporte de novo pelo app e mantenha UTF-8 |
| Acceptance Criteria mostra tags `<p>` | O campo é texto simples no seu processo | Remova as tags ou mude o campo para HTML |

## Jira Cloud

### Antes de começar
- A importação de CSV com vínculos de pai é feita por um **administrador do site ou da organização**. Quem não é administrador precisa das permissões "Create work items" e "Make bulk changes" e fica limitado a 250 itens por arquivo.
- O projeto de destino deve ser **gerenciado pela empresa** (company-managed) e ter os tipos `Epic` e `Story`. A importação não cria status, tipos nem campos personalizados novos; o projeto precisa já estar compatível.
- `Epic Link` e `Epic Name` estão obsoletos; este arquivo liga as histórias aos épicos com `Parent`.
- Se `Parent` não aparecer no mapeamento, habilite as subtarefas em System → Work items → Sub-Tasks.

### Passos
1. No app, baixe o **CSV do Jira**.
2. Vá em **Settings (engrenagem) → System → External system import → CSV**. Se o Jira oferecer a nova experiência, talvez seja preciso voltar para a antiga para mapear os campos.
3. Escolha `jira.csv` e selecione **Next**.
4. Selecione o projeto de destino. Mantenha os formatos de data e e-mail padrão.
5. Mapeie os campos: `Issue Id → Issue id`, `Issue Type → Issue Type`, `Summary → Summary`, `Description → Description`, `Priority → Priority`, `Parent → Parent`, `Labels → Labels`.
6. Selecione **Next** e depois **Begin import**.
7. Abra uma história e confirme que o **Parent** é o épico correto.

### Bom saber
- O importador processa as linhas de cima para baixo, então o pai precisa aparecer acima dos filhos. O arquivo exportado já respeita isso (cada linha de épico vem antes das suas histórias).
- `Parent` recebe o `Issue Id` numérico, não uma chave como `PROJ-1`.
- As prioridades precisam existir no projeto (`Highest`, `High`, `Medium` e `Low` são as padrão).

### Solução de problemas
| Sintoma | Causa provável | Correção |
|---|---|---|
| Histórias importadas sem épico | `Parent` não mapeado, ou linha do pai abaixo da do filho | Mapeie `Parent`; mantenha os épicos acima das histórias |
| "Issue type not found" | O projeto não tem o tipo `Epic` ou `Story` | Adicione o tipo ao esquema do projeto |
| Prioridade ignorada | Valor fora do esquema de prioridades do projeto | Renomeie os valores no CSV ou adicione a prioridade |
| Falha ao ligar a um épico que já existe | Limitação conhecida ao ligar a pais existentes | Importe épicos e histórias no mesmo arquivo |

## Documentação oficial
- [Azure Boards: exportar, atualizar e importar work items com CSV](https://learn.microsoft.com/en-us/azure/devops/boards/queries/import-work-items-from-csv)
- [Atlassian: manter relações pai-filho na importação de CSV no Jira Cloud](https://support.atlassian.com/jira/kb/keep-issue-parent-child-mapping-during-csv-import-to-jira-cloud/)
- [Atlassian: importar trabalho para um espaço existente via CSV](https://support.atlassian.com/jira-software-cloud/docs/import-issues-into-an-existing-space-in-jira-using-csv/)
