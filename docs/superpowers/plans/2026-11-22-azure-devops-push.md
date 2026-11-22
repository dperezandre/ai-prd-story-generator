# Azure DevOps Push (stories and tasks) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate explicit tasks with every story and push stories plus child tasks to Azure DevOps through its REST API, after a preview and an explicit confirmation, from the `po-spec-review` skill, a CLI and the Streamlit app.

**Architecture:** A fifth pipeline step produces `Story.tasks`. One module, `src/azure_devops.py`, turns either a `PipelineResult` or the skill's JSON into neutral `PushItem`s, builds a preview, and pushes them with an idempotency ledger. The CLI, the skill and the app are thin callers of that module.

**Tech Stack:** Python 3.11+, pydantic v2, httpx (`MockTransport` in tests), Streamlit, pytest. PyMuPDF stays optional (PDF only).

**Spec:** `docs/superpowers/specs/2026-11-22-azure-devops-push-design.md`

## Global Constraints

- Only user stories and tasks. No epics, no features. The epic name survives only as a tag.
- The PAT is read from the `AZDO_PAT` environment variable (CLI) or a password field (app, session only). It never appears in chat, logs, files, error text, test output or the repository. The skill never reads or asks for it.
- Nothing is sent without a preview and an explicit confirmation (`--yes` / the send button / a yes in chat).
- Tasks carry no hours or estimates.
- No network in tests: `httpx.MockTransport` only. Existing tests keep passing (`python -m pytest`).
- No content from confidential specifications in the repository, tests or examples.
- Jira exporter, Jira guide and Jira CSV are not touched.
- Follow the surrounding code style: short docstrings, type hints, no comments that restate code. Repo files use LF; `.gitattributes` already handles CSV.
- Official Azure DevOps docs are the authority for payload shapes; verify each endpoint while implementing (REST version 7.1).

## Review Focus

Inputs and conditions the spec implies but no task's happy path exercises, most likely first:
1. A story is created but a later task fails: rerun must create only the missing tasks, never a second story.
2. A wrong or expired PAT: Azure may answer with a 203 and an HTML sign-in page instead of a 401. Must surface as an `auth` error, not a JSON parse crash.
3. The project's process lacks Acceptance Criteria or Story Points/Effort (Basic): those fields are omitted, no 400.
4. Two stories with the same title in one run, or the same story re-sent from a re-generated file: the ledger key must not collide or double-send.
5. HTML or markup characters in story text reach Azure escaped.
6. The token must never be part of any exception message, including ones built from the server's response body.
7. A story with zero tasks (the model returned none): story still pushes, preview warns.
8. Organization given as a bare name, as `dev.azure.com/org` or as a full URL.

---

### Task 1: Task model and `Story.tasks`

**Files:**
- Modify: `src/models.py`
- Test: `tests/test_models.py`

**Interfaces:**
- Produces: `Task(title: str, description: str = "")`; `Story.tasks: list[Task] = []`.

- [ ] **Step 1: Write the failing tests** in `tests/test_models.py`: `test_story_tasks_default_empty_and_roundtrip` (default `[]`; a story with `[Task(title="t", description="d")]` survives `model_validate_json(model_dump_json())`) and `test_pipeline_result_with_tasks_roundtrips`.
- [ ] **Step 2: Run** `python -m pytest tests/test_models.py -q`. Expected: FAIL (`Task` not importable).
- [ ] **Step 3: Implement** `Task` and the `tasks` field on `Story` in `src/models.py`.
- [ ] **Step 4: Run** the same command. Expected: PASS, and the full suite still green.
- [ ] **Step 5: Commit** `feat: Task model and Story.tasks`.

### Task 2: Tasks pipeline step and prompts

**Files:**
- Create: `prompts/en/05_tasks.md`, `prompts/pt-BR/05_tasks.md`
- Modify: `src/pipeline.py`, `app.py` (step labels only), `tests/test_prompts.py`, `tests/test_pipeline.py`, `tests/test_app.py` if a step count is asserted

**Interfaces:**
- Consumes: `Task`, `Story.tasks` (Task 1); `_context(result)` and `_call_json` already in `src/pipeline.py`.
- Produces: `STEPS = ("prd", "stories", "invest", "gherkin", "tasks")`; the prompt output is `{"tasks": {"S1": [{"title": "...", "description": "..."}]}}`; `app.TEXT[lang]["steps"]["tasks"]`.

- [ ] **Step 1: Write the failing tests.** In `tests/test_prompts.py` add `"05_tasks.md"` to `FILES` and `OUTPUT_KEYS["05_tasks.md"] = ["tasks", "title", "description"]`. In `tests/test_pipeline.py`: extend `good_responses()` with a fifth JSON reply; assert `seen == ["prd", "stories", "invest", "gherkin", "tasks"]`; `test_tasks_attach_to_matching_story` (story S1 gets its tasks); `test_tasks_for_unknown_story_id_are_ignored`; `test_story_without_tasks_in_reply_gets_empty_list`; `test_tasks_step_failure_keeps_earlier_results` (a `ProviderError` on the fifth call raises `PipelineError` with `step == "tasks"` and the stories and scenarios still in `partial`).
- [ ] **Step 2: Run** `python -m pytest tests/test_prompts.py tests/test_pipeline.py -q`. Expected: FAIL.
- [ ] **Step 3: Write the two prompts** in the existing five-heading format (EN: Persona, Task, Rules, Output format, Examples; PT-BR: Persona, Tarefa, Regras, Formato de saída, Exemplos). Rules to include: 2 to 6 tasks per story; each is one concrete piece of work (build, test, configure, document) traceable to a scenario of the story; verbs in the imperative; no hours, no estimates; no people or dates; do not repeat the acceptance criteria as tasks; output only the JSON object. Add one good and one bad task example.
- [ ] **Step 4: Implement** `do_tasks` in `run_pipeline` (new private `_TaskMap` model like `_ScenarioMap`), register `"tasks"` in `STEPS` and `_PROMPT_FILES`, add the label to both language blocks in `app.py` (EN "Writing the tasks", PT-BR "Escrevendo as tasks").
- [ ] **Step 5: Run** `python -m pytest -q`. Expected: all pass.
- [ ] **Step 6: Commit** `feat: tasks pipeline step with prompts`.

### Task 3: Exporters with tasks, Azure CSV without epics

**Files:**
- Modify: `src/exporters.py`, `tests/test_exporters.py`

**Interfaces:**
- Consumes: `Story.tasks`.
- Produces: `azure_devops_csv` rows are `User Story` rows with the story title in `Title 1`, each followed by its `Task` rows with the task title in `Title 2`; no Epic rows; `Tags` is `MoSCoW-<Priority>; <epic>`. `prd_markdown` lists a `**Tasks**` bullet list (`**Tarefas**` in PT-BR) after the criteria when a story has tasks. `jira_csv` unchanged.

- [ ] **Step 1: Rewrite the failing tests.** Replace `test_azure_epic_and_story_rows_use_title_levels` with `test_azure_rows_are_stories_at_title_1_and_tasks_at_title_2` and add `test_azure_has_no_epic_rows`, `test_azure_tags_carry_moscow_and_epic`, `test_azure_task_description_is_escaped_html`, `test_prd_markdown_lists_tasks_localized`. Fix the row indexes in the existing Azure tests (stories now start at row 1). Keep header, escaping and formula-injection tests.
- [ ] **Step 2: Run** `python -m pytest tests/test_exporters.py -q`. Expected: FAIL.
- [ ] **Step 3: Implement** the exporter changes. Keep the AZURE column list as is.
- [ ] **Step 4: Run** the same command. Expected: PASS. (`tests/test_demo.py` will fail until Task 4 regenerates the example CSVs; that is expected.)
- [ ] **Step 5: Commit** `feat: exporters list tasks, Azure CSV drops epics`.

### Task 4: Examples with tasks

**Files:**
- Modify: `examples/*.json` (4 files), regenerated `examples/*.prd.md`, `*.azure.csv`, `*.jira.csv`

**Interfaces:**
- Consumes: Tasks 1 and 3; `scripts.generate_examples.write_example_files`.

- [ ] **Step 1:** Add 2 to 4 hand-written tasks to every story of the four example JSONs (referral and abandoned cart, EN and PT-BR), in the same patch-script style used to add `rule_refs`, then call `write_example_files` to regenerate the derived files. Keep tasks free of hours.
- [ ] **Step 2: Run** `python -m pytest -q`. Expected: all pass, including `tests/test_demo.py` (derived files equal the exporters' output; CSVs keep CRLF through `.gitattributes`).
- [ ] **Step 3: Commit** `docs: example tasks and regenerated exports`.

### Task 5: Azure DevOps core, part 1: items, adapters and preview

**Files:**
- Create: `src/azure_devops.py`, `tests/test_azure_devops.py`

**Interfaces:**
- Consumes: `PipelineResult`, `Story`, `Task`.
- Produces:
  - `PushTask(title: str, description: str)` and `PushItem(key: str, title: str, description_html: str, acceptance_html: str, priority: int | None, points: int | None, tags: list[str], tasks: list[PushTask])`, frozen dataclasses.
  - `items_from_result(result: PipelineResult) -> list[PushItem]` (priority 1 to 4 from MoSCoW as in the CSV, tags `MoSCoW-X` plus the epic, acceptance criteria as HTML paragraphs of the Gherkin blocks).
  - `items_from_stories_json(data: dict) -> list[PushItem]` for the skill JSON (`stories[].title`, `description`, `acceptance_criteria` list, `tasks` list of `{title, description}`; priority, points and tags absent).
  - `normalize_organization(value: str) -> str` (accepts a bare name, `dev.azure.com/org` or a full URL).
  - `plan(items: list[PushItem], ledger: "Ledger") -> list[PlanLine]` where `PlanLine(story_title: str, task_titles: list[str], status: Literal["new", "sent", "partial"], warning: str | None)`.
  - `Ledger` class: `Ledger.load(path: Path) -> Ledger`, `.save()`, `.get(key) -> dict | None`, `.record(key, story_id, task_ids)`; `item_key(organization, project, item)` stable hash over organization, project, title and description.

- [ ] **Step 1: Write the failing tests:** `test_items_from_result_maps_priority_tags_and_escaped_html`; `test_items_from_stories_json_keeps_tasks_and_omits_priority`; `test_item_key_is_stable_and_differs_for_same_title_different_text`; `test_normalize_organization_accepts_name_domain_and_url`; `test_plan_marks_new_sent_and_partial`; `test_plan_warns_story_without_tasks`; `test_plan_makes_no_http_call` (no client involved); `test_ledger_roundtrip_and_missing_file_is_empty`.
- [ ] **Step 2: Run** `python -m pytest tests/test_azure_devops.py -q`. Expected: FAIL.
- [ ] **Step 3: Implement** the module parts above. HTML-escape every text field (reuse the escaping approach of `_html_paragraph` in `src/exporters.py`, extracted to a shared helper if that avoids duplication).
- [ ] **Step 4: Run** the same command. Expected: PASS.
- [ ] **Step 5: Commit** `feat: Azure DevOps push items, preview plan and ledger`.

### Task 6: Azure DevOps core, part 2: HTTP client

**Files:**
- Modify: `src/azure_devops.py`, `tests/test_azure_devops.py`

**Interfaces:**
- Consumes: `PushItem`, `PushTask`.
- Produces:
  - `AzureDevOpsError(message: str, kind: Literal["auth", "not_found", "network", "rate_limit", "validation"])`; messages never contain the PAT.
  - `AzureDevOpsClient(organization: str, project: str, pat: str, transport: httpx.BaseTransport | None = None, area: str | None = None, iteration: str | None = None)`.
  - `.story_type() -> str` (first present of `User Story`, `Product Backlog Item`, `Requirement`, `Issue` among the project's work item types; error `validation` if none).
  - `.available_fields(work_item_type: str) -> set[str]` (reference names).
  - `.create_story(item: PushItem, story_type: str, available: set[str]) -> int`.
  - `.create_task(task: PushTask, parent_id: int, available: set[str]) -> int` (parent link `System.LinkTypes.Hierarchy-Reverse` to the story's work item URL).
  - Fields: `System.Title`, `System.Description`, plus `Microsoft.VSTS.Common.AcceptanceCriteria`, `Microsoft.VSTS.Common.Priority`, `Microsoft.VSTS.Scheduling.StoryPoints` or `Microsoft.VSTS.Scheduling.Effort`, `System.Tags` (joined with `; `) only when present in `available` and the item has a value; `System.AreaPath` and `System.IterationPath` when given. Basic auth with an empty user name and the PAT; one retry on 429 or 5xx honoring `Retry-After`.

- [ ] **Step 1: Write the failing tests** with `httpx.MockTransport`: `test_story_type_prefers_user_story_then_pbi`; `test_story_type_without_known_type_is_validation_error`; `test_create_story_sends_only_available_fields` (Basic-like set omits criteria and points); `test_create_story_uses_effort_when_no_story_points`; `test_create_task_links_parent_with_hierarchy_reverse`; `test_auth_header_is_basic_with_empty_user`; `test_203_html_response_is_auth_error`; `test_401_is_auth_and_404_is_not_found`; `test_429_retries_once_then_raises_rate_limit`; `test_network_error_is_network_kind`; `test_error_messages_never_contain_the_pat` (server body echoes the token; message must not).
- [ ] **Step 2: Run** `python -m pytest tests/test_azure_devops.py -q`. Expected: FAIL.
- [ ] **Step 3: Implement** the client. Verify the endpoint paths, `application/json-patch+json` content type and REST version against the official docs and note any difference from the Interfaces text in the commit message.
- [ ] **Step 4: Run** the same command. Expected: PASS.
- [ ] **Step 5: Commit** `feat: Azure DevOps REST client`.

### Task 7: Azure DevOps core, part 3: confirmed, idempotent push

**Files:**
- Modify: `src/azure_devops.py`, `tests/test_azure_devops.py`

**Interfaces:**
- Consumes: `AzureDevOpsClient`, `Ledger`, `PushItem`, `plan`.
- Produces: `push(client: AzureDevOpsClient, items: list[PushItem], ledger: Ledger, confirmed: bool, force: bool = False) -> PushReport`; `PushReport(created_stories: int, created_tasks: int, skipped: int, urls: list[str], error: AzureDevOpsError | None)`. With `confirmed=False` it raises `ValueError` before any request.

- [ ] **Step 1: Write the failing tests:** `test_push_requires_confirmation_and_makes_no_request`; `test_push_creates_story_then_its_tasks_in_order` (request order and parent ids); `test_push_records_ledger_after_each_item` (saved even if a later item fails); `test_rerun_skips_finished_stories`; `test_rerun_after_partial_failure_creates_only_missing_tasks_and_no_second_story`; `test_force_ignores_ledger`; `test_failure_stops_and_reports_what_was_created`; `test_story_without_tasks_still_pushes`; `test_two_stories_same_title_get_distinct_ledger_keys`.
- [ ] **Step 2: Run** `python -m pytest tests/test_azure_devops.py -q`. Expected: FAIL.
- [ ] **Step 3: Implement** `push` and `PushReport`: detect story type and fields once, then iterate items sequentially, skipping finished ones, creating only missing tasks for partial ones, saving the ledger after every created work item, stopping on the first `AzureDevOpsError` and returning it in the report.
- [ ] **Step 4: Run** the same command and then `python -m pytest -q`. Expected: all pass.
- [ ] **Step 5: Commit** `feat: confirmed idempotent push to Azure DevOps`.

### Task 8: CLI

**Files:**
- Create: `scripts/azure_push.py`, `tests/test_azure_push_cli.py`

**Interfaces:**
- Consumes: Tasks 5 to 7.
- Produces: `main(argv: list[str] | None = None, transport: httpx.BaseTransport | None = None, environ: Mapping[str, str] | None = None) -> int`. Arguments: input JSON path, `--org`, `--project`, `--area`, `--iteration`, `--ledger PATH` (default: next to the input, `<input stem>.azdo-ledger.json`), `--yes`, `--force`. Input detection: a JSON with an `idea` key is a `PipelineResult`; otherwise the skill JSON. Exit codes: 0 success or preview, 2 missing token or bad input, 3 Azure error.

- [ ] **Step 1: Write the failing tests** (inject `transport` and `environ`): `test_preview_by_default_prints_plan_and_sends_nothing`; `test_yes_pushes_and_prints_urls`; `test_missing_pat_exits_2_without_printing_it`; `test_accepts_pipeline_result_and_skill_json`; `test_azure_error_exits_3_and_message_has_no_token`; `test_ledger_path_defaults_next_to_input`.
- [ ] **Step 2: Run** `python -m pytest tests/test_azure_push_cli.py -q`. Expected: FAIL.
- [ ] **Step 3: Implement** the CLI with argparse; print the preview as story and indented task lines with the status and any warning; read the token only from the environment.
- [ ] **Step 4: Run** the same command. Expected: PASS.
- [ ] **Step 5: Commit** `feat: azure_push CLI`.

### Task 9: Skill JSON, PDF Tasks block and skill step

**Files:**
- Modify: `skills/po-spec-review/scripts/stories_pdf.py`, `skills/po-spec-review/SKILL.md`, `scripts/install_skill.py`, `tests/test_stories_pdf.py`, `tests/test_install_skill.py`

**Interfaces:**
- Consumes: `scripts/azure_push.py` (Task 8).
- Produces: skill JSON stories now require `tasks` (non-empty list of `{title, description}`); the PDF shows a fourth block, **Tasks**, after the criteria; `install()` also writes `repo-path.txt` (the repository root) into the installed skill folder.

- [ ] **Step 1: Write the failing tests:** `test_pdf_has_tasks_block_for_each_story` (text contains `Tasks` once per story and each task title); `test_story_without_tasks_is_rejected` (`ValueError` naming `tasks`); `test_install_writes_repo_path` (file content equals the repository root).
- [ ] **Step 2: Run** `python -m pytest tests/test_stories_pdf.py tests/test_install_skill.py -q`. Expected: FAIL.
- [ ] **Step 3: Implement** the validator and HTML changes in `stories_pdf.py` (use a neutral fixture, never real specification text) and the installer change.
- [ ] **Step 4: Update `SKILL.md`:** in the JSON description add `tasks`; in the rules for acceptance criteria add that each story gets 2 to 6 tasks (title and description, no hours, drawn only from what the text supports, blocked stories get `[A DEFINIR]` tasks only for the open points); keep the JSON until the push decision. Add a last optional step, "Subir para o Azure DevOps": ask organization and project; tell the user to set `AZDO_PAT` in their own terminal and never paste it; read the repository path from `repo-path.txt`; run `python "<repo>/scripts/azure_push.py" "<json>" --org ... --project ...` and show the preview; ask for an explicit yes; run again with `--yes`; delete the JSON afterwards and leave the ledger next to the PDF.
- [ ] **Step 5: Run** `python -m pytest -q`, then `python -m scripts.install_skill`. Expected: tests pass; skill reinstalled.
- [ ] **Step 6: Commit** `feat: PDF Tasks block and Azure push step in the skill`.

### Task 10: Streamlit "Link com Azure DevOps"

**Files:**
- Modify: `app.py`, `tests/test_app.py`

**Interfaces:**
- Consumes: `items_from_result`, `plan`, `push`, `Ledger`, `AzureDevOpsClient`, `AzureDevOpsError`; the app calls them as `azure_devops.<name>` so tests can monkeypatch `src.azure_devops.AzureDevOpsClient`.
- Produces: in the Export tab, when not in demo mode and a result exists, an expander with text inputs keyed `azdo_org`, `azdo_project`, a password input `azdo_pat`, buttons `azdo_preview` and `azdo_send`. Preview renders the plan; send is enabled only after a preview of the current result and calls `push(..., confirmed=True)`; success shows counts and links; errors show the message. The ledger lives in the session (an in-memory `Ledger`) because the app has no output folder.

- [ ] **Step 1: Write the failing tests** (AppTest, monkeypatch the client with a fake recording calls): `test_azure_section_hidden_in_demo_mode`; `test_preview_makes_no_request`; `test_send_button_disabled_until_preview`; `test_send_pushes_stories_and_tasks_and_shows_links`; `test_azure_error_is_shown_and_pat_not_displayed`.
- [ ] **Step 2: Run** `python -m pytest tests/test_app.py -q`. Expected: FAIL.
- [ ] **Step 3: Implement** a `render_azure_push(result, t, key)` function and texts in both language blocks (labels: EN "Link with Azure DevOps", PT-BR "Link com Azure DevOps"); keep `app.py` UI-only.
- [ ] **Step 4: Run** `python -m pytest -q`. Expected: all pass.
- [ ] **Step 5: Commit** `feat: Azure DevOps push section in the app`.

### Task 11: Docs and final check

**Files:**
- Create: `docs/azure-push.md`, `docs/azure-push.pt-BR.md`
- Modify: `docs/import-guide.md`, `docs/import-guide.pt-BR.md`, `README.md`, `README.pt-BR.md`, `docs/spec-standard.md`, `docs/spec-standard.pt-BR.md`

- [ ] **Step 1:** Write the two push guides: creating a PAT with the Work Items read and write scope, setting `AZDO_PAT` (PowerShell example), first send into a sandbox project, the preview and `--yes`, what the ledger file does and `--force`, the skill flow, the app flow, and the honest note that it has not yet run against a live organization.
- [ ] **Step 2:** Update the import guides: the Azure CSV now has stories at `Title 1` and tasks at `Title 2` with no epic rows, and why (Agile's Epic children are Features). Add short README sections in both languages and one line in the spec standard (tasks are part of the story).
- [ ] **Step 3: Run** `python -m pytest -q` and a confidentiality scan: `grep -rniE "hapvida|opme|protomaker|siga|lecom|gnhap|peso no simulador" --exclude-dir=.git .` must find nothing outside this plan and spec files' neutral wording.
- [ ] **Step 4: Commit** `docs: Azure push guides and updated import guides`.
