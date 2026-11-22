# Spec review page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (inline). Steps use checkbox syntax.

**Goal:** A local Streamlit page that runs the `po-spec-review` skill through the Claude Code CLI (subscription login, no API key) on an uploaded spec, offers the stories PDF, and pushes to Azure DevOps only through a separate confirm button.

**Architecture:** `src/claude_cli.py` wraps the CLI (injectable runner, so tests use a fake). `spec_review_page.py` is the UI and reuses `src/azure_devops.py`. No change to `app.py`.

**Tech Stack:** Python 3.14 locally (3.11 in CI), Streamlit (AppTest), pytest, existing `src.azure_devops`.

**Spec:** `docs/superpowers/specs/2026-11-22-spec-review-page-design.md`

## Global Constraints

- Python: `C:\Users\dpere\AppData\Local\Programs\Python\Python314\python.exe -m pytest`; CI is 3.11, so no 3.12+ only syntax.
- The CLI path default is `~/.local/bin/claude.exe`; not on PATH.
- Confidential input: temp dir only, deleted in `finally`; never written under the repo.
- The PAT is never stored, logged or put in an error message.
- Azure send only via the confirm button, enabled only after a preview for the same org/project.
- Portuguese (pt-BR) UI text.

## Review Focus

- CLI missing, logged out ("OAuth session expired"), or exiting non-zero with no result: a plain message, not a traceback.
- Skill finishes but writes no `stories.json` or no PDF: clear message, no crash.
- Org/project changed after the preview: the confirm button must be disabled again.
- Temp dir removed even when the run fails.
- Re-clicking confirm must not duplicate (ledger in session state per org/project).

---

### Task 1: CLI wrapper

**Files:** Create `src/claude_cli.py`, `tests/test_claude_cli.py`

**Interfaces:**
- Produces:
  - `class ClaudeCliError(Exception)` with `.kind` in `{"not_found","auth","failed"}`.
  - `find_claude(path_env: str | None = None, home: Path | None = None) -> Path`: PATH lookup via `shutil.which("claude")`, else `home/.local/bin/claude.exe` (or `claude`), else raise `ClaudeCliError("not_found")`.
  - `build_command(exe: Path, prompt: str) -> list[str]`: `[exe, "-p", prompt, "--output-format", "stream-json", "--verbose", "--permission-mode", "acceptEdits", "--allowedTools", "Read", "Write", "Bash"]`.
  - `@dataclass Event(kind: str, text: str)` with kinds `"text"` and `"result"`.
  - `parse_events(lines: Iterable[str]) -> Iterator[Event]`: JSON lines; `assistant` messages yield one `text` Event per text block; a `result` line yields a `result` Event; a result with `is_error` true whose text contains "authenticate", "OAuth" or "login" raises `ClaudeCliError("auth")`; any other `is_error` raises `ClaudeCliError("failed")` with the text; non-JSON lines are skipped.
  - `default_runner(cmd: list[str], cwd: Path) -> Iterator[str]`: `subprocess.Popen` with utf-8, yields stdout lines; non-zero exit and no result seen is handled by `parse_events` caller (see Task 2).

- [ ] **Step 1: Failing tests** in `tests/test_claude_cli.py`: `test_find_claude_uses_home_fallback` (tmp home with `.local/bin/claude.exe`, PATH empty → that path), `test_find_claude_not_found` (raises kind `not_found`), `test_build_command_is_headless` (contains `-p`, `stream-json`, `--verbose`, prompt as the arg after `-p`), `test_parse_events_text_and_result`, `test_parse_events_auth_error_raises` (result line `{"type":"result","is_error":true,"result":"Failed to authenticate: OAuth session expired and could not be refreshed"}` → kind `auth`), `test_parse_events_other_error_is_failed`, `test_parse_events_skips_garbage`.
- [ ] **Step 2:** Run `python -m pytest tests/test_claude_cli.py -q`. Expected: FAIL (module missing).
- [ ] **Step 3:** Implement `src/claude_cli.py` as specified.
- [ ] **Step 4:** Run the file. Expected: all pass.
- [ ] **Step 5:** Commit `feat: claude CLI wrapper`.

### Task 2: Review workflow

**Files:** Modify `src/claude_cli.py`; extend `tests/test_claude_cli.py`

**Interfaces:**
- Consumes: Task 1.
- Produces:
  - `@dataclass ReviewResult(text: str, stories: dict, pdf: bytes)`.
  - `REVIEW_PROMPT` (pt-BR): use the `po-spec-review` skill on `{spec_name}` in this folder; run without asking questions; also write `stories.json` (the skill's JSON) and `historias.pdf` in this folder; do not send anything to Azure DevOps.
  - `review_spec(data: bytes, filename: str, on_event: Callable[[Event], None] | None = None, runner=default_runner, exe: Path | None = None) -> ReviewResult`: create a temp dir (`tempfile.mkdtemp`), write `data` to `spec<suffix>` (suffix from filename, `.pdf` or `.txt`/`.md`), build the command, stream events to `on_event` and collect text, then read `stories.json` and `historias.pdf`. Missing files → `ClaudeCliError("failed")` with a message naming which is missing. A runner that raises, or ends with no `result` event, → `ClaudeCliError("failed")`. Always `shutil.rmtree` the temp dir in `finally`.

- [ ] **Step 1: Failing tests** with a fake runner that writes `stories.json` and `historias.pdf` into `cwd` and yields stream lines: `test_review_spec_returns_text_stories_pdf`, `test_review_spec_cleans_temp_dir` (cwd captured by the fake; gone afterwards, also when the fake raises), `test_review_spec_missing_outputs_fails`, `test_review_spec_no_result_event_fails`, `test_review_spec_writes_spec_with_suffix` (fake asserts `spec.pdf` exists with the bytes).
- [ ] **Step 2:** Run; Expected: FAIL.
- [ ] **Step 3:** Implement `review_spec` and `REVIEW_PROMPT`.
- [ ] **Step 4:** Run the file; Expected: pass. Then run the full suite; Expected: green.
- [ ] **Step 5:** Commit `feat: review_spec workflow with temp-dir cleanup`.

### Task 3: The page

**Files:** Create `spec_review_page.py`, `tests/test_spec_review_page.py`

**Interfaces:**
- Consumes: `claude_cli.review_spec`, `claude_cli.ClaudeCliError`, `azure_devops.items_from_stories_json`, `normalize_organization`, `Ledger.load(None, org, project)`, `plan`, `push`, `AzureDevOpsClient`.
- Produces: `streamlit run spec_review_page.py`. Widget keys: `spec_file` (uploader, pdf/txt/md), `spec_text` (text area), `run_review` (button), `dl_pdf` (download), `azdo_org`, `azdo_project`, `azdo_pat` (password), `azdo_preview`, `azdo_confirm` (primary, disabled until a preview exists for the current org/project and stories fingerprint).

Behavior: the review calls `claude_cli.review_spec` (module attribute looked up at call time so tests can monkeypatch it); shows streamed text in a `st.status`; stores the `ReviewResult` in session state. `ClaudeCliError` kinds show: `not_found` → "Claude Code não encontrado; instale-o ou ajuste o PATH"; `auth` → "Login do Claude Code expirado: abra um terminal, rode `claude` e entre de novo"; `failed` → the message. The preview stores `(org, project, fingerprint)`; confirm is disabled whenever the current values differ. Confirm calls `push(client, items, ledger, confirmed=True)` with the per-scope ledger from session state and shows the same summary and links as `app.py`.

- [ ] **Step 1: Failing AppTest tests** (monkeypatch `claude_cli.review_spec` to return a fixed `ReviewResult` with two stories with tasks): `test_page_renders_and_confirm_disabled_before_review`, `test_review_shows_pdf_download` (after clicking `run_review` with `spec_text` filled), `test_auth_error_shows_login_message`, `test_not_found_shows_install_message`, `test_confirm_disabled_until_preview`, `test_confirm_disabled_again_when_org_changes`, `test_confirm_sends_via_push` (monkeypatch `azure_devops.push` to record the call; assert `confirmed=True` and called once).
- [ ] **Step 2:** Run; Expected: FAIL.
- [ ] **Step 3:** Implement the page (light CSS reuse: copy the `STYLE` block idea, do not import `app.py`, which runs `main()` on import).
- [ ] **Step 4:** Run the file, then the full suite; Expected: green.
- [ ] **Step 5:** Commit `feat: spec review page`.

### Task 4: Docs and run check

**Files:** Modify `README.md`, `README.pt-BR.md`; create `docs/spec-review-page.pt-BR.md`

- [ ] **Step 1:** Write the doc: what it is, how to run (`python -m streamlit run spec_review_page.py`), the login requirement (`claude` in a terminal), local-only and plan-limit caveats, and that real reviews were not verified by the builder. Add one line to each README pointing to it.
- [ ] **Step 2:** Full suite; Expected: green.
- [ ] **Step 3:** Start the page on port 8502 and confirm HTTP 200 with curl.
- [ ] **Step 4:** Commit `docs: spec review page`.
