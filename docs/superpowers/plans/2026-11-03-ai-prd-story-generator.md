# AI PRD & User Story Generator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a bilingual (PT-BR/EN) Streamlit app and prompt library that turns a feature idea into a PRD, INVEST-reviewed user stories with Gherkin criteria, and import-ready CSVs for Azure DevOps and Jira, packaged as a PO portfolio repo.

**Architecture:** A 4-step pipeline (PRD → stories → INVEST review → Gherkin) calls a pluggable LLM provider (`complete(system, user) -> str`) with prompts loaded from `prompts/<lang>/*.md`; responses are JSON validated by pydantic models. Exporters and the Streamlit UI consume only the models. Demo mode replays pre-generated `examples/` with no network.

**Tech Stack:** Python 3.11+, streamlit, pydantic v2, httpx, pytest, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-11-03-ai-prd-story-generator-design.md`

## Global Constraints

- Languages: `"pt-BR"` and `"en"` only; the prompt folder name equals the language code.
- Prompt files, per language: `01_prd.md`, `02_stories.md`, `03_invest_review.md`, `04_gherkin.md`.
- LLM output is JSON validated by `src/models.py`; invalid JSON gets exactly 1 retry with the validation error appended, then a clear error.
- API key lives only in `st.session_state`; never written to disk, logs, or error messages.
- Providers: Gemini, Groq (free tiers), Claude, OpenAI; BYOK; plus demo mode with no key and no network.
- Priority is MoSCoW: `Must | Should | Could | Won't`. INVEST score per criterion is an int 0–2.
- Azure DevOps CSV columns: `Work Item Type, Title 1, Title 2, Description, Acceptance Criteria, Priority, Story Points, Tags`; epic uses `Title 1`, story uses `Title 2`.
- Jira CSV: `Issue Type, Summary, Description, Priority, Parent/Epic link, Labels`; acceptance criteria inside the description (exact columns confirmed in Task 6 against official docs).
- CSV is UTF-8 and correctly escapes accents, commas, quotes and line breaks.
- Gherkin keywords: EN `Given/When/Then/And`; PT-BR `Dado/Quando/Então/E`.
- Anything not derived from the idea is labelled an assumption; no invented metrics.
- Costs the author nothing: tests need no network; free-tier limits are described as "verify current limits".
- Use `python -m pytest` (Windows). Commit after each task.

## Review Focus

1. LLM wraps JSON in ```` ```json ```` fences or adds prose around it → parsed successfully.
2. Empty/whitespace-only idea, or one longer than 4000 characters → clear `ValueError`, no provider call.
3. Provider returns HTTP 429/401 mid-pipeline → `PipelineError` that carries the steps already completed; message never contains the API key.
4. Story fields with commas, quotes, newlines, accents, or a leading `=`, `+`, `-`, `@` → CSV opens correctly in Excel/Azure/Jira without formula injection.
5. Reviewer or Gherkin response omits a story or references an unknown `story_id` → that story is kept as-is (unreviewed / no scenarios) and the pipeline does not crash.

---

### Task 1: Project scaffold and CI

**Files:**
- Create: `requirements.txt`, `.gitignore`, `.env.example`, `LICENSE` (MIT, holder "dperezandre"), `pytest.ini`, `.github/workflows/tests.yml`, `src/__init__.py`, `tests/__init__.py`, `tests/test_smoke.py`

**Interfaces:**
- Produces: importable package `src`; `python -m pytest` runs from repo root.

- [ ] **Step 1: Write failing test** `tests/test_smoke.py::test_src_importable` asserting `import src` works.
- [ ] **Step 2: Run** `python -m pytest -q` → FAIL (no module `src`).
- [ ] **Step 3: Create the files.** `requirements.txt`: `streamlit`, `pydantic>=2`, `httpx`, `pytest`. `pytest.ini`: `pythonpath = .`, `testpaths = tests`. `.gitignore`: Python, venv, `.env`. `.env.example`: only variable names `GEMINI_API_KEY`, `GROQ_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY` with empty values and a comment that the app takes the key in the UI. Workflow: on push/PR, Python 3.11, `pip install -r requirements.txt`, `python -m pytest`.
- [ ] **Step 4: Install and run** `pip install -r requirements.txt` then `python -m pytest -q` → PASS.
- [ ] **Step 5: Commit** `chore: project scaffold and CI`.

### Task 2: Models and Markdown/Gherkin rendering

**Files:**
- Create: `src/models.py`
- Test: `tests/test_models.py`

**Interfaces:**
- Produces (all pydantic `BaseModel` unless noted):
  - `Language = Literal["pt-BR","en"]`; `Priority = Literal["Must","Should","Could","Won't"]`
  - `PRD`: `title, problem: str`; `personas, goals, success_metrics, scope_in, scope_out, requirements, risks, assumptions, open_questions: list[str]`; `to_markdown(language: Language) -> str` (section headings localized, one `##` per field, empty lists omitted).
  - `Scenario`: `name: str; given, when, then: list[str]`; `to_gherkin(language: Language) -> str` (first step uses Given/When/Then, further steps `And`/`E`; PT-BR output starts with `# language: pt`, uses `Cenário:`).
  - `Story`: `id, epic, title, as_a, i_want, so_that: str; priority: Priority; points: int; prd_ref: str; scenarios: list[Scenario] = []`; `to_text(language) -> str` ("As a … I want … so that …" / "Como … quero … para …").
  - `InvestScores`: `independent, negotiable, valuable, estimable, small, testable: int` each `ge=0, le=2`; property `total -> int`.
  - `Review`: `story_id: str; scores: InvestScores; verdict: Literal["pass","rewrite"]; comment: str; rewrite: Story | None = None; scores_after: InvestScores | None = None`.
  - `PipelineResult`: `idea: str; language: Language; prd: PRD | None = None; stories: list[Story] = []; reviews: list[Review] = []`.

- [ ] **Step 1: Write failing tests:** `test_scores_reject_out_of_range` (score 3 raises `ValidationError`); `test_gherkin_en` (`Given a\nWhen b\nThen c\nAnd d` form with `Scenario: x`); `test_gherkin_pt` (contains `# language: pt`, `Cenário: x`, `Dado`, `Quando`, `Então`, `E d`); `test_prd_markdown_omits_empty_lists_and_localizes_headings`; `test_result_roundtrips_json` (`PipelineResult.model_validate_json(r.model_dump_json()) == r`).
- [ ] **Step 2: Run** `python -m pytest tests/test_models.py -v` → FAIL.
- [ ] **Step 3: Implement** the models above in `src/models.py`; heading translations in a module-level dict keyed by language.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat: pipeline data models`.

### Task 3: Provider layer

**Files:**
- Create: `src/providers.py`
- Test: `tests/test_providers.py`, `tests/conftest.py` (adds `FakeProvider`)

**Interfaces:**
- Produces:
  - `class LLMProvider(Protocol): def complete(self, system: str, user: str) -> str`
  - `class ProviderError(Exception)` with attribute `kind: Literal["auth","rate_limit","network","other"]`; message is human-readable and never contains the API key.
  - `PROVIDERS: dict[str, str]` mapping provider name (`"gemini"`, `"groq"`, `"claude"`, `"openai"`) to its default model id (use current model ids; confirm in each provider's docs at implementation time).
  - `get_provider(name: str, api_key: str, model: str | None = None, transport: httpx.BaseTransport | None = None) -> LLMProvider` (raises `ValueError` for unknown name or empty key).
  - `tests/conftest.py::FakeProvider(responses: list[str | Exception])`: `complete` pops the next item (raises it if an Exception) and records calls in `.calls: list[tuple[str, str]]`.
- Implementation: one class for OpenAI-compatible chat completions (OpenAI and Groq, differing in base URL), one for Gemini `generateContent`, one for Anthropic Messages; all via `httpx` so tests use `httpx.MockTransport`.

- [ ] **Step 1: Write failing tests** using `httpx.MockTransport`: for each provider, a 200 response yields the extracted text; 401 → `ProviderError(kind="auth")`; 429 → `kind="rate_limit"`; connection error → `kind="network"`; the key string never appears in `str(error)`; `get_provider("nope","k")` and `get_provider("groq","")` raise `ValueError`.
- [ ] **Step 2: Run** `python -m pytest tests/test_providers.py -v` → FAIL.
- [ ] **Step 3: Implement** `src/providers.py` and `FakeProvider` in `tests/conftest.py`.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat: pluggable LLM providers`.

### Task 4: Prompt library (8 files)

**Files:**
- Create: `prompts/en/{01_prd,02_stories,03_invest_review,04_gherkin}.md` and `prompts/pt-BR/` (same names)
- Test: `tests/test_prompts.py`

**Interfaces:**
- Consumes: JSON field names from Task 2 models (each prompt's output-format section must list them exactly).
- Produces: system prompts used by Task 5.

Required headings (exact), EN: `# Persona`, `# Task`, `# Rules`, `# Output format`, `# Examples`. PT-BR: `# Persona`, `# Tarefa`, `# Regras`, `# Formato de saída`, `# Exemplos`. Content requirements from the spec §5:
- 01 PRD: senior PM persona; output = `PRD` JSON; rule: anything not from the idea goes into `assumptions` or `open_questions`; never invent numbers.
- 02 Stories: input is the PRD JSON; output = `{"stories": [Story without scenarios]}`; ids `S1…`, `prd_ref` names the PRD section/requirement; estimates in points.
- 03 Review: critical, adversarial PO persona; objective INVEST rubric with a test per criterion (Small: more than 8 points scores 0); output = `{"reviews": [Review]}`; `rewrite` and `scores_after` required when verdict is `rewrite`; few-shot with one good and one bad story.
- 04 Gherkin: output = `{"scenarios": {"<story_id>": [Scenario]}}`; 2–4 scenarios per story (happy, alternative, error); one behaviour per scenario; business language, no UI detail; scenario name states the rule.

- [ ] **Step 1: Write failing tests:** parametrized over language × file: file exists, contains every required heading for its language, and (for the output format section) mentions the JSON key names it must produce (`stories`, `reviews`, `scenarios`, `problem`).
- [ ] **Step 2: Run** `python -m pytest tests/test_prompts.py -v` → FAIL.
- [ ] **Step 3: Write the 8 prompts.** These are the portfolio's core: write them carefully in each language (not machine-literal), each with the few-shot example the spec requires.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat: bilingual prompt library`.

### Task 5: Pipeline

**Files:**
- Create: `src/pipeline.py`
- Test: `tests/test_pipeline.py`

**Interfaces:**
- Consumes: `LLMProvider`, `ProviderError` (Task 3); models (Task 2); prompt files (Task 4).
- Produces:
  - `MAX_IDEA_CHARS = 4000`
  - `STEPS = ("prd","stories","invest","gherkin")`
  - `parse_json_response(text: str) -> Any` (accepts ```` ``` ```` fences and prose around a single JSON object)
  - `class PipelineError(Exception)`: `step: str; partial: PipelineResult`
  - `run_pipeline(idea: str, language: Language, provider: LLMProvider, on_step: Callable[[str, PipelineResult], None] | None = None, prompts_dir: Path = Path("prompts")) -> PipelineResult`. `on_step` is called after each completed step with the result so far.
- Behaviour: step 2 receives the PRD JSON, not the raw idea; after step 3 any `rewrite` replaces the story in `stories` (same `id`) while the `Review` keeps both scores; step 4 attaches scenarios by `story_id`.

- [ ] **Step 1: Write failing tests** using `FakeProvider` with canned JSON: `test_happy_path_runs_four_steps_in_order`; `test_stories_step_receives_prd_not_idea`; `test_rewrite_replaces_story_and_keeps_scores`; `test_invalid_json_retries_once_with_error_appended` (second call's user text contains the error); `test_second_invalid_json_raises_pipeline_error`; `test_fenced_json_is_parsed`; `test_empty_or_whitespace_idea_raises_value_error_without_calling_provider`; `test_idea_over_max_raises_value_error`; `test_provider_error_midway_keeps_completed_steps` (`PipelineError.partial.prd` set, `.step == "stories"`, message has no key); `test_unknown_story_id_in_review_or_gherkin_is_ignored_and_missing_story_kept`; `test_on_step_called_after_each_step`.
- [ ] **Step 2: Run** `python -m pytest tests/test_pipeline.py -v` → FAIL.
- [ ] **Step 3: Implement** `src/pipeline.py`. Retry helper: parse + validate; on failure call again with the original user text plus the error text; second failure raises `PipelineError`.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** `feat: four-step generation pipeline`.

### Task 6: Exporters (CSV for Azure DevOps and Jira, Markdown)

**Files:**
- Create: `src/exporters.py`
- Test: `tests/test_exporters.py`

**Interfaces:**
- Consumes: `PipelineResult`, `Story` (Task 2).
- Produces:
  - `prd_markdown(result: PipelineResult) -> str` (PRD markdown plus stories with Gherkin)
  - `azure_devops_csv(result: PipelineResult) -> str`
  - `jira_csv(result: PipelineResult) -> str`
  - Priority maps: Azure `Must→1, Should→2, Could→3, Won't→4`; Jira `Must→Highest, Should→High, Could→Medium, Won't→Low`.
  - Layout: one Epic row per distinct `Story.epic`, followed by its stories. Azure: epic title in `Title 1`, story title in `Title 2`, `Work Item Type` = `Epic`/`User Story`. Jira: `Issue Type` = `Epic`/`Story`; stories point to their epic via the parent column.

- [ ] **Step 1: Verify formats against official docs.** Use WebFetch/WebSearch on Microsoft Learn ("Import work items from a CSV file", Azure Boards) and Atlassian ("Import data from CSV", Jira Cloud, including epic/parent linkage for company-managed and team-managed projects). If a column name or linkage mechanism differs from Global Constraints, update the Global Constraints line and this task before writing tests, and note the change in the spec.
- [ ] **Step 2: Write failing tests:** Azure header row equals the exact column list; epic rows have `Title 1` set and `Title 2` empty, story rows the reverse; commas, quotes, newlines and accents round-trip through `csv.reader`; cells beginning with `=`, `+`, `-`, `@` are prefixed with `'`; acceptance criteria appear in Azure `Acceptance Criteria` and inside the Jira `Description`; stories with the same `epic` share one epic row; result with no stories yields header-only CSV.
- [ ] **Step 3: Run** `python -m pytest tests/test_exporters.py -v` → FAIL.
- [ ] **Step 4: Implement** `src/exporters.py` with the stdlib `csv` module (returns `str`, UTF-8 safe; the UI adds a BOM only if Step 1 shows Excel needs it).
- [ ] **Step 5: Run** → PASS. **Step 6: Commit** `feat: Azure DevOps, Jira and Markdown exporters`.

### Task 7: Examples and demo mode

**Files:**
- Create: `scripts/generate_examples.py`, `src/demo.py`, `examples/` (generated), `tests/test_demo.py`
- Test: `tests/test_demo.py`

**Interfaces:**
- Consumes: `run_pipeline`, `get_provider`, exporters.
- Produces:
  - `DEMO_CASES: dict[str, dict[Language, str]]` with keys `"referral"` and `"abandoned_cart"`, values = the example idea text per language (also used for the UI's clickable examples).
  - `load_demo(case_id: str, language: Language, examples_dir: Path = Path("examples")) -> PipelineResult` reading `examples/<case_id>.<language>.json`.
  - `scripts/generate_examples.py --provider NAME --key-env VAR`: runs the pipeline for both cases and languages, writes `examples/<case>.<lang>.json`, `.prd.md`, `.azure.csv`, `.jira.csv`.

- [ ] **Step 1: Write failing tests:** `test_load_demo_returns_complete_result` for each case × language (prd set, ≥3 stories, every story has scenarios, ≥1 review with a rewrite); `test_load_demo_unknown_case_raises_key_error`; `test_demo_csvs_open_with_csv_reader`.
- [ ] **Step 2: Run** → FAIL (no examples yet).
- [ ] **Step 3: Implement** `src/demo.py` and `scripts/generate_examples.py`.
- [ ] **Step 4: Generate examples.** Ask the author for a provider key (or use a free-tier one), run the script, then **ask the author to review and edit the four JSON files** so they read as human-curated. Do not commit unreviewed outputs.
- [ ] **Step 5: Run** `python -m pytest tests/test_demo.py -v` → PASS. **Step 6: Commit** `feat: demo mode and reviewed examples`.

### Task 8: Streamlit app

**Files:**
- Create: `app.py`
- Test: `tests/test_app.py`

**Interfaces:**
- Consumes: `PROVIDERS`, `get_provider`, `run_pipeline`, `PipelineError`, `load_demo`, `DEMO_CASES`, exporters.
- Layout per spec §8: sidebar (language, provider, API key as password input, model, demo toggle that disables provider/key); main area (idea text area, two clickable example buttons from `DEMO_CASES`, **Generate**); tabs `PRD`, `Stories` (INVEST scores before/after), `Gherkin`, `Export` (three `st.download_button`s plus link to `docs/import-guide`); `st.status` progress per step; privacy notice that the idea goes to the chosen provider. Key kept only in `st.session_state`; errors shown via `st.error` with the partial results still rendered.

- [ ] **Step 1: Write failing test** with `streamlit.testing.v1.AppTest.from_file("app.py")`: demo mode on, click Generate → no exception, four tabs rendered, three download buttons present, and with demo off and empty key a clear error is shown instead of a crash.
- [ ] **Step 2: Run** `python -m pytest tests/test_app.py -v` → FAIL.
- [ ] **Step 3: Implement** `app.py` (UI only; no provider or CSV logic).
- [ ] **Step 4: Run** → PASS; then run `streamlit run app.py` and check the page in the browser pane in both languages (demo mode).
- [ ] **Step 5: Commit** `feat: Streamlit UI`.

### Task 9: Documentation and portfolio packaging

**Files:**
- Create: `README.md` (EN), `README.pt-BR.md`, `docs/import-guide.md`, `docs/import-guide.pt-BR.md`, `docs/prompt-design.md`, `docs/demo.gif` (or screenshots)

**Interfaces:**
- Consumes: generated example CSVs (Task 7) and confirmed formats (Task 6).

- [ ] **Step 1: Write import guides (EN + PT-BR)** following spec §9: Azure DevOps (prerequisites, Boards → Work items → Import Work Items, preview, Save items, `Title 1`/`Title 2` hierarchy, troubleshooting) and Jira Cloud (admin permission, Settings → System → External System Import → CSV, column mapping, epic/parent differences, troubleshooting). Verify every click path against the official docs fetched in Task 6; dry-run the steps against the real example CSVs where a test project is available, otherwise say "not tested against a live instance" in the guide.
- [ ] **Step 2: Write `docs/prompt-design.md`:** why persona, rubric, few-shot, JSON schema, anti-invention rules; INVEST rubric table.
- [ ] **Step 3: Capture demo GIF** of demo mode in the browser pane and save to `docs/`.
- [ ] **Step 4: Write both READMEs** in the order of spec §11: value line, badge, GIF, problem (only claims the author can support — ask the author for a real data point or use "from my experience as a PO"), solution + flow diagram, product decisions (INVEST reviewer, Gherkin, interview deferred to v2), before/after story with INVEST scores taken from `examples/`, 3-command run + demo mode + free providers ("verify current limits"), links to import guides, roadmap, limitations, license. Ask the author for their GitHub username for the badge URL.
- [ ] **Step 5: Run full suite** `python -m pytest -q` → all PASS.
- [ ] **Step 6: Commit** `docs: READMEs, import guides, prompt design`.

### Task 10: Portfolio handoff

**Files:** none in repo.

- [ ] **Step 1: Write the CV/LinkedIn text in chat** (spec §11): one project line (PT-BR and EN) and three result bullets grounded in what was actually built.
- [ ] **Step 2: Ask the author** whether to create the GitHub repository and push; do not publish without their explicit yes.
