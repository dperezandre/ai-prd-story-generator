# Pushing stories and tasks to Azure DevOps

Instead of importing a CSV, the project can create the work items for you through the Azure DevOps REST API: one **User Story** per story and its **Tasks** as children. There are no epics or features.

> **Status.** The code is tested with simulated HTTP responses and the endpoints were checked against the official Azure DevOps documentation (REST 7.1). It has **not yet run against a live organization**. Do the first send into a sandbox project.

## 1. Create a personal access token (PAT)

In Azure DevOps: **User settings → Personal access tokens → New token**. Give it a short expiry and the scope **Work Items: Read & write**. Copy the token once; Azure does not show it again.

Never paste the token into a chat, a file or the repository.

## 2. Make the token available

PowerShell, in the same window where you will run the command:

```powershell
$env:AZDO_PAT = "<your token>"
```

The app has a password field instead; the token stays in that browser session and is never stored.

## 3. Always preview first

```bash
python -m scripts.azure_push stories.json --org <organization> --project <project>
```

Without `--yes` the command only prints what it would create, marked `[new]`, `[already sent]` or `[partly sent]`, and sends nothing. The token is not needed for the preview.

The input is either a generated result (`PipelineResult` JSON) or the `po-spec-review` skill's JSON (stories with `title`, `description`, `acceptance_criteria` and `tasks`).

## 4. Send

```bash
python -m scripts.azure_push stories.json --org <organization> --project <project> --yes
```

Options: `--area` and `--iteration` set the area and iteration paths (default: the project root); `--ledger PATH` chooses where the ledger is kept.

What happens: the project's story type is detected (User Story, Product Backlog Item, Requirement or Issue), then each story is created, then its tasks with a parent link. Optional fields (acceptance criteria, story points or effort, priority) are sent only if the project's process has them.

## What the ledger does

After every created work item the command writes a small file next to the input (`<name>.azdo-ledger.json`). If you run it again, finished stories are skipped, and a story that lost some tasks to an error only gets the missing ones. Nothing is duplicated. `--force` ignores the ledger and creates everything again.

## From the app and from the skill

- **App:** in live mode, open the **Export** tab → **Link with Azure DevOps**, fill in organization, project and token, click **Preview**, then **Send to Azure DevOps**. Hidden in demo mode.
- **Skill:** after the PDF, `po-spec-review` offers to push. It shows the preview and asks for a clear yes before sending, and never reads the token. Install it with `python -m scripts.install_skill`.

## If something fails

| Message | Likely cause |
|---|---|
| "rejected the token (it answered with a sign-in page)" | Wrong or expired token, or missing the Work Items scope |
| "Organization or project not found" | Check the names; the organization is the part after `dev.azure.com/` |
| "none of the supported story types" | The project's process has no User Story, PBI, Requirement or Issue |
| "refused the request (...)" | A project rule, for example a required field; the detail from Azure is shown |
| "rate limiting" | Wait and run again; the ledger keeps what was created |
