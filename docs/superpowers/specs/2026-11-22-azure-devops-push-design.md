# Azure DevOps push (stories and tasks) — Design

Date: 2026-11-22 · Status: draft for approval

## Intent and why

The author is a Product Owner who reviews and breaks down specifications into stories. Today the result is a PDF or a CSV that someone then imports by hand. They want a "link with Azure DevOps" that **uploads the stories and their tasks** straight into a project, with the tasks written explicitly in the first generation instead of added later.

## Goals

- Generate tasks together with the stories (a new pipeline step), so every story carries 2 to 6 explicit tasks from the first run.
- Send stories and their child tasks to Azure DevOps through its REST API, after a preview and an explicit confirmation.
- One shared sending core used by the `po-spec-review` skill first (where confidential specifications are reviewed without an external AI provider) and by a button in the Streamlit app second.
- Safe to repeat: running the same send twice never silently duplicates work items.

## Non-goals

- No epics and no features: only user stories and tasks. The epic name the generator makes today is kept only as a tag.
- Jira is untouched (its CSV and guide stay as they are).
- No updating or deleting existing work items, no two-way sync.

## Anti-goals (would make it a failure even if it works)

- Sending anything without showing a preview and getting a yes.
- The token appearing in chat, logs, files, error messages or the repository.
- Task hours or estimates the specification never gave.

## Constraints

- Authentication is a personal access token (PAT) with Work Items read and write. It is read from the `AZDO_PAT` environment variable in the CLI and typed into a password field in the app (session memory only). The skill never reads or asks for it.
- Confidential specifications: the skill path makes no call to an AI provider; only the Azure DevOps call leaves the machine.
- No live Azure DevOps is available to the builder: everything is tested with mocked HTTP (`httpx.MockTransport`, already used for the AI providers). The first real send is done by the author into a sandbox project.
- Python, `httpx` and `pydantic` stay as the stack. PyMuPDF stays optional (PDF only).

## Approaches considered

1. **REST API, shared core (chosen).** Preview plus confirmed send, idempotent, one core for skill, CLI and app. Costs: needs a token and network.
2. **Extended CSV with tasks, imported by hand.** No token, but no push button and a manual step. Kept only as a side effect: the Azure CSV also gets tasks (below).
3. **`az boards` CLI.** Needs the CLI installed and logged in; does not work in the web app.

## Design

**Data.** New `Task(title, description)`; `Story.tasks: list[Task] = []`. A new pipeline step `tasks` runs after `gherkin` and reads stories and scenarios. Prompts `prompts/<lang>/05_tasks.md` follow the existing five-heading format. Rules: 2 to 6 tasks per story, each a concrete piece of work traceable to a scenario, no hours, JSON map `{story_id: [tasks]}` like the Gherkin step; unknown story ids are ignored. The app shows tasks under each story.

**Azure client** (`src/azure_devops.py`).
- `AzureDevOpsClient(organization, project, pat, transport=None)`; errors as `AzureDevOpsError(kind)` with kinds auth, not_found, network, rate_limit, validation. The token never appears in a message.
- The story type is detected from the project's work item types, in this order: User Story, Product Backlog Item, Requirement, Issue. Optional fields (acceptance criteria, story points or effort) are sent only if the type has them (discovered from the type's field list), so Agile, Scrum, CMMI and Basic all work.
- A neutral `PushItem` list (story title, HTML description, acceptance criteria, priority from MoSCoW, points, tags, tasks) is the only input. Adapters build it from a `PipelineResult` and from the skill's JSON.
- `plan()` builds the preview without any write. `push()` creates each story, then each task with a parent link (`System.LinkTypes.Hierarchy-Reverse`), one request at a time, one retry on 429 or 5xx. On failure it stops, keeps what was created and reports it.
- Idempotency: a ledger file (JSON, outside the repository by default, next to the input) maps a hash of organization, project and story to the created ids. A repeat run skips finished stories and only creates missing tasks. `--force` ignores it.
- Optional `--area` and `--iteration` set the area and iteration paths; default is the project root.

**Entry points.**
- CLI `python -m scripts.azure_push <stories.json> --org <o> --project <p>`: preview by default; `--yes` sends.
- Skill: new optional last step after the PDF: ask organization and project, tell the author to set `AZDO_PAT` in their own terminal, show the CLI preview, ask for an explicit yes, then send.
- Streamlit: in the Export tab, an expander "Link com Azure DevOps" with organization, project, token, "Ver prévia" and "Enviar ao Azure DevOps". Hidden in demo mode.

**Skill JSON and PDF.** Each story gets `tasks` (title, description). The PDF gets a fourth block, **Tasks**, after the acceptance criteria. The story's three original blocks are unchanged. Tasks are required in the skill JSON.

**Azure CSV.** Epic rows are removed: stories at `Title 1`, tasks at `Title 2` (Task type). This also fixes a problem found while designing this: in the Agile process an Epic's children are Features, so the current Epic-to-Story CSV can be rejected. The import guides (EN and PT-BR) are updated.

**Examples and docs.** The four example JSONs get hand-written tasks and the derived files are regenerated. New `docs/azure-push.md` and `.pt-BR.md`: creating the PAT, the environment variable, the first send into a sandbox, what the ledger does. README mentions.

**Tests** (no network): type and field discovery, creation order and parent links, preview makes no write, auth and partial failure, ledger skip and `--force`, token never in errors, the tasks step and its prompts, the CSV, the PDF with tasks, the app flow with a fake client.

## Left to the builder

Exact JSON-Patch payloads and API version, checked against the official Azure DevOps docs while implementing; the wording of UI texts; the ledger file name.

## Calls made without asking

Tags carry the MoSCoW priority and the epic name; no hours on tasks; sequential requests; PDF gets the Tasks block; Azure CSV loses its Epic rows.
